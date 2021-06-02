#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 30 12:12:54 2021

@author: yuduo
"""

from flask import Flask, render_template, current_app
from gevent import pywsgi
import io
import logging
import sys

sys.path.append('..')
from worker.akmain import get_list_df, get_detailed_dfs, dumpToJson
import pandas as pd

DEBUG = True

app = Flask(__name__)
logging.basicConfig(filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')

@app.errorhandler(404)
def page_not_found(e):
    return e

@app.route('/')
def index():
    return render_template('index.html')

def is_trade_time():
    return not False

list_df = pd.DataFrame()
detailed_dfs = {}

def data_valid():
    return not detailed_dfs
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

class db_cache:
    def __init__(self):
        self.db_valid = False
        self.list_df = pd.DataFrame()
        self.detailed_dfs = {}
    def sync_db(self):
        if not self.db_valid:
            self.list_df = get_list_df()
            self.detailed_dfs = get_detailed_dfs(self.list_df)
            self.db_valid = True
    def get_list(self):
        return self.list_df
    def get_detailed(self):
        return self.detailed_dfs
    
    def sync_with_today(self):
        # 0. sync 15 min a time, otherwise return immediatly
        
        # 1. merge today's data with detailed_dfs
        
        # 2. calculate based on current detailed_dfs
        candidates = []
    
        for index, row in self.list_df.iterrows():
            code = row['code']
            if (all(map(lambda filer: filer(self.detailed_dfs, code), [macd_filter, volumne_filter]) )):
                candidates.append(code)
        dumpToJson(candidates, self.list_df, self.detailed_dfs)
    
dbc = db_cache()

@app.route('/mingzhiS')
def real_analysis():
    if is_trade_time():        
        dbc.sync_db()
        dbc.sync_with_today()        
        
        return render_template('dump.html')
    else:
        return '404'
    #logging.info('server get list')
    # 1. need snapshot data of yesterday
    
    #logging.info('server get details')
    # 2. need real time data of today
    
    # 3. compare data and show on page
    fout = io.StringIO('');
    fout.write('<!DOCTYPE html>\n')
    fout.write('<html>\n<body>\n')
    fout.write('<table border="1">\n')
    fout.write('<tr><td>xx</td></tr>')
    fout.write('</table>\n')
    fout.write('</body>\n</html>\n')
    txt =  fout.getvalue()
    fout.close()
    return txt


@app.route('/dump')
def dump():
   return render_template('dump.html')

@app.route('/snapshot.json')
def get_snapshot():
    json_file = "../snapshot/snapshot.json"
    fin = open(json_file, "r", encoding='utf-8')
    json = fin.read()
    return json

@app.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('favicon.ico')

if __name__ == '__main__':
    if DEBUG:        
        app.run(debug = DEBUG)
    else:
        server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
        server.serve_forever()
    