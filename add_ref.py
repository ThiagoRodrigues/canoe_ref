import pandas as pd
import sqlite3
import shutil
import db_mgmt as mgmt

def add_refinery_to_db(db_core, db_path):
    print('\nAdding Refinery to Database...\n')

    print('Loading refinery data from CSV files...')
    period = pd.read_csv('dbs/ref_att_period.csv').period.to_list()
    output = pd.read_csv('dbs/ref_att_output.csv')
    input = pd.read_csv('dbs/ref_att_input.csv')
    region = pd.read_csv('dbs/ref_att_region.csv').region.to_list()
    tech = pd.read_csv('dbs/ref_att_tech.csv')

    print('Processing refinery data...')
    inflow = {input.loc[i, 'input_comm']: input.loc[i, 'input_flow'] for i in range(len(input))}
    outflow = {output.loc[i, 'output_comm']: output.loc[i, 'output_flow'] for i in range(len(output))}  


    Technology = {}
    for i in range(len(tech)):
        Technology[tech.loc[i, 'attribute']] = tech.loc[i, 'value']
    Technology = pd.DataFrame(Technology, index=[0])

    Efficiency = {
        'region': [],
        'input_comm': [],
        'tech': [],
        'vintage': [],
        'output_comm': [],
        'efficiency': [],
        'notes': [],
        'data_source': [],
        'dq_cred': [],
        'dq_geog': [],
        'dq_struc': [],
        'dq_tech': [],
        'dq_time': [],
        'data_id': []
    }

    for reg in region: 
        for input_comm in inflow.keys():
            for output_comm in outflow.keys():
                Efficiency['efficiency'].append(outflow[output_comm]/inflow[input_comm])
                Efficiency['input_comm'].append(input_comm)
                Efficiency['output_comm'].append(output_comm)
                Efficiency['region'].append(reg)
                Efficiency['tech'].append(Technology.loc[0, 'tech'])
                Efficiency['vintage'].append(2025)
                Efficiency['data_id'].append(f'IND{reg}HR001')
                Efficiency['notes'].append(None)
                Efficiency['data_source'].append(None)
                Efficiency['dq_cred'].append(None)
                Efficiency['dq_geog'].append(None)
                Efficiency['dq_struc'].append(None)
                Efficiency['dq_tech'].append(None)
                Efficiency['dq_time'].append(None)  
                

    LimitTechInputSplitAnnual = {'region': [],
                        'period': [], 
                        'input_comm': [], 
                        'tech': [], 
                        'operator': [], 
                        'proportion': [], 
                        'notes': [], 
                        'data_source': [], 
                        'dq_cred': [], 
                        'dq_geog': [], 
                        'dq_struc': [], 
                        'dq_tech': [], 
                        'dq_time': [], 
                        'data_id': []}

    LimitTechOutputSplitAnnual = {'region': [],
                            'period': [], 
                            'output_comm': [], 
                            'tech': [], 
                            'operator': [], 
                            'proportion': [], 
                            'notes': [], 
                            'data_source': [], 
                            'dq_cred': [], 
                            'dq_geog': [], 
                            'dq_struc': [], 
                            'dq_tech': [], 
                            'dq_time': [], 
                            'data_id': []}

    LifetimeTech = {'region': [],
                    'tech': [],
                    'lifetime': [],
                    'notes': [],
                    'data_source': [],
                    'dq_cred': [],
                    'dq_geog': [],
                    'dq_struc': [],
                    'dq_tech': [],
                    'dq_time': [],
                    'data_id': []
                    }

    for reg in region:
        LifetimeTech['region'].append(reg)
        LifetimeTech['tech'].append(Technology.loc[0, 'tech'])
        LifetimeTech['lifetime'].append(50) # assumed lifetime of 50 years
        LifetimeTech['data_id'].append(f'IND{reg}HR001')
        LifetimeTech['notes'].append(None)
        LifetimeTech['data_source'].append(None)
        LifetimeTech['dq_cred'].append(None)
        LifetimeTech['dq_geog'].append(None)
        LifetimeTech['dq_struc'].append(None)
        LifetimeTech['dq_tech'].append(None)
        LifetimeTech['dq_time'].append(None) 


    for year in period: 
        for reg in region: 
            for input_comm in inflow.keys():
                LimitTechInputSplitAnnual['region'].append(reg)
                LimitTechInputSplitAnnual['period'].append(year)
                LimitTechInputSplitAnnual['input_comm'].append(input_comm)
                LimitTechInputSplitAnnual['tech'].append(Technology.loc[0, 'tech'])
                LimitTechInputSplitAnnual['operator'].append('ge')
                LimitTechInputSplitAnnual['proportion'].append(inflow[input_comm]/sum(inflow.values()))
                LimitTechInputSplitAnnual['data_id'].append(f'IND{reg}HR001')
                LimitTechInputSplitAnnual['notes'].append(None)
                LimitTechInputSplitAnnual['data_source'].append(None)
                LimitTechInputSplitAnnual['dq_cred'].append(None)
                LimitTechInputSplitAnnual['dq_geog'].append(None)
                LimitTechInputSplitAnnual['dq_struc'].append(None)
                LimitTechInputSplitAnnual['dq_tech'].append(None)
                LimitTechInputSplitAnnual['dq_time'].append(None)  

            for output_comm in outflow.keys():
                LimitTechOutputSplitAnnual['region'].append(reg)
                LimitTechOutputSplitAnnual['period'].append(year)
                LimitTechOutputSplitAnnual['output_comm'].append(output_comm)
                LimitTechOutputSplitAnnual['tech'].append(Technology.loc[0, 'tech'])
                LimitTechOutputSplitAnnual['operator'].append('ge')
                LimitTechOutputSplitAnnual['proportion'].append(outflow[output_comm]/sum(outflow.values()))
                LimitTechOutputSplitAnnual['data_id'].append(f'IND{reg}HR001')
                LimitTechOutputSplitAnnual['notes'].append(None)
                LimitTechOutputSplitAnnual['data_source'].append(None)
                LimitTechOutputSplitAnnual['dq_cred'].append(None)
                LimitTechOutputSplitAnnual['dq_geog'].append(None)
                LimitTechOutputSplitAnnual['dq_struc'].append(None)
                LimitTechOutputSplitAnnual['dq_tech'].append(None)
                LimitTechOutputSplitAnnual['dq_time'].append(None)

    Efficiency = pd.DataFrame(Efficiency)                
    LimitTechInputSplitAnnual = pd.DataFrame(LimitTechInputSplitAnnual)
    LimitTechOutputSplitAnnual = pd.DataFrame(LimitTechOutputSplitAnnual)
    print('Loading crude oil data from CSV files...')
    

    crude = {'Technology': pd.read_csv('dbs/crude_oil_tech.csv')} 
    crude['Efficiency'] = pd.read_csv('dbs/crude_oil_efficiency.csv')
    crude['Commodity'] = pd.read_csv('dbs/crude_oil_commodity.csv')
    crude['CostVariable'] = pd.read_csv('dbs/crude_oil_costvariable.csv') 
    crude['EmissionActivity'] = pd.read_csv('dbs/crude_oil_emissionactivity.csv')
    print('Combining refinery and crude oil data...')
    
    Efficiency = pd.concat([Efficiency, crude['Efficiency']], ignore_index=True)
    Technology = pd.concat([Technology, crude['Technology']], ignore_index=True)

    data = {
        'Technology': Technology,
        'Efficiency': Efficiency,
        'LimitTechInputSplitAnnual': LimitTechInputSplitAnnual,
        'LimitTechOutputSplitAnnual': LimitTechOutputSplitAnnual,
        'LifetimeTech': pd.DataFrame(LifetimeTech),
        'CostVariable': crude['CostVariable'],
        'Commodity': crude['Commodity'],
        'EmissionActivity': crude['EmissionActivity']
    }

    # Remove refining technologies from the reference database
    print('Cleaning existing refining data from database...')
    shutil.copy2(db_core, db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all table names
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        # Check if table has a 'tech' column
        cur.execute(f"PRAGMA table_info({table});")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'tech' in columns:
            print(f"Cleaning table: {table}")
            cur.execute(f"DELETE FROM {table} WHERE tech LIKE '%I_REFINING%';")
        else:
            print(f"Skipping table (no tech column): {table}")
            
    cur.execute(f"DELETE FROM Commodity WHERE name LIKE '%I_d_refining%';")
    cur.execute(f"DELETE FROM Demand WHERE commodity LIKE '%I_d_refining%';")
    conn.commit()
    conn.close()

    print('Adding new refinery data to the reference database...')

    mgmt.update_sqlite(db_path, data)

    print('\nRefinery Successfully Added to Database\n')


