import hashlib
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.demo import SCENARIOS
from app.documents import read_document
from app.models import Classification, Extraction, Review
from app.providers import AI, ProviderError, historical_fx
from app.store import Store

logger = logging.getLogger("belegflow")
NODE_META = {
    "intake": (
        "Read document",
        "Text extraction or vision OCR",
        "Read PDF text locally; OCR only scanned pages. The original is kept intact.",
    ),
    "extract": (
        "Extract & translate",
        "Typed document facts",
        "Extract original amounts and dates; translate the document to German without changing the money.",
    ),
    "fx": (
        "Normalize currency",
        "Historical rate · Decimal math",
        "Fetch the document-date EUR rate and calculate amounts using deterministic decimal arithmetic.",
    ),
    "classify": (
        "Classify tax context",
        "Evidence-based suggestion",
        "Suggest a German income category with source quotations and uncertainty notes.",
    ),
    "validate": (
        "Validate record",
        "Completeness & provenance",
        "Validate source evidence, required fields and export readiness. Never invent missing values.",
    ),
    "review": (
        "Human review",
        "Checkpoint · awaiting approval",
        "Pause the graph, persist state, and require a human to confirm or correct the record.",
    ),
    "finalize": (
        "Approve for export",
        "Local approved record",
        "Persist the reviewer-approved record. Google Sheets export is a separate, explicit action.",
    ),
}


class State(TypedDict, total=False):
    run_id: str
    text: str
    extraction: dict
    fx: dict
    classification: dict
    result: dict
    approved: dict


