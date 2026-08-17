# import sys
# import asyncio

# from mcp.server import MCPServer
# from services.icp_service import ICPService
# from services.buyer_group_service import BuyerGroupService


# server = MCPServer(
#     name="Delphi MCP Server"
# )

# icp = ICPService()
# buyer_groups = BuyerGroupService()


# async def discover_icp(
#     user_id: int,
#     country_id: int = None,
#     industry_id: int = None,
#     brand_id: int = None,
#     page: int = 1,
#     page_size: int = 20
# ):

#     try:
#         result = icp.discover_icp(
#             user_id=user_id,
#             country_id=country_id,
#             industry_id=industry_id,
#             brand_id=brand_id,
#             page=page,
#             page_size=page_size
#         )

#         return {
#             "status": "success",
#             "data": result
#         }

#     except Exception as e:
#         return {
#             "status": "error",
#             "message": str(e)
#         }


# async def discover_buyer_groups(
#     user_id: int,
#     product: str = None,
#     brand_ids: list = None
# ):
#     """
#     brand_ids should normally be the matched_brand_ids from a prior
#     discover_icp call in this session, per the business logic:
#     Buyer Group identifies decision-makers WITHIN the ICP's brand
#     scope, not an independently re-derived one.
#     """

#     try:
#         result = buyer_groups.discover_buyer_groups(
#             user_id=user_id,
#             product_override=product,
#             brand_ids=brand_ids
#         )

#         return {
#             "status": "success",
#             "data": result
#         }

#     except Exception as e:
#         return {
#             "status": "error",
#             "message": str(e)
#         }


# server.add_tool(
#     discover_icp,
#     name="discover_icp",
#     description="Discover the ideal customer profile for a Delphi user, using historical lead/customer data for their selected product."
# )

# server.add_tool(
#     discover_buyer_groups,
#     name="discover_buyer_groups",
#     description="Given a previously generated ICP's matched brand_ids, identify decision-makers and influencers within that ICP-qualified population, grouped by role and mapped by buying influence."
# )


# async def main():
#     print(
#         "[MCP] Delphi MCP server starting...",
#         file=sys.stderr
#     )

#     await server.run_stdio_async()


# if __name__ == "__main__":
#     asyncio.run(main())



#####################################

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
    """
    NOTE: No `product` argument here on purpose. The product/service
    to analyze is always the one already saved for this user
    (delphi_context_builder_user_selections.selected_product), resolved
    inside ICPService.discover_icp via get_selected_product(). This tool
    must never prompt the user for a product/service — that only happens
    through the sidebar product/service switcher card.
    """

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


async def discover_buyer_groups(user_id: int):
    """
    No `product` or `brand_ids` arguments on purpose. The brand
    scope is always resolved server-side from the user's saved
    product selection (BuyerGroupService.resolve_brand_context),
    using the exact same competitor-brand matching discover_icp
    uses — never a separate user choice, never re-derived
    independently, and never asked of the user.
    """

    try:
        result = buyer_groups.discover_buyer_groups(user_id=user_id)

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
    description=(
        "Discover the ideal customer profile for a Delphi user, using historical "
        "lead/customer data for their ALREADY-SELECTED product/service. "
        "The product/service is automatically resolved from the user's saved "
        "context inside this tool — do NOT ask the user which product or "
        "service to analyze, and do NOT pass a product/service argument. "
        "Only call this with user_id (and optional country_id/industry_id/"
        "brand_id filters). If the user wants to analyze a different product, "
        "they must change it via the product/service switcher card in the "
        "sidebar, not via this tool."
    )
)

server.add_tool(
    discover_buyer_groups,
    name="discover_buyer_groups",
    description=(
        "Identify decision-makers and influencers for a Delphi user's "
        "ALREADY-SELECTED product/service, grouped by role and mapped by "
        "buying influence. The brand scope is automatically resolved "
        "server-side from the same competitor-brand matching used for ICP "
        "discovery — do NOT ask the user which brand to build a buyer "
        "group for, and do NOT pass a brand argument. Only call this with "
        "user_id. If the user wants a different product/brand, they must "
        "change it via the product/service switcher card in the sidebar."
    )
)


async def main():
    print(
        "[MCP] Delphi MCP server starting...",
        file=sys.stderr
    )

    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())