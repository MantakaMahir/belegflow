import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.demo import SCENARIOS
from app.documents import attachments
from app.exports import csv_export
from app.google import append_sheet, import_google
from app.models import ImportInput, Review, RunInput
from app.providers import ProviderError
from app.store import Store
from app.workflow import Engine


class RequestSizeLimitMiddleware:
    """Bound streamed browser writes before multipart parsing can spool large bodies."""

    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length:
            try:
                if int(length) > self.limit:
                    await self.reject(send)
                    return
            except ValueError:
                await self.reject(send)
                return

        size = 0
        oversized = False
        response = []

        async def bounded_receive():
            nonlocal size, oversized
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.limit:
                    oversized = True
                    return {"type": "http.disconnect"}
            return message

        async def capture(message):
            response.append(message)

        try:
            await self.app(scope, bounded_receive, capture)
        except Exception:
            if not oversized:
                raise
        if oversized:
            await self.reject(send)
        else:
            for message in response:
                await send(message)

    @staticmethod
    async def reject(send):
        body = b'{"detail":"Request exceeds the upload limit."}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def public(run):
    return {
        key: value
        for key, value in run.items()
        if key not in {"file_path", "fingerprint", "pending_review"}
    }


def create_app(settings=None):
    settings = settings or Settings()
    store = Store(settings.data_dir)
    engine = Engine(settings, store)

    @asynccontextmanager
    async def lifespan(app):
        engine.recover()
        if settings.seed_demo:
            for key, scenario in SCENARIOS.items():
                engine.create(
                    filename=scenario["filename"],
                    mode="demo",
                    scenario_id=key,
                    source="Demo library",
                )
        yield
        await run_in_threadpool(engine.close)

    app = FastAPI(title="BelegFlow", version="0.1.0", lifespan=lifespan)
    app.state.engine, app.state.store = engine, store
    app.add_middleware(RequestSizeLimitMiddleware, limit=settings.max_upload_bytes + 1024 * 1024)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_boundary(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            same_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
            if origin and origin not in {
                same_origin,
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            }:
                return JSONResponse(
                    {"detail": "Cross-origin writes are not allowed."}, status_code=403
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Document not found."}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(ProviderError)
    async def unavailable(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/config")
    def config():
        return {
            "live_ready": settings.live_ready,
            "model": settings.openai_model,
            "provider_host": urlparse(settings.openai_base_url).hostname,
            "max_upload_mb": settings.max_upload_bytes // 1024 // 1024,
            "max_pages": settings.max_pages,
            "google_ready": bool(settings.google_credentials_file),
            "drive_ready": bool(
                settings.google_credentials_file and settings.google_drive_folder_id
            ),
            "sheets_ready": bool(settings.google_credentials_file and settings.google_sheet_id),
        }

    @app.get("/api/scenarios")
    def scenarios():
        return [
            {
                "id": key,
                "title": value["title"],
                "description": value["description"],
                "filename": value["filename"],
            }
            for key, value in SCENARIOS.items()
        ]

    @app.get("/api/workflow")
    def workflow():
        return engine.definition()

    @app.get("/api/runs")
    def runs():
        return [public(run) for run in store.list()]

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str):
        return public(store.get(run_id))

    @app.post("/api/demo", status_code=201)
    def start_demo(body: RunInput):
        if body.scenario_id not in SCENARIOS:
            raise ValueError("Choose a supported demo scenario.")
        scenario = SCENARIOS[body.scenario_id]
        run, created = engine.create(
            filename=scenario["filename"],
            mode="demo",
            scenario_id=body.scenario_id,
            source="Demo library",
        )
        return {"run": public(run), "created": created}

    @app.post("/api/upload", status_code=201)
    async def upload(file: UploadFile):
        if not settings.live_ready:
            raise HTTPException(
                409, "Live mode is not configured. Choose a prepared demo or set OPENAI_API_KEY."
            )
        try:
            content = await file.read(settings.max_upload_bytes + 1)
        finally:
            await file.close()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(413, "Upload exceeds the 15 MB limit.")
        files = await run_in_threadpool(
            attachments, file.filename or "", content, settings.max_upload_bytes
        )
        result = []
        for name, data in files:
            run, created = await run_in_threadpool(
                engine.create,
                filename=name,
                content=data,
                mode="live",
                source="Email file" if (file.filename or "").lower().endswith(".eml") else "Upload",
            )
            result.append({"run": public(run), "created": created})
        return result

    @app.get("/api/runs/{run_id}/events")
    def events(run_id: str):
        store.get(run_id)
        return store.events(run_id)

    @app.get("/api/runs/{run_id}/stream")
    async def stream(run_id: str, request: Request):
        store.get(run_id)
        after = request.headers.get("last-event-id", "0")
        after = int(after) if after.isdigit() else 0

        async def generate():
            nonlocal after
            while not await request.is_disconnected():
                rows = await run_in_threadpool(store.events, run_id, after)
                for event in rows:
                    after = event["id"]
                    yield f"id: {after}\nevent: step\ndata: {json.dumps(event)}\n\n"
                run = await run_in_threadpool(store.get, run_id)
                if run["status"] not in {"queued", "processing"}:
                    yield f"event: settled\ndata: {json.dumps({'status': run['status']})}\n\n"
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.4)

        return StreamingResponse(
            generate(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    @app.post("/api/runs/{run_id}/approve")
    def approve(run_id: str, body: Review):
        engine.approve(run_id, body)
        return {"status": "queued"}

    @app.post("/api/runs/{run_id}/retry")
    def retry(run_id: str):
        if store.get(run_id)["status"] != "failed":
            raise HTTPException(409, "Only failed runs can be retried.")
        engine.retry(run_id)
        return {"status": "queued"}

    @app.get("/api/runs/{run_id}/export")
    def export(run_id: str, format: str = "csv"):
        run = store.get(run_id)
        if run["status"] != "approved":
            raise HTTPException(409, "Review and approve the document before export.")
        if format == "csv":
            return Response(
                csv_export([run]),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="belegflow-record.csv"'},
            )
        if format != "json":
            raise ValueError("Export format must be csv or json.")
        return JSONResponse(
            public(run),
            headers={"Content-Disposition": 'attachment; filename="belegflow-record.json"'},
        )

    @app.post("/api/import")
    def google_import(body: ImportInput):
        if not settings.live_ready:
            raise HTTPException(409, "Configure live AI before importing documents.")
        return {"imported": import_google(settings, engine, body.source, body.limit)}

    @app.post("/api/runs/{run_id}/sheets")
    def sheets(run_id: str):
        run = store.get(run_id)
        if run["mode"] == "demo" or run["status"] != "approved":
            raise HTTPException(409, "Only approved live documents can be sent to Google Sheets.")
        if run.get("sheets_status"):
            raise HTTPException(
                409,
                "Sheet export already attempted. Check the target sheet before retrying manually.",
            )
        # An ambiguous timeout must not cause an automatic duplicate append.
        store.update(
            run_id,
            sheets_status="attempted",
            expected={"status": "approved", "sheets_status": None},
        )
        target = append_sheet(settings, run)
        store.update(run_id, sheets_status="exported", sheets_range=target)
        store.event(run_id, "sheets", "completed", output={"range": target})
        return {"range": target}

    dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app
