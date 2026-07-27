# backend/apis/Onboarding/enrichment.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import get_conn

from urllib.parse import parse_qsl, urlencode, urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup

import asyncio
import httpx
import json
import os
import re
import sys

# On Windows, the default asyncio event loop policy doesn't support subprocess
# management the way Playwright needs it to — switch to the Proactor policy.
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

# Playwright is only usable off Windows (see policy note above) and can be
# disabled entirely via the ENABLE_PLAYWRIGHT env var (defaults to enabled).
PLAYWRIGHT_ENABLED = (
    sys.platform != "win32"
    and
    os.getenv("ENABLE_PLAYWRIGHT", "true").lower() in ("1", "true", "yes")
)

# Router mounted under /onboarding — groups the enrichment + profile-save endpoints
router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"]
)

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

MAX_PAGES   = 2     # reduced for faster responses
MAX_DEPTH   = 1     # keep shallow by default
MAX_ITEMS   = 50
MAX_WORDS   = 4

# Concurrency caps — tune to taste
HTTPX_CONCURRENCY       = 5   # parallel httpx fetches
PLAYWRIGHT_CONCURRENCY  = 2   # parallel Playwright tabs (CPU-heavy)

# httpx: short timeout; Playwright reserved for JS-heavy pages
HTTPX_TIMEOUT       = 6    # shorter HTTP timeout to avoid long waits
PLAYWRIGHT_TIMEOUT  = 8000  # ms — reduce Playwright page navigation timeout
NETWORK_IDLE_TIMEOUT = 2000  # ms — smaller network idle wait

# Module-level Playwright reuse state.
# A single browser instance is launched lazily and reused across requests
# (rather than launching a new browser per page/request) to save startup cost.
_playwright_instance = None
_playwright_browser = None
_playwright_lock = asyncio.Lock()


# HTML container/text tags we're willing to scan for business items (products/services)
ALLOWED_CONTAINERS = ("section", "article", "div", "header", "footer", "nav")
ALLOWED_TEXT_TAGS  = ("h2", "h3", "h4", "h5", "h6", "li", "a", "button")

# File extensions that indicate a link points to a static asset, not a page —
# these are skipped during link discovery/crawling.
STATIC_EXTENSIONS = (
    ".7z", ".avi", ".css", ".csv", ".doc", ".docx", ".gif", ".ico",
    ".jpeg", ".jpg", ".js", ".json", ".mov", ".mp3", ".mp4", ".pdf",
    ".png", ".ppt", ".pptx", ".rar", ".rss", ".svg", ".txt", ".webp",
    ".xls", ".xlsx", ".xml", ".zip"
)

# ─────────────────────────────────────────
# STRICT TERMS  (unchanged)
# ─────────────────────────────────────────

# Vocabulary that signals a piece of text is describing a *service* offering
SERVICE_TERMS = {
    "ai", "analytics", "automation", "cloud", "consulting", "cybersecurity",
    "data", "digital", "engineering", "experience", "governance",
    "hybrid", "intelligence", "integration", "management", "migration",
    "modernization", "operations", "platform", "process", "security",
    "service", "services", "solution", "solutions", "strategy", "supply", "technology",
    "transformation",
    "ai-boosted", "prototyping", "ai-enhanced", "quality", "ai-led", "insights",
    "ai-powered", "engagement", "bespoke", "customer", "collaboration",
    "quality engineering", "managed services", "talent scaling", "product engineering",
    "product evolution", "platform modernization", "data transformation",
    "data visualization", "cio advisory", "adaptive architectures",
    "change management", "seamless integration", "always-on stability",
    "responsive support", "smarter economics", "secure operations",
    "data harvesting", "infra setup", "market entry", "digital experiences",
    "risk management", "fraud management", "data-driven", "consulting",
    "deployment", "implementation"
}

# Vocabulary that signals a piece of text is describing a *product* (hardware
# category words plus known product/model names)
PRODUCT_TERMS = {
    "accessories", "accessory",
    "book", "camera", "desktop", "device", "headphones", "headset",
    "laptop", "monitor", "notebook", "phone", "printer", "router",
    "scanner", "server", "series", "speaker", "storage", "switch",
    "tablet", "watch", "workstation",
    "xts ai forge", "agentic ai", "rapid", "sentinel", "meridian",
    "prism", "cadence", "kalliope", "engage", "lumen",
    "forge", "ai forge"
}

