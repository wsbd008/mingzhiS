#from entry import entry
from os import path
from datetime import datetime
import os, time, sys
import pandas as pd
import tushare as ts
import multiprocessing
import shutil

DEBUG = 0
DEBUG_DETAIL = 0
date_format = "%Y-%m-%d"

difTitle = 'dif'
deaTitle = 'dea'
macdTitle = 'macd'

testCodeList = ['600036', '600779', '601318']

def getRoot():
    rootPath = path.dirname( path.realpath(__file__) )
    return rootPath

def dummyDF():
    dummyData = {'open' : 0.,
                 'high' : 0,
                 'close': 0,
                 'low' : 0,
                 'volumn' : 0,
                 'price_change' : 0,
                 'p_change' : 0,
                 'ma5' : 0,
                 'ma10' : 0,
                 'ma20' : 0,
                 'v_ma5' : 0,
                 'v_ma10' : 0,
                 'v_ma20' : 0,
                 'turnover' : 0,
                 'date' : datetime.now().strftime('%m/%d/%Y')
                 }
    return pd.DataFrame(dummyData, index=[0])

class mzMuscle:
    __dbPath__ = '.\\storage\\'
    __stockBasicName__ = 'stock_basic.csv'
    __dbFormat__ = '.csv'

    def __init__(self, bInitDetails = False):
        self.init(bInitDetails)
        
    def init(self, bInitDetails):
        self.dfs = {}
        # 1. make sure database PATH exists
        path = getRoot() + self.__dbPath__
        if (not os.path.exists(path)):
            if DEBUG:
                print('Muscle - making path')
            os.makedirs(path)

        # 2 init basics info
        self.initBasics()
        
        bUsingPool = True
        
        if DEBUG:
            print('Muscle - init details : {} ; using pool : {}'.format(bInitDetails, bUsingPool))
        if bInitDetails:
            # 3 init details info        
            basics = self.dfs['basic']
            selected = basics#.head(10)#.loc[basics['code'].isin(testCodeList)]
            codes = selected['code'].to_list()
            self.initDetails(codes, bUsingPool)
        pass

    def initBasics(self):
        df = self.StockBasicInfo()
        #df.drop(df[df['timeToMarket']<=0].index, inplace=True)
        #df.drop(df[df['pe']<=0].index, inplace=True)
        self.dfs['basic'] = df
    
    def StockBasicInfo(self):
        path = getRoot() + self.__dbPath__
        stockBasicFullPath = path + self.__stockBasicName__
        if (not os.path.exists(stockBasicFullPath)):
            if DEBUG:
                print('Muscle - init stock basics from scratch')
            df = self.InitStockBasic()
            df.to_csv(stockBasicFullPath, index=False)
        else:
            if DEBUG:
                print('Muscle - init stock basics (from cache)')
            df = pd.read_csv(stockBasicFullPath)
            df['code'] = df['code'].apply(lambda x : format(str(x), '0>6'))
            df['code'] = df['code'].astype(str)
        return df
    
    def InitStockBasic(self):
        df = ts.get_stock_basics()
        df['code'] = df.index
        df['code'] = df['code'].apply(lambda x : format(str(x), '0>6'))
        df['code'] = df['code'].astype(str)        
        df.set_index(pd.Index(range(0, len(df.index))), inplace=True)
        return df

    def initDetails(self, codes : list = [], UsingPool = False):
        if DEBUG:
            start = time.time()        
        
        if not codes:
            codes = self.dfs['basic']['code'].to_list()
        
        if UsingPool:
            self.initDetailsWithPool(codes)
        else:
            self.initDetailsWithOneProc(codes)
        
        if DEBUG:
            end = time.time()
            print('Init details cost {:.3f} seconds.'.format(end - start))
      
    def initDetailsWithPool(self, codes):
        print('initDetailsWithPool,begin')
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        manager = multiprocessing.Manager()
        poolDict = manager.dict()
        lock = manager.Lock()
        total = len(codes)
        count = manager.Value("i", 0, lock = lock)
        for code in codes:
            pool.apply_async(func = mzMuscle.initDWM, args = (self, code, poolDict, count, total, lock))
        pool.close()
        pool.join()
        
        if DEBUG:
            print('init details with pool, finished with {} keys'.format(len(poolDict)) )
        self.dfs = {**self.dfs, **poolDict}

    def initDetailsWithOneProc(self, codes, dummyDict):
        if DEBUG:
            print('initDetailsWithOneProc - begin')
        for code in codes:
            self.initDWM(str(code))
        if DEBUG:
            print('init details with one proc, finished with {} keys'.format(len(self.dfs.keys()) - 1))

    def initDWM(self, code : str, poolDict, count, total, lock):
        for ktype in ['D', 'W', 'M']:
            key = code + ktype
            if not key in poolDict:
                poolDict[key] = self.StockDetailInfo(code,ktype)
        lock.acquire()
        count.value += 1
        print('{} / {}'.format(count.value, total), end='\r')
        lock.release()
        if count.value == total:
            print('\n')

    def StockDetailInfo(self, index, ktype='D'):
        stockKey = index + ktype
        filename = getRoot() + self.__dbPath__ + stockKey + self.__dbFormat__
        if (not os.path.exists(filename)):
            if DEBUG:
                print('Muscle - init stock {} {} detail'.format(index, ktype))
            df = self.InitStockDetail(index, ktype)                
            df.to_csv(filename, index=False)
        else:
            if DEBUG:
                if DEBUG_DETAIL:
                    print('Muscle - init stock {} {} detail (from cache)'.format(index, ktype))
            df = pd.read_csv(filename)
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def InitStockDetail(self, index, ktype='D'):
        df = ts.get_hist_data(code=str(index), ktype = ktype)
        if df is None:
            df = dummyDF()
        df = self.__reformatDetailFromTushare(df)
        
        macd = self.get_macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        return df

    def get_macd(self, close, short = 12, long = 26, mid = 9):
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
        data[difTitle]=data['sema']-data['lema']    
        data[deaTitle]=pd.Series(data[difTitle]).ewm(span=mid).mean()
        data[macdTitle]=round(2*(data[difTitle]-data[deaTitle]), 2)
        #data.fillna(0,inplace=True)
        
        return data[[difTitle,deaTitle,macdTitle]].iloc[::-1] # 逆序
    
    def __reformatDetailFromTushare(self, df):
        if df is None:
            return df
        df['date'] = df.index
        df['date'] = pd.to_datetime(df['date'])
        df.set_index(pd.Index(range(0, len(df.index))), inplace=True)
        return df
    
    def getListByBoard(self, board : str):
        return [1,2,3]

    def loadDatabase(self):
        self.initDetails(codes = [], UsingPool = True)
    
    def updateDatabase(self):
        # delete the 'storage' folder
        print('--- Update database: cleaning ---')
        path = getRoot() + self.__dbPath__
        shutil.rmtree(path, True)
        
        # init muscle from scratch
        print('--- Update database: building ---')
        self.init(True)
    
    def getDetail(self, key):
        if key in self.dfs:
            return self.dfs[key]
        else:
            return 'wrong key'
            # better implementation below but not used now
            if len(key) == 7 :
                code = key[0:6]
                ktype = key[6:7]
                if code in self.dfs['basic']['code'].to_list() and ktype in ['D', 'W', 'M'] :                    
                    tmpDict = {}
                    self.initDWM(code, tmpDict)
                    self.dfs = {**self.dfs, **tmpDict}
                    return self.dfs[key]
            return 'wrong key'           

if __name__ == "__main__":

    muscle = mzMuscle(False)
    
    def listBasics():
        print(muscle.dfs['basic'])
    def listDetais():
        default = '600036D'
        key : str = input("enter code: (default {})".format(default)) or default
        df = muscle.getDetail(key)
        print(df)
    def loadDatabase():
        muscle.loadDatabase()
    def updateDatabase():
        muscle.updateDatabase()

    def printMenuAndGetInput() -> str:
        print('''
        1. List basic infos
        2. Show details with code
        3. Load database
        9. Update database (do this once a day)
        0. Quit'''
              )
        return input("Op>> ")

    def unknownOp():
        print('unknown option')
        return

    
    ####################################
    
    Ops = {'1' : listBasics,
           '2' : listDetais,
           '3' : loadDatabase,
           '9' : updateDatabase
           }
    choice : str = printMenuAndGetInput()
    while (choice != '0'):
        Ops.get(choice, unknownOp)()
        
        choice = printMenuAndGetInput()
    print('bye\n')
