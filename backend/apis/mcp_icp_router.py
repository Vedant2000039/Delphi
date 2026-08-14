"""
APIs service router — calls the MCP service's internal HTTP
bridge (http_server.py, running in the MCP venv on its own
port) rather than importing MCP code directly, since APIs and
MCP are separate services with separate dependencies.
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# URL of the MCP service's HTTP bridge — move this to your
# APIs service's own config/env handling, don't hardcode in
# production.
MCP_SERVICE_URL = "http://localhost:8100"

router = APIRouter(prefix="/mcp-icp", tags=["MCP ICP"])


class DiscoverICPRequest(BaseModel):
    user_id: int
    product: Optional[str] = None
    country_id: Optional[int] = None
    industry_id: Optional[int] = None


@router.get("/product-options/{user_id}")
async def get_product_options(user_id: int):

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{MCP_SERVICE_URL}/product-options/{user_id}"
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
async def discover_icp(payload: DiscoverICPRequest):

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{MCP_SERVICE_URL}/discover",
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