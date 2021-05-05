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

# each detailed stock info has at least date, close, volume, macd, diff, dea
def get_detailed_df(row, start_date, end_date, adjust):
    # through akshare
    symbol = row['prefix'] + row['code']
    df = ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)
    
    res_df = pd.DataFrame()
    res_df[['close', 'volume']] = df[['close', 'volume']]
    
    def get_macd(close, short = 12, long = 26, mid = 9):
        """
        根据数据约定，最新的数据在最前，所以先逆序，计算好macd后再逆序
        """
        series = close#.iloc[::-1]  # 逆序
        
        #计算短期的ema，使用pandas的ewm得到指数加权的方法，mean方法指定数据用于平均
        s1 = series.ewm(span=short).mean()
        #计算长期的ema，方式同上
        s2 = series.ewm(span=long).mean()
        data = pd.DataFrame({'sema':s1,'lema':s2})
        #填充为na的数据
        #data.fillna(0,inplace=True)
        
        #计算dif，加入新列data_dif
        difTitle = 'dif'
        deaTitle = 'dea'
        macdTitle = 'macd'
        data[difTitle]=data['sema']-data['lema']    
        data[deaTitle]=pd.Series(data[difTitle]).ewm(span=mid).mean()
        data[macdTitle]=round(2*(data[difTitle]-data[deaTitle]), 2)
        #data.fillna(0,inplace=True)
        
        return data[[difTitle,deaTitle,macdTitle]]
    
    macd = get_macd(res_df['close'])
    res_df = pd.concat([res_df, macd], axis=1)
    res_df = res_df.iloc[::-1] # 逆序, akshare返回数据按日期排列
    res_df.set_index(pd.Index(range(0, len(res_df.index))), inplace=True)
    return  res_df

##############################################################################
"""
main logic
- sync database
- do calculation: 1. macd 
- filter based on 2 criteria: 1. macd. 2. volumn
- print result
"""

##############################################################################
# - sync database: check containing folder and last sync record

__database_flag_path__ = '\\database\\'
__database_flag_file__ = 'last-sync-record.txt'
__start_date__ = '2020/01/01'

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

datetime_format = "%Y/%m/%d"
akshare_datetime_format = "%Y%m%d"

fin = open(database_flag_file, "r")
last_sync_date_str = fin.readline()
last_sync_date = datetime.datetime.strptime(last_sync_date_str, datetime_format)
current_sync_date = datetime.datetime.now()

"""
sync database content
1. sync lists and basic info, saved in list_df
2. sync detailed info, saved in a map: detailed_dfs, use code as key
"""
__list_file__ = "list.csv"
list_file_path = database_path + __list_file__

list_df = DataFrame()
detailed_dfs = {}
if (current_sync_date.date() == last_sync_date.date()):
    # up to date, just read from file
    list_df = pd.read_csv(list_file_path)
else:
    # out of date, sync and save to file
    
    # 1. sync lists and basic info
    # list_df has at least 3 columns: prefix('sh' or 'sz'), code, name
    list_df = get_list_df()
    list_df.to_csv(list_file_path)
    
    # 2. sync detailed info
    # each detailed stock intf has at least 4 columns: date, close, macd, volumn 
    if DEBUG:
        debug_count = 3
        list_df = list_df.head(debug_count)        
    
    count = len(list_df)
    current = 0
    for index, row in list_df.iterrows():
        code = row['code']
        detailed_dfs[code] = get_detailed_df(row, last_sync_date.strftime(akshare_datetime_format),
                                             current_sync_date.strftime(akshare_datetime_format), 'qfq')
        if DEBUG:
            current += 1
            print('{}\t / {}\r'.format(current, count))
    print('\n')
    
    fout = open(database_flag_file, "w")
    fout.write(current_sync_date.strftime(datetime_format))
    fout.close()
    
    if DEBUG:
        print("synced {} detailed dfs".format(count))
        #print(detailed_dfs)    

##############################################################################
# - do calculation


##############################################################################
# - filter
candidates = []
def macd_filter(code):
    return True
def volumne_filter(code):
    return True

for index, row in list_df.iterrows():
    code = row['code']
    if (all(map(lambda filer: filer(code), [macd_filter, volumne_filter]) )):
        candidates.append(code)
    
    
    
    
    
##############################################################################
# - print result
print(candidates)
