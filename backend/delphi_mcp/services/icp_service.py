
import mysql.connector

try:
    from config import MYSQL_CONFIG
except ImportError:
    from ..config import MYSQL_CONFIG

from .brand_matcher import find_similar_brands_llm, analyze_product
from .insight_generator import generate_icp_insight


class ICPService:

    def __init__(self):
        self.conn = mysql.connector.connect(**MYSQL_CONFIG)
        self.cursor = self.conn.cursor(dictionary=True)

    # ----------------------------------------------------
    # STEP 1
    # Get user's selected product
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
            raise Exception("No context found for user.")

        return row["selected_product"]

    # ----------------------------------------------------
    # Product / service options for the "choose what to
    # analyze" screen — combines the user's originally
    # selected product/service with everything detected
    # from their company profile (brands + services).
    # ----------------------------------------------------

    def get_product_options(self, user_id):

        sql = """
        SELECT
            selected_product,
            selected_service
        FROM delphi_context_builder_user_selections
        WHERE user_id=%s
        """
        self.cursor.execute(sql, (user_id,))
        context_row = self.cursor.fetchone() or {}

        sql = """
        SELECT
            brands,
            services
        FROM delphi_company_profiles
        WHERE user_id=%s
        ORDER BY updated_at DESC
        LIMIT 1
        """
        self.cursor.execute(sql, (user_id,))
        profile_row = self.cursor.fetchone() or {}

        def _split(raw):
            if not raw:
                return []
            # brands/services are stored as free text — support
            # comma-separated or JSON array either way.
            raw = raw.strip()
            if raw.startswith("["):
                try:
                    import json
                    return [str(x).strip() for x in json.loads(raw) if str(x).strip()]
                except Exception:
                    pass
            return [x.strip() for x in raw.split(",") if x.strip()]

        detected_products = _split(profile_row.get("brands"))
        detected_services = _split(profile_row.get("services"))

        selected_product = context_row.get("selected_product")
        selected_service = context_row.get("selected_service")

        # Merge without duplicates, keeping the originally
        # selected item first so the UI can default to it.
        all_options = []

        for item in [selected_product] + detected_products:
            if item and item not in all_options:
                all_options.append(item)

        for item in [selected_service] + detected_services:
            if item and item not in all_options:
                all_options.append(item)

        return {
            "selected_product": selected_product,
            "selected_service": selected_service,
            "options": all_options
        }

    # ----------------------------------------------------
    # STEP 2
    # Compare product against CRM brands using an LLM.
    # Falls back silently to a hardcoded mapping inside
    # brand_matcher.py if OpenAI is unavailable or errors.
    # ----------------------------------------------------

    def find_similar_brands(self, product):

        return find_similar_brands_llm(product)

    # ----------------------------------------------------
    # STEP 3
    # Find matching CRM clients for the matched brands
    # ----------------------------------------------------

    def get_client_ids(self, brands):

        if not brands:
            return []

        placeholders = ",".join(["%s"] * len(brands))

        sql = f"""
        SELECT
            Client_id,
            Brand_name
        FROM Mst_tblclient_brands
        WHERE Brand_name IN ({placeholders})
            AND Isactive = 1
        """

        self.cursor.execute(sql, brands)

        return self.cursor.fetchall()

    # ----------------------------------------------------
    # STEP 4
    # Find campaigns tied to those clients
    # ----------------------------------------------------

    def get_campaigns(self, client_rows):

        if not client_rows:
            return []

        ids = [row["Client_id"] for row in client_rows]

        placeholders = ",".join(["%s"] * len(ids))

        sql = f"""
        SELECT
            Campaign_key_id,
            Campaign_desc,
            Client_id
        FROM Mst_tblclient_campaigns
        WHERE Client_id IN ({placeholders})
            AND Isactive = 1
        """

        self.cursor.execute(sql, ids)

        return self.cursor.fetchall()

    # ----------------------------------------------------
    # STEP 5 / 6
    # Run existing stored procedures for ICP analysis
    # ----------------------------------------------------

    def get_ideal_snapshot(self, industry_id=None, brand_id=None, country_id=None):
        """
        Calls Usp_get_icp_ideal_snapshot.
        Actual procedure signature (confirmed via
        INFORMATION_SCHEMA.PARAMETERS) is:
            1. p_industry_id
            2. p_brand_id
            3. p_country_id
        Returns 4 result sets (Employee Size, Revenue Size,
        Job Level, Job Function) merged into a single list.
        """

        args = (industry_id, brand_id, country_id)

        self.cursor.callproc(
            "Usp_get_icp_ideal_snapshot",
            args
        )

        snapshot = []

        for result in self.cursor.stored_results():
            snapshot.extend(result.fetchall())

        return snapshot

    def get_filtered_leads(
        self,
        country_id=None,
        industry_id=None,
        employee_size_id=None,
        revenue_size_id=None,
        job_level_id=None,
        job_function_id=None,
        page=1,
        page_size=20
    ):
        """
        Calls Usp_get_icp_filtered_leads.
        Returns (total_count, leads_list).
        """

        args = (
            country_id,
            industry_id,
            employee_size_id,
            revenue_size_id,
            job_level_id,
            job_function_id,
            page,
            page_size
        )

        self.cursor.callproc(
            "Usp_get_icp_filtered_leads",
            args
        )

        stored_results = list(self.cursor.stored_results())

        total = 0
        leads = []

        if len(stored_results) >= 1:
            count_row = stored_results[0].fetchone()
            if count_row:
                total = count_row.get("total", 0)

        if len(stored_results) >= 2:
            leads = stored_results[1].fetchall()

        return total, leads

    def get_top_regions(self, industry_id=None, country_id=None, limit=3):
        """
        Top countries by lead frequency among propensity-qualified
        leads, mirroring the same filter logic as the ideal
        snapshot proc. Kept as a plain query (not a stored proc)
        so it doesn't require a DB migration.
        """

        sql = """
        SELECT
            loc.Location_desc AS region,
            COUNT(*) AS frequency,
            ROUND(
                (COUNT(*) * 100.0) / (
                    SELECT COUNT(*)
                    FROM tblleads_masterlist lm2
                    JOIN vw_propensity_qualified_leads pq2
                        ON pq2.Lead_id = lm2.Lead_id
                    WHERE
                        (%(country_id)s IS NULL OR lm2.Country_id = %(country_id)s)
                        AND (%(industry_id)s IS NULL OR lm2.Standard_industry_id = %(industry_id)s)
                ),
                2
            ) AS percentage
        FROM tblleads_masterlist lm
        JOIN vw_propensity_qualified_leads pq
            ON pq.Lead_id = lm.Lead_id
        JOIN Mst_tbllocationelements loc
            ON loc.Location_id = lm.Country_id
        WHERE
            (%(country_id)s IS NULL OR lm.Country_id = %(country_id)s)
            AND (%(industry_id)s IS NULL OR lm.Standard_industry_id = %(industry_id)s)
        GROUP BY loc.Location_desc
        ORDER BY frequency DESC
        LIMIT %(limit)s
        """

        self.cursor.execute(
            sql,
            {
                "country_id": country_id,
                "industry_id": industry_id,
                "limit": limit
            }
        )

        return self.cursor.fetchall()

    # ----------------------------------------------------
    # STEP 7
    # Orchestrate the full ICP discovery pipeline
    # ----------------------------------------------------

    def discover_icp(
        self,
        user_id,
        product_override=None,
        country_id=None,
        industry_id=None,
        brand_id=None,
        page=1,
        page_size=20
    ):

        product = product_override or self.get_selected_product(user_id)

        product_analysis = analyze_product(product)

        similar_brands = product_analysis.get("competitor_brands", [])

        matched_clients = self.get_client_ids(similar_brands)

        campaigns = self.get_campaigns(matched_clients)

        ideal_snapshot = self.get_ideal_snapshot(
            industry_id=industry_id,
            brand_id=brand_id,
            country_id=country_id
        )

        top_regions = self.get_top_regions(
            industry_id=industry_id,
            country_id=country_id
        )

        # Only the COUNT is used — raw lead-level details
        # (names, titles, companies) must never be returned
        # to the caller. Insights only.
        total_leads, _raw_leads = self.get_filtered_leads(
            country_id=country_id,
            industry_id=industry_id,
            page=page,
            page_size=page_size
        )

        icp_insight = generate_icp_insight(
            product_analysis=product_analysis,
            ideal_snapshot=ideal_snapshot,
            top_regions=top_regions,
            total_leads=total_leads,
            campaign_count=len(campaigns),
            client_count=len(matched_clients)
        )

        return {
            "selected_product": product,
            "product_analysis": product_analysis,
            "matched_brands": similar_brands,
            "total_matched_clients": len(matched_clients),
            "total_campaigns": len(campaigns),
            "total_leads": total_leads,
            "icp_insight": icp_insight
        }

    def close(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception:
            pass