class Engine:
    def __init__(self, settings, store):
        self.settings, self.store = settings, store
        self.ai = AI(settings)
        self.connection = sqlite3.connect(
            settings.data_dir / "checkpoints.db", check_same_thread=False
        )
        Store.restrict(settings.data_dir / "checkpoints.db")
        self.checkpointer = SqliteSaver(self.connection)
        # ponytail: one local worker bounds OCR/memory and serializes checkpoint writes.
        # Use a durable job service and separate workers before hosting multi-user workloads.
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="documents")
        builder = StateGraph(State)
        for name in NODE_META:
            function = getattr(self, name)
            builder.add_node(name, function if name == "review" else self.traced(name, function))
        order = list(NODE_META)
        builder.add_edge(START, order[0])
        for source, target in zip(order, order[1:], strict=False):
            builder.add_edge(source, target)
        builder.add_edge(order[-1], END)
        self.graph = builder.compile(checkpointer=self.checkpointer)

    def close(self):
        self.worker.shutdown(wait=True)
        self.ai.close()
        self.connection.close()

    def traced(self, name, function):
        def step(state):
            run_id = state["run_id"]
            self.store.event(run_id, name, "running")
            started = time.perf_counter()
            try:
                output = function(state)
            except Exception as exc:
                safe = (
                    str(exc)
                    if isinstance(exc, (ProviderError, ValueError))
                    else "Processing failed. Check the local server log and retry."
                )
                self.store.event(run_id, name, "failed", error=safe)
                raise
            duration = round((time.perf_counter() - started) * 1000)
            self.store.event(run_id, name, "completed", duration_ms=duration, output=output)
            return output

        return step

    def create(
        self, *, filename, mode, content=None, scenario_id=None, source="Upload", source_url=None
    ):
        run_id = uuid4().hex
        fingerprint = scenario_id if mode == "demo" else hashlib.sha256(content).hexdigest()
        run, created = self.store.create(
            {
                "id": run_id,
                "mode": mode,
                "filename": filename,
                "fingerprint": fingerprint,
                "scenario_id": scenario_id,
                "source": source,
                "source_url": source_url,
            }
        )
        if created and content is not None:
            path = self.store.directory / "uploads" / f"{run_id}{Path(filename).suffix.lower()}"
            path.write_bytes(content)
            self.store.restrict(path)
            run = self.store.update(run_id, file_path=str(path))
        if created:
            self.worker.submit(self.execute, run_id, {"run_id": run_id})
        return run, created

    def execute(self, run_id, value):
        self.store.update(run_id, status="processing", error=None)
        try:
            output = self.graph.invoke(value, {"configurable": {"thread_id": run_id}})
            if output.get("__interrupt__"):
                self.store.update(run_id, status="review")
                self.store.event(
                    run_id,
                    "review",
                    "waiting",
                    output={"message": "Confirm the extracted record before export."},
                )
        except Exception as exc:
            safe = (
                str(exc)
                if isinstance(exc, (ProviderError, ValueError))
                else "Processing failed. Inspect the local server log and retry."
            )
            logger.error("run_failed id=%s error_type=%s", run_id, type(exc).__name__)
            self.store.update(run_id, status="failed", error=safe)

    def recover(self, *, skip_live=False):
        for run in self.store.list():
            if skip_live and run["mode"] != "demo":
                continue
            if run["status"] in {"processing", "queued"}:
                # Checkpointed steps resume; completed AI steps are not deliberately rerun.
                config = {"configurable": {"thread_id": run["id"]}}
                state = self.graph.get_state(config)
                value = (
                    Command(resume=run["pending_review"])
                    if run.get("pending_review")
                    else (None if state.values else {"run_id": run["id"]})
                )
                self.worker.submit(self.execute, run["id"], value)

    def retry(self, run_id):
        self.store.update(run_id, status="queued", error=None, expected={"status": "failed"})
        self.worker.submit(self.execute, run_id, None)

    def intake(self, state):
        run = self.store.get(state["run_id"])
        usage = None
        if run["mode"] == "demo":
            text = SCENARIOS[run["scenario_id"]]["text"]
        else:
            text, images = read_document(Path(run["file_path"]), self.settings.max_pages)
            if images:
                text, usage = self.ai.ocr(text, images)
            if not text.strip():
                raise ValueError("No readable text found. Upload a clearer document.")
        self.store.update(run["id"], original_text=text)
        self.record_usage(run["id"], usage)
        return {"text": text}

    def extract(self, state):
        run = self.store.get(state["run_id"])
        if run["mode"] == "demo":
            data = Extraction.model_validate(
                SCENARIOS[run["scenario_id"]]["extraction"]
            ).model_dump(mode="json")
        else:
            data, usage = self.ai.extract(state["text"])
            self.record_usage(run["id"], usage)
        return {"extraction": data}

    def fx(self, state):
        run = self.store.get(state["run_id"])
        try:
            result = historical_fx(state["extraction"], run["mode"], run["scenario_id"])
        except ProviderError as exc:
            result = {
                "rate": None,
                "date": None,
                "source": "Unavailable",
                "amount_eur": None,
                "tax_deduction_eur": None,
                "warning": str(exc),
            }
        return {"fx": result}

    def classify(self, state):
        run = self.store.get(state["run_id"])
        if run["mode"] == "demo":
            result = Classification.model_validate(
                SCENARIOS[run["scenario_id"]]["classification"]
            ).model_dump()
        else:
            result, usage = self.ai.classify(state["text"], state["extraction"])
            self.record_usage(run["id"], usage)
        return {"classification": result}

    def validate(self, state):
        extraction, classification, fx = state["extraction"], state["classification"], state["fx"]
        warnings = extraction["warnings"] + classification["warnings"]
        evidence = [quote for quote in classification["evidence"] if quote in state["text"]]
        if len(evidence) != len(classification["evidence"]):
            warnings.append(
                "Some proposed evidence was not an exact source quotation and was excluded."
            )
        if fx.get("warning"):
            warnings.append(fx["warning"])
        missing = [
            key
            for key in (
                "document_id",
                "client_name",
                "document_date",
                "original_amount",
                "currency",
            )
            if extraction.get(key) in (None, "")
        ]
        result = {
            **extraction,
            **classification,
            "evidence": evidence,
            "fx": fx,
            "warnings": list(dict.fromkeys(warnings)),
            "missing_fields": missing,
            "checks_passed": 5 - len(missing),
            "checks_total": 5,
            "review_note": "",
            "reviewed_at": None,
        }
        self.store.update(state["run_id"], result=result)
        return {"result": result}

    def review(self, state):
        approved = interrupt({"record": state["result"], "action": "review"})
        return {"approved": approved}

    def finalize(self, state):
        from app.store import now

        result = {**state["approved"], "reviewed_at": now()}
        self.store.update(state["run_id"], status="approved", result=result, pending_review=None)
        return {"result": result}

    def approve(self, run_id, review: Review):
        run = self.store.get(run_id)
        if run["status"] != "review":
            raise ValueError("Only a document awaiting review can be approved.")
        if review.income_type == "Unclassified":
            raise ValueError("Choose an income category before approving this record.")
        if not review.document_id or not review.client_name or not review.party:
            raise ValueError("Document ID, client name, and counterparty are required.")
        changes = review.model_dump(mode="json", exclude={"notes", "income_type"})
        result = {
            **run["result"],
            **changes,
            "income_type": review.income_type,
            "tax_year": run["result"].get("tax_year") or review.document_date.year,
            "review_note": review.notes,
            "missing_fields": [],
            "checks_passed": 5,
        }
        if result["currency"] != run["result"].get("currency") and result.get("tax_deduction"):
            raise ValueError(
                "Currency changes on a document with withholding require reprocessing; the deduction currency must be verified too."
            )
        result["fx"] = historical_fx(result, run["mode"], run["scenario_id"])
        if result["fx"].get("warning"):
            raise ValueError(result["fx"]["warning"])
        self.store.update(
            run_id, status="queued", pending_review=result, expected={"status": "review"}
        )
        self.store.event(
            run_id, "review", "completed", output={"corrections": changes, "notes": review.notes}
        )
        self.worker.submit(self.execute, run_id, Command(resume=result))

    def record_usage(self, run_id, usage):
        if usage is None:
            return
        previous = self.store.get(run_id).get("usage", {})
        self.store.update(
            run_id,
            usage={
                "input_tokens": previous.get("input_tokens", 0) + usage["input_tokens"],
                "output_tokens": previous.get("output_tokens", 0) + usage["output_tokens"],
                "model": usage["model"],
            },
        )

    def definition(self):
        graph = self.graph.get_graph().to_json()
        return {
            "nodes": [
                {"id": key, "label": value[0], "subtitle": value[1], "description": value[2]}
                for key, value in NODE_META.items()
            ],
            "edges": [
                {"source": edge["source"], "target": edge["target"]}
                for edge in graph["edges"]
                if edge["source"] in NODE_META and edge["target"] in NODE_META
            ],
        }
