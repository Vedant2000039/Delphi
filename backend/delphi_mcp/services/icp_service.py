# import mysql.connector

# try:
#     from config import MYSQL_CONFIG
# except ImportError:
#     from ..config import MYSQL_CONFIG

# from .brand_matcher import find_similar_brands_llm, analyze_product
# from .insight_generator import generate_icp_insight


# class ICPService:

#     def __init__(self):
#         self.conn = mysql.connector.connect(**MYSQL_CONFIG)
#         self.cursor = self.conn.cursor(dictionary=True)

#     # ----------------------------------------------------
#     # STEP 1
#     # Get user's selected product
#     # ----------------------------------------------------

#     def get_selected_product(self, user_id):

#         sql = """
#         SELECT
#             selected_product
#         FROM delphi_context_builder_user_selections
#         WHERE user_id=%s
#         """

#         self.cursor.execute(sql, (user_id,))
#         row = self.cursor.fetchone()

#         if not row:
#             raise Exception("No context found for user.")

#         return row["selected_product"]

#     # ----------------------------------------------------
#     # Product / service options for the "choose what to
#     # analyze" screen — combines the user's originally
#     # selected product/service with everything detected
#     # from their company profile (brands + services).
#     # ----------------------------------------------------

#     def get_product_options(self, user_id):

#         sql = """
#         SELECT
#             selected_product,
#             selected_service
#         FROM delphi_context_builder_user_selections
#         WHERE user_id=%s
#         """
#         self.cursor.execute(sql, (user_id,))
#         context_row = self.cursor.fetchone() or {}

#         sql = """
#         SELECT
#             brands,
#             services
#         FROM delphi_company_profiles
#         WHERE user_id=%s
#         ORDER BY updated_at DESC
#         LIMIT 1
#         """
#         self.cursor.execute(sql, (user_id,))
#         profile_row = self.cursor.fetchone() or {}

#         def _split(raw):
#             if not raw:
#                 return []
#             # brands/services are stored as free text — support
#             # comma-separated or JSON array either way.
#             raw = raw.strip()
#             if raw.startswith("["):
#                 try:
#                     import json
#                     return [str(x).strip() for x in json.loads(raw) if str(x).strip()]
#                 except Exception:
#                     pass
#             return [x.strip() for x in raw.split(",") if x.strip()]

#         detected_products = _split(profile_row.get("brands"))
#         detected_services = _split(profile_row.get("services"))

#         selected_product = context_row.get("selected_product")
#         selected_service = context_row.get("selected_service")

#         # Merge without duplicates, keeping the originally
#         # selected item first so the UI can default to it.
#         all_options = []

#         for item in [selected_product] + detected_products:
#             if item and item not in all_options:
#                 all_options.append(item)

#         for item in [selected_service] + detected_services:
#             if item and item not in all_options:
#                 all_options.append(item)

#         return {
#             "selected_product": selected_product,
#             "selected_service": selected_service,
#             "options": all_options
#         }

#     # ----------------------------------------------------
#     # STEP 2
#     # Compare product against CRM brands using an LLM.
#     # Falls back silently to a hardcoded mapping inside
#     # brand_matcher.py if OpenAI is unavailable or errors.
#     # ----------------------------------------------------

#     def find_similar_brands(self, product):

#         return find_similar_brands_llm(product)

#     # ----------------------------------------------------
#     # STEP 3
#     # Find matching CRM clients for the matched brands
#     # ----------------------------------------------------

#     def get_client_ids(self, brands):

#         if not brands:
#             return []

#         placeholders = ",".join(["%s"] * len(brands))

#         sql = f"""
#         SELECT
#             Client_id,
#             Brand_name
#         FROM Mst_tblclient_brands
#         WHERE Brand_name IN ({placeholders})
#             AND Isactive = 1
#         """

#         self.cursor.execute(sql, brands)

#         return self.cursor.fetchall()

#     # ----------------------------------------------------
#     # STEP 4
#     # Find campaigns tied to those clients
#     # ----------------------------------------------------

#     def get_campaigns(self, client_rows):

#         if not client_rows:
#             return []

#         ids = [row["Client_id"] for row in client_rows]

#         placeholders = ",".join(["%s"] * len(ids))

#         sql = f"""
#         SELECT
#             Campaign_key_id,
#             Campaign_desc,
#             Client_id
#         FROM Mst_tblclient_campaigns
#         WHERE Client_id IN ({placeholders})
#             AND Isactive = 1
#         """

