import pandas as pd
import sqlite3
import db_mgmt as mgmt

def add_clustering(data_id = 'TRPHR001'):
    vehicle_grouping = pd.read_csv("dbs/vehicle_grouping.csv")
    modes = [label for mode in ['HDV', 'LDV', 'MDV'] for label in [f'{mode}', f'{mode} ZEV', f'{mode} N-ZEV']]

    TechGroup = pd.DataFrame({'group_name': modes})
    TechGroup['notes'] = None
    TechGroup['data_id'] = data_id

    TechGroup = TechGroup.loc[TechGroup['group_name'].isin(modes)].copy()
    TechGroup.reset_index(inplace=True, drop=True)
    TechGroupMember = vehicle_grouping.loc[vehicle_grouping['group_name'].isin(modes), ['group_name', 'tech']].copy()
    TechGroupMember['data_id'] = data_id

    return {'TechGroup': TechGroup, 'TechGroupMember': TechGroupMember}


def add_LimitNewCapacity(share, period = [int(2025 + 5*i) for i in range(6)], region = 'ON', operator = 'ge'):
    df = pd.DataFrame({'period': period, 'share': share})
    df['region'] = region
    df['notes'] = None
    df['sub_group'] = 'LDV ZEV'
    df['super_group'] = 'LDV'
    df['data_id'] = f'TRPHR{region}001'
    df['operator'] = operator

    return df
    

def set_ZEV(min_proportion, db_path = 'dbs/canoe_ref.sqlite',):
    cluster = add_clustering()
    cluster['LimitNewCapacityShare'] = add_LimitNewCapacity(min_proportion)
    mgmt.update_sqlite(db_path, cluster)


def main():
    min_proportion = [0, 0.6, 1, 1, 1, 1]
    set_ZEV(min_proportion)
    print('\nClustering Successfully Executed\n')

if __name__ == '__main__':
    main()