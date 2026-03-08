"""Simple session state persistence.

Stores session data as JSON files on disk. Each session represents
one reader + one document. This is adequate for local MVP usage.
Replace with a database for production.
"""

import json
import os
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


@dataclass
class Session:
    id: str
    document_name: str
    pdf_path: str
    concepts: list[dict] = field(default_factory=list)
    dependency_graph: dict = field(default_factory=dict)
    calibration_questions: list[dict] = field(default_factory=list)
    reader_profile: dict = field(default_factory=dict)
    current_page: int = 1
    highlights: list[dict] = field(default_factory=list)


def create_session(document_name: str, pdf_path: str) -> Session:
    session = Session(
        id=str(uuid.uuid4())[:8],
        document_name=document_name,
        pdf_path=pdf_path,
    )
    save_session(session)
    return session


def save_session(session: Session) -> None:
    path = SESSIONS_DIR / f"{session.id}.json"
    with open(path, "w") as f:
        json.dump(asdict(session), f, indent=2)


def load_session(session_id: str) -> Session | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return Session(**data)


def list_sessions() -> list[dict]:
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        with open(path) as f:
            data = json.load(f)
        sessions.append({"id": data["id"], "document_name": data["document_name"]})
    return sessions
