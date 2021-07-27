# -*- coding: utf-8 -*-
"""
Created on Tue Jul 27 22:17:57 2021

@author: yuduo
"""
import json, time, datetime
import tushare as ts

json_file = "../snapshot/snapshot.json"
check_dict = {} # key: code, value: volume of last trade day
with open(json_file, "r", encoding='utf-8') as fin:
    res = fin.read()
    py_obj = json.loads(res)
    for code, data in py_obj.items():
        volume_list = data['volume']
        check_dict[code] = volume_list[-1]

while True:
    for code, volume in check_dict.items():
        df = ts.get_realtime_quotes(code)
        latest_volume = float(df['volume'][0]) / 100
        if (latest_volume >= volume):
            msg = '{c}: current volume {new_v} large than last trade volume {v}\n'.format(c = code, new_v = latest_volume, v = volume)
            print(datetime.datetime.now())
            print(msg)
    #break
    time.sleep(5)

print('\n!!! market closed !!!\n')