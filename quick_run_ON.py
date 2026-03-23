import numpy as np
import pandas as pd
import sqlite3
import os
from datetime import datetime
import shutil
import subprocess
from pathlib import Path
import re
from db_mgmt import update_database_from_excel, update_db_paths, convert_sql_to_sqlite
import vehicle_cluster as vc
import add_ref
import flex_scenario as flex
import fix_imports as fi
import survival_curve as sc
import db_mgmt as mgmt
import remove_h2 as rh



def change_existing_cap(db, existing_capa_new):
    # Connect directly to the original database
    connection = sqlite3.connect(db)
    
    try:
        ### remove rows with technologies in the new table from existing capacity table
        techs_new_sales = existing_capa_new['tech'].unique().tolist()

        query_remove_existing = f"""DELETE FROM ExistingCapacity
                                    WHERE tech IN ({','.join(['?']*len(techs_new_sales))})"""
        
        connection.execute(query_remove_existing, techs_new_sales)
        
        ### insert new vehicle sales data into existing capacity table
        existing_capa_new.to_sql('ExistingCapacity', connection, if_exists='append', index=False)
        
        connection.commit()

        # Optional: Run VACUUM to reclaim space and optimize the original file now that it's modified
        connection.execute("VACUUM")
        
    finally:
        connection.close()

def insert_eff_surv_new(efficiency_new, survival_curve_new, db):
    # build connection directly to the original database
    connection = sqlite3.connect(db)
    
    try:
        # insert efficiency_new to table "Efficiency"
        efficiency_new.to_sql('Efficiency', connection, if_exists='append', index=False)
        
        # insert survival_curve_new to table "LifetimeSurvivalCurve"
        survival_curve_new.to_sql('LifetimeSurvivalCurve', connection, if_exists='append', index=False)
        
        connection.commit()
        # Clean up the file internally
        connection.execute("VACUUM")
        
    finally:
        connection.close()



def remove_tech_vintage(db):
    # Connect directly to the original database
    connection = sqlite3.connect(db)
    
    # Define targets
    tech_vintage_remove = {'T_LDV_LTF_GSL_HEV_EX': 2015}
    
    tables = ['ExistingCapacity', 'Efficiency', 'CostVariable', 'LifetimeSurvivalCurve']
    
    try:
        # Loop through tables to keep the code clean
        for table in tables:
            query = f"DELETE FROM {table} WHERE tech = ? AND vintage = ?"
            for tech, vintage in tech_vintage_remove.items():
                connection.execute(query, (tech, vintage))
        
        # Commit the deletions
        connection.commit()
        
        # Optimize the file after multiple deletions
        connection.execute("VACUUM")
        print(f"Successfully removed {list(tech_vintage_remove.keys())} (Vintage: {list(tech_vintage_remove.values())}) from all tables.")
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        connection.rollback()
    finally:
        connection.close()    
    

def update_db_tables(db_path, data_dict):
    conn = sqlite3.connect(db_path)
    
    try:
        for table_name, df in data_dict.items():
            if df.empty:
                print(f"Skipping {table_name}: Dataframe is empty.")
                continue

            # 1. Get Schema Information
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            # col[1] is name, col[5] is pk flag (non-zero if part of PK)
            pk_cols = [col[1] for col in columns_info if col[5] > 0]

            # 2. Safety Check: Only use PKs that actually exist in the CSV
            valid_pks = [col for col in pk_cols if col in df.columns]
            
            if not valid_pks:
                # If no PKs match, we can't safely target rows for deletion
                print(f"Warning: No matching Primary Keys found for {table_name}. Skipping delete step.")
            else:
                # 3. Targeted Deletion
                where_clause = " AND ".join([f"{col} = ?" for col in valid_pks])
                delete_query = f"DELETE FROM {table_name} WHERE {where_clause}"
                
                # Convert DF rows to tuples for the SQL parameters
                pk_values = df[valid_pks].to_records(index=False).tolist()
                
                conn.executemany(delete_query, pk_values)
                print(f"Cleared existing entries for {table_name} using keys: {valid_pks}")

            # 4. Data Type Alignment
            # Ensure the DF columns match the SQL table order/names
            db_cols = [col[1] for col in columns_info]
            df_to_insert = df[[c for c in db_cols if c in df.columns]]

            # 5. Insert new data
            df_to_insert.to_sql(table_name, conn, if_exists='append', index=False)
            print(f"Successfully updated {table_name}.")

        conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating {table_name}: {e}")
    finally:
        conn.close()

def update_lacf(lacf_update, db):
    # organize LACF data
    ## only keep data during 2025 period and cross join with all periods
    lacf_update = lacf_update[lacf_update['period'] == 2025].copy()
    lacf_update = lacf_update.drop(columns=['period'])
    
    periods_df = pd.DataFrame({'period': [2025, 2030, 2035, 2040, 2045, 2050]})
    lacf_update = lacf_update.merge(periods_df, how='cross')

    # build connection directly to the original database
    connection = sqlite3.connect(db)
    
    try:
        # delete rows in LimitAnnualCapacityFactor table whose tech is in lacf_update
        techs_lacf = lacf_update['tech'].unique().tolist()
        query_remove_existing_lacf = f"""DELETE FROM LimitAnnualCapacityFactor
                                         WHERE tech IN ({','.join(['?']*len(techs_lacf))})"""
        
        connection.execute(query_remove_existing_lacf, techs_lacf)
        
        # insert updated LACF data into LimitAnnualCapacityFactor table
        lacf_update.to_sql('LimitAnnualCapacityFactor', connection, if_exists='append', index=False)
        
        connection.commit()
        connection.execute("VACUUM")
        
    finally:
        connection.close()

    return lacf_update


