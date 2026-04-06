"""
Final infeasibility tests
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect("dbs/canoe_hr_16d.sqlite")
curs = conn.cursor()

# Need these
time_all = curs.execute('SELECT period FROM TimePeriod').fetchall()
time_all = [p[0] for p in time_all[0:-1]]

# get lifetimes. Major headache but needs to be done
lifetime_process = dict()
data = curs.execute('SELECT region, tech, vintage FROM Efficiency').fetchall()
for rtv in data:
    lifetime_process[rtv] = 40
data = curs.execute('SELECT region, tech, lifetime FROM LifetimeTech').fetchall()
for rtl in data:
    for v in time_all:
        lifetime_process[(*rtl[0:2], v)] = rtl[2]
data = curs.execute('SELECT region, tech, vintage, lifetime FROM LifetimeProcess').fetchall()
for rtvl in data:
    lifetime_process[rtvl[0:3]] = rtvl[3]

df = pd.read_sql_query('SELECT * FROM LimitTechInputSplitAnnual', conn)
df = df.groupby(['region','period','tech','operator'])['proportion'].sum()
print('TechInputSplitAnnual summation problems:')
print(df.loc[(df<0.999)&(df.index.get_level_values('operator')=='le')]-1)
print(df.loc[(df>1.001)&(df.index.get_level_values('operator')=='ge')]-1)

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
df_existing = df_existing.loc[df_existing['vintage'] + df_existing.apply(lambda row: lifetime_process.get((row['region'], row['tech'], row['vintage']), 0), axis=1) > 2025]
df_c2a = pd.read_sql_query('SELECT region, tech, c2a FROM CapacityToActivity', conn)
df_acf = pd.read_sql_query(
    'SELECT region, tech, vintage, output_comm, factor FROM LimitAnnualCapacityFactor WHERE operator = "le"'
    , conn
)
df_dem = pd.read_sql_query('SELECT region, period, commodity, demand FROM Demand WHERE period = 2025', conn)
df_lsc = pd.read_sql_query('SELECT region, period, tech, vintage, fraction FROM LifetimeSurvivalCurve', conn).set_index(['region','period','tech','vintage'])
for region, tech, vintage in df_existing[['region','tech','vintage']].values:
    mpl = min(1, (vintage + lifetime_process.get((region, tech, vintage), 0) - 2025) / 5)
    if (region, 2025, tech, vintage) in df_lsc.index:
        df_existing.loc[
            (df_existing['region'] == region) & (df_existing['tech'] == tech) & (df_existing['vintage'] == vintage),
            'capacity'
        ] *= df_lsc.loc[(region, 2027, tech, vintage), 'fraction']
    else:
        df_existing.loc[
            (df_existing['region'] == region) & (df_existing['tech'] == tech) & (df_existing['vintage'] == vintage),
            'capacity'
        ] *= mpl

# Vectorized approach: merge all dataframes
result = df_acf.merge(df_existing, on=['region', 'tech', 'vintage'], how='left')
result = result.merge(df_c2a, on=['region', 'tech'], how='left')
result['c2a'] = result['c2a'].fillna(1)  # Fill missing c2a values with 1
result['min_output'] = result['capacity'] * result['factor'] * result['c2a']
result = result.groupby(['region','output_comm'])['min_output'].sum().reset_index()
result = result.merge(df_dem, left_on=['region', 'output_comm'], 
                      right_on=['region', 'commodity'], how='left')
result['satisfaction'] = result['min_output'] / result['demand'] * 100
result['satisfaction'] = result['satisfaction'].round(0)
result = result.sort_values('satisfaction', ascending=True)

result.to_csv('demand_satisfaction.csv', index=False)

# Find infeasible cases
print(
    'Existing capacity * c2a * minacf > demand:\n',
    'region | tech | demand_output | period | demand_name | annual_demand | output % of demand'
)
infeasible = result[result['satisfaction'] > 100]
for _, row in infeasible.iterrows():
    print([el for el in row[:-1]] + [f"{int(row['satisfaction'])}%"])

conn.close()