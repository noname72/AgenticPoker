import sqlite3
from pathlib import Path
import pandas as pd

def inspect_database(db_path):
    """Connect to the poker game database and display sample data from each table."""
    try:
        # Set pandas display options for better terminal output
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_rows', 5)
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\n=== Poker Game Database Inspector ===\n")
        
        # For each table, show structure and sample data
        for (table_name,) in tables:
            print(f"\nTable: {table_name}")
            print("-" * 50)
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print("\nColumns:")
            columns_df = pd.DataFrame(columns, columns=["cid", "name", "type", "notnull", "dflt_value", "pk"])
            print(columns_df)
            
            # Get sample data
            df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5;", conn)
            
            if not df.empty:
                print("\nSample Data:")
                print(df)
            else:
                print("\nNo data in table")
            
            print("\n" + "=" * 50)
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Assuming the database is in the same directory as the script
    db_path = Path("poker_game.db")
    
    if not db_path.exists():
        print(f"Database file not found at: {db_path}")
    else:
        inspect_database(db_path) 