# Broader hardware-family words used as a secondary signal for product detection
PRODUCT_FAMILY_TERMS = {
    "computer", "computers", "desktop", "desktops", "display", "displays",
    "laptop", "laptops", "monitor", "monitors", "notebook", "notebooks",
    "pc", "pcs", "server", "servers", "tablet", "tablets",
    "workstation", "workstations",
}

# Extra words (beyond SERVICE_TERMS) that indicate a *link* points to a services page
SERVICE_LINK_TERMS = SERVICE_TERMS | {
    "capabilities", "expertise", "industries", "industry", "offering",
    "offerings", "services", "solutions", "verticals"
}

# Extra words (beyond PRODUCT_TERMS) that indicate a *link* points to a products page
PRODUCT_LINK_TERMS = PRODUCT_TERMS | {
    "accessories", "catalog", "collection", "collections", "product",
    "products", "shop", "store"
}

# Text prefixes that mark marketing/CTA copy rather than an actual product/service name
BAD_PREFIXES = (
    "accelerate", "boost", "build a", "contact", "explore", "discover",
    "find", "get", "learn", "read", "reinvent", "see", "shop", "start",
    "transform your", "view", "watch", "follow", "what", "why",
)

# Known third-party partner/vendor names — never treated as the company's own product/service
PARTNERS = {
    "amazon web services", "aws", "microsoft", "oracle", "sap",
    "adobe", "salesforce", "cloudflare", "google", "intel", "amd", "nvidia",
}

# Generic navigation/footer/social words to always discard as noise
NOISE_WORDS = {
    "home", "about", "contact", "careers", "privacy", "terms", "cookie",
    "cookies", "blog", "news", "support", "resources", "products",
    "services", "solutions", "offerings", "faq", "menu", "search",
    "deals", "offers", "login", "register", "subscribe", "footer",
    "header", "linkedin", "facebook", "instagram", "youtube", "twitter",
    "x", "tiktok", "kartik anand", "rajesh kurup",
}

# Generic marketing phrases to always discard as noise
NOISE_PHRASES = {
    "our services", "our solutions", "our products", "all products",
    "for business", "for home", "learn more", "read more", "view all",
    "see all", "discover more", "contact us", "get started", "shop now",
    "join us", "best performance ever", "case study", "click here",
    "customers also viewed", "featured products", "follow us",
    "reinvent with ai", "what's trending","1-800-MY-APPLE",
}

# Container class/id keywords that mark a section as likely holding products/services
TARGET_CONTAINERS = (
    "product", "products", "service", "services", "solution", "solutions",
    "offering", "offerings", "portfolio", "catalog", "collection", "card", "grid",
)

# Container class/id keywords that mark a section as chrome/noise to skip entirely
SKIP_CONTAINERS = (
    "cookie", "newsletter", "social", "popup", "banner",
    "breadcrumb", "legal", "modal",
)

# URL path segments that mark a page as not worth crawling (about, legal, blog, etc.)
SKIP_PATH_TERMS = {
    "about", "accessibility", "blog", "career", "careers", "case-study",
    "case-studies", "cookie", "events", "investor", "legal", "login",
    "news", "press", "privacy", "resources", "signin", "signup", "social",
    "support", "terms", "whitepaper"
}

# Generic URL path segments to strip out before treating a slug as an entity name
URL_ENTITY_STOPWORDS = {
    "a", "all", "and", "au", "ca", "cart", "category", "compare", "deals",
    "en", "for", "fr", "home", "in", "lp", "new", "offers", "page", "pages",
    "p", "products", "shop", "store", "uk", "us", "view", "with"
}

# ─────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────

class EnrichRequest(BaseModel):
    """Payload for POST /onboarding/enrich — the company website to scrape."""
    website_url: str
    user_id: int
    company_type: str = ""


class SaveProfileRequest(BaseModel):
    """Payload for POST /onboarding/save-profile — the full company profile to persist."""
    user_id: int
    company_name: str
    industry: str
    linkedin_url: str
    company_size: str
    headquarters: str
    type: str
    company_type: str
    founded: str
    revenue_size: str
    specialties: str
    website: str
    brands: str
    services: str = ""

# ─────────────────────────────────────────
# HELPERS  (unchanged logic, same code)
# ─────────────────────────────────────────

def normalize_url(url: str) -> str:
    """Ensure the URL has a scheme, validate it has a host, then canonicalize it."""
    url = url.strip()
    if not url.startswith("http"):
        # Assume https if no scheme was given
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid website URL")
    return canonicalize_url(url)