#         self.cursor.execute(sql, ids)

#         return self.cursor.fetchall()

#     # ----------------------------------------------------
#     # STEP 5 / 6
#     # Run existing stored procedures for ICP analysis
#     # ----------------------------------------------------

#     def get_ideal_snapshot(self, industry_id=None, brand_id=None, country_id=None):
#         """
#         Calls Usp_get_icp_ideal_snapshot.
#         Actual procedure signature (confirmed via
#         INFORMATION_SCHEMA.PARAMETERS) is:
#             1. p_industry_id
#             2. p_brand_id
#             3. p_country_id
#         Returns 4 result sets (Employee Size, Revenue Size,
#         Job Level, Job Function) merged into a single list.
#         """

#         args = (industry_id, brand_id, country_id)

#         self.cursor.callproc(
#             "Usp_get_icp_ideal_snapshot",
#             args
#         )

#         snapshot = []

#         for result in self.cursor.stored_results():
#             snapshot.extend(result.fetchall())

#         return snapshot

#     def get_filtered_leads(
#         self,
#         country_id=None,
#         industry_id=None,
#         employee_size_id=None,
#         revenue_size_id=None,
#         job_level_id=None,
#         job_function_id=None,
#         page=1,
#         page_size=20
#     ):
#         """
#         Calls Usp_get_icp_filtered_leads.
#         Returns (total_count, leads_list).
#         """

#         args = (
#             country_id,
#             industry_id,
#             employee_size_id,
#             revenue_size_id,
#             job_level_id,
#             job_function_id,
#             page,
#             page_size
#         )

#         self.cursor.callproc(
#             "Usp_get_icp_filtered_leads",
#             args
#         )

#         stored_results = list(self.cursor.stored_results())

#         total = 0
#         leads = []

#         if len(stored_results) >= 1:
#             count_row = stored_results[0].fetchone()
#             if count_row:
#                 total = count_row.get("total", 0)

#         if len(stored_results) >= 2:
#             leads = stored_results[1].fetchall()

#         return total, leads

#     def get_top_regions(self, industry_id=None, country_id=None, limit=3):
#         """
#         Top countries by lead frequency among propensity-qualified
#         leads, mirroring the same filter logic as the ideal
#         snapshot proc. Kept as a plain query (not a stored proc)
#         so it doesn't require a DB migration.
#         """

#         sql = """
#         SELECT
#             loc.Location_desc AS region,
#             COUNT(*) AS frequency,
#             ROUND(
#                 (COUNT(*) * 100.0) / (
#                     SELECT COUNT(*)
#                     FROM tblleads_masterlist lm2
#                     JOIN vw_propensity_qualified_leads pq2
#                         ON pq2.Lead_id = lm2.Lead_id
#                     WHERE
#                         (%(country_id)s IS NULL OR lm2.Country_id = %(country_id)s)
#                         AND (%(industry_id)s IS NULL OR lm2.Standard_industry_id = %(industry_id)s)
#                 ),
#                 2
#             ) AS percentage
#         FROM tblleads_masterlist lm
#         JOIN vw_propensity_qualified_leads pq
#             ON pq.Lead_id = lm.Lead_id
#         JOIN Mst_tbllocationelements loc
#             ON loc.Location_id = lm.Country_id
#         WHERE
#             (%(country_id)s IS NULL OR lm.Country_id = %(country_id)s)
#             AND (%(industry_id)s IS NULL OR lm.Standard_industry_id = %(industry_id)s)
#         GROUP BY loc.Location_desc
#         ORDER BY frequency DESC
#         LIMIT %(limit)s
#         """

#         self.cursor.execute(
#             sql,
#             {
#                 "country_id": country_id,
#                 "industry_id": industry_id,
#                 "limit": limit
#             }
#         )

#         return self.cursor.fetchall()

#     # ----------------------------------------------------
#     # STEP 7
#     # Orchestrate the full ICP discovery pipeline
#     # ----------------------------------------------------

#     def discover_icp(
#         self,
#         user_id,
#         product_override=None,
#         country_id=None,
#         industry_id=None,
#         brand_id=None,
#         page=1,
#         page_size=20
#     ):

#         product = product_override or self.get_selected_product(user_id)

#         product_analysis = analyze_product(product)

#         similar_brands = product_analysis.get("competitor_brands", [])

