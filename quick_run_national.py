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



main_path = os.path.join('temoa/', "main.py")
config_path = 'temoa/data_files/my_configs/config_sample.toml'

db_core = 'dbs/canoe_ALL_cm_8d.sqlite'
db_path = f'dbs/canoe_all.sqlite'


os.remove(db_path) if os.path.exists(db_path) else None

shutil.copy2(db_core, db_path)

def change_existing_capa(db, existing_capa_new):
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


change_existing_capa(db = db_path,
                     existing_capa_new = pd.read_csv('dbs/ExistingCapacity_ALL.csv'))

insert_eff_surv_new(efficiency_new = pd.read_csv("dbs/Efficiency_NEW_ALL.csv"),
                    survival_curve_new = pd.read_csv("dbs/LifetimeSurvivalCurve_ALL.csv"),
                    db = db_path)

update_lacf(lacf_update = pd.read_csv("dbs/LimitAnnualCapacityFactor_ALL.csv"),
            db = db_path)

remove_tech_vintage(db = db_path)

# Fix fuel import technologies in CostVariable
fi.fix_imports(db_path)
tech_to_remove = pd.read_csv('dbs/h2_Techs_to_remove.csv')
comm_to_remove = pd.read_csv('dbs/h2_commodities_to_remove.csv')

rh.remove_h2(db_path)


def remove_tech_vintage_region(db):
    # Connect directly to the original database
    connection = sqlite3.connect(db)
    
    # Define targets
    tech_vintage_remove = {'T_LDV_C_DSL_EX': {'vintage':[2020], "region": ['MB',"NB", 'NLLAB', 'PEI', 'SK']}, 
                           'T_LDV_LTF_GSL_HEV_EX': {'vintage':[2015], "region": 'all'},
                           'T_LDV_BEV_CHRG': {'vintage':[2015], "region": ['AB', 'MB', 'NB', 'NLLAB', 'PEI', 'SK']},
                           }
    
    tables = ['ExistingCapacity', 'Efficiency', 'CostVariable', 'LifetimeSurvivalCurve', 'CostFixed']
    
    try:    
        # Loop through tables to keep the code clean
        for table in tables:
            query = f"DELETE FROM {table} WHERE tech = ? AND vintage = ? AND region = ?"
            for tech in tech_vintage_remove.keys():
                for v in tech_vintage_remove[tech]['vintage']:
                    if tech_vintage_remove[tech]['region'] == 'all':
                        # If region is 'all', delete all regions for this tech and vintage
                        connection.execute(f"DELETE FROM {table} WHERE tech = ? AND vintage = ?", (tech, v))
                    else:
                        for region in tech_vintage_remove[tech]['region']:
                            connection.execute(query, (tech, v, region))
        
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



def add_cost_variable_rows(db_path, survival_df):
    conn = sqlite3.connect(db_path)
    cv_existing = pd.read_sql("SELECT * FROM CostVariable", conn)
    
    # 1. Force Dtypes to match to prevent merge failures
    # This ensures 'period' and 'vintage' are always compared as integers
    for df in [cv_existing, survival_df]:
        for col in ['period', 'vintage']:
            if col in df.columns:
                df[col] = df[col].astype(int)

    # 2. Define the 'Required' combinations
    required = survival_df[['region', 'tech', 'period', 'vintage']].copy()
    required = required[required['period'].isin([int(y) for y in range(2025, 2051, 5)])].drop_duplicates()
    required = required[required['vintage'].isin([int(y) for y in range(2005, 2021, 5)])].drop_duplicates()


    # 3. Identify missing rows using a named indicator
    combined = pd.merge(
        required, 
        cv_existing, 
        on=['region', 'tech', 'period', 'vintage'], 
        how='left', 
        indicator='_merge_check' 
    )
    
    # Check for 'left_only' which means it exists in survival_df but NOT the DB
    missing = combined[combined['_merge_check'] == 'left_only'].copy()
    
    if missing.empty:
        print("All required CostVariable rows already exist. No action needed.")
        conn.close()
        return

    # 4. Determine "Latest Cost" and "Units"
    # We sort to ensure 'last()' gives us the most recent data point
    reference_data = (
        cv_existing.sort_values(['region', 'tech', 'period', 'vintage'])
        .groupby(['region', 'tech'])
        .last()
        .reset_index()[['region', 'tech', 'cost', 'units']]
    )

    # 5. Fill missing data
    # Remove the columns we don't need from the merge result before re-filling
    cols_to_keep = ['region', 'tech', 'period', 'vintage']
    missing = missing[cols_to_keep] 
    
    final_to_add = pd.merge(missing, reference_data, on=['region', 'tech'], how='left')
    final_to_add['notes'] = 'Auto-filled via cross-vintage carry-forward'
    
    # Optional: Fill units with a default if the tech is totally new
    final_to_add['units'] = final_to_add['units'].fillna('Unknown')
    final_to_add = final_to_add.dropna(subset=['cost'])

    # 6. Final Push
    if not final_to_add.empty:
        final_to_add.to_sql('CostVariable', conn, if_exists='append', index=False)
        conn.commit()
        conn.execute("VACUUM")
        print(f"Successfully added {len(final_to_add)} rows.")
    
    conn.close()
    

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

# add_cost_variable_rows(db_path, pd.read_csv("dbs/LifetimeSurvivalCurve_ALL.csv"))

remove_tech_vintage_region(db_path)

data_dict = {f: pd.read_csv(Path('dbs') / files[f]) for f in files.keys()}


update_db_tables(db_path, data_dict)


output_path = 'outputs'
output_dir = f'{output_path}/CANOE_TRANSPORT_NATIONAL'

print('\nUpdating Database Paths in Configuration File...\n')
update_db_paths(config_path, db_path, False) 
print('\nDatabase Paths Successfully Updated\n')


print('\nRunning CANOE Model...\n')
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


shutil.copy2(db_path, output_dir)
subprocess.run(["python", main_path, "--config", config_path, "-o", output_dir])
shutil.copy2(db_path, output_dir)





