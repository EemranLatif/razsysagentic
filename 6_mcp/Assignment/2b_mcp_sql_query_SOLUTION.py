#
# <h1>RAZ Systems </h1>
#
# SOLUTION 2b — Query SQLite via MCP
# =====================================

import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    # =========================================================
    # 1. DB MCP SERVER CONFIG
    # =========================================================
    db_params = {
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "D:/raz_training/6_mcp/bank.db"],
    }

    # =========================================================
    # 2. CONNECT TO MCP SERVER
    # =========================================================
    async with MCPServerStdio(
        params=db_params,
        client_session_timeout_seconds=60,
    ) as server:

        print("Connected to DB MCP server")

        tools_response = await server.session.list_tools()
        for tool in tools_response.tools:
            print("\n===================")
            print("TOOL NAME:", tool.name)
            print("DESCRIPTION:", tool.description)
            print("INPUT SCHEMA:", tool.inputSchema)

        # =====================================================
        # 3. QUERY ACCOUNT BALANCE
        # =====================================================
        query_result = await server.session.call_tool(
            "read_query",
            {"query": "SELECT * FROM CountryBankBalance"},
        )

        print("Query executed")

        # =====================================================
        # 4. EXTRACT RESULT TEXT
        # =====================================================
        data_text = str(query_result)

        response = await server.session.call_tool("list_tables", {})
        print(response)

        # =====================================================
        # 5. SAVE TO FILE
        # =====================================================
        output_path = "D:/raz_training/6_mcp/account_balance.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("ACCOUNT BALANCE REPORT\n")
            f.write("=" * 40 + "\n\n")
            f.write(data_text)

        print(f"Saved output to {output_path}")


asyncio.run(main())


# ─────────────────────────────────────────────────────
# REFLECTION ANSWERS (sketch)
# ─────────────────────────────────────────────────────
#
# 1. MCP tools tend to be kept small and single-purpose (read_query for
#    running a query, list_tables for schema discovery) rather than one huge
#    do-everything tool. This mirrors good API design generally: narrower
#    tools have clearer input schemas, are easier for an LLM to pick
#    correctly, and make permissions/auditing simpler (e.g. you could imagine
#    a server that exposes read_query but not a write/delete equivalent, to
#    enforce read-only access at the tool level).
#
# 2. str(query_result) captures the entire MCP response object's repr,
#    including metadata/wrapper fields, not just the row data -- that makes
#    the saved file noisier than a clean CSV or JSON export, and harder to
#    re-parse programmatically later. A cleaner approach would be to inspect
#    query_result.content (a list of content blocks) and extract just the
#    .text field(s) that hold the actual query result, writing only that to
#    the file.
