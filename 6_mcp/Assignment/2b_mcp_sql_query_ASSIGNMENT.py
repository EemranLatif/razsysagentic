#
# <h1>RAZ Systems </h1>
#
# ASSIGNMENT 2b — Query SQLite via MCP
# =======================================
#
# Now that assignment 2a has created D:/raz_training/6_mcp/bank.db with data
# in it, this script connects to that database THROUGH an MCP server instead
# of using sqlite3 directly. mcp-server-sqlite exposes tools like
# "read_query" (run a SELECT) and "list_tables" (see what tables exist).
#
# YOUR TASK:
# Connect to the SQLite MCP server pointed at bank.db, list its tools, query
# the CountryBankBalance table, list the tables in the database, and save the
# query result to a text file.

import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    # =========================================================
    # 1. DB MCP SERVER CONFIG
    # =========================================================
    # TODO 1: Build db_params.
    # - command: "uvx"
    # - args: ["mcp-server-sqlite", "--db-path", "D:/raz_training/6_mcp/bank.db"]
    db_params = {
        # your code here
    }

    # =========================================================
    # 2. CONNECT TO MCP SERVER
    # =========================================================
    # TODO 2: Open the session with MCPServerStdio(params=db_params,
    # client_session_timeout_seconds=60)
    async with None:  # replace None with your MCPServerStdio(...) call

        print("Connected to DB MCP server")

        # TODO 3: List available tools and print each tool's name,
        # description, and inputSchema (loop over tools_response.tools).
        tools_response = None

        # =====================================================
        # 3. QUERY ACCOUNT BALANCE
        # =====================================================
        # TODO 4: Call the "read_query" tool with a query that selects all
        # rows from CountryBankBalance.
        query_result = None

        print("Query executed")

        # =====================================================
        # 4. EXTRACT RESULT TEXT
        # =====================================================
        data_text = str(query_result)

        # TODO 5: Call the "list_tables" tool (it takes no arguments -- pass
        # an empty dict) and print the response.
        response = None
        print(response)

        # =====================================================
        # 5. SAVE TO FILE
        # =====================================================
        output_path = "D:/raz_training/6_mcp/account_balance.txt"

        # TODO 6: Open output_path for writing (utf-8 encoding) and write a
        # short header plus data_text into it. Print a confirmation message
        # with the path once done.


asyncio.run(main())


# ─────────────────────────────────────────────────────
# REFLECTION QUESTIONS
# ─────────────────────────────────────────────────────
#
# 1. "read_query" and "list_tables" are two different tools exposed by the
#    same MCP server. What does that tell you about how granular MCP tools
#    typically are, compared to exposing one big "run_sql" catch-all tool?
#
# 2. This script writes the *string representation* of query_result to a
#    file rather than parsing out just the row data. What's a downside of
#    saving str(query_result) directly, and how might you extract just the
#    actual rows instead?
