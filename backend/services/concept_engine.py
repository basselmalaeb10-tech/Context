"""LLM-powered concept extraction and knowledge dependency graph.

Uses Claude to intelligently identify concepts, references to other
thinkers/theories, and build a meaningful prerequisite graph.
"""

import json
from dataclasses import dataclass, field

from .llm import call_llm_json


@dataclass
class Concept:
    name: str
    domain: str  # e.g. "philosophy", "economics", "rhetoric", "psychology"
    importance: float  # 0.0 to 1.0
    prerequisites: list[str] = field(default_factory=list)
    description: str = ""
    source_reference: str = ""  # e.g. "Aristotle", "Kahneman"
    page_mentions: list[int] = field(default_factory=list)


def extract_book_metadata(text_sample: str) -> dict:
    """Extract book title, author, and summary from the first few pages.

    Returns dict with keys: title, author, subtitle, summary, domain.
    """
    # Use first ~4000 chars (title page, copyright, intro)
    sample = text_sample[:4000]

    result = call_llm_json(
        prompt=f"""Analyze this text from the beginning of a book and extract metadata.

TEXT:
{sample}

Respond with JSON only:
{{
  "title": "the book title",
  "author": "author name(s)",
  "subtitle": "subtitle if any, or empty string",
  "summary": "A 2-3 sentence summary of what this book is about based on the text",
  "domain": "primary domain (e.g. philosophy, economics, rhetoric, psychology, history, science, self-help, political theory, etc.)"
}}""",
        system="You are a librarian and book analyst. Extract metadata accurately from the text provided. If you cannot determine a field with confidence, use your best guess based on available clues. Respond with valid JSON only.",
    )
    return result


def extract_concepts(full_text: str, book_metadata: dict | None = None) -> list[Concept]:
    """Extract key concepts from document text using LLM.

    Identifies real intellectual concepts, references to other thinkers,
    theories, frameworks, and ideas that a reader might need context for.
    """
    # Use a representative sample — first 6000 + middle 3000 + last 2000 chars
    text_len = len(full_text)
    sample = full_text[:6000]
    if text_len > 12000:
        mid = text_len // 2
        sample += "\n\n[...middle section...]\n\n" + full_text[mid:mid + 3000]
    if text_len > 8000:
        sample += "\n\n[...later section...]\n\n" + full_text[-2000:]

    book_context = ""
    if book_metadata:
        book_context = f"""
Book: "{book_metadata.get('title', 'Unknown')}" by {book_metadata.get('author', 'Unknown')}
Domain: {book_metadata.get('domain', 'general')}
Summary: {book_metadata.get('summary', '')}
"""

    result = call_llm_json(
        prompt=f"""Analyze this book text and extract the key concepts a reader would need to understand.
{book_context}
TEXT SAMPLE:
{sample}

For each concept, identify:
1. Named theories, frameworks, or models (e.g. "Aristotle's Rhetoric Triangle", "Maslow's Hierarchy")
2. References to other thinkers, philosophers, or researchers whose work is cited or built upon
3. Technical terms or jargon specific to the domain
4. Key arguments or theses the author presents
5. Historical events or case studies referenced

Do NOT include:
- Common English words or generic terms
- Names that are just mentioned in passing (chapter authors, editors)
- Section headers or formatting artifacts

Respond with a JSON array of 10-20 concepts:
[
  {{
    "name": "Concept or theory name",
    "domain": "specific domain",
    "importance": 0.9,
    "prerequisites": ["prerequisite concept 1", "prerequisite concept 2"],
    "description": "One sentence explaining what this is and why it matters in this book",
    "source_reference": "Original thinker or source if applicable"
  }}
]

Order by importance (most important first). Importance should reflect how central the concept is to understanding this book.""",
        system="You are an expert academic analyst. Extract meaningful intellectual concepts that would help a reader understand this book. Focus on ideas that require background knowledge — things a reader might need to look up or have explained. Be specific and accurate. Respond with valid JSON only.",
        max_tokens=3000,
    )

    concepts = []
    for item in result:
        concepts.append(Concept(
            name=item["name"],
            domain=item.get("domain", "general"),
            importance=item.get("importance", 0.5),
            prerequisites=item.get("prerequisites", []),
            description=item.get("description", ""),
            source_reference=item.get("source_reference", ""),
        ))
    return concepts


def extract_page_concepts(
    page_text: str,
    page_number: int,
    all_concepts: list[Concept],
    book_metadata: dict | None = None,
) -> list[dict]:
    """Identify which concepts from the book appear on a specific page,
    plus any new references that might need explanation.

    Returns list of dicts with: name, description, needs_explanation, type.
    """
    concept_names = [c.name for c in all_concepts]

    book_context = ""
    if book_metadata:
        book_context = f'Book: "{book_metadata.get("title", "")}" by {book_metadata.get("author", "")}'

    result = call_llm_json(
        prompt=f"""{book_context}

Page {page_number} text:
{page_text[:3000]}

Known concepts in this book: {json.dumps(concept_names)}

Identify concepts, references, or ideas on this page that a reader might want explained.
Include both known concepts from the list above AND any new references (other authors, theories, historical events, data/studies cited).

Respond with JSON array:
[
  {{
    "name": "concept or reference name",
    "is_known_concept": true,
    "needs_explanation": true,
    "explanation_hint": "Brief 1-sentence hint of what this is",
    "type": "theory|person|event|term|study"
  }}
]

Only include items that genuinely warrant explanation — skip obvious terms.""",
        system="You are a reading assistant identifying concepts on a page that readers might need help with. Be selective — only flag things that truly require background knowledge. Respond with valid JSON only.",
        max_tokens=1500,
        use_cache=True,
    )

    return result


def build_dependency_graph(concepts: list[Concept]) -> dict:
    """Build an adjacency-list dependency graph from concepts.

    Returns a dict mapping concept name -> list of prerequisite names.
    """
    graph: dict[str, list[str]] = {}
    for concept in concepts:
        graph[concept.name] = list(set(concept.prerequisites))
    return graph


def build_concept_map(concepts: list[Concept]) -> dict:
    """Build a visual concept map structure for the frontend.

    Returns a graph with nodes and edges suitable for rendering
    an interactive concept map.
    """
    nodes = []
    edges = []
    concept_names = {c.name for c in concepts}

    for concept in concepts:
        nodes.append({
            "id": concept.name,
            "label": concept.name,
            "domain": concept.domain,
            "importance": concept.importance,
            "description": concept.description,
            "source_reference": concept.source_reference,
        })
        for prereq in concept.prerequisites:
            edges.append({
                "from": prereq,
                "to": concept.name,
                "label": "prerequisite for",
            })
            # Add prereq as node if not already a concept
            if prereq not in concept_names:
                nodes.append({
                    "id": prereq,
                    "label": prereq,
                    "domain": concept.domain,
                    "importance": 0.3,
                    "description": "",
                    "source_reference": "",
                    "is_prerequisite_only": True,
                })
                concept_names.add(prereq)

    return {"nodes": nodes, "edges": edges}
