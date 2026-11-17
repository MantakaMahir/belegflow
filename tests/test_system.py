import asyncio
import io
import time
from decimal import Decimal
from email.message import EmailMessage

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.demo import SCENARIOS
from app.documents import attachments, image_part, validate_file
from app.exports import export_row, spreadsheet_value
from app.main import RequestSizeLimitMiddleware, create_app
from app.models import Extraction
from app.providers import AI, convert_money, historical_fx


@pytest.fixture
def client(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Demo attempted an external request")

    monkeypatch.setattr(httpx, "get", no_network)
    monkeypatch.setattr(AI, "structured", no_network)
    app = create_app(
        Settings(data_dir=tmp_path, seed_demo=False, openai_api_key="", _env_file=None)
    )
    with TestClient(app, base_url="http://localhost") as value:
        yield value


def settled(client, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] not in {"processing", "queued"}:
            return run
        time.sleep(0.02)
    raise AssertionError("Workflow did not settle")


def demo(client, scenario="us-dividend"):
    response = client.post("/api/demo", json={"scenario_id": scenario})
    assert response.status_code == 201
    return settled(client, response.json()["run"]["id"])


def review_payload(run):
    return {
        key: run["result"][key]
        for key in (
            "document_id",
            "client_name",
            "party",
            "purpose",
            "document_date",
            "original_amount",
            "currency",
            "income_type",
        )
    }


def test_real_demo_review_and_export_with_no_network(client):
    run = demo(client)
    assert run["status"] == "review"
    assert run["result"]["fx"]["amount_eur"] == "1101.50"
    assert run["result"]["fx"]["tax_deduction_eur"] == "165.23"
    assert "file_path" not in run and "fingerprint" not in run
    assert client.get(f"/api/runs/{run['id']}/export").status_code == 409
    events = client.get(f"/api/runs/{run['id']}/events").json()
    assert [event["node"] for event in events if event["status"] == "completed"] == [
        "intake",
        "extract",
        "fx",
        "classify",
        "validate",
    ]
    assert all(
        "duration_ms" in event["payload"] for event in events if event["status"] == "completed"
    )
    assert "usage" not in run  # No fabricated model metrics.
    response = client.post(
        f"/api/runs/{run['id']}/approve", json={**review_payload(run), "notes": "Reviewed fixture"}
    )
    assert response.status_code == 200, response.text
    run = settled(client, run["id"])
    assert run["status"] == "approved"
    assert run["result"]["reviewed_at"]
    csv = client.get(f"/api/runs/{run['id']}/export")
    assert csv.status_code == 200 and "1101.50" in csv.text and "Reviewed fixture" in csv.text
    assert client.get(f"/api/runs/{run['id']}/export?format=json").json()["mode"] == "demo"
    assert client.post(f"/api/runs/{run['id']}/sheets").status_code == 409


def test_live_upload_uses_typed_provider_boundary_fx_and_review(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    extraction = {
        "document_id": "LIVE-TEST-01",
        "client_name": "Alex Morgan",
        "client_number": "",
        "language": "en",
        "translated_text": "FIKTIVE RECHNUNG EUR 100,00",
        "document_type": "Invoice",
        "document_date": "2025-05-12",
        "period_start": None,
        "period_end": None,
        "tax_year": 2025,
        "original_amount": "100.00",
        "currency": "USD",
        "party": "Studio North",
        "purpose": "Design services",
        "tax_deduction": None,
        "tax_types": [],
        "periodicity": "One-time",
        "warnings": [],
    }
    classification = {
        "income_type": "Self-employment",
        "relevance": "Possibly relevant",
        "assessment": "Review the issuer's role.",
        "evidence": ["Design services"],
        "warnings": [],
    }
    monkeypatch.setattr(AI, "extract", lambda self, text: (extraction, None))
    monkeypatch.setattr(AI, "classify", lambda self, text, facts: (classification, None))

    def fx_request(url, **kwargs):
        return httpx.Response(
            200,
            json={"base": "USD", "date": "2025-05-12", "rates": {"EUR": 0.9}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("app.providers.httpx.get", fx_request)
    settings = Settings(
        data_dir=tmp_path, seed_demo=False, openai_api_key="test-key", _env_file=None
    )
    app = create_app(settings)
    with TestClient(app, base_url="http://localhost") as value:
        response = value.post(
            "/api/upload",
            files={"file": ("invoice.txt", b"Design services\nAmount USD 100.00", "text/plain")},
        )
        assert response.status_code == 201, response.text
        run = settled(value, response.json()[0]["run"]["id"])
        assert run["mode"] == "live" and run["status"] == "review"
        assert run["original_text"] == "Design services\nAmount USD 100.00"
        assert run["result"]["fx"]["amount_eur"] == "90.00"
        assert run["result"]["evidence"] == ["Design services"]
        assert (
            value.post(f"/api/runs/{run['id']}/approve", json=review_payload(run)).status_code
            == 200
        )
        assert settled(value, run["id"])["status"] == "approved"


def test_missing_data_blocks_approval_but_can_be_corrected(client):
    run = demo(client, "ambiguous-receipt")
    assert run["result"]["currency"] is None
    assert run["result"]["fx"]["amount_eur"] is None
    assert "document_date" in run["result"]["missing_fields"]
    assert (
        client.post(f"/api/runs/{run['id']}/approve", json=review_payload(run)).status_code == 422
    )
    body = {
        **review_payload(run),
        "currency": "EUR",
        "document_date": "2025-05-12",
        "income_type": "Business",
    }
    assert client.post(f"/api/runs/{run['id']}/approve", json=body).status_code == 200
    approved = settled(client, run["id"])
    assert approved["status"] == "approved" and approved["result"]["fx"]["amount_eur"] == "480.00"


def test_duplicate_intake_and_local_boundaries(client):
    first = demo(client)
    second = client.post("/api/demo", json={"scenario_id": "us-dividend"}).json()
    assert second["created"] is False and first["id"] == second["run"]["id"]
    assert len(client.get("/api/runs").json()) == 1
    assert (
        client.post(
            "/api/demo",
            headers={"Origin": "https://attacker.example"},
            json={"scenario_id": "us-dividend"},
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
    assert client.post("/api/upload", files={"file": ("file.txt", b"example")}).status_code == 409
    assert client.post("/api/demo", json={"scenario_id": "not-real"}).status_code == 422
    assert client.get("/api/runs/unknown").status_code == 404
    assert "api_key" not in str(client.get("/api/config").json()).lower()


def test_only_local_hosts_are_allowed(client):
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400


def test_configured_public_host_is_allowed_but_spoofed_hosts_are_not(tmp_path):
    settings = Settings(
        data_dir=tmp_path, seed_demo=False, public_host="belegflow.gotiq.co", _env_file=None
    )
    with TestClient(create_app(settings), base_url="https://belegflow.gotiq.co") as client:
        assert client.get("/api/health").status_code == 200
        assert (
            client.post(
                "/api/demo",
                headers={"Origin": "https://belegflow.gotiq.co"},
                json={"scenario_id": "us-dividend"},
            ).status_code
            == 201
        )
        assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400


def test_public_mode_fails_closed_without_the_access_identity(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        seed_demo=False,
        public_host="belegflow.gotiq.co",
        cloudflare_access_required=True,
        public_access_email="owner@example.com",
        _env_file=None,
    )
    with TestClient(create_app(settings), base_url="https://belegflow.gotiq.co") as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/runs").status_code == 403
        assert (
            client.get(
                "/api/runs", headers={"Cf-Access-Authenticated-User-Email": "other@example.com"}
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/runs", headers={"Cf-Access-Authenticated-User-Email": "owner@example.com"}
            ).status_code
            == 200
        )


def test_public_demo_is_anonymous_read_only_and_isolates_live_records(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        seed_demo=False,
        public_host="belegflow.gotiq.co",
        public_demo_mode=True,
        openai_api_key="must-not-be-exposed",
        google_credentials_file="private-credentials.json",
        google_drive_folder_id="private-folder",
        _env_file=None,
    )
    with TestClient(create_app(settings), base_url="https://belegflow.gotiq.co") as client:
        app = client.app
        app.state.store.create(
            {
                "id": "private-live-run",
                "mode": "live",
                "filename": "private-tax-record.pdf",
                "fingerprint": "private-document-fingerprint",
                "scenario_id": None,
                "original_text": "CONFIDENTIAL PRIVATE DOCUMENT",
                "result": {"client_name": "Private Client"},
            }
        )

        config = client.get("/api/config").json()
        assert config["public_demo_mode"] is True
        assert config["live_ready"] is False
        assert config["google_ready"] is False
        assert config["drive_ready"] is False
        assert config["provider_host"] == ""
        assert "private-credentials" not in str(config)

        run = demo(client)
        assert all(value["mode"] == "demo" for value in client.get("/api/runs").json())
        assert client.get("/api/runs/private-live-run").status_code == 404
        assert client.get("/api/runs/private-live-run/events").status_code == 404
        assert client.get("/api/runs/private-live-run/stream").status_code == 404
        assert client.get("/api/runs/private-live-run/export").status_code == 404

        assert client.post("/api/upload", files={"file": ("tax.pdf", b"private")}).status_code == 403
        assert client.post("/api/import", json={"source": "drive", "limit": 1}).status_code == 403
        assert (
            client.post(f"/api/runs/{run['id']}/approve", json=review_payload(run)).status_code
            == 403
        )
        assert client.post(f"/api/runs/{run['id']}/retry").status_code == 403
        assert client.post(f"/api/runs/{run['id']}/sheets").status_code == 403
        assert client.get(f"/api/runs/{run['id']}/export").status_code == 409

        response = client.get("/api/runs/private-live-run")
        assert "CONFIDENTIAL" not in response.text
        assert "Private Client" not in response.text


def test_graph_definition_and_sse_come_from_execution(client):
    run = demo(client, "german-invoice")
    graph = client.get("/api/workflow").json()
    assert len(graph["nodes"]) == 7 and len(graph["edges"]) == 6
    assert {"source": "review", "target": "finalize"} in graph["edges"]
    stream = client.get(f"/api/runs/{run['id']}/stream")
    assert "event: step" in stream.text and "event: settled" in stream.text
    assert "Extract" not in stream.text or "extraction" in stream.text
    assert run["result"]["fx"]["rate"] == "1"


def test_review_checkpoint_survives_restart(tmp_path):
    settings = Settings(data_dir=tmp_path, seed_demo=False, openai_api_key="", _env_file=None)
    with TestClient(create_app(settings), base_url="http://localhost") as client:
        run = demo(client)
    with TestClient(create_app(settings), base_url="http://localhost") as client:
        assert client.get(f"/api/runs/{run['id']}").json()["status"] == "review"
        assert (
            client.post(f"/api/runs/{run['id']}/approve", json=review_payload(run)).status_code
            == 200
        )
        assert settled(client, run["id"])["status"] == "approved"


def test_money_validation_and_formula_injection():
    assert convert_money("187.50", "0.8812") == "165.23"
    assert convert_money("0.10", "0.20") == "0.02"
    assert convert_money(None, "1") is None
    for value in ('=HYPERLINK("https://bad.example")', " +cmd", "@SUM(A1)", "-10+1"):
        assert spreadsheet_value(value).startswith("'")
    assert spreadsheet_value("ordinary text") == "ordinary text"
    row = export_row(
        {
            "result": {
                "original_amount": "-12.50",
                "tax_year": 2025,
                "fx": {"amount_eur": "-10.20"},
            },
            "filename": "=bad.txt",
        }
    )
    assert row[13] == "-12.50" and row[16] == "-10.20" and row[4] == "'=bad.txt"
    with pytest.raises(ValueError):
        Extraction(original_amount=Decimal("NaN"))
    with pytest.raises(ValueError):
        Extraction(currency="../../")
    with pytest.raises(ValueError):
        Settings(openai_base_url="http://untrusted.example/v1", _env_file=None)


def test_fx_uses_fixed_host_and_effective_date(monkeypatch):
    called = []

    def fetch(url, **kwargs):
        called.append((url, kwargs))
        return httpx.Response(
            200,
            json={"base": "USD", "date": "2025-04-17", "rates": {"EUR": 0.8812}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fetch)
    result = historical_fx(SCENARIOS["us-dividend"]["extraction"], "live")
    assert result["amount_eur"] == "1101.50" and result["date"] == "2025-04-17"
    assert called[0][0] == "https://api.frankfurter.dev/v1/2025-04-18"
    assert called[0][1]["params"] == {"base": "USD", "symbols": "EUR"}


def test_upload_validation_and_email_attachment_parser():
    assert validate_file("../../invoice.txt", b"Example", 100) == "invoice.txt"
    with pytest.raises(ValueError):
        validate_file("invoice.pdf", b"not a pdf", 100)
    with pytest.raises(ValueError):
        validate_file("file.txt", b"\x00", 100)
    message = EmailMessage()
    message.set_content("Document attached")
    message.add_attachment(
        b"Invoice EUR 20", maintype="text", subtype="plain", filename="invoice.txt"
    )
    assert attachments("email.eml", message.as_bytes(), 10000) == [
        ("invoice.txt", b"Invoice EUR 20")
    ]
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
    part = image_part(buffer.getvalue())
    assert part["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_request_size_boundary_rejects_chunked_body_without_content_length():
    called, sent = False, []

    async def endpoint(scope, receive, send):
        nonlocal called
        called = True
        while True:
            if (await receive())["type"] == "http.disconnect":
                break

    chunks = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def exercise():
        await RequestSizeLimitMiddleware(endpoint, limit=5)(
            {"type": "http", "method": "POST", "headers": []}, receive, send
        )

    asyncio.run(exercise())
    assert called and sent[0]["status"] == 413

    async def endpoint_not_reached(scope, receive, send):
        pytest.fail("oversized Content-Length must be rejected before route handling")

    async def unused_receive():
        pytest.fail("request body must not be read when Content-Length is oversized")

    async def exercise_declared():
        await RequestSizeLimitMiddleware(endpoint_not_reached, limit=5)(
            {"type": "http", "method": "POST", "headers": [(b"content-length", b"6")]},
            unused_receive,
            send,
        )

    sent.clear()
    asyncio.run(exercise_declared())
    assert sent[0]["status"] == 413


def test_local_database_permissions_and_preserve_existing_directory_mode(tmp_path):
    import os
    import stat

    if os.name == "nt":
        pytest.skip("POSIX file permissions are not available on Windows")
    from app.store import Store

    directory = tmp_path / "private"
    directory.mkdir(mode=0o755)
    directory.chmod(0o755)
    store = Store(directory)
    assert stat.S_IMODE(store.directory.stat().st_mode) == 0o755
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE((store.directory / "uploads").stat().st_mode) == 0o700
