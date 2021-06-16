#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 30 12:12:54 2021

@author: yuduo
"""

from flask import Flask, render_template
from gevent import pywsgi
#import logging

##logging.basicConfig(filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')

DEBUG = False

app = Flask(__name__)

@app.errorhandler(404)
def page_not_found(e):
    return e

@app.route('/')
def index():
    return render_template('dump.html')

@app.route('/snapshot.json')
def get_snapshot():
    json_file = "../snapshot/snapshot.json"
    fin = open(json_file, "r", encoding='utf-8')
    json_txt = fin.read()
    return json_txt

if __name__ == '__main__':
    if DEBUG:        
        app.run(debug = DEBUG)
        # time.sleep(60)
        # txt = dbc.get_result_json_str()
        # print(txt)
    else:
        server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
        server.serve_forever()
    