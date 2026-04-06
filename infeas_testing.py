"""
Final infeasibility tests
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect("dbs/canoe_hr_16d.sqlite")

df = pd.read_sql_query('SELECT * FROM LimitTechInputSplitAnnual', conn)
df = df.groupby(['region','period','tech','operator'])['proportion'].sum()
print('TechInputSplitAnnual summation problems:')
print(df.loc[(df<1)&(df.index.get_level_values('operator')=='le')]-1)
print(df.loc[(df>1)&(df.index.get_level_values('operator')=='ge')]-1)

df = pd.read_sql_query(
    (
        'SELECT region, tech, vintage, output_comm, factor FROM LimitAnnualCapacityFactor '
        'WHERE output_comm IN (SELECT DISTINCT demand_name FROM DemandSpecificDistribution) '
        'AND vintage < 2025 '
        'AND operator == "ge"'
    )
    , conn
)
df['period'] = 2025
df_dsd = pd.read_sql_query('SELECT * FROM DemandSpecificDistribution', conn).groupby(['region','period','demand_name'])['dsd']
max_acf = (df_dsd.mean() / df_dsd.max()).to_dict()
df['max_acf'] = [max_acf[tuple(rpo)] for rpo in df[['region','period','output_comm']].values]
print('ACF - DSD conflicts:')
print(df.loc[df['factor'] > df['max_acf']])

# Check that existing capacity * c2a * minacf <= demand for all demands in 2025
df_existing = pd.read_sql_query('SELECT region, tech, vintage, capacity FROM ExistingCapacity', conn)
df_c2a = pd.read_sql_query('SELECT region, tech, c2a FROM CapacityToActivity', conn)
df_acf = pd.read_sql_query(
    'SELECT region, tech, vintage, output_comm, factor FROM LimitAnnualCapacityFactor WHERE operator = "le"'
    , conn
)
df_dem = pd.read_sql_query('SELECT region, period, commodity, demand FROM Demand WHERE period = 2025', conn)

# Vectorized approach: merge all dataframes
result = df_acf.merge(df_existing, on=['region', 'tech', 'vintage'], how='left')
result = result.merge(df_c2a, on=['region', 'tech'], how='left')
result['c2a'] = result['c2a'].fillna(1)  # Fill missing c2a values with 1
result['min_output'] = result['capacity'] * result['factor'] * result['c2a']
result = result.groupby(['region','output_comm'])['min_output'].sum().reset_index()
result = result.merge(df_dem, left_on=['region', 'output_comm'], 
                      right_on=['region', 'commodity'], how='left')

result['satisfaction'] = result['min_output'] / result['demand']
result = result.sort_values('satisfaction', ascending=True)

result.to_csv('demand_satisfaction.csv', index=False)

# Find infeasible cases
print('Existing capacity * c2a * minacf > demand:')
infeasible = result[result['satisfaction'] > 1]
for _, row in infeasible.iterrows():
    print([el for el in row])

conn.close()