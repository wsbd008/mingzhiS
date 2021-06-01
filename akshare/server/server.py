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
from worker.akmain import get_detailed_df_with_pool, ak_get_list_df

DEBUG = True

app = Flask(__name__)
#logging.basicConfig(filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')

@app.errorhandler(404)
def page_not_found(e):
    return e

@app.route('/')
def index():
    return render_template('index.html')

def is_trade_time():
    return False

@app.route('/mingzhiS')
def real_analysis():
    if is_trade_time():
        list_df = ak_get_list_df()
        return render_template('index.html')
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
    