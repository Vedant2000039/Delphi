# ==============================================================================
# File: campaign_suggestions.py
#
# Description:
# Fetches industry and geography suggestions from the database.
# These suggestions are used to provide autocomplete options
# during the Campaign Suggestion workflow.
# ==============================================================================

from db import get_conn


# ==============================================================================
# Get Industry Suggestions
# ==============================================================================

def get_industry_suggestions(limit=12):
    """
    Fetches active industry names from the database.

    Parameters
    ----------
    limit : int
        Maximum number of industry suggestions to return.
    """

    # --------------------------------------------------------------------------
    # Create Database Connection
    # --------------------------------------------------------------------------

    conn = get_conn()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------------------------
        # Fetch Active Industries
        # ----------------------------------------------------------------------

        query = """
        SELECT Standard_industry_desc
        FROM Mst_tblstandardindustry
        WHERE Isactive = 1
        ORDER BY Standard_industry_desc
        LIMIT %s
        """

        cursor.execute(query, (limit,))

        rows = cursor.fetchall()

        # ----------------------------------------------------------------------
        # Return Industry List
        # ----------------------------------------------------------------------

        return [
            row[0]
            for row in rows
            if row[0]
        ]

    finally:

        # ----------------------------------------------------------------------
        # Close Database Resources
        # ----------------------------------------------------------------------

        cursor.close()
        conn.close()


# ==============================================================================
# Get Geography Suggestions
# ==============================================================================

def get_geography_suggestions(limit=15):
    """
    Fetches active country and region names from the database.

    Parameters
    ----------
    limit : int
        Maximum number of geography suggestions to return.
    """

    # --------------------------------------------------------------------------
    # Create Database Connection
    # --------------------------------------------------------------------------

    conn = get_conn()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------------------------
        # Fetch Active Countries and Regions
        # ----------------------------------------------------------------------

        query = """
        SELECT Location_desc
        FROM Mst_tbllocationelements
        WHERE Isactive = 1
          AND Location_type IN ('country', 'region')
        ORDER BY Location_desc
        LIMIT %s
        """

        cursor.execute(query, (limit,))

        rows = cursor.fetchall()

        # ----------------------------------------------------------------------
        # Return Geography List
        # ----------------------------------------------------------------------

        return [
            row[0]
            for row in rows
            if row[0]
        ]

    finally:

        # ----------------------------------------------------------------------
        # Close Database Resources
        # ----------------------------------------------------------------------

        cursor.close()
        conn.close()