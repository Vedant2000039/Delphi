# ==============================================================================
# File: campaign_profile.py
#
# Description:
# Fetches the logged-in user's company profile details from the
# delphi_company_profiles table. The returned data is used by
# Intelligence.js to display the available brands, services,
# and specialties without relying on localStorage.
# ==============================================================================

from __future__ import annotations

from db import get_conn


# ==============================================================================
# Get User Products
# ==============================================================================

def get_user_products(user_id: int) -> dict:
    """
    Fetches the latest company profile for the given user and returns
    the available brands, services, and specialties.

    Any NULL or empty value is returned as an empty list.
    """

    # --------------------------------------------------------------------------
    # Create Database Connection
    # --------------------------------------------------------------------------

    conn = get_conn()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------------------------
        # Fetch Latest Company Profile
        # ----------------------------------------------------------------------

        cursor.execute(
            """
            SELECT
                specialties,
                brands,
                services,
                company_name,
                company_type
            FROM delphi_company_profiles
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )

        row = cursor.fetchone()

        # ----------------------------------------------------------------------
        # Return Default Response If Profile Is Not Found
        # ----------------------------------------------------------------------

        if not row:
            return {
                "found": False,
                "company_name": None,
                "company_type": None,
                "brands": [],
                "services": [],
                "specialties": [],
            }

        specialties_raw, brands_raw, services_raw, company_name, company_type = row

        # ----------------------------------------------------------------------
        # Convert Comma-Separated Values Into Lists
        # ----------------------------------------------------------------------

        def _split(raw) -> list[str]:
            """
            Converts a comma-separated string into a list.
            Returns an empty list if the value is NULL or empty.
            """
            if not raw:
                return []

            return [
                item.strip()
                for item in str(raw).split(",")
                if item.strip()
            ]

        # ----------------------------------------------------------------------
        # Return Company Profile Details
        # ----------------------------------------------------------------------

        return {
            "found": True,
            "company_name": company_name or "",
            "company_type": company_type or "",
            "brands": _split(brands_raw),
            "services": _split(services_raw),
            "specialties": _split(specialties_raw),
        }

    finally:

        # ----------------------------------------------------------------------
        # Close Database Resources
        # ----------------------------------------------------------------------

        cursor.close()
        conn.close()