#         matched_clients = self.get_client_ids(similar_brands)

#         campaigns = self.get_campaigns(matched_clients)

#         ideal_snapshot = self.get_ideal_snapshot(
#             industry_id=industry_id,
#             brand_id=brand_id,
#             country_id=country_id
#         )

#         top_regions = self.get_top_regions(
#             industry_id=industry_id,
#             country_id=country_id
#         )

#         # Only the COUNT is used — raw lead-level details
#         # (names, titles, companies) must never be returned
#         # to the caller. Insights only.
#         total_leads, _raw_leads = self.get_filtered_leads(
#             country_id=country_id,
#             industry_id=industry_id,
#             page=page,
#             page_size=page_size
#         )

#         icp_insight = generate_icp_insight(
#             product_analysis=product_analysis,
#             ideal_snapshot=ideal_snapshot,
#             top_regions=top_regions,
#             total_leads=total_leads,
#             campaign_count=len(campaigns),
#             client_count=len(matched_clients)
#         )

#         return {
#             "selected_product": product,
#             "product_analysis": product_analysis,
#             "matched_brands": similar_brands,
#             "total_matched_clients": len(matched_clients),
#             "total_campaigns": len(campaigns),
#             "total_leads": total_leads,
#             "icp_insight": icp_insight
#         }

#     def close(self):
#         try:
#             self.cursor.close()
#             self.conn.close()
#         except Exception:
#             pass


#################################################
import mysql.connector
import json
import logging

