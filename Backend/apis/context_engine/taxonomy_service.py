# taxonomy_service.py
from db import get_conn


def fetch_column_values(query, params=None):

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute(query, params or ())
        rows = cursor.fetchall()

        return [
            str(row[0]).strip()
            for row in rows
            if row[0]
        ]

    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────────────────────
# INDUSTRIES
# ─────────────────────────────────────────────────────────────

def get_industries():

    query = """
        SELECT DISTINCT Standard_industry_desc
        FROM Mst_tblstandardindustry
        WHERE Isactive = 1
        ORDER BY Standard_industry_desc
        LIMIT 50
    """

    return fetch_column_values(query)


# ─────────────────────────────────────────────────────────────
# SECTORS / INDUSTRY DOMAIN
#
# The mst_industry_taxonomy table does not currently have a
# 'sector' column in this environment.  industry_domain is
# intentionally excluded from the active pipeline, so these
# functions return an empty list rather than hitting the DB.
# ─────────────────────────────────────────────────────────────

def get_industry_domains() -> list:
    return []


def get_industry_domains_by_industry(industry) -> list:
    return []


# ─────────────────────────────────────────────────────────────
# JOB FUNCTIONS
# ─────────────────────────────────────────────────────────────

def get_job_functions():

    query = """
        SELECT DISTINCT Jobfunction_desc
        FROM Mst_tbljobfunction
        WHERE Isactive = 1
        ORDER BY Jobfunction_desc
    """

    return fetch_column_values(query)


# ─────────────────────────────────────────────────────────────
# JOB LEVELS
# ─────────────────────────────────────────────────────────────

def get_job_levels():

    query = """
        SELECT DISTINCT Job_level_desc
        FROM Mst_tbljoblevel
        WHERE Isactive = 1
        ORDER BY Job_level_desc
    """

    return fetch_column_values(query)


# ─────────────────────────────────────────────────────────────
# EMPLOYEE SIZES
# ─────────────────────────────────────────────────────────────

def get_employee_sizes():

    query = """
        SELECT DISTINCT Employee_size_desc
        FROM Mst_tblemployeesize
        WHERE Isactive = 1
        ORDER BY Employee_size_desc
    """

    return fetch_column_values(query)


# ─────────────────────────────────────────────────────────────
# REVENUE RANGES
# ─────────────────────────────────────────────────────────────

def get_revenue_ranges():

    query = """
        SELECT DISTINCT Revenue_size_desc
        FROM Mst_tblrevenuesize
        WHERE Isactive = 1
        ORDER BY Revenue_size_desc
    """

    return fetch_column_values(query)


# ─────────────────────────────────────────────────────────────
# GEOGRAPHY VALIDATION
# ─────────────────────────────────────────────────────────────

def is_valid_geography(value):

    conn = get_conn()
    cursor = conn.cursor()

    try:
        query = """
            SELECT 1
            FROM Mst_tbllocationelements
            WHERE LOWER(Location_desc) = %s
            LIMIT 1
        """

        cursor.execute(query, (value.lower(),))
        result = cursor.fetchone()
        return result is not None

    finally:
        cursor.close()
        conn.close()