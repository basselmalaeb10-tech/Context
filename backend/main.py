"""FastAPI backend for the Context reading assistant."""

import os
import shutil
from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.pdf_parser import extract_text, extract_pages
from services.concept_engine import extract_concepts, build_dependency_graph
from services.calibration import generate_questions, build_reader_profile
from services.explanation import generate_explanation, detect_difficult_passage
from services.session import create_session, save_session, load_session, list_sessions

app = FastAPI(title="Context — AI Reading Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# --- Models ---

class CalibrationAnswers(BaseModel):
    answers: dict[str, int]  # question_id -> familiarity level (0-3)


class ExplanationRequest(BaseModel):
    selected_text: str
    surrounding_text: str = ""
    page: int = 1
    mode: str = "quick"  # "quick", "deep", "prerequisites", "why_it_matters"


# --- Endpoints ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF and trigger document analysis."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    # Save the file
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text and analyze
    full_text = extract_text(str(dest))
    if len(full_text.strip()) < 50:
        raise HTTPException(400, "Could not extract enough text from this PDF.")

    concepts = extract_concepts(full_text)
    dep_graph = build_dependency_graph(concepts)
    questions = generate_questions(concepts)

    # Create session
    session = create_session(document_name=file.filename, pdf_path=str(dest))
    session.concepts = [asdict(c) for c in concepts]  # type: ignore
    session.dependency_graph = dep_graph
    session.calibration_questions = [asdict(q) for q in questions]  # type: ignore
    save_session(session)

    return {
        "session_id": session.id,
        "document_name": session.document_name,
        "concept_count": len(concepts),
        "calibration_questions": session.calibration_questions,
    }


@app.post("/api/sessions/{session_id}/calibrate")
def submit_calibration(session_id: str, body: CalibrationAnswers):
    """Submit calibration answers and build reader profile."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    from services.calibration import CalibrationQuestion
    questions = [CalibrationQuestion(**q) for q in session.calibration_questions]
    profile = build_reader_profile(body.answers, questions)

    session.reader_profile = profile
    save_session(session)

    return {"status": "calibrated", "profile": profile}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """Get session metadata."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    return {
        "id": session.id,
        "document_name": session.document_name,
        "concept_count": len(session.concepts),
        "is_calibrated": bool(session.reader_profile),
        "current_page": session.current_page,
    }


@app.get("/api/sessions/{session_id}/pdf")
def serve_pdf(session_id: str):
    """Serve the uploaded PDF for the reader view."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    if not os.path.exists(session.pdf_path):
        raise HTTPException(404, "PDF file not found.")
    return FileResponse(session.pdf_path, media_type="application/pdf")


@app.get("/api/sessions/{session_id}/pages")
def get_pages(session_id: str):
    """Get extracted text pages for the document."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    pages = extract_pages(session.pdf_path)
    return {"pages": pages, "total_pages": len(pages)}


@app.post("/api/sessions/{session_id}/explain")
def explain(session_id: str, body: ExplanationRequest):
    """Generate a context-aware explanation for selected text."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    result = generate_explanation(
        selected_text=body.selected_text,
        surrounding_text=body.surrounding_text,
        mode=body.mode,
        reader_profile=session.reader_profile,
        concepts=session.concepts,
        dependency_graph=session.dependency_graph,
    )

    return {
        "selected_text": result.selected_text,
        "mode": result.mode,
        "content": result.content,
        "related_concepts": result.related_concepts,
    }


@app.get("/api/sessions/{session_id}/nudge")
def check_nudge(session_id: str, page: int = 1):
    """Check if the current page has a concept the reader might need help with."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    pages = extract_pages(session.pdf_path)
    page_data = next((p for p in pages if p["page"] == page), None)
    if not page_data:
        return {"nudge": None}

    nudge = detect_difficult_passage(
        page_text=page_data["text"],
        reader_profile=session.reader_profile,
        concepts=session.concepts,
    )

    return {"nudge": nudge}


@app.put("/api/sessions/{session_id}/page")
def update_page(session_id: str, page: int = 1):
    """Update the reader's current page position."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    session.current_page = page
    save_session(session)
    return {"current_page": page}


@app.get("/api/sessions")
def get_sessions():
    """List all sessions."""
    return {"sessions": list_sessions()}
