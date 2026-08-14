"""
APIs service router — calls the MCP service's internal HTTP
bridge (http_server.py, running in the MCP venv on its own
port) rather than importing MCP code directly, since APIs and
MCP are separate services with separate dependencies.

Mirrors mcp_icp_router.py's httpx bridge pattern exactly, but
the prefix here is "/buyer-group" (not "/mcp-buyer-groups")
because that's what BuyerGroup.js actually calls:

    GET  /buyer-group/brand-options/{userId}
    POST /buyer-group/discover
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# URL of the MCP service's HTTP bridge — move this to your
# APIs service's own config/env handling, don't hardcode in
# production. Same value as mcp_icp_router.py's MCP_SERVICE_URL.
MCP_SERVICE_URL = "http://localhost:8100"

router = APIRouter(prefix="/buyer-group", tags=["Buyer Group"])


class DiscoverBuyerGroupsRequest(BaseModel):
    brand_id: int
    brand_name: Optional[str] = None
    product_name: Optional[str] = None


@router.get("/brand-options/{user_id}")
async def get_brand_options(user_id: int):

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{MCP_SERVICE_URL}/buyer-group/brand-options/{user_id}"
            )
            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"MCP service unreachable: {e}"
            )


@router.post("/discover")
async def discover_buyer_groups(payload: DiscoverBuyerGroupsRequest):

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{MCP_SERVICE_URL}/buyer-group/discover",
                json=payload.model_dump()
            )
            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"MCP service unreachable: {e}"
            )