#
# <h1>RAZ Systems </h1>
#
# SOLUTION 2a — Load Sample Data into SQLite
# =============================================

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
cursor.execute("""
CREATE TABLE IF NOT EXISTS CountryBankBalance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Country TEXT,
    Bank TEXT,
    Account_no TEXT,
    Balance_in_Million REAL
)
""")

print("Table created successfully")

# =========================================================
# 4. Insert sample data
# =========================================================
sample_data = [
    ("USA", "Citi", "ACC1001", 1200.5),
    ("USA", "JP Morgan", "ACC1002", 980.0),
    ("India", "SBI", "ACC2001", 1500.75),
    ("India", "HDFC", "ACC2002", 1100.25),
    ("UK", "Barclays", "ACC3001", 800.0),
]

cursor.executemany("""
INSERT INTO CountryBankBalance (Country, Bank, Account_no, Balance_in_Million)
VALUES (?, ?, ?, ?)
""", sample_data)

# =========================================================
# 5. Verify + commit + close
# =========================================================
cursor.execute("SELECT * FROM CountryBankBalance")
print(cursor.fetchall())

conn.commit()
conn.close()

print("Sample data inserted successfully")


# ─────────────────────────────────────────────────────
# REFLECTION ANSWER (sketch)
# ─────────────────────────────────────────────────────
#
# The MCP SQLite server (mcp-server-sqlite) doesn't share any in-memory state
# with this script -- it's a completely separate process that only knows
# about whatever SQLite file it's told to open via its --db-path argument.
# If assignment 2b points at a different path (a typo, a different folder, a
# database that doesn't exist yet), the MCP server will either open/create an
# empty database at that path or fail outright -- either way, it will NOT see
# the CountryBankBalance table this script just created, because as far as
# that process is concerned, it's a completely different file on disk.
