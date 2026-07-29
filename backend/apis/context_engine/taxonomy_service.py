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


# -----------------------------
# INDUSTRIES
# -----------------------------
def get_industries():

    query = """
        SELECT DISTINCT Standard_industry_desc
        FROM Mst_tblstandardindustry
        WHERE Isactive = 1
        ORDER BY Standard_industry_desc
        Limit 5
    """

    return fetch_column_values(query)


# -----------------------------
# SECTORS (DOMAIN)
# -----------------------------
def get_industry_domains():

    query = """
        SELECT DISTINCT domain
        FROM mst_industry_taxonomy
        WHERE domain IS NOT NULL
        ORDER BY domain
    """

    return fetch_column_values(query)


# -----------------------------
# SECTORS BY INDUSTRY (OPTIONAL FILTER)
# -----------------------------
def get_industry_domains_by_industry(industry):

    query = """
        SELECT DISTINCT industry
        FROM mst_industry_taxonomy
        WHERE industry = %s
        AND secto IS NOT NULL
        ORDER BY sector
    """

    return fetch_column_values(query, (industry,))
# =========================================
# JOB FUNCTIONS
# =========================================

def get_job_functions():

    query = """
        SELECT DISTINCT Jobfunction_desc
        FROM Mst_tbljobfunction
        WHERE Isactive = 1
        ORDER BY Jobfunction_desc
    """

    return fetch_column_values(query)


# =========================================
# JOB LEVELS
# =========================================

def get_job_levels():

    query = """
        SELECT DISTINCT Job_level_desc
        FROM Mst_tbljoblevel
        WHERE Isactive = 1
        ORDER BY Job_level_desc
    """

    return fetch_column_values(query)


# =========================================
# EMPLOYEE SIZES
# =========================================

def get_employee_sizes():

     query = """
        SELECT DISTINCT Employee_size_desc
        FROM Mst_tblemployeesize
        WHERE Isactive = 1
        ORDER BY Employee_size_desc
    """

     return fetch_column_values(query)


# =========================================
# REVENUE RANGES
# =========================================

def get_revenue_ranges():

     query = """
        SELECT DISTINCT Revenue_size_desc
        FROM Mst_tblrevenuesize
        WHERE Isactive = 1
        ORDER BY Revenue_size_desc
    """

     return fetch_column_values(query)


# =========================================
# GEOGRAPHY VALIDATION
# =========================================

def is_valid_geography(value):

    conn = get_conn()
    cursor = conn.cursor()

    try:

        query = """
            SELECT 1
            FROM Mst_tbllocationelements
            WHERE LOWER(Location_desc) = %s
            LIMIT 5
        """

        cursor.execute(
            query,
            (value.lower(),)
        )

        result = cursor.fetchone()

        return result is not None

    finally:

        cursor.close()
        conn.close()