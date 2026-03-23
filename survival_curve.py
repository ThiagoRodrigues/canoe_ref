import pandas as pd
import db_mgmt as mgmt 
from pathlib import Path


def adjust_survival_curve(db_path, files, dbs_dir="dbs"):
    

    dbs_dir = Path(dbs_dir)
    data_dict = {f: pd.read_csv(dbs_dir / files[f]) for f in files.keys()}
    regions = data_dict['ExistingCapacity']['region'].unique()

    df = data_dict["LifetimeTech"]

    regions_df = pd.DataFrame({"region": regions})

    df_expanded = (
        df.drop(columns="region")
        .merge(regions_df, how="cross")
    )

    data_dict["LifetimeTech"] = df_expanded.copy()


    mgmt.update_sqlite(db_path, data_dict)

def main():
    db_path = 'dbs/canoe_ref.sqlite'


if __name__ == "__main__":
    main()

