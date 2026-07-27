# context_builder.py
from .intent_analyzer import analyze_intent
from .taxonomy_matcher import match_taxonomy_value
from .ai_taxonomy_service import (
    PRODUCT_FIELDS,
    TARGETING_FIELDS,
    extract_product_context,
    get_next_field,
)

# ── Keywords that strongly signal a targeting-first message ──────────────────
_TARGETING_SIGNALS = (
    "targeting", "target", "c-level", "c level", "vp ", "director",
    "manager", "ceo", "cto", "cfo", "cmo", "coo",
    "enterprise", "mid-size", "mid size", "midsize", "small business",
    "manufacturing", "technology", "healthcare", "finance", "retail",
    "united states", " usa", " us ", "europe", "india", "uk ",
    "campaign for", "leads for", "run a campaign",
)

def _is_targeting_flavored(text: str) -> bool:
    lower = text.lower()
    return any(signal in lower for signal in _TARGETING_SIGNALS)


def build_context(
    user_input: str,
    existing_context: dict,
    current_phase: str = "product",
) -> dict:
    """
    Phase-aware context builder.

    current_phase is passed in from routes.py so analyze_intent() can suppress
    revenue_range extraction when a budget/pricing answer arrives in product phase.
    This fixes the bug where "$30K" budget answer was leaking into revenue_range.
    """
    candidates = {}

    # ── Determine which product field was just being asked about ──────────────
    next_product_field = next(
        (f for f in PRODUCT_FIELDS if not existing_context.get(f)),
        None
    )

    # ── Product field extraction ──────────────────────────────────────────────
    # Skip if:
    #   (a) no product field is pending, OR
    #   (b) the pending field is product_description and the message looks like
    #       the user is giving targeting info (first-message targeting pattern)
    should_skip_product_extraction = (
        next_product_field is None
        or (
            next_product_field == "product_description"
            and _is_targeting_flavored(user_input)
        )
    )

    if not should_skip_product_extraction:
        product_data = extract_product_context(user_input, next_product_field)
        candidates.update(product_data)

    # ── Targeting extraction ──────────────────────────────────────────────────
    # Pass current_phase so the extractor blocks budget→revenue_range leakage
    extracted = analyze_intent(user_input, current_phase=current_phase)
    taxonomy_data = match_taxonomy_value(user_input)
    targeting_candidates = {**extracted, **taxonomy_data}
    for k, v in targeting_candidates.items():
        if k in TARGETING_FIELDS:
            candidates[k] = v

    # ── Write to context — never overwrite existing values ────────────────────
    for k, v in candidates.items():
        if v and isinstance(v, str) and v.strip():
            if not existing_context.get(k):
                existing_context[k] = v.strip()

    return existing_context