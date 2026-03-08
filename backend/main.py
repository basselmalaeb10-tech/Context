"""FastAPI backend for the Context reading assistant."""

import os
import shutil
from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.pdf_parser import extract_text, extract_pages
from services.concept_engine import (
    extract_concepts, extract_book_metadata, build_dependency_graph,
    build_concept_map, extract_page_concepts,
)
from services.calibration import generate_questions, build_reader_profile
from services.explanation import generate_explanation, detect_difficult_passage
from services.session import create_session, save_session, load_session, list_sessions

app = FastAPI(title="Context — AI Reading Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".epub"}

# Serve frontend static build if it exists
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


# --- Models ---

class CalibrationAnswers(BaseModel):
    answers: dict[str, int]  # question_id -> familiarity level (0-3)


class ExplanationRequest(BaseModel):
    selected_text: str
    surrounding_text: str = ""
    page: int = 1
    mode: str = "quick"  # "quick", "deep", "prerequisites", "why_it_matters"


class MetadataConfirmation(BaseModel):
    title: str
    author: str


# --- Endpoints ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a PDF or EPUB and extract book metadata for confirmation."""
    if not file.filename:
        raise HTTPException(400, "No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Only {', '.join(ALLOWED_EXTENSIONS)} files are accepted.")

    # Save the file
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    full_text = extract_text(str(dest))
    if len(full_text.strip()) < 50:
        raise HTTPException(400, "Could not extract enough text from this file.")

    # Extract book metadata using LLM
    try:
        book_metadata = extract_book_metadata(full_text)
    except Exception as e:
        raise HTTPException(500, f"Failed to analyze book metadata: {e}")

    # Create session with metadata (analysis happens after user confirms)
    session = create_session(document_name=file.filename, pdf_path=str(dest))
    session.book_metadata = book_metadata
    save_session(session)

    return {
        "session_id": session.id,
        "document_name": session.document_name,
        "book_metadata": book_metadata,
    }


@app.post("/api/sessions/{session_id}/confirm")
def confirm_metadata(session_id: str, body: MetadataConfirmation):
    """User confirms/corrects book metadata, then full analysis runs."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    # Update metadata with user corrections
    session.book_metadata["title"] = body.title
    session.book_metadata["author"] = body.author

    # Now run full analysis with confirmed metadata
    try:
        full_text = extract_text(session.pdf_path)
        concepts = extract_concepts(full_text, book_metadata=session.book_metadata)
        dep_graph = build_dependency_graph(concepts)
        concept_map = build_concept_map(concepts)
        questions = generate_questions(concepts, book_metadata=session.book_metadata)
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")

    session.concepts = [asdict(c) for c in concepts]
    session.dependency_graph = dep_graph
    session.concept_map = concept_map
    session.calibration_questions = [asdict(q) for q in questions]
    save_session(session)

    return {
        "session_id": session.id,
        "book_metadata": session.book_metadata,
        "concept_count": len(concepts),
        "concept_map": concept_map,
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
        "book_metadata": session.book_metadata,
        "concept_count": len(session.concepts),
        "concept_map": session.concept_map,
        "is_calibrated": bool(session.reader_profile),
        "current_page": session.current_page,
    }


@app.get("/api/sessions/{session_id}/pdf")
def serve_pdf(session_id: str):
    """Serve the uploaded file for the reader view."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    if not os.path.exists(session.pdf_path):
        raise HTTPException(404, "File not found.")
    return FileResponse(session.pdf_path)


@app.get("/api/sessions/{session_id}/pages")
def get_pages(session_id: str):
    """Get extracted text pages for the document."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    pages = extract_pages(session.pdf_path)
    return {"pages": pages, "total_pages": len(pages)}


@app.get("/api/sessions/{session_id}/page-concepts")
def get_page_concepts(session_id: str, page: int = 1):
    """Get concepts relevant to a specific page for the sidebar."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    pages = extract_pages(session.pdf_path)
    page_data = next((p for p in pages if p["page"] == page), None)
    if not page_data:
        return {"concepts": []}

    from services.concept_engine import Concept
    all_concepts = [Concept(**c) for c in session.concepts]

    page_concepts = extract_page_concepts(
        page_text=page_data["text"],
        page_number=page,
        all_concepts=all_concepts,
        book_metadata=session.book_metadata,
    )

    return {"concepts": page_concepts, "page": page}


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
        book_metadata=session.book_metadata,
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


# --- Serve frontend SPA ---
# Mount static assets if the frontend has been built
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve the frontend SPA for all non-API routes."""
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return HTMLResponse(index.read_text())
        raise HTTPException(404, "Frontend not built. Run: cd frontend && npm run build")
