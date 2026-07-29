from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from db import get_conn
import json

router = APIRouter(prefix="/profile", tags=["Product Context"])


from fastapi import HTTPException

@router.get("/products/{user_id}")
def get_products(user_id: int):
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, company_name, brands, services, selected_flag
            FROM delphi_company_profiles
            WHERE user_id = %s
        """, (user_id,))

        rows = cur.fetchall()

        return rows

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()


class SelectProductRequest(BaseModel):
    user_id: int
    profile_id: int
    value: str
    type: str


@router.post("/products/select")
def select_product(payload: SelectProductRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE delphi_company_profiles
        SET selected_flag = 0
        WHERE user_id = %s
    """, (payload.user_id,))
    cur.execute("""
        UPDATE delphi_company_profiles
        SET selected_flag = 1, selected_value = %s, selected_type = %s
        WHERE id = %s AND user_id = %s
    """, (payload.value, payload.type, payload.profile_id, payload.user_id))
    conn.commit()
    cur.close(); conn.close()
    return {"status": "ok", "selected": {"profile_id": payload.profile_id, "value": payload.value, "type": payload.type}}


@router.get("/context/{user_id}")
def get_context(user_id: int):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT selected_product, selected_service, geographies, industries, categories, domains
        FROM delphi_context_builder_user_selections
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        return {"context": None}

    for f in ("geographies", "industries", "categories", "domains"):
        if isinstance(row.get(f), str):
            row[f] = json.loads(row[f])
    return {"context": row}


class ContextUpdateRequest(BaseModel):
    user_id: int
    selected_product: Optional[str] = None
    selected_service: Optional[str] = None
    geographies: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    domains: Optional[List[str]] = None


@router.post("/context/update")
def update_context(payload: ContextUpdateRequest):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM delphi_context_builder_user_selections WHERE user_id = %s", (payload.user_id,))
    exists = cur.fetchone()

    fields = {
        "selected_product": payload.selected_product,
        "selected_service": payload.selected_service,
        "geographies": json.dumps(payload.geographies) if payload.geographies is not None else None,
        "industries": json.dumps(payload.industries) if payload.industries is not None else None,
        "categories": json.dumps(payload.categories) if payload.categories is not None else None,
        "domains": json.dumps(payload.domains) if payload.domains is not None else None,
    }
    fields = {k: v for k, v in fields.items() if v is not None}

    if exists:
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        cur2 = conn.cursor()
        cur2.execute(
            f"UPDATE delphi_context_builder_user_selections SET {set_clause} WHERE user_id = %s",
            (*fields.values(), payload.user_id)
        )
        cur2.close()
    else:
        cols = ", ".join(["user_id"] + list(fields.keys()))
        placeholders = ", ".join(["%s"] * (len(fields) + 1))
        defaults = {"geographies": "[]", "industries": "[]", "categories": "[]", "domains": "[]"}
        for k, v in defaults.items():
            fields.setdefault(k, v)
        cols = ", ".join(["user_id"] + list(fields.keys()))
        placeholders = ", ".join(["%s"] * (len(fields) + 1))
        cur2 = conn.cursor()
        cur2.execute(
            f"INSERT INTO delphi_context_builder_user_selections ({cols}) VALUES ({placeholders})",
            (payload.user_id, *fields.values())
        )
        cur2.close()

    conn.commit()
    cur.close(); conn.close()
    return {"status": "ok"}