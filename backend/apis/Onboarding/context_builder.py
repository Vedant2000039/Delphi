"""
backend/apis/Onboarding/context_builder.py

Context Builder API
--------------------------------------------------------------------------
Collects product/service-specific targeting context (product, geography,
industry, category, target audience) between Website Scraping and the
Intelligence Dashboard in the onboarding flow.

Industry -> Category -> Domain are all sourced from the single
`mst_industry_taxonomy` table (cascading distinct queries):

    SELECT DISTINCT industry FROM mst_industry_taxonomy WHERE is_active = 1;
    SELECT DISTINCT category FROM mst_industry_taxonomy WHERE industry IN (...) AND is_active = 1;
    SELECT DISTINCT domain   FROM mst_industry_taxonomy WHERE category IN (...) AND is_active = 1;

Exposes:
    GET  /context-builder/items/{user_id}
    GET  /context-builder/geographies
    GET  /context-builder/industries
    POST /context-builder/categories
    POST /context-builder/domains
    POST /context-builder/save
    GET  /context-builder/context/{user_id}

Uses a pooled MySQL connector, parameterized queries, and Pydantic models
for request validation.
--------------------------------------------------------------------------
"""

import os
import json
import logging
from typing import List, Optional

import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logger = logging.getLogger("delphi.context_builder")
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------
# Database connection pool
# --------------------------------------------------------------------------

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "delphi"),
}

try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="context_builder_pool",
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        **DB_CONFIG,
    )
except MySQLError as exc:
    # Defer the hard failure to request time so the app can still boot
    # (e.g. during local dev when the DB isn't up yet).
    connection_pool = None
    logger.error("Failed to initialize MySQL connection pool: %s", exc)


def get_db_connection():
    """
    Returns a pooled MySQL connection.
    Raises HTTPException(503) if the pool is unavailable or exhausted.
    """
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = pooling.MySQLConnectionPool(
                pool_name="context_builder_pool",
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                **DB_CONFIG,
            )
        except MySQLError as exc:
            logger.error("MySQL pool re-initialization failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is currently unavailable. Please try again shortly.",
            )
    try:
        return connection_pool.get_connection()
    except MySQLError as exc:
        logger.error("Failed to acquire DB connection: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is currently unavailable. Please try again shortly.",
        )


# --------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------

router = APIRouter(prefix="/context-builder", tags=["Context Builder"])


# --------------------------------------------------------------------------
# Pydantic Models
# --------------------------------------------------------------------------

class ProductServiceItemsResponse(BaseModel):
    company_type: Optional[str] = None
    items: List[str] = Field(default_factory=list)


class GeographyItem(BaseModel):
    Location_id: int
    Location_desc: str


class GeographiesResponse(BaseModel):
    geographies: List[GeographyItem] = Field(default_factory=list)


class IndustriesResponse(BaseModel):
    """
    Industries are plain distinct strings from mst_industry_taxonomy.industry
    (this table has no surrogate id for industry - just the text column).
    """
    industries: List[str] = Field(default_factory=list)


class CategoriesRequest(BaseModel):
    industries: List[str] = Field(default_factory=list)

    @field_validator("industries")
    @classmethod
    def validate_industries(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("At least one industry must be provided.")
        return value


class CategoriesResponse(BaseModel):
    categories: List[str] = Field(default_factory=list)


class DomainsRequest(BaseModel):
    categories: List[str] = Field(default_factory=list)

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("At least one category must be provided.")
        return value


class DomainsResponse(BaseModel):
    domains: List[str] = Field(default_factory=list)


class SaveContextRequest(BaseModel):
    user_id: int
    selected_product: Optional[str] = None
    selected_service: Optional[str] = None
    geographies: List[int] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)

    @field_validator("geographies", "industries", "categories", "domains")
    @classmethod
    def validate_non_empty_list(cls, value):
        if not value:
            raise ValueError("This field must contain at least one selection.")
        return value

    @field_validator("selected_service")
    @classmethod
    def validate_product_or_service(cls, value, info):
        product = info.data.get("selected_product")
        if not product and not value:
            raise ValueError(
                "Either selected_product or selected_service must be provided."
            )
        return value


class SavedContextResponse(BaseModel):
    """Shape returned when reading back a user's saved context."""
    user_id: int
    selected_product: Optional[str] = None
    selected_service: Optional[str] = None
    geographies: List[int] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)


