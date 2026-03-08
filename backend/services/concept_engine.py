"""Concept extraction and internal knowledge dependency graph.

For MVP, this uses keyword-frequency heuristics and a curated set of
domain patterns. The interface is designed so a real LLM can replace the
mock logic without changing the rest of the system.
"""

import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Concept:
    name: str
    domain: str  # e.g. "philosophy", "economics", "general"
    importance: float  # 0.0 to 1.0
    prerequisites: list[str] = field(default_factory=list)
    description: str = ""


# Common stop-phrases to filter out of concept candidates
_STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was",
    "were", "been", "being", "have", "has", "had", "not", "but", "what",
    "which", "their", "they", "will", "would", "could", "should", "can",
    "may", "might", "about", "into", "through", "between", "each", "also",
    "more", "some", "such", "than", "other", "its", "only", "these",
    "those", "then", "them", "very", "just", "because", "how", "all",
    "when", "where", "who", "whom", "why", "before", "after", "above",
    "below", "both", "same", "own", "most", "one", "two", "three",
}

# Domain keyword hints — used to tag extracted concepts
_DOMAIN_HINTS: dict[str, list[str]] = {
    "philosophy": [
        "epistemology", "ontology", "metaphysics", "ethics", "dialectic",
        "phenomenology", "existentialism", "stoicism", "rationalism",
        "empiricism", "hermeneutics", "teleology", "deontological",
        "virtue", "categorical imperative", "nihilism", "pragmatism",
    ],
    "economics": [
        "supply", "demand", "equilibrium", "inflation", "monetary",
        "fiscal", "gdp", "capital", "labor", "market", "trade",
        "keynesian", "neoclassical", "marginal", "utility", "scarcity",
    ],
    "political theory": [
        "sovereignty", "democracy", "republic", "liberalism",
        "conservatism", "authoritarianism", "social contract",
        "legitimacy", "power", "governance", "state", "constitution",
    ],
    "strategy": [
        "deterrence", "escalation", "alliance", "asymmetric",
        "realism", "balance of power", "geopolitics", "diplomacy",
    ],
}

# Simple prerequisite mapping for well-known concepts
_PREREQUISITE_MAP: dict[str, list[str]] = {
    "categorical imperative": ["ethics", "Immanuel Kant", "deontological ethics"],
    "dialectic": ["thesis", "antithesis", "synthesis"],
    "social contract": ["state of nature", "sovereignty"],
    "supply and demand": ["scarcity", "market", "price"],
    "game theory": ["rational choice", "Nash equilibrium"],
    "phenomenology": ["consciousness", "intentionality", "Edmund Husserl"],
    "existentialism": ["phenomenology", "freedom", "authenticity"],
    "keynesian economics": ["aggregate demand", "fiscal policy", "multiplier effect"],
    "utilitarianism": ["consequentialism", "Jeremy Bentham", "John Stuart Mill"],
    "virtue ethics": ["Aristotle", "eudaimonia", "character"],
}


def _detect_domain(text: str) -> str:
    """Guess the dominant domain of the document."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_HINTS.items():
        scores[domain] = sum(text_lower.count(kw) for kw in keywords)
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=lambda d: scores[d])


def _extract_capitalized_phrases(text: str) -> list[str]:
    """Extract multi-word capitalized phrases (potential proper nouns / concepts)."""
    # Match sequences of capitalized words (2+ words)
    pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    return re.findall(pattern, text)


def extract_concepts(full_text: str) -> list[Concept]:
    """Extract key concepts from document text.

    This is the main entry point. For MVP it uses frequency analysis
    and pattern matching. Replace internals with LLM calls for production.
    """
    domain = _detect_domain(full_text)

    # Collect candidate concept names
    candidates: Counter[str] = Counter()

    # 1. Capitalized phrases (proper nouns, named concepts)
    for phrase in _extract_capitalized_phrases(full_text):
        if len(phrase) > 3 and phrase.lower() not in _STOP_WORDS:
            candidates[phrase] += 1

    # 2. Domain keywords found in text
    text_lower = full_text.lower()
    for kw_list in _DOMAIN_HINTS.values():
        for kw in kw_list:
            count = text_lower.count(kw)
            if count > 0:
                candidates[kw.title()] += count

    # 3. Frequent significant words (single words, 6+ chars, not stop words)
    words = re.findall(r"\b[a-z]{6,}\b", text_lower)
    word_freq = Counter(words)
    for word, count in word_freq.most_common(30):
        if word not in _STOP_WORDS and count >= 3:
            candidates[word.title()] += count

    # Rank and limit
    top = candidates.most_common(25)
    if not top:
        return []

    max_count = top[0][1]
    concepts: list[Concept] = []
    for name, count in top:
        importance = round(count / max_count, 2)
        prereqs = _PREREQUISITE_MAP.get(name.lower(), [])
        concepts.append(Concept(
            name=name,
            domain=domain,
            importance=importance,
            prerequisites=prereqs,
        ))

    return concepts


def build_dependency_graph(concepts: list[Concept]) -> dict:
    """Build a simple adjacency-list dependency graph from concepts.

    Returns a dict mapping concept name -> list of prerequisite names.
    This is the internal knowledge graph used by the explanation engine.
    """
    graph: dict[str, list[str]] = {}
    concept_names = {c.name.lower() for c in concepts}

    for concept in concepts:
        deps = []
        for prereq in concept.prerequisites:
            deps.append(prereq)
            # If the prerequisite is also an extracted concept, link them
            if prereq.lower() in concept_names:
                deps.append(prereq)
        graph[concept.name] = list(set(deps))

    return graph
