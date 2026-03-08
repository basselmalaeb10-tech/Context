"""LLM service layer — supports Anthropic Claude and OpenAI ChatGPT.

Automatically uses whichever API key is available:
- ANTHROPIC_API_KEY → Claude
- OPENAI_API_KEY → ChatGPT

If both are set, defaults to Anthropic (set LLM_PROVIDER=openai to override).
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

_CACHE_DIR = Path(__file__).parent.parent / ".llm_cache"
_CACHE_DIR.mkdir(exist_ok=True)

# --- Provider detection ---

def _get_provider() -> str:
    """Determine which LLM provider to use."""
    explicit = os.environ.get("LLM_PROVIDER", "").lower()
    if explicit in ("openai", "chatgpt"):
        return "openai"
    if explicit in ("anthropic", "claude"):
        return "anthropic"
    # Auto-detect from available keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise RuntimeError(
        "No LLM API key found. Set either ANTHROPIC_API_KEY or OPENAI_API_KEY "
        "in your environment or .env file."
    )


# Default model per provider
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


# --- Anthropic ---

_anthropic_client = None

def _call_anthropic(
    prompt: str, system: str, model: str, max_tokens: int, temperature: float,
) -> str:
    global _anthropic_client
    from anthropic import Anthropic

    if _anthropic_client is None:
        _anthropic_client = Anthropic()

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = _anthropic_client.messages.create(**kwargs)
    return response.content[0].text


# --- OpenAI ---

_openai_client = None

def _call_openai(
    prompt: str, system: str, model: str, max_tokens: int, temperature: float,
) -> str:
    global _openai_client
    from openai import OpenAI

    if _openai_client is None:
        _openai_client = OpenAI()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = _openai_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


# --- Public API ---

def _cache_key(prompt: str, system: str) -> str:
    h = hashlib.sha256(f"{system}||{prompt}".encode()).hexdigest()[:16]
    return h


def call_llm(
    prompt: str,
    system: str = "",
    model: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.3,
    use_cache: bool = True,
) -> str:
    """Call the configured LLM and return the text response.

    Uses a simple disk cache to avoid repeated API calls for
    identical prompts (concept extraction, book metadata, etc).
    """
    if use_cache:
        key = _cache_key(prompt, system)
        cache_path = _CACHE_DIR / f"{key}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text())["response"]

    provider = _get_provider()
    if not model:
        model = DEFAULT_MODELS[provider]

    if provider == "anthropic":
        text = _call_anthropic(prompt, system, model, max_tokens, temperature)
    else:
        text = _call_openai(prompt, system, model, max_tokens, temperature)

    if use_cache:
        cache_path = _CACHE_DIR / f"{key}.json"
        cache_path.write_text(json.dumps({"response": text}))

    return text


def call_llm_json(
    prompt: str,
    system: str = "",
    model: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.2,
    use_cache: bool = True,
) -> dict | list:
    """Call the LLM and parse the response as JSON."""
    raw = call_llm(prompt, system, model, max_tokens, temperature, use_cache)

    # Extract JSON from markdown code blocks if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
