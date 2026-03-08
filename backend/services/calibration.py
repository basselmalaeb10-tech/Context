"""LLM-powered calibration question generation.

Generates meaningful, context-aware familiarity questions based on the
book's actual concepts — not generic word-matching.
"""

from dataclasses import dataclass

from .concept_engine import Concept
from .llm import call_llm_json


@dataclass
class CalibrationQuestion:
    id: str
    concept_name: str
    question: str
    options: list[str]
    context_hint: str = ""  # Brief hint about why this concept matters


FAMILIARITY_LEVELS = [
    "Never heard of it",
    "Heard of it, but can't explain it",
    "I have a basic understanding",
    "I know it well",
]


def generate_questions(
    concepts: list[Concept],
    book_metadata: dict | None = None,
    max_questions: int = 7,
) -> list[CalibrationQuestion]:
    """Generate meaningful familiarity-check questions using LLM.

    Instead of asking "How familiar are you with X?" for random words,
    this identifies the most important prerequisite knowledge areas and
    frames questions that help the reader understand WHY they're being asked.
    """
    # Sort by importance, take top concepts
    sorted_concepts = sorted(concepts, key=lambda c: c.importance, reverse=True)
    selected = sorted_concepts[:max_questions + 3]  # Extra for LLM to choose from

    concept_info = []
    for c in selected:
        concept_info.append({
            "name": c.name,
            "domain": c.domain,
            "description": c.description,
            "source_reference": c.source_reference,
            "prerequisites": c.prerequisites,
        })

    book_context = ""
    if book_metadata:
        book_context = f"""Book: "{book_metadata.get('title', '')}" by {book_metadata.get('author', '')}
Domain: {book_metadata.get('domain', '')}
Summary: {book_metadata.get('summary', '')}"""

    result = call_llm_json(
        prompt=f"""{book_context}

Key concepts in this book:
{concept_info}

Generate {max_questions} calibration questions to assess the reader's background knowledge.
Each question should ask about a concept that is PREREQUISITE to understanding this book —
not about the book's own arguments, but about the background knowledge needed.

For example, if the book discusses Aristotle's rhetoric, ask about "Aristotle's Rhetoric Triangle"
or "the concept of ethos, pathos, and logos" — not about the book's title or author name.

Respond with a JSON array:
[
  {{
    "concept_name": "The concept being assessed",
    "question": "A natural, well-phrased question (not just 'How familiar are you with X?')",
    "context_hint": "Brief note about why this matters for the book (shown to reader)"
  }}
]

Make questions feel natural and informative. The reader should learn something just from
seeing the questions — they should hint at what the book covers.""",
        system="You are designing an onboarding quiz for a reading app. Generate questions that are genuinely useful for assessing background knowledge. Each question should be specific and meaningful, not generic. Respond with valid JSON only.",
        max_tokens=2000,
    )

    questions = []
    for i, item in enumerate(result[:max_questions]):
        questions.append(CalibrationQuestion(
            id=f"q_{i}",
            concept_name=item["concept_name"],
            question=item["question"],
            options=FAMILIARITY_LEVELS,
            context_hint=item.get("context_hint", ""),
        ))

    return questions


def build_reader_profile(
    answers: dict[str, int],
    questions: list[CalibrationQuestion],
) -> dict[str, int]:
    """Convert calibration answers into a reader profile.

    Returns a dict mapping concept name to familiarity level (0-3).
    """
    profile: dict[str, int] = {}
    for question in questions:
        level = answers.get(question.id, 0)
        profile[question.concept_name] = level
    return profile
