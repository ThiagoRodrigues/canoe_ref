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

db_path = 'dbs/canoe_hr_16d.sqlite'

output_dir = f'outputs/CANOE_{datetime.now().strftime("%Y%m%d_%H_%M")}'

print('\nUpdating Database Paths in Configuration File...\n')
update_db_paths(config_path, db_path, False) 

print('\nDatabase Paths Successfully Updated\n')

print('\nRunning CANOE Model...\n')
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

shutil.copy2(db_path, output_dir)
subprocess.run(["python3", main_path, "--config", config_path, "-o", output_dir])
shutil.copy2(db_path, output_dir)





