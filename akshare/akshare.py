# -*- coding: utf-8 -*-
"""
Created on Tue May  4 11:40:01 2021

@author: yuduo
"""

import os
import datetime

DEBUG = 1

def getRoot():
    rootPath = os.path.dirname( os.path.realpath(__file__) )
    return rootPath

def get_list_df():
                   
        
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
__start_date__ = '2010/01/01'

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
detailed_dfs = {}
for code in list_df['code']:
    detailed_dfs[code] = get_detailed_df(code)

# - do calculation

# - filter

# - print result
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    