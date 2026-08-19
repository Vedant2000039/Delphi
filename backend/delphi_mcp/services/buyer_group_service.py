import json
import mysql.connector

try:
    from config import MYSQL_CONFIG
except Exception:
    from ..config import MYSQL_CONFIG

from .brand_matcher import find_similar_brands_llm
from .buyer_group_insight import generate_buyer_group_insight


class BuyerGroupService:

    def __init__(self):
        self.conn = mysql.connector.connect(**MYSQL_CONFIG)
        self.cursor = self.conn.cursor(dictionary=True)

    # ----------------------------------------------------
    # STEP 1
    # Get user's selected product (same table/shape as
    # ICPService.get_selected_product — kept here as its own
    # copy so BuyerGroupService doesn't depend on ICPService).
    # ----------------------------------------------------

    def get_selected_product(self, user_id):

        sql = """
        SELECT
            selected_product
        FROM delphi_selected_product_context
        WHERE user_id=%s
        """

        self.cursor.execute(sql, (user_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        return row.get("selected_product")

    # ----------------------------------------------------
    # STEP 2a
    # Read the brand scope ICP already resolved and cached
    # (ICPService._save_matched_brand_context writes this row at
    # the end of every discover_icp call). This is the preferred
    # path — Buyer Group should reuse ICP's brand match, not
    # independently re-derive it.
    # ----------------------------------------------------

    def _get_cached_brand_context(self, user_id):

        sql = """
        SELECT
            product,
            matched_brands,
            matched_brand_ids
        FROM delphi_icp_brand_context
        WHERE user_id=%s
        """

        try:
            self.cursor.execute(sql, (user_id,))
            row = self.cursor.fetchone()
        except Exception:
            # Table may not exist yet in older environments — fall
            # back to recomputing rather than erroring out.
            return None

        if not row:
            return None

        try:
            brand_ids = json.loads(row.get("matched_brand_ids") or "[]")
            brand_names = json.loads(row.get("matched_brands") or "[]")
        except (TypeError, ValueError):
            return None

        return {
            "product": row.get("product"),
            "brand_ids": brand_ids,
            "brand_names": brand_names
        }

    # ----------------------------------------------------
    # STEP 2b
    # Resolve the brand_id(s) to build a buyer group for. First
    # tries the cached context ICP already produced; only if
    # that's missing (e.g. ICP was never run for this user) does
    # it fall back to recomputing via find_similar_brands_llm —
    # the exact same competitor-brand matching ICP discovery uses.
    #
    # NOTE: assumes Mst_tblclient_brands has a Brand_id column.
    # If your schema instead keys buyer-group data off Client_id,
    # swap Brand_id -> Client_id below and in Usp_get_buyer_groups.
    # ----------------------------------------------------

    def resolve_brand_context(self, user_id):
        """
        Returns:
            {
                "product": "MacBook" | None,
                "brand_ids": [12, 47, ...],
                "brand_names": ["Apple", ...]
            }
        """

        cached = self._get_cached_brand_context(user_id)
        current_product = self.get_selected_product(user_id)

        # Only trust the cache if it was resolved for the SAME product
        # the user currently has selected. Otherwise (product switched
        # since ICP last ran) it's stale and must be recomputed.
        if cached and cached.get("product") and cached.get("product") == current_product:
            return cached

        product = current_product

        if not product:
            return {"product": None, "brand_ids": [], "brand_names": []}

        competitor_brands = find_similar_brands_llm(product) or []

        if not competitor_brands:
            return {"product": product, "brand_ids": [], "brand_names": []}

        placeholders = ",".join(["%s"] * len(competitor_brands))

        sql = f"""
        SELECT
            Brand_id,
            Brand_name
        FROM Mst_tblclient_brands
        WHERE Brand_name IN ({placeholders})
            AND Isactive = 1
        """

        self.cursor.execute(sql, competitor_brands)
        rows = self.cursor.fetchall()

        brand_ids = list({row["Brand_id"] for row in rows if row.get("Brand_id")})
        brand_names = list({row["Brand_name"] for row in rows if row.get("Brand_name")})

        return {"product": product, "brand_ids": brand_ids, "brand_names": brand_names}

    # ----------------------------------------------------
    # STEP 3
    # Call Usp_get_buyer_groups(p_brand_id) and return the
    # aggregated employee_size / revenue_size / job_level /
    # job_function candidate rows. No individual lead records
    # are touched — the proc itself only returns counts and
    # percentages.
    # ----------------------------------------------------

    def get_buyer_group_candidates(self, brand_id):
        """
        Calls Usp_get_buyer_groups.
        Signature: (p_brand_id)
        Returns up to 10 rows, already ordered by lead_count DESC
        by the proc itself:

            {
                "employee_size": "51-200",
                "revenue_size": "10M-50M",
                "job_level": "Director",
                "job_function": "Information Technology",
                "lead_count": 1250,
                "percentage": 25.40
            }
        """

        self.cursor.callproc(
            "Usp_get_buyer_groups",
            (brand_id,)
        )

        candidates = []

        for result in self.cursor.stored_results():
            candidates.extend(result.fetchall())

        return candidates

    def get_buyer_group_candidates_merged(self, brand_ids):
        """
        A product can match multiple CRM brands (mirrors
        ICPService.get_ideal_snapshot_merged). Runs
        Usp_get_buyer_groups per matched brand_id and merges rows
        across brands, summing lead_count for identical
        (employee_size, revenue_size, job_level, job_function)
        combinations and recomputing percentage across the merged
        total, then keeps the top 10 by lead_count.
        """

        if not brand_ids:
            return []

        merged = {}

        for brand_id in brand_ids:
            for row in self.get_buyer_group_candidates(brand_id):
                key = (
                    row.get("employee_size"),
                    row.get("revenue_size"),
                    row.get("job_level"),
                    row.get("job_function"),
                )
                if key not in merged:
                    merged[key] = dict(row)
                else:
                    merged[key]["lead_count"] = (
                        merged[key].get("lead_count", 0) + row.get("lead_count", 0)
                    )

        total = sum(r.get("lead_count", 0) for r in merged.values())

        result = list(merged.values())
        for row in result:
            row["percentage"] = (
                round((row.get("lead_count", 0) * 100.0 / total), 2) if total else 0
            )

        result.sort(key=lambda r: r.get("lead_count", 0), reverse=True)

        return result[:10]

    # ----------------------------------------------------
    # STEP 4
    # Orchestrate the full Buyer Group discovery pipeline and
    # shape the response to match what BuyerGroup.js renders.
    # Always driven off the user's saved ICP/product context —
    # never asks the user to pick a brand.
    # ----------------------------------------------------

    def discover_buyer_groups(self, user_id):

        context = self.resolve_brand_context(user_id)
        product = context["product"]
        brand_ids = context["brand_ids"]
        brand_names = context["brand_names"]

        if not product:
            return {
                "product": None,
                "brand_names": [],
                "buyer_group_insight": {
                    "economic_buyer": "Not enough data yet.",
                    "champion": "Not enough data yet.",
                    "influencers": [],
                    "group_size": "Unknown",
                    "why": "No product or service has been selected for this account yet."
                },
                "roles": [],
                "summary": {"job_levels": []},
                "total_qualified_leads": 0,
                "error": "no_product_selected"
            }

        candidates = self.get_buyer_group_candidates_merged(brand_ids)

        if not candidates:
            return {
                "product": product,
                "brand_names": brand_names,
                "buyer_group_insight": {
                    "economic_buyer": "Not enough data yet.",
                    "champion": "Not enough data yet.",
                    "influencers": [],
                    "group_size": "Unknown",
                    "why": "Not enough qualified leads were found to map a buyer group for this ICP yet."
                },
                "roles": [],
                "summary": {"job_levels": []},
                "total_qualified_leads": 0
            }

        insight = generate_buyer_group_insight(
            candidates=candidates,
            brand_name=", ".join(brand_names),
            product_name=product
        )

        roles = [
            {
                "job_level": row.get("job_level"),
                "job_function": row.get("job_function"),
                "employee_size": row.get("employee_size"),
                "revenue_size": row.get("revenue_size"),
                "percentage": row.get("percentage")
            }
            for row in candidates
        ]

        job_levels = list(dict.fromkeys(
            row.get("job_level") for row in candidates if row.get("job_level")
        ))

        total_qualified_leads = sum(row.get("lead_count", 0) for row in candidates)

        return {
            "product": product,
            "brand_names": brand_names,
            "buyer_group_insight": insight,
            "roles": roles,
            "summary": {"job_levels": job_levels},
            "total_qualified_leads": total_qualified_leads
        }

    def close(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception:
            pass