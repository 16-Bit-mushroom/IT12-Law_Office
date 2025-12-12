import sqlite3
import os

DB_PATH = os.path.join('instance', 'app.db')

def add_column(table):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print(f"Checking {table}...", end=" ")
        
        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'deleted_at' not in columns:
            print(f"Adding 'deleted_at' column...", end=" ")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at DATETIME")
            conn.commit()
            print("Success.")
        else:
            print("Already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
    else:
        print("--- Updating Database Schema for Recycle Bin ---")
        add_column('clients')
        add_column('cases')
        add_column('notarial_entries')
        add_column('documents')
        print("--- Done ---")