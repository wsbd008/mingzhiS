import argparse
from brain import brain

def printMenuAndGetInput() -> str:
    print('''
    1. Query by code
    2. List best selection
    8. Update database (NO more than once a day!!!)
    0. Quit'''
          )
    return input("Op>> ")

b = brain()
def queryByCode():
    default = '9527'
    code : str = input("Input code (default {}): ".format(default)) or default
    b.queryByCode(code)
    return

def listBestSelectionOnBoard():
    default = 'main'
    board : str = input("Input board name (default {}): ".format(default)) or default
    b.listBestSelectionOnBoard(board)
    return

def updateDB():
    b.updateDatabase()
    return

def unknownOp():
    print('unknown option')
    return;
    
def main():
    Ops = {'1' : queryByCode,
           '2' : listBestSelectionOnBoard,
           '8' : updateDB
           }
    choice : str = printMenuAndGetInput()
    while (choice != '0'):
        Ops.get(choice, unknownOp)()
        
        choice = printMenuAndGetInput()
    print('bye\n')

if __name__ == "__main__":
    main()
