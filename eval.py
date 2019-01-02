from __future__ import print_function
from logging import getLogger
from math import exp, log

'''
def main(argv=sys.argv[1:]):
    args = argparser().parse_args(argv)

def argparser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('model')
    parser.add_argument('data')
    return parser
'''

def getLogList(expression):
    i = 4
    logLocation = []
    logList = []
    roundCounter = 0
    while i < len(expression):
        if expression[i-3:i] == "log" and roundCounter == 0:
            i += 1
            start = i
            roundCounter = 1
            while roundCounter != 0 and i < len(expression):
                if expression[i] == "(":
                    roundCounter += 1
                elif expression[i] == ")":
                    roundCounter -= 1
                i += 1
            end = i - 1
            logLocation.append((start-4, end+1))
            logList.append(expression[start:end])
        i += 1
    return logList, logLocation

def evaluateExpression(expression):
    try:
        ans = eval(expression)
        return ans
        #print("correct answer")
    except:
        logList, logLocation = getLogList(expression)
        logOutput = []
        for item in logList:
            try:
                output = eval(item)
            except:
                getLogger("probfoil").warning("Exception occurred in logOutput")
                getLogger("probfoil").warning("item\t\t\t\t:" + item)
                output = 0.0
            logOutput.append(output)     
        
        #At each logLocation, replace the log with either the output or with -Inf
        start = 0
        approximateExpression = ""
        for i, (j, k) in enumerate(logLocation):
            approximateExpression = approximateExpression + expression[start:j]
            if logOutput[i] > 0:
                approximateExpression = approximateExpression + "log(" + str(logOutput[i]) + ")"
            else:
                approximateExpression = approximateExpression + "-float('inf')"
            start = k
        approximateExpression = approximateExpression + expression[start:]
        #approximateExpression = approximateExpression + expression[k:]
        try:
            ans = eval(approximateExpression)
            return ans
        except:
            getLogger("probfoil").warning('Exception\t\t\t\t\t\t: %s' % approximateExpression)
            return None

if __name__ == '__main__':
    main()
