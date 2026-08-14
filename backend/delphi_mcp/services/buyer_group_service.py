import mysql.connector

from config import MYSQL_CONFIG
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
        FROM delphi_context_builder_user_selections
        WHERE user_id=%s
        """

        self.cursor.execute(sql, (user_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        return row.get("selected_product")

    # ----------------------------------------------------
    # STEP 2
    # Brand options for the "which brand do you want to
    # build a buyer group for" screen. Mirrors
    # ICPService.get_product_options's shape, but resolves
    # all the way down to Brand_id since Usp_get_buyer_groups
    # needs a concrete brand_id, not just a name.
    #
    # NOTE: assumes Mst_tblclient_brands has a Brand_id column.
    # If your schema instead keys buyer-group data off Client_id,
    # swap Brand_id -> Client_id below and in Usp_get_buyer_groups.
    # ----------------------------------------------------

    def get_brand_options(self, user_id):

        product = self.get_selected_product(user_id)

        competitor_brands = find_similar_brands_llm(product) if product else []

        if not competitor_brands:
            return {"options": []}

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

        options = [
            {"brand_id": row["Brand_id"], "brand_name": row["Brand_name"]}
            for row in rows
        ]

        return {"options": options}

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

    # ----------------------------------------------------
    # STEP 4
    # Orchestrate the full Buyer Group discovery pipeline and
    # shape the response to match what BuyerGroup.js renders:
    #
    #   {
    #       "buyer_group_insight": {
    #           "economic_buyer": "...",
    #           "champion": "...",
    #           "influencers": [...],
    #           "group_size": "...",
    #           "why": "..."
    #       },
    #       "roles": [
    #           {
    #               "job_level": "...",
    #               "job_function": "...",
    #               "employee_size": "...",
    #               "revenue_size": "...",
    #               "percentage": 25.40
    #           }
    #       ],
    #       "summary": { "job_levels": [...] },
    #       "total_qualified_leads": 4920
    #   }
    # ----------------------------------------------------

    def discover_buyer_groups(self, brand_id, brand_name=None, product_name=None):

        candidates = self.get_buyer_group_candidates(brand_id)

        if not candidates:
            return {
                "buyer_group_insight": {
                    "economic_buyer": "Not enough data yet.",
                    "champion": "Not enough data yet.",
                    "influencers": [],
                    "group_size": "Unknown",
                    "why": "Not enough qualified leads were found to map a buyer group for this brand yet."
                },
                "roles": [],
                "summary": {"job_levels": []},
                "total_qualified_leads": 0
            }

        insight = generate_buyer_group_insight(
            candidates=candidates,
            brand_name=brand_name,
            product_name=product_name
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