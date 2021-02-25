from muscle import mzMuscle
from util import grouper, evaler
from os import path
import os, time
import pandas as pd

DEBUG = 0
msl = mzMuscle()

class entry:
    def __init__(self):
        pass

def getRoot():
    rootPath = path.dirname( path.realpath(__file__) )
    return rootPath

class brain:
    __dbPath__ = '.\\storage\\'
    __stockComputedName__ = 'stock_computed.csv'

    def __init__(self):
        # 1. make storage path if not exists
        path = getRoot() + self.__dbPath__
        if (not os.path.exists(path)):
            if DEBUG:
                print('Brain - making storage path')
            os.makedirs(path)

        # 2. init brain basics
        if DEBUG:
            print('Brain - init basics from muscle')
        df = msl.dfs['basic']
        #df.drop(df[df['pe']<=0].index, inplace=True)
        self.basics = df
            
        # 3. init brain computed
        brainPath = path + self.__stockComputedName__
        if (not os.path.exists(brainPath)):
            # 3.1 init from scratch by muscle, and save to file
            if DEBUG:
                print('Brain - init computed from scratch')
            #self.msl = mzMuscle()
            self.computed = self.compute()
            self.saveComputedToFile()
        else:
            # 3.2 init from saved file
            if DEBUG:
                print('Brain - init computed (from cache)')
            self.loadComputedFromFile()
    
    def saveComputedToFile(self):
        path = getRoot() + self.__dbPath__
        brainPath = path + self.__stockComputedName__
        self.computed.to_csv(brainPath, index=False)

    def loadComputedFromFile(self):
        path = getRoot() + self.__dbPath__
        brainPath = path + self.__stockComputedName__
        df = pd.read_csv(brainPath)
        df['code'] = df['code'].apply(lambda x : format(str(x), '0>6'))
        self.computed = df
        
    def clearComputedFile(self):
        path = getRoot() + self.__dbPath__
        brainPath = path + self.__stockComputedName__
        if (os.path.exists(brainPath)):
            os.remove(brainPath)
            if DEBUG:
                print('Brain - computed file removed ({})'.format(brainPath))

    def recompute(self):
        self.clearComputedFile()
        msl.loadDatabase()
        self.computed = self.compute()
        self.saveComputedToFile()

    def compute(self):
        #msl = self.msl
        basics = self.basics
        
        #########
        # for now, test with 3 stocks only,
        #                           remove the following later
        basics = basics#.head(10)#.loc[basics['code'].isin(testCodeList)]
        #print(basics)
        #                           remove the above later
        #########
        
        codes = basics['code'].to_list()
        #msl.initDetails(codes)
        basics['dkscore'] = self.computeScoreByOneProc(codes, 'D')
        basics['wkscore'] = self.computeScoreByOneProc(codes, 'W')#[self.evaluate(str(code), 'W') for code in codes ]
        basics['mkscore'] = self.computeScoreByOneProc(codes, 'M')#[self.evaluate(str(code), 'M') for code in codes ]
        if DEBUG:
            print(basics)
        return basics
    
    def computeScoreByOneProc(self, codes, ktype):
        if DEBUG:
            start = time.time()
            
        res = []
        for code in codes:
            score = self.evaluate(str(code), ktype)
            res.append(score)
        
        if DEBUG:
            end = time.time()
            codesCount = len(codes)
            print('Computed {} codes of type {} cost {:.3f} seconds.'.format(codesCount, ktype, end - start))
        return res

    def evaluate(self, code : str, ktype : str):
        key = code + ktype
        if key in msl.dfs:
            detail = msl.dfs[code + ktype]
            return evaler(detail['macd'])
        else:
            return 0

    def runCritera(self, board, criteria, column : str = '', rangeList : list = []):
        candidates = self.computed
        if not board == 'main':
            candidates = candidates.loc[candidates['industry'].isin([board])]

        res = grouper(candidates[column].tolist(), criteria, rangeList)
        if DEBUG:
            names = candidates['name']
            for i in res[0]:
                print(names.iloc[i], candidates[column].iloc[i])
            print(res)
        return res

    def listBestSelectionOnBoard(self, board : str ='main'):
        buy = lambda value : value == 1
        hold = lambda value : value == 0
        sell = lambda value : value == -1
        selectionCriteria = [buy, hold, sell]
        
        criteriaDict = {1: ['dkscore', 'wkscore'],
                        2: ['mkscore', 'wkscore'],
                        3: ['dkscore', 'wkscore', 'mkscore'], 
                        4: ['mkscore', 'wkscore', 'dkscore']}
        print(criteriaDict)
        select = int(input('select criteria (default 1) > ') or 1)        
        
        print('\n')
        columns = criteriaDict[select]
        res = []
        info = '\n'
        for column in columns:
            res = self.runCritera(board, selectionCriteria, column, res)
            toBuy = len(res[0])
            info += 'selected {} stocks by {}\n'.format(toBuy, column)
        
        best = self.computed.iloc[res[0]].sort_values(by='industry')
        best = best[best['pe']>0]
        best = best[best['pb']>0]
        print(best[['name', 'code', 'industry', 'esp', 'pe', 'bvps', 'pb']])
        print(info)
        print('selected {} stocks by positive pe/pb'.format(len(best)))
        
        self.lastSelected = res

    def queryByCode(self, code : str):
        #print('code {}, name {} is ok'.format(code, 'xx'))
        if code in self.computed['code'].to_list():
            row =  self.computed[self.computed['code']==code]
            print(row[['dkscore', 'wkscore', 'mkscore', 'name', 'industry', 'esp', 'pe', 'bvps', 'pb']])
        else:
            print('wrong code')

    def updateDatabase(self):
        print('Brain: update database')
        msl.updateDatabase()
        self.clearComputedFile()
        self.computed = self.compute()
        self.saveComputedToFile()
        pass
        
    def showStatistics(self):
        print('Has {} basic stocks info'.format(len(self.basics)))
        print('Has {} computed stocks info'.format(len(self.computed)))

if __name__ == "__main__":

    brain = brain()
    
    def listBestSelectionOnBoard():
        default = 'main'
        #ids = brain.basics['industry'].drop_duplicates().to_list()
        board : str = default#input("Input board name (default {}): ".format(default)) or default
        brain.listBestSelectionOnBoard(board)
        return
    
    def queryByCode():
        default = '000001'
        code : str = input("Input code (default {}): ".format(default)) or default
        brain.queryByCode(code)
    
    def showStatistics():
        brain.showStatistics()
        return
    
    def recompute():
        brain.recompute()
        return
    
    def updateDatabase():
        brain.updateDatabase()

    def printMenuAndGetInput() -> str:
        print('''
        1. List best selection
        2. Query by code
        3. Show statistics
        8. Recompute
        9. Update database (do this NO more than once a day)
        0. Quit'''
              )
        return input("Op >> ")

    def unknownOp():
        print('unknown option')
        return
    
    ####################################
    
    Ops = {'1' : listBestSelectionOnBoard,
           '2' : queryByCode,
           '3' : showStatistics,
           '8' : recompute,
           '9' : updateDatabase
           }
    choice : str = printMenuAndGetInput()
    while (choice != '0'):
        Ops.get(choice, unknownOp)()
        
        choice = printMenuAndGetInput()
    print('bye\n')

    #brain.recompute()

    # peGood = lambda pe : pe > 0 and pe < 10
    # peBad = lambda pe : pe >= 10 or pe <= 0
    # peCriteria = [peGood, peBad]

    # brain.runCritera(peCriteria)
