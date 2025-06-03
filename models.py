import sqlite3
import os

DB_PATH = 'data/inventory.db'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "inventory.db")

# Function to get the database connection and get the products table
def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, category, quantity, price FROM products")
    rows = cur.fetchall()
    conn.close()
    return rows


# Function to add a new product to the database
def add_product(name, category, quantity, price):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO products (name, category, quantity, price) VALUES (?, ?, ?, ?)',
                (name, category, quantity, price))
    conn.commit()
    conn.close()

def update_product(product_id, name, category, quantity, price):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('UPDATE products SET name=?, category=?, quantity=?, price=? WHERE id=?',
                (name, category, quantity, price, product_id))
    conn.commit()
    conn.close()


def get_product_by_id(product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "quantity": row[3],
            "price": row[4],
        }
    return None


def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM products WHERE id=?', (product_id,))
    conn.commit()
    conn.close()
