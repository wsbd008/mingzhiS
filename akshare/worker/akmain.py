# -*- coding: utf-8 -*-
"""
Created on Tue May  4 11:40:01 2021

@author: yuduo
"""

import os, io
import datetime
import pandas as pd
import akshare as ak
import tushare as ts
import multiprocessing
import json
import logging
import time

DEBUG = 0
USE_DATABASE = 0
USE_MULTITHREAD = 1

def getRoot():
    rootPath = os.path.dirname( os.path.realpath(__file__) )
    return rootPath + '/'

def get_database_path():
    __database_path__ = '../database/'
    return getRoot() + __database_path__

# list_df has at least prefix('sh' or 'sz'), code, name
def ak_get_list_df():
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
def ak_get_detailed_df(row, start_date, end_date, adjust):
    # through akshare
    symbol = row['prefix'] + row['code']
    df = ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)
    # adjust index and date
    #df['date'] = df.index
    df['date'] = pd.to_datetime(df['date'])
    #df.set_index(pd.Index(range(0, len(df.index))), inplace=True)
    
    res_df = pd.DataFrame()
    requited_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    res_df[requited_columns] = df[requited_columns]
    
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

def tu_get_detailed_df(row, start_date, end_date, adjust, database_path, ktype = 'D'):
    tushare_datetime_format = "%Y-%m-%d"
    code = str(row['code'])
    
    #df = ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)
    start_date_str = start_date.strftime(tushare_datetime_format)
    end_date_str = end_date.strftime(tushare_datetime_format)
    df = ts.get_hist_data(code, start_date_str, end_date_str, ktype)
    # adjust index and date
    df['date'] = df.index
    df['date'] = pd.to_datetime(df['date'])
    df.set_index(pd.Index(range(0, len(df.index))), inplace=True)
    
    res_df = pd.DataFrame()
    required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    res_df[required_columns] = df[required_columns]
    
    def get_macd(close, short = 12, long = 26, mid = 9):
        """
        根据数据约定，最新的数据在最前，所以先逆序，计算好macd后再逆序
        """
        series = close.iloc[::-1]  # 逆序
        
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
        
        return data[[difTitle,deaTitle,macdTitle]].iloc[::-1] # 逆序
    
    macd = get_macd(res_df['close'])
    res_df = pd.concat([res_df, macd], axis=1)
    res_df.set_index(pd.Index(range(0, len(res_df.index))), inplace=True)    
    
    code_file_path = database_path + code + ktype + ".csv"  
    res_df.to_csv(code_file_path, index=False)
    return  res_df

def sync_detail( row, poolDict, start_date, end_date, adjust, database_path):
    for ktype in ['D', 'W', 'M']:
        code = str(row['code'])
        dict_key = code + ktype
        poolDict[dict_key] = tu_get_detailed_df(row, start_date, end_date, adjust, database_path, ktype)
    return

def get_detailed_df_with_pool(last_sync_date, current_sync_date):
    start_date = last_sync_date
    end_date = current_sync_date
    adjust = 'qfq'
    database_path = get_database_path()
    
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    manager = multiprocessing.Manager()
    poolDict = manager.dict()
    for index, row in list_df.iterrows():
        pool.apply_async(func = sync_detail, args = (row, poolDict,  
                                                     start_date, end_date, adjust, database_path ))
    pool.close()
    pool.join()
    
    return poolDict

def dump_to_py_obj(code_list, list_df, detailed_dfs):
    py_obj = {}
    for i in range(len(code_list)):
        code = code_list[i]
        dfs_key = code + 'D'
        df = detailed_dfs[dfs_key]
        df = df.head(30).iloc[::-1]
        
        stock_info = {}
                
        date_list = [datetime.datetime.strftime(d, datetime_format) for d in df['date'].to_list()]
        stock_info['date'] = date_list
        
        for item in ['name', 'prefix']:
            item_content = list_df[list_df['code']==code][item].iloc[0]
            stock_info[item] = item_content
        
        for item in ['open', 'high', 'low', 'close', 'dif', 'dea', 'macd', 'volume']:
            item_list = df[item].to_numpy().tolist()
            stock_info[item] = item_list
            
        py_obj[code] = stock_info
    return py_obj        
    
