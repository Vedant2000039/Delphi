import sys
import asyncio

from mcp.server import MCPServer
from services.icp_service import ICPService
from services.buyer_group_service import BuyerGroupService


server = MCPServer(
    name="Delphi MCP Server"
)

icp = ICPService()
buyer_groups = BuyerGroupService()


async def discover_icp(
    user_id: int,
    country_id: int = None,
    industry_id: int = None,
    brand_id: int = None,
    page: int = 1,
    page_size: int = 20
):

    try:
        result = icp.discover_icp(
            user_id=user_id,
            country_id=country_id,
            industry_id=industry_id,
            brand_id=brand_id,
            page=page,
            page_size=page_size
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


async def discover_buyer_groups(
    user_id: int,
    product: str = None,
    brand_ids: list = None
):
    """
    brand_ids should normally be the matched_brand_ids from a prior
    discover_icp call in this session, per the business logic:
    Buyer Group identifies decision-makers WITHIN the ICP's brand
    scope, not an independently re-derived one.
    """

    try:
        result = buyer_groups.discover_buyer_groups(
            user_id=user_id,
            product_override=product,
            brand_ids=brand_ids
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


server.add_tool(
    discover_icp,
    name="discover_icp",
    description="Discover the ideal customer profile for a Delphi user, using historical lead/customer data for their selected product."
)

server.add_tool(
    discover_buyer_groups,
    name="discover_buyer_groups",
    description="Given a previously generated ICP's matched brand_ids, identify decision-makers and influencers within that ICP-qualified population, grouped by role and mapped by buying influence."
)


async def main():
    print(
        "[MCP] Delphi MCP server starting...",
        file=sys.stderr
    )

    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())