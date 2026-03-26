import os
import shutil
import pandas as pd
import db_mgmt as mgmt
import sqlite3


def fix_imports(db_path: str) -> None:
    data = mgmt.sqlite_to_dfs(db_path)
    cvar = data["CostVariable"].copy()

    # 1) Build "new_tech" (vectorized)
    mask_import = (
        cvar["tech"].str.contains("F_", na=False)
        & ~cvar["tech"].str.contains("DV_", na=False)
        & (cvar["tech"] != "F_IMP_CO")
    )


    cvar["new_tech"] = cvar["tech"]
    cvar.loc[mask_import, "new_tech"] = (
        cvar.loc[mask_import, "tech"].str.slice(0, 2)
        + "IMP"
        + cvar.loc[mask_import, "tech"].str.slice(3)
    )

    
    # cvar.to_csv('dbs/debug.csv')    


    # 2) Identify groups that become non-unique
    key_cols = ["region", "period", "vintage", "new_tech"]
    dupe_mask = cvar.duplicated(subset=key_cols, keep=False)
    

    dup = cvar.loc[dupe_mask].copy()
    
    nondup = cvar.loc[~dupe_mask].copy()

    # print(dup.loc[dup['tech'].str.contains('NG')&(dup['region'] == 'AB')&(dup['period'] == 2025)])
    # print()
    
    # Case: No collisions
    if dup.empty:
        nondup["tech"] = nondup["new_tech"]
        out = nondup.drop(columns=["new_tech"])
        mgmt.update_sqlite(db_path, {"CostVariable": out})
        
        # Optimize after update
        _run_vacuum(db_path)
        return

    # 3) Process duplicate groups
    dup["min_cost"] = dup.groupby(key_cols)["cost"].transform("min")
    
    dup["delta_cost"] = dup["cost"] - dup["min_cost"]
    print(dup)
    delta_rows = dup# .loc[dup["delta_cost"] != 0].copy()
    delta_rows["cost"] = delta_rows["delta_cost"]
    
    
    # print(delta_rows.loc[delta_rows['tech'].str.contains('NG')&(delta_rows['region'] == 'AB')&(delta_rows['period'] == 2025)])
    
    baseline_rows = (
        dup.sort_values(key_cols)
           .drop_duplicates(subset=key_cols, keep="first")
           .copy()
    )
    baseline_rows["tech"] = baseline_rows["new_tech"]
    baseline_rows["cost"] = baseline_rows["min_cost"]
    
    # print(baseline_rows.loc[baseline_rows['tech'].str.contains('NG')&(baseline_rows['region'] == 'AB')&(baseline_rows['period'] == 2025)])

    # print(baseline_rows)
    # 4) Process non-duplicate rows
    nondup["tech"] = nondup["new_tech"]
    

    # 5) Assemble final table
    out = pd.concat([nondup, delta_rows, baseline_rows], ignore_index=True)

    # 6) Cleanup and update
    drop_cols = [c for c in ["new_tech", "min_cost", "delta_cost"] if c in out.columns]
    out = out.drop(columns=drop_cols)

    mgmt.update_sqlite(db_path, {"CostVariable": out})

    mgmt.delete_zero_cost_rows(db_path, table='CostVariable', column='cost')
    
    # Optimize after update
    _run_vacuum(db_path)

def _run_vacuum(db_path: str) -> None:
    """Helper to keep the main function clean."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
    except Exception as e:
        print(f"Warning: Could not VACUUM database at {db_path}: {e}")

def main():
    db_core = 'dbs/canoe_ALL_cm_8d.sqlite'
    db_path = f'dbs/canoe_all_fix_imports.sqlite'
    
    os.remove(db_path) if os.path.exists(db_path) else None
    shutil.copy2(db_core, db_path)
    
    fix_imports(db_path)


if __name__ == "__main__":
    main()