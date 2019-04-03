from problog.program import PrologFile, PrologString
from problog.core import ProbLog
from problog import get_evaluatable

from probfoil import learn
from probfoil.data import DataFile
from probfoil.probfoil import ProbFOIL2

import sys
from collections import Counter 
from multiprocessing import Process, Pool
#import itertools

#fold = sys.argv[1]
#person = sys.argv[2]
mainDir = sys.argv[1]
rd = sys.argv[2]
pid = sys.argv[3]
precedences = []
for precedence in sys.argv[4].split(' '):
	l = []
	for character in precedence:
		l.append(int(character))
	precedences.append(tuple(l))
rulesIndicator = sys.argv[5]


def getAtom(response, person, id):
	# Input: Iac, 23, 4
	# Output: rsome4(a23, c23)
	
	if response[0] == 'A':
		atom = 'rall' + str(person) + '(' + response[1] + str(id) + ',' + response[2] + str(id) + ')'
	elif response[0] == 'E':
		atom = 'rno' + str(person) + '(' + response[1] + str(id) + ',' + response[2] + str(id) + ')'
	elif response[0] == 'I':
		atom = 'rsome' + str(person) + '(' + response[1] + str(id) + ',' + response[2] + str(id) + ')'
	elif response[0] == 'O':
		atom = 'rsomenot' + str(person) + '(' + response[1] + str(id) + ',' + response[2] + str(id) + ')'
	elif response == 'NVC':
		atom = 'rnvc' + str(person) + '(a' + str(id) + ',c' + str(id) + ')'
	else:
		atom = None
		print('Error ocurred in getAtom:')
		print('Response \t: ' + str(response))
		print('Person \t: ' + str(person))
		print('ID \t: ' + str(id))

	return atom

def getResponse(response, person):
	# Input: Iac, 23
	# Output: rsome23(A,C)

	if response == 'NVC':
		#mfa = 'Aca'
		return('rnvc' + str(person) + '(A,C)')
	elif response[1] == 'c':
		if response[0] == 'A':
			return('rall' + str(person) + '(C,A)')
		elif response[0] == 'E':
			return('rno' + str(person) + '(C,A)')
		elif response[0] == 'I':
			return('rsome' + str(person) + '(C,A)')
		elif response[0] == 'O':
			return('rsomenot' + str(person) + '(C,A)')
	else:
		if response[0] == 'A':
			return('rall' + str(person) + '(A,C)')
		elif response[0] == 'E':
			return('rno' + str(person) + '(A,C)')
		elif response[0] == 'I':
			return('rsome' + str(person) + '(A,C)')
		elif response[0] == 'O':
			return('rsomenot' + str(person) + '(A,C)')

def decodeTask(task, person):
	#Input: AA4
	#Output: (all32(B,A), all32(B,C))

	atom1 = ''
	atom2 = ''

	if task[0] == 'A':
		atom1 = 'all'+str(person)
	elif task[0] == 'E':
		atom1 = 'no'+str(person)
	elif task[0] == 'I':
		atom1 = 'some'+str(person)
	elif task[0] == 'O':
		atom1 = 'somenot'+str(person)

	if task[1] == 'A':
		atom2 = 'all'+str(person)
	elif task[1] == 'E':
		atom2 = 'no'+str(person)
	elif task[1] == 'I':
		atom2 = 'some'+str(person)
	elif task[1] == 'O':
		atom2 = 'somenot'+str(person)

	if task[2] == '1':
		atom1 += '(A,B)'
		atom2 += '(B,C)'
	elif task[2] == '2':
		atom1 += '(B,A)'
		atom2 += '(C,B)'
	elif task[2] == '3':
		atom1 += '(A,B)'
		atom2 += '(C,B)'
	elif task[2] == '4':
		atom1 += '(B,A)'
		atom2 += '(B,C)'

	return (atom1, atom2)

def encodeTask(task1, task2):
	# Input: rall1(a34,b34), rsome1(c34, b34)
	# Output: AI3

	functor1 = task1[0]
	arg11 = str(task1[1][0])[0]
	arg12 = str(task1[1][1])[0]
	
	functor2 = task2[0]
	arg21 = str(task2[1][0])[0]
	arg22 = str(task2[1][1])[0]

	if functor1[:3] == "all":
		encodedTask = 'A'
	elif functor1[:2] == "no":
		encodedTask = 'E'
	elif functor1[:7] == "somenot":
		encodedTask = 'O'
	elif functor1[:4] == "some":
		encodedTask = 'I'
	
	if functor2[:3] == "all":
		encodedTask += 'A'
	elif functor2[:2] == "no":
		encodedTask += 'E'
	elif functor2[:7] == "somenot":
		encodedTask += 'O'
	elif functor2[:4] == "some":
		encodedTask += 'I'

	if arg11 == 'a' and arg22 == 'c':
		encodedTask += '1'
	elif arg12 == 'a' and arg21 == 'c':
		encodedTask += '2'
	elif arg11 == 'a' and arg21 == 'c':
		encodedTask += '3'
	elif arg12 == 'a' and arg22 == 'c':
		encodedTask += '4'

	return encodedTask

