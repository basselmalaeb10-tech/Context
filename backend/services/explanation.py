"""LLM-powered context-aware explanation engine.

Generates real, tailored explanations using Claude based on:
- the selected text and surrounding context
- the reader's familiarity profile
- the document's concept dependency graph
- the book's metadata and domain
- (optionally) web research from book sites and encyclopedias
"""

from dataclasses import dataclass, field

from .llm import call_llm


@dataclass
class WebSource:
    title: str
    url: str
    snippet: str
    source: str  # domain name


@dataclass
class Explanation:
    selected_text: str
    mode: str  # "quick", "deep", "prerequisites", "why_it_matters"
    content: str
    related_concepts: list[str]
    web_sources: list[WebSource] = field(default_factory=list)


def _find_relevant_concepts(
    selected_text: str,
    concepts: list[dict],
) -> list[dict]:
    """Find concepts that appear in or relate to the selected text."""
    text_lower = selected_text.lower()
    relevant = []
    for concept in concepts:
        name = concept.get("name", "").lower()
        if name in text_lower or any(
            p.lower() in text_lower
            for p in concept.get("prerequisites", [])
        ):
            relevant.append(concept)
    return relevant


def _reader_level_label(level: int) -> str:
    return {0: "unfamiliar", 1: "vaguely familiar", 2: "basically familiar", 3: "well-versed"}.get(level, "unfamiliar")


MODE_INSTRUCTIONS = {
    "quick": "Give a concise 2-3 sentence explanation of what this passage means. Focus on clarity. If it references specific concepts, briefly define them.",
    "deep": "Give a thorough explanation (4-8 sentences). Unpack the ideas, explain the underlying logic, define key terms, and show how the ideas connect. If the passage references other thinkers or theories, explain those references.",
    "prerequisites": "Identify what the reader needs to know BEFORE they can fully understand this passage. List prerequisite concepts, theories, or background knowledge. For each one, give a brief explanation. Focus on things the reader has indicated they are unfamiliar with.",
    "why_it_matters": "Explain why this passage matters in the larger context of the book and the field. What are the implications? How does it connect to the book's main argument? Why should the reader care about this point?",
}


def generate_explanation(
    selected_text: str,
    surrounding_text: str,
    mode: str,
    reader_profile: dict[str, int],
    concepts: list[dict],
    dependency_graph: dict[str, list[str]],
    book_metadata: dict | None = None,
    use_web: bool = True,
) -> Explanation:
    """Generate a context-aware explanation for selected text.

    When use_web=True, enriches the explanation with web research from
    book sites, encyclopedias, and educational resources — reducing
    reliance on LLM API credits.
    """
    relevant = _find_relevant_concepts(selected_text, concepts)
    related_names = [c["name"] for c in relevant]

    # Determine reader's level for tone adaptation
    levels = [reader_profile.get(name, 0) for name in related_names]
    avg_level = sum(levels) / len(levels) if levels else 1

    if avg_level < 1:
        tone = "The reader is a beginner. Use simple, accessible language. Define all technical terms. Use analogies where helpful."
    elif avg_level < 2.5:
        tone = "The reader has some background knowledge. You can assume basic familiarity but explain connections and nuances."
    else:
        tone = "The reader is advanced. Be concise and focus on subtle points, implications, and connections they might miss."

    # Build context about known concepts
    concept_context = ""
    if relevant:
        concept_parts = []
        for c in relevant[:5]:
            desc = c.get("description", "")
            prereqs = c.get("prerequisites", [])
            familiarity = _reader_level_label(reader_profile.get(c["name"], 0))
            part = f"- {c['name']}: {desc}"
            if prereqs:
                part += f" (prerequisites: {', '.join(prereqs)})"
            part += f" [reader is {familiarity}]"
            concept_parts.append(part)
        concept_context = "\n\nRelevant concepts in this book:\n" + "\n".join(concept_parts)

    book_context = ""
    if book_metadata:
        book_context = f'\nBook: "{book_metadata.get("title", "")}" by {book_metadata.get("author", "")}\nDomain: {book_metadata.get("domain", "")}\n'

    # --- Web research (free, no API credits needed) ---
    web_context = ""
    web_sources: list[WebSource] = []
    if use_web:
        try:
            from .web_research import research_topic
            research = research_topic(
                text=selected_text,
                book_title=book_metadata.get("title", "") if book_metadata else "",
                book_author=book_metadata.get("author", "") if book_metadata else "",
                book_domain=book_metadata.get("domain", "") if book_metadata else "",
            )
            if research.summary:
                web_context = f"\n\nWEB RESEARCH (use this to improve your explanation):\n{research.summary[:3000]}\n"
            web_sources = [
                WebSource(title=r.title, url=r.url, snippet=r.snippet, source=r.source)
                for r in research.results[:5]
            ]
        except Exception:
            pass  # Web research is best-effort

    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["quick"])

    prompt = f"""{book_context}
SURROUNDING CONTEXT:
{surrounding_text[:2000]}

SELECTED TEXT (this is what the reader highlighted and wants explained):
"{selected_text}"
{concept_context}{web_context}

INSTRUCTION: {mode_instruction}

Tone: {tone}

Respond directly with the explanation. Do not include headers, labels, or meta-commentary. Just explain."""

    content = call_llm(
        prompt=prompt,
        system="You are a knowledgeable reading companion helping someone understand a book. Your explanations should be clear, accurate, and helpful. Draw on your knowledge of the subject matter to provide real, substantive explanations — not vague platitudes. If the text references specific thinkers, theories, or events, explain them concretely. When web research is provided, incorporate relevant information from it to give a more thorough and grounded answer.",
        use_cache=False,  # Explanations should always be fresh
    )

    return Explanation(
        selected_text=selected_text,
        mode=mode,
        content=content,
        related_concepts=related_names,
        web_sources=web_sources,
    )


def detect_difficult_passage(
    page_text: str,
    reader_profile: dict[str, int],
    concepts: list[dict],
) -> str | None:
    """Check if a page contains concepts the reader is unfamiliar with."""
    text_lower = page_text.lower()
    unfamiliar = []

    for concept in concepts:
        name = concept.get("name", "")
        if name.lower() in text_lower and reader_profile.get(name, 0) < 2:
            unfamiliar.append(name)

    if unfamiliar:
        names = ", ".join(unfamiliar[:3])
        return (
            f"This section touches on {names} — concepts you may want "
            f"a quick refresher on. Select any passage to get an explanation."
        )

    return None
