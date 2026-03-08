"""LLM service layer — wraps Anthropic Claude API.

All LLM calls go through this module so we can swap providers,
add caching, or rate-limit in one place.
"""

import os
import json
import hashlib
from pathlib import Path

# Load .env file if present (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from anthropic import Anthropic

_client: Anthropic | None = None
_CACHE_DIR = Path(__file__).parent.parent / ".llm_cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()  # uses ANTHROPIC_API_KEY env var
    return _client


def _cache_key(prompt: str, system: str) -> str:
    h = hashlib.sha256(f"{system}||{prompt}".encode()).hexdigest()[:16]
    return h


def call_llm(
    prompt: str,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
    temperature: float = 0.3,
    use_cache: bool = True,
) -> str:
    """Call Claude and return the text response.

    Uses a simple disk cache to avoid repeated API calls for
    identical prompts (concept extraction, book metadata, etc).
    """
    if use_cache:
        key = _cache_key(prompt, system)
        cache_path = _CACHE_DIR / f"{key}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text())["response"]

    client = _get_client()
    messages = [{"role": "user", "content": prompt}]

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    text = response.content[0].text

    if use_cache:
        cache_path = _CACHE_DIR / f"{key}.json"
        cache_path.write_text(json.dumps({"response": text}))

    return text


def call_llm_json(
    prompt: str,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
    temperature: float = 0.2,
    use_cache: bool = True,
) -> dict | list:
    """Call Claude and parse the response as JSON.

    The prompt should instruct the model to respond with valid JSON.
    """
    raw = call_llm(prompt, system, model, max_tokens, temperature, use_cache)

    # Extract JSON from markdown code blocks if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
