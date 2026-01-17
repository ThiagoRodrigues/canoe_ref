import pandas as pd
import sqlite3
import db_mgmt as mgmt


def impose_flex_constraints(db_path):
    LimitActivity = pd.read_csv("dbs/LimitActivity.csv")

    # importers = ['F_IMP_DSL', 'F_IMP_GSL']
    # regions = ['ON']
    # periods = [int(i) for i in range(2025, 2051,5)]
    # data_id = [f'INDHR{region}001' for region in regions]

    # for region in regions:

    # print(periods)

    data_dict = {'LimitActivity': LimitActivity}

    mgmt.update_sqlite(db_path, data_dict)


    # 
    # conn = sqlite3.connect(db_path)
    # for table_name, df in data.items():
    #     df.to_sql(table_name, conn, if_exists='append', index=False)
    # conn.close()
