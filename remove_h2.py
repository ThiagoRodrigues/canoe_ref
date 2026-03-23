import db_mgmt as mgmt
import sqlite3
import pandas as pd
import os
import shutil


def remove_h2(db_path):
    tech_to_remove = pd.read_csv('dbs/h2_Techs_to_remove.csv')
    comm_to_remove = pd.read_csv('dbs/h2_commodities_to_remove.csv')
    data = mgmt.sqlite_to_dfs(db_path)
    # Connect once at the top level
    conn = sqlite3.connect(db_path)
    try:
        
        # Define the tables you want to clean
        tables_to_check = ['Technology', 'CostVariable', 'OtherTable'] 

        for table, df in data.items():
            if ('tech' in df.columns) and len(set(tech_to_remove['tech']).intersection(df['tech'])) > 0:
                for tech in tech_to_remove['tech']:
                    # Pass the connection object instead of opening a new one
                    execute_delete(conn, table, 'tech', tech)    
            for comm in comm_to_remove['commodity']:
                cols_with_val = df.columns[df.isin([comm]).any()].tolist()
                # print(f"Checking table '{table}' for commodity '{comm}' in columns: {cols_with_val}")
                if len(cols_with_val) > 0:
                    for col in cols_with_val:
                        # print(col)
                        execute_delete(conn, table, col, comm)
        conn.commit() # Commit all deletes at once
    
    finally:
        conn.close()

    replace_value_globally(db_path, 'T_h2', 'T_h2_700')

    
def replace_value_globally(db_path, old_val, new_val):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        tables = [t for t in tables if t != 'Commodity']
        
        for table in tables:
            # 2. Get all column names for the current table
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = [col[1] for col in cursor.fetchall()]
            
            for column in columns:
                # 3. Update the value if it exists in this column
                # We use a parameterized query for safety and to handle strings
                query = f'UPDATE "{table}" SET "{column}" = ? WHERE "{column}" = ?'
                cursor.execute(query, (new_val, old_val))
                
                if cursor.rowcount > 0:
                    print(f"Updated {cursor.rowcount} rows in [{table}].[{column}]")
        
        # 4. Commit all changes at once
        query = f'DELETE FROM Commodity WHERE name = ?'
        cursor.execute(query, (old_val,))
        conn.commit()
        print("\nGlobal replacement complete.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()


def execute_delete(conn, table, column, value):
    cursor = conn.cursor()
    # Use ? for the value to handle strings/integers correctly and safely
    query = f'DELETE FROM "{table}" WHERE "{column}" = ?'
    cursor.execute(query, (value,))
    # print(f"Deleted {cursor.rowcount} rows from {table} where {column} = {value}")   
        
def main():
    db_core = 'dbs/canoe_ALL_cm_8d.sqlite'
    db_path = f'dbs/canoe_all_remove_h2.sqlite'
    
    
    os.remove(db_path) if os.path.exists(db_path) else None
    shutil.copy2(db_core, db_path)

    remove_h2(db_path)

if __name__ == "__main__":
    main()