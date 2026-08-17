"""
backend/apis/Intellegence/product_context.py
Single source of truth for "which product/service is currently selected"
+ cached product_analysis so ICP and Buyer Group never re-ask the user
and never re-run the LLM product analysis twice for the same product.
"""

import os, json, logging
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("delphi.product_context")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "delphi"),
}

try:
    _pool = pooling.MySQLConnectionPool(pool_name="product_context_pool", pool_size=5, **DB_CONFIG)
except MySQLError as exc:
    _pool = None
    logger.error("product_context pool init failed: %s", exc)


def _conn():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(pool_name="product_context_pool", pool_size=5, **DB_CONFIG)
        except MySQLError as exc:
            raise HTTPException(503, "Database unavailable.") from exc
    try:
        return _pool.get_connection()
    except MySQLError as exc:
        raise HTTPException(503, "Database unavailable.") from exc


router = APIRouter(prefix="/intellegence", tags=["Intellegence Context"])


def _ensure_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delphi_selected_product_context (
            user_id BIGINT PRIMARY KEY,
            selected_product VARCHAR(500),
            selected_type VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delphi_product_analysis_cache (
            user_id BIGINT PRIMARY KEY,
            product VARCHAR(500),
            product_analysis JSON,
            icp_insight JSON,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)


class SelectProductRequest(BaseModel):
    user_id: int
    product: str
    type: Optional[str] = None


@router.get("/product-options/{user_id}")
def get_product_options(user_id: int):
    conn = _conn()
    try:
        cursor = conn.cursor(dictionary=True)
        _ensure_tables(cursor)
        conn.commit()

        cursor.execute(
            "SELECT brands, services FROM delphi_company_profiles WHERE user_id=%s ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        )
        profile = cursor.fetchone() or {}

        def _split(raw):
            if not raw:
                return []
            raw = raw.strip()
            if raw.startswith("["):
                try:
                    return [str(x).strip() for x in json.loads(raw) if str(x).strip()]
                except Exception:
                    pass
            return [x.strip() for x in raw.split(",") if x.strip()]

        brands = _split(profile.get("brands"))
        services = _split(profile.get("services"))

        cursor.execute(
            "SELECT selected_product FROM delphi_selected_product_context WHERE user_id=%s", (user_id,)
        )
        sel_row = cursor.fetchone()
        selected = sel_row["selected_product"] if sel_row else None

        items = [{"value": b, "type": "product", "selected": b == selected} for b in brands]
        items += [{"value": s, "type": "service", "selected": s == selected} for s in services]

        return {
            "items": items,
            "selected": next((i for i in items if i["selected"]), None),
            "is_first_time": selected is None,
        }
    except MySQLError as exc:
        logger.error("get_product_options error: %s", exc)
        raise HTTPException(500, "Failed to fetch products/services.")
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


@router.post("/select-product")
def select_product(payload: SelectProductRequest):
    conn = _conn()
    try:
        cursor = conn.cursor()
        _ensure_tables(cursor)
        cursor.execute(
            """
            INSERT INTO delphi_selected_product_context (user_id, selected_product, selected_type)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                selected_product = VALUES(selected_product),
                selected_type    = VALUES(selected_type),
                updated_at       = CURRENT_TIMESTAMP
            """,
            (payload.user_id, payload.product, payload.type or "product"),
        )
        # switching product invalidates any cached analysis tied to a different product
        cursor.execute(
            "DELETE FROM delphi_product_analysis_cache WHERE user_id=%s AND product != %s",
            (payload.user_id, payload.product),
        )
        conn.commit()
        return {"success": True, "selected": payload.product}
    except MySQLError as exc:
        conn.rollback()
        logger.error("select_product error: %s", exc)
        raise HTTPException(500, "Failed to save your selection.")
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


@router.get("/selected-product/{user_id}")
def get_selected_product(user_id: int):
    conn = _conn()
    try:
        cursor = conn.cursor(dictionary=True)
        _ensure_tables(cursor)
        conn.commit()
        cursor.execute(
            "SELECT selected_product, selected_type FROM delphi_selected_product_context WHERE user_id=%s",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row or not row.get("selected_product"):
            return {"selected_product": None, "is_first_time": True}
        return {"selected_product": row["selected_product"], "selected_type": row["selected_type"], "is_first_time": False}
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


class SaveAnalysisRequest(BaseModel):
    user_id: int
    product: str
    product_analysis: dict
    icp_insight: Optional[dict] = None


@router.post("/save-product-analysis")
def save_product_analysis(payload: SaveAnalysisRequest):
    conn = _conn()
    try:
        cursor = conn.cursor()
        _ensure_tables(cursor)
        cursor.execute(
            """
            INSERT INTO delphi_product_analysis_cache (user_id, product, product_analysis, icp_insight)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                product = VALUES(product),
                product_analysis = VALUES(product_analysis),
                icp_insight = VALUES(icp_insight),
                updated_at = CURRENT_TIMESTAMP
            """,
            (payload.user_id, payload.product, json.dumps(payload.product_analysis),
             json.dumps(payload.icp_insight) if payload.icp_insight else None),
        )
        conn.commit()
        return {"success": True}
    except MySQLError as exc:
        conn.rollback()
        logger.error("save_product_analysis error: %s", exc)
        raise HTTPException(500, "Failed to cache product analysis.")
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


@router.get("/product-analysis/{user_id}")
def get_product_analysis(user_id: int):
    conn = _conn()
    try:
        cursor = conn.cursor(dictionary=True)
        _ensure_tables(cursor)
        conn.commit()
        cursor.execute(
            "SELECT product, product_analysis, icp_insight FROM delphi_product_analysis_cache WHERE user_id=%s",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {"cached": False}
        return {
            "cached": True,
            "product": row["product"],
            "product_analysis": json.loads(row["product_analysis"]) if row["product_analysis"] else None,
            "icp_insight": json.loads(row["icp_insight"]) if row["icp_insight"] else None,
        }
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


class AddProductRequest(BaseModel):
    user_id: int
    value: str
    type: Optional[str] = None


def get_profile(user_id: int):
    conn = _conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM delphi_company_profiles WHERE user_id=%s ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        )
        return cursor.fetchone() or {}
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


def update_profile_column(user_id: int, column: str, value: str):
    conn = _conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM delphi_company_profiles WHERE user_id=%s ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            row_id = row[0]
            cursor.execute(
                f"UPDATE delphi_company_profiles SET {column}=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (value, row_id),
            )
        else:
            cursor.execute(
                f"INSERT INTO delphi_company_profiles (user_id, {column}) VALUES (%s, %s)",
                (user_id, value),
            )
        conn.commit()
    except MySQLError as exc:
        conn.rollback()
        logger.error("update_profile_column error: %s", exc)
        raise HTTPException(500, "Failed to update company profile.")
    finally:
        if conn.is_connected():
            cursor.close(); conn.close()


@router.post("/add-product")
def add_product(payload: AddProductRequest):
    # payload: user_id, value, type ("product" | "brand" | "service")
    profile = get_profile(payload.user_id)
    column = "services" if payload.type == "service" else "brands"
    existing = [v.strip() for v in (profile.get(column) or "").split(",") if v.strip()]
    if payload.value not in existing:
        existing.append(payload.value)
        update_profile_column(payload.user_id, column, ", ".join(existing))
    return {"items": get_product_options(payload.user_id)["items"]}