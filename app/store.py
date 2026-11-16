import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


def now():
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "uploads").mkdir(mode=0o700, exist_ok=True)
        self.path = self.directory / "belegflow.db"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, mode TEXT NOT NULL, status TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL, UNIQUE(mode, fingerprint)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL, node TEXT NOT NULL, status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_run ON events(run_id, id);
            """)
        self.restrict(self.path)

    @staticmethod
    def restrict(path):
        if os.name != "nt" and path.exists():
            path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        self.restrict(self.path)
        for suffix in ("-wal", "-shm"):
            self.restrict(Path(f"{self.path}{suffix}"))
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, run):
        stamp = now()
        run = {**run, "created_at": stamp, "updated_at": stamp, "status": "queued"}
        with self.connect() as db:
            try:
                db.execute(
                    "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run["id"],
                        run["mode"],
                        run["status"],
                        run["fingerprint"],
                        stamp,
                        stamp,
                        json.dumps(run),
                    ),
                )
            except sqlite3.IntegrityError:
                row = db.execute(
                    "SELECT payload FROM runs WHERE mode=? AND fingerprint=?",
                    (run["mode"], run["fingerprint"]),
                ).fetchone()
                if row is None:
                    raise
                return json.loads(row["payload"]), False
        return run, True

    def get(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return json.loads(row["payload"])

    def list(self):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM runs ORDER BY created_at DESC").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def update(self, run_id, *, expected=None, **changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            previous = json.loads(row["payload"])
            if expected and any(previous.get(key) != value for key, value in expected.items()):
                raise ValueError("Document state changed. Refresh before trying again.")
            run = {**previous, **changes, "updated_at": now()}
            db.execute(
                "UPDATE runs SET status=?, updated_at=?, payload=? WHERE id=?",
                (run["status"], run["updated_at"], json.dumps(run), run_id),
            )
        return run

    def event(self, run_id, node, status, **payload):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id, created_at, node, status, payload) VALUES (?, ?, ?, ?, ?)",
                (run_id, now(), node, status, json.dumps(payload)),
            )

    def events(self, run_id, after=0):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id", (run_id, after)
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]
