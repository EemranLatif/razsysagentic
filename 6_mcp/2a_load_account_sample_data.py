#
#<h1>RAZ Systems </h1>
#



import sqlite3
from pathlib import Path

# =========================================================
# 1. Ensure folder exists
# =========================================================
db_folder = Path("D:/raz_training/6_mcp")
db_folder.mkdir(parents=True, exist_ok=True)

# Database file path
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


#cursor = conn.cursor()

cursor.execute("SELECT * FROM CountryBankBalance")
print(cursor.fetchall())
# =========================================================
# 5. Commit and close
# =========================================================
conn.commit()
conn.close()

print("Sample data inserted successfully")