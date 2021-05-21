# -*- coding: utf-8 -*-
"""
Created on Fri May 21 20:40:06 2021

@author: yuduo
"""
import pandas as pd
import tushare as ts
import datetime

def get_detailed_df(row, start_date, end_date, adjust, database_path):
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
    requited_columns = ['date', 'open', 'close', 'volume']
    res_df[requited_columns] = df[requited_columns]
    
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

if __name__ == "__main__":
    row = {'code':'600036'}
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=90)
    adjust = ''
    database_path='./'
    df = get_detailed_df(row, start_date, end_date, adjust, database_path)
    print(df)