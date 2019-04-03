import os
import sys

# Input Directory
dir = sys.argv[1]

for file in os.listdir(dir):

    inputf = open(file, 'r')
    for line in inputf:

        if line == '\n':
        	continue

        person = 0
        if line[:7] == 'somenot':
        	person = line.split('(')[0][7:]
        elif line[:4] == 'some':
        	person = line.split('(')[0][4:]
        elif line[:2] == 'no':
        	person = line.split('(')[0][2:]
        elif line[:3] == 'all':
        	person = line.split('(')[0][3:]
        elif line[:8] == 'rsomenot':
        	person = line.split('(')[0][8:]
        elif line[:5] == 'rsome':
        	person = line.split('(')[0][5:]
        elif line[:3] == 'rno':
        	person = line.split('(')[0][3:]
        elif line[:4] == 'rall':
        	person = line.split('(')[0][4:]

        outputf = open(dir + '/' + file.split('.')[0] + '_' + person + '.pl', 'w+')
        outputf.writeln(line)
        outputf.close()