# taxonomy_service.py

# =========================================
# INDUSTRIES
# =========================================

def get_industries():
    return [
        "Information Technology",
        "Healthcare",
        "Financial Services",
        "Manufacturing",
        "Retail"
    ]


# =========================================
# SECTORS (DOMAIN)
# =========================================

def get_industry_domains():
    return [
        "Software",
        "Cloud Computing",
        "Cyber Security",
        "Artificial Intelligence",
        "Data Analytics"
    ]


# =========================================
# SECTORS BY INDUSTRY
# =========================================

def get_industry_domains_by_industry(industry):

    mapping = {
        "Information Technology": [
            "Software",
            "Cloud Computing",
            "Cyber Security"
        ],
        "Healthcare": [
            "Hospitals",
            "Medical Devices",
            "Pharmaceuticals"
        ],
        "Financial Services": [
            "Banking",
            "Insurance",
            "FinTech"
        ]
    }

    return mapping.get(industry, [])


# =========================================
# JOB FUNCTIONS
# =========================================

def get_job_functions():
    return [
        "Engineering",
        "Sales",
        "Marketing",
        "Operations",
        "Human Resources"
    ]


# =========================================
# JOB LEVELS
# =========================================

def get_job_levels():
    return [
        "Entry Level",
        "Manager",
        "Director",
        "Vice President",
        "C-Level"
    ]


# =========================================
# EMPLOYEE SIZES
# =========================================

def get_employee_sizes():
    return [
        "1-10",
        "11-50",
        "51-200",
        "201-1000",
        "1000+"
    ]


# =========================================
# REVENUE RANGES
# =========================================

def get_revenue_ranges():
    return [
        "Under $1M",
        "$1M-$10M",
        "$10M-$100M",
        "$100M-$1B",
        "$1B+"
    ]


# =========================================
# GEOGRAPHY VALIDATION
# =========================================

def is_valid_geography(value):

    valid_locations = {
        "india",
        "united states",
        "usa",
        "canada",
        "united kingdom",
        "germany",
        "france",
        "australia",
        "pune",
        "mumbai",
        "nashik",
        "bangalore",
        "hyderabad",
        "delhi"
    }

    return value.lower().strip() in valid_locations