def dumpToJson(code_list, list_df, detailed_dfs):    
    py_obj = dump_to_py_obj(code_list, list_df, detailed_dfs)

    dump_folder = '../snapshot/'
    if (not os.path.exists(dump_folder)):
        os.makedirs(dump_folder)
    json_file = dump_folder + 'snapshot.json'
    
    with open(json_file, "w", encoding='utf-8') as fout:
        json.dump(py_obj, fout, ensure_ascii = False)
    
    return

__database_flag_file__ = 'last-sync-record.txt'
datetime_format = "%Y/%m/%d"

def database_last_sync_date():
    database_flag_file = get_database_path() + __database_flag_file__
    fin = open(database_flag_file, "r")
    last_sync_date_str = fin.readline()
    fin.close()
    last_sync_date = datetime.datetime.strptime(last_sync_date_str, datetime_format)
    return last_sync_date
    
def database_is_valid():
    __start_date__ = '2020/01/01'
    
    database_path = get_database_path()
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
        return False

    last_sync_date = database_last_sync_date()
    current_sync_date = datetime.datetime.now()
    
    if (current_sync_date.date() == last_sync_date.date()):
        return True
    else:
        return False

def mark_database_valid():
    database_flag_file = get_database_path() + __database_flag_file__
    fout = open(database_flag_file, "w")
    current_sync_date = datetime.datetime.now()
    fout.write(current_sync_date.strftime(datetime_format))
    fout.close()    

def get_list_df():
    list_df = pd.DataFrame()
    __list_file__ = "list.csv"
    list_file_path = get_database_path() + __list_file__
    if database_is_valid():
        print('*** sync lists from database ***')
        
        list_df = pd.read_csv(list_file_path)
        list_df['code'] = list_df['code'].apply(lambda x : format(str(x), '0>6'))
    else:
        print('*** sync lists from network ***')
        # out of date, sync and save to file    
        list_df = ak_get_list_df()
        list_df.to_csv(list_file_path, index=False)
    return list_df

def get_detailed_dfs(list_df):
    detailed_dfs = {}
    if database_is_valid():
        print('*** sync details from database ***')
        database_path = get_database_path()       
        for index, row in list_df.iterrows():
            for ktype in ['D', 'W', 'M']:
                code = row['code'] + ktype
                code_file_path = database_path + str(code) + ".csv"
                code_df = pd.read_csv(code_file_path)
                code_df['date'] = pd.to_datetime(code_df['date'])
                detailed_dfs[code] = code_df
    else:
        print('*** sync details from network ***')
        last_sync_date = database_last_sync_date()
        current_sync_date = datetime.datetime.now()
        detailed_dfs = get_detailed_df_with_pool(last_sync_date, current_sync_date)
    
    mark_database_valid()
    return detailed_dfs

def tu_get_realtime_df():
    df = ts.get_today_all()
    df['volume'] = df['volume'] / 100
    df['close'] = df['trade']
    df['date'] = datetime.datetime.now().strftime(datetime_format)
    df[['dif', 'dea', 'macd']] = 0
    res_df = pd.DataFrame()
    required_columns = ['date','code', 'open', 'high', 'low', 'close', 'volume', 'dif', 'dea', 'macd']
    res_df[required_columns] = df[required_columns]
    
    return res_df

def tu_get_realtime_df_st(list_df):
    res = pd.DataFrame()
    res_dict = {}
    for index, row in list_df.iterrows():
        code = row['code']
        df = ts.get_realtime_quotes(code)
        res_dict[code] = df
    res = pd.concat(list(res_dict.values()))
    return res

def sync_realtime(row, poolDict):
    code = row['code']
    df = ts.get_realtime_quotes(code)
    poolDict[code] = df

def tu_get_realtime_df_mt(list_df):
    print('*** get realtime quotes ***')
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    manager = multiprocessing.Manager()
    poolDict = manager.dict()
    for index, row in list_df.iterrows():
        pool.apply_async(func = sync_realtime, args = (row, poolDict))
    pool.close()
    pool.join()
    res = pd.concat(list(poolDict.values()))
    res[['dif', 'dea', 'macd']] = 0
    res['volume'] = res['volume'].apply(lambda x : int(x) / 100)
    res['close'] = res['price']
    return res[['date','code', 'open', 'high', 'low', 'close', 'volume', 'dif', 'dea', 'macd']]

def get_realtime_df():
    rt_df = tu_get_realtime_df()
    return rt_df