def matchAccuracy(fold, person, ruleDir, precedence):
	#print('\nperson = ' + str(person))
	trainDataFile = DataFile(PrologFile(mainDir + '/cv' + str(fold) + '_train_' + str(person) + '.pl'))
	#trainFile = open(mainDir + '/cv' + str(fold) + '_train_' + str(person) + '.pl', 'r')
	trainFacts = []
	trainAnswers = []
	trainSyllogisms = set()
	acCount = 0
	caCount = 0
	for line in trainDataFile._database._ClauseDB__nodes:
		if hasattr(line, 'probability') and line.probability == None and str(line.functor) not in ['base', 'mode']:
			if str(line.functor)[0] == 'r':
				trainAnswers.append((line.functor, line.args))
				if str(line.args[0])[0] == "a":
					acCount += 1
				else:
					caCount += 1
			else:
				trainSyllogisms.add(int(str(line.args[0])[1:]))
				trainFacts.append((line.functor, line.args))

	testFile = DataFile(PrologFile(mainDir + "/cv" + str(fold) + "_test_" + str(person) + ".pl"))._database._ClauseDB__nodes

	testFacts = []
	testTasks = {}
	testAnswers = {}
	testPremises = {}
	for line in testFile:
		if hasattr(line, 'probability') and line.probability == None and str(line.functor) != 'base':
			if str(line.functor)[0] == 'r':
				id = int(str(line.args[0])[1:])
				testAnswers[id] = str(line.functor) + '(' + str(line.args[0]) + ',' + str(line.args[1]) + ')'
			else:
				testFacts.append((line.functor, line.args))
				id = int(str(line.args[0])[1:])
				if id not in testPremises:
					testPremises[id] = set([str(line.functor)])
					testTasks[id] = [(str(line.functor), line.args)]
				else:
					testPremises[id].add(str(line.functor))
					testTasks[id].append((str(line.functor), line.args))
	#print('Test Facts \t:' + '\n'.join([str(item[0])+str(item[1])+'.' for item in testFacts]))

	testSyllogisms = []
	for i in range(1, 65):
		if i not in trainSyllogisms:
			testSyllogisms.append(i)

	#print("acCount \t:" + str(acCount))
	#print("caCount \t:" + str(caCount))
	#Get the most frequent response of the users in train dataset
	occurence_count = Counter([functor for (functor, args) in trainAnswers])
	#print("trainAnswers \t:" + str(trainAnswers))
	#print(occurence_count)
	mostFrequentResponse = occurence_count.most_common(1)[0][0]

	#Get the most frequent response of the users in train dataset at predicate level
	#Response Dict = {id: Fact1, Fact2, Response}
	responseDict = {}
	for (functor, args) in trainAnswers:
		id = str(args[0])[1:]
		responseDict[id] = [str(functor)]

	for (functor, args) in trainFacts:
		id = str(args[0])[1:]
		responseDict[id].append(str(functor))

	#print('Train Answers \t: '  + str(trainAnswers) +'\n\n')
	#print('Train Facts \t: '  + str(trainFacts) +'\n\n')
	#print('Response Dict \t: '  + str(responseDict) +'\n\n')

	#Most Frequent Response Dict = {Predcate: (MostFrequentResponseForPredicate, NumberOfOccurances)}

	frequentResponseDict = {}
	for id, p in responseDict.items():
		
		(predicate1, predicate2, predicate3) = p

		if predicate1[0] == 'r':
			premises = [predicate2, predicate3]
			response = predicate1
		elif predicate2[0] == 'r':
			premises = [predicate1, predicate3]
			response = predicate2
		elif predicate3[0] == 'r':
			premises = [predicate1, predicate2]
			response = predicate3

		for premise in premises:
			if premise not in frequentResponseDict:
				frequentResponseDict[premise]= {}
				frequentResponseDict[premise][response] = 1
			else:
				if response not in frequentResponseDict[premise]:
					frequentResponseDict[premise][response] = 1
				else:
					frequentResponseDict[premise][response] += 1

	mostFrequentResponseDict = {}
	for premise, value in frequentResponseDict.items():
		maxFreq = 0
		for response, frequency in value.items():
			if frequency > maxFreq:
				mode = [response]
				maxFreq = frequency
			elif frequency == maxFreq:
				mode.append(response)
		mostFrequentResponseDict[premise] = (mode, maxFreq)

	learn = False		# When learn = True, run ProbFOIL to learn rules from scratch. 
						# Otherwise read learned rules from out files.
	responses = ['rall', 'rsome', 'rno', 'rsomenot', 'rnvc']
	rules = []

	if learn == True:
		def callProbfoil(response):
			print('Probfoil started for '+ response + str(person) + '/2')
			pf = ProbFOIL2(trainDataFile, target = response + str(person) + '/2')
			print('Probfoil ended for '+ response + str(person) + '/2')
			return pf.learn()

		pool = Pool(processes = 5)
		ruleList = pool.map(callProbfoil, responses)

	emptyResponses = []
	for i, response in enumerate(responses):
		if learn == True:
			hypothesis = ruleList[i]
			while str(hypothesis)[-4:] != 'fail':
				rules.append(str(hypothesis)+'.')
				hypothesis = hypothesis.previous
		else:
			pf = open(ruleDir + '/cv' + str(fold) + '_' + response + str(person) + '.out').readlines()
			pfRules = pf[12:-7]
			pfPrecision = pf[-5].split(' ')[-1][:-1]

			if pfRules == []:
				emptyResponses.append(response)
			
			for rule in pfRules:
				if rulesIndicator[0] == '2':
					rules.append(pfPrecision + '::' + rule[:-1]+'.')
				elif rulesIndicator[0] == '1':
					rules.append(rule[:-1]+'.')
	#print('PD Rules \t: ' + '\n'.join(rules) + '\n')
	
	queries = []
	for response in responses:
		for id in testSyllogisms:
			if response in emptyResponses:
				continue
			if response == 'rnvc':
				queries.append('query(rnvc' + str(person) + '(a' + str(id) + ', c' + str(id) + ')).')
			else:
				queries.append('query(' + response + str(person) + '(c' + str(id) + ', a' + str(id) + ')).')
				queries.append('query(' + response + str(person) + '(a' + str(id) + ', c' + str(id) + ')).')

	init = []
	for response in responses:
		init.append('0::' + response[1:] + str(person) + '(a,b).')

	logicallyValidRules_bad = ['0.1::rsomenot#(C, A):-all#(A, B), no#(B, C).','0.1::rsomenot#(C, A):-all#(A, B), no#(C, B).','0.1::rsomenot#(C, A):-all#(B, A), no#(C, B).','0.12::rsome#(C, A):-all#(B, A), all#(B, C).','0.12::rsomenot#(A, C):-all#(B, A), somenot#(B, C).','0.13::rsomenot#(C, A):-some#(B, A), no#(C, B).','0.135::rnvc#(A, C):-all#(A, B), somenot#(B, C).','0.14::rnvc#(A, C):-all#(A, B), some#(B, C).','0.15::rsomenot#(A, C):-some#(B, A), no#(B, C).','0.185::rnvc#(A, C):-all#(B, A), somenot#(C, B).','0.2::rsomenot#(C, A):-some#(A, B), no#(C, B).','0.21::rsomenot#(A, C):-some#(A, B), no#(C, B).','0.25::rsome#(A, C):-all#(A, B), all#(B, C).','0.28::rsomenot#(C, A):-some#(B, A), no#(B, C).','0.1::rsomenot#(C, A):-all#(A, B), no#(C, B).','0.3::rsomenot#(A, C):-all#(B, A), no#(C, B).','0.31::rnvc#(A, C):-all#(A, B), all#(C, B).','0.315::rnvc#(A, C):-some#(A, B), some#(B, C).','0.32::rno#(A, C):-all#(A, B), no#(C, B).','0.32::rnvc#(A, C):-some#(A, B), somenot#(B, C).','0.325::rnvc#(A, C):-all#(A, B), some#(C, B).','0.33::rsome#(A, C):-all#(B, A), some#(B, C).','0.36::rsomenot#(C, A):-all#(A, B), somenot#(C, B).','0.37::rsomenot#(A, C):-some#(A, B), no#(B, C).','0.395::rnvc#(A, C):-no#(A, B), somenot#(B, C).','0.395::rnvc#(A, C):-somenot#(A, B), somenot#(B, C).','0.4::rsome#(A, C):-all#(B, A), all#(B, C).','0.4::rsomenot#(A, C):-all#(A, B), somenot#(C, B).','0.42::rnvc#(A, C):-no#(B, A), somenot#(C, B).','0.425::rnvc#(A, C):-some#(B, A), somenot#(C, B).','0.44::rnvc#(A, C):-no#(A, B), no#(B, C).','0.44::rsomenot#(C, A):-some#(A, B), no#(B, C).','0.45::rsome#(C, A):-all#(A, B), all#(B, C).','0.48::rall#(A, C):-all#(A, B), all#(B, C).','0.48::rno#(C, A):-all#(A, B), no#(C, B).','0.48::rnvc#(A, C):-no#(A, B), somenot#(C, B).','0.49::rsome#(C, A):-all#(B, A), some#(B, C).','0.505::rnvc#(A, C):-some#(B, A), somenot#(B, C).','0.51::rnvc#(A, C):-some#(A, B), some#(C, B).','0.51::rnvc#(A, C):-some#(A, B), somenot#(C, B).','0.51::rsome#(C, A):-all#(B, A), some#(C, B).','0.53::rno#(C, A):-all#(A, B), no#(B, C).','0.53::rnvc#(A, C):-no#(B, A), somenot#(B, C).','0.54::rsomenot#(C, A):-all#(B, A), somenot#(B, C).','0.61::rnvc#(A, C):-some#(B, A), some#(B, C).','0.64::rnvc#(A, C):-somenot#(A, B), somenot#(C, B).','0.655::rno#(A, C):-all#(A, B), no#(B, C).','0.655::rsome#(A, C):-all#(B, A), some#(C, B).','0.66::rnvc#(A, C):-no#(B, A), no#(B, C).','0.66::rnvc#(A, C):-somenot#(B, A), somenot#(B, C).','0.76::rnvc#(A, C):-no#(A, B), no#(C, B).','0.8::rsomenot#(A, C):-some#(B, A), no#(C, B).','0.8::rsomenot#(C, A):-all#(B, A), no#(B, C).','0.81::rall#(C, A):-all#(A, B), all#(B, C).','0.9::rsomenot#(A, C):-all#(B, A), no#(B, C).']
	logicallyValidRules = ['0.920454545454545::rall#(C,A);0.0681818181818182::rsome#(C,A);0.0113636363636364::rsome#(A,C):-all#(A,B),all#(B,C).','0.872727272727273::rall#(A,C);0.0545454545454545::rsome#(C,A);0.0727272727272727::rsome#(A,C):-all#(A,B),all#(B,C).','0.75::rsome#(C,A);0.25::rsome#(A,C):-all#(B,A),all#(B,C).','0.21978021978022::rsome#(C,A);0.78021978021978::rsome#(A,C):-all#(B,A),some#(C,B).','0.650602409638554::rsome#(C,A);0.349397590361446::rsome#(A,C):-all#(B,A),some#(B,C).','0.896551724137931::rno#(C,A);0.0919540229885057::rno#(A,C);0.0114942528735632::rsomenot#(C,A):-all#(A,B),no#(B,C).','1::rsomenot#(C,A):-all#(B,A),no#(C,B).','0.4125::rno#(C,A);0.5875::rno#(A,C):-all#(A,B),no#(C,B).','1::rsomenot#(C,A):-all#(B,A),no#(B,C).','1::rsomenot#(A,C):-all#(A,B),somenot#(C,B).','1::rsomenot#(C,A):-all#(B,A),somenot#(B,C).','0.931818181818182::rsome#(C,A);0.0681818181818182::rsome#(A,C):-all#(B,A),some#(C,B).','0.54320987654321::rsome#(C,A);0.45679012345679::rsome#(A,C):-all#(B,A),some#(B,C).','1::rsomenot#(C,A):-some#(A,B),no#(B,C).','1::rsomenot#(C,A):-some#(B,A),no#(C,B).','1::rsomenot#(C,A):-some#(A,B),no#(C,B).','1::rsomenot#(C,A):-some#(B,A),no#(B,C).','1::rsomenot#(A,C):-all#(B,A),no#(C,B).','0.35::rno#(C,A);0.6375::rno#(A,C);0.0125::rsomenot#(C,A):-all#(A,B),no#(B,C).','0.75::rno#(C,A);0.202380952380952::rno#(A,C);0.0119047619047619::rsomenot#(C,A);0.0357142857142857::rsomenot#(A,C):-all#(A,B),no#(C,B).','1::rsomenot#(A,C):-all#(B,A),no#(B,C).','1::rsomenot#(A,C):-some#(B,A),no#(C,B).','1::rsomenot#(A,C):-some#(A,B),no#(B,C).','1::rsomenot#(A,C):-some#(A,B),no#(C,B).','1::rsomenot#(A,C):-some#(B,A),no#(B,C).','1::rsomenot#(C,A):-all#(A,B),somenot#(C,B).','1::rsomenot#(A,C):-all#(B,A),somenot#(B,C).','1::rnvc#(A,C):-all#(A,B),all#(C,B).','1::rnvc#(A,C):-all#(A,B),some#(B,C).','1::rnvc#(A,C):-all#(A,B),some#(C,B).','1::rnvc#(A,C):-all#(A,B),somenot#(B,C).','1::rnvc#(A,C):-all#(B,A),somenot#(C,B).','1::rnvc#(A,C):-all#(A,B),some#(B,C).','1::rnvc#(A,C):-all#(A,B),some#(C,B).','1::rnvc#(A,C):-some#(A,B),some#(B,C).','1::rnvc#(A,C):-some#(A,B),some#(B,C).','1::rnvc#(A,C):-some#(A,B),some#(C,B).','1::rnvc#(A,C):-some#(B,A),some#(B,C).','1::rnvc#(A,C):-some#(A,B),somenot#(B,C).','1::rnvc#(A,C):-some#(B,A),somenot#(C,B).','1::rnvc#(A,C):-some#(A,B),somenot#(C,B).','1::rnvc#(A,C):-some#(B,A),somenot#(B,C).','1::rnvc#(A,C):-no#(A,B),no#(B,C).','1::rnvc#(A,C):-no#(A,B),no#(B,C).','1::rnvc#(A,C):-no#(A,B),no#(C,B).','1::rnvc#(A,C):-no#(B,A),no#(B,C).','1::rnvc#(A,C):-no#(A,B),somenot#(B,C).','1::rnvc#(A,C):-no#(B,A),somenot#(C,B).','1::rnvc#(A,C):-no#(A,B),somenot#(C,B).','1::rnvc#(A,C):-no#(B,A),somenot#(B,C).','1::rnvc#(A,C):-all#(B,A),somenot#(C,B).','1::rnvc#(A,C):-all#(A,B),somenot#(B,C).','1::rnvc#(A,C):-some#(B,A),somenot#(C,B).','1::rnvc#(A,C):-some#(A,B),somenot#(B,C).','1::rnvc#(A,C):-some#(A,B),somenot#(C,B).','1::rnvc#(A,C):-some#(B,A),somenot#(B,C).','1::rnvc#(A,C):-no#(B,A),somenot#(C,B).','1::rnvc#(A,C):-no#(A,B),somenot#(B,C).','1::rnvc#(A,C):-no#(A,B),somenot#(C,B).','1::rnvc#(A,C):-no#(B,A),somenot#(B,C).','1::rnvc#(A,C):-somenot#(A,B),somenot#(B,C).','1::rnvc#(A,C):-somenot#(A,B),somenot#(B,C).','1::rnvc#(A,C):-somenot#(A,B),somenot#(C,B).','1::rnvc#(A,C):-somenot#(B,A),somenot#(B,C).']
	if rulesIndicator[2] == '0':
		logicallyValidRules = []
	elif rulesIndicator[2] == '1':
		logicallyValidRules = [':'.join(item.split(':')[-2:]).replace('#',str(person)).replace(' ','') for item in logicallyValidRules] #Replace # by person
	elif rulesIndicator[2] == '2':
		logicallyValidRules = [item.replace('#',str(person)).replace(' ','') for item in logicallyValidRules] #Replace # by person

	personIndependentRules = []
	for response in responses:
		outfile = open(pid + '/cv5_fold' + str(fold) + '_' + response + '.out').readlines()
		hypothesis = outfile[12:-7]
		precision = outfile[-5].split(' ')[-1][:-1]
		for rule in hypothesis:
			transformedRule = rule.replace(' ','').replace('task_','').replace('(',str(person)+'(')[:-1]
			if rulesIndicator[1] == '2':
				personIndependentRules.append(precision + '::' + transformedRule +'.')
			elif rulesIndicator[1] == '1':
				personIndependentRules.append(transformedRule +'.')
	#print('PI Rules \t: ' + '\n'.join(personIndependentRules) + '\n')

	eqTasks = {'AA1' : 'AA2', 'AA2' : 'AA1', 'AI1' : 'IA2', 'AI2' : 'IA1', 'AI3' : 'IA3', 'AI4' : 'IA4', 'AE1' : 'EA2', 'AE2' : 'EA1', 'AE3' : 'EA3', 'AE4' : 'EA4', 'AO1' : 'OA2', 'AO2' : 'OA1', 'AO3' : 'OA3', 'AO4' : 'OA4', 'IA1' : 'AI2', 'IA2' : 'AI1', 'IA3' : 'AI3', 'IA4' : 'AI4', 'II1' : 'II2', 'II2' : 'II1', 'IE1' : 'EI2', 'IE2' : 'EI1', 'IE3' : 'EI3', 'IE4' : 'EI4', 'IO1' : 'OI2', 'IO2' : 'OI1', 'IO3' : 'OI3', 'IO4' : 'OI4', 'EA1' : 'AE2', 'EA2' : 'AE1', 'EA3' : 'AE3', 'EA4' : 'AE4', 'EI1' : 'IE2', 'EI2' : 'IE1', 'EI3' : 'IE3', 'EI4' : 'IE4', 'EE1' : 'EE2', 'EE2' : 'EE1', 'EO1' : 'OE2', 'EO2' : 'OE1', 'EO3' : 'OE3', 'EO4' : 'OE4', 'OA1' : 'AO2', 'OA2' : 'AO1', 'OA3' : 'AO3', 'OA4' : 'AO4', 'OI1' : 'IO2', 'OI2' : 'IO1', 'OI3' : 'IO3', 'OI4' : 'IO4', 'OE1' : 'EO2', 'OE2' : 'EO1', 'OE3' : 'EO3', 'OE4' : 'EO4', 'OO1' : 'OO2', 'OO2' : 'OO1'}

	# mfaFreq[fold][Task][Response] = Frequency of that response for that task for that fold
	mfaFreq = [{'II4': {'Aca': 2, 'NVC': 59, 'Eca': 1, 'Aac': 0, 'Oca': 6, 'Oac': 16, 'Eac': 1, 'Ica': 6, 'Iac': 31}, 'OE3': {'Aca': 8, 'NVC': 43, 'Eca': 9, 'Aac': 1, 'Oca': 12, 'Oac': 7, 'Eac': 0, 'Ica': 29, 'Iac': 13}, 'EE1': {'Aca': 33, 'NVC': 54, 'Eca': 14, 'Aac': 1, 'Oca': 3, 'Oac': 5, 'Eac': 4, 'Ica': 6, 'Iac': 8}, 'OE1': {'Aca': 6, 'NVC': 38, 'Eca': 11, 'Aac': 0, 'Oca': 10, 'Oac': 7, 'Eac': 1, 'Ica': 36, 'Iac': 18}, 'OE4': {'Aca': 13, 'NVC': 49, 'Eca': 13, 'Aac': 1, 'Oca': 10, 'Oac': 9, 'Eac': 1, 'Ica': 21, 'Iac': 11}, 'OO4': {'Aca': 2, 'NVC': 71, 'Eca': 2, 'Aac': 0, 'Oca': 14, 'Oac': 8, 'Eac': 0, 'Ica': 13, 'Iac': 11}, 'OO1': {'Aca': 1, 'NVC': 48, 'Eca': 0, 'Aac': 1, 'Oca': 18, 'Oac': 3, 'Eac': 0, 'Ica': 39, 'Iac': 14}, 'EE3': {'Aca': 13, 'NVC': 86, 'Eca': 11, 'Aac': 1, 'Oca': 4, 'Oac': 2, 'Eac': 2, 'Ica': 4, 'Iac': 6}, 'OO3': {'Aca': 2, 'NVC': 77, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 9, 'Eac': 1, 'Ica': 14, 'Iac': 15}, 'OO2': {'Aca': 1, 'NVC': 52, 'Eca': 0, 'Aac': 0, 'Oca': 34, 'Oac': 11, 'Eac': 0, 'Ica': 16, 'Iac': 9}, 'EE2': {'Aca': 17, 'NVC': 57, 'Eca': 26, 'Aac': 1, 'Oca': 5, 'Oac': 6, 'Eac': 3, 'Ica': 4, 'Iac': 9}, 'OI3': {'Aca': 3, 'NVC': 58, 'Eca': 1, 'Aac': 1, 'Oca': 17, 'Oac': 11, 'Eac': 0, 'Ica': 16, 'Iac': 16}, 'OI2': {'Aca': 5, 'NVC': 36, 'Eca': 1, 'Aac': 0, 'Oca': 49, 'Oac': 14, 'Eac': 0, 'Ica': 15, 'Iac': 6}, 'OI1': {'Aca': 1, 'NVC': 41, 'Eca': 1, 'Aac': 3, 'Oca': 18, 'Oac': 6, 'Eac': 1, 'Ica': 26, 'Iac': 23}, 'OI4': {'Aca': 4, 'NVC': 61, 'Eca': 2, 'Aac': 0, 'Oca': 27, 'Oac': 6, 'Eac': 0, 'Ica': 12, 'Iac': 16}, 'EO2': {'Aca': 8, 'NVC': 42, 'Eca': 4, 'Aac': 2, 'Oca': 34, 'Oac': 21, 'Eac': 2, 'Ica': 7, 'Iac': 7}, 'IE1': {'Aca': 20, 'NVC': 25, 'Eca': 6, 'Aac': 1, 'Oca': 16, 'Oac': 4, 'Eac': 1, 'Ica': 44, 'Iac': 11}, 'IE3': {'Aca': 13, 'NVC': 20, 'Eca': 24, 'Aac': 0, 'Oca': 12, 'Oac': 12, 'Eac': 1, 'Ica': 40, 'Iac': 5}, 'IE2': {'Aca': 12, 'NVC': 35, 'Eca': 35, 'Aac': 0, 'Oca': 15, 'Oac': 11, 'Eac': 0, 'Ica': 17, 'Iac': 4}, 'IE4': {'Aca': 19, 'NVC': 32, 'Eca': 11, 'Aac': 0, 'Oca': 12, 'Oac': 4, 'Eac': 2, 'Ica': 32, 'Iac': 9}, 'IO2': {'Aca': 4, 'NVC': 42, 'Eca': 0, 'Aac': 0, 'Oca': 32, 'Oac': 11, 'Eac': 2, 'Ica': 19, 'Iac': 15}, 'OE2': {'Aca': 5, 'NVC': 55, 'Eca': 17, 'Aac': 1, 'Oca': 15, 'Oac': 13, 'Eac': 4, 'Ica': 18, 'Iac': 4}, 'IA4': {'Aca': 2, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 49, 'Eac': 4, 'Ica': 6, 'Iac': 48}, 'EO4': {'Aca': 8, 'NVC': 46, 'Eca': 6, 'Aac': 2, 'Oca': 24, 'Oac': 7, 'Eac': 0, 'Ica': 20, 'Iac': 9}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 3, 'Oca': 4, 'Oac': 20, 'Eac': 0, 'Ica': 6, 'Iac': 89}, 'IA3': {'Aca': 2, 'NVC': 29, 'Eca': 3, 'Aac': 1, 'Oca': 4, 'Oac': 28, 'Eac': 1, 'Ica': 9, 'Iac': 46}, 'IA2': {'Aca': 0, 'NVC': 10, 'Eca': 0, 'Aac': 4, 'Oca': 5, 'Oac': 73, 'Eac': 5, 'Ica': 3, 'Iac': 24}, 'EI1': {'Aca': 32, 'NVC': 33, 'Eca': 7, 'Aac': 1, 'Oca': 28, 'Oac': 2, 'Eac': 0, 'Ica': 10, 'Iac': 7}, 'IO4': {'Aca': 0, 'NVC': 47, 'Eca': 0, 'Aac': 2, 'Oca': 11, 'Oac': 8, 'Eac': 0, 'Ica': 39, 'Iac': 11}, 'II1': {'Aca': 1, 'NVC': 40, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 12, 'Eac': 0, 'Ica': 9, 'Iac': 60}, 'OA1': {'Aca': 4, 'NVC': 20, 'Eca': 4, 'Aac': 2, 'Oca': 19, 'Oac': 6, 'Eac': 1, 'Ica': 37, 'Iac': 28}, 'II3': {'Aca': 4, 'NVC': 59, 'Eca': 1, 'Aac': 1, 'Oca': 4, 'Oac': 18, 'Eac': 0, 'Ica': 6, 'Iac': 29}, 'II2': {'Aca': 1, 'NVC': 39, 'Eca': 2, 'Aac': 1, 'Oca': 9, 'Oac': 48, 'Eac': 1, 'Ica': 2, 'Iac': 24}, 'EE4': {'Aca': 16, 'NVC': 82, 'Eca': 11, 'Aac': 0, 'Oca': 4, 'Oac': 5, 'Eac': 0, 'Ica': 5, 'Iac': 6}, 'IO3': {'Aca': 2, 'NVC': 57, 'Eca': 2, 'Aac': 0, 'Oca': 19, 'Oac': 6, 'Eac': 0, 'Ica': 24, 'Iac': 16}, 'EI3': {'Aca': 20, 'NVC': 31, 'Eca': 14, 'Aac': 0, 'Oca': 37, 'Oac': 4, 'Eac': 0, 'Ica': 14, 'Iac': 4}, 'IO1': {'Aca': 3, 'NVC': 44, 'Eca': 1, 'Aac': 0, 'Oca': 14, 'Oac': 6, 'Eac': 0, 'Ica': 48, 'Iac': 9}, 'EI2': {'Aca': 6, 'NVC': 21, 'Eca': 20, 'Aac': 1, 'Oca': 50, 'Oac': 14, 'Eac': 2, 'Ica': 9, 'Iac': 2}, 'OA3': {'Aca': 6, 'NVC': 19, 'Eca': 4, 'Aac': 1, 'Oca': 17, 'Oac': 15, 'Eac': 0, 'Ica': 39, 'Iac': 17}, 'AO4': {'Aca': 3, 'NVC': 12, 'Eca': 0, 'Aac': 1, 'Oca': 17, 'Oac': 14, 'Eac': 0, 'Ica': 76, 'Iac': 7}, 'AO3': {'Aca': 2, 'NVC': 30, 'Eca': 1, 'Aac': 1, 'Oca': 39, 'Oac': 10, 'Eac': 1, 'Ica': 22, 'Iac': 13}, 'AO2': {'Aca': 4, 'NVC': 20, 'Eca': 3, 'Aac': 0, 'Oca': 50, 'Oac': 17, 'Eac': 2, 'Ica': 17, 'Iac': 14}, 'AO1': {'Aca': 1, 'NVC': 14, 'Eca': 0, 'Aac': 0, 'Oca': 17, 'Oac': 8, 'Eac': 1, 'Ica': 75, 'Iac': 6}, 'EA1': {'Aca': 63, 'NVC': 23, 'Eca': 20, 'Aac': 3, 'Oca': 5, 'Oac': 3, 'Eac': 1, 'Ica': 5, 'Iac': 4}, 'EA3': {'Aca': 66, 'NVC': 8, 'Eca': 35, 'Aac': 1, 'Oca': 4, 'Oac': 1, 'Eac': 0, 'Ica': 7, 'Iac': 5}, 'EA2': {'Aca': 16, 'NVC': 12, 'Eca': 73, 'Aac': 1, 'Oca': 7, 'Oac': 3, 'Eac': 1, 'Ica': 5, 'Iac': 1}, 'EA4': {'Aca': 32, 'NVC': 28, 'Eca': 39, 'Aac': 1, 'Oca': 12, 'Oac': 6, 'Eac': 1, 'Ica': 3, 'Iac': 3}, 'EI4': {'Aca': 9, 'NVC': 44, 'Eca': 9, 'Aac': 0, 'Oca': 33, 'Oac': 9, 'Eac': 0, 'Ica': 11, 'Iac': 9}, 'AE1': {'Aca': 81, 'NVC': 8, 'Eca': 21, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 1, 'Ica': 7, 'Iac': 5}, 'AE3': {'Aca': 47, 'NVC': 14, 'Eca': 46, 'Aac': 0, 'Oca': 4, 'Oac': 3, 'Eac': 3, 'Ica': 4, 'Iac': 2}, 'AE2': {'Aca': 27, 'NVC': 28, 'Eca': 51, 'Aac': 0, 'Oca': 7, 'Oac': 1, 'Eac': 1, 'Ica': 12, 'Iac': 1}, 'AE4': {'Aca': 43, 'NVC': 28, 'Eca': 18, 'Aac': 2, 'Oca': 6, 'Oac': 3, 'Eac': 0, 'Ica': 22, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 7, 'Eca': 0, 'Aac': 2, 'Oca': 3, 'Oac': 33, 'Eac': 4, 'Ica': 6, 'Iac': 67}, 'AI1': {'Aca': 1, 'NVC': 12, 'Eca': 0, 'Aac': 2, 'Oca': 7, 'Oac': 20, 'Eac': 2, 'Ica': 5, 'Iac': 81}, 'AI3': {'Aca': 4, 'NVC': 36, 'Eca': 2, 'Aac': 2, 'Oca': 5, 'Oac': 47, 'Eac': 0, 'Ica': 6, 'Iac': 25}, 'AI2': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 73, 'Eac': 3, 'Ica': 4, 'Iac': 26}, 'EO3': {'Aca': 7, 'NVC': 52, 'Eca': 9, 'Aac': 1, 'Oca': 26, 'Oac': 11, 'Eac': 0, 'Ica': 11, 'Iac': 10}, 'AA4': {'Aca': 1, 'NVC': 27, 'Eca': 0, 'Aac': 50, 'Oca': 1, 'Oac': 14, 'Eac': 13, 'Ica': 3, 'Iac': 21}, 'EO1': {'Aca': 18, 'NVC': 58, 'Eca': 4, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 11, 'Iac': 13}, 'OA4': {'Aca': 3, 'NVC': 13, 'Eca': 3, 'Aac': 4, 'Oca': 64, 'Oac': 8, 'Eac': 1, 'Ica': 16, 'Iac': 13}, 'AA1': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 90, 'Oca': 2, 'Oac': 5, 'Eac': 11, 'Ica': 3, 'Iac': 11}, 'OA2': {'Aca': 0, 'NVC': 19, 'Eca': 2, 'Aac': 0, 'Oca': 74, 'Oac': 12, 'Eac': 1, 'Ica': 9, 'Iac': 10}, 'AA3': {'Aca': 2, 'NVC': 56, 'Eca': 1, 'Aac': 40, 'Oca': 1, 'Oac': 4, 'Eac': 11, 'Ica': 2, 'Iac': 7}, 'AA2': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 33, 'Oca': 2, 'Oac': 5, 'Eac': 71, 'Ica': 1, 'Iac': 7}}, {'II4': {'Aca': 3, 'NVC': 57, 'Eca': 0, 'Aac': 0, 'Oca': 5, 'Oac': 16, 'Eac': 1, 'Ica': 7, 'Iac': 35}, 'OE3': {'Aca': 8, 'NVC': 43, 'Eca': 9, 'Aac': 1, 'Oca': 12, 'Oac': 7, 'Eac': 0, 'Ica': 35, 'Iac': 15}, 'EE1': {'Aca': 28, 'NVC': 56, 'Eca': 15, 'Aac': 1, 'Oca': 4, 'Oac': 5, 'Eac': 4, 'Ica': 6, 'Iac': 9}, 'OE1': {'Aca': 6, 'NVC': 38, 'Eca': 13, 'Aac': 0, 'Oca': 12, 'Oac': 7, 'Eac': 1, 'Ica': 33, 'Iac': 17}, 'OE4': {'Aca': 11, 'NVC': 48, 'Eca': 12, 'Aac': 1, 'Oca': 8, 'Oac': 10, 'Eac': 2, 'Ica': 16, 'Iac': 10}, 'OO4': {'Aca': 2, 'NVC': 76, 'Eca': 2, 'Aac': 0, 'Oca': 16, 'Oac': 8, 'Eac': 0, 'Ica': 13, 'Iac': 13}, 'OO1': {'Aca': 0, 'NVC': 47, 'Eca': 1, 'Aac': 1, 'Oca': 13, 'Oac': 5, 'Eac': 0, 'Ica': 41, 'Iac': 12}, 'EE3': {'Aca': 12, 'NVC': 82, 'Eca': 12, 'Aac': 1, 'Oca': 4, 'Oac': 2, 'Eac': 1, 'Ica': 4, 'Iac': 7}, 'OO3': {'Aca': 2, 'NVC': 75, 'Eca': 1, 'Aac': 2, 'Oca': 9, 'Oac': 6, 'Eac': 1, 'Ica': 16, 'Iac': 15}, 'OO2': {'Aca': 1, 'NVC': 49, 'Eca': 0, 'Aac': 0, 'Oca': 35, 'Oac': 10, 'Eac': 0, 'Ica': 17, 'Iac': 9}, 'EE2': {'Aca': 18, 'NVC': 52, 'Eca': 26, 'Aac': 1, 'Oca': 3, 'Oac': 7, 'Eac': 3, 'Ica': 5, 'Iac': 9}, 'OI3': {'Aca': 3, 'NVC': 54, 'Eca': 1, 'Aac': 1, 'Oca': 19, 'Oac': 12, 'Eac': 0, 'Ica': 14, 'Iac': 18}, 'OI2': {'Aca': 3, 'NVC': 34, 'Eca': 1, 'Aac': 0, 'Oca': 56, 'Oac': 13, 'Eac': 0, 'Ica': 12, 'Iac': 7}, 'OI1': {'Aca': 1, 'NVC': 42, 'Eca': 1, 'Aac': 3, 'Oca': 19, 'Oac': 8, 'Eac': 0, 'Ica': 25, 'Iac': 24}, 'OI4': {'Aca': 3, 'NVC': 56, 'Eca': 2, 'Aac': 0, 'Oca': 28, 'Oac': 4, 'Eac': 0, 'Ica': 13, 'Iac': 18}, 'EO2': {'Aca': 8, 'NVC': 44, 'Eca': 4, 'Aac': 1, 'Oca': 30, 'Oac': 21, 'Eac': 1, 'Ica': 8, 'Iac': 8}, 'IE1': {'Aca': 19, 'NVC': 25, 'Eca': 7, 'Aac': 1, 'Oca': 16, 'Oac': 4, 'Eac': 1, 'Ica': 41, 'Iac': 11}, 'IE3': {'Aca': 17, 'NVC': 21, 'Eca': 23, 'Aac': 0, 'Oca': 11, 'Oac': 12, 'Eac': 1, 'Ica': 37, 'Iac': 5}, 'IE2': {'Aca': 12, 'NVC': 34, 'Eca': 32, 'Aac': 0, 'Oca': 15, 'Oac': 11, 'Eac': 1, 'Ica': 16, 'Iac': 4}, 'IE4': {'Aca': 18, 'NVC': 35, 'Eca': 14, 'Aac': 0, 'Oca': 12, 'Oac': 5, 'Eac': 1, 'Ica': 34, 'Iac': 8}, 'IO2': {'Aca': 3, 'NVC': 45, 'Eca': 0, 'Aac': 0, 'Oca': 33, 'Oac': 11, 'Eac': 2, 'Ica': 19, 'Iac': 14}, 'OE2': {'Aca': 6, 'NVC': 54, 'Eca': 17, 'Aac': 0, 'Oca': 15, 'Oac': 10, 'Eac': 4, 'Ica': 17, 'Iac': 3}, 'IA4': {'Aca': 2, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 51, 'Eac': 3, 'Ica': 6, 'Iac': 48}, 'EO4': {'Aca': 9, 'NVC': 51, 'Eca': 5, 'Aac': 2, 'Oca': 24, 'Oac': 7, 'Eac': 0, 'Ica': 20, 'Iac': 10}, 'IA1': {'Aca': 0, 'NVC': 1, 'Eca': 1, 'Aac': 3, 'Oca': 4, 'Oac': 18, 'Eac': 1, 'Ica': 7, 'Iac': 86}, 'IA3': {'Aca': 2, 'NVC': 32, 'Eca': 3, 'Aac': 1, 'Oca': 6, 'Oac': 28, 'Eac': 1, 'Ica': 7, 'Iac': 50}, 'IA2': {'Aca': 0, 'NVC': 8, 'Eca': 0, 'Aac': 4, 'Oca': 4, 'Oac': 75, 'Eac': 5, 'Ica': 3, 'Iac': 25}, 'EI1': {'Aca': 30, 'NVC': 36, 'Eca': 9, 'Aac': 1, 'Oca': 24, 'Oac': 2, 'Eac': 0, 'Ica': 10, 'Iac': 10}, 'IO4': {'Aca': 0, 'NVC': 47, 'Eca': 0, 'Aac': 2, 'Oca': 13, 'Oac': 8, 'Eac': 0, 'Ica': 46, 'Iac': 12}, 'II1': {'Aca': 1, 'NVC': 39, 'Eca': 1, 'Aac': 1, 'Oca': 7, 'Oac': 11, 'Eac': 0, 'Ica': 9, 'Iac': 57}, 'OA1': {'Aca': 3, 'NVC': 16, 'Eca': 4, 'Aac': 2, 'Oca': 20, 'Oac': 6, 'Eac': 1, 'Ica': 42, 'Iac': 26}, 'II3': {'Aca': 2, 'NVC': 65, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 18, 'Eac': 0, 'Ica': 6, 'Iac': 30}, 'II2': {'Aca': 0, 'NVC': 38, 'Eca': 2, 'Aac': 1, 'Oca': 12, 'Oac': 47, 'Eac': 0, 'Ica': 2, 'Iac': 26}, 'EE4': {'Aca': 18, 'NVC': 78, 'Eca': 12, 'Aac': 0, 'Oca': 4, 'Oac': 5, 'Eac': 0, 'Ica': 5, 'Iac': 6}, 'IO3': {'Aca': 1, 'NVC': 60, 'Eca': 2, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 25, 'Iac': 15}, 'EI3': {'Aca': 23, 'NVC': 32, 'Eca': 12, 'Aac': 0, 'Oca': 40, 'Oac': 4, 'Eac': 0, 'Ica': 11, 'Iac': 5}, 'IO1': {'Aca': 3, 'NVC': 42, 'Eca': 1, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 1, 'Ica': 46, 'Iac': 12}, 'EI2': {'Aca': 5, 'NVC': 23, 'Eca': 22, 'Aac': 1, 'Oca': 52, 'Oac': 12, 'Eac': 2, 'Ica': 9, 'Iac': 3}, 'OA3': {'Aca': 6, 'NVC': 23, 'Eca': 4, 'Aac': 1, 'Oca': 19, 'Oac': 15, 'Eac': 0, 'Ica': 39, 'Iac': 17}, 'AO4': {'Aca': 3, 'NVC': 11, 'Eca': 0, 'Aac': 1, 'Oca': 14, 'Oac': 15, 'Eac': 0, 'Ica': 71, 'Iac': 5}, 'AO3': {'Aca': 2, 'NVC': 31, 'Eca': 1, 'Aac': 1, 'Oca': 46, 'Oac': 12, 'Eac': 1, 'Ica': 22, 'Iac': 13}, 'AO2': {'Aca': 2, 'NVC': 21, 'Eca': 2, 'Aac': 0, 'Oca': 52, 'Oac': 18, 'Eac': 2, 'Ica': 18, 'Iac': 14}, 'AO1': {'Aca': 1, 'NVC': 11, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 9, 'Eac': 2, 'Ica': 80, 'Iac': 6}, 'EA1': {'Aca': 58, 'NVC': 24, 'Eca': 18, 'Aac': 5, 'Oca': 6, 'Oac': 3, 'Eac': 1, 'Ica': 5, 'Iac': 3}, 'EA3': {'Aca': 65, 'NVC': 8, 'Eca': 32, 'Aac': 1, 'Oca': 5, 'Oac': 1, 'Eac': 0, 'Ica': 6, 'Iac': 5}, 'EA2': {'Aca': 20, 'NVC': 10, 'Eca': 76, 'Aac': 1, 'Oca': 7, 'Oac': 4, 'Eac': 1, 'Ica': 5, 'Iac': 1}, 'EA4': {'Aca': 26, 'NVC': 30, 'Eca': 40, 'Aac': 1, 'Oca': 11, 'Oac': 6, 'Eac': 1, 'Ica': 3, 'Iac': 3}, 'EI4': {'Aca': 13, 'NVC': 44, 'Eca': 9, 'Aac': 0, 'Oca': 34, 'Oac': 10, 'Eac': 0, 'Ica': 11, 'Iac': 8}, 'AE1': {'Aca': 84, 'NVC': 7, 'Eca': 21, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 1, 'Ica': 6, 'Iac': 3}, 'AE3': {'Aca': 51, 'NVC': 13, 'Eca': 44, 'Aac': 0, 'Oca': 5, 'Oac': 4, 'Eac': 3, 'Ica': 6, 'Iac': 2}, 'AE2': {'Aca': 28, 'NVC': 28, 'Eca': 52, 'Aac': 0, 'Oca': 6, 'Oac': 0, 'Eac': 1, 'Ica': 10, 'Iac': 1}, 'AE4': {'Aca': 43, 'NVC': 29, 'Eca': 14, 'Aac': 2, 'Oca': 7, 'Oac': 4, 'Eac': 0, 'Ica': 23, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 8, 'Eca': 0, 'Aac': 2, 'Oca': 4, 'Oac': 36, 'Eac': 4, 'Ica': 7, 'Iac': 68}, 'AI1': {'Aca': 1, 'NVC': 12, 'Eca': 0, 'Aac': 2, 'Oca': 6, 'Oac': 18, 'Eac': 1, 'Ica': 4, 'Iac': 76}, 'AI3': {'Aca': 3, 'NVC': 34, 'Eca': 1, 'Aac': 3, 'Oca': 5, 'Oac': 45, 'Eac': 0, 'Ica': 6, 'Iac': 25}, 'AI2': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 77, 'Eac': 4, 'Ica': 6, 'Iac': 25}, 'EO3': {'Aca': 4, 'NVC': 53, 'Eca': 9, 'Aac': 1, 'Oca': 24, 'Oac': 9, 'Eac': 0, 'Ica': 13, 'Iac': 11}, 'AA4': {'Aca': 1, 'NVC': 28, 'Eca': 0, 'Aac': 48, 'Oca': 1, 'Oac': 15, 'Eac': 14, 'Ica': 3, 'Iac': 18}, 'EO1': {'Aca': 17, 'NVC': 56, 'Eca': 4, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 14, 'Iac': 11}, 'OA4': {'Aca': 3, 'NVC': 13, 'Eca': 2, 'Aac': 3, 'Oca': 67, 'Oac': 9, 'Eac': 1, 'Ica': 14, 'Iac': 14}, 'AA1': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 86, 'Oca': 3, 'Oac': 5, 'Eac': 11, 'Ica': 3, 'Iac': 9}, 'OA2': {'Aca': 1, 'NVC': 18, 'Eca': 1, 'Aac': 0, 'Oca': 72, 'Oac': 13, 'Eac': 1, 'Ica': 12, 'Iac': 7}, 'AA3': {'Aca': 2, 'NVC': 57, 'Eca': 1, 'Aac': 37, 'Oca': 1, 'Oac': 5, 'Eac': 15, 'Ica': 3, 'Iac': 9}, 'AA2': {'Aca': 0, 'NVC': 6, 'Eca': 2, 'Aac': 32, 'Oca': 2, 'Oac': 6, 'Eac': 76, 'Ica': 1, 'Iac': 8}}, {'II4': {'Aca': 3, 'NVC': 59, 'Eca': 1, 'Aac': 0, 'Oca': 5, 'Oac': 19, 'Eac': 0, 'Ica': 6, 'Iac': 33}, 'OE3': {'Aca': 8, 'NVC': 40, 'Eca': 8, 'Aac': 1, 'Oca': 12, 'Oac': 5, 'Eac': 0, 'Ica': 32, 'Iac': 15}, 'EE1': {'Aca': 30, 'NVC': 51, 'Eca': 12, 'Aac': 1, 'Oca': 4, 'Oac': 5, 'Eac': 3, 'Ica': 5, 'Iac': 9}, 'OE1': {'Aca': 6, 'NVC': 40, 'Eca': 11, 'Aac': 0, 'Oca': 13, 'Oac': 6, 'Eac': 1, 'Ica': 32, 'Iac': 19}, 'OE4': {'Aca': 12, 'NVC': 49, 'Eca': 10, 'Aac': 1, 'Oca': 9, 'Oac': 9, 'Eac': 1, 'Ica': 19, 'Iac': 12}, 'OO4': {'Aca': 2, 'NVC': 77, 'Eca': 2, 'Aac': 0, 'Oca': 14, 'Oac': 7, 'Eac': 0, 'Ica': 13, 'Iac': 11}, 'OO1': {'Aca': 1, 'NVC': 47, 'Eca': 1, 'Aac': 1, 'Oca': 15, 'Oac': 5, 'Eac': 0, 'Ica': 41, 'Iac': 14}, 'EE3': {'Aca': 10, 'NVC': 84, 'Eca': 9, 'Aac': 1, 'Oca': 3, 'Oac': 2, 'Eac': 2, 'Ica': 4, 'Iac': 5}, 'OO3': {'Aca': 2, 'NVC': 76, 'Eca': 1, 'Aac': 2, 'Oca': 9, 'Oac': 9, 'Eac': 1, 'Ica': 16, 'Iac': 14}, 'OO2': {'Aca': 1, 'NVC': 48, 'Eca': 0, 'Aac': 0, 'Oca': 37, 'Oac': 10, 'Eac': 0, 'Ica': 16, 'Iac': 8}, 'EE2': {'Aca': 18, 'NVC': 52, 'Eca': 26, 'Aac': 1, 'Oca': 5, 'Oac': 8, 'Eac': 2, 'Ica': 5, 'Iac': 8}, 'OI3': {'Aca': 3, 'NVC': 57, 'Eca': 2, 'Aac': 1, 'Oca': 20, 'Oac': 10, 'Eac': 0, 'Ica': 17, 'Iac': 19}, 'OI2': {'Aca': 5, 'NVC': 34, 'Eca': 0, 'Aac': 0, 'Oca': 49, 'Oac': 11, 'Eac': 0, 'Ica': 12, 'Iac': 6}, 'OI1': {'Aca': 0, 'NVC': 41, 'Eca': 0, 'Aac': 3, 'Oca': 20, 'Oac': 9, 'Eac': 1, 'Ica': 28, 'Iac': 23}, 'OI4': {'Aca': 4, 'NVC': 60, 'Eca': 2, 'Aac': 0, 'Oca': 22, 'Oac': 6, 'Eac': 0, 'Ica': 11, 'Iac': 18}, 'EO2': {'Aca': 7, 'NVC': 46, 'Eca': 3, 'Aac': 3, 'Oca': 28, 'Oac': 25, 'Eac': 2, 'Ica': 8, 'Iac': 7}, 'IE1': {'Aca': 20, 'NVC': 24, 'Eca': 7, 'Aac': 1, 'Oca': 15, 'Oac': 2, 'Eac': 1, 'Ica': 43, 'Iac': 11}, 'IE3': {'Aca': 15, 'NVC': 23, 'Eca': 25, 'Aac': 0, 'Oca': 10, 'Oac': 11, 'Eac': 1, 'Ica': 36, 'Iac': 7}, 'IE2': {'Aca': 9, 'NVC': 39, 'Eca': 33, 'Aac': 0, 'Oca': 15, 'Oac': 11, 'Eac': 1, 'Ica': 15, 'Iac': 4}, 'IE4': {'Aca': 17, 'NVC': 36, 'Eca': 14, 'Aac': 0, 'Oca': 10, 'Oac': 4, 'Eac': 2, 'Ica': 34, 'Iac': 7}, 'IO2': {'Aca': 4, 'NVC': 45, 'Eca': 0, 'Aac': 0, 'Oca': 33, 'Oac': 11, 'Eac': 2, 'Ica': 20, 'Iac': 14}, 'OE2': {'Aca': 6, 'NVC': 50, 'Eca': 14, 'Aac': 1, 'Oca': 16, 'Oac': 11, 'Eac': 3, 'Ica': 13, 'Iac': 4}, 'IA4': {'Aca': 2, 'NVC': 8, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 51, 'Eac': 3, 'Ica': 5, 'Iac': 44}, 'EO4': {'Aca': 7, 'NVC': 48, 'Eca': 7, 'Aac': 1, 'Oca': 23, 'Oac': 6, 'Eac': 0, 'Ica': 18, 'Iac': 10}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 2, 'Oca': 4, 'Oac': 19, 'Eac': 1, 'Ica': 7, 'Iac': 89}, 'IA3': {'Aca': 2, 'NVC': 30, 'Eca': 3, 'Aac': 1, 'Oca': 4, 'Oac': 29, 'Eac': 0, 'Ica': 8, 'Iac': 43}, 'IA2': {'Aca': 0, 'NVC': 11, 'Eca': 0, 'Aac': 2, 'Oca': 5, 'Oac': 70, 'Eac': 5, 'Ica': 3, 'Iac': 24}, 'EI1': {'Aca': 32, 'NVC': 34, 'Eca': 8, 'Aac': 2, 'Oca': 27, 'Oac': 2, 'Eac': 0, 'Ica': 10, 'Iac': 9}, 'IO4': {'Aca': 0, 'NVC': 45, 'Eca': 0, 'Aac': 2, 'Oca': 12, 'Oac': 9, 'Eac': 0, 'Ica': 42, 'Iac': 12}, 'II1': {'Aca': 1, 'NVC': 39, 'Eca': 0, 'Aac': 1, 'Oca': 5, 'Oac': 12, 'Eac': 0, 'Ica': 7, 'Iac': 60}, 'OA1': {'Aca': 3, 'NVC': 18, 'Eca': 3, 'Aac': 1, 'Oca': 18, 'Oac': 8, 'Eac': 1, 'Ica': 39, 'Iac': 31}, 'II3': {'Aca': 4, 'NVC': 58, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 19, 'Eac': 0, 'Ica': 6, 'Iac': 30}, 'II2': {'Aca': 1, 'NVC': 40, 'Eca': 2, 'Aac': 1, 'Oca': 12, 'Oac': 45, 'Eac': 1, 'Ica': 1, 'Iac': 26}, 'EE4': {'Aca': 14, 'NVC': 82, 'Eca': 12, 'Aac': 0, 'Oca': 4, 'Oac': 5, 'Eac': 0, 'Ica': 5, 'Iac': 6}, 'IO3': {'Aca': 1, 'NVC': 60, 'Eca': 2, 'Aac': 0, 'Oca': 18, 'Oac': 5, 'Eac': 0, 'Ica': 25, 'Iac': 15}, 'EI3': {'Aca': 23, 'NVC': 30, 'Eca': 13, 'Aac': 0, 'Oca': 40, 'Oac': 5, 'Eac': 0, 'Ica': 14, 'Iac': 3}, 'IO1': {'Aca': 3, 'NVC': 39, 'Eca': 1, 'Aac': 0, 'Oca': 15, 'Oac': 7, 'Eac': 1, 'Ica': 46, 'Iac': 12}, 'EI2': {'Aca': 5, 'NVC': 20, 'Eca': 18, 'Aac': 1, 'Oca': 45, 'Oac': 14, 'Eac': 3, 'Ica': 11, 'Iac': 3}, 'OA3': {'Aca': 6, 'NVC': 25, 'Eca': 3, 'Aac': 1, 'Oca': 19, 'Oac': 14, 'Eac': 0, 'Ica': 41, 'Iac': 18}, 'AO4': {'Aca': 3, 'NVC': 10, 'Eca': 0, 'Aac': 1, 'Oca': 13, 'Oac': 17, 'Eac': 0, 'Ica': 77, 'Iac': 6}, 'AO3': {'Aca': 1, 'NVC': 27, 'Eca': 0, 'Aac': 0, 'Oca': 45, 'Oac': 11, 'Eac': 0, 'Ica': 25, 'Iac': 14}, 'AO2': {'Aca': 4, 'NVC': 22, 'Eca': 3, 'Aac': 0, 'Oca': 51, 'Oac': 16, 'Eac': 2, 'Ica': 16, 'Iac': 12}, 'AO1': {'Aca': 1, 'NVC': 15, 'Eca': 1, 'Aac': 0, 'Oca': 14, 'Oac': 10, 'Eac': 2, 'Ica': 78, 'Iac': 5}, 'EA1': {'Aca': 64, 'NVC': 22, 'Eca': 17, 'Aac': 4, 'Oca': 6, 'Oac': 3, 'Eac': 0, 'Ica': 5, 'Iac': 4}, 'EA3': {'Aca': 65, 'NVC': 9, 'Eca': 32, 'Aac': 1, 'Oca': 4, 'Oac': 1, 'Eac': 0, 'Ica': 7, 'Iac': 6}, 'EA2': {'Aca': 18, 'NVC': 9, 'Eca': 79, 'Aac': 1, 'Oca': 7, 'Oac': 4, 'Eac': 1, 'Ica': 3, 'Iac': 1}, 'EA4': {'Aca': 32, 'NVC': 31, 'Eca': 38, 'Aac': 0, 'Oca': 14, 'Oac': 6, 'Eac': 0, 'Ica': 2, 'Iac': 3}, 'EI4': {'Aca': 14, 'NVC': 44, 'Eca': 10, 'Aac': 0, 'Oca': 31, 'Oac': 10, 'Eac': 0, 'Ica': 12, 'Iac': 9}, 'AE1': {'Aca': 84, 'NVC': 8, 'Eca': 23, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 1, 'Ica': 6, 'Iac': 5}, 'AE3': {'Aca': 51, 'NVC': 13, 'Eca': 44, 'Aac': 0, 'Oca': 5, 'Oac': 3, 'Eac': 2, 'Ica': 6, 'Iac': 2}, 'AE2': {'Aca': 25, 'NVC': 29, 'Eca': 51, 'Aac': 0, 'Oca': 7, 'Oac': 1, 'Eac': 1, 'Ica': 12, 'Iac': 1}, 'AE4': {'Aca': 43, 'NVC': 26, 'Eca': 15, 'Aac': 2, 'Oca': 7, 'Oac': 3, 'Eac': 0, 'Ica': 23, 'Iac': 3}, 'AI4': {'Aca': 0, 'NVC': 9, 'Eca': 0, 'Aac': 2, 'Oca': 4, 'Oac': 34, 'Eac': 4, 'Ica': 5, 'Iac': 65}, 'AI1': {'Aca': 0, 'NVC': 13, 'Eca': 0, 'Aac': 2, 'Oca': 7, 'Oac': 17, 'Eac': 1, 'Ica': 7, 'Iac': 77}, 'AI3': {'Aca': 2, 'NVC': 35, 'Eca': 1, 'Aac': 2, 'Oca': 4, 'Oac': 48, 'Eac': 0, 'Ica': 5, 'Iac': 24}, 'AI2': {'Aca': 0, 'NVC': 5, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 73, 'Eac': 4, 'Ica': 6, 'Iac': 20}, 'EO3': {'Aca': 7, 'NVC': 49, 'Eca': 6, 'Aac': 1, 'Oca': 28, 'Oac': 10, 'Eac': 0, 'Ica': 12, 'Iac': 10}, 'AA4': {'Aca': 0, 'NVC': 24, 'Eca': 0, 'Aac': 46, 'Oca': 0, 'Oac': 13, 'Eac': 11, 'Ica': 3, 'Iac': 22}, 'EO1': {'Aca': 15, 'NVC': 59, 'Eca': 5, 'Aac': 0, 'Oca': 18, 'Oac': 6, 'Eac': 0, 'Ica': 12, 'Iac': 12}, 'OA4': {'Aca': 2, 'NVC': 13, 'Eca': 3, 'Aac': 3, 'Oca': 63, 'Oac': 6, 'Eac': 1, 'Ica': 15, 'Iac': 11}, 'AA1': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 88, 'Oca': 3, 'Oac': 3, 'Eac': 12, 'Ica': 3, 'Iac': 10}, 'OA2': {'Aca': 1, 'NVC': 18, 'Eca': 2, 'Aac': 0, 'Oca': 72, 'Oac': 14, 'Eac': 1, 'Ica': 11, 'Iac': 8}, 'AA3': {'Aca': 2, 'NVC': 52, 'Eca': 1, 'Aac': 40, 'Oca': 1, 'Oac': 5, 'Eac': 13, 'Ica': 2, 'Iac': 8}, 'AA2': {'Aca': 0, 'NVC': 5, 'Eca': 2, 'Aac': 25, 'Oca': 2, 'Oac': 4, 'Eac': 72, 'Ica': 1, 'Iac': 8}}, {'II4': {'Aca': 3, 'NVC': 57, 'Eca': 1, 'Aac': 0, 'Oca': 6, 'Oac': 18, 'Eac': 1, 'Ica': 6, 'Iac': 31}, 'OE3': {'Aca': 7, 'NVC': 39, 'Eca': 8, 'Aac': 1, 'Oca': 12, 'Oac': 6, 'Eac': 0, 'Ica': 33, 'Iac': 15}, 'EE1': {'Aca': 32, 'NVC': 52, 'Eca': 16, 'Aac': 0, 'Oca': 3, 'Oac': 3, 'Eac': 3, 'Ica': 6, 'Iac': 8}, 'OE1': {'Aca': 6, 'NVC': 38, 'Eca': 10, 'Aac': 0, 'Oca': 12, 'Oac': 5, 'Eac': 0, 'Ica': 33, 'Iac': 18}, 'OE4': {'Aca': 12, 'NVC': 47, 'Eca': 13, 'Aac': 1, 'Oca': 8, 'Oac': 9, 'Eac': 2, 'Ica': 19, 'Iac': 10}, 'OO4': {'Aca': 1, 'NVC': 76, 'Eca': 2, 'Aac': 0, 'Oca': 11, 'Oac': 8, 'Eac': 0, 'Ica': 13, 'Iac': 12}, 'OO1': {'Aca': 1, 'NVC': 49, 'Eca': 1, 'Aac': 1, 'Oca': 16, 'Oac': 5, 'Eac': 0, 'Ica': 42, 'Iac': 13}, 'EE3': {'Aca': 14, 'NVC': 82, 'Eca': 10, 'Aac': 1, 'Oca': 5, 'Oac': 1, 'Eac': 2, 'Ica': 3, 'Iac': 5}, 'OO3': {'Aca': 2, 'NVC': 75, 'Eca': 1, 'Aac': 2, 'Oca': 7, 'Oac': 8, 'Eac': 1, 'Ica': 16, 'Iac': 14}, 'OO2': {'Aca': 1, 'NVC': 52, 'Eca': 0, 'Aac': 0, 'Oca': 38, 'Oac': 10, 'Eac': 0, 'Ica': 18, 'Iac': 6}, 'EE2': {'Aca': 17, 'NVC': 55, 'Eca': 25, 'Aac': 1, 'Oca': 4, 'Oac': 7, 'Eac': 3, 'Ica': 5, 'Iac': 8}, 'OI3': {'Aca': 3, 'NVC': 56, 'Eca': 2, 'Aac': 1, 'Oca': 20, 'Oac': 13, 'Eac': 0, 'Ica': 15, 'Iac': 19}, 'OI2': {'Aca': 5, 'NVC': 33, 'Eca': 1, 'Aac': 0, 'Oca': 52, 'Oac': 12, 'Eac': 0, 'Ica': 14, 'Iac': 8}, 'OI1': {'Aca': 1, 'NVC': 44, 'Eca': 1, 'Aac': 3, 'Oca': 15, 'Oac': 9, 'Eac': 1, 'Ica': 27, 'Iac': 25}, 'OI4': {'Aca': 3, 'NVC': 54, 'Eca': 2, 'Aac': 0, 'Oca': 27, 'Oac': 6, 'Eac': 0, 'Ica': 13, 'Iac': 19}, 'EO2': {'Aca': 7, 'NVC': 42, 'Eca': 4, 'Aac': 3, 'Oca': 31, 'Oac': 23, 'Eac': 2, 'Ica': 6, 'Iac': 7}, 'IE1': {'Aca': 19, 'NVC': 23, 'Eca': 6, 'Aac': 1, 'Oca': 14, 'Oac': 4, 'Eac': 0, 'Ica': 46, 'Iac': 12}, 'IE3': {'Aca': 16, 'NVC': 21, 'Eca': 24, 'Aac': 0, 'Oca': 10, 'Oac': 11, 'Eac': 1, 'Ica': 37, 'Iac': 7}, 'IE2': {'Aca': 11, 'NVC': 35, 'Eca': 33, 'Aac': 0, 'Oca': 15, 'Oac': 11, 'Eac': 1, 'Ica': 16, 'Iac': 4}, 'IE4': {'Aca': 19, 'NVC': 36, 'Eca': 16, 'Aac': 0, 'Oca': 11, 'Oac': 5, 'Eac': 1, 'Ica': 33, 'Iac': 8}, 'IO2': {'Aca': 4, 'NVC': 44, 'Eca': 0, 'Aac': 0, 'Oca': 30, 'Oac': 10, 'Eac': 2, 'Ica': 18, 'Iac': 15}, 'OE2': {'Aca': 7, 'NVC': 56, 'Eca': 13, 'Aac': 1, 'Oca': 14, 'Oac': 13, 'Eac': 3, 'Ica': 17, 'Iac': 3}, 'IA4': {'Aca': 2, 'NVC': 8, 'Eca': 0, 'Aac': 1, 'Oca': 5, 'Oac': 49, 'Eac': 3, 'Ica': 5, 'Iac': 51}, 'EO4': {'Aca': 8, 'NVC': 50, 'Eca': 6, 'Aac': 1, 'Oca': 26, 'Oac': 5, 'Eac': 0, 'Ica': 21, 'Iac': 9}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 2, 'Oca': 3, 'Oac': 20, 'Eac': 1, 'Ica': 7, 'Iac': 88}, 'IA3': {'Aca': 2, 'NVC': 29, 'Eca': 3, 'Aac': 1, 'Oca': 6, 'Oac': 28, 'Eac': 1, 'Ica': 10, 'Iac': 47}, 'IA2': {'Aca': 0, 'NVC': 11, 'Eca': 0, 'Aac': 3, 'Oca': 4, 'Oac': 76, 'Eac': 6, 'Ica': 3, 'Iac': 25}, 'EI1': {'Aca': 32, 'NVC': 33, 'Eca': 10, 'Aac': 2, 'Oca': 27, 'Oac': 2, 'Eac': 0, 'Ica': 11, 'Iac': 10}, 'IO4': {'Aca': 0, 'NVC': 50, 'Eca': 0, 'Aac': 2, 'Oca': 13, 'Oac': 10, 'Eac': 0, 'Ica': 43, 'Iac': 10}, 'II1': {'Aca': 1, 'NVC': 39, 'Eca': 1, 'Aac': 0, 'Oca': 7, 'Oac': 11, 'Eac': 0, 'Ica': 9, 'Iac': 55}, 'OA1': {'Aca': 4, 'NVC': 19, 'Eca': 3, 'Aac': 1, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 44, 'Iac': 29}, 'II3': {'Aca': 4, 'NVC': 64, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 18, 'Eac': 0, 'Ica': 4, 'Iac': 25}, 'II2': {'Aca': 1, 'NVC': 34, 'Eca': 2, 'Aac': 1, 'Oca': 12, 'Oac': 46, 'Eac': 1, 'Ica': 2, 'Iac': 26}, 'EE4': {'Aca': 18, 'NVC': 78, 'Eca': 9, 'Aac': 0, 'Oca': 4, 'Oac': 5, 'Eac': 0, 'Ica': 3, 'Iac': 6}, 'IO3': {'Aca': 2, 'NVC': 59, 'Eca': 2, 'Aac': 0, 'Oca': 18, 'Oac': 6, 'Eac': 0, 'Ica': 25, 'Iac': 13}, 'EI3': {'Aca': 21, 'NVC': 31, 'Eca': 13, 'Aac': 0, 'Oca': 36, 'Oac': 5, 'Eac': 0, 'Ica': 12, 'Iac': 5}, 'IO1': {'Aca': 2, 'NVC': 43, 'Eca': 1, 'Aac': 0, 'Oca': 15, 'Oac': 7, 'Eac': 1, 'Ica': 48, 'Iac': 13}, 'EI2': {'Aca': 6, 'NVC': 22, 'Eca': 20, 'Aac': 1, 'Oca': 51, 'Oac': 12, 'Eac': 3, 'Ica': 11, 'Iac': 3}, 'OA3': {'Aca': 5, 'NVC': 24, 'Eca': 4, 'Aac': 1, 'Oca': 17, 'Oac': 14, 'Eac': 0, 'Ica': 43, 'Iac': 18}, 'AO4': {'Aca': 2, 'NVC': 12, 'Eca': 0, 'Aac': 1, 'Oca': 15, 'Oac': 15, 'Eac': 0, 'Ica': 73, 'Iac': 7}, 'AO3': {'Aca': 2, 'NVC': 27, 'Eca': 1, 'Aac': 1, 'Oca': 43, 'Oac': 12, 'Eac': 1, 'Ica': 22, 'Iac': 12}, 'AO2': {'Aca': 3, 'NVC': 22, 'Eca': 1, 'Aac': 0, 'Oca': 52, 'Oac': 13, 'Eac': 2, 'Ica': 18, 'Iac': 14}, 'AO1': {'Aca': 1, 'NVC': 13, 'Eca': 1, 'Aac': 0, 'Oca': 18, 'Oac': 9, 'Eac': 1, 'Ica': 78, 'Iac': 6}, 'EA1': {'Aca': 62, 'NVC': 23, 'Eca': 19, 'Aac': 5, 'Oca': 6, 'Oac': 2, 'Eac': 1, 'Ica': 5, 'Iac': 4}, 'EA3': {'Aca': 65, 'NVC': 8, 'Eca': 32, 'Aac': 1, 'Oca': 4, 'Oac': 1, 'Eac': 0, 'Ica': 6, 'Iac': 7}, 'EA2': {'Aca': 21, 'NVC': 10, 'Eca': 79, 'Aac': 1, 'Oca': 6, 'Oac': 4, 'Eac': 0, 'Ica': 5, 'Iac': 1}, 'EA4': {'Aca': 32, 'NVC': 29, 'Eca': 40, 'Aac': 1, 'Oca': 13, 'Oac': 5, 'Eac': 1, 'Ica': 2, 'Iac': 2}, 'EI4': {'Aca': 12, 'NVC': 42, 'Eca': 9, 'Aac': 0, 'Oca': 36, 'Oac': 9, 'Eac': 0, 'Ica': 9, 'Iac': 9}, 'AE1': {'Aca': 83, 'NVC': 8, 'Eca': 22, 'Aac': 0, 'Oca': 1, 'Oac': 1, 'Eac': 1, 'Ica': 6, 'Iac': 5}, 'AE3': {'Aca': 52, 'NVC': 13, 'Eca': 43, 'Aac': 0, 'Oca': 4, 'Oac': 3, 'Eac': 3, 'Ica': 6, 'Iac': 1}, 'AE2': {'Aca': 26, 'NVC': 27, 'Eca': 48, 'Aac': 0, 'Oca': 7, 'Oac': 1, 'Eac': 1, 'Ica': 12, 'Iac': 1}, 'AE4': {'Aca': 44, 'NVC': 29, 'Eca': 16, 'Aac': 2, 'Oca': 6, 'Oac': 4, 'Eac': 0, 'Ica': 22, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 8, 'Eca': 0, 'Aac': 2, 'Oca': 3, 'Oac': 34, 'Eac': 4, 'Ica': 8, 'Iac': 64}, 'AI1': {'Aca': 1, 'NVC': 14, 'Eca': 0, 'Aac': 2, 'Oca': 7, 'Oac': 18, 'Eac': 2, 'Ica': 7, 'Iac': 76}, 'AI3': {'Aca': 4, 'NVC': 37, 'Eca': 2, 'Aac': 3, 'Oca': 2, 'Oac': 49, 'Eac': 0, 'Ica': 5, 'Iac': 23}, 'AI2': {'Aca': 0, 'NVC': 6, 'Eca': 0, 'Aac': 1, 'Oca': 6, 'Oac': 78, 'Eac': 4, 'Ica': 5, 'Iac': 27}, 'EO3': {'Aca': 7, 'NVC': 47, 'Eca': 7, 'Aac': 1, 'Oca': 28, 'Oac': 10, 'Eac': 0, 'Ica': 12, 'Iac': 11}, 'AA4': {'Aca': 1, 'NVC': 26, 'Eca': 0, 'Aac': 44, 'Oca': 1, 'Oac': 15, 'Eac': 14, 'Ica': 3, 'Iac': 19}, 'EO1': {'Aca': 13, 'NVC': 54, 'Eca': 3, 'Aac': 0, 'Oca': 19, 'Oac': 5, 'Eac': 0, 'Ica': 13, 'Iac': 11}, 'OA4': {'Aca': 3, 'NVC': 14, 'Eca': 3, 'Aac': 4, 'Oca': 67, 'Oac': 9, 'Eac': 1, 'Ica': 14, 'Iac': 14}, 'AA1': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 86, 'Oca': 3, 'Oac': 4, 'Eac': 13, 'Ica': 3, 'Iac': 9}, 'OA2': {'Aca': 1, 'NVC': 15, 'Eca': 1, 'Aac': 0, 'Oca': 72, 'Oac': 11, 'Eac': 0, 'Ica': 11, 'Iac': 9}, 'AA3': {'Aca': 1, 'NVC': 57, 'Eca': 0, 'Aac': 36, 'Oca': 1, 'Oac': 5, 'Eac': 12, 'Ica': 3, 'Iac': 8}, 'AA2': {'Aca': 0, 'NVC': 6, 'Eca': 2, 'Aac': 30, 'Oca': 1, 'Oac': 5, 'Eac': 73, 'Ica': 0, 'Iac': 7}}, {'II4': {'Aca': 3, 'NVC': 63, 'Eca': 1, 'Aac': 0, 'Oca': 5, 'Oac': 17, 'Eac': 1, 'Ica': 6, 'Iac': 32}, 'OE3': {'Aca': 8, 'NVC': 43, 'Eca': 7, 'Aac': 0, 'Oca': 12, 'Oac': 7, 'Eac': 0, 'Ica': 33, 'Iac': 15}, 'EE1': {'Aca': 35, 'NVC': 52, 'Eca': 14, 'Aac': 1, 'Oca': 4, 'Oac': 5, 'Eac': 4, 'Ica': 6, 'Iac': 7}, 'OE1': {'Aca': 5, 'NVC': 38, 'Eca': 11, 'Aac': 0, 'Oca': 12, 'Oac': 6, 'Eac': 1, 'Ica': 31, 'Iac': 19}, 'OE4': {'Aca': 10, 'NVC': 52, 'Eca': 13, 'Aac': 1, 'Oca': 10, 'Oac': 10, 'Eac': 2, 'Ica': 21, 'Iac': 12}, 'OO4': {'Aca': 2, 'NVC': 76, 'Eca': 2, 'Aac': 0, 'Oca': 16, 'Oac': 8, 'Eac': 0, 'Ica': 12, 'Iac': 11}, 'OO1': {'Aca': 1, 'NVC': 48, 'Eca': 1, 'Aac': 1, 'Oca': 17, 'Oac': 5, 'Eac': 0, 'Ica': 39, 'Iac': 13}, 'EE3': {'Aca': 13, 'NVC': 79, 'Eca': 10, 'Aac': 1, 'Oca': 5, 'Oac': 2, 'Eac': 2, 'Ica': 3, 'Iac': 7}, 'OO3': {'Aca': 2, 'NVC': 72, 'Eca': 1, 'Aac': 2, 'Oca': 7, 'Oac': 7, 'Eac': 1, 'Ica': 16, 'Iac': 11}, 'OO2': {'Aca': 1, 'NVC': 51, 'Eca': 0, 'Aac': 0, 'Oca': 35, 'Oac': 10, 'Eac': 0, 'Ica': 17, 'Iac': 9}, 'EE2': {'Aca': 15, 'NVC': 50, 'Eca': 26, 'Aac': 1, 'Oca': 5, 'Oac': 6, 'Eac': 2, 'Ica': 3, 'Iac': 10}, 'OI3': {'Aca': 2, 'NVC': 56, 'Eca': 2, 'Aac': 1, 'Oca': 19, 'Oac': 13, 'Eac': 0, 'Ica': 16, 'Iac': 19}, 'OI2': {'Aca': 3, 'NVC': 32, 'Eca': 1, 'Aac': 0, 'Oca': 55, 'Oac': 13, 'Eac': 0, 'Ica': 11, 'Iac': 7}, 'OI1': {'Aca': 1, 'NVC': 45, 'Eca': 1, 'Aac': 3, 'Oca': 20, 'Oac': 9, 'Eac': 1, 'Ica': 26, 'Iac': 22}, 'OI4': {'Aca': 3, 'NVC': 62, 'Eca': 2, 'Aac': 0, 'Oca': 28, 'Oac': 4, 'Eac': 0, 'Ica': 10, 'Iac': 18}, 'EO2': {'Aca': 8, 'NVC': 41, 'Eca': 4, 'Aac': 3, 'Oca': 31, 'Oac': 21, 'Eac': 2, 'Ica': 8, 'Iac': 6}, 'IE1': {'Aca': 21, 'NVC': 25, 'Eca': 6, 'Aac': 1, 'Oca': 14, 'Oac': 4, 'Eac': 1, 'Ica': 43, 'Iac': 9}, 'IE3': {'Aca': 16, 'NVC': 20, 'Eca': 24, 'Aac': 0, 'Oca': 11, 'Oac': 10, 'Eac': 0, 'Ica': 39, 'Iac': 7}, 'IE2': {'Aca': 11, 'NVC': 36, 'Eca': 29, 'Aac': 0, 'Oca': 12, 'Oac': 8, 'Eac': 1, 'Ica': 18, 'Iac': 5}, 'IE4': {'Aca': 18, 'NVC': 34, 'Eca': 16, 'Aac': 0, 'Oca': 9, 'Oac': 4, 'Eac': 2, 'Ica': 30, 'Iac': 8}, 'IO2': {'Aca': 4, 'NVC': 47, 'Eca': 0, 'Aac': 0, 'Oca': 33, 'Oac': 11, 'Eac': 2, 'Ica': 18, 'Iac': 13}, 'OE2': {'Aca': 6, 'NVC': 53, 'Eca': 18, 'Aac': 1, 'Oca': 15, 'Oac': 12, 'Eac': 4, 'Ica': 18, 'Iac': 4}, 'IA4': {'Aca': 2, 'NVC': 7, 'Eca': 1, 'Aac': 0, 'Oca': 6, 'Oac': 52, 'Eac': 3, 'Ica': 5, 'Iac': 51}, 'EO4': {'Aca': 9, 'NVC': 52, 'Eca': 7, 'Aac': 2, 'Oca': 23, 'Oac': 7, 'Eac': 0, 'Ica': 19, 'Iac': 9}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 0, 'Aac': 3, 'Oca': 2, 'Oac': 20, 'Eac': 1, 'Ica': 8, 'Iac': 88}, 'IA3': {'Aca': 1, 'NVC': 28, 'Eca': 3, 'Aac': 1, 'Oca': 5, 'Oac': 31, 'Eac': 1, 'Ica': 8, 'Iac': 47}, 'IA2': {'Aca': 0, 'NVC': 10, 'Eca': 0, 'Aac': 4, 'Oca': 5, 'Oac': 72, 'Eac': 6, 'Ica': 1, 'Iac': 25}, 'EI1': {'Aca': 33, 'NVC': 36, 'Eca': 10, 'Aac': 2, 'Oca': 29, 'Oac': 2, 'Eac': 0, 'Ica': 11, 'Iac': 10}, 'IO4': {'Aca': 0, 'NVC': 50, 'Eca': 0, 'Aac': 2, 'Oca': 13, 'Oac': 9, 'Eac': 0, 'Ica': 42, 'Iac': 11}, 'II1': {'Aca': 1, 'NVC': 41, 'Eca': 1, 'Aac': 1, 'Oca': 7, 'Oac': 13, 'Eac': 0, 'Ica': 10, 'Iac': 50}, 'OA1': {'Aca': 4, 'NVC': 19, 'Eca': 4, 'Aac': 2, 'Oca': 19, 'Oac': 7, 'Eac': 1, 'Ica': 41, 'Iac': 29}, 'II3': {'Aca': 4, 'NVC': 62, 'Eca': 1, 'Aac': 0, 'Oca': 5, 'Oac': 18, 'Eac': 0, 'Ica': 5, 'Iac': 31}, 'II2': {'Aca': 1, 'NVC': 37, 'Eca': 1, 'Aac': 1, 'Oca': 10, 'Oac': 44, 'Eac': 1, 'Ica': 2, 'Iac': 25}, 'EE4': {'Aca': 16, 'NVC': 85, 'Eca': 11, 'Aac': 0, 'Oca': 4, 'Oac': 4, 'Eac': 0, 'Ica': 5, 'Iac': 3}, 'IO3': {'Aca': 2, 'NVC': 59, 'Eca': 0, 'Aac': 0, 'Oca': 18, 'Oac': 6, 'Eac': 0, 'Ica': 24, 'Iac': 14}, 'EI3': {'Aca': 25, 'NVC': 28, 'Eca': 13, 'Aac': 0, 'Oca': 38, 'Oac': 4, 'Eac': 0, 'Ica': 14, 'Iac': 4}, 'IO1': {'Aca': 3, 'NVC': 44, 'Eca': 1, 'Aac': 0, 'Oca': 13, 'Oac': 6, 'Eac': 1, 'Ica': 45, 'Iac': 12}, 'EI2': {'Aca': 5, 'NVC': 23, 'Eca': 21, 'Aac': 1, 'Oca': 44, 'Oac': 14, 'Eac': 3, 'Ica': 11, 'Iac': 3}, 'OA3': {'Aca': 6, 'NVC': 25, 'Eca': 3, 'Aac': 1, 'Oca': 18, 'Oac': 16, 'Eac': 0, 'Ica': 42, 'Iac': 17}, 'AO4': {'Aca': 2, 'NVC': 11, 'Eca': 0, 'Aac': 1, 'Oca': 17, 'Oac': 17, 'Eac': 0, 'Ica': 71, 'Iac': 5}, 'AO3': {'Aca': 2, 'NVC': 31, 'Eca': 1, 'Aac': 1, 'Oca': 47, 'Oac': 13, 'Eac': 1, 'Ica': 23, 'Iac': 15}, 'AO2': {'Aca': 4, 'NVC': 20, 'Eca': 3, 'Aac': 0, 'Oca': 52, 'Oac': 16, 'Eac': 2, 'Ica': 16, 'Iac': 11}, 'AO1': {'Aca': 1, 'NVC': 14, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 7, 'Eac': 2, 'Ica': 83, 'Iac': 4}, 'EA1': {'Aca': 63, 'NVC': 21, 'Eca': 22, 'Aac': 5, 'Oca': 6, 'Oac': 3, 'Eac': 1, 'Ica': 5, 'Iac': 4}, 'EA3': {'Aca': 58, 'NVC': 10, 'Eca': 32, 'Aac': 1, 'Oca': 5, 'Oac': 0, 'Eac': 0, 'Ica': 6, 'Iac': 7}, 'EA2': {'Aca': 21, 'NVC': 12, 'Eca': 80, 'Aac': 1, 'Oca': 7, 'Oac': 4, 'Eac': 1, 'Ica': 5, 'Iac': 0}, 'EA4': {'Aca': 28, 'NVC': 29, 'Eca': 40, 'Aac': 1, 'Oca': 14, 'Oac': 4, 'Eac': 1, 'Ica': 3, 'Iac': 3}, 'EI4': {'Aca': 12, 'NVC': 41, 'Eca': 9, 'Aac': 0, 'Oca': 34, 'Oac': 10, 'Eac': 0, 'Ica': 11, 'Iac': 8}, 'AE1': {'Aca': 82, 'NVC': 7, 'Eca': 21, 'Aac': 0, 'Oca': 1, 'Oac': 1, 'Eac': 1, 'Ica': 5, 'Iac': 5}, 'AE3': {'Aca': 49, 'NVC': 14, 'Eca': 43, 'Aac': 0, 'Oca': 5, 'Oac': 4, 'Eac': 3, 'Ica': 6, 'Iac': 2}, 'AE2': {'Aca': 26, 'NVC': 25, 'Eca': 49, 'Aac': 0, 'Oca': 6, 'Oac': 1, 'Eac': 1, 'Ica': 13, 'Iac': 1}, 'AE4': {'Aca': 40, 'NVC': 26, 'Eca': 16, 'Aac': 2, 'Oca': 6, 'Oac': 4, 'Eac': 0, 'Ica': 22, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 7, 'Eca': 0, 'Aac': 2, 'Oca': 4, 'Oac': 34, 'Eac': 3, 'Ica': 8, 'Iac': 68}, 'AI1': {'Aca': 1, 'NVC': 13, 'Eca': 0, 'Aac': 2, 'Oca': 6, 'Oac': 18, 'Eac': 2, 'Ica': 6, 'Iac': 75}, 'AI3': {'Aca': 3, 'NVC': 36, 'Eca': 2, 'Aac': 3, 'Oca': 5, 'Oac': 47, 'Eac': 0, 'Ica': 5, 'Iac': 26}, 'AI2': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 80, 'Eac': 3, 'Ica': 6, 'Iac': 23}, 'EO3': {'Aca': 7, 'NVC': 49, 'Eca': 9, 'Aac': 1, 'Oca': 27, 'Oac': 10, 'Eac': 0, 'Ica': 10, 'Iac': 10}, 'AA4': {'Aca': 1, 'NVC': 26, 'Eca': 0, 'Aac': 51, 'Oca': 1, 'Oac': 15, 'Eac': 12, 'Ica': 2, 'Iac': 20}, 'EO1': {'Aca': 17, 'NVC': 53, 'Eca': 5, 'Aac': 0, 'Oca': 17, 'Oac': 5, 'Eac': 0, 'Ica': 13, 'Iac': 12}, 'OA4': {'Aca': 3, 'NVC': 12, 'Eca': 3, 'Aac': 3, 'Oca': 64, 'Oac': 7, 'Eac': 1, 'Ica': 15, 'Iac': 13}, 'AA1': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 85, 'Oca': 3, 'Oac': 5, 'Eac': 10, 'Ica': 3, 'Iac': 8}, 'OA2': {'Aca': 1, 'NVC': 17, 'Eca': 2, 'Aac': 0, 'Oca': 73, 'Oac': 12, 'Eac': 1, 'Ica': 11, 'Iac': 10}, 'AA3': {'Aca': 2, 'NVC': 57, 'Eca': 1, 'Aac': 38, 'Oca': 1, 'Oac': 3, 'Eac': 15, 'Ica': 3, 'Iac': 8}, 'AA2': {'Aca': 0, 'NVC': 5, 'Eca': 2, 'Aac': 26, 'Oca': 2, 'Oac': 4, 'Eac': 74, 'Ica': 1, 'Iac': 6}}, {'II4': {'Aca': 3, 'NVC': 58, 'Eca': 1, 'Aac': 0, 'Oca': 5, 'Oac': 20, 'Eac': 1, 'Ica': 6, 'Iac': 31}, 'OE3': {'Aca': 8, 'NVC': 42, 'Eca': 9, 'Aac': 1, 'Oca': 14, 'Oac': 5, 'Eac': 0, 'Ica': 32, 'Iac': 17}, 'EE1': {'Aca': 31, 'NVC': 50, 'Eca': 13, 'Aac': 1, 'Oca': 4, 'Oac': 4, 'Eac': 4, 'Ica': 5, 'Iac': 7}, 'OE1': {'Aca': 4, 'NVC': 37, 'Eca': 13, 'Aac': 0, 'Oca': 11, 'Oac': 7, 'Eac': 1, 'Ica': 31, 'Iac': 19}, 'OE4': {'Aca': 12, 'NVC': 49, 'Eca': 13, 'Aac': 1, 'Oca': 8, 'Oac': 10, 'Eac': 2, 'Ica': 21, 'Iac': 11}, 'OO4': {'Aca': 2, 'NVC': 75, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 9, 'Eac': 0, 'Ica': 13, 'Iac': 12}, 'OO1': {'Aca': 1, 'NVC': 44, 'Eca': 1, 'Aac': 1, 'Oca': 17, 'Oac': 5, 'Eac': 0, 'Ica': 41, 'Iac': 13}, 'EE3': {'Aca': 14, 'NVC': 81, 'Eca': 11, 'Aac': 1, 'Oca': 5, 'Oac': 1, 'Eac': 1, 'Ica': 4, 'Iac': 7}, 'OO3': {'Aca': 2, 'NVC': 76, 'Eca': 1, 'Aac': 2, 'Oca': 9, 'Oac': 9, 'Eac': 1, 'Ica': 16, 'Iac': 14}, 'OO2': {'Aca': 1, 'NVC': 53, 'Eca': 0, 'Aac': 0, 'Oca': 40, 'Oac': 12, 'Eac': 0, 'Ica': 19, 'Iac': 8}, 'EE2': {'Aca': 18, 'NVC': 52, 'Eca': 26, 'Aac': 1, 'Oca': 5, 'Oac': 8, 'Eac': 3, 'Ica': 5, 'Iac': 9}, 'OI3': {'Aca': 2, 'NVC': 52, 'Eca': 2, 'Aac': 0, 'Oca': 17, 'Oac': 12, 'Eac': 0, 'Ica': 16, 'Iac': 17}, 'OI2': {'Aca': 5, 'NVC': 34, 'Eca': 1, 'Aac': 0, 'Oca': 54, 'Oac': 12, 'Eac': 0, 'Ica': 14, 'Iac': 7}, 'OI1': {'Aca': 1, 'NVC': 45, 'Eca': 1, 'Aac': 3, 'Oca': 20, 'Oac': 8, 'Eac': 1, 'Ica': 25, 'Iac': 23}, 'OI4': {'Aca': 4, 'NVC': 60, 'Eca': 1, 'Aac': 0, 'Oca': 22, 'Oac': 5, 'Eac': 0, 'Ica': 11, 'Iac': 18}, 'EO2': {'Aca': 7, 'NVC': 44, 'Eca': 3, 'Aac': 3, 'Oca': 32, 'Oac': 24, 'Eac': 2, 'Ica': 7, 'Iac': 6}, 'IE1': {'Aca': 20, 'NVC': 27, 'Eca': 7, 'Aac': 1, 'Oca': 12, 'Oac': 4, 'Eac': 1, 'Ica': 43, 'Iac': 12}, 'IE3': {'Aca': 16, 'NVC': 22, 'Eca': 21, 'Aac': 0, 'Oca': 9, 'Oac': 9, 'Eac': 1, 'Ica': 37, 'Iac': 6}, 'IE2': {'Aca': 10, 'NVC': 36, 'Eca': 30, 'Aac': 0, 'Oca': 15, 'Oac': 12, 'Eac': 1, 'Ica': 16, 'Iac': 5}, 'IE4': {'Aca': 16, 'NVC': 33, 'Eca': 14, 'Aac': 0, 'Oca': 11, 'Oac': 4, 'Eac': 2, 'Ica': 34, 'Iac': 8}, 'IO2': {'Aca': 3, 'NVC': 48, 'Eca': 0, 'Aac': 0, 'Oca': 32, 'Oac': 12, 'Eac': 1, 'Ica': 20, 'Iac': 13}, 'OE2': {'Aca': 7, 'NVC': 54, 'Eca': 18, 'Aac': 1, 'Oca': 14, 'Oac': 13, 'Eac': 4, 'Ica': 13, 'Iac': 4}, 'IA4': {'Aca': 1, 'NVC': 8, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 54, 'Eac': 4, 'Ica': 6, 'Iac': 49}, 'EO4': {'Aca': 8, 'NVC': 50, 'Eca': 7, 'Aac': 2, 'Oca': 22, 'Oac': 6, 'Eac': 0, 'Ica': 21, 'Iac': 8}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 3, 'Oca': 4, 'Oac': 20, 'Eac': 1, 'Ica': 8, 'Iac': 89}, 'IA3': {'Aca': 2, 'NVC': 29, 'Eca': 2, 'Aac': 1, 'Oca': 6, 'Oac': 26, 'Eac': 1, 'Ica': 9, 'Iac': 48}, 'IA2': {'Aca': 0, 'NVC': 11, 'Eca': 0, 'Aac': 4, 'Oca': 3, 'Oac': 72, 'Eac': 4, 'Ica': 3, 'Iac': 27}, 'EI1': {'Aca': 30, 'NVC': 34, 'Eca': 9, 'Aac': 2, 'Oca': 27, 'Oac': 1, 'Eac': 0, 'Ica': 9, 'Iac': 11}, 'IO4': {'Aca': 0, 'NVC': 50, 'Eca': 0, 'Aac': 2, 'Oca': 12, 'Oac': 8, 'Eac': 0, 'Ica': 39, 'Iac': 11}, 'II1': {'Aca': 1, 'NVC': 40, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 13, 'Eac': 0, 'Ica': 10, 'Iac': 56}, 'OA1': {'Aca': 2, 'NVC': 19, 'Eca': 4, 'Aac': 2, 'Oca': 21, 'Oac': 7, 'Eac': 1, 'Ica': 42, 'Iac': 30}, 'II3': {'Aca': 4, 'NVC': 61, 'Eca': 0, 'Aac': 1, 'Oca': 6, 'Oac': 18, 'Eac': 0, 'Ica': 6, 'Iac': 28}, 'II2': {'Aca': 1, 'NVC': 36, 'Eca': 2, 'Aac': 1, 'Oca': 11, 'Oac': 42, 'Eac': 1, 'Ica': 2, 'Iac': 22}, 'EE4': {'Aca': 17, 'NVC': 76, 'Eca': 11, 'Aac': 0, 'Oca': 4, 'Oac': 5, 'Eac': 0, 'Ica': 5, 'Iac': 4}, 'IO3': {'Aca': 2, 'NVC': 57, 'Eca': 2, 'Aac': 0, 'Oca': 16, 'Oac': 5, 'Eac': 0, 'Ica': 24, 'Iac': 16}, 'EI3': {'Aca': 24, 'NVC': 29, 'Eca': 13, 'Aac': 0, 'Oca': 34, 'Oac': 4, 'Eac': 0, 'Ica': 13, 'Iac': 4}, 'IO1': {'Aca': 3, 'NVC': 39, 'Eca': 0, 'Aac': 0, 'Oca': 16, 'Oac': 7, 'Eac': 1, 'Ica': 48, 'Iac': 10}, 'EI2': {'Aca': 5, 'NVC': 23, 'Eca': 19, 'Aac': 1, 'Oca': 51, 'Oac': 12, 'Eac': 3, 'Ica': 11, 'Iac': 2}, 'OA3': {'Aca': 5, 'NVC': 22, 'Eca': 4, 'Aac': 0, 'Oca': 19, 'Oac': 13, 'Eac': 0, 'Ica': 41, 'Iac': 19}, 'AO4': {'Aca': 3, 'NVC': 10, 'Eca': 0, 'Aac': 1, 'Oca': 15, 'Oac': 16, 'Eac': 0, 'Ica': 71, 'Iac': 7}, 'AO3': {'Aca': 2, 'NVC': 24, 'Eca': 1, 'Aac': 1, 'Oca': 44, 'Oac': 12, 'Eac': 1, 'Ica': 23, 'Iac': 13}, 'AO2': {'Aca': 4, 'NVC': 21, 'Eca': 3, 'Aac': 0, 'Oca': 47, 'Oac': 17, 'Eac': 1, 'Ica': 19, 'Iac': 13}, 'AO1': {'Aca': 1, 'NVC': 14, 'Eca': 1, 'Aac': 0, 'Oca': 15, 'Oac': 9, 'Eac': 2, 'Ica': 79, 'Iac': 5}, 'EA1': {'Aca': 61, 'NVC': 25, 'Eca': 21, 'Aac': 4, 'Oca': 5, 'Oac': 1, 'Eac': 1, 'Ica': 5, 'Iac': 3}, 'EA3': {'Aca': 65, 'NVC': 8, 'Eca': 33, 'Aac': 1, 'Oca': 4, 'Oac': 1, 'Eac': 0, 'Ica': 6, 'Iac': 7}, 'EA2': {'Aca': 19, 'NVC': 11, 'Eca': 77, 'Aac': 1, 'Oca': 5, 'Oac': 4, 'Eac': 1, 'Ica': 4, 'Iac': 1}, 'EA4': {'Aca': 29, 'NVC': 29, 'Eca': 43, 'Aac': 1, 'Oca': 14, 'Oac': 6, 'Eac': 1, 'Ica': 2, 'Iac': 3}, 'EI4': {'Aca': 14, 'NVC': 38, 'Eca': 10, 'Aac': 0, 'Oca': 31, 'Oac': 7, 'Eac': 0, 'Ica': 11, 'Iac': 7}, 'AE1': {'Aca': 82, 'NVC': 7, 'Eca': 23, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 1, 'Ica': 7, 'Iac': 4}, 'AE3': {'Aca': 54, 'NVC': 11, 'Eca': 47, 'Aac': 0, 'Oca': 4, 'Oac': 4, 'Eac': 3, 'Ica': 6, 'Iac': 2}, 'AE2': {'Aca': 26, 'NVC': 28, 'Eca': 55, 'Aac': 0, 'Oca': 7, 'Oac': 1, 'Eac': 0, 'Ica': 12, 'Iac': 1}, 'AE4': {'Aca': 44, 'NVC': 28, 'Eca': 18, 'Aac': 2, 'Oca': 6, 'Oac': 4, 'Eac': 0, 'Ica': 23, 'Iac': 2}, 'AI4': {'Aca': 0, 'NVC': 7, 'Eca': 0, 'Aac': 2, 'Oca': 4, 'Oac': 28, 'Eac': 4, 'Ica': 8, 'Iac': 66}, 'AI1': {'Aca': 1, 'NVC': 14, 'Eca': 0, 'Aac': 1, 'Oca': 6, 'Oac': 20, 'Eac': 2, 'Ica': 7, 'Iac': 74}, 'AI3': {'Aca': 4, 'NVC': 36, 'Eca': 2, 'Aac': 3, 'Oca': 5, 'Oac': 48, 'Eac': 0, 'Ica': 4, 'Iac': 25}, 'AI2': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 74, 'Eac': 3, 'Ica': 6, 'Iac': 26}, 'EO3': {'Aca': 6, 'NVC': 51, 'Eca': 8, 'Aac': 1, 'Oca': 28, 'Oac': 10, 'Eac': 0, 'Ica': 13, 'Iac': 9}, 'AA4': {'Aca': 1, 'NVC': 24, 'Eca': 0, 'Aac': 49, 'Oca': 1, 'Oac': 15, 'Eac': 13, 'Ica': 3, 'Iac': 21}, 'EO1': {'Aca': 15, 'NVC': 59, 'Eca': 5, 'Aac': 0, 'Oca': 20, 'Oac': 6, 'Eac': 0, 'Ica': 12, 'Iac': 13}, 'OA4': {'Aca': 3, 'NVC': 12, 'Eca': 2, 'Aac': 3, 'Oca': 67, 'Oac': 9, 'Eac': 0, 'Ica': 17, 'Iac': 14}, 'AA1': {'Aca': 0, 'NVC': 7, 'Eca': 0, 'Aac': 88, 'Oca': 3, 'Oac': 4, 'Eac': 13, 'Ica': 3, 'Iac': 10}, 'OA2': {'Aca': 1, 'NVC': 18, 'Eca': 2, 'Aac': 0, 'Oca': 74, 'Oac': 14, 'Eac': 1, 'Ica': 10, 'Iac': 10}, 'AA3': {'Aca': 2, 'NVC': 56, 'Eca': 1, 'Aac': 38, 'Oca': 1, 'Oac': 4, 'Eac': 14, 'Ica': 3, 'Iac': 8}, 'AA2': {'Aca': 0, 'NVC': 5, 'Eca': 2, 'Aac': 29, 'Oca': 2, 'Oac': 6, 'Eac': 67, 'Ica': 1, 'Iac': 8}}, {'II4': {'Aca': 3, 'NVC': 59, 'Eca': 1, 'Aac': 0, 'Oca': 5, 'Oac': 19, 'Eac': 1, 'Ica': 7, 'Iac': 31}, 'OE3': {'Aca': 9, 'NVC': 39, 'Eca': 6, 'Aac': 1, 'Oca': 13, 'Oac': 6, 'Eac': 0, 'Ica': 32, 'Iac': 16}, 'EE1': {'Aca': 31, 'NVC': 54, 'Eca': 16, 'Aac': 1, 'Oca': 3, 'Oac': 3, 'Eac': 3, 'Ica': 4, 'Iac': 7}, 'OE1': {'Aca': 6, 'NVC': 36, 'Eca': 12, 'Aac': 0, 'Oca': 13, 'Oac': 6, 'Eac': 1, 'Ica': 32, 'Iac': 18}, 'OE4': {'Aca': 11, 'NVC': 52, 'Eca': 13, 'Aac': 1, 'Oca': 10, 'Oac': 7, 'Eac': 2, 'Ica': 17, 'Iac': 10}, 'OO4': {'Aca': 1, 'NVC': 79, 'Eca': 1, 'Aac': 0, 'Oca': 14, 'Oac': 8, 'Eac': 0, 'Ica': 12, 'Iac': 12}, 'OO1': {'Aca': 1, 'NVC': 49, 'Eca': 1, 'Aac': 1, 'Oca': 17, 'Oac': 5, 'Eac': 0, 'Ica': 39, 'Iac': 13}, 'EE3': {'Aca': 11, 'NVC': 81, 'Eca': 11, 'Aac': 1, 'Oca': 5, 'Oac': 2, 'Eac': 2, 'Ica': 4, 'Iac': 6}, 'OO3': {'Aca': 1, 'NVC': 71, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 9, 'Eac': 1, 'Ica': 14, 'Iac': 14}, 'OO2': {'Aca': 0, 'NVC': 50, 'Eca': 0, 'Aac': 0, 'Oca': 37, 'Oac': 12, 'Eac': 0, 'Ica': 18, 'Iac': 9}, 'EE2': {'Aca': 18, 'NVC': 52, 'Eca': 28, 'Aac': 1, 'Oca': 5, 'Oac': 8, 'Eac': 2, 'Ica': 5, 'Iac': 10}, 'OI3': {'Aca': 3, 'NVC': 60, 'Eca': 2, 'Aac': 1, 'Oca': 17, 'Oac': 11, 'Eac': 0, 'Ica': 16, 'Iac': 18}, 'OI2': {'Aca': 5, 'NVC': 32, 'Eca': 1, 'Aac': 0, 'Oca': 51, 'Oac': 12, 'Eac': 0, 'Ica': 15, 'Iac': 7}, 'OI1': {'Aca': 1, 'NVC': 40, 'Eca': 1, 'Aac': 2, 'Oca': 18, 'Oac': 6, 'Eac': 1, 'Ica': 24, 'Iac': 24}, 'OI4': {'Aca': 4, 'NVC': 58, 'Eca': 2, 'Aac': 0, 'Oca': 27, 'Oac': 5, 'Eac': 0, 'Ica': 12, 'Iac': 18}, 'EO2': {'Aca': 7, 'NVC': 41, 'Eca': 3, 'Aac': 3, 'Oca': 28, 'Oac': 23, 'Eac': 2, 'Ica': 7, 'Iac': 8}, 'IE1': {'Aca': 21, 'NVC': 26, 'Eca': 5, 'Aac': 0, 'Oca': 14, 'Oac': 3, 'Eac': 1, 'Ica': 41, 'Iac': 10}, 'IE3': {'Aca': 14, 'NVC': 20, 'Eca': 21, 'Aac': 0, 'Oca': 10, 'Oac': 9, 'Eac': 1, 'Ica': 36, 'Iac': 6}, 'IE2': {'Aca': 10, 'NVC': 31, 'Eca': 34, 'Aac': 0, 'Oca': 14, 'Oac': 10, 'Eac': 1, 'Ica': 16, 'Iac': 5}, 'IE4': {'Aca': 17, 'NVC': 35, 'Eca': 15, 'Aac': 0, 'Oca': 11, 'Oac': 5, 'Eac': 2, 'Ica': 34, 'Iac': 9}, 'IO2': {'Aca': 4, 'NVC': 41, 'Eca': 0, 'Aac': 0, 'Oca': 32, 'Oac': 11, 'Eac': 2, 'Ica': 18, 'Iac': 15}, 'OE2': {'Aca': 7, 'NVC': 50, 'Eca': 14, 'Aac': 1, 'Oca': 15, 'Oac': 12, 'Eac': 4, 'Ica': 15, 'Iac': 4}, 'IA4': {'Aca': 2, 'NVC': 9, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 55, 'Eac': 4, 'Ica': 6, 'Iac': 43}, 'EO4': {'Aca': 9, 'NVC': 51, 'Eca': 7, 'Aac': 2, 'Oca': 23, 'Oac': 6, 'Eac': 0, 'Ica': 19, 'Iac': 10}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 3, 'Oca': 4, 'Oac': 21, 'Eac': 1, 'Ica': 6, 'Iac': 91}, 'IA3': {'Aca': 2, 'NVC': 23, 'Eca': 3, 'Aac': 1, 'Oca': 5, 'Oac': 27, 'Eac': 1, 'Ica': 10, 'Iac': 48}, 'IA2': {'Aca': 0, 'NVC': 10, 'Eca': 0, 'Aac': 4, 'Oca': 4, 'Oac': 74, 'Eac': 6, 'Ica': 2, 'Iac': 27}, 'EI1': {'Aca': 32, 'NVC': 36, 'Eca': 9, 'Aac': 2, 'Oca': 26, 'Oac': 2, 'Eac': 0, 'Ica': 10, 'Iac': 11}, 'IO4': {'Aca': 0, 'NVC': 49, 'Eca': 0, 'Aac': 2, 'Oca': 11, 'Oac': 10, 'Eac': 0, 'Ica': 43, 'Iac': 12}, 'II1': {'Aca': 1, 'NVC': 39, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 11, 'Eac': 0, 'Ica': 10, 'Iac': 52}, 'OA1': {'Aca': 4, 'NVC': 20, 'Eca': 3, 'Aac': 2, 'Oca': 21, 'Oac': 8, 'Eac': 1, 'Ica': 42, 'Iac': 29}, 'II3': {'Aca': 3, 'NVC': 62, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 15, 'Eac': 0, 'Ica': 6, 'Iac': 27}, 'II2': {'Aca': 1, 'NVC': 33, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 46, 'Eac': 1, 'Ica': 2, 'Iac': 27}, 'EE4': {'Aca': 16, 'NVC': 76, 'Eca': 12, 'Aac': 0, 'Oca': 4, 'Oac': 4, 'Eac': 0, 'Ica': 4, 'Iac': 6}, 'IO3': {'Aca': 2, 'NVC': 59, 'Eca': 2, 'Aac': 0, 'Oca': 20, 'Oac': 3, 'Eac': 0, 'Ica': 26, 'Iac': 10}, 'EI3': {'Aca': 23, 'NVC': 27, 'Eca': 15, 'Aac': 0, 'Oca': 36, 'Oac': 5, 'Eac': 0, 'Ica': 13, 'Iac': 5}, 'IO1': {'Aca': 3, 'NVC': 37, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 7, 'Eac': 1, 'Ica': 46, 'Iac': 11}, 'EI2': {'Aca': 6, 'NVC': 18, 'Eca': 17, 'Aac': 1, 'Oca': 46, 'Oac': 12, 'Eac': 3, 'Ica': 10, 'Iac': 3}, 'OA3': {'Aca': 5, 'NVC': 23, 'Eca': 4, 'Aac': 1, 'Oca': 17, 'Oac': 14, 'Eac': 0, 'Ica': 43, 'Iac': 19}, 'AO4': {'Aca': 3, 'NVC': 11, 'Eca': 0, 'Aac': 1, 'Oca': 14, 'Oac': 15, 'Eac': 0, 'Ica': 75, 'Iac': 7}, 'AO3': {'Aca': 2, 'NVC': 31, 'Eca': 1, 'Aac': 1, 'Oca': 48, 'Oac': 12, 'Eac': 1, 'Ica': 20, 'Iac': 14}, 'AO2': {'Aca': 4, 'NVC': 20, 'Eca': 3, 'Aac': 0, 'Oca': 50, 'Oac': 16, 'Eac': 2, 'Ica': 17, 'Iac': 12}, 'AO1': {'Aca': 0, 'NVC': 13, 'Eca': 1, 'Aac': 0, 'Oca': 17, 'Oac': 10, 'Eac': 2, 'Ica': 77, 'Iac': 6}, 'EA1': {'Aca': 52, 'NVC': 23, 'Eca': 20, 'Aac': 5, 'Oca': 6, 'Oac': 3, 'Eac': 1, 'Ica': 6, 'Iac': 3}, 'EA3': {'Aca': 66, 'NVC': 9, 'Eca': 34, 'Aac': 1, 'Oca': 5, 'Oac': 1, 'Eac': 0, 'Ica': 5, 'Iac': 6}, 'EA2': {'Aca': 17, 'NVC': 11, 'Eca': 83, 'Aac': 0, 'Oca': 5, 'Oac': 3, 'Eac': 1, 'Ica': 5, 'Iac': 1}, 'EA4': {'Aca': 33, 'NVC': 26, 'Eca': 37, 'Aac': 1, 'Oca': 13, 'Oac': 6, 'Eac': 1, 'Ica': 3, 'Iac': 3}, 'EI4': {'Aca': 14, 'NVC': 39, 'Eca': 8, 'Aac': 0, 'Oca': 33, 'Oac': 9, 'Eac': 0, 'Ica': 10, 'Iac': 9}, 'AE1': {'Aca': 83, 'NVC': 5, 'Eca': 22, 'Aac': 0, 'Oca': 0, 'Oac': 2, 'Eac': 1, 'Ica': 6, 'Iac': 5}, 'AE3': {'Aca': 49, 'NVC': 12, 'Eca': 45, 'Aac': 0, 'Oca': 4, 'Oac': 4, 'Eac': 3, 'Ica': 6, 'Iac': 2}, 'AE2': {'Aca': 26, 'NVC': 24, 'Eca': 51, 'Aac': 0, 'Oca': 7, 'Oac': 1, 'Eac': 1, 'Ica': 10, 'Iac': 1}, 'AE4': {'Aca': 44, 'NVC': 29, 'Eca': 18, 'Aac': 1, 'Oca': 7, 'Oac': 4, 'Eac': 0, 'Ica': 24, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 9, 'Eca': 0, 'Aac': 1, 'Oca': 3, 'Oac': 37, 'Eac': 4, 'Ica': 7, 'Iac': 66}, 'AI1': {'Aca': 1, 'NVC': 12, 'Eca': 0, 'Aac': 2, 'Oca': 7, 'Oac': 19, 'Eac': 2, 'Ica': 6, 'Iac': 81}, 'AI3': {'Aca': 4, 'NVC': 37, 'Eca': 2, 'Aac': 2, 'Oca': 5, 'Oac': 47, 'Eac': 0, 'Ica': 6, 'Iac': 23}, 'AI2': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 7, 'Oac': 79, 'Eac': 4, 'Ica': 6, 'Iac': 24}, 'EO3': {'Aca': 5, 'NVC': 56, 'Eca': 7, 'Aac': 1, 'Oca': 25, 'Oac': 11, 'Eac': 0, 'Ica': 11, 'Iac': 8}, 'AA4': {'Aca': 1, 'NVC': 24, 'Eca': 0, 'Aac': 43, 'Oca': 1, 'Oac': 14, 'Eac': 12, 'Ica': 3, 'Iac': 21}, 'EO1': {'Aca': 18, 'NVC': 56, 'Eca': 4, 'Aac': 0, 'Oca': 18, 'Oac': 4, 'Eac': 0, 'Ica': 13, 'Iac': 11}, 'OA4': {'Aca': 3, 'NVC': 11, 'Eca': 2, 'Aac': 4, 'Oca': 62, 'Oac': 8, 'Eac': 1, 'Ica': 15, 'Iac': 15}, 'AA1': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 87, 'Oca': 2, 'Oac': 5, 'Eac': 11, 'Ica': 3, 'Iac': 11}, 'OA2': {'Aca': 1, 'NVC': 17, 'Eca': 2, 'Aac': 0, 'Oca': 68, 'Oac': 13, 'Eac': 1, 'Ica': 9, 'Iac': 8}, 'AA3': {'Aca': 2, 'NVC': 52, 'Eca': 1, 'Aac': 35, 'Oca': 1, 'Oac': 5, 'Eac': 15, 'Ica': 2, 'Iac': 8}, 'AA2': {'Aca': 0, 'NVC': 6, 'Eca': 2, 'Aac': 28, 'Oca': 2, 'Oac': 6, 'Eac': 70, 'Ica': 1, 'Iac': 5}}, {'II4': {'Aca': 2, 'NVC': 61, 'Eca': 1, 'Aac': 0, 'Oca': 6, 'Oac': 18, 'Eac': 1, 'Ica': 5, 'Iac': 28}, 'OE3': {'Aca': 9, 'NVC': 39, 'Eca': 9, 'Aac': 1, 'Oca': 12, 'Oac': 7, 'Eac': 0, 'Ica': 31, 'Iac': 16}, 'EE1': {'Aca': 32, 'NVC': 53, 'Eca': 15, 'Aac': 1, 'Oca': 3, 'Oac': 5, 'Eac': 3, 'Ica': 5, 'Iac': 9}, 'OE1': {'Aca': 4, 'NVC': 38, 'Eca': 11, 'Aac': 0, 'Oca': 12, 'Oac': 5, 'Eac': 1, 'Ica': 31, 'Iac': 20}, 'OE4': {'Aca': 12, 'NVC': 46, 'Eca': 13, 'Aac': 1, 'Oca': 9, 'Oac': 9, 'Eac': 2, 'Ica': 20, 'Iac': 10}, 'OO4': {'Aca': 2, 'NVC': 70, 'Eca': 2, 'Aac': 0, 'Oca': 14, 'Oac': 8, 'Eac': 0, 'Ica': 12, 'Iac': 13}, 'OO1': {'Aca': 1, 'NVC': 50, 'Eca': 1, 'Aac': 1, 'Oca': 17, 'Oac': 4, 'Eac': 0, 'Ica': 40, 'Iac': 14}, 'EE3': {'Aca': 12, 'NVC': 82, 'Eca': 11, 'Aac': 1, 'Oca': 5, 'Oac': 2, 'Eac': 2, 'Ica': 3, 'Iac': 7}, 'OO3': {'Aca': 2, 'NVC': 74, 'Eca': 0, 'Aac': 2, 'Oca': 7, 'Oac': 8, 'Eac': 1, 'Ica': 14, 'Iac': 13}, 'OO2': {'Aca': 1, 'NVC': 51, 'Eca': 0, 'Aac': 0, 'Oca': 37, 'Oac': 12, 'Eac': 0, 'Ica': 17, 'Iac': 6}, 'EE2': {'Aca': 16, 'NVC': 57, 'Eca': 27, 'Aac': 1, 'Oca': 4, 'Oac': 6, 'Eac': 3, 'Ica': 4, 'Iac': 9}, 'OI3': {'Aca': 3, 'NVC': 53, 'Eca': 2, 'Aac': 1, 'Oca': 20, 'Oac': 11, 'Eac': 0, 'Ica': 13, 'Iac': 16}, 'OI2': {'Aca': 5, 'NVC': 34, 'Eca': 1, 'Aac': 0, 'Oca': 52, 'Oac': 13, 'Eac': 0, 'Ica': 15, 'Iac': 8}, 'OI1': {'Aca': 1, 'NVC': 42, 'Eca': 1, 'Aac': 2, 'Oca': 21, 'Oac': 9, 'Eac': 1, 'Ica': 28, 'Iac': 24}, 'OI4': {'Aca': 3, 'NVC': 58, 'Eca': 2, 'Aac': 0, 'Oca': 27, 'Oac': 6, 'Eac': 0, 'Ica': 10, 'Iac': 19}, 'EO2': {'Aca': 7, 'NVC': 40, 'Eca': 4, 'Aac': 3, 'Oca': 29, 'Oac': 22, 'Eac': 2, 'Ica': 7, 'Iac': 7}, 'IE1': {'Aca': 19, 'NVC': 27, 'Eca': 7, 'Aac': 1, 'Oca': 14, 'Oac': 3, 'Eac': 1, 'Ica': 43, 'Iac': 12}, 'IE3': {'Aca': 12, 'NVC': 23, 'Eca': 21, 'Aac': 0, 'Oca': 12, 'Oac': 11, 'Eac': 1, 'Ica': 38, 'Iac': 6}, 'IE2': {'Aca': 11, 'NVC': 35, 'Eca': 33, 'Aac': 0, 'Oca': 14, 'Oac': 12, 'Eac': 1, 'Ica': 15, 'Iac': 5}, 'IE4': {'Aca': 18, 'NVC': 31, 'Eca': 15, 'Aac': 0, 'Oca': 10, 'Oac': 5, 'Eac': 2, 'Ica': 33, 'Iac': 7}, 'IO2': {'Aca': 3, 'NVC': 49, 'Eca': 0, 'Aac': 0, 'Oca': 29, 'Oac': 10, 'Eac': 1, 'Ica': 20, 'Iac': 12}, 'OE2': {'Aca': 7, 'NVC': 53, 'Eca': 17, 'Aac': 1, 'Oca': 12, 'Oac': 13, 'Eac': 4, 'Ica': 18, 'Iac': 4}, 'IA4': {'Aca': 1, 'NVC': 9, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 51, 'Eac': 4, 'Ica': 5, 'Iac': 47}, 'EO4': {'Aca': 7, 'NVC': 47, 'Eca': 6, 'Aac': 2, 'Oca': 27, 'Oac': 7, 'Eac': 0, 'Ica': 21, 'Iac': 5}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 3, 'Oca': 3, 'Oac': 20, 'Eac': 1, 'Ica': 8, 'Iac': 88}, 'IA3': {'Aca': 2, 'NVC': 29, 'Eca': 2, 'Aac': 1, 'Oca': 6, 'Oac': 30, 'Eac': 1, 'Ica': 10, 'Iac': 49}, 'IA2': {'Aca': 0, 'NVC': 9, 'Eca': 0, 'Aac': 4, 'Oca': 5, 'Oac': 74, 'Eac': 5, 'Ica': 3, 'Iac': 24}, 'EI1': {'Aca': 32, 'NVC': 35, 'Eca': 9, 'Aac': 2, 'Oca': 29, 'Oac': 2, 'Eac': 0, 'Ica': 8, 'Iac': 11}, 'IO4': {'Aca': 0, 'NVC': 52, 'Eca': 0, 'Aac': 2, 'Oca': 12, 'Oac': 10, 'Eac': 0, 'Ica': 42, 'Iac': 11}, 'II1': {'Aca': 0, 'NVC': 40, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 11, 'Eac': 0, 'Ica': 8, 'Iac': 55}, 'OA1': {'Aca': 4, 'NVC': 20, 'Eca': 4, 'Aac': 2, 'Oca': 17, 'Oac': 8, 'Eac': 1, 'Ica': 43, 'Iac': 30}, 'II3': {'Aca': 4, 'NVC': 60, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 19, 'Eac': 0, 'Ica': 4, 'Iac': 29}, 'II2': {'Aca': 1, 'NVC': 40, 'Eca': 2, 'Aac': 0, 'Oca': 10, 'Oac': 50, 'Eac': 1, 'Ica': 1, 'Iac': 28}, 'EE4': {'Aca': 14, 'NVC': 86, 'Eca': 9, 'Aac': 0, 'Oca': 3, 'Oac': 5, 'Eac': 0, 'Ica': 5, 'Iac': 6}, 'IO3': {'Aca': 2, 'NVC': 62, 'Eca': 2, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 25, 'Iac': 13}, 'EI3': {'Aca': 23, 'NVC': 29, 'Eca': 14, 'Aac': 0, 'Oca': 40, 'Oac': 4, 'Eac': 0, 'Ica': 12, 'Iac': 5}, 'IO1': {'Aca': 2, 'NVC': 43, 'Eca': 1, 'Aac': 0, 'Oca': 15, 'Oac': 5, 'Eac': 1, 'Ica': 42, 'Iac': 13}, 'EI2': {'Aca': 6, 'NVC': 21, 'Eca': 22, 'Aac': 1, 'Oca': 52, 'Oac': 13, 'Eac': 3, 'Ica': 7, 'Iac': 3}, 'OA3': {'Aca': 5, 'NVC': 25, 'Eca': 3, 'Aac': 1, 'Oca': 17, 'Oac': 13, 'Eac': 0, 'Ica': 39, 'Iac': 18}, 'AO4': {'Aca': 3, 'NVC': 11, 'Eca': 0, 'Aac': 0, 'Oca': 15, 'Oac': 14, 'Eac': 0, 'Ica': 74, 'Iac': 6}, 'AO3': {'Aca': 2, 'NVC': 31, 'Eca': 1, 'Aac': 1, 'Oca': 43, 'Oac': 11, 'Eac': 1, 'Ica': 25, 'Iac': 13}, 'AO2': {'Aca': 4, 'NVC': 19, 'Eca': 3, 'Aac': 0, 'Oca': 54, 'Oac': 15, 'Eac': 2, 'Ica': 18, 'Iac': 11}, 'AO1': {'Aca': 1, 'NVC': 14, 'Eca': 1, 'Aac': 0, 'Oca': 18, 'Oac': 8, 'Eac': 2, 'Ica': 71, 'Iac': 6}, 'EA1': {'Aca': 58, 'NVC': 23, 'Eca': 20, 'Aac': 5, 'Oca': 4, 'Oac': 3, 'Eac': 1, 'Ica': 6, 'Iac': 4}, 'EA3': {'Aca': 63, 'NVC': 10, 'Eca': 32, 'Aac': 0, 'Oca': 4, 'Oac': 1, 'Eac': 0, 'Ica': 7, 'Iac': 6}, 'EA2': {'Aca': 20, 'NVC': 12, 'Eca': 77, 'Aac': 1, 'Oca': 7, 'Oac': 3, 'Eac': 1, 'Ica': 5, 'Iac': 1}, 'EA4': {'Aca': 29, 'NVC': 30, 'Eca': 40, 'Aac': 1, 'Oca': 14, 'Oac': 4, 'Eac': 1, 'Ica': 3, 'Iac': 2}, 'EI4': {'Aca': 11, 'NVC': 44, 'Eca': 9, 'Aac': 0, 'Oca': 33, 'Oac': 9, 'Eac': 0, 'Ica': 10, 'Iac': 8}, 'AE1': {'Aca': 77, 'NVC': 8, 'Eca': 21, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 0, 'Ica': 6, 'Iac': 4}, 'AE3': {'Aca': 50, 'NVC': 11, 'Eca': 39, 'Aac': 0, 'Oca': 5, 'Oac': 3, 'Eac': 2, 'Ica': 5, 'Iac': 1}, 'AE2': {'Aca': 26, 'NVC': 28, 'Eca': 52, 'Aac': 0, 'Oca': 5, 'Oac': 1, 'Eac': 1, 'Ica': 13, 'Iac': 0}, 'AE4': {'Aca': 41, 'NVC': 25, 'Eca': 16, 'Aac': 1, 'Oca': 4, 'Oac': 4, 'Eac': 0, 'Ica': 22, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 8, 'Eca': 0, 'Aac': 2, 'Oca': 3, 'Oac': 34, 'Eac': 4, 'Ica': 8, 'Iac': 63}, 'AI1': {'Aca': 1, 'NVC': 11, 'Eca': 0, 'Aac': 2, 'Oca': 7, 'Oac': 20, 'Eac': 2, 'Ica': 7, 'Iac': 73}, 'AI3': {'Aca': 4, 'NVC': 38, 'Eca': 2, 'Aac': 3, 'Oca': 5, 'Oac': 45, 'Eac': 0, 'Ica': 6, 'Iac': 22}, 'AI2': {'Aca': 0, 'NVC': 7, 'Eca': 1, 'Aac': 1, 'Oca': 7, 'Oac': 77, 'Eac': 4, 'Ica': 5, 'Iac': 24}, 'EO3': {'Aca': 7, 'NVC': 54, 'Eca': 9, 'Aac': 1, 'Oca': 23, 'Oac': 6, 'Eac': 0, 'Ica': 13, 'Iac': 10}, 'AA4': {'Aca': 1, 'NVC': 23, 'Eca': 0, 'Aac': 49, 'Oca': 1, 'Oac': 12, 'Eac': 11, 'Ica': 2, 'Iac': 20}, 'EO1': {'Aca': 17, 'NVC': 57, 'Eca': 5, 'Aac': 0, 'Oca': 18, 'Oac': 5, 'Eac': 0, 'Ica': 12, 'Iac': 12}, 'OA4': {'Aca': 2, 'NVC': 13, 'Eca': 3, 'Aac': 4, 'Oca': 68, 'Oac': 9, 'Eac': 1, 'Ica': 17, 'Iac': 14}, 'AA1': {'Aca': 0, 'NVC': 5, 'Eca': 1, 'Aac': 82, 'Oca': 3, 'Oac': 5, 'Eac': 13, 'Ica': 2, 'Iac': 10}, 'OA2': {'Aca': 1, 'NVC': 16, 'Eca': 2, 'Aac': 0, 'Oca': 67, 'Oac': 11, 'Eac': 1, 'Ica': 12, 'Iac': 10}, 'AA3': {'Aca': 2, 'NVC': 56, 'Eca': 1, 'Aac': 37, 'Oca': 0, 'Oac': 5, 'Eac': 13, 'Ica': 3, 'Iac': 9}, 'AA2': {'Aca': 0, 'NVC': 5, 'Eca': 2, 'Aac': 32, 'Oca': 2, 'Oac': 6, 'Eac': 75, 'Ica': 1, 'Iac': 8}}, {'II4': {'Aca': 2, 'NVC': 58, 'Eca': 1, 'Aac': 0, 'Oca': 6, 'Oac': 18, 'Eac': 1, 'Ica': 7, 'Iac': 30}, 'OE3': {'Aca': 7, 'NVC': 44, 'Eca': 8, 'Aac': 1, 'Oca': 14, 'Oac': 6, 'Eac': 0, 'Ica': 36, 'Iac': 15}, 'EE1': {'Aca': 32, 'NVC': 55, 'Eca': 14, 'Aac': 1, 'Oca': 4, 'Oac': 5, 'Eac': 4, 'Ica': 5, 'Iac': 8}, 'OE1': {'Aca': 5, 'NVC': 41, 'Eca': 13, 'Aac': 0, 'Oca': 10, 'Oac': 7, 'Eac': 1, 'Ica': 32, 'Iac': 21}, 'OE4': {'Aca': 13, 'NVC': 54, 'Eca': 14, 'Aac': 0, 'Oca': 8, 'Oac': 7, 'Eac': 2, 'Ica': 22, 'Iac': 11}, 'OO4': {'Aca': 2, 'NVC': 76, 'Eca': 2, 'Aac': 0, 'Oca': 14, 'Oac': 8, 'Eac': 0, 'Ica': 12, 'Iac': 11}, 'OO1': {'Aca': 1, 'NVC': 47, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 4, 'Eac': 0, 'Ica': 40, 'Iac': 14}, 'EE3': {'Aca': 14, 'NVC': 90, 'Eca': 11, 'Aac': 1, 'Oca': 5, 'Oac': 2, 'Eac': 2, 'Ica': 3, 'Iac': 6}, 'OO3': {'Aca': 1, 'NVC': 78, 'Eca': 1, 'Aac': 2, 'Oca': 8, 'Oac': 9, 'Eac': 1, 'Ica': 17, 'Iac': 12}, 'OO2': {'Aca': 1, 'NVC': 55, 'Eca': 0, 'Aac': 0, 'Oca': 37, 'Oac': 10, 'Eac': 0, 'Ica': 15, 'Iac': 8}, 'EE2': {'Aca': 18, 'NVC': 48, 'Eca': 24, 'Aac': 1, 'Oca': 4, 'Oac': 8, 'Eac': 3, 'Ica': 5, 'Iac': 10}, 'OI3': {'Aca': 2, 'NVC': 54, 'Eca': 2, 'Aac': 1, 'Oca': 19, 'Oac': 13, 'Eac': 0, 'Ica': 17, 'Iac': 19}, 'OI2': {'Aca': 5, 'NVC': 38, 'Eca': 1, 'Aac': 0, 'Oca': 51, 'Oac': 12, 'Eac': 0, 'Ica': 13, 'Iac': 8}, 'OI1': {'Aca': 1, 'NVC': 45, 'Eca': 1, 'Aac': 3, 'Oca': 20, 'Oac': 8, 'Eac': 1, 'Ica': 27, 'Iac': 23}, 'OI4': {'Aca': 4, 'NVC': 59, 'Eca': 1, 'Aac': 0, 'Oca': 26, 'Oac': 6, 'Eac': 0, 'Ica': 12, 'Iac': 17}, 'EO2': {'Aca': 7, 'NVC': 41, 'Eca': 3, 'Aac': 3, 'Oca': 32, 'Oac': 23, 'Eac': 1, 'Ica': 8, 'Iac': 8}, 'IE1': {'Aca': 21, 'NVC': 25, 'Eca': 6, 'Aac': 1, 'Oca': 14, 'Oac': 4, 'Eac': 1, 'Ica': 45, 'Iac': 8}, 'IE3': {'Aca': 17, 'NVC': 20, 'Eca': 22, 'Aac': 0, 'Oca': 12, 'Oac': 12, 'Eac': 1, 'Ica': 41, 'Iac': 7}, 'IE2': {'Aca': 11, 'NVC': 36, 'Eca': 34, 'Aac': 0, 'Oca': 14, 'Oac': 12, 'Eac': 1, 'Ica': 17, 'Iac': 5}, 'IE4': {'Aca': 18, 'NVC': 35, 'Eca': 14, 'Aac': 0, 'Oca': 12, 'Oac': 4, 'Eac': 2, 'Ica': 35, 'Iac': 9}, 'IO2': {'Aca': 4, 'NVC': 45, 'Eca': 0, 'Aac': 0, 'Oca': 29, 'Oac': 10, 'Eac': 2, 'Ica': 19, 'Iac': 11}, 'OE2': {'Aca': 6, 'NVC': 45, 'Eca': 16, 'Aac': 1, 'Oca': 15, 'Oac': 10, 'Eac': 3, 'Ica': 18, 'Iac': 4}, 'IA4': {'Aca': 2, 'NVC': 9, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 51, 'Eac': 4, 'Ica': 6, 'Iac': 49}, 'EO4': {'Aca': 8, 'NVC': 50, 'Eca': 5, 'Aac': 2, 'Oca': 26, 'Oac': 5, 'Eac': 0, 'Ica': 19, 'Iac': 10}, 'IA1': {'Aca': 1, 'NVC': 1, 'Eca': 1, 'Aac': 3, 'Oca': 4, 'Oac': 19, 'Eac': 1, 'Ica': 7, 'Iac': 86}, 'IA3': {'Aca': 1, 'NVC': 29, 'Eca': 2, 'Aac': 0, 'Oca': 6, 'Oac': 25, 'Eac': 1, 'Ica': 9, 'Iac': 52}, 'IA2': {'Aca': 0, 'NVC': 11, 'Eca': 0, 'Aac': 4, 'Oca': 5, 'Oac': 73, 'Eac': 6, 'Ica': 3, 'Iac': 25}, 'EI1': {'Aca': 32, 'NVC': 32, 'Eca': 10, 'Aac': 2, 'Oca': 27, 'Oac': 2, 'Eac': 0, 'Ica': 11, 'Iac': 11}, 'IO4': {'Aca': 0, 'NVC': 53, 'Eca': 0, 'Aac': 2, 'Oca': 11, 'Oac': 10, 'Eac': 0, 'Ica': 45, 'Iac': 8}, 'II1': {'Aca': 1, 'NVC': 38, 'Eca': 1, 'Aac': 1, 'Oca': 7, 'Oac': 11, 'Eac': 0, 'Ica': 10, 'Iac': 54}, 'OA1': {'Aca': 4, 'NVC': 20, 'Eca': 4, 'Aac': 2, 'Oca': 19, 'Oac': 8, 'Eac': 1, 'Ica': 40, 'Iac': 29}, 'II3': {'Aca': 3, 'NVC': 65, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 17, 'Eac': 0, 'Ica': 6, 'Iac': 28}, 'II2': {'Aca': 1, 'NVC': 37, 'Eca': 2, 'Aac': 1, 'Oca': 12, 'Oac': 45, 'Eac': 1, 'Ica': 2, 'Iac': 26}, 'EE4': {'Aca': 16, 'NVC': 77, 'Eca': 10, 'Aac': 0, 'Oca': 3, 'Oac': 3, 'Eac': 0, 'Ica': 3, 'Iac': 6}, 'IO3': {'Aca': 2, 'NVC': 60, 'Eca': 2, 'Aac': 0, 'Oca': 20, 'Oac': 5, 'Eac': 0, 'Ica': 23, 'Iac': 16}, 'EI3': {'Aca': 21, 'NVC': 31, 'Eca': 15, 'Aac': 0, 'Oca': 38, 'Oac': 5, 'Eac': 0, 'Ica': 12, 'Iac': 5}, 'IO1': {'Aca': 2, 'NVC': 43, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 5, 'Eac': 1, 'Ica': 47, 'Iac': 13}, 'EI2': {'Aca': 5, 'NVC': 23, 'Eca': 18, 'Aac': 0, 'Oca': 54, 'Oac': 11, 'Eac': 2, 'Ica': 11, 'Iac': 2}, 'OA3': {'Aca': 5, 'NVC': 24, 'Eca': 4, 'Aac': 1, 'Oca': 19, 'Oac': 16, 'Eac': 0, 'Ica': 42, 'Iac': 17}, 'AO4': {'Aca': 2, 'NVC': 9, 'Eca': 0, 'Aac': 1, 'Oca': 16, 'Oac': 14, 'Eac': 0, 'Ica': 73, 'Iac': 7}, 'AO3': {'Aca': 1, 'NVC': 29, 'Eca': 1, 'Aac': 1, 'Oca': 44, 'Oac': 13, 'Eac': 1, 'Ica': 20, 'Iac': 14}, 'AO2': {'Aca': 3, 'NVC': 21, 'Eca': 3, 'Aac': 0, 'Oca': 51, 'Oac': 17, 'Eac': 2, 'Ica': 18, 'Iac': 11}, 'AO1': {'Aca': 1, 'NVC': 14, 'Eca': 1, 'Aac': 0, 'Oca': 14, 'Oac': 10, 'Eac': 2, 'Ica': 81, 'Iac': 5}, 'EA1': {'Aca': 59, 'NVC': 18, 'Eca': 20, 'Aac': 4, 'Oca': 5, 'Oac': 3, 'Eac': 1, 'Ica': 6, 'Iac': 4}, 'EA3': {'Aca': 65, 'NVC': 10, 'Eca': 37, 'Aac': 1, 'Oca': 5, 'Oac': 1, 'Eac': 0, 'Ica': 6, 'Iac': 7}, 'EA2': {'Aca': 18, 'NVC': 10, 'Eca': 81, 'Aac': 1, 'Oca': 7, 'Oac': 4, 'Eac': 1, 'Ica': 4, 'Iac': 1}, 'EA4': {'Aca': 32, 'NVC': 29, 'Eca': 41, 'Aac': 1, 'Oca': 15, 'Oac': 6, 'Eac': 1, 'Ica': 3, 'Iac': 2}, 'EI4': {'Aca': 13, 'NVC': 44, 'Eca': 9, 'Aac': 0, 'Oca': 33, 'Oac': 8, 'Eac': 0, 'Ica': 11, 'Iac': 6}, 'AE1': {'Aca': 84, 'NVC': 6, 'Eca': 21, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 1, 'Ica': 7, 'Iac': 5}, 'AE3': {'Aca': 49, 'NVC': 12, 'Eca': 44, 'Aac': 0, 'Oca': 4, 'Oac': 4, 'Eac': 2, 'Ica': 5, 'Iac': 2}, 'AE2': {'Aca': 26, 'NVC': 27, 'Eca': 52, 'Aac': 0, 'Oca': 7, 'Oac': 1, 'Eac': 1, 'Ica': 11, 'Iac': 1}, 'AE4': {'Aca': 46, 'NVC': 28, 'Eca': 14, 'Aac': 2, 'Oca': 7, 'Oac': 3, 'Eac': 0, 'Ica': 22, 'Iac': 4}, 'AI4': {'Aca': 0, 'NVC': 9, 'Eca': 0, 'Aac': 2, 'Oca': 4, 'Oac': 38, 'Eac': 2, 'Ica': 8, 'Iac': 73}, 'AI1': {'Aca': 1, 'NVC': 12, 'Eca': 0, 'Aac': 1, 'Oca': 7, 'Oac': 21, 'Eac': 2, 'Ica': 7, 'Iac': 77}, 'AI3': {'Aca': 4, 'NVC': 36, 'Eca': 2, 'Aac': 3, 'Oca': 5, 'Oac': 46, 'Eac': 0, 'Ica': 6, 'Iac': 24}, 'AI2': {'Aca': 0, 'NVC': 5, 'Eca': 1, 'Aac': 0, 'Oca': 7, 'Oac': 79, 'Eac': 3, 'Ica': 4, 'Iac': 24}, 'EO3': {'Aca': 6, 'NVC': 58, 'Eca': 9, 'Aac': 0, 'Oca': 27, 'Oac': 11, 'Eac': 0, 'Ica': 9, 'Iac': 11}, 'AA4': {'Aca': 1, 'NVC': 26, 'Eca': 0, 'Aac': 49, 'Oca': 1, 'Oac': 16, 'Eac': 13, 'Ica': 3, 'Iac': 22}, 'EO1': {'Aca': 16, 'NVC': 61, 'Eca': 5, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 14, 'Iac': 12}, 'OA4': {'Aca': 3, 'NVC': 11, 'Eca': 3, 'Aac': 4, 'Oca': 67, 'Oac': 9, 'Eac': 1, 'Ica': 14, 'Iac': 15}, 'AA1': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 85, 'Oca': 2, 'Oac': 5, 'Eac': 11, 'Ica': 1, 'Iac': 11}, 'OA2': {'Aca': 1, 'NVC': 18, 'Eca': 2, 'Aac': 0, 'Oca': 71, 'Oac': 14, 'Eac': 1, 'Ica': 11, 'Iac': 9}, 'AA3': {'Aca': 2, 'NVC': 51, 'Eca': 1, 'Aac': 40, 'Oca': 1, 'Oac': 4, 'Eac': 14, 'Ica': 3, 'Iac': 7}, 'AA2': {'Aca': 0, 'NVC': 5, 'Eca': 1, 'Aac': 31, 'Oca': 1, 'Oac': 6, 'Eac': 78, 'Ica': 1, 'Iac': 8}}, {'II4': {'Aca': 3, 'NVC': 63, 'Eca': 1, 'Aac': 0, 'Oca': 5, 'Oac': 19, 'Eac': 1, 'Ica': 7, 'Iac': 33}, 'OE3': {'Aca': 9, 'NVC': 42, 'Eca': 8, 'Aac': 1, 'Oca': 13, 'Oac': 7, 'Eac': 0, 'Ica': 31, 'Iac': 16}, 'EE1': {'Aca': 31, 'NVC': 54, 'Eca': 15, 'Aac': 1, 'Oca': 4, 'Oac': 5, 'Eac': 4, 'Ica': 6, 'Iac': 9}, 'OE1': {'Aca': 6, 'NVC': 34, 'Eca': 12, 'Aac': 0, 'Oca': 12, 'Oac': 7, 'Eac': 1, 'Ica': 33, 'Iac': 20}, 'OE4': {'Aca': 11, 'NVC': 49, 'Eca': 12, 'Aac': 1, 'Oca': 10, 'Oac': 10, 'Eac': 2, 'Ica': 22, 'Iac': 11}, 'OO4': {'Aca': 2, 'NVC': 71, 'Eca': 2, 'Aac': 0, 'Oca': 15, 'Oac': 9, 'Eac': 0, 'Ica': 13, 'Iac': 11}, 'OO1': {'Aca': 1, 'NVC': 48, 'Eca': 1, 'Aac': 1, 'Oca': 16, 'Oac': 4, 'Eac': 0, 'Ica': 43, 'Iac': 15}, 'EE3': {'Aca': 13, 'NVC': 81, 'Eca': 12, 'Aac': 0, 'Oca': 4, 'Oac': 2, 'Eac': 2, 'Ica': 4, 'Iac': 7}, 'OO3': {'Aca': 2, 'NVC': 73, 'Eca': 1, 'Aac': 2, 'Oca': 9, 'Oac': 7, 'Eac': 0, 'Ica': 14, 'Iac': 13}, 'OO2': {'Aca': 1, 'NVC': 52, 'Eca': 0, 'Aac': 0, 'Oca': 39, 'Oac': 11, 'Eac': 0, 'Ica': 18, 'Iac': 9}, 'EE2': {'Aca': 16, 'NVC': 56, 'Eca': 27, 'Aac': 0, 'Oca': 5, 'Oac': 8, 'Eac': 3, 'Ica': 4, 'Iac': 8}, 'OI3': {'Aca': 3, 'NVC': 58, 'Eca': 2, 'Aac': 1, 'Oca': 21, 'Oac': 11, 'Eac': 0, 'Ica': 13, 'Iac': 19}, 'OI2': {'Aca': 4, 'NVC': 35, 'Eca': 1, 'Aac': 0, 'Oca': 53, 'Oac': 14, 'Eac': 0, 'Ica': 14, 'Iac': 8}, 'OI1': {'Aca': 1, 'NVC': 47, 'Eca': 1, 'Aac': 2, 'Oca': 18, 'Oac': 9, 'Eac': 1, 'Ica': 25, 'Iac': 23}, 'OI4': {'Aca': 4, 'NVC': 57, 'Eca': 2, 'Aac': 0, 'Oca': 27, 'Oac': 6, 'Eac': 0, 'Ica': 13, 'Iac': 19}, 'EO2': {'Aca': 6, 'NVC': 42, 'Eca': 4, 'Aac': 3, 'Oca': 31, 'Oac': 22, 'Eac': 2, 'Ica': 6, 'Iac': 8}, 'IE1': {'Aca': 18, 'NVC': 25, 'Eca': 6, 'Aac': 1, 'Oca': 15, 'Oac': 4, 'Eac': 1, 'Ica': 43, 'Iac': 12}, 'IE3': {'Aca': 17, 'NVC': 17, 'Eca': 20, 'Aac': 0, 'Oca': 11, 'Oac': 11, 'Eac': 1, 'Ica': 37, 'Iac': 7}, 'IE2': {'Aca': 11, 'NVC': 34, 'Eca': 31, 'Aac': 0, 'Oca': 15, 'Oac': 10, 'Eac': 1, 'Ica': 16, 'Iac': 4}, 'IE4': {'Aca': 20, 'NVC': 35, 'Eca': 15, 'Aac': 0, 'Oca': 10, 'Oac': 5, 'Eac': 2, 'Ica': 34, 'Iac': 8}, 'IO2': {'Aca': 3, 'NVC': 44, 'Eca': 0, 'Aac': 0, 'Oca': 32, 'Oac': 11, 'Eac': 2, 'Ica': 18, 'Iac': 13}, 'OE2': {'Aca': 6, 'NVC': 52, 'Eca': 18, 'Aac': 1, 'Oca': 13, 'Oac': 10, 'Eac': 3, 'Ica': 15, 'Iac': 2}, 'IA4': {'Aca': 2, 'NVC': 9, 'Eca': 1, 'Aac': 1, 'Oca': 6, 'Oac': 50, 'Eac': 4, 'Ica': 4, 'Iac': 47}, 'EO4': {'Aca': 8, 'NVC': 50, 'Eca': 7, 'Aac': 2, 'Oca': 25, 'Oac': 7, 'Eac': 0, 'Ica': 20, 'Iac': 10}, 'IA1': {'Aca': 1, 'NVC': 0, 'Eca': 1, 'Aac': 2, 'Oca': 4, 'Oac': 21, 'Eac': 1, 'Ica': 8, 'Iac': 88}, 'IA3': {'Aca': 2, 'NVC': 30, 'Eca': 3, 'Aac': 1, 'Oca': 6, 'Oac': 27, 'Eac': 1, 'Ica': 10, 'Iac': 47}, 'IA2': {'Aca': 0, 'NVC': 8, 'Eca': 0, 'Aac': 3, 'Oca': 5, 'Oac': 79, 'Eac': 6, 'Ica': 3, 'Iac': 26}, 'EI1': {'Aca': 30, 'NVC': 33, 'Eca': 9, 'Aac': 2, 'Oca': 26, 'Oac': 1, 'Eac': 0, 'Ica': 9, 'Iac': 9}, 'IO4': {'Aca': 0, 'NVC': 52, 'Eca': 0, 'Aac': 0, 'Oca': 9, 'Oac': 8, 'Eac': 0, 'Ica': 42, 'Iac': 10}, 'II1': {'Aca': 1, 'NVC': 41, 'Eca': 1, 'Aac': 1, 'Oca': 7, 'Oac': 12, 'Eac': 0, 'Ica': 8, 'Iac': 59}, 'OA1': {'Aca': 4, 'NVC': 18, 'Eca': 3, 'Aac': 2, 'Oca': 18, 'Oac': 8, 'Eac': 1, 'Ica': 44, 'Iac': 27}, 'II3': {'Aca': 4, 'NVC': 65, 'Eca': 1, 'Aac': 1, 'Oca': 5, 'Oac': 20, 'Eac': 0, 'Ica': 5, 'Iac': 31}, 'II2': {'Aca': 1, 'NVC': 35, 'Eca': 2, 'Aac': 1, 'Oca': 12, 'Oac': 46, 'Eac': 1, 'Ica': 2, 'Iac': 22}, 'EE4': {'Aca': 17, 'NVC': 81, 'Eca': 11, 'Aac': 0, 'Oca': 2, 'Oac': 4, 'Eac': 0, 'Ica': 5, 'Iac': 5}, 'IO3': {'Aca': 2, 'NVC': 61, 'Eca': 2, 'Aac': 0, 'Oca': 17, 'Oac': 6, 'Eac': 0, 'Ica': 22, 'Iac': 16}, 'EI3': {'Aca': 22, 'NVC': 29, 'Eca': 13, 'Aac': 0, 'Oca': 39, 'Oac': 5, 'Eac': 0, 'Ica': 11, 'Iac': 5}, 'IO1': {'Aca': 3, 'NVC': 40, 'Eca': 1, 'Aac': 0, 'Oca': 16, 'Oac': 7, 'Eac': 1, 'Ica': 43, 'Iac': 12}, 'EI2': {'Aca': 5, 'NVC': 22, 'Eca': 21, 'Aac': 1, 'Oca': 50, 'Oac': 12, 'Eac': 3, 'Ica': 9, 'Iac': 3}, 'OA3': {'Aca': 5, 'NVC': 24, 'Eca': 3, 'Aac': 1, 'Oca': 18, 'Oac': 14, 'Eac': 0, 'Ica': 45, 'Iac': 20}, 'AO4': {'Aca': 3, 'NVC': 11, 'Eca': 0, 'Aac': 1, 'Oca': 17, 'Oac': 16, 'Eac': 0, 'Ica': 77, 'Iac': 6}, 'AO3': {'Aca': 2, 'NVC': 27, 'Eca': 1, 'Aac': 1, 'Oca': 42, 'Oac': 11, 'Eac': 1, 'Ica': 23, 'Iac': 14}, 'AO2': {'Aca': 4, 'NVC': 21, 'Eca': 3, 'Aac': 0, 'Oca': 45, 'Oac': 17, 'Eac': 1, 'Ica': 14, 'Iac': 14}, 'AO1': {'Aca': 1, 'NVC': 13, 'Eca': 1, 'Aac': 0, 'Oca': 17, 'Oac': 10, 'Eac': 2, 'Ica': 72, 'Iac': 5}, 'EA1': {'Aca': 63, 'NVC': 23, 'Eca': 21, 'Aac': 5, 'Oca': 5, 'Oac': 3, 'Eac': 1, 'Ica': 6, 'Iac': 3}, 'EA3': {'Aca': 61, 'NVC': 10, 'Eca': 34, 'Aac': 1, 'Oca': 5, 'Oac': 1, 'Eac': 0, 'Ica': 7, 'Iac': 7}, 'EA2': {'Aca': 19, 'NVC': 11, 'Eca': 78, 'Aac': 1, 'Oca': 5, 'Oac': 3, 'Eac': 1, 'Ica': 4, 'Iac': 1}, 'EA4': {'Aca': 33, 'NVC': 27, 'Eca': 38, 'Aac': 1, 'Oca': 15, 'Oac': 5, 'Eac': 1, 'Ica': 3, 'Iac': 3}, 'EI4': {'Aca': 14, 'NVC': 43, 'Eca': 8, 'Aac': 0, 'Oca': 35, 'Oac': 9, 'Eac': 0, 'Ica': 12, 'Iac': 8}, 'AE1': {'Aca': 79, 'NVC': 8, 'Eca': 21, 'Aac': 0, 'Oca': 1, 'Oac': 2, 'Eac': 1, 'Ica': 7, 'Iac': 4}, 'AE3': {'Aca': 52, 'NVC': 13, 'Eca': 46, 'Aac': 0, 'Oca': 5, 'Oac': 4, 'Eac': 3, 'Ica': 4, 'Iac': 2}, 'AE2': {'Aca': 25, 'NVC': 26, 'Eca': 52, 'Aac': 0, 'Oca': 4, 'Oac': 1, 'Eac': 1, 'Ica': 12, 'Iac': 1}, 'AE4': {'Aca': 44, 'NVC': 31, 'Eca': 17, 'Aac': 2, 'Oca': 7, 'Oac': 3, 'Eac': 0, 'Ica': 22, 'Iac': 3}, 'AI4': {'Aca': 0, 'NVC': 9, 'Eca': 0, 'Aac': 1, 'Oca': 4, 'Oac': 34, 'Eac': 3, 'Ica': 7, 'Iac': 66}, 'AI1': {'Aca': 1, 'NVC': 13, 'Eca': 0, 'Aac': 2, 'Oca': 3, 'Oac': 18, 'Eac': 2, 'Ica': 7, 'Iac': 75}, 'AI3': {'Aca': 4, 'NVC': 35, 'Eca': 2, 'Aac': 3, 'Oca': 4, 'Oac': 46, 'Eac': 0, 'Ica': 5, 'Iac': 26}, 'AI2': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 1, 'Oca': 8, 'Oac': 75, 'Eac': 4, 'Ica': 6, 'Iac': 24}, 'EO3': {'Aca': 7, 'NVC': 53, 'Eca': 8, 'Aac': 1, 'Oca': 25, 'Oac': 11, 'Eac': 0, 'Ica': 13, 'Iac': 9}, 'AA4': {'Aca': 1, 'NVC': 24, 'Eca': 0, 'Aac': 48, 'Oca': 1, 'Oac': 15, 'Eac': 13, 'Ica': 2, 'Iac': 23}, 'EO1': {'Aca': 16, 'NVC': 54, 'Eca': 5, 'Aac': 0, 'Oca': 19, 'Oac': 5, 'Eac': 0, 'Ica': 12, 'Iac': 10}, 'OA4': {'Aca': 2, 'NVC': 14, 'Eca': 3, 'Aac': 4, 'Oca': 68, 'Oac': 7, 'Eac': 1, 'Ica': 16, 'Iac': 12}, 'AA1': {'Aca': 0, 'NVC': 6, 'Eca': 1, 'Aac': 87, 'Oca': 3, 'Oac': 4, 'Eac': 12, 'Ica': 3, 'Iac': 10}, 'OA2': {'Aca': 1, 'NVC': 15, 'Eca': 2, 'Aac': 0, 'Oca': 77, 'Oac': 12, 'Eac': 1, 'Ica': 12, 'Iac': 9}, 'AA3': {'Aca': 1, 'NVC': 55, 'Eca': 1, 'Aac': 37, 'Oca': 1, 'Oac': 5, 'Eac': 13, 'Ica': 3, 'Iac': 9}, 'AA2': {'Aca': 0, 'NVC': 5, 'Eca': 2, 'Aac': 31, 'Oca': 2, 'Oac': 6, 'Eac': 73, 'Ica': 1, 'Iac': 7}}]
	foldDict = mfaFreq[fold]

	mfaFacts = []
	for id in testSyllogisms:
		task1 = testTasks[id][0]
		task2 = testTasks[id][1]
		encodedTask = encodeTask(task1, task2)
		#print("Encoded Task of " + str(task1) + ' and ' + str(task2) + 'is \t:' + str(encodedTask))
		
		#insert the responses with their frequencies as probabilities for the task and eqTask for each id

		freqDict = foldDict[encodedTask]
		sumFreq = 0.0
		freqList = []
		responseList = []
		for response, freq in freqDict.items():
			freqList.append(freq)
			responseList.append(response)
			sumFreq += freq

		facts = []
		if encodedTask not in eqTasks:
			for response, freq in zip(responseList, freqList):
				prob = freq/sumFreq
				atom = getAtom(response, person, id)
				if prob > 0:
					facts.append(str(prob) + '::' + atom)

		else:
			eqTask = eqTasks[encodedTask]
			freqEqDict = foldDict[eqTask]
			sumEqFreq = sumFreq
			freqEqList = []
			responseEqList = []
			for response, freq in freqEqDict.items():
				freqEqList.append(freq)
				if response == 'NVC':
					responseEq = response
				else:
					responseEq = response[0] + response[2] + response[1]
				responseEqList.append(responseEq)
				sumEqFreq += freq
			
			for responseEq, freqEq in zip(responseEqList, freqEqList):
				index = responseList.index(responseEq)
				freq = freqList[index]
				prob = (freqEq + freq)/sumEqFreq

				atom = getAtom(responseEq, person, id)
				

				if prob > 0:
					facts.append(str(prob) + '::' + atom)
		
		mfaFacts.append(';'.join(facts) + '.')
	
	

	# For a given fold, mfaRules := Freq/sum_freq :: Response :- Task
	mfaRules = []
	
	for task, freqDict in foldDict.items():
		sumFreq = 0.0
		freqList = []
		responseList = []
		for response, freq in freqDict.items():
			freqList.append(freq)
			responseList.append(response)
			sumFreq += freq
		freqList = [freq/sumFreq for freq in freqList]
		heads = []
		for freq, response in zip(freqList, responseList):
			if freq > 0:
				heads.append(str(freq)+'::'+getResponse(response, person))
		head = ';'.join(heads)
		body = ','.join(decodeTask(task, person))
		mfaRules.append(head + ':-' + body + '.')

	problogQuery = '\n'.join(init)
	problogQuery += '\n'
	problogQuery += '\n'.join([str(item[0])+str(item[1])+'.' for item in testFacts])
	problogQuery += '\n'
	problogQuery += '\n'.join(mfaFacts)
	problogQuery += '\n'
	problogQuery += '\n'.join(logicallyValidRules)
	problogQuery += '\n'
	problogQuery += '\n'.join(personIndependentRules)
	problogQuery += '\n'
	problogQuery += '\n'.join(rules)
	#problogQuery += '\n'.join(mfaRules)
	problogQuery += '\n'
	problogQuery += '\n'.join(queries)
	print("ProbLog Query \t:" + str(problogQuery))

	if rulesIndicator != '000':
		p = PrologString(problogQuery)
		inferences = get_evaluatable().create_from(p).evaluate()

		# Create a new dict after converting every term in the key to a string
		inferenceDict = {}
		for term, probability in inferences.items():
			inferenceDict[str(term)] = probability

		#if probability > 1e-8:
		#	print('Fact inferred \t:' + str(probability) + '::' + str(term) + '.')
	
	mfaList = [{'II4': ('NVC', 59), 'OE3': ('NVC', 43), 'EE1': ('NVC', 54), 'OE1': ('NVC', 38), 'OE4': ('NVC', 49), 'OO4': ('NVC', 71), 'OO1': ('NVC', 48), 'EE3': ('NVC', 86), 'OO3': ('NVC', 77), 'OO2': ('NVC', 52), 'EE2': ('NVC', 57), 'OI3': ('NVC', 58), 'OI2': ('Oca', 49), 'OI1': ('NVC', 41), 'OI4': ('NVC', 61), 'EO2': ('NVC', 42), 'IE1': ('Ica', 44), 'IE3': ('Ica', 40), 'IE2': ('NVC', 35), 'IE4': ('NVC', 32), 'IO2': ('NVC', 42), 'OE2': ('NVC', 55), 'IA4': ('Oac', 49), 'EO4': ('NVC', 46), 'IA1': ('Iac', 89), 'IA3': ('Iac', 46), 'IA2': ('Oac', 73), 'EI1': ('NVC', 33), 'IO4': ('NVC', 47), 'II1': ('Iac', 60), 'OA1': ('Ica', 37), 'II3': ('NVC', 59), 'II2': ('Oac', 48), 'EE4': ('NVC', 82), 'IO3': ('NVC', 57), 'EI3': ('Oca', 37), 'IO1': ('Ica', 48), 'EI2': ('Oca', 50), 'OA3': ('Ica', 39), 'AO4': ('Ica', 76), 'AO3': ('Oca', 39), 'AO2': ('Oca', 50), 'AO1': ('Ica', 75), 'EA1': ('Aca', 63), 'EA3': ('Aca', 66), 'EA2': ('Eca', 73), 'EA4': ('Eca', 39), 'EI4': ('NVC', 44), 'AE1': ('Aca', 81), 'AE3': ('Aca', 47), 'AE2': ('Eca', 51), 'AE4': ('Aca', 43), 'AI4': ('Iac', 67), 'AI1': ('Iac', 81), 'AI3': ('Oac', 47), 'AI2': ('Oac', 73), 'EO3': ('NVC', 52), 'AA4': ('Aac', 50), 'EO1': ('NVC', 58), 'OA4': ('Oca', 64), 'AA1': ('Aac', 90), 'OA2': ('Oca', 74), 'AA3': ('NVC', 56), 'AA2': ('Eac', 71)}, {'II4': ('NVC', 57), 'OE3': ('NVC', 43), 'EE1': ('NVC', 56), 'OE1': ('NVC', 38), 'OE4': ('NVC', 48), 'OO4': ('NVC', 76), 'OO1': ('NVC', 47), 'EE3': ('NVC', 82), 'OO3': ('NVC', 75), 'OO2': ('NVC', 49), 'EE2': ('NVC', 52), 'OI3': ('NVC', 54), 'OI2': ('Oca', 56), 'OI1': ('NVC', 42), 'OI4': ('NVC', 56), 'EO2': ('NVC', 44), 'IE1': ('Ica', 41), 'IE3': ('Ica', 37), 'IE2': ('NVC', 34), 'IE4': ('NVC', 35), 'IO2': ('NVC', 45), 'OE2': ('NVC', 54), 'IA4': ('Oac', 51), 'EO4': ('NVC', 51), 'IA1': ('Iac', 86), 'IA3': ('Iac', 50), 'IA2': ('Oac', 75), 'EI1': ('NVC', 36), 'IO4': ('NVC', 47), 'II1': ('Iac', 57), 'OA1': ('Ica', 42), 'II3': ('NVC', 65), 'II2': ('Oac', 47), 'EE4': ('NVC', 78), 'IO3': ('NVC', 60), 'EI3': ('Oca', 40), 'IO1': ('Ica', 46), 'EI2': ('Oca', 52), 'OA3': ('Ica', 39), 'AO4': ('Ica', 71), 'AO3': ('Oca', 46), 'AO2': ('Oca', 52), 'AO1': ('Ica', 80), 'EA1': ('Aca', 58), 'EA3': ('Aca', 65), 'EA2': ('Eca', 76), 'EA4': ('Eca', 40), 'EI4': ('NVC', 44), 'AE1': ('Aca', 84), 'AE3': ('Aca', 51), 'AE2': ('Eca', 52), 'AE4': ('Aca', 43), 'AI4': ('Iac', 68), 'AI1': ('Iac', 76), 'AI3': ('Oac', 45), 'AI2': ('Oac', 77), 'EO3': ('NVC', 53), 'AA4': ('Aac', 48), 'EO1': ('NVC', 56), 'OA4': ('Oca', 67), 'AA1': ('Aac', 86), 'OA2': ('Oca', 72), 'AA3': ('NVC', 57), 'AA2': ('Eac', 76)}, {'II4': ('NVC', 59), 'OE3': ('NVC', 40), 'EE1': ('NVC', 51), 'OE1': ('NVC', 40), 'OE4': ('NVC', 49), 'OO4': ('NVC', 77), 'OO1': ('NVC', 47), 'EE3': ('NVC', 84), 'OO3': ('NVC', 76), 'OO2': ('NVC', 48), 'EE2': ('NVC', 52), 'OI3': ('NVC', 57), 'OI2': ('Oca', 49), 'OI1': ('NVC', 41), 'OI4': ('NVC', 60), 'EO2': ('NVC', 46), 'IE1': ('Ica', 43), 'IE3': ('Ica', 36), 'IE2': ('NVC', 39), 'IE4': ('NVC', 36), 'IO2': ('NVC', 45), 'OE2': ('NVC', 50), 'IA4': ('Oac', 51), 'EO4': ('NVC', 48), 'IA1': ('Iac', 89), 'IA3': ('Iac', 43), 'IA2': ('Oac', 70), 'EI1': ('NVC', 34), 'IO4': ('NVC', 45), 'II1': ('Iac', 60), 'OA1': ('Ica', 39), 'II3': ('NVC', 58), 'II2': ('Oac', 45), 'EE4': ('NVC', 82), 'IO3': ('NVC', 60), 'EI3': ('Oca', 40), 'IO1': ('Ica', 46), 'EI2': ('Oca', 45), 'OA3': ('Ica', 41), 'AO4': ('Ica', 77), 'AO3': ('Oca', 45), 'AO2': ('Oca', 51), 'AO1': ('Ica', 78), 'EA1': ('Aca', 64), 'EA3': ('Aca', 65), 'EA2': ('Eca', 79), 'EA4': ('Eca', 38), 'EI4': ('NVC', 44), 'AE1': ('Aca', 84), 'AE3': ('Aca', 51), 'AE2': ('Eca', 51), 'AE4': ('Aca', 43), 'AI4': ('Iac', 65), 'AI1': ('Iac', 77), 'AI3': ('Oac', 48), 'AI2': ('Oac', 73), 'EO3': ('NVC', 49), 'AA4': ('Aac', 46), 'EO1': ('NVC', 59), 'OA4': ('Oca', 63), 'AA1': ('Aac', 88), 'OA2': ('Oca', 72), 'AA3': ('NVC', 52), 'AA2': ('Eac', 72)}, {'II4': ('NVC', 57), 'OE3': ('NVC', 39), 'EE1': ('NVC', 52), 'OE1': ('NVC', 38), 'OE4': ('NVC', 47), 'OO4': ('NVC', 76), 'OO1': ('NVC', 49), 'EE3': ('NVC', 82), 'OO3': ('NVC', 75), 'OO2': ('NVC', 52), 'EE2': ('NVC', 55), 'OI3': ('NVC', 56), 'OI2': ('Oca', 52), 'OI1': ('NVC', 44), 'OI4': ('NVC', 54), 'EO2': ('NVC', 42), 'IE1': ('Ica', 46), 'IE3': ('Ica', 37), 'IE2': ('NVC', 35), 'IE4': ('NVC', 36), 'IO2': ('NVC', 44), 'OE2': ('NVC', 56), 'IA4': ('Iac', 51), 'EO4': ('NVC', 50), 'IA1': ('Iac', 88), 'IA3': ('Iac', 47), 'IA2': ('Oac', 76), 'EI1': ('NVC', 33), 'IO4': ('NVC', 50), 'II1': ('Iac', 55), 'OA1': ('Ica', 44), 'II3': ('NVC', 64), 'II2': ('Oac', 46), 'EE4': ('NVC', 78), 'IO3': ('NVC', 59), 'EI3': ('Oca', 36), 'IO1': ('Ica', 48), 'EI2': ('Oca', 51), 'OA3': ('Ica', 43), 'AO4': ('Ica', 73), 'AO3': ('Oca', 43), 'AO2': ('Oca', 52), 'AO1': ('Ica', 78), 'EA1': ('Aca', 62), 'EA3': ('Aca', 65), 'EA2': ('Eca', 79), 'EA4': ('Eca', 40), 'EI4': ('NVC', 42), 'AE1': ('Aca', 83), 'AE3': ('Aca', 52), 'AE2': ('Eca', 48), 'AE4': ('Aca', 44), 'AI4': ('Iac', 64), 'AI1': ('Iac', 76), 'AI3': ('Oac', 49), 'AI2': ('Oac', 78), 'EO3': ('NVC', 47), 'AA4': ('Aac', 44), 'EO1': ('NVC', 54), 'OA4': ('Oca', 67), 'AA1': ('Aac', 86), 'OA2': ('Oca', 72), 'AA3': ('NVC', 57), 'AA2': ('Eac', 73)}, {'II4': ('NVC', 63), 'OE3': ('NVC', 43), 'EE1': ('NVC', 52), 'OE1': ('NVC', 38), 'OE4': ('NVC', 52), 'OO4': ('NVC', 76), 'OO1': ('NVC', 48), 'EE3': ('NVC', 79), 'OO3': ('NVC', 72), 'OO2': ('NVC', 51), 'EE2': ('NVC', 50), 'OI3': ('NVC', 56), 'OI2': ('Oca', 55), 'OI1': ('NVC', 45), 'OI4': ('NVC', 62), 'EO2': ('NVC', 41), 'IE1': ('Ica', 43), 'IE3': ('Ica', 39), 'IE2': ('NVC', 36), 'IE4': ('NVC', 34), 'IO2': ('NVC', 47), 'OE2': ('NVC', 53), 'IA4': ('Oac', 52), 'EO4': ('NVC', 52), 'IA1': ('Iac', 88), 'IA3': ('Iac', 47), 'IA2': ('Oac', 72), 'EI1': ('NVC', 36), 'IO4': ('NVC', 50), 'II1': ('Iac', 50), 'OA1': ('Ica', 41), 'II3': ('NVC', 62), 'II2': ('Oac', 44), 'EE4': ('NVC', 85), 'IO3': ('NVC', 59), 'EI3': ('Oca', 38), 'IO1': ('Ica', 45), 'EI2': ('Oca', 44), 'OA3': ('Ica', 42), 'AO4': ('Ica', 71), 'AO3': ('Oca', 47), 'AO2': ('Oca', 52), 'AO1': ('Ica', 83), 'EA1': ('Aca', 63), 'EA3': ('Aca', 58), 'EA2': ('Eca', 80), 'EA4': ('Eca', 40), 'EI4': ('NVC', 41), 'AE1': ('Aca', 82), 'AE3': ('Aca', 49), 'AE2': ('Eca', 49), 'AE4': ('Aca', 40), 'AI4': ('Iac', 68), 'AI1': ('Iac', 75), 'AI3': ('Oac', 47), 'AI2': ('Oac', 80), 'EO3': ('NVC', 49), 'AA4': ('Aac', 51), 'EO1': ('NVC', 53), 'OA4': ('Oca', 64), 'AA1': ('Aac', 85), 'OA2': ('Oca', 73), 'AA3': ('NVC', 57), 'AA2': ('Eac', 74)}, {'II4': ('NVC', 58), 'OE3': ('NVC', 42), 'EE1': ('NVC', 50), 'OE1': ('NVC', 37), 'OE4': ('NVC', 49), 'OO4': ('NVC', 75), 'OO1': ('NVC', 44), 'EE3': ('NVC', 81), 'OO3': ('NVC', 76), 'OO2': ('NVC', 53), 'EE2': ('NVC', 52), 'OI3': ('NVC', 52), 'OI2': ('Oca', 54), 'OI1': ('NVC', 45), 'OI4': ('NVC', 60), 'EO2': ('NVC', 44), 'IE1': ('Ica', 43), 'IE3': ('Ica', 37), 'IE2': ('NVC', 36), 'IE4': ('Ica', 34), 'IO2': ('NVC', 48), 'OE2': ('NVC', 54), 'IA4': ('Oac', 54), 'EO4': ('NVC', 50), 'IA1': ('Iac', 89), 'IA3': ('Iac', 48), 'IA2': ('Oac', 72), 'EI1': ('NVC', 34), 'IO4': ('NVC', 50), 'II1': ('Iac', 56), 'OA1': ('Ica', 42), 'II3': ('NVC', 61), 'II2': ('Oac', 42), 'EE4': ('NVC', 76), 'IO3': ('NVC', 57), 'EI3': ('Oca', 34), 'IO1': ('Ica', 48), 'EI2': ('Oca', 51), 'OA3': ('Ica', 41), 'AO4': ('Ica', 71), 'AO3': ('Oca', 44), 'AO2': ('Oca', 47), 'AO1': ('Ica', 79), 'EA1': ('Aca', 61), 'EA3': ('Aca', 65), 'EA2': ('Eca', 77), 'EA4': ('Eca', 43), 'EI4': ('NVC', 38), 'AE1': ('Aca', 82), 'AE3': ('Aca', 54), 'AE2': ('Eca', 55), 'AE4': ('Aca', 44), 'AI4': ('Iac', 66), 'AI1': ('Iac', 74), 'AI3': ('Oac', 48), 'AI2': ('Oac', 74), 'EO3': ('NVC', 51), 'AA4': ('Aac', 49), 'EO1': ('NVC', 59), 'OA4': ('Oca', 67), 'AA1': ('Aac', 88), 'OA2': ('Oca', 74), 'AA3': ('NVC', 56), 'AA2': ('Eac', 67)}, {'II4': ('NVC', 59), 'OE3': ('NVC', 39), 'EE1': ('NVC', 54), 'OE1': ('NVC', 36), 'OE4': ('NVC', 52), 'OO4': ('NVC', 79), 'OO1': ('NVC', 49), 'EE3': ('NVC', 81), 'OO3': ('NVC', 71), 'OO2': ('NVC', 50), 'EE2': ('NVC', 52), 'OI3': ('NVC', 60), 'OI2': ('Oca', 51), 'OI1': ('NVC', 40), 'OI4': ('NVC', 58), 'EO2': ('NVC', 41), 'IE1': ('Ica', 41), 'IE3': ('Ica', 36), 'IE2': ('Eca', 34), 'IE4': ('NVC', 35), 'IO2': ('NVC', 41), 'OE2': ('NVC', 50), 'IA4': ('Oac', 55), 'EO4': ('NVC', 51), 'IA1': ('Iac', 91), 'IA3': ('Iac', 48), 'IA2': ('Oac', 74), 'EI1': ('NVC', 36), 'IO4': ('NVC', 49), 'II1': ('Iac', 52), 'OA1': ('Ica', 42), 'II3': ('NVC', 62), 'II2': ('Oac', 46), 'EE4': ('NVC', 76), 'IO3': ('NVC', 59), 'EI3': ('Oca', 36), 'IO1': ('Ica', 46), 'EI2': ('Oca', 46), 'OA3': ('Ica', 43), 'AO4': ('Ica', 75), 'AO3': ('Oca', 48), 'AO2': ('Oca', 50), 'AO1': ('Ica', 77), 'EA1': ('Aca', 52), 'EA3': ('Aca', 66), 'EA2': ('Eca', 83), 'EA4': ('Eca', 37), 'EI4': ('NVC', 39), 'AE1': ('Aca', 83), 'AE3': ('Aca', 49), 'AE2': ('Eca', 51), 'AE4': ('Aca', 44), 'AI4': ('Iac', 66), 'AI1': ('Iac', 81), 'AI3': ('Oac', 47), 'AI2': ('Oac', 79), 'EO3': ('NVC', 56), 'AA4': ('Aac', 43), 'EO1': ('NVC', 56), 'OA4': ('Oca', 62), 'AA1': ('Aac', 87), 'OA2': ('Oca', 68), 'AA3': ('NVC', 52), 'AA2': ('Eac', 70)}, {'II4': ('NVC', 61), 'OE3': ('NVC', 39), 'EE1': ('NVC', 53), 'OE1': ('NVC', 38), 'OE4': ('NVC', 46), 'OO4': ('NVC', 70), 'OO1': ('NVC', 50), 'EE3': ('NVC', 82), 'OO3': ('NVC', 74), 'OO2': ('NVC', 51), 'EE2': ('NVC', 57), 'OI3': ('NVC', 53), 'OI2': ('Oca', 52), 'OI1': ('NVC', 42), 'OI4': ('NVC', 58), 'EO2': ('NVC', 40), 'IE1': ('Ica', 43), 'IE3': ('Ica', 38), 'IE2': ('NVC', 35), 'IE4': ('Ica', 33), 'IO2': ('NVC', 49), 'OE2': ('NVC', 53), 'IA4': ('Oac', 51), 'EO4': ('NVC', 47), 'IA1': ('Iac', 88), 'IA3': ('Iac', 49), 'IA2': ('Oac', 74), 'EI1': ('NVC', 35), 'IO4': ('NVC', 52), 'II1': ('Iac', 55), 'OA1': ('Ica', 43), 'II3': ('NVC', 60), 'II2': ('Oac', 50), 'EE4': ('NVC', 86), 'IO3': ('NVC', 62), 'EI3': ('Oca', 40), 'IO1': ('NVC', 43), 'EI2': ('Oca', 52), 'OA3': ('Ica', 39), 'AO4': ('Ica', 74), 'AO3': ('Oca', 43), 'AO2': ('Oca', 54), 'AO1': ('Ica', 71), 'EA1': ('Aca', 58), 'EA3': ('Aca', 63), 'EA2': ('Eca', 77), 'EA4': ('Eca', 40), 'EI4': ('NVC', 44), 'AE1': ('Aca', 77), 'AE3': ('Aca', 50), 'AE2': ('Eca', 52), 'AE4': ('Aca', 41), 'AI4': ('Iac', 63), 'AI1': ('Iac', 73), 'AI3': ('Oac', 45), 'AI2': ('Oac', 77), 'EO3': ('NVC', 54), 'AA4': ('Aac', 49), 'EO1': ('NVC', 57), 'OA4': ('Oca', 68), 'AA1': ('Aac', 82), 'OA2': ('Oca', 67), 'AA3': ('NVC', 56), 'AA2': ('Eac', 75)}, {'II4': ('NVC', 58), 'OE3': ('NVC', 44), 'EE1': ('NVC', 55), 'OE1': ('NVC', 41), 'OE4': ('NVC', 54), 'OO4': ('NVC', 76), 'OO1': ('NVC', 47), 'EE3': ('NVC', 90), 'OO3': ('NVC', 78), 'OO2': ('NVC', 55), 'EE2': ('NVC', 48), 'OI3': ('NVC', 54), 'OI2': ('Oca', 51), 'OI1': ('NVC', 45), 'OI4': ('NVC', 59), 'EO2': ('NVC', 41), 'IE1': ('Ica', 45), 'IE3': ('Ica', 41), 'IE2': ('NVC', 36), 'IE4': ('NVC', 35), 'IO2': ('NVC', 45), 'OE2': ('NVC', 45), 'IA4': ('Oac', 51), 'EO4': ('NVC', 50), 'IA1': ('Iac', 86), 'IA3': ('Iac', 52), 'IA2': ('Oac', 73), 'EI1': ('NVC', 32), 'IO4': ('NVC', 53), 'II1': ('Iac', 54), 'OA1': ('Ica', 40), 'II3': ('NVC', 65), 'II2': ('Oac', 45), 'EE4': ('NVC', 77), 'IO3': ('NVC', 60), 'EI3': ('Oca', 38), 'IO1': ('Ica', 47), 'EI2': ('Oca', 54), 'OA3': ('Ica', 42), 'AO4': ('Ica', 73), 'AO3': ('Oca', 44), 'AO2': ('Oca', 51), 'AO1': ('Ica', 81), 'EA1': ('Aca', 59), 'EA3': ('Aca', 65), 'EA2': ('Eca', 81), 'EA4': ('Eca', 41), 'EI4': ('NVC', 44), 'AE1': ('Aca', 84), 'AE3': ('Aca', 49), 'AE2': ('Eca', 52), 'AE4': ('Aca', 46), 'AI4': ('Iac', 73), 'AI1': ('Iac', 77), 'AI3': ('Oac', 46), 'AI2': ('Oac', 79), 'EO3': ('NVC', 58), 'AA4': ('Aac', 49), 'EO1': ('NVC', 61), 'OA4': ('Oca', 67), 'AA1': ('Aac', 85), 'OA2': ('Oca', 71), 'AA3': ('NVC', 51), 'AA2': ('Eac', 78)}, {'II4': ('NVC', 63), 'OE3': ('NVC', 42), 'EE1': ('NVC', 54), 'OE1': ('NVC', 34), 'OE4': ('NVC', 49), 'OO4': ('NVC', 71), 'OO1': ('NVC', 48), 'EE3': ('NVC', 81), 'OO3': ('NVC', 73), 'OO2': ('NVC', 52), 'EE2': ('NVC', 56), 'OI3': ('NVC', 58), 'OI2': ('Oca', 53), 'OI1': ('NVC', 47), 'OI4': ('NVC', 57), 'EO2': ('NVC', 42), 'IE1': ('Ica', 43), 'IE3': ('Ica', 37), 'IE2': ('NVC', 34), 'IE4': ('NVC', 35), 'IO2': ('NVC', 44), 'OE2': ('NVC', 52), 'IA4': ('Oac', 50), 'EO4': ('NVC', 50), 'IA1': ('Iac', 88), 'IA3': ('Iac', 47), 'IA2': ('Oac', 79), 'EI1': ('NVC', 33), 'IO4': ('NVC', 52), 'II1': ('Iac', 59), 'OA1': ('Ica', 44), 'II3': ('NVC', 65), 'II2': ('Oac', 46), 'EE4': ('NVC', 81), 'IO3': ('NVC', 61), 'EI3': ('Oca', 39), 'IO1': ('Ica', 43), 'EI2': ('Oca', 50), 'OA3': ('Ica', 45), 'AO4': ('Ica', 77), 'AO3': ('Oca', 42), 'AO2': ('Oca', 45), 'AO1': ('Ica', 72), 'EA1': ('Aca', 63), 'EA3': ('Aca', 61), 'EA2': ('Eca', 78), 'EA4': ('Eca', 38), 'EI4': ('NVC', 43), 'AE1': ('Aca', 79), 'AE3': ('Aca', 52), 'AE2': ('Eca', 52), 'AE4': ('Aca', 44), 'AI4': ('Iac', 66), 'AI1': ('Iac', 75), 'AI3': ('Oac', 46), 'AI2': ('Oac', 75), 'EO3': ('NVC', 53), 'AA4': ('Aac', 48), 'EO1': ('NVC', 54), 'OA4': ('Oca', 68), 'AA1': ('Aac', 87), 'OA2': ('Oca', 77), 'AA3': ('NVC', 55), 'AA2': ('Eac', 73)}]

	#Get predictions from inferences by fitting in the most frequence response

	testPredictions = {}
	total = 0
	match = 0
	count = 0
	
	for id in testSyllogisms:
		premises = testPremises[id]

		possibleResponses = []
		for response in responses:
			if response == 'rnvc':
				possibleResponses.append('rnvc' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			else:
				if caCount >= acCount:
					possibleResponses.append(response + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
					possibleResponses.append(response + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
				else:
					possibleResponses.append(response + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
					possibleResponses.append(response + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
		# Prediction starts now
			# If exactly 1 possible response has probability = 1, predict that.
			# If more than 1 possible responses has probability = 1, predict one of those through the following tie-breaker:
				# 1. Take intersection with the most frequent responses for the premises and predict that if there's only one.

		task1 = testTasks[id][0]
		task2 = testTasks[id][1]
		encodedTask = encodeTask(task1, task2)
		#print("Encoded Task of " + str(task1) + ' and ' + str(task2) + 'is \t:' + str(encodedTask))

		# Set of all possible responses with maximum inferred probability.
		set1 = set()
		if rulesIndicator != '000':
			maxProb = 0
			maxTerms = []
				
			for possibleResponse in possibleResponses:
				if possibleResponse.split('(')[0][:-1*len(str(person))] in emptyResponses:
					continue
				
				if possibleResponse not in inferenceDict:
					print('Error:' + possibleResponse + ' not in the inference dict: ' + str(inferenceDict))
				#if inferenceDict[possibleResponse] > 1 - 1e-8:
				#	set1.add(possibleResponse)
				
				
				probability = inferenceDict[possibleResponse]
				#print('probability of ' + str(possibleResponse) + '\t:' +str(probability))
				if probability == maxProb and probability > 1e-8:
					set1.add(possibleResponse)
				elif probability > maxProb:
					set1 = set([possibleResponse])
					maxProb = probability
		#print('Terms with Max Prob (' + str(maxProb) + ') \t: ' + str(set1))
		
		set6  = set() # Most Frequent Answer (MFA)
		
		mfa = mfaList[fold][encodedTask][0]
		
		if mfa == 'NVC':
			#mfa = 'Aca'
			set6.add('rnvc' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
		elif mfa[1] == 'c':
			if mfa[0] == 'A':
				set6.add('rall' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
			elif mfa[0] == 'E':
				set6.add('rno' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
			elif mfa[0] == 'I':
				set6.add('rsome' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
			elif mfa[0] == 'O':
				set6.add('rsomenot' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
		else:
			if mfa[0] == 'A':
				set6.add('rall' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif mfa[0] == 'E':
				set6.add('rno' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif mfa[0] == 'I':
				set6.add('rsome' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif mfa[0] == 'O':
				set6.add('rsomenot' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
		set6Prediction = list(set6)[0]
		#print('MFA of ' + encodedTask + ' in fold ' + str(fold) + ' is \t: ' + str(mfa))	

		print('Set1 \t: ' + str(set1))
		print('Set6 \t: ' + str(set6))

		responseNumList = []
		for possibleResponse in possibleResponses:
			responseNumber = 0.0
			if possibleResponse in set1:
				responseNumber += 10**(precedence[0])
			if possibleResponse in set6:
				responseNumber += 10**(precedence[5])
			responseNumList.append(responseNumber)
			#print(str(id) + '\t:' + possibleResponse + '\t:' + str(responseNumber))


		testPredictions[id] = possibleResponses[max(enumerate(responseNumList), key=lambda x: x[1])[0]]

		#print('Person ' + str(person) + '\t Syllogism ' + str(id) + '\t Predicted ' + testPredictions[id] + '\t Actual ' + testAnswers[id])
	
		if testPredictions[id] == testAnswers[id]:
			match += 1
		total += 1

		
		if set6Prediction not in set1:
			count += 1
			if count > 2:
				break

			print('id \t: ' + str(id))
			print('Rule Predictions \t: ' + str(set1))
			print('MFA \t: ' + str(set6))
			print('Test Prediction \t: ' + str(testPredictions[id]))
			print('Correct Response \t: ' + str(testAnswers[id]))
		
	#print('Learned Rule \t: ' + str(rules))
	#print('testSyllogisms \t: ' + str(testSyllogisms))
	#print('testPremises \t: ' + str(testPremises))
	#print('testFacts \t: ' + str(testFacts))
	#print('testAnswers \t: ' + str(testAnswers))
	#print('testPredictions \t: ' + str(testPredictions))
	#print(str(match) + ' matches out of ' + str(total))
	return (match, total)



#precedences = list(itertools.permutations([1, 2, 3, 4, 5]))

#precedences = [(6,0,0,0,0,5)]

for precedence in precedences:
	def foldAccuracy(fold):
		matchSum = 0.0
		totalSum = 0.0
		ruleDir = rd + 'Class' + str(fold) + '/'
		
		for person in range(1, 2):
		#for person in range(1, 140):
			(match, total) = matchAccuracy(fold, person, ruleDir, precedence)
			matchSum += match
			totalSum += total

		#print('Accuracy for fold ' + str(fold) + ' = ' + str(matchSum) + '/' + str(totalSum) + ' = ' + str(matchSum/totalSum))
		return matchSum/totalSum
	#pool = Pool(processes = 10)
	#accuracyList = pool.map(foldAccuracy, range(0,10))
	accuracyList = [foldAccuracy(0)]
	print(str(rulesIndicator) + ': Net Accuracy for precedence ' + str(precedence) + '\t: ' + str(sum(accuracyList)/len(accuracyList)))
