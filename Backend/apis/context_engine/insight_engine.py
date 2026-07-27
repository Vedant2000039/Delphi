# insight_engine.py
# ─────────────────────────────────────────────────────────────
# Orchestrates all three scoring models for a list of lead IDs:
#   1. Propensity Scoring  (vw_lead_score_breakdown)
#   2. ICP Scoring         (vw_icp_score_breakdown)
#   3. Persona Scoring     (Usp_get_persona_breakdown)
# Returns enriched, ranked lead records ready for display.
# ─────────────────────────────────────────────────────────────
from __future__ import annotations
import logging
from db import get_conn

log = logging.getLogger(__name__)

# ── Priority / tier sort maps ─────────────────────────────────
PRIORITY_ORDER = {"Very High": 1, "High": 2, "Medium": 3, "Low": 4, "Very Low": 5}
TIER_ORDER     = {"Tier 1": 1, "Tier 2": 2, "Tier 3": 3, "Tier 4": 4}

# ── Thresholds ────────────────────────────────────────────────
HIGH_SCORE_THRESHOLD = 40          # minimum combined score to include a lead
TOP_N               = 10           # max leads returned to the user


# ══════════════════════════════════════════════════════════════
# BUSINESS LOGIC (from GeneratePersona.py — kept in sync)
# ══════════════════════════════════════════════════════════════

def _derive_persona(job_level_desc: str, persona_tier: str) -> str:
    level = (job_level_desc or "").lower()
    tier  = (persona_tier or "Tier 4").strip()
    if any(k in level for k in ["cxo", "c-suite", "chief", "ceo", "cio", "cto", "cfo", "president"]):
        return "Economic Buyer" if tier in ("Tier 1", "Tier 2") else "Technical Buyer"
    if any(k in level for k in ["director", "vp", "vice president", "head"]):
        return "Champion" if tier in ("Tier 1", "Tier 2") else "Operational Influencer"
    if "manager" in level:
        return "Evaluator"
    if any(k in level for k in ["senior", "lead", "principal", "architect"]):
        return "Technical Evaluator"
    if any(k in level for k in ["procurement", "purchasing", "admin"]):
        return "Gatekeeper"
    return "Influencer"


def _derive_persona_role(persona: str, persona_tier: str, engagement_score: float) -> str:
    tier = (persona_tier or "Tier 4").strip()
    if persona == "Economic Buyer":
        return "Decision Maker"
    if persona == "Champion" or (tier == "Tier 1" and engagement_score >= 70):
        return "Internal Advocate" if engagement_score >= 75 else "Champion"
    if persona == "Gatekeeper" or tier == "Tier 4":
        return "Blocker"
    if persona in ("Technical Buyer", "Technical Evaluator", "Evaluator", "Operational Influencer"):
        return "Influencer"
    return "Influencer"


def _derive_priority(icp_score: float, propensity_score: float, persona_tier: str) -> str:
    tier = (persona_tier or "Tier 4").strip()
    if icp_score >= 50 and propensity_score >= 50 and tier == "Tier 1":
        return "Very High"
    if (icp_score >= 50 or propensity_score >= 60) and tier == "Tier 2":
        return "High"
    if (icp_score >= 40 or propensity_score >= 50) and tier == "Tier 3":
        return "Medium"
    if (icp_score >= 30 or propensity_score >= 30) and tier == "Tier 4":
        return "Low"
    return "Very Low"


def _derive_action(priority: str, persona_role: str, persona: str) -> str:
    if priority == "Very High":
        if persona_role == "Decision Maker":       return "Fast-track to proposal"
        if persona_role in ("Internal Advocate", "Champion"): return "Equip with sales enablement"
        return "Accelerate consensus building"
    if priority == "High":
        if persona_role == "Decision Maker":       return "Personalized executive outreach"
        if persona_role in ("Internal Advocate", "Champion"): return "Equip with sales enablement"
        if persona in ("Technical Buyer", "Technical Evaluator"): return "Deep-dive architecture call"
        if persona == "Evaluator":                 return "Technical demo + validation"
        return "Engage and qualify"
    if priority == "Medium":
        if persona_role == "Decision Maker":       return "Nurture with ROI content"
        if persona_role == "Blocker":              return "Deprioritize / monitor"
        return "Tactical short-cycle close"
    if persona_role == "Blocker":                  return "Suppress from active outreach"
    return "Deprioritize / monitor"


# ══════════════════════════════════════════════════════════════
# DB HELPERS
# ══════════════════════════════════════════════════════════════

