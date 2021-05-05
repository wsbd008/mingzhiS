# -*- coding: utf-8 -*-
"""
Created on Wed May  5 17:17:18 2021

@author: yuduo
"""

import json
from urllib.request import urlopen, Request
date = "20210130"
server_url = "http://www.easybots.cn/api/holiday.php?d="

def is_holiday(date) -> bool: 
    vop_url_request = Request(server_url + date)
    vop_response = urlopen(vop_url_request)
     
    vop_data= json.loads(vop_response.read())
    # 0 : workday; 1: weekend; 2: holiday
    if vop_data[date]=='1' or vop_data[date]=='2':
        return True
    else:
        return False