logger = logging.getLogger("icp_service")

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
            selected_product,
            selected_type
        FROM delphi_selected_product_context
        WHERE user_id=%s
        """

        self.cursor.execute(sql, (user_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        return row.get("selected_product")

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
            selected_type
        FROM delphi_selected_product_context
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

        # delphi_selected_product_context holds ONE currently-selected
        # value + its type ("product" | "brand" | "service") — it's the
        # single source of truth the sidebar switcher writes to. Split
        # it back into selected_product / selected_service so the rest
        # of this response shape stays unchanged for the frontend.
        raw_selected_value = context_row.get("selected_product")
        raw_selected_type = (context_row.get("selected_type") or "").lower()

        selected_product = raw_selected_value if raw_selected_type != "service" else None
        selected_service = raw_selected_value if raw_selected_type == "service" else None

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
    # ----------------------------------------------------

    def find_similar_brands(self, product):

        return find_similar_brands_llm(product)

    # ----------------------------------------------------
    # STEP 3
    # Find matching CRM clients + brand_ids for the matched
    # brand names. Brand_id is selected explicitly here — it's
    # required by the new single-parameter version of
    # Usp_get_icp_ideal_snapshot below.
    # ----------------------------------------------------

    def get_client_ids(self, brands):

        if not brands:
            return []

        placeholders = ",".join(["%s"] * len(brands))

        sql = f"""
        SELECT
            Brand_id,
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

        ids = list({row["Client_id"] for row in client_rows if row.get("Client_id")})

        if not ids:
            return []

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

    def get_ideal_snapshot(self, brand_id=None):
        """
        Calls Usp_get_icp_ideal_snapshot.

        THIS PROC NOW TAKES EXACTLY 1 PARAMETER: p_brand_id.
        Do NOT pass industry_id / country_id here — the proc
        does not accept them (confirmed by the proc body: only
        p_brand_id is referenced anywhere in it). Passing extra
        args raises:
            1318 (42000): Incorrect number of arguments for
            PROCEDURE ...Usp_get_icp_ideal_snapshot; expected 1, got 3

        Returns 4 result sets (Employee Size, Revenue Size,
        Job Level, Job Function) merged into a single list.
        """

        self.cursor.callproc(
            "Usp_get_icp_ideal_snapshot",
            (brand_id,)
        )

        snapshot = []

        for result in self.cursor.stored_results():
            snapshot.extend(result.fetchall())

        return snapshot

    def get_ideal_snapshot_merged(self, brand_ids):
        """
        A product can match multiple CRM brands. Runs
        Usp_get_icp_ideal_snapshot per matched brand_id and merges
        rows across brands, summing frequency for identical
        (parameter, ideal_value) combinations and recomputing
        percentage across the merged total_leads.

        Returns [] if brand_ids is empty — callers must treat
        that as "no CRM overlap for this product."
        """

        if not brand_ids:
            return []

        merged = {}
        total_leads_by_param = {}

        for brand_id in brand_ids:
            rows = self.get_ideal_snapshot(brand_id=brand_id)

            for row in rows:
                param = row.get("parameter")
                value = row.get("ideal_value")
                freq = row.get("frequency") or 0
                total = row.get("total_leads") or 0

                key = (param, value)
                merged[key] = merged.get(key, 0) + freq
                total_leads_by_param[param] = max(total_leads_by_param.get(param, 0), total)

        result = []
        for (param, value), freq in merged.items():
            total = total_leads_by_param.get(param, 0)
            pct = round((freq * 100.0 / total), 2) if total else 0
            result.append({
                "parameter": param,
                "ideal_value": value,
                "frequency": freq,
                "total_leads": total,
                "percentage": pct
            })

        by_param = {}
        for row in result:
            by_param.setdefault(row["parameter"], []).append(row)

        final = []
        for param, rows in by_param.items():
            rows.sort(key=lambda r: r["frequency"], reverse=True)
            final.extend(rows[:3])

        return final

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
        leads. Plain query, unaffected by the ideal_snapshot proc
        change.
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
    # Orchestrate the full ICP discovery pipeline.
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

        if not product:
            return {
                "selected_product": None,
                "product_analysis": {},
                "matched_brands": [],
                "matched_brand_ids": [],
                "has_crm_overlap": False,
                "total_matched_clients": 0,
                "total_campaigns": 0,
                "total_leads": 0,
                "icp_insight": None,
                "error": "no_product_selected",
                "message": "No product or service has been selected for this account yet."
            }

        product_analysis = analyze_product(product)

        similar_brands = product_analysis.get("competitor_brands", [])

        matched_clients = self.get_client_ids(similar_brands)

        campaigns = self.get_campaigns(matched_clients)

        matched_brand_ids = list({
            row["Brand_id"] for row in matched_clients if row.get("Brand_id")
        })

        effective_brand_ids = [brand_id] if brand_id else matched_brand_ids

        has_crm_overlap = bool(effective_brand_ids)

        if has_crm_overlap:
            ideal_snapshot = self.get_ideal_snapshot_merged(brand_ids=effective_brand_ids)
        else:
            ideal_snapshot = []

        top_regions = self.get_top_regions(
            industry_id=industry_id,
            country_id=country_id
        )

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

        # Persist the resolved brand scope so Buyer Group discovery can
        # reuse it directly instead of re-running brand-matching. Buyer
        # Group must always be scoped to the SAME brands the ICP was
        # built from, not an independently re-derived set.
        self._save_matched_brand_context(
            user_id=user_id,
            product=product,
            matched_brands=similar_brands,
            matched_brand_ids=effective_brand_ids
        )

        return {
            "selected_product": product,
            "product_analysis": product_analysis,
            "matched_brands": similar_brands,
            "matched_brand_ids": effective_brand_ids,
            "has_crm_overlap": has_crm_overlap,
            "total_matched_clients": len(matched_clients),
            "total_campaigns": len(campaigns),
            "total_leads": total_leads,
            "icp_insight": icp_insight
        }

    def _save_matched_brand_context(self, user_id, product, matched_brands, matched_brand_ids):
        """
        UPSERTs the last-resolved brand scope for this user so
        BuyerGroupService can read it back instead of recomputing it
        via find_similar_brands_llm on every Buyer Group call.
        """

        sql = """
        INSERT INTO delphi_icp_brand_context
            (user_id, product, matched_brands, matched_brand_ids, updated_at)
        VALUES
            (%s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            product = VALUES(product),
            matched_brands = VALUES(matched_brands),
            matched_brand_ids = VALUES(matched_brand_ids),
            updated_at = NOW()
        """

        try:
            self.cursor.execute(
                sql,
                (
                    user_id,
                    product,
                    json.dumps(matched_brands or []),
                    json.dumps(matched_brand_ids or [])
                )
            )
            # MYSQL_CONFIG sets autocommit=True for this connection, but
            # commit explicitly anyway in case that ever changes.
            self.conn.commit()

        except Exception as e:
            # Don't let context-caching failures break ICP discovery,
            # but DO surface the reason instead of failing silently —
            # this is exactly what was hiding the "no rows" issue.
            logger.error(
                "Failed to save matched_brand_context for user_id=%s: %s",
                user_id, e
            )

    def close(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Exception:
            pass