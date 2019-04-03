import os
import sys

# Input Directory
dir = sys.argv[1]

newpath = r'./CV_PersonalLevelFiles/'
if not os.path.exists(newpath):
    os.makedirs(newpath)

for i in range(1, 140):

    header = []
    header.append('base(all'+str(i)+'(object, object)).')
    header.append('base(some'+str(i)+'(object, object)).')
    header.append('base(no'+str(i)+'(object, object)).')
    header.append('base(somenot'+str(i)+'(object, object)).')
    header.append('base(rall'+str(i)+'(object, object)).')
    header.append('base(rsome'+str(i)+'(object, object)).')
    header.append('base(rno'+str(i)+'(object, object)).')
    header.append('base(rsomenot'+str(i)+'(object, object)).')
    header.append('base(rnvc'+str(i)+'(object, object)).\n\n')

    mode = []
    mode.append('mode(all'+str(i)+'(+, +)).')
    mode.append('mode(all'+str(i)+'(+, -)).')
    mode.append('mode(all'+str(i)+'(-, +)).')
    mode.append('mode(some'+str(i)+'(+, +)).')
    mode.append('mode(some'+str(i)+'(+, -)).')
    mode.append('mode(some'+str(i)+'(-, +)).')
    mode.append('mode(no'+str(i)+'(+, +)).')
    mode.append('mode(no'+str(i)+'(+, -)).')
    mode.append('mode(no'+str(i)+'(-, +)).')
    mode.append('mode(somenot'+str(i)+'(+, +)).')
    mode.append('mode(somenot'+str(i)+'(+, -)).')
    mode.append('mode(somenot'+str(i)+'(-, +)).\n\n')

    for j in range(0, 10):
        f1 = open(newpath + '/cv' + str(j) + '_train_' + str(i) + '.pl', 'w+')
        f1.write('\n'.join(header))
        f1.write('\n'.join(mode))
        f1.close()

        f2 = open(newpath + '/cv' + str(j) + '_test_' + str(i) + '.pl', 'w+')
        f2.write('\n'.join(header))
        f2.close()

for file in os.listdir(dir):

    inputf = open(dir + '/' + file, 'r')
    try:
        r = False
        for line in inputf:

            if line == '\n':
            	continue

            person = '0'
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
            elif line[:4] == 'rnvc':
                person = line.split('(')[0][4:]
            elif line[:11] == '0::rsomenot':
                person = line.split('(')[0][11:]
            elif line[:8] == '0::rsome':
                person = line.split('(')[0][8:]
            elif line[:6] == '0::rno':
                person = line.split('(')[0][6:]
            elif line[:7] == '0::rall':
                person = line.split('(')[0][7:]
            elif line[:7] == '0::rnvc':
                person = line.split('(')[0][7:]

            outputf = open(newpath + '/' + file.split('.')[0] + '_' + person + '.pl', 'a')
            outputf.write(line)
            outputf.close()
    except:
        print(inputf)
        print(line)






