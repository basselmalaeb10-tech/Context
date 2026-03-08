"""Document text extraction — supports PDF and EPUB."""

import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class Section:
    title: str
    text: str
    page_start: int
    page_end: int


def extract_text(file_path: str) -> str:
    """Extract full text from a PDF or EPUB file."""
    path = Path(file_path)
    if path.suffix.lower() == ".epub":
        return _extract_epub_text(file_path)
    return _extract_pdf_text(file_path)


def extract_pages(file_path: str) -> list[dict]:
    """Extract text page by page, returning a list of {page, text} dicts."""
    path = Path(file_path)
    if path.suffix.lower() == ".epub":
        return _extract_epub_pages(file_path)
    return _extract_pdf_pages(file_path)


# --- PDF ---

def _extract_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def _extract_pdf_pages(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


# --- EPUB ---

def _strip_html(html: str) -> str:
    """Simple HTML tag stripping for EPUB content."""
    # Remove script and style elements
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block elements with newlines
    text = re.sub(r'<(p|div|br|h[1-6]|li|tr|blockquote)[^>]*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|h[1-6]|li|tr|blockquote)>', '\n', text, flags=re.IGNORECASE)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&#39;', "'")
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_epub_text(epub_path: str) -> str:
    """Extract full text from an EPUB file."""
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        raise RuntimeError("ebooklib is required for EPUB support. Install with: pip install ebooklib")

    book = epub.read_epub(epub_path, options={"ignore_ncx": True})
    texts = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode('utf-8', errors='ignore')
        text = _strip_html(content)
        if text and len(text) > 20:
            texts.append(text)
    return "\n\n".join(texts)


def _extract_epub_pages(epub_path: str) -> list[dict]:
    """Extract EPUB chapters as pages.

    Since EPUBs don't have physical pages, each chapter/section
    becomes a "page" for navigation.
    """
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        raise RuntimeError("ebooklib is required for EPUB support. Install with: pip install ebooklib")

    book = epub.read_epub(epub_path, options={"ignore_ncx": True})
    pages = []
    page_num = 0
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode('utf-8', errors='ignore')
        text = _strip_html(content)
        if text and len(text) > 20:
            page_num += 1
            pages.append({"page": page_num, "text": text})
    return pages


def split_into_sections(pages: list[dict]) -> list[Section]:
    """Split pages into rough sections based on text density and headers."""
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

    if current_text:
        last_page = pages[-1]["page"] if pages else current_start
        sections.append(Section(
            title=current_title,
            text="\n".join(current_text),
            page_start=current_start,
            page_end=last_page,
        ))

    return sections