class SaveContextResponse(BaseModel):
    success: bool
    message: str
    context_id: Optional[int] = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _split_csv(value: Optional[str]) -> List[str]:
    """Splits a comma-separated string into a clean list, dropping blanks."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@router.get("/items/{user_id}", response_model=ProductServiceItemsResponse)
def get_product_or_service_items(user_id: int):
    """
    Returns the list of brands (Product Based Company) or services
    (Service Based Company) associated with the given user's company profile.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT brands, services, company_type
            FROM delphi_company_profiles
            WHERE user_id = %s
            LIMIT 1
        """
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No company profile found for this user.",
            )

        company_type = row.get("company_type")

        if company_type == "Product Based Company":
            items = _split_csv(row.get("brands"))
        elif company_type == "Service Based Company":
            items = _split_csv(row.get("services"))
        else:
            logger.warning(
                "Unrecognized company_type '%s' for user_id=%s", company_type, user_id
            )
            items = []

        return ProductServiceItemsResponse(company_type=company_type, items=items)

    except MySQLError as exc:
        logger.error("Database error in get_product_or_service_items: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products or services. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@router.get("/geographies", response_model=GeographiesResponse)
def get_geographies():
    """Returns all active countries available for targeting."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT Location_id, Location_desc
            FROM Mst_tbllocationelements
            WHERE Location_type = %s AND Isactive = 1
            ORDER BY Location_desc
        """
        cursor.execute(query, ("Country",))
        rows = cursor.fetchall()
        return GeographiesResponse(geographies=rows)

    except MySQLError as exc:
        logger.error("Database error in get_geographies: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch geographies. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@router.get("/industries", response_model=IndustriesResponse)
def get_industries():
    """
    Returns all distinct active industries from mst_industry_taxonomy.

    Equivalent to:
        SELECT DISTINCT industry FROM mst_industry_taxonomy
        WHERE is_active = 1
        ORDER BY industry;
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT DISTINCT industry
            FROM mst_industry_taxonomy
            WHERE is_active = 1
            ORDER BY industry
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        industries = [row["industry"] for row in rows if row.get("industry")]
        return IndustriesResponse(industries=industries)

    except MySQLError as exc:
        logger.error("Database error in get_industries: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch industries. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@router.post("/categories", response_model=CategoriesResponse)
def get_categories(payload: CategoriesRequest):
    """
    Returns distinct active categories for the given industries.

    Equivalent to:
        SELECT DISTINCT category FROM mst_industry_taxonomy
        WHERE industry IN (...) AND is_active = 1
        ORDER BY category;
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        placeholders = ", ".join(["%s"] * len(payload.industries))
        query = f"""
            SELECT DISTINCT category
            FROM mst_industry_taxonomy
            WHERE industry IN ({placeholders})
              AND is_active = 1
            ORDER BY category
        """
        cursor.execute(query, tuple(payload.industries))
        rows = cursor.fetchall()
        categories = [row["category"] for row in rows if row.get("category")]
        return CategoriesResponse(categories=categories)

    except MySQLError as exc:
        logger.error("Database error in get_categories: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@router.post("/domains", response_model=DomainsResponse)
def get_domains(payload: DomainsRequest):
    """
    Returns distinct active domains for the given categories.

    Equivalent to:
        SELECT DISTINCT domain FROM mst_industry_taxonomy
        WHERE category IN (...) AND is_active = 1
        ORDER BY domain;
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        placeholders = ", ".join(["%s"] * len(payload.categories))
        query = f"""
            SELECT DISTINCT domain
            FROM mst_industry_taxonomy
            WHERE category IN ({placeholders})
              AND is_active = 1
            ORDER BY domain
        """
        cursor.execute(query, tuple(payload.categories))
        rows = cursor.fetchall()
        domains = [row["domain"] for row in rows if row.get("domain")]
        return DomainsResponse(domains=domains)

    except MySQLError as exc:
        logger.error("Database error in get_domains: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch target audience options. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@router.post("/save", response_model=SaveContextResponse, status_code=status.HTTP_201_CREATED)
def save_context(payload: SaveContextRequest):
    """
    Persists the user's full context builder selections
    (product/service, geographies, industries, categories, domains).

    Upserts on user_id: re-running the wizard overwrites the user's
    previous selections rather than creating duplicate history rows.
    Requires the ` delphi_context_builder_user_selections` table to already
    exist - see backend/migrations/create_ delphi_context_builder_user_selections.sql.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        upsert_query = """
            INSERT INTO  delphi_context_builder_user_selections (
                user_id,
                selected_product,
                selected_service,
                geographies,
                industries,
                categories,
                domains
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                selected_product = VALUES(selected_product),
                selected_service = VALUES(selected_service),
                geographies      = VALUES(geographies),
                industries       = VALUES(industries),
                categories       = VALUES(categories),
                domains          = VALUES(domains),
                updated_at       = CURRENT_TIMESTAMP
        """
        cursor.execute(
            upsert_query,
            (
                payload.user_id,
                payload.selected_product,
                payload.selected_service,
                json.dumps(payload.geographies),
                json.dumps(payload.industries),
                json.dumps(payload.categories),
                json.dumps(payload.domains),
            ),
        )
        connection.commit()

        # lastrowid is 0 on an UPDATE branch of an upsert; fall back to
        # looking the row's id up explicitly so the response is always populated.
        context_id = cursor.lastrowid
        if not context_id:
            cursor.execute(
                "SELECT id FROM  delphi_context_builder_user_selections WHERE user_id = %s",
                (payload.user_id,),
            )
            row = cursor.fetchone()
            context_id = row[0] if row else None

        return SaveContextResponse(
            success=True,
            message="Context saved successfully.",
            context_id=context_id,
        )

    except MySQLError as exc:
        connection.rollback()
        logger.error("Database error in save_context: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save your context. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@router.get("/context/{user_id}", response_model=SavedContextResponse)
def get_saved_context(user_id: int):
    """
    Returns a user's previously saved context builder selections.
    Used by downstream features (Intelligence Dashboard, ICP generation,
    campaign recommendations, etc.) that need the user's targeting context.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, selected_product, selected_service,
                   geographies, industries, categories, domains
            FROM  delphi_context_builder_user_selections
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No saved context found for this user.",
            )

        return SavedContextResponse(
            user_id=row["user_id"],
            selected_product=row["selected_product"],
            selected_service=row["selected_service"],
            geographies=json.loads(row["geographies"]),
            industries=json.loads(row["industries"]),
            categories=json.loads(row["categories"]),
            domains=json.loads(row["domains"]),
        )

    except MySQLError as exc:
        logger.error("Database error in get_saved_context: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved context. Please try again.",
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()