# Context — AI Reading Assistant

An intelligent reading companion that reveals what you need to know, exactly when you need it.

Context analyzes uploaded documents, builds an internal knowledge dependency graph, calibrates to the reader's existing knowledge, and delivers context-aware explanations on demand. It's an intelligent footnote system — not a summarizer, not a copilot.

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000.

## How It Works

1. **Upload** a PDF (philosophy, economics, research papers, etc.)
2. **Calibrate** — answer 5–7 quick questions about your familiarity with key concepts
3. **Read** — clean, focused reading interface
4. **Highlight** any text to get context-aware explanations tailored to your level
5. **Choose** your depth: quick explanation, deeper dive, prerequisites, or "why does this matter?"

## Architecture

- **Frontend:** React + TypeScript (Vite)
- **Backend:** Python (FastAPI)
- **PDF Parsing:** PyMuPDF
- **AI Layer:** Mock functions with clean interfaces, ready for LLM drop-in replacement
- **State:** File-based session persistence (JSON)

## Project Structure

```
backend/
  main.py                 # FastAPI app and endpoints
  services/
    pdf_parser.py          # PDF text extraction and section splitting
    concept_engine.py      # Concept extraction and dependency graph
    calibration.py         # Familiarity calibration questions
    explanation.py         # Context-aware explanation engine
    session.py             # Session state persistence

frontend/
  src/
    App.tsx                # App shell and navigation state
    components/
      Upload.tsx           # PDF upload with drag-and-drop
      Calibration.tsx      # Quick familiarity check flow
      Reader.tsx           # Clean reading interface
      ExplanationPanel.tsx # Slide-in explanation panel
    services/
      api.ts               # Backend API client
    styles/
      app.css              # Full design system
```

## LLM Integration

The explanation engine (`backend/services/explanation.py`) uses mock template responses for MVP. Each function includes comments showing exactly where to plug in an LLM call. The concept engine (`concept_engine.py`) similarly uses heuristic extraction that can be replaced with LLM-powered analysis.