def _call_proc(cursor, proc: str, args: list) -> list[dict]:
    cursor.callproc(proc, args)
    rows: list[dict] = []
    for result in cursor.stored_results():
        cols = [d[0] for d in result.description]
        for row in result.fetchall():
            rows.append(dict(zip(cols, row)))
    return rows


def _flt(val, default: float = 0.0) -> float:
    try:
        return float(val or default)
    except (TypeError, ValueError):
        return default


# ══════════════════════════════════════════════════════════════
# FETCH LEAD DETAILS  (full profile from DB)
# ══════════════════════════════════════════════════════════════

def _fetch_lead_detail(cursor, lead_id: int) -> dict | None:
    cursor.execute("""
        SELECT
            lm.Lead_id,
            lm.Company_name,
            CONCAT(lm.First_name, ' ', lm.Last_name)  AS name,
            lm.Email_id,
            lm.Phone_number,
            lm.Job_title,

            jl.Job_level_desc,
            jf.Jobfunction_desc,
            si.Standard_industry_desc  AS industry,
            es.Employee_size_desc,
            rs.Revenue_size_desc,
            loc.Location_desc          AS country,

            COALESCE(qs.QAstatus_desc, 'Not Audited') AS qa_status,
            CASE WHEN qad.Record_id IS NULL THEN 0 ELSE 1 END AS is_audited,

            sup.Supressreason_desc,
            sup.Supress_until_dt,
            sup.Inserted_dt            AS suppressed_on_dt

        FROM tblleads_masterlist lm

        LEFT JOIN (
            SELECT e1.*
            FROM tblengaged_leads e1
            JOIN (
                SELECT Lead_id, MAX(Engage_id) AS max_engage_id
                FROM tblengaged_leads
                WHERE Isdelete = b'0' AND Isaudited = b'1'
                GROUP BY Lead_id
            ) e2 ON e1.Lead_id = e2.Lead_id AND e1.Engage_id = e2.max_engage_id
        ) el ON el.Lead_id = lm.Lead_id

        LEFT JOIN tblqualityaudit_details qad
            ON qad.Engage_id = el.Engage_id AND qad.Isdelete = b'0'
        LEFT JOIN Mst_tblqualityaudit_status qs
            ON qs.QAstatus_id = qad.Auditstatus_id

        LEFT JOIN Mst_tbljoblevel    jl ON jl.Job_level_id         = lm.Job_level_id
        LEFT JOIN Mst_tbljobfunction jf ON jf.Jobfunction_id       = lm.Jobfunction_id
        LEFT JOIN Mst_tblstandardindustry si ON si.Standard_industry_id = lm.Standard_industry_id
        LEFT JOIN Mst_tblemployeesize es ON es.Employee_size_id    = lm.Employee_size_id
        LEFT JOIN Mst_tblrevenuesize  rs ON rs.Revenue_size_id     = lm.Revenue_size_id
        LEFT JOIN Mst_tbllocationelements loc ON loc.Location_id   = lm.Country_id
        LEFT JOIN vw_recent_suppressed_leads sup ON sup.Lead_id    = lm.Lead_id

        WHERE lm.Lead_id = %s
        LIMIT 1
    """, (lead_id,))
    return cursor.fetchone()


# ══════════════════════════════════════════════════════════════
# SCORE A SINGLE LEAD
# ══════════════════════════════════════════════════════════════

