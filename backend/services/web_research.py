"""Web research service — searches the web for book-related context.

Uses DuckDuckGo (no API key needed) to find explanations, summaries,
and analyses from sites like SparkNotes, Stanford Encyclopedia of
Philosophy, book review sites, etc.

Results are cached to disk to avoid repeated searches.
"""

import json
import hashlib
import re
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent / ".web_cache"
_CACHE_DIR.mkdir(exist_ok=True)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
})

# Priority domains for book/philosophy content
BOOK_DOMAINS = [
    "sparknotes.com",
    "litcharts.com",
    "cliffsnotes.com",
    "gradesaver.com",
    "shmoop.com",
    "plato.stanford.edu",       # Stanford Encyclopedia of Philosophy
    "iep.utm.edu",              # Internet Encyclopedia of Philosophy
    "gutenberg.org",
    "jstor.org",
    "en.wikipedia.org",
    "goodreads.com",
    "bookrags.com",
    "coursehero.com",
    "enotes.com",
    "philpapers.org",
    "britannica.com",
]


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str
    source: str  # domain name


@dataclass
class ResearchResult:
    query: str
    results: list[WebResult]
    summary: str  # combined extracted content


def _cache_key(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def _get_cached(query: str) -> ResearchResult | None:
    key = _cache_key(query)
    path = _CACHE_DIR / f"{key}.json"
    if path.exists():
        data = json.loads(path.read_text())
        results = [WebResult(**r) for r in data["results"]]
        return ResearchResult(
            query=data["query"],
            results=results,
            summary=data["summary"],
        )
    return None


def _save_cache(result: ResearchResult) -> None:
    key = _cache_key(result.query)
    path = _CACHE_DIR / f"{key}.json"
    data = {
        "query": result.query,
        "results": [asdict(r) for r in result.results],
        "summary": result.summary,
    }
    path.write_text(json.dumps(data, ensure_ascii=False))


def _search_duckduckgo(query: str, max_results: int = 8) -> list[WebResult]:
    """Search DuckDuckGo HTML version and parse results."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = _SESSION.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for item in soup.select(".result")[:max_results]:
        title_el = item.select_one(".result__a")
        snippet_el = item.select_one(".result__snippet")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")

        # DuckDuckGo wraps URLs in a redirect — extract the actual URL
        if "uddg=" in str(href):
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(str(href))
            actual = parse_qs(parsed.query).get("uddg", [""])[0]
            href = actual

        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        source = _extract_domain(str(href))

        results.append(WebResult(
            title=title,
            url=str(href),
            snippet=snippet,
            source=source,
        ))

    return results


def _extract_domain(url: str) -> str:
    """Extract readable domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except Exception:
        return url


def _fetch_page_content(url: str, max_chars: int = 3000) -> str:
    """Fetch and extract main text content from a URL."""
    try:
        resp = _SESSION.get(url, timeout=8)
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove scripts, styles, navs, footers
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Try to find main content area
    main = (
        soup.select_one("article")
        or soup.select_one("main")
        or soup.select_one(".content")
        or soup.select_one("#content")
        or soup.select_one(".entry-content")
        or soup.select_one(".post-content")
        or soup.body
    )
    if not main:
        return ""

    text = main.get_text(separator="\n", strip=True)
    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


def _build_search_queries(
    text: str,
    book_title: str = "",
    book_author: str = "",
    book_domain: str = "",
) -> list[str]:
    """Build targeted search queries for the selected text."""
    queries = []

    # Clean up selected text for search
    search_text = text[:120].strip()

    # Main query: book-specific explanation
    if book_title:
        queries.append(f'"{book_title}" {search_text} explanation')
        queries.append(f'{book_title} {book_author} summary analysis')
    else:
        queries.append(f"{search_text} explanation meaning")

    # Domain-specific queries
    if book_domain:
        domain_queries = {
            "philosophy": f"{search_text} philosophy explanation Stanford Encyclopedia",
            "literature": f"{search_text} literary analysis SparkNotes",
            "psychology": f"{search_text} psychology concept explained",
            "economics": f"{search_text} economics concept explained",
            "history": f"{search_text} historical context explained",
            "science": f"{search_text} science concept explained simply",
            "politics": f"{search_text} political theory explained",
            "sociology": f"{search_text} sociology concept explained",
        }
        for key, q in domain_queries.items():
            if key in book_domain.lower():
                queries.append(q)
                break
        else:
            queries.append(f"{search_text} {book_domain} explained")

    return queries[:3]  # Limit to 3 queries


def research_topic(
    text: str,
    book_title: str = "",
    book_author: str = "",
    book_domain: str = "",
    max_results: int = 6,
) -> ResearchResult:
    """Search the web for explanations related to selected text.

    Returns search results with snippets and extracted content.
    """
    # Build a cache key from all inputs
    cache_query = f"{text}|{book_title}|{book_domain}"
    cached = _get_cached(cache_query)
    if cached:
        return cached

    queries = _build_search_queries(text, book_title, book_author, book_domain)

    all_results: list[WebResult] = []
    seen_urls: set[str] = set()

    for query in queries:
        results = _search_duckduckgo(query, max_results=6)
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append(r)

    # Prioritize results from known book/education sites
    def _score(r: WebResult) -> int:
        for i, domain in enumerate(BOOK_DOMAINS):
            if domain in r.source:
                return i
        return 100

    all_results.sort(key=_score)
    top_results = all_results[:max_results]

    # Fetch full content from top 2-3 results for summary
    content_parts = []
    for r in top_results[:3]:
        content = _fetch_page_content(r.url)
        if content:
            content_parts.append(f"[{r.source}] {content[:1500]}")

    summary = "\n\n---\n\n".join(content_parts) if content_parts else ""

    result = ResearchResult(
        query=cache_query,
        results=top_results,
        summary=summary,
    )
    _save_cache(result)
    return result


def research_book_overview(
    book_title: str,
    book_author: str = "",
    book_domain: str = "",
) -> ResearchResult:
    """Search for general book summaries, reviews, and analysis."""
    cache_query = f"overview|{book_title}|{book_author}"
    cached = _get_cached(cache_query)
    if cached:
        return cached

    queries = [
        f'"{book_title}" {book_author} summary analysis',
        f'"{book_title}" SparkNotes OR CliffsNotes OR summary',
        f'"{book_title}" book review key themes',
    ]

    all_results: list[WebResult] = []
    seen_urls: set[str] = set()

    for query in queries:
        results = _search_duckduckgo(query, max_results=6)
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append(r)

    def _score(r: WebResult) -> int:
        for i, domain in enumerate(BOOK_DOMAINS):
            if domain in r.source:
                return i
        return 100

    all_results.sort(key=_score)
    top_results = all_results[:6]

    content_parts = []
    for r in top_results[:3]:
        content = _fetch_page_content(r.url)
        if content:
            content_parts.append(f"[{r.source}] {content[:1500]}")

    summary = "\n\n---\n\n".join(content_parts) if content_parts else ""

    result = ResearchResult(
        query=cache_query,
        results=top_results,
        summary=summary,
    )
    _save_cache(result)
    return result