def remove_retired_techs(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Get the first_period (sequence 0)
        query_tp = "SELECT period FROM TimePeriod WHERE sequence = 0 LIMIT 1"
        first_period = pd.read_sql_query(query_tp, conn)['period'].iloc[0]

        # 2. Get the lifetime mapping
        query_lt = "SELECT tech, region, lifetime FROM LifetimeTech"
        lt_df = pd.read_sql_query(query_lt, conn)

        # 3. Prepare parameters: (tech, region, cutoff_vintage)
        # where cutoff_vintage = first_period - lifetime
        delete_list = []
        for _, row in lt_df.iterrows():
            cutoff = int(first_period - row['lifetime'])
            delete_list.append((row['region'], row['tech'], cutoff))
            print(row['region'], row['tech'], cutoff)

        # 4. Define the target tables
        # We use a loop here to apply the same deletion logic to multiple tables
        target_tables = ['ExistingCapacity', 'Efficiency', 'LifetimeSurvivalCurve']



        for table in target_tables:
            delete_query = f"""
                DELETE FROM {table} 
                WHERE region = ? 
                  AND tech = ? 
                  AND vintage <= ?
            """
            cursor.executemany(delete_query, delete_list)
            print(f"Cleaned up {cursor.rowcount} retired rows from {table}.")

        # 5. Commit all deletions at once
        conn.commit()
        print(f"Database cleanup for {db_path} successful.")

    except Exception as e:
        conn.rollback()
        print(f"Error during retirement cleanup: {e}")
    finally:
        conn.close()

    
def main():
    # Paths
    main_path = os.path.join('temoa/', "main.py")
    config_path = 'temoa/data_files/my_configs/config_sample.toml'

    db_core = 'dbs/canoe_ON_16d.sqlite'
    db_path = f'dbs/ON_16days.sqlite'

    os.remove(db_path) if os.path.exists(db_path) else None

    shutil.copy2(db_core, db_path)

    output_path = 'outputs'
    output_dir = f'{output_path}/canoe_ON'

    # Load new data from CSVs
    existing_capacity = pd.read_csv('dbs/ExistingCapacity_ALL.csv')
    efficiency = pd.read_csv("dbs/Efficiency_NEW_ALL.csv")
    survival_curve = pd.read_csv("dbs/LifetimeSurvivalCurve_ALL.csv")
    
    # Define regions of interest
    regions = ['ON']

    # Add new refinery data to the reference database
    add_ref.add_refinery_to_db(db_core=db_core, db_path=db_path, regions=regions)
    
    # Filter new data for the specified regions
    ec = existing_capacity[existing_capacity['region'].isin(regions)]
    efficiency = efficiency[efficiency['region'].isin(regions)]
    survival_curve = survival_curve[survival_curve['region'].isin(regions)]

   
    change_existing_cap(db = db_path, existing_capa_new = ec)
    insert_eff_surv_new(efficiency_new = efficiency,
                    survival_curve_new = survival_curve,
                    db = db_path)
    
    

    fi.fix_imports(db_path)
    rh.remove_h2(db_path)


    files = {
         'TechGroup': "TechGroup.csv",
         'TechGroupMember': "TechGroupMember.csv",
         'LifetimeTech': "LifetimeTech_ALL.csv",
         'LimitGrowthNewCapacity': "LimitGrowthNewCapacity.csv",
         'LimitAnnualCapacityFactor': "LimitAnnualCapacityFactor_ALL.csv",
         'CostFixed': "CostFixed.csv",
         'CostInvest': "CostInvest.csv",
         'CostVariable': "CostVariable_ALL.csv",
         'LifetimeSurvivalCurve': "LifetimeSurvivalCurve_ALL.csv",
         # 'ExistingCapacity': "ExistingCapacity_ALL.csv",
         # 'Efficiency': "Efficiency_NEW_ALL.csv"
    }

    data_dict = {
        f: pd.read_csv(Path('dbs') / files[f]) for f in files.keys()
    }
    for table, df in data_dict.items():
        if 'region' in df.columns:
            df = df[df['region'].isin(regions)].reset_index(drop=True)
            data_dict[table] = df
    
    update_lacf(lacf_update = data_dict['LimitAnnualCapacityFactor'],
            db = db_path)
    update_db_tables(db_path, data_dict)
    remove_tech_vintage(db = db_path)

    data = mgmt.sqlite_to_dfs(db_path)
    for table, df in data.items():
        if ('region' in df.columns) and (len(set(df['region'].unique()))>1):
            print(f"\nTable: {table}")
            print(df['region'].unique())
    

    print('\nUpdating Database Paths in Configuration File...\n')
    update_db_paths(config_path, db_path, False) 
    print('\nDatabase Paths Successfully Updated\n')


    remove_retired_techs(db_path)

    print('\nRunning CANOE Model...\n')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    shutil.copy2(db_path, output_dir)
    subprocess.run(["python", main_path, "--config", config_path, "-o", output_dir])
    shutil.copy2(db_path, output_dir)

    
if __name__ == "__main__":
    main() 

    