"""
backend/delphi_mcp/http_server.py

A thin HTTP interface around ICPService and BuyerGroupService,
separate from the MCP stdio server (Server.py). This exists
because the APIs service runs in its own venv and can't import
delphi_mcp's Python modules directly (different dependencies,
different process). Instead, the APIs service calls this over
HTTP.

Run with:
    cd backend/delphi_mcp
    uvicorn http_server:app --host 0.0.0.0 --port 8100

Requires fastapi + uvicorn installed in the delphi_mcp venv:
    python -m pip install fastapi uvicorn
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

try:
    from services.icp_service import ICPService
    from services.buyer_group_service import BuyerGroupService
except ImportError:
    from .services.icp_service import ICPService
    from .services.buyer_group_service import BuyerGroupService


app = FastAPI(title="Delphi MCP - Internal HTTP Bridge")


class DiscoverICPRequest(BaseModel):
    user_id: int
    product: Optional[str] = None
    country_id: Optional[int] = None
    industry_id: Optional[int] = None


class DiscoverBuyerGroupsRequest(BaseModel):
    brand_id: int
    brand_name: Optional[str] = None
    product_name: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# ICP
# ============================================================

@app.get("/product-options/{user_id}")
def get_product_options(user_id: int):

    svc = ICPService()

    try:
        return svc.get_product_options(user_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        svc.close()


@app.post("/discover")
def discover_icp(payload: DiscoverICPRequest):

    svc = ICPService()

    try:
        result = svc.discover_icp(
            user_id=payload.user_id,
            product_override=payload.product,
            country_id=payload.country_id,
            industry_id=payload.industry_id
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        svc.close()


# ============================================================
# Buyer Groups
# ============================================================

@app.get("/buyer-group/brand-options/{user_id}")
def get_brand_options(user_id: int):

    svc = BuyerGroupService()

    try:
        return svc.get_brand_options(user_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        svc.close()


@app.post("/buyer-group/discover")
def discover_buyer_groups(payload: DiscoverBuyerGroupsRequest):

    svc = BuyerGroupService()

    try:
        result = svc.discover_buyer_groups(
            brand_id=payload.brand_id,
            brand_name=payload.brand_name,
            product_name=payload.product_name
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        svc.close()