def merge_dfs(detailed_dfs, realtime_df):
    print('*** merging realtime df ***')
    new_dfs = {}
    for (code, df) in detailed_dfs.items():
        row_df = realtime_df[realtime_df['code']==code]
        new_df = pd.concat([row_df, df])
        new_df.set_index(pd.Index(range(0, len(new_df.index))), inplace=True)        
        new_dfs[code] = new_df[['date', 'open', 'high', 'low', 'close', 'volume', 'dif', 'dea', 'macd']]
    return new_dfs

def d_filter(detailed_dfs, code : str):
    ck = code + 'D'
    df = detailed_dfs[ck]
    dif = df['dif']
    macd = df['macd']
    try:
        if (macd[0] < 0 and macd[1] < 0 and dif[0] < 0 and (macd[0] - macd[1] > abs(macd[0]))):
            return True
        else:
            return False
    except:
        return False
def w_filter(detailed_dfs, code : str):
    ck = code + 'W'
    df = detailed_dfs[ck]
    dif = df['dif']
    macd = df['macd']
    try:
        if (macd[0] > 0 and macd[1] < 0 and dif[0] < 0):
            return True
        else:
            return False
    except:
        return False    
def m_filter(detailed_dfs, code : str):
    ck = code + 'M'
    df = detailed_dfs[ck]
    dif = df['dif']
    macd = df['macd']
    try:
        if (macd[0] > 0 and macd[1] < 0 and dif[0] < 0):
            return True
        else:
            return False
    except:
        return False   
def macd_filter(detailed_dfs, code : str):
    good = True
    good = good and d_filter(detailed_dfs, code)
    good = good and w_filter(detailed_dfs, code)
    #good = good and m_filter(detailed_dfs, code)
    return good

def volumne_filter(detailed_dfs, code):
    if DEBUG:
        print('*** volumn check for {} ***'.format(code))
    df = detailed_dfs[code]
    volume_column = df['volume']

    try:
        if volume_column[0] > (volume_column[1] * 1.5):
            return True
    except:
        return False
    return False
def trim_list_df(list_df, detailed_dfs):
    print('*** trim list df ***')
    codes = list(detailed_dfs.keys())
    list_df = list_df[list_df['code'].isin(codes)]
    __list_file__ = "list.csv"
    list_file_path = get_database_path() + __list_file__
    list_df.to_csv(list_file_path, index=False)
    return list_df

##############################################################################
"""
main logic
- sync database
- do calculation: 1. macd 
- filter based on 2 criteria: 1. macd. 2. volumn
- print result
"""

##############################################################################
list_df = pd.DataFrame()
detailed_dfs = {}
# - sync database: check containing folder and last sync record
if __name__ == "__main__":
    list_df = get_list_df()    
    if DEBUG:
        list_df = list_df.head(10)
    print('list has {} items\n'.format(len(list_df)))
    
    time1 = time.time()
    detailed_dfs = get_detailed_dfs(list_df)
    time2 = time.time()
    print('time: {}'.format(time2-time1))
    print('history dfs has {} items\n'.format(len(detailed_dfs)))

    # list_df = trim_list_df(list_df, detailed_dfs)
    # print('list has {} items after trim\n'.format(len(list_df)))
    
    # time1 = time.time()
    # realtime_df = tu_get_realtime_df_mt(list_df)
    # time2 = time.time()
    # print('time: {}'.format(time2-time1))
    # print('realtime df has {} items\n'.format(len(realtime_df)))

    # merged_dfs = merge_dfs(detailed_dfs, realtime_df)
    # print('merged dfs has {} items\n'.format(len(merged_dfs)))
    merged_dfs = detailed_dfs
    
    #debug_file = getRoot() + 'debug.csv'
    #merged_dfs['600000'].to_csv(debug_file, index=False)
    # TODO: dump a snapshot of lists? details?
    
    print('\n*** core calculation start ***')
    ##############################################################################
    # - do calculation
    
    
    ##############################################################################
    # - filter
    candidates = []
    
    count = len(list_df)
    current = 0
    for index, row in list_df.iterrows():
        code = row['code']
        if (all(map(lambda filer: filer(merged_dfs, code), [macd_filter]) )):
            candidates.append(code)
        if DEBUG:
            current += 1
            print('{}\t / {}\r'.format(current, count))
            
    ##############################################################################
    # - print result
    print('*** core calculation result: ***')
    print(candidates)
   
    dumpToJson(candidates, list_df, detailed_dfs)
