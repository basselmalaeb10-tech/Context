"""Generate calibration questions from extracted concepts.

Calibration questions assess the reader's familiarity with the most
important concepts in the document, so the explanation engine can
tailor its output.
"""

from dataclasses import dataclass
from .concept_engine import Concept


@dataclass
class CalibrationQuestion:
    id: str
    concept_name: str
    question: str
    options: list[str]


# Familiarity levels returned by the user
FAMILIARITY_LEVELS = [
    "Never heard of it",
    "Heard of it, but can't explain it",
    "I have a basic understanding",
    "I know it well",
]


def generate_questions(
    concepts: list[Concept],
    max_questions: int = 7,
) -> list[CalibrationQuestion]:
    """Generate familiarity-check questions for the top concepts.

    Selects the most important concepts and asks the reader how
    familiar they are. This is intentionally simple: a quick
    self-assessment, not a quiz.
    """
    # Sort by importance descending, take top N
    sorted_concepts = sorted(concepts, key=lambda c: c.importance, reverse=True)
    selected = sorted_concepts[:max_questions]

    questions: list[CalibrationQuestion] = []
    for i, concept in enumerate(selected):
        questions.append(CalibrationQuestion(
            id=f"q_{i}",
            concept_name=concept.name,
            question=f"How familiar are you with \"{concept.name}\"?",
            options=FAMILIARITY_LEVELS,
        ))

    return questions


def build_reader_profile(
    answers: dict[str, int],
    questions: list[CalibrationQuestion],
) -> dict[str, int]:
    """Convert calibration answers into a reader profile.

    Returns a dict mapping concept name to familiarity level (0-3).
    0 = never heard of it, 3 = knows it well.
    """
    profile: dict[str, int] = {}
    for question in questions:
        level = answers.get(question.id, 0)
        profile[question.concept_name] = level
    return profile
