import pandas as pd
import db_mgmt as mgmt 


def adjust_survival_curve(db_path):
    files = ['TechGroup.csv', 'TechGroupMember.csv', 'LifetimeTech.csv', 'LifetimeSurvivalCurve.csv', 'LimitGrowthNewCapacity.csv', 'ExistingCapacity.csv']
    tables = [pd.read_csv(f'dbs/{file}') for file in files]

    data_dict = {
        'TechGroup': tables[0],
        'TechGroupMember': tables[1],
        'LifetimeTech': tables[2],
        'LifetimeSurvivalCurve': tables[3],
        'LimitGrowthNewCapacity': tables[4],
        'ExistingCapacity': tables[5],
    }

    data_dict['CostVariable'] = adjust_var_costs(data_dict['LifetimeTech'])

    mgmt.update_sqlite(db_path, data_dict)


def adjust_var_costs(LifetimeTech):
    cv = pd.read_csv('dbs/CostVariable.csv')
    # lifetime_tech = pd.read_csv('dbs/LifetimeTech.csv')

    techs = LifetimeTech['tech'].unique()
    # print(techs)
    # print(cv.head())

    # cv = cv.loc[cv['tech'].isin(techs)].copy()
    data_to_add = {'region': [], 'period': [], 'vintage': [], 'cost': [], 'tech': [],
                   'notes': [], 'data_source': [], 'dq_cred': [], 'dq_geog': [],
                   'dq_struc': [], 'dq_tech': [], 'dq_time': [], 'data_id': []}
    for tech in techs:
        cv_tech = cv.loc[cv['tech'] == tech].copy()
        periods = [int(p) for p in range(2025, 2051, 5)]
        vintages = cv_tech['vintage'].unique()
        for period in periods:
            for vintage in vintages:
                if vintage <= period:    
                    cv_subset = cv_tech.loc[(cv_tech['period'] == period) & (cv_tech['vintage'] == vintage)]
                    if len(cv_subset) < 1:
                        # print(vintage, period, tech)
                        cv_cost = cv_tech['cost'].max()
                        data_to_add['period'].append(period)
                        data_to_add['vintage'].append(vintage)
                        data_to_add['cost'].append(cv_cost)
                        data_to_add['tech'].append(tech)
                        data_to_add['region'].append(cv_tech.iloc[0]['region'])
                        data_to_add['notes'].append('Added to adjust variable costs based on survival curve')
                        data_to_add['data_source'].append(cv_tech.iloc[0]['data_source'])
                        data_to_add['dq_cred'].append(None)
                        data_to_add['dq_geog'].append(None)
                        data_to_add['dq_struc'].append(None)
                        data_to_add['dq_tech'].append(None)
                        data_to_add['dq_time'].append(None)
                        data_to_add['data_id'].append(cv_tech.iloc[0]['data_id'])
    
    CostVariable = pd.DataFrame(data_to_add)
    return CostVariable

def main():
    db_path = 'dbs/canoe_ref.sqlite'

    adjust_var_costs(db_path)


if __name__ == "__main__":
    main()