def canonicalize_url(url: str) -> str:
    """
    Normalize a URL into a stable, de-duplicatable form:
    strips tracking query params (utm_*, fbclid, gclid, msclkid), drops the
    fragment, and removes any trailing slash from the path.
    """
    parsed = urlparse(urljoin(url, url))
    # Keep only query params that aren't known tracking parameters
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "fbclid", "gclid", "msclkid"))
    ]
    clean = parsed._replace(
        fragment="",
        query=urlencode(query_pairs, doseq=True),
        path=parsed.path.rstrip("/") or "/"
    )
    return urlunparse(clean)


def clean_text(text: str) -> str:
    """Collapse whitespace/non-breaking spaces and strip common separator characters."""
    text = text or ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -|•:\n\t\r,.;")


def titleize_slug(slug: str) -> str:
    """
    Convert a URL path slug (e.g. "cloud-migration-services.html") into a
    readable title (e.g. "Cloud Migration Services"), dropping stopwords and
    rejecting slugs that are empty or too long after cleanup.
    """
    # Drop trailing file extensions and normalize separators to hyphens
    slug = re.sub(r"\.(html?|aspx?|php)$", "", slug.lower())
    slug = re.sub(r"[_+]+", "-", slug)

    # Split on hyphens and drop generic stopwords (e.g. "shop", "us", "en")
    parts = [
        part for part in slug.split("-")
        if part and part not in URL_ENTITY_STOPWORDS
    ]
    if not parts or len(parts) > MAX_WORDS:
        # Nothing left, or too many words to be a clean entity name
        return ""

    # Build each word: short all-alpha words (e.g. "ai") are upper-cased as
    # acronyms, everything else is capitalized normally
    titled_words = []
    for word in parts:
        if len(word) <= 3 and word.isalpha():
            titled_words.append(word.upper())
        else:
            titled_words.append(word.capitalize())
    return " ".join(titled_words)


def candidates_from_href(href: str, company_kind: str):
    """
    Derive candidate product/service names directly from a link's URL path
    (useful when the anchor text itself is generic, e.g. "Learn more").
    Checks up to the last 4 path segments, most specific first.
    """
    parsed = urlparse(href)
    raw_path_parts = [
        part.lower() for part in parsed.path.split("/") if part
    ]
    # Bail out entirely if this URL's path contains a "skip" segment (about, blog, etc.)
    if set(raw_path_parts) & SKIP_PATH_TERMS:
        return []

    # Drop generic stopword segments before considering the remaining parts
    path_parts = [
        part for part in raw_path_parts
        if part and part.lower() not in URL_ENTITY_STOPWORDS
    ]

    candidates = []
    # Look at the last 4 segments, checking from most specific (last) to least
    for part in reversed(path_parts[-4:]):
        candidate = titleize_slug(part)
        if not candidate:
            continue
        lower = candidate.lower()
        if company_kind == "service":
            # Only keep this segment if it matches a known service term
            if any(re.search(rf"\b{re.escape(term)}\b", lower) for term in SERVICE_TERMS):
                candidates.append(candidate)
        else:
            # Only keep this segment if it matches a product term/family term,
            # or contains a digit (e.g. a model number)
            if (
                any(re.search(rf"\b{re.escape(term)}\b", lower) for term in PRODUCT_TERMS)
                or any(re.search(rf"\b{re.escape(term)}\b", lower) for term in PRODUCT_FAMILY_TERMS)
                or re.search(r"\d", candidate)
            ):
                candidates.append(candidate)
    return candidates


def is_noise_container(tag) -> bool:
    """True if this tag's class/id marks it as chrome/noise (cookie banner, social, etc.)."""
    content = (
        " ".join(tag.get("class") or []) + " " + (tag.get("id") or "")
    ).lower()
    return any(x in content for x in SKIP_CONTAINERS)


def is_target_container(tag) -> bool:
    """True if this tag's class/id marks it as a likely products/services section."""
    content = (
        " ".join(tag.get("class") or []) + " " + (tag.get("id") or "")
    ).lower()
    return any(x in content for x in TARGET_CONTAINERS)


def container_context(tag) -> str:
    """
    Infer whether a container is more likely about "service" or "product"
    content, based on its class/id plus the text of any headings inside it.
    Returns "" if neither is indicated.
    """
    descriptor = (
        " ".join(tag.get("class") or []) + " " + (tag.get("id") or "")
    ).lower()
    heading_text = " ".join(
        clean_text(heading.get_text(" ", strip=True)).lower()
        for heading in tag.find_all(["h1", "h2", "h3", "h4"], recursive=True)
    )
    content = f"{descriptor} {heading_text}"
    if re.search(r"\b(service|services|solution|solutions|offering|offerings)\b", content):
        return "service"
    if re.search(r"\b(product|products|catalog|collection|collections|portfolio)\b", content):
        return "product"
    return ""


