#
#<h1>RAZ Systems </h1>
#



import asyncio
from agents.mcp.server import MCPServerStdio


async def main():

    # =========================================================
    # 1. DB MCP SERVER CONFIG
    # =========================================================
    db_params = {
        "command": "uvx",
        "args": ["mcp-server-sqlite" , "--db-path", "D:/raz_training/6_mcp/bank.db"],
        "env": {
            # path to your database file
           #"SQLITE_DB_PATH": "D:/raz_training/6_mcp/bank.db"

        }
    }


    # =========================================================
    # 2. CONNECT TO MCP SERVER
    # =========================================================
    async with MCPServerStdio(params=db_params,
          client_session_timeout_seconds=60) as server:

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
            {
                "query": "SELECT * FROM CountryBankBalance"
                #"query": "SELECT name FROM sqlite_master WHERE type='table';"
            }
        )


        print("Query executed")


        # =====================================================
        # 4. EXTRACT RESULT TEXT
        # =====================================================
        # MCP returns structured content, usually in text form
        data_text = str(query_result)
        response = await server.session.call_tool(
            "list_tables",
            {}
        )

        print(response)

        # =====================================================
        # 5. SAVE TO FILE (D:\raz)
        # =====================================================
        output_path = "D:/raz_training/6_mcp/account_balance.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("ACCOUNT BALANCE REPORT\n")
            f.write("=" * 40 + "\n\n")
            f.write(data_text)

        print(f"Saved output to {output_path}")


# =========================================================
# RUN PROGRAM
# =========================================================
asyncio.run(main())