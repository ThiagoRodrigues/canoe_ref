import pandas as pd
import db_mgmt as mgmt


def fix_imports(db_path):
    data = mgmt.sqlite_to_dfs(db_path)
    C_var = data['CostVariable'].copy()


    techs_cost_var = C_var.loc[(C_var['tech'].str.contains('F_'))&(~C_var['tech'].str.contains('DV_')), 'tech'].unique()
    print(techs_cost_var)

    replace = {tech: tech[:2]+'IMP'+tech[3:] for tech in techs_cost_var if tech!="F_IMP_CO"}
    C_var['new_tech'] = C_var['tech'].replace(replace)
    print(C_var[['tech', 'new_tech']].drop_duplicates().reset_index(drop=True))

    # a = 1/0

    # Group by the relevant columns and count how many rows per group
    duplicates = (
        C_var.groupby(['new_tech', 'period', 'region', 'vintage'])
        .size()
        .reset_index(name='count')
    )

    # Filter groups with more than one entry
    non_unique = duplicates.loc[duplicates['count'] > 1, 'new_tech'].unique()


    # If you still want a set
    non_unique_entries = set(non_unique)


    # Get indices of all rows in C_var whose new_tech is in the non-unique set
    dupe_indices = C_var.index[C_var['new_tech'].isin(non_unique_entries)]

    # If you want them as a list:
    dupe_indices = dupe_indices.tolist()



    cols = ['new_tech', 'period', 'region', 'vintage']

    dupe_indices = C_var.index[
        C_var['new_tech'].isin(non_unique_entries) &
        C_var.duplicated(subset=cols, keep=False)
    ].tolist()

    df = C_var.loc[dupe_indices]
    df_to_be_appended = pd.DataFrame()
    for period in df['period'].unique():
        df_period = df.loc[df['period'] == period]
        for tech in non_unique_entries:
            df_low = df_period.loc[df_period['new_tech'] == tech]
            # get rows from df_low with the minimum cost for each (region, period, vintage)
            group_cols = ['region', 'period', 'vintage']
            idx_min = df_low.groupby(group_cols)['cost'].idxmin()
            df_low_min = df_low.loc[idx_min].sort_values(group_cols).reset_index(drop=True)

            # show a quick summary
            # print(f"Selected {len(df_low_min)} rows (one per unique {group_cols})")
            df_low_min.head()

            # Compute the difference between the lowest cost and the other entries in df_low
            min_cost = df_low_min['cost'].min()
            df_low_diff = df_low.copy()
            df_low_diff['cost'] = df_low_diff['cost'] - min_cost

            # Drop the entry where cost == 0 (the lowest cost entry)
            df_low_diff = df_low_diff[df_low_diff['cost'] != 0].copy()

            # Add a row with tech replaced by new_tech and cost set to the lowest cost
            new_row = df_low_min.iloc[0].copy()
            new_row['tech'] = new_row['new_tech']
            new_row['cost'] = min_cost

            # Append the new row
            df_low_diff = pd.concat([df_low_diff, pd.DataFrame([new_row])], ignore_index=True)
            df_to_be_appended = pd.concat([df_to_be_appended, df_low_diff], ignore_index=True)
            # print(df_low_diff)

    df1 = df_to_be_appended.set_index(['region', 'period', 'vintage', 'tech']).copy()
    df2 = C_var.set_index(['region', 'period', 'vintage', 'tech']).copy()
    indexes_missing = []
    for i in range(len(df1.index.isin(df2.index))):
        if not df1.index.isin(df2.index)[i]:
            #print(df1.index[i])
            indexes_missing.append(df1.index[i])

    cvar = df2.loc[~df2.index.isin(df1.index)].copy().reset_index()

    techs_cost_var = cvar.loc[(cvar['tech'].str.contains('F_'))&(~cvar['tech'].str.contains('DV_')), 'tech'].unique()
    replace = {tech: tech[:2]+'IMP'+tech[3:] for tech in techs_cost_var if tech!="F_IMP_CO"}
    cvar['tech'] = cvar['tech'].replace(replace)
    cvar = pd.concat([cvar, df1.reset_index()], ignore_index=True)
    cvar = cvar.drop(columns=['new_tech'])

    data_dict = {'CostVariable': cvar}

    mgmt.update_sqlite(db_path, data_dict)


