#
# <h1>RAZ Systems </h1>
#
# ASSIGNMENT 2a — Load Sample Data into SQLite
# ===============================================
#
# Before the SQLite MCP server has anything to query, we need an actual
# database file on disk with some data in it. This script builds that
# database directly with sqlite3 (no MCP involved yet -- that comes in
# assignment 2b).
#
# YOUR TASK:
# Create a SQLite database at D:/raz_training/6_mcp/bank.db containing a
# CountryBankBalance table, and insert at least 5 rows of sample data.

import sqlite3
from pathlib import Path

# =========================================================
# 1. Ensure folder exists
# =========================================================
db_folder = Path("D:/raz_training/6_mcp")
db_folder.mkdir(parents=True, exist_ok=True)

db_path = db_folder / "bank.db"

# =========================================================
# 2. Connect to SQLite DB
# =========================================================
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Database created at: {db_path}")

# =========================================================
# 3. Create table
# =========================================================
# TODO 1: Write a CREATE TABLE IF NOT EXISTS statement for
# CountryBankBalance with these columns:
#   id (INTEGER PRIMARY KEY AUTOINCREMENT)
#   Country (TEXT)
#   Bank (TEXT)
#   Account_no (TEXT)
#   Balance_in_Million (REAL)
cursor.execute("""
-- your CREATE TABLE statement here
""")

print("Table created successfully")

# =========================================================
# 4. Insert sample data
# =========================================================
# TODO 2: Add at least 5 rows of sample data as tuples:
# (Country, Bank, Account_no, Balance_in_Million)
sample_data = [
    # ("USA", "Citi", "ACC1001", 1200.5),
]

# TODO 3: Use cursor.executemany(...) to insert sample_data into the table.
# The SQL should look like:
# INSERT INTO CountryBankBalance (Country, Bank, Account_no, Balance_in_Million)
# VALUES (?, ?, ?, ?)


# =========================================================
# 5. Verify + commit + close
# =========================================================
cursor.execute("SELECT * FROM CountryBankBalance")
print(cursor.fetchall())

conn.commit()
conn.close()

print("Sample data inserted successfully")


# ─────────────────────────────────────────────────────
# REFLECTION QUESTION
# ─────────────────────────────────────────────────────
#
# This script uses plain sqlite3 -- no MCP server involved. In assignment 2b,
# an MCP server will read from this exact same database file. Why does the
# MCP server need to be pointed at this specific file path, and what would
# happen if the path in 2b didn't match the path used here?
