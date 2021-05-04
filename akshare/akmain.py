# -*- coding: utf-8 -*-
"""
Created on Tue May  4 11:40:01 2021

@author: yuduo
"""

import os
import datetime
import pandas as pd
import akshare as ak

DEBUG = 1

def getRoot():
    rootPath = os.path.dirname( os.path.realpath(__file__) )
    return rootPath

# list_df has at least prefix('sh' or 'sz'), code, name
def get_list_df():
    # through akshare
    
    def get_sh_list_df():
        sh_indicator = ["主板A股", "科创板"]
        res_df = pd.DataFrame()
        
        for indicator in sh_indicator:
            sh_df = ak.stock_info_sh_name_code(indicator)
            df = pd.DataFrame()
            df[['code', 'name']] = sh_df[['COMPANY_CODE', 'COMPANY_ABBR']]
            res_df = res_df.append(df, ignore_index=True)
        res_df['prefix'] = 'sh'
        return res_df
    
    def get_sz_list_df():
        sz_indicator = ["A股列表"]
        res_df = pd.DataFrame()
        
        for indicator in sz_indicator:
            sh_df = ak.stock_info_sz_name_code(indicator)
            df = pd.DataFrame()
            df[['code', 'name']] = sh_df[['A股代码', 'A股简称']]
            res_df = res_df.append(df, ignore_index=True)
        res_df['prefix'] = 'sz'
        return res_df
    
    sh_df = get_sh_list_df()
    sz_df = get_sz_list_df()
    return sh_df.append(sz_df, ignore_index=True)

# each detailed stock intf has at least date, close, volume
def get_detailed_df(row):
    # through akshare
    symbol = row['prefix'] + row['code']
    
    
        
"""
main logic
- sync database
- do calculation: 1. macd 
- filter based on 2 criteria: 1. macd. 2. volumn
- print result
"""

# - sync database

__database_flag_path__ = '\\database\\'
__database_flag_file__ = 'last-sync-record.txt'
__start_date__ = '2021/04/01'

database_path = getRoot() + __database_flag_path__
if (not os.path.exists(database_path)):
    if DEBUG:
        print('\tdababase path {} does not exists, make it...'.format(database_path))
    os.makedirs(database_path)

database_flag_file = database_path + __database_flag_file__
if (not os.path.exists(database_flag_file)):
    if DEBUG:
        print('\tdababase sync record file {} does not exists, make it...'.format(database_flag_file))
    fout = open(database_flag_file, "w")
    fout.write(__start_date__)
    fout.close()

sync_date = datetime.datetime.now()
"""
sync database
1. sync lists and basic info
2. sync detailed info
"""
__list_file__ = "list.csv"
# 1. sync lists and basic info
# list_df has at least prefix('sh' or 'sz'), code, name
list_df = get_list_df()

# 2. sync detailed info
# each detailed stock intf has at least date, close, macd, volumn 

fin = open(database_flag_file, "r")
last_sync_date = fin.readline()

detailed_dfs = {}
for row in list_df.iterrows():
    detailed_dfs[code] = get_detailed_df(row)

# - do calculation

# - filter

# - print result
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    