def _score_lead(cursor, lead_id: int, lead_detail: dict) -> dict:
    """
    Run all three scoring models and combine into one enriched record.
    """
    # ── 1. Propensity breakdown ───────────────────────────────
    try:
        cursor.execute("""
            SELECT parameter_name, raw_score, weight, weighted_score
            FROM vw_lead_score_breakdown
            WHERE Lead_id = %s
            ORDER BY weighted_score DESC
        """, (lead_id,))
        propensity_breakdown = cursor.fetchall()
        propensity_score = sum(_flt(r["weighted_score"]) for r in propensity_breakdown)
    except Exception as e:
        log.warning(f"Propensity fetch failed for lead {lead_id}: {e}")
        propensity_breakdown = []
        propensity_score = 0.0

    # ── 2. ICP breakdown ─────────────────────────────────────
    try:
        cursor.execute("""
            SELECT parameter_name, raw_score, weight, weighted_score
            FROM vw_icp_score_breakdown
            WHERE Lead_id = %s
            ORDER BY weighted_score DESC
        """, (lead_id,))
        icp_breakdown = cursor.fetchall()
        icp_score = sum(_flt(r["weighted_score"]) for r in icp_breakdown)
    except Exception as e:
        log.warning(f"ICP fetch failed for lead {lead_id}: {e}")
        icp_breakdown = []
        icp_score = 0.0

    # ── 3. Persona breakdown ──────────────────────────────────
    try:
        persona_rows = _call_proc(cursor, "Usp_get_persona_breakdown", [lead_id])
        bd = persona_rows[0] if persona_rows else {}
    except Exception as e:
        log.warning(f"Persona proc failed for lead {lead_id}: {e}")
        bd = {}

    engagement_score  = _flt(bd.get("Engagement_Score"))
    conversion_score  = _flt(bd.get("Conversion_Score"))
    velocity_score    = _flt(bd.get("Deal_Velocity_Score"))
    deal_size_score   = _flt(bd.get("Deal_Size_Impact_Score"))
    final_score       = _flt(bd.get("Final_Persona_Score"))
    persona_tier      = bd.get("Persona_Tier", "Tier 4")
    business_meaning  = bd.get("Business_Meaning", "")

    # ── 4. Derived fields ─────────────────────────────────────
    job_level_desc    = lead_detail.get("Job_level_desc", "") or ""
    persona           = _derive_persona(job_level_desc, persona_tier)
    persona_role      = _derive_persona_role(persona, persona_tier, engagement_score)
    priority          = _derive_priority(icp_score, propensity_score, persona_tier)
    action            = _derive_action(priority, persona_role, persona)

    # ── 5. Combined score (equal-weight blend) ────────────────
    combined_score = round((propensity_score + icp_score + final_score) / 3, 2)

    return {
        # Identity
        "lead_id":           lead_id,
        "name":              lead_detail.get("name", ""),
        "email":             lead_detail.get("Email_id", ""),
        "phone":             lead_detail.get("Phone_number", ""),
        "company":           lead_detail.get("Company_name", ""),
        "job_title":         lead_detail.get("Job_title", ""),
        "job_level":         job_level_desc,
        "job_function":      lead_detail.get("Jobfunction_desc", "") or "",
        "industry":          lead_detail.get("industry", "") or "",
        "employee_size":     lead_detail.get("Employee_size_desc", "") or "",
        "revenue_size":      lead_detail.get("Revenue_size_desc", "") or "",
        "country":           lead_detail.get("country", "") or "",
        "qa_status":         lead_detail.get("qa_status", "Not Audited"),
        "is_audited":        bool(lead_detail.get("is_audited", 0)),
        "suppressed":        bool(lead_detail.get("Supressreason_desc")),
        "suppress_reason":   lead_detail.get("Supressreason_desc", ""),

        # Scores
        "propensity_score":  round(propensity_score, 2),
        "icp_score":         round(icp_score, 2),
        "engagement_score":  round(engagement_score, 2),
        "conversion_score":  round(conversion_score, 2),
        "velocity_score":    round(velocity_score, 2),
        "deal_size_score":   round(deal_size_score, 2),
        "final_persona_score": round(final_score, 2),
        "combined_score":    combined_score,

        # Intelligence
        "persona":           persona,
        "persona_tier":      persona_tier,
        "business_meaning":  business_meaning,
        "persona_role":      persona_role,
        "priority":          priority,
        "recommended_action": action,

        # Breakdowns (for detailed view)
        "breakdown": {
            "propensity": propensity_breakdown,
            "icp":        icp_breakdown,
        }
    }


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def run_insight_engine(cortex_leads: list[dict]) -> list[dict]:
    """
    Given a list of leads from Cortex (each must have a 'lead_id' or 'Lead_id' key),
    score each lead through all three models, filter by threshold, and return
    the TOP_N leads ranked by combined_score descending.
    """
    if not cortex_leads:
        return []

    conn   = None
    cursor = None

    try:
        conn   = get_conn()
        cursor = conn.cursor(dictionary=True)

        enriched: list[dict] = []

        for raw in cortex_leads:
            lead_id = raw.get("lead_id") or raw.get("Lead_id")
            if not lead_id:
                continue

            try:
                detail = _fetch_lead_detail(cursor, int(lead_id))
                if not detail:
                    log.warning(f"Lead {lead_id} not found in DB — skipping")
                    continue

                scored = _score_lead(cursor, int(lead_id), detail)

                # Filter out very low combined score leads
                if scored["combined_score"] >= HIGH_SCORE_THRESHOLD:
                    enriched.append(scored)

            except Exception as e:
                log.exception(f"Scoring failed for lead {lead_id}: {e}")
                continue

        # Sort by combined score desc, then by priority tier
        enriched.sort(key=lambda x: (
            -x["combined_score"],
            PRIORITY_ORDER.get(x["priority"], 6),
            TIER_ORDER.get(x["persona_tier"], 5),
        ))

        return enriched[:TOP_N]

    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass