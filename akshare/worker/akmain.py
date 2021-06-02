# -*- coding: utf-8 -*-
"""
Created on Tue May  4 11:40:01 2021

@author: yuduo
"""

import os
import datetime
import pandas as pd
import akshare as ak
import tushare as ts
import multiprocessing
import json
import logging

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

def tu_get_realtime_df():
    df = ts.get_today_all()    
    df['close'] = df['trade']
    res_df = pd.DataFrame()
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    res_df[required_columns] = df[required_columns]
    
    return res_df

def tu_get_detailed_df(row, start_date, end_date, adjust, database_path):
    tushare_datetime_format = "%Y-%m-%d"
    code = str(row['code'])
    
    #df = ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)
    start_date_str = start_date.strftime(tushare_datetime_format)
    end_date_str = end_date.strftime(tushare_datetime_format)
    df = ts.get_hist_data(code, start_date_str, end_date_str)
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
    
    code_file_path = database_path + code + ".csv"  
    res_df.to_csv(code_file_path, index=False)
    return  res_df
    
def sync_detail( row, poolDict, start_date, end_date, adjust, database_path):
    code = str(row['code'])
    poolDict[code] = tu_get_detailed_df(row, start_date, end_date, adjust, database_path)
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

def macd_filter(code):
    df = detailed_dfs[code]
    close_column = df['close']
    open_column = df['open']
    dif = df['dif']
    macd = df['macd']
    try:
        if (close_column[0] > open_column[0]) and dif[0] < 0 and macd[0] > 0:
            return True
    except:
        return False
    return False
def volumne_filter(code):
    if DEBUG:
        print('*** volumn check for {} ***'.format(code))
    df = detailed_dfs[code]
    volume_column = df['volume']

    try:
        if volume_column[0] > (volume_column[1] * 3):
            return True
    except:
        return False
    return False
    
def dumpToJson(code_list, list_df, detailed_dfs):
    dump_folder = '../snapshot/'
    if (not os.path.exists(dump_folder)):
        os.makedirs(dump_folder)
    json_file = dump_folder + 'snapshot.json'
    fout = open(json_file, "w", encoding='utf-8')
    fout.write('{\n')
    lst_len = len(code_list)
    for i in range(lst_len):
        code = code_list[i]
        df = detailed_dfs[code]
        if len(df) < 40:
            continue
        df = df.head(30).iloc[::-1]
        
        # use code as key, type is string
        fout.write('\t"{}" : '.format(code))
        fout.write('{\n')
        # value as object
        name = list_df[list_df['code']==code]['name'].iloc[0]
        fout.write('\t\t"name" : "{}"'.format(name))
        fout.write(',\n')
        
        prefix = list_df[list_df['code']==code]['prefix'].iloc[0]
        fout.write('\t\t"prefix" : "{}"'.format(prefix))
        fout.write(',\n')
        
        date_list = [datetime.datetime.strftime(d, datetime_format) for d in df['date'].to_list()]
        fout.write('\t\t"date" : {}'.format(json.dumps(date_list)))
        fout.write(',\n')
        
        open_list = df['open'].to_numpy().tolist()
        fout.write('\t\t"open" : {}'.format(open_list))
        fout.write(',\n')
        
        high_list = df['high'].to_numpy().tolist()
        fout.write('\t\t"high" : {}'.format(high_list))
        fout.write(',\n')
        
        low_list = df['low'].to_numpy().tolist()
        fout.write('\t\t"low" : {}'.format(low_list))
        fout.write(',\n')
        
        close = df['close'].to_numpy().tolist()
        fout.write('\t\t"close" : {}'.format(close))
        fout.write(',\n')
        
        dif = df['dif'].to_numpy().tolist()
        fout.write('\t\t"dif" : {}'.format(dif))
        fout.write(',\n')
        
        dea = df['dea'].to_numpy().tolist()
        fout.write('\t\t"dea" : {}'.format(dea))
        fout.write(',\n')
        
        macd = df['macd'].to_numpy().tolist()
        fout.write('\t\t"macd" : {}'.format(macd))
        fout.write(',\n')
        
        volume = df['volume'].to_numpy().tolist()
        fout.write('\t\t"volume" : {}'.format(volume))        
        fout.write('\n')
        
        if DEBUG:
            print('i: {} / len: {}'.format(i, lst_len))
        if (i == (lst_len - 1)):
            fout.write("\t}\n")
        else:
            fout.write("\t},\n")
    fout.write('}')
    fout.close()

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
        logging.info('*** sync lists from database ***')
        
        list_df = pd.read_csv(list_file_path)
        list_df['code'] = list_df['code'].apply(lambda x : format(str(x), '0>6'))
    else:
        logging.info('*** sync lists from network ***')
        # out of date, sync and save to file    
        list_df = ak_get_list_df()
        list_df.to_csv(list_file_path, index=False)
    return list_df

def get_detailed_dfs(list_df):
    detailed_dfs = {}
    if database_is_valid():
        logging.info('*** sync details from database ***')
        database_path = get_database_path()       
        for index, row in list_df.iterrows():
            code = row['code']
            code_file_path = database_path + str(code) + ".csv"
            code_df = pd.read_csv(code_file_path)
            code_df['date'] = pd.to_datetime(code_df['date'])
            detailed_dfs[code] = code_df
    else:
        logging.info('*** sync details from network ***')
        last_sync_date = database_last_sync_date()
        current_sync_date = datetime.datetime.now()
        detailed_dfs = get_detailed_df_with_pool(last_sync_date, current_sync_date)
    
    mark_database_valid()
    return detailed_dfs

def get_realtime_dfs(list_df):
    rt_dfs = tu_get_realtime_df()
    return rt_dfs
    
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
    detailed_dfs = get_detailed_dfs(list_df)

    
    # TODO: dump a snapshot of lists? details?
    
    print('\n\n*** core calculation start ***')
    ##############################################################################
    # - do calculation
    
    
    ##############################################################################
    # - filter
    candidates = []
    
    count = len(list_df)
    current = 0
    for index, row in list_df.iterrows():
        code = row['code']
        if (all(map(lambda filer: filer(code), [macd_filter, volumne_filter]) )):
            candidates.append(code)
        if DEBUG:
            current += 1
            print('{}\t / {}\r'.format(current, count))
            
    ##############################################################################
    # - print result
    print('*** core calculation result: ***')
    print(candidates)
   
    dumpToJson(candidates, list_df, detailed_dfs)
