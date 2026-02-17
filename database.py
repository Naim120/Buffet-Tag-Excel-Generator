import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'food_database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            calories INTEGER,
            allergens TEXT
        )
    ''')
    # allergens will be a comma-separated string of allergen names present in the food (e.g. "Fish,Egg")
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_food(name):
    conn = get_db_connection()
    food = conn.execute('SELECT * FROM food_items WHERE name = ?', (name,)).fetchone()
    conn.close()
    return food

def add_food(name, calories, allergens_list):
    conn = get_db_connection()
    allergens_str = ",".join(allergens_list) if allergens_list else ""
    try:
        conn.execute('INSERT INTO food_items (name, calories, allergens) VALUES (?, ?, ?)',
                     (name, calories, allergens_str))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Food {name} already exists.")
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
