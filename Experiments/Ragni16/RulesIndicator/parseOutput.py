import os
import sys

# Input Directory
dir = sys.argv[1]

outputFile = open(dir + '.csv', 'a')

for file in os.listdir(dir):
    inputf = open(dir + '/' + file, 'r')
    try:
        r = False
        for line in inputf:

            if line == '\n':
            	continue

            accuracy = float(line.split(' ')[-1][:-1])
            weight = line[line.index('[')+1:line.index(']')].replace(' ','')

            outputFile.write(weight + ',' + str(accuracy) + '\n')
            continue

        inputf.close()
    
    except Exception as e:
    	print(e)
        print(inputf)
        print(line)
        break

outputFile.close()