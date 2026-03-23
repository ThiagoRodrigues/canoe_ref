import pandas as pd
import db_mgmt as mgmt


ex_cap = pd.read_csv('dbs/ExistingCapacity_ALL.csv')
eff = pd.read_csv('dbs/Efficiency_NEW_ALL.csv')

db_path = 'dbs/canoe_all.sqlite'
data = mgmt.sqlite_to_dfs(db_path)

df = data['TimePeriod'].copy()
periods = df.loc[df['flag']=='f', 'period'].tolist()


print(eff.loc[(eff['tech'] == 'T_LDV_C_DSL_EX') & (eff['region'] == 'AB')])
print(periods)