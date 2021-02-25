'''
Input 1: rawList: Raw data list to be groupped, example [1 2 3 4]
Input 2: Group criteria, list of lambda, example [odd even]
Input 3: Range in the raw list to execute the grouping
Output: List of List of Indexs of the rawList, which satisfies criteria
        and keep order [[1 3], [2 4]]
'''
DEBUG = 0
def grouper(rawList : list, criteria : list, rangeList : list = []):
    result = []
    if not rangeList:
        rangeList = [[i for i in range(0, len(rawList))]]
        if DEBUG:
            print(rangeList)
    for rng in rangeList:
        for lam in criteria:
            l = []
            for idx in rng:
                if lam(rawList[idx]):
                    l.append(idx)
            result.append(l)
    reslen = 0
    rangelen = 0
    for lst in result:
        reslen += len(lst)
    for lst in rangeList:
        rangelen += len(lst)
    if reslen != rangelen:
        print('result len: {} ; range len: {}'.format(reslen, rangelen))
        raise Exception('wrong result size, check!')
    return result

def evaler(macd : list):
    if len(macd) < 3:
        return 0
    a = macd[0]
    b = macd[1]
    c = macd[2]
    if ( a * b < 0):
        return 0
    if (a > 0):
        if ( a < b ):
            return -1
        else:
            return 0
    elif ( a < 0 ):
        if ( a > b ):
            return 1
        else:
            return 0
    return 0

def criteriaFromList(segments : list):
    lams = []
    return lams



if __name__ == "__main__":
    # test grouper
    rawInput = [i for i in range(1, 11)]
    oddEven = [lambda x : x % 2, lambda x : not (x % 2)]
    greater = [lambda x : x > 15, lambda x : x <=15]
    G1 = grouper(rawInput, greater)
    G2 = grouper(rawInput, oddEven, G1)
    print(G1)
    print(G2)

    # test evaler

    # test criteriaFromList