def inherited_container_context(tag, fallback: str = "") -> str:
    """Walk up the ancestor chain looking for the nearest container with a clear service/product context."""
    current = tag
    while current:
        context = container_context(current)
        if context:
            return context
        current = current.find_parent(ALLOWED_CONTAINERS)
    return fallback


def is_valid_candidate(text: str) -> bool:
    """
    General-purpose gate applied to any candidate string before it's even
    considered as a product/service name — filters out noise, CTAs, URLs,
    overly long/short text, and generic sentence fragments.
    """
    text = clean_text(text)
    if not text:
        return False
    # Reject text that's clearly too short or too long to be an entity name
    if len(text) < 2 or len(text) > 70:
        return False
    lower = text.lower()
    # Reject known noise words and partner/vendor names
    if lower in NOISE_WORDS or lower in PARTNERS:
        return False
    # Reject known marketing/noise phrases
    if any(phrase in lower for phrase in NOISE_PHRASES):
        return False
    # Reject text that starts like a call-to-action ("Get started", "Learn more", etc.)
    if lower.startswith(BAD_PREFIXES):
        return False
    # Reject full sentences/questions (contains punctuation marks)
    if any(mark in text for mark in ("?", "!", ".")):
        return False
    # Reject anything that looks like a URL or email/handle
    if re.search(r"(https?://|www\.|@)", text, flags=re.I):
        return False
    # Reject anything containing a path separator
    if "/" in text:
        return False
    words = [w for w in re.findall(r"[a-z0-9]+", lower)]
    if not words:
        return False
    # Reject overly long phrases (more than MAX_WORDS words)
    if len(words) > MAX_WORDS:
        return False
    # Reject longer phrases that read like a sentence fragment (contain connector words)
    if len(words) > 3 and re.search(
        r"\b(the|your|our|we|you|with|for|that|from|into|through)\b", lower
    ):
        return False
    # Reject bare numbers/percentages (e.g. "50%")
    if re.search(r"^\d+%?$", text):
        return False
    return True


def is_meaningful_html(html: str) -> bool:
    """
    Quick heuristic: avoid booting Playwright for already-rich pages.
    Uses a lightweight text-length check first before parsing.
    """
    if not html or len(html) < 2000:       # ← fast pre-check, avoids BeautifulSoup cost
        return False
    soup = BeautifulSoup(html, "html.parser")
    body_text = clean_text(soup.get_text(" ", strip=True))
    if len(body_text) < 500:
        # Not enough visible text — likely a JS-rendered shell page
        return False
    # Count how many "content-bearing" tags (headings/list items/links) exist
    # inside the main structural containers
    content_tags = len(soup.select(
        "section h2, section h3, section h4, section li, section a, "
        "article h2, article h3, article h4, article li, article a, "
        "div h2, div h3, div h4, div li, div a"
    ))
    return content_tags >= 6

# ─────────────────────────────────────────
# STRICT FILTERS  (unchanged)
# ─────────────────────────────────────────

def is_strict_service(text: str) -> bool:
    """True if text passes general validity checks AND matches a known service term (but isn't just the bare term itself)."""
    text = clean_text(text)
    lower = text.lower()
    if not is_valid_candidate(text):
        return False
    # Reject if the text IS a bare service term (e.g. just "Consulting") rather than a specific offering
    if lower in SERVICE_TERMS:
        return False
    # Require the text to at least contain a service term somewhere
    if not any(re.search(rf"\b{re.escape(term)}\b", lower) for term in SERVICE_TERMS):
        return False
    return True


