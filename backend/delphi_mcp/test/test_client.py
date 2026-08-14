import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================
# CONFIGURATION
# ============================================================

# This file lives at: backend/delphi_mcp/test/test_client.py
# The server lives at: backend/delphi_mcp/server.py
# So we go up ONE level (out of "test/") to reach "delphi_mcp/".

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

SERVER_PATH = os.path.join(
    BASE_DIR,
    "server.py"
)

PYTHON_PATH = sys.executable

# IMPORTANT:
# Change this to an actual Delphi user_id that has a row in
# delphi_context_builder_user_selections.
USER_ID = 133


# ============================================================
# MAIN
# ============================================================

async def main():

    print("Starting Delphi MCP client...")
    print(f"Python: {PYTHON_PATH}")
    print(f"Server: {SERVER_PATH}")
    print(f"User ID: {USER_ID}")
    print()

    server_params = StdioServerParameters(
        command=PYTHON_PATH,
        args=[SERVER_PATH],
        env=os.environ.copy()
    )

    try:

        async with stdio_client(server_params) as (
            read_stream,
            write_stream
        ):

            print("STDIO connection established.")

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:

                print("Initializing MCP session...")

                await session.initialize()

                print("MCP session initialized successfully.")
                print()

                # ------------------------------------------------
                # LIST TOOLS
                # ------------------------------------------------

                print("Available tools:")

                tools_result = await session.list_tools()

                for tool in tools_result.tools:

                    print(
                        f"- {tool.name}: "
                        f"{tool.description}"
                    )

                print()

                # ------------------------------------------------
                # CALL DISCOVER ICP
                # ------------------------------------------------

                print("Calling discover_icp...")
                print()

                result = await session.call_tool(
                    "discover_icp",
                    {
                        "user_id": USER_ID
                    }
                )

                print("Tool result:")
                print()

                for content in result.content:

                    if hasattr(content, "text"):

                        try:

                            parsed = json.loads(content.text)

                            print(
                                json.dumps(
                                    parsed,
                                    indent=4,
                                    ensure_ascii=False
                                )
                            )

                        except json.JSONDecodeError:

                            print(content.text)

                    else:

                        print(content)

                print()
                print("MCP test completed successfully.")

    except Exception as e:

        print()
        print("MCP test failed.")
        print(f"Error: {type(e).__name__}: {e}")

        raise


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())