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

main_path = os.path.join('temoa/', "main.py")
config_path = 'temoa/data_files/my_configs/config_sample.toml'

# excel_path = f"dbs/transport_ON.xlsx"
#sql_file_path = 'dbs/canoe_dataset_schema.sql'
# db_core = 'dbs/canoe_ON_16d.sqlite'
# db_path = f'dbs/canoe_ref.sqlite'

db_core = 'dbs/canoe_ALL_cm_8d.sqlite'
db_path = f'dbs/canoe_all.sqlite'

os.remove(db_path) if os.path.exists(db_path) else None

# convert_sql_to_sqlite(sql_file_path, db_path)
# update_database_from_excel(excel_path, db_path)

# Add refinery to database
add_ref.add_refinery_to_db(db_core, db_path)

# Fix fuel import technologies in CostVariable
fi.fix_imports(db_path)
sc.adjust_survival_curve(db_path)

ZEV_constraints = False  # Set to True to impose ZEV proportions

if ZEV_constraints:
    # Set ZEV proportions
    print('\nSetting ZEV Proportions in Vehicle Clustering...\n')
    min_proportion = [0, 0.6, 1, 1, 1, 1] # share of ZEV per period
    vc.set_ZEV(min_proportion, db_path=db_path)
    print('\nZEV Proportions Successfully Set\n')


inflex_constraint = False  # Set to True to impose fuel import constraints
if inflex_constraint:
    print('\nConstraining Fuel Imports in Database...\n')
    flex.impose_flex_constraints(db_path)
    print('\nFlexibility Scenario Constraints Successfully Added\n')


print('\nUpdating Database Paths in Configuration File...\n')
update_db_paths(config_path, db_path, False) 
print('\nDatabase Paths Successfully Updated\n')

output_path = 'outputs'
output_dir = f'{output_path}/{"all_inflex" if inflex_constraint else "all_flex"}{"_ZEV" if ZEV_constraints else ""}_ON'

print('\nRunning CANOE Model...\n')
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


shutil.copy2(db_path, output_dir)
subprocess.run(["python", main_path, "--config", config_path, "-o", output_dir])
shutil.copy2(db_path, output_dir)

