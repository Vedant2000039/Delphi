# taxonomy_loader.py
from .taxonomy_service import (
    get_industries,
    get_job_functions,
    get_job_levels,
    get_employee_sizes,
    get_revenue_ranges,          # ← was get_revenue_sizes (typo in original)
)

TAXONOMY = {
    "industry":       get_industries(),
    "job_function":   get_job_functions(),
    "job_level":      get_job_levels(),
    "employee_size":  get_employee_sizes(),
    "revenue_range":  get_revenue_ranges(),   # ← fixed key name
}