def is_strict_product(text: str) -> bool:
    """
    True if text passes general validity checks AND looks like a specific
    product/model name — via known product vocabulary, model-number-style
    patterns (e.g. "iPhone 15", "RTX4090"), or CamelCase/acronym styling.
    """
    text = clean_text(text)
    lower = text.lower()
    if not is_valid_candidate(text):
        return False
    # Matches a known product term (e.g. "laptop", "Sentinel")
    if any(re.search(rf"\b{re.escape(term)}\b", lower) for term in PRODUCT_TERMS):
        return True
    # Matches a broader hardware-family term (e.g. "workstation")
    if any(re.search(rf"\b{re.escape(term)}\b", lower) for term in PRODUCT_FAMILY_TERMS):
        return True
    # Looks like "Word123" / "Word 123abc" — a name followed by a model number
    if re.search(r"\b[A-Z][A-Za-z]+ ?\d+[A-Za-z0-9-]*\b", text):
        return True
    # Looks like a short alphanumeric model code, e.g. "RTX4090"
    if re.search(r"\b[A-Z]{1,4}\d{1,4}\b", text):
        return True
    # Looks like CamelCase, e.g. "PowerEdge"
    if re.search(r"\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b", text):
        return True
    # Contains both a digit and an uppercase letter somewhere (mixed alnum styling)
    if any(char.isdigit() for char in text) and re.search(r"[A-Z]", text):
        return True
    # Short (1-3 word) phrases that look like an acronym or a single Title-Cased word
    words = text.split()
    if 1 <= len(words) <= 3 and re.search(r"[A-Z]", text):
        acronym_count     = sum(1 for w in words if re.fullmatch(r"[A-Z0-9]{2,}", w))
        title_word_count  = sum(1 for w in words if re.fullmatch(r"[A-Z][a-zA-Z0-9-]+", w))
        if acronym_count:
            return True
        if len(words) == 1 and title_word_count == 1:
            return True
    return False


def is_contextual_entity(text: str) -> bool:
    """
    Looser check used only when we already know the surrounding container's
    context (product/service): True if the text still passes general validity
    and every word is capitalized/acronym-styled (i.e. looks like a proper noun).
    """
    text = clean_text(text)
    if not is_valid_candidate(text):
        return False
    words = text.split()
    if len(words) == 1:
        return bool(re.fullmatch(r"[A-Z][a-zA-Z0-9-]+|[A-Z0-9]{2,}", text))
    return all(
        re.fullmatch(r"[A-Z][a-zA-Z0-9&-]+|[A-Z0-9]{2,}", word) for word in words
    )

# ─────────────────────────────────────────
# ADD CANDIDATE
# ─────────────────────────────────────────

def add_candidate(results, seen, text, company_kind, context_kind=""):
    """
    Validate and (if it passes) append a candidate string to `results`,
    de-duplicating case-insensitively via the `seen` set.

    A candidate is accepted if it passes the strict service/product check,
    OR if the surrounding container context matches company_kind and the
    text looks like a proper-noun entity (is_contextual_entity).
    """
    text = clean_text(text)
    if not is_valid_candidate(text):
        return
    if company_kind == "service":
        if not is_strict_service(text) and not (
            context_kind == "service" and is_contextual_entity(text)
        ):
            return
    else:
        if not is_strict_product(text) and not (
            context_kind == "product" and is_contextual_entity(text)
        ):
            return
    key = text.lower()
    if key in seen:
        # Already collected this candidate (case-insensitively) — skip duplicate
        return
    seen.add(key)
    results.append(text)

# ─────────────────────────────────────────
# EXTRACTION ENGINE
# ─────────────────────────────────────────

def extract_business_items(soup, company_kind):
    """
    Walk the parsed page looking for product/service names inside relevant
    containers (page-chrome tags, or containers whose class/id/context
    matches company_kind), pulling candidates from both text content and
    link hrefs, up to MAX_ITEMS total.
    """
    found = []
    seen  = set()
    for container in soup.find_all(ALLOWED_CONTAINERS):
        # header/footer/nav are always scanned (page chrome often holds
        # global product/service menus); other containers must look "on-topic"
        is_page_chrome = container.name in ("header", "footer", "nav")
        context_kind   = container_context(container)
        if not is_page_chrome and not is_target_container(container) and context_kind != company_kind:
            continue
        if is_noise_container(container):
            continue
        if container.find_parent(["script", "style"]):
            continue

        for child in container.find_all(ALLOWED_TEXT_TAGS):
            if child.find_parent(["script", "style"]):
                continue
            if is_noise_container(child):
                continue
            # Determine the best-known context (service/product) for this specific child,
            # inheriting from the nearest ancestor container if the child's own container is unclear
            nearest_container = child.find_parent(ALLOWED_CONTAINERS)
            local_context_kind = inherited_container_context(nearest_container, context_kind)

            # Try the visible text of this element as a candidate
            add_candidate(found, seen, child.get_text(" ", strip=True), company_kind, local_context_kind)

            # If it's a link, also try candidates derived from its URL path
            if child.name == "a" and child.get("href"):
                for candidate in candidates_from_href(child.get("href"), company_kind):
                    add_candidate(found, seen, candidate, company_kind, local_context_kind)

            if len(found) >= MAX_ITEMS:
                break
        if len(found) >= MAX_ITEMS:
            break
    return found[:MAX_ITEMS]

