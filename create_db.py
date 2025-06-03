import sqlite3
import os

os.makedirs("data", exist_ok=True)  # Create data folder if not exists

conn = sqlite3.connect("data/inventory.db")
cur = conn.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER,
        price REAL
    )
"""
)

conn.commit()
conn.close()
print("✅ Database and table created successfully.")

# Create sales table if it does not exist
conn = sqlite3.connect("data/inventory.db")
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        price REAL,
        total REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)
conn.commit()
conn.close()
print("✅ Sales table created successfully.")