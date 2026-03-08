"""PDF text extraction and section splitting."""

import fitz  # PyMuPDF
from dataclasses import dataclass


@dataclass
class Section:
    title: str
    text: str
    page_start: int
    page_end: int


def extract_text(pdf_path: str) -> str:
    """Extract full text from a PDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text page by page, returning a list of {page, text} dicts."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def split_into_sections(pages: list[dict]) -> list[Section]:
    """Split pages into rough sections based on text density and headers.

    This is a practical heuristic: lines that are short, uppercase, or start
    a new page after sparse content are treated as section boundaries. For MVP
    this gives a usable approximation without NLP overhead.
    """
    sections: list[Section] = []
    current_title = "Introduction"
    current_text: list[str] = []
    current_start = 1

    for page_data in pages:
        lines = page_data["text"].split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Heuristic: short lines that look like headers
            is_header = (
                len(stripped) < 80
                and not stripped.endswith(".")
                and (stripped.isupper() or stripped.istitle())
                and len(stripped.split()) <= 10
            )
            if is_header and current_text:
                sections.append(Section(
                    title=current_title,
                    text="\n".join(current_text),
                    page_start=current_start,
                    page_end=page_data["page"],
                ))
                current_title = stripped
                current_text = []
                current_start = page_data["page"]
            else:
                current_text.append(stripped)

    # Final section
    if current_text:
        last_page = pages[-1]["page"] if pages else current_start
        sections.append(Section(
            title=current_title,
            text="\n".join(current_text),
            page_start=current_start,
            page_end=last_page,
        ))

    return sections