# ─────────────────────────────────────────
# DISCOVER LINKS
# ─────────────────────────────────────────

def is_valid_link(url, domain):
    """
    True if the link is same-domain, uses http(s), doesn't point to a static
    asset file, doesn't touch a "skip" path segment, and isn't excessively deep.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc and normalize_host(parsed.netloc) != normalize_host(domain):
        # External link — not part of this crawl
        return False
    path = parsed.path.lower()
    if any(path.endswith(x) for x in STATIC_EXTENSIONS):
        # Points to a file (image, doc, etc.), not a crawlable page
        return False
    parts = {part for part in path.strip("/").split("/") if part}
    if parts & SKIP_PATH_TERMS:
        # Path touches a known "skip" section (about, blog, legal, etc.)
        return False
    if path.count("/") > 6:
        # Too deep to be worth following
        return False
    return True


def normalize_host(host: str) -> str:
    """Lowercase a hostname and strip a leading 'www.' so domain comparisons ignore it."""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def link_relevance(url: str, text: str, company_kind: str) -> int:
    """
    Score a link's relevance to company_kind by counting how many
    service/product-related terms appear in its path or anchor text.
    Links that touch a "skip" path term are heavily penalized.
    """
    terms    = SERVICE_LINK_TERMS if company_kind == "service" else PRODUCT_LINK_TERMS
    haystack = " ".join([
        urlparse(url).path.lower().replace("-", " "),
        clean_text(text).lower()
    ])
    # +3 points for every relevant term found in the URL path or link text
    score = sum(3 for term in terms if re.search(rf"\b{re.escape(term)}\b", haystack))
    # Heavy penalty if the link touches a known "skip" section
    if any(term in haystack for term in SKIP_PATH_TERMS):
        score -= 10
    return score


def discover_links(soup, base_url, company_kind):
    """
    Scan all anchor tags on the page, keep only same-domain/valid/relevant
    links, and return up to MAX_PAGES of them ranked by relevance score
    (highest first).
    """
    domain = urlparse(base_url).netloc
    found  = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            # Skip in-page anchors, mail/phone links, and JS pseudo-links
            continue
        full = canonicalize_url(urljoin(base_url, href))
        if not is_valid_link(full, domain):
            continue
        text  = clean_text(a.get_text(" ", strip=True))
        lower = text.lower()
        if lower in NOISE_WORDS:
            continue
        score = link_relevance(full, text, company_kind)
        if score <= 0:
            # Not relevant enough to bother crawling
            continue
        # Keep the highest score seen for this URL (it may appear as multiple links)
        found[full] = max(score, found.get(full, 0))
        if len(found) >= MAX_PAGES:
            break
    # Rank by score descending and return only the URLs, capped at MAX_PAGES
    return [
        url for url, _ in sorted(found.items(), key=lambda item: item[1], reverse=True)
    ][:MAX_PAGES]

# ─────────────────────────────────────────
# HTTPX FETCH  (shared client — no re-handshake per page)
# ─────────────────────────────────────────

# Browser-like headers so requests aren't trivially blocked as bot traffic
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language":  "en-US,en;q=0.9",
    "Accept-Encoding":  "gzip, deflate, br",
    "Connection":       "keep-alive",
    "Referer":          "https://www.google.com/",
    "Sec-Fetch-Dest":   "document",
    "Sec-Fetch-Mode":   "navigate",
    "Sec-Fetch-Site":   "same-origin",
    "Sec-Fetch-User":   "?1",
}


async def fetch_html_batch(urls: list[str]) -> dict[str, str]:
    """
    Fetch all URLs concurrently with a single shared httpx client.
    Returns {url: html_or_empty_string}.
    """
    # Cap how many fetches run in parallel at once
    sem = asyncio.Semaphore(HTTPX_CONCURRENCY)

    async def _fetch_one(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
        async with sem:
            try:
                resp = await client.get(url)
                ct   = resp.headers.get("content-type", "").lower()
                if resp.status_code < 400 and "text/html" in ct:
                    return url, resp.text
            except Exception:
                # Network error, timeout, etc. — treated as an empty result below
                pass
            return url, ""

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=HTTPX_TIMEOUT,
        verify=False,
        headers=_HEADERS,
    ) as client:
        # Kick off all fetches at once; the semaphore inside _fetch_one throttles them
        results = await asyncio.gather(*[_fetch_one(client, u) for u in urls])

    return dict(results)


# kept for single-URL backward-compat (used only by playwright fallback path)
async def fetch_html(url: str) -> str:
    """Fetch a single URL via the batch fetcher and return its HTML (or "" on failure)."""
    result = await fetch_html_batch([url])
    return result.get(url, "")

# ─────────────────────────────────────────
# PLAYWRIGHT FETCH  (one browser, N pages in parallel)
# ─────────────────────────────────────────

async def playwright_fetch_batch(urls: list[str]) -> dict[str, str]:
    """
    Launch one browser, open up to PLAYWRIGHT_CONCURRENCY tabs in parallel.
    Much cheaper than launching a new browser per URL.
    """
    if not PLAYWRIGHT_ENABLED or not urls:
        return {u: "" for u in urls}

    # Use shared browser instance; create it lazily in a concurrency-safe way
    sem = asyncio.Semaphore(PLAYWRIGHT_CONCURRENCY)

    global _playwright_instance, _playwright_browser

    async def _ensure_browser():
        # Fast path: browser already launched by a previous call
        if _playwright_browser is not None:
            return _playwright_browser
        # Slow path: acquire the lock so only one coroutine launches the browser
        async with _playwright_lock:
            # Re-check inside the lock in case another coroutine launched it while we waited
            if _playwright_browser is not None:
                return _playwright_browser
            try:
                from playwright.async_api import async_playwright
                p = await async_playwright().start()
                browser = await p.chromium.launch(headless=True)
                _playwright_instance = p
                _playwright_browser = browser
                return _playwright_browser
            except Exception:
                # Playwright not installed / failed to launch — disable for this run
                _playwright_instance = None
                _playwright_browser = None
                return None

    browser = await _ensure_browser()
    if not browser:
        return {u: "" for u in urls}

    async def _fetch_one(url: str) -> tuple[str, str]:
        async with sem:
            try:
                page = await browser.new_page(viewport={"width": 1440, "height": 1100})
                await page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)
                try:
                    # Best-effort wait for network activity to settle (JS-rendered content)
                    await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
                except Exception:
                    pass
                # Scroll to the bottom to trigger any lazy-loaded content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(300)
                html = await page.content()
                await page.close()
                return url, html
            except Exception:
                # Ensure the page is closed even if navigation/content extraction failed
                try:
                    await page.close()
                except Exception:
                    pass
                return url, ""

    results = await asyncio.gather(*[_fetch_one(u) for u in urls])
    return dict(results)


# kept for single-URL backward-compat
async def playwright_fetch(url: str) -> str:
    """Fetch a single URL via the batch Playwright fetcher and return its HTML (or "" on failure)."""
    result = await playwright_fetch_batch([url])
    return result.get(url, "")

# ─────────────────────────────────────────
# MAIN SCRAPER  (concurrent page processing)
# ─────────────────────────────────────────

async def scrape_website(url: str, company_type: str = ""):
    """
    Generic fallback scraper: breadth-first crawl (bounded by MAX_PAGES /
    MAX_DEPTH) of the given site, fetching pages concurrently via httpx and
    falling back to Playwright only for pages that look JS-rendered/thin,
    then extracting product or service names from each page.
    """

    url          = normalize_url(url)
    company_kind = "service" if "service" in company_type.lower() else "product"
    parsed       = urlparse(url)
    root         = f"{parsed.scheme}://{parsed.netloc}"

    # BFS queue: list of (url, depth)
    queue   = [(url, 0)]
    visited = set()
    collected: list[str] = []

    while queue and len(visited) < MAX_PAGES:

        # ── 1. Pull a batch of unvisited URLs at the current frontier ──────
        batch: list[tuple[str, int]] = []
        seen_in_batch: set[str] = set()

        for item in list(queue):
            canon_url, depth = item
            canon_url = canonicalize_url(canon_url)
            if canon_url not in visited and canon_url not in seen_in_batch:
                batch.append((canon_url, depth))
                seen_in_batch.add(canon_url)
            if len(batch) >= HTTPX_CONCURRENCY:
                break

        # Remove consumed items from the queue
        consumed = {u for u, _ in batch}
        queue    = [(u, d) for u, d in queue if u not in consumed]

        if not batch:
            break

        batch_urls = [u for u, _ in batch]
        for u in batch_urls:
            visited.add(u)

        # ── 2. Fetch all batch URLs concurrently with httpx ────────────────
        html_map = await fetch_html_batch(batch_urls)

        # ── 3. Identify pages that need Playwright ────────────────────────
        # (i.e. their httpx-fetched HTML doesn't look content-rich, likely JS-rendered)
        needs_playwright = [
            u for u in batch_urls
            if PLAYWRIGHT_ENABLED and not is_meaningful_html(html_map[u])
        ]

        if needs_playwright:
            pw_map   = await playwright_fetch_batch(needs_playwright)
            html_map.update(pw_map)   # overwrite only the weak pages

        # ── 4. Parse & extract from each fetched page ─────────────────────
        for canon_url, depth in batch:
            html = html_map.get(canon_url, "")
            if not html:
                continue

            soup  = BeautifulSoup(html, "html.parser")
            items = extract_business_items(soup, company_kind)
            collected.extend(items)

            if depth >= MAX_DEPTH:
                # Don't crawl further from pages already at the max depth
                continue

            links = discover_links(soup, canon_url or root, company_kind)
            for link in links:
                if link not in visited and not any(link == q[0] for q in queue):
                    queue.append((link, depth + 1))

        queue = queue[: MAX_PAGES * 2]   # keep queue bounded

    # ── Final dedup ────────────────────────────────────────────────────────
    final: list[str] = []
    seen:  set[str]  = set()

    for item in collected:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            final.append(item)
        if len(final) >= MAX_ITEMS:
            break

    if not final:
        return {"scraped": False, "reason": "No items found"}

    # Result key differs depending on whether we scraped services or products/brands
    key = "services" if company_kind == "service" else "brands"
    return {
        "scraped":  True,
        "website":  url,
        key:        ", ".join(final),
        "category": company_kind,
    }

# ─────────────────────────────────────────
# API ROUTE
# ─────────────────────────────────────────

@router.post("/enrich")
async def enrich_company(payload: EnrichRequest):
    """
    Scrape the given company website for its products/brands or services,
    depending on company_type. Prefers a dedicated service/product scraper
    module, falling back to the generic scrape_website() if delegation fails.
    """
    if not payload.website_url.strip():
        raise HTTPException(status_code=400, detail="Website URL required")

    try:
        if "service" in (payload.company_type or "").lower():
            # Company self-identified as a services business — use the specialized scraper
            from .service_scraper import scrape_service_site
            result = await scrape_service_site(payload.website_url)
        else:
            # Default to the product/brand scraper
            from .product_scraper import scrape_product_site
            result = await scrape_product_site(payload.website_url)
    except Exception:
        # If delegation fails, fall back to the generic scraper
        result = await scrape_website(payload.website_url, payload.company_type)

    return {
        "success": True,
        "scraped": result.get("scraped", False),
        "message": result.get("reason", ""),
        "data": {
            "website":  result.get("website", ""),
            "brands":   result.get("brands", ""),
            "services": result.get("services", ""),
            "category": result.get("category", ""),
        }
    }

# ─────────────────────────────────────────
# SAVE PROFILE  (unchanged)
# ─────────────────────────────────────────

@router.post("/save-profile")
async def save_profile(payload: SaveProfileRequest):
    """
    Persist the (possibly user-edited) company profile — including the
    scraped brands/services — into delphi_company_profiles.
    """
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        query = """
        INSERT INTO delphi_company_profiles (
            user_id, linkedin_url, company_name, industry, company_size,
            headquarters, type, company_type, founded, revenue_size,
            specialties, website, brands, services
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        # Only store brands for product companies and services for service
        # companies — the other column is left blank for this row
        company_kind = "service" if "service" in payload.company_type.lower() else "product"
        brands   = payload.brands   if company_kind == "product" else ""
        services = payload.services if company_kind == "service"  else ""

        values = (
            payload.user_id, payload.linkedin_url, payload.company_name,
            payload.industry, payload.company_size, payload.headquarters,
            payload.type, payload.company_type, payload.founded,
            payload.revenue_size, payload.specialties, payload.website,
            brands, services,
        )

        cursor.execute(query, values)
        conn.commit()

        return {
            "success":    True,
            "message":    "Profile saved successfully",
            "profile_id": cursor.lastrowid,
        }

    except Exception as e:
        # Surface DB errors as a 500 with the exception message
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Always attempt to clean up the cursor/connection, even on error
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass