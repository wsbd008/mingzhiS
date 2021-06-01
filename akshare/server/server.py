#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 30 12:12:54 2021

@author: yuduo
"""

from flask import Flask, render_template
from gevent import pywsgi
import io

DEBUG = True

app = Flask(__name__)

@app.errorhandler(404)
def page_not_found(e):
    print(e)
    return e


@app.route('/')
def real_analysis():
    # 1. need snapshot data of yesterday
    
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
def hello_world():
   return render_template('dump.html')

@app.route('/snapshot.json')
def get_snapshot():
    json_file = "snapshot.json"
    fin = open(json_file, "r", encoding='utf-8')
    json = fin.read()
    return json

if __name__ == '__main__':
    if DEBUG:
        app.run(debug = DEBUG)
    else:
        server = pywsgi.WSGIServer(('0.0.0.0', 8080), app)
        server.serve_forever()
    