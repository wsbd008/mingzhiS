#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 30 12:12:54 2021

@author: yuduo
"""

from flask import Flask, render_template
from gevent import pywsgi
import io
#import logging
import sys
import threading, time
import multiprocessing
import json

sys.path.append('..')
from worker.akmain import get_list_df, get_detailed_dfs, dump_to_py_obj, get_realtime_df, tu_get_realtime_df_mt
import pandas as pd

##logging.basicConfig(filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')

DEBUG = 1            
df_merge_mutex = threading.Lock()

class db_cache:
    def __init__(self):
        self.db_valid = False
        self.list_df = pd.DataFrame()
        self.detailed_dfs = {}
        self.merged = {}
        self.snapshot_py_obj = {}
        
        self.db_sync_db()
        
    def db_sync_db(self):
        if not self.db_valid:
            self.list_df = get_list_df()
            self.detailed_dfs = get_detailed_dfs(self.list_df)
            print('after sync db, detailed dfs is len: {}'.format(len(self.detailed_dfs)))
            self.db_valid = True
    def get_list(self):
        return self.list_df
    def get_detailed(self):
        return self.detailed_dfs
    
    def merge_todays_df(self, todays_df):
        for (code, df) in self.detailed_dfs.items():
            row_df = todays_df[todays_df['code']==code]
            new_df = pd.concat([row_df, df])
            new_df.set_index(pd.Index(range(0, len(new_df.index))), inplace=True)        
            x = new_df[['date', 'open', 'high', 'low', 'close', 'volume', 'dif', 'dea', 'macd']]
            self.detailed_dfs[code] = x
        return
    
    def merge_one_df(self, code, poolDict, df, todays_df):
        row_df = todays_df[todays_df['code']==code]
        new_df = pd.concat([row_df, df])
        new_df.set_index(pd.Index(range(0, len(new_df.index))), inplace=True)        
        x = new_df[['date', 'open', 'high', 'low', 'close', 'volume', 'dif', 'dea', 'macd']]
        poolDict[code] = x
    
    def merge_todays_df_with_pool(self, todays_df):
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        manager = multiprocessing.Manager()
        poolDict = manager.dict()
        for (code, df) in self.detailed_dfs.items():
            pool.apply_async(func = db_cache.merge_one_df, args = (self, code, poolDict, df, todays_df))
        pool.close()
        pool.join()
        self.detailed_dfs = poolDict        
        return 
    
    def sync_with_today(self, todays_df):
        self.db_sync_db()
        # 1. merge today's data with detailed_dfs
        MERGE_WITH_MULTITHREADING = False
        ##logging.info('database : start merging')
        print('database : start merging')
        if MERGE_WITH_MULTITHREADING:
            self.merge_todays_df_with_pool(todays_df)
        else:
            self.merge_todays_df(todays_df)
        #logging.info('database : finish merging')
        print('database : finish merging')
        
        # 2. calculate based on current detailed_dfs
        self.update_result_json()
    
    def update_result_json(self):
        candidates = []
    
        for index, row in self.list_df.head(10).iterrows():
            code = row['code']
            #if (all(map(lambda filer: filer(self.detailed_dfs, code), [macd_filter, volumne_filter]) )):
            candidates.append(code)
        
        self.snapshot_py_obj = dump_to_py_obj(candidates, self.list_df, self.detailed_dfs)
        pass
    
    def get_result_json_str(self) -> str:
        fout = io.StringIO()
        json.dump(self.snapshot_py_obj, fout)
        txt = fout.getvalue()
        return txt
    
#dbc = db_cache()

def producer():
    sleep_minites_after_one_sync = 5
    while True:
        #logging.info('producer : get today\'s realtime data')
        try:
            df = tu_get_realtime_df_mt(dbc.list_df)
        
            with df_merge_mutex:
                print('producer got realtime df with size: ')
                print(df.shape)
                dbc.sync_with_today(df)
            
        except:
            print('server denied - get today\'s realtime data')
            pass    
        
        time.sleep(sleep_minites_after_one_sync * 60)
        
app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
    return e

@app.route('/')
def index():
    return render_template('index.html')

def is_trade_time():
    return not False

# list_df = pd.DataFrame()
# detailed_dfs = {}

def macd_filter(dfs, code):
    df = dfs[code]
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
def volumne_filter(dfs, code):
    df = dfs[code]
    volume_column = df['volume']

    try:
        if volume_column[0] > (volume_column[1] * 3):
            return True
    except:
        return False
    return False


@app.route('/mingzhiS')
def real_analysis():
    if is_trade_time():
        with df_merge_mutex:
            dbc.update_result_json()
        
        return render_template('dump.html')
    else:
        return '404'

@app.route('/dump')
def dump():
   return render_template('dump.html')

@app.route('/snapshot.json')
def get_snapshot():    
    json_file = "../snapshot/snapshot.json"
    with open(json_file, "r", encoding='utf-8') as fin:
        res = fin.read()
        py_obj = json.loads(res)
        print(py_obj)
    #json = dbc.get_result_json_str()
    return res

if __name__ == '__main__':
    #p = threading.Thread(target = producer)
    #p.start()
    
    if DEBUG:        
        app.run(debug = DEBUG)
        # time.sleep(60)
        # txt = dbc.get_result_json_str()
        # print(txt)
    else:
        server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
        server.serve_forever()
    