# -*- coding: utf-8 -*-
"""
Created on Tue May  4 11:40:01 2021

@author: yuduo
"""

import os
import datetime
import pandas as pd
import akshare as ak
import json
import io

DEBUG = 0
USE_DATABASE = 0

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

__database_flag_path__ = '/database/'
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
fin.close()
last_sync_date = datetime.datetime.strptime(last_sync_date_str, datetime_format)
current_sync_date = datetime.datetime.now()

"""
sync database content
1. sync lists and basic info, saved in list_df
2. sync detailed info, saved in a map: detailed_dfs, use code as key
"""
__list_file__ = "list.csv"
list_file_path = database_path + __list_file__


# 1. sync lists and basic info
# list_df has at least 3 columns: prefix('sh' or 'sz'), code, name
list_df = pd.DataFrame()
detailed_dfs = {}
illed_codes = [] #recording problems

if (current_sync_date.date() == last_sync_date.date() or USE_DATABASE):
    # up to date, just read from file
    print('*** sync lists from database ***')
    list_df = pd.read_csv(list_file_path)
    list_df['code'] = list_df['code'].apply(lambda x : format(str(x), '0>6'))
else:    
    print('*** sync lists from network ***')
    # out of date, sync and save to file    
    list_df = get_list_df()
    list_df.to_csv(list_file_path, index=False)

if DEBUG:
    debug_count = 100
    list_df = list_df.head(debug_count)

# 2. sync detailed info
# each detailed stock intf has at least 4 columns: date, close, macd, volumn 
if (current_sync_date.date() == last_sync_date.date() or USE_DATABASE):    
    print('*** sync details from database ***')
    # up to date, just read from file
    count = len(list_df)
    current = 0
    for index, row in list_df.iterrows():
        code = row['code']
        code_file_path = database_path + str(code) + ".csv"
        code_df = pd.read_csv(code_file_path)
        code_df['date'] = pd.to_datetime(code_df['date'])
        detailed_dfs[code] = code_df
else:
    print('*** sync details from network ***')
    count = len(list_df)
    current = 0
    for index, row in list_df.iterrows():
        code = row['code']
        code_file_path = database_path + code + ".csv"
        try:
            code_df = get_detailed_df(row, last_sync_date.strftime(akshare_datetime_format),
                                      current_sync_date.strftime(akshare_datetime_format), 'qfq')
            detailed_dfs[code] = code_df
            code_df.to_csv(code_file_path, index=False)
        except:
            illed_codes.append(code)
    print('\n')

# deal with illed stocks
if illed_codes: # not empty
    print('\n*** illed stocks:{} ***\n'.format(illed_codes))
    for code in illed_codes:
        list_df.drop(list_df.loc[list_df['code']==code].index, inplace=True)
    list_df.to_csv(list_file_path)
        
# sync finishhed, log sync date back to file
fout = open(database_flag_file, "w")
fout.write(current_sync_date.strftime(datetime_format))
fout.close()

if DEBUG:
    print("synced {} detailed dfs".format(count))

# TODO: dump a snapshot of lists? details?

##############################################################################
# - do calculation


##############################################################################
# - filter
candidates = []
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

# output to html
def dumpToHtml(code_list):
    html_file = 'stock-output.html'
    #fout = open(html_file, "w")
    fout = io.StringIO('');
    fout.write('<!DOCTYPE html>\n')
    fout.write('<html>\n<body>\n')
    fout.write('<table border="1">\n')
    fout.write('<tr>')
    table_headers = ['code', 'name', 'link']
    for table_header in table_headers:
        fout.write('<th>{}</th>\n'.format(table_header))
    fout.write('</tr>\n')
    for code in code_list:
        fout.write('<tr>\n')
        fout.write('<th>{}</th>\n'.format(code))
        
        name = list_df[list_df['code']==code]['name'].iloc[0]
        fout.write('<th>{}</th>\n'.format(name))
        
        prefix = list_df[list_df['code']==code]['prefix'].iloc[0]
        url = 'https://xueqiu.com/S/{}{}'.format(prefix, code)
        fout.write('<th><a href="{}" target="_blank" rel="noopener noreferrer">link</a></th>\n'.format(url))
        fout.write('</tr>\n')
    fout.write('</table>\n')
    fout.write('</body>\n</html>\n')
    fout.close()

#dumpToHtml(candidates)

def dumpToJson(code_list):
    json_file = "snapshot.json"
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
    
dumpToJson(candidates)