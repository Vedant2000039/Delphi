# backend/apis/Onboarding/explorium_service.py
"""
Thin, resilient wrapper around Explorium's Business Match API.

Design mirrors openai_service.py's failure discipline:
  - Never raises out to the caller.
  - Never returns a value that looks like success but isn't (no silent
    empty-but-truthy payloads) — callers get either a real match dict or None.
  - A 429 (quota exhaustion) trips a short cooldown so we don't hammer
    Explorium or block onboarding while it's rate-limiting us.
"""

import os
import time
import logging
import httpx

logger = logging.getLogger("explorium_service")

EXPLORIUM_API_KEY = os.getenv("EXPLORIUM_API_KEY")
BASE_URL = "https://api.explorium.ai/v1"

REQUEST_TIMEOUT = 8  # seconds
COOLDOWN_SECONDS = 60

# Module-level cooldown state. Simple and process-local — fine for a single
# API instance; move to Redis/shared cache if you run multiple workers and
# want the cooldown to be shared across them.
_cooldown_until = 0.0


def _in_cooldown() -> bool:
    return time.time() < _cooldown_until


def _trip_cooldown() -> None:
    global _cooldown_until
    _cooldown_until = time.time() + COOLDOWN_SECONDS


async def match_business(name: str, domain: str) -> dict | None:
    """
    Resolve a company by name + domain to an Explorium business record.

    Returns:
        dict  - the first matched business record on success
        None  - on no-match, timeout, HTTP error, 429/cooldown, or missing
                API key. Callers must treat None as "no data available"
                and fall back to manual entry — never treat it as an error
                to surface to the end user.
    """
    if not EXPLORIUM_API_KEY:
        logger.warning("EXPLORIUM_API_KEY is not set — skipping lookup for domain=%s", domain)
        return None

    if _in_cooldown():
        logger.info("Explorium in cooldown — skipping lookup for domain=%s", domain)
        return None

    if not domain:
        return None

    payload = {"businesses_to_match": [{"name": name, "domain": domain}]}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/businesses/match",
                headers={"api_key": EXPLORIUM_API_KEY},
                json=payload,
            )

        if resp.status_code == 429:
            logger.warning("Explorium 429 rate limited — tripping cooldown")
            _trip_cooldown()
            return None

        if resp.status_code >= 500:
            logger.warning("Explorium %s server error for domain=%s", resp.status_code, domain)
            return None

        if resp.status_code >= 400:
            logger.warning(
                "Explorium %s error for domain=%s: %s",
                resp.status_code, domain, resp.text[:500],
            )
            return None

        resp.raise_for_status()
        body = resp.json()

    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.warning("Explorium request failed for domain=%s: %s", domain, e)
        _trip_cooldown()
        return None
    except ValueError:
        logger.warning("Explorium returned unparseable JSON for domain=%s", domain)
        return None
    except Exception:
        logger.exception("Unexpected error calling Explorium for domain=%s", domain)
        return None

    matches = (
        body.get("matched_businesses")
        or body.get("data")
        or body.get("businesses")
        or []
    )

    if not matches:
        logger.info("Explorium returned no matches for domain=%s: %s", domain, body)
        return None

    return matches[0]


def map_explorium_to_profile(match: dict) -> dict:
    """
    Map an Explorium match record to the SaveProfileRequest field names
    used by Delphi's onboarding form.

    NOTE: Explorium's actual field names vary by endpoint/plan version.
    The keys read below (firmo.get("industry"), etc.) are best-guess
    based on typical firmographic API shapes — confirm against a real
    response payload and adjust the .get(...) keys accordingly. Every
    field defaults to "" so a partially-wrong mapping degrades to "field
    left blank," never to a crash or garbage value in the form.
    """
    if not match:
        return {}

    # Some Explorium responses nest firmographic detail under a sub-key;
    # others return it flat on the match object. Handle both.
    firmo = match.get("firmographics") or match

    employees = firmo.get("employees_count") or firmo.get("number_of_employees")
    founded_year = firmo.get("founded_year") or firmo.get("year_founded")
    keywords = firmo.get("keywords") or firmo.get("specialties") or []

    return {
        "industry": firmo.get("industry", "") or "",
        "company_size": str(employees) if employees else "",
        "headquarters": (
            firmo.get("hq_location")
            or firmo.get("headquarters")
            or firmo.get("country")
            or ""
        ),
        "founded": str(founded_year) if founded_year else "",
        "revenue_size": firmo.get("revenue_range") or firmo.get("revenue") or "",
        "linkedin_url": firmo.get("linkedin_url") or firmo.get("linkedin") or "",
        "specialties": ", ".join(keywords) if isinstance(keywords, list) else str(keywords or ""),
    }