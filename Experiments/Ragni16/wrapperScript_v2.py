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

def matchAccuracy(fold, person, ruleDir, precedence):
	
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


	testSyllogisms = []
	for i in range(1, 65):
		if i not in trainSyllogisms:
			testSyllogisms.append(i)

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

	logicallyValidRules = ['0.1::rsomenot#(C, A):-all#(A, B), no#(B, C).','0.1::rsomenot#(C, A):-all#(A, B), no#(C, B).','0.1::rsomenot#(C, A):-all#(B, A), no#(C, B).','0.12::rsome#(C, A):-all#(B, A), all#(B, C).','0.12::rsomenot#(A, C):-all#(B, A), somenot#(B, C).','0.13::rsomenot#(C, A):-some#(B, A), no#(C, B).','0.135::rnvc#(A, C):-all#(A, B), somenot#(B, C).','0.14::rnvc#(A, C):-all#(A, B), some#(B, C).','0.15::rsomenot#(A, C):-some#(B, A), no#(B, C).','0.185::rnvc#(A, C):-all#(B, A), somenot#(C, B).','0.2::rsomenot#(C, A):-some#(A, B), no#(C, B).','0.21::rsomenot#(A, C):-some#(A, B), no#(C, B).','0.25::rsome#(A, C):-all#(A, B), all#(B, C).','0.28::rsomenot#(C, A):-some#(B, A), no#(B, C).','0.1::rsomenot#(C, A):-all#(A, B), no#(C, B).','0.3::rsomenot#(A, C):-all#(B, A), no#(C, B).','0.31::rnvc#(A, C):-all#(A, B), all#(C, B).','0.315::rnvc#(A, C):-some#(A, B), some#(B, C).','0.32::rno#(A, C):-all#(A, B), no#(C, B).','0.32::rnvc#(A, C):-some#(A, B), somenot#(B, C).','0.325::rnvc#(A, C):-all#(A, B), some#(C, B).','0.33::rsome#(A, C):-all#(B, A), some#(B, C).','0.36::rsomenot#(C, A):-all#(A, B), somenot#(C, B).','0.37::rsomenot#(A, C):-some#(A, B), no#(B, C).','0.395::rnvc#(A, C):-no#(A, B), somenot#(B, C).','0.395::rnvc#(A, C):-somenot#(A, B), somenot#(B, C).','0.4::rsome#(A, C):-all#(B, A), all#(B, C).','0.4::rsomenot#(A, C):-all#(A, B), somenot#(C, B).','0.42::rnvc#(A, C):-no#(B, A), somenot#(C, B).','0.425::rnvc#(A, C):-some#(B, A), somenot#(C, B).','0.44::rnvc#(A, C):-no#(A, B), no#(B, C).','0.44::rsomenot#(C, A):-some#(A, B), no#(B, C).','0.45::rsome#(C, A):-all#(A, B), all#(B, C).','0.48::rall#(A, C):-all#(A, B), all#(B, C).','0.48::rno#(C, A):-all#(A, B), no#(C, B).','0.48::rnvc#(A, C):-no#(A, B), somenot#(C, B).','0.49::rsome#(C, A):-all#(B, A), some#(B, C).','0.505::rnvc#(A, C):-some#(B, A), somenot#(B, C).','0.51::rnvc#(A, C):-some#(A, B), some#(C, B).','0.51::rnvc#(A, C):-some#(A, B), somenot#(C, B).','0.51::rsome#(C, A):-all#(B, A), some#(C, B).','0.53::rno#(C, A):-all#(A, B), no#(B, C).','0.53::rnvc#(A, C):-no#(B, A), somenot#(B, C).','0.54::rsomenot#(C, A):-all#(B, A), somenot#(B, C).','0.61::rnvc#(A, C):-some#(B, A), some#(B, C).','0.64::rnvc#(A, C):-somenot#(A, B), somenot#(C, B).','0.655::rno#(A, C):-all#(A, B), no#(B, C).','0.655::rsome#(A, C):-all#(B, A), some#(C, B).','0.66::rnvc#(A, C):-no#(B, A), no#(B, C).','0.66::rnvc#(A, C):-somenot#(B, A), somenot#(B, C).','0.76::rnvc#(A, C):-no#(A, B), no#(C, B).','0.8::rsomenot#(A, C):-some#(B, A), no#(C, B).','0.8::rsomenot#(C, A):-all#(B, A), no#(B, C).','0.81::rall#(C, A):-all#(A, B), all#(B, C).','0.9::rsomenot#(A, C):-all#(B, A), no#(B, C).']
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

	problogQuery = '\n'.join(init)
	problogQuery += '\n'
	problogQuery += '\n'.join([str(item[0])+str(item[1])+'.' for item in testFacts])
	problogQuery += '\n'
	problogQuery += '\n'.join(logicallyValidRules)
	problogQuery += '\n'
	problogQuery += '\n'.join(personIndependentRules)
	problogQuery += '\n'
	problogQuery += '\n'.join(rules)
	problogQuery += '\n'
	problogQuery += '\n'.join(queries)
	#print("ProbLog Query \t:" + str(problogQuery))

	if rulesIndicator != '000':
		p = PrologString(problogQuery)
		inferences = get_evaluatable().create_from(p).evaluate()

		# Create a new dict after converting every term in the key to a string
		inferenceDict = {}
		for term, probability in inferences.items():
			inferenceDict[str(term)] = probability

		#if probability > 1e-8:
		#	print('Fact inferred \t:' + str(probability) + '::' + str(term) + '.')
	
	def getEncodedTask(task1, task2):
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

	mfaList = [{'II4': ('NVC', 59), 'OE3': ('NVC', 43), 'EE1': ('NVC', 54), 'OE1': ('NVC', 38), 'OE4': ('NVC', 49), 'OO4': ('NVC', 71), 'OO1': ('NVC', 48), 'EE3': ('NVC', 86), 'OO3': ('NVC', 77), 'OO2': ('NVC', 52), 'EE2': ('NVC', 57), 'OI3': ('NVC', 58), 'OI2': ('Oca', 49), 'OI1': ('NVC', 41), 'OI4': ('NVC', 61), 'EO2': ('NVC', 42), 'IE1': ('Ica', 44), 'IE3': ('Ica', 40), 'IE2': ('NVC', 35), 'IE4': ('NVC', 32), 'IO2': ('NVC', 42), 'OE2': ('NVC', 55), 'IA4': ('Oac', 49), 'EO4': ('NVC', 46), 'IA1': ('Iac', 89), 'IA3': ('Iac', 46), 'IA2': ('Oac', 73), 'EI1': ('NVC', 33), 'IO4': ('NVC', 47), 'II1': ('Iac', 60), 'OA1': ('Ica', 37), 'II3': ('NVC', 59), 'II2': ('Oac', 48), 'EE4': ('NVC', 82), 'IO3': ('NVC', 57), 'EI3': ('Oca', 37), 'IO1': ('Ica', 48), 'EI2': ('Oca', 50), 'OA3': ('Ica', 39), 'AO4': ('Ica', 76), 'AO3': ('Oca', 39), 'AO2': ('Oca', 50), 'AO1': ('Ica', 75), 'EA1': ('Aca', 63), 'EA3': ('Aca', 66), 'EA2': ('Eca', 73), 'EA4': ('Eca', 39), 'EI4': ('NVC', 44), 'AE1': ('Aca', 81), 'AE3': ('Aca', 47), 'AE2': ('Eca', 51), 'AE4': ('Aca', 43), 'AI4': ('Iac', 67), 'AI1': ('Iac', 81), 'AI3': ('Oac', 47), 'AI2': ('Oac', 73), 'EO3': ('NVC', 52), 'AA4': ('Aac', 50), 'EO1': ('NVC', 58), 'OA4': ('Oca', 64), 'AA1': ('Aac', 90), 'OA2': ('Oca', 74), 'AA3': ('NVC', 56), 'AA2': ('Eac', 71)}, {'II4': ('NVC', 57), 'OE3': ('NVC', 43), 'EE1': ('NVC', 56), 'OE1': ('NVC', 38), 'OE4': ('NVC', 48), 'OO4': ('NVC', 76), 'OO1': ('NVC', 47), 'EE3': ('NVC', 82), 'OO3': ('NVC', 75), 'OO2': ('NVC', 49), 'EE2': ('NVC', 52), 'OI3': ('NVC', 54), 'OI2': ('Oca', 56), 'OI1': ('NVC', 42), 'OI4': ('NVC', 56), 'EO2': ('NVC', 44), 'IE1': ('Ica', 41), 'IE3': ('Ica', 37), 'IE2': ('NVC', 34), 'IE4': ('NVC', 35), 'IO2': ('NVC', 45), 'OE2': ('NVC', 54), 'IA4': ('Oac', 51), 'EO4': ('NVC', 51), 'IA1': ('Iac', 86), 'IA3': ('Iac', 50), 'IA2': ('Oac', 75), 'EI1': ('NVC', 36), 'IO4': ('NVC', 47), 'II1': ('Iac', 57), 'OA1': ('Ica', 42), 'II3': ('NVC', 65), 'II2': ('Oac', 47), 'EE4': ('NVC', 78), 'IO3': ('NVC', 60), 'EI3': ('Oca', 40), 'IO1': ('Ica', 46), 'EI2': ('Oca', 52), 'OA3': ('Ica', 39), 'AO4': ('Ica', 71), 'AO3': ('Oca', 46), 'AO2': ('Oca', 52), 'AO1': ('Ica', 80), 'EA1': ('Aca', 58), 'EA3': ('Aca', 65), 'EA2': ('Eca', 76), 'EA4': ('Eca', 40), 'EI4': ('NVC', 44), 'AE1': ('Aca', 84), 'AE3': ('Aca', 51), 'AE2': ('Eca', 52), 'AE4': ('Aca', 43), 'AI4': ('Iac', 68), 'AI1': ('Iac', 76), 'AI3': ('Oac', 45), 'AI2': ('Oac', 77), 'EO3': ('NVC', 53), 'AA4': ('Aac', 48), 'EO1': ('NVC', 56), 'OA4': ('Oca', 67), 'AA1': ('Aac', 86), 'OA2': ('Oca', 72), 'AA3': ('NVC', 57), 'AA2': ('Eac', 76)}, {'II4': ('NVC', 59), 'OE3': ('NVC', 40), 'EE1': ('NVC', 51), 'OE1': ('NVC', 40), 'OE4': ('NVC', 49), 'OO4': ('NVC', 77), 'OO1': ('NVC', 47), 'EE3': ('NVC', 84), 'OO3': ('NVC', 76), 'OO2': ('NVC', 48), 'EE2': ('NVC', 52), 'OI3': ('NVC', 57), 'OI2': ('Oca', 49), 'OI1': ('NVC', 41), 'OI4': ('NVC', 60), 'EO2': ('NVC', 46), 'IE1': ('Ica', 43), 'IE3': ('Ica', 36), 'IE2': ('NVC', 39), 'IE4': ('NVC', 36), 'IO2': ('NVC', 45), 'OE2': ('NVC', 50), 'IA4': ('Oac', 51), 'EO4': ('NVC', 48), 'IA1': ('Iac', 89), 'IA3': ('Iac', 43), 'IA2': ('Oac', 70), 'EI1': ('NVC', 34), 'IO4': ('NVC', 45), 'II1': ('Iac', 60), 'OA1': ('Ica', 39), 'II3': ('NVC', 58), 'II2': ('Oac', 45), 'EE4': ('NVC', 82), 'IO3': ('NVC', 60), 'EI3': ('Oca', 40), 'IO1': ('Ica', 46), 'EI2': ('Oca', 45), 'OA3': ('Ica', 41), 'AO4': ('Ica', 77), 'AO3': ('Oca', 45), 'AO2': ('Oca', 51), 'AO1': ('Ica', 78), 'EA1': ('Aca', 64), 'EA3': ('Aca', 65), 'EA2': ('Eca', 79), 'EA4': ('Eca', 38), 'EI4': ('NVC', 44), 'AE1': ('Aca', 84), 'AE3': ('Aca', 51), 'AE2': ('Eca', 51), 'AE4': ('Aca', 43), 'AI4': ('Iac', 65), 'AI1': ('Iac', 77), 'AI3': ('Oac', 48), 'AI2': ('Oac', 73), 'EO3': ('NVC', 49), 'AA4': ('Aac', 46), 'EO1': ('NVC', 59), 'OA4': ('Oca', 63), 'AA1': ('Aac', 88), 'OA2': ('Oca', 72), 'AA3': ('NVC', 52), 'AA2': ('Eac', 72)}, {'II4': ('NVC', 57), 'OE3': ('NVC', 39), 'EE1': ('NVC', 52), 'OE1': ('NVC', 38), 'OE4': ('NVC', 47), 'OO4': ('NVC', 76), 'OO1': ('NVC', 49), 'EE3': ('NVC', 82), 'OO3': ('NVC', 75), 'OO2': ('NVC', 52), 'EE2': ('NVC', 55), 'OI3': ('NVC', 56), 'OI2': ('Oca', 52), 'OI1': ('NVC', 44), 'OI4': ('NVC', 54), 'EO2': ('NVC', 42), 'IE1': ('Ica', 46), 'IE3': ('Ica', 37), 'IE2': ('NVC', 35), 'IE4': ('NVC', 36), 'IO2': ('NVC', 44), 'OE2': ('NVC', 56), 'IA4': ('Iac', 51), 'EO4': ('NVC', 50), 'IA1': ('Iac', 88), 'IA3': ('Iac', 47), 'IA2': ('Oac', 76), 'EI1': ('NVC', 33), 'IO4': ('NVC', 50), 'II1': ('Iac', 55), 'OA1': ('Ica', 44), 'II3': ('NVC', 64), 'II2': ('Oac', 46), 'EE4': ('NVC', 78), 'IO3': ('NVC', 59), 'EI3': ('Oca', 36), 'IO1': ('Ica', 48), 'EI2': ('Oca', 51), 'OA3': ('Ica', 43), 'AO4': ('Ica', 73), 'AO3': ('Oca', 43), 'AO2': ('Oca', 52), 'AO1': ('Ica', 78), 'EA1': ('Aca', 62), 'EA3': ('Aca', 65), 'EA2': ('Eca', 79), 'EA4': ('Eca', 40), 'EI4': ('NVC', 42), 'AE1': ('Aca', 83), 'AE3': ('Aca', 52), 'AE2': ('Eca', 48), 'AE4': ('Aca', 44), 'AI4': ('Iac', 64), 'AI1': ('Iac', 76), 'AI3': ('Oac', 49), 'AI2': ('Oac', 78), 'EO3': ('NVC', 47), 'AA4': ('Aac', 44), 'EO1': ('NVC', 54), 'OA4': ('Oca', 67), 'AA1': ('Aac', 86), 'OA2': ('Oca', 72), 'AA3': ('NVC', 57), 'AA2': ('Eac', 73)}, {'II4': ('NVC', 63), 'OE3': ('NVC', 43), 'EE1': ('NVC', 52), 'OE1': ('NVC', 38), 'OE4': ('NVC', 52), 'OO4': ('NVC', 76), 'OO1': ('NVC', 48), 'EE3': ('NVC', 79), 'OO3': ('NVC', 72), 'OO2': ('NVC', 51), 'EE2': ('NVC', 50), 'OI3': ('NVC', 56), 'OI2': ('Oca', 55), 'OI1': ('NVC', 45), 'OI4': ('NVC', 62), 'EO2': ('NVC', 41), 'IE1': ('Ica', 43), 'IE3': ('Ica', 39), 'IE2': ('NVC', 36), 'IE4': ('NVC', 34), 'IO2': ('NVC', 47), 'OE2': ('NVC', 53), 'IA4': ('Oac', 52), 'EO4': ('NVC', 52), 'IA1': ('Iac', 88), 'IA3': ('Iac', 47), 'IA2': ('Oac', 72), 'EI1': ('NVC', 36), 'IO4': ('NVC', 50), 'II1': ('Iac', 50), 'OA1': ('Ica', 41), 'II3': ('NVC', 62), 'II2': ('Oac', 44), 'EE4': ('NVC', 85), 'IO3': ('NVC', 59), 'EI3': ('Oca', 38), 'IO1': ('Ica', 45), 'EI2': ('Oca', 44), 'OA3': ('Ica', 42), 'AO4': ('Ica', 71), 'AO3': ('Oca', 47), 'AO2': ('Oca', 52), 'AO1': ('Ica', 83), 'EA1': ('Aca', 63), 'EA3': ('Aca', 58), 'EA2': ('Eca', 80), 'EA4': ('Eca', 40), 'EI4': ('NVC', 41), 'AE1': ('Aca', 82), 'AE3': ('Aca', 49), 'AE2': ('Eca', 49), 'AE4': ('Aca', 40), 'AI4': ('Iac', 68), 'AI1': ('Iac', 75), 'AI3': ('Oac', 47), 'AI2': ('Oac', 80), 'EO3': ('NVC', 49), 'AA4': ('Aac', 51), 'EO1': ('NVC', 53), 'OA4': ('Oca', 64), 'AA1': ('Aac', 85), 'OA2': ('Oca', 73), 'AA3': ('NVC', 57), 'AA2': ('Eac', 74)}, {'II4': ('NVC', 58), 'OE3': ('NVC', 42), 'EE1': ('NVC', 50), 'OE1': ('NVC', 37), 'OE4': ('NVC', 49), 'OO4': ('NVC', 75), 'OO1': ('NVC', 44), 'EE3': ('NVC', 81), 'OO3': ('NVC', 76), 'OO2': ('NVC', 53), 'EE2': ('NVC', 52), 'OI3': ('NVC', 52), 'OI2': ('Oca', 54), 'OI1': ('NVC', 45), 'OI4': ('NVC', 60), 'EO2': ('NVC', 44), 'IE1': ('Ica', 43), 'IE3': ('Ica', 37), 'IE2': ('NVC', 36), 'IE4': ('Ica', 34), 'IO2': ('NVC', 48), 'OE2': ('NVC', 54), 'IA4': ('Oac', 54), 'EO4': ('NVC', 50), 'IA1': ('Iac', 89), 'IA3': ('Iac', 48), 'IA2': ('Oac', 72), 'EI1': ('NVC', 34), 'IO4': ('NVC', 50), 'II1': ('Iac', 56), 'OA1': ('Ica', 42), 'II3': ('NVC', 61), 'II2': ('Oac', 42), 'EE4': ('NVC', 76), 'IO3': ('NVC', 57), 'EI3': ('Oca', 34), 'IO1': ('Ica', 48), 'EI2': ('Oca', 51), 'OA3': ('Ica', 41), 'AO4': ('Ica', 71), 'AO3': ('Oca', 44), 'AO2': ('Oca', 47), 'AO1': ('Ica', 79), 'EA1': ('Aca', 61), 'EA3': ('Aca', 65), 'EA2': ('Eca', 77), 'EA4': ('Eca', 43), 'EI4': ('NVC', 38), 'AE1': ('Aca', 82), 'AE3': ('Aca', 54), 'AE2': ('Eca', 55), 'AE4': ('Aca', 44), 'AI4': ('Iac', 66), 'AI1': ('Iac', 74), 'AI3': ('Oac', 48), 'AI2': ('Oac', 74), 'EO3': ('NVC', 51), 'AA4': ('Aac', 49), 'EO1': ('NVC', 59), 'OA4': ('Oca', 67), 'AA1': ('Aac', 88), 'OA2': ('Oca', 74), 'AA3': ('NVC', 56), 'AA2': ('Eac', 67)}, {'II4': ('NVC', 59), 'OE3': ('NVC', 39), 'EE1': ('NVC', 54), 'OE1': ('NVC', 36), 'OE4': ('NVC', 52), 'OO4': ('NVC', 79), 'OO1': ('NVC', 49), 'EE3': ('NVC', 81), 'OO3': ('NVC', 71), 'OO2': ('NVC', 50), 'EE2': ('NVC', 52), 'OI3': ('NVC', 60), 'OI2': ('Oca', 51), 'OI1': ('NVC', 40), 'OI4': ('NVC', 58), 'EO2': ('NVC', 41), 'IE1': ('Ica', 41), 'IE3': ('Ica', 36), 'IE2': ('Eca', 34), 'IE4': ('NVC', 35), 'IO2': ('NVC', 41), 'OE2': ('NVC', 50), 'IA4': ('Oac', 55), 'EO4': ('NVC', 51), 'IA1': ('Iac', 91), 'IA3': ('Iac', 48), 'IA2': ('Oac', 74), 'EI1': ('NVC', 36), 'IO4': ('NVC', 49), 'II1': ('Iac', 52), 'OA1': ('Ica', 42), 'II3': ('NVC', 62), 'II2': ('Oac', 46), 'EE4': ('NVC', 76), 'IO3': ('NVC', 59), 'EI3': ('Oca', 36), 'IO1': ('Ica', 46), 'EI2': ('Oca', 46), 'OA3': ('Ica', 43), 'AO4': ('Ica', 75), 'AO3': ('Oca', 48), 'AO2': ('Oca', 50), 'AO1': ('Ica', 77), 'EA1': ('Aca', 52), 'EA3': ('Aca', 66), 'EA2': ('Eca', 83), 'EA4': ('Eca', 37), 'EI4': ('NVC', 39), 'AE1': ('Aca', 83), 'AE3': ('Aca', 49), 'AE2': ('Eca', 51), 'AE4': ('Aca', 44), 'AI4': ('Iac', 66), 'AI1': ('Iac', 81), 'AI3': ('Oac', 47), 'AI2': ('Oac', 79), 'EO3': ('NVC', 56), 'AA4': ('Aac', 43), 'EO1': ('NVC', 56), 'OA4': ('Oca', 62), 'AA1': ('Aac', 87), 'OA2': ('Oca', 68), 'AA3': ('NVC', 52), 'AA2': ('Eac', 70)}, {'II4': ('NVC', 61), 'OE3': ('NVC', 39), 'EE1': ('NVC', 53), 'OE1': ('NVC', 38), 'OE4': ('NVC', 46), 'OO4': ('NVC', 70), 'OO1': ('NVC', 50), 'EE3': ('NVC', 82), 'OO3': ('NVC', 74), 'OO2': ('NVC', 51), 'EE2': ('NVC', 57), 'OI3': ('NVC', 53), 'OI2': ('Oca', 52), 'OI1': ('NVC', 42), 'OI4': ('NVC', 58), 'EO2': ('NVC', 40), 'IE1': ('Ica', 43), 'IE3': ('Ica', 38), 'IE2': ('NVC', 35), 'IE4': ('Ica', 33), 'IO2': ('NVC', 49), 'OE2': ('NVC', 53), 'IA4': ('Oac', 51), 'EO4': ('NVC', 47), 'IA1': ('Iac', 88), 'IA3': ('Iac', 49), 'IA2': ('Oac', 74), 'EI1': ('NVC', 35), 'IO4': ('NVC', 52), 'II1': ('Iac', 55), 'OA1': ('Ica', 43), 'II3': ('NVC', 60), 'II2': ('Oac', 50), 'EE4': ('NVC', 86), 'IO3': ('NVC', 62), 'EI3': ('Oca', 40), 'IO1': ('NVC', 43), 'EI2': ('Oca', 52), 'OA3': ('Ica', 39), 'AO4': ('Ica', 74), 'AO3': ('Oca', 43), 'AO2': ('Oca', 54), 'AO1': ('Ica', 71), 'EA1': ('Aca', 58), 'EA3': ('Aca', 63), 'EA2': ('Eca', 77), 'EA4': ('Eca', 40), 'EI4': ('NVC', 44), 'AE1': ('Aca', 77), 'AE3': ('Aca', 50), 'AE2': ('Eca', 52), 'AE4': ('Aca', 41), 'AI4': ('Iac', 63), 'AI1': ('Iac', 73), 'AI3': ('Oac', 45), 'AI2': ('Oac', 77), 'EO3': ('NVC', 54), 'AA4': ('Aac', 49), 'EO1': ('NVC', 57), 'OA4': ('Oca', 68), 'AA1': ('Aac', 82), 'OA2': ('Oca', 67), 'AA3': ('NVC', 56), 'AA2': ('Eac', 75)}, {'II4': ('NVC', 58), 'OE3': ('NVC', 44), 'EE1': ('NVC', 55), 'OE1': ('NVC', 41), 'OE4': ('NVC', 54), 'OO4': ('NVC', 76), 'OO1': ('NVC', 47), 'EE3': ('NVC', 90), 'OO3': ('NVC', 78), 'OO2': ('NVC', 55), 'EE2': ('NVC', 48), 'OI3': ('NVC', 54), 'OI2': ('Oca', 51), 'OI1': ('NVC', 45), 'OI4': ('NVC', 59), 'EO2': ('NVC', 41), 'IE1': ('Ica', 45), 'IE3': ('Ica', 41), 'IE2': ('NVC', 36), 'IE4': ('NVC', 35), 'IO2': ('NVC', 45), 'OE2': ('NVC', 45), 'IA4': ('Oac', 51), 'EO4': ('NVC', 50), 'IA1': ('Iac', 86), 'IA3': ('Iac', 52), 'IA2': ('Oac', 73), 'EI1': ('NVC', 32), 'IO4': ('NVC', 53), 'II1': ('Iac', 54), 'OA1': ('Ica', 40), 'II3': ('NVC', 65), 'II2': ('Oac', 45), 'EE4': ('NVC', 77), 'IO3': ('NVC', 60), 'EI3': ('Oca', 38), 'IO1': ('Ica', 47), 'EI2': ('Oca', 54), 'OA3': ('Ica', 42), 'AO4': ('Ica', 73), 'AO3': ('Oca', 44), 'AO2': ('Oca', 51), 'AO1': ('Ica', 81), 'EA1': ('Aca', 59), 'EA3': ('Aca', 65), 'EA2': ('Eca', 81), 'EA4': ('Eca', 41), 'EI4': ('NVC', 44), 'AE1': ('Aca', 84), 'AE3': ('Aca', 49), 'AE2': ('Eca', 52), 'AE4': ('Aca', 46), 'AI4': ('Iac', 73), 'AI1': ('Iac', 77), 'AI3': ('Oac', 46), 'AI2': ('Oac', 79), 'EO3': ('NVC', 58), 'AA4': ('Aac', 49), 'EO1': ('NVC', 61), 'OA4': ('Oca', 67), 'AA1': ('Aac', 85), 'OA2': ('Oca', 71), 'AA3': ('NVC', 51), 'AA2': ('Eac', 78)}, {'II4': ('NVC', 63), 'OE3': ('NVC', 42), 'EE1': ('NVC', 54), 'OE1': ('NVC', 34), 'OE4': ('NVC', 49), 'OO4': ('NVC', 71), 'OO1': ('NVC', 48), 'EE3': ('NVC', 81), 'OO3': ('NVC', 73), 'OO2': ('NVC', 52), 'EE2': ('NVC', 56), 'OI3': ('NVC', 58), 'OI2': ('Oca', 53), 'OI1': ('NVC', 47), 'OI4': ('NVC', 57), 'EO2': ('NVC', 42), 'IE1': ('Ica', 43), 'IE3': ('Ica', 37), 'IE2': ('NVC', 34), 'IE4': ('NVC', 35), 'IO2': ('NVC', 44), 'OE2': ('NVC', 52), 'IA4': ('Oac', 50), 'EO4': ('NVC', 50), 'IA1': ('Iac', 88), 'IA3': ('Iac', 47), 'IA2': ('Oac', 79), 'EI1': ('NVC', 33), 'IO4': ('NVC', 52), 'II1': ('Iac', 59), 'OA1': ('Ica', 44), 'II3': ('NVC', 65), 'II2': ('Oac', 46), 'EE4': ('NVC', 81), 'IO3': ('NVC', 61), 'EI3': ('Oca', 39), 'IO1': ('Ica', 43), 'EI2': ('Oca', 50), 'OA3': ('Ica', 45), 'AO4': ('Ica', 77), 'AO3': ('Oca', 42), 'AO2': ('Oca', 45), 'AO1': ('Ica', 72), 'EA1': ('Aca', 63), 'EA3': ('Aca', 61), 'EA2': ('Eca', 78), 'EA4': ('Eca', 38), 'EI4': ('NVC', 43), 'AE1': ('Aca', 79), 'AE3': ('Aca', 52), 'AE2': ('Eca', 52), 'AE4': ('Aca', 44), 'AI4': ('Iac', 66), 'AI1': ('Iac', 75), 'AI3': ('Oac', 46), 'AI2': ('Oac', 75), 'EO3': ('NVC', 53), 'AA4': ('Aac', 48), 'EO1': ('NVC', 54), 'OA4': ('Oca', 68), 'AA1': ('Aac', 87), 'OA2': ('Oca', 77), 'AA3': ('NVC', 55), 'AA2': ('Eac', 73)}]

	#Get predictions from inferences by fitting in the most frequence response

	testPredictions = {}
	total = 0
	tp_person = 0.0
	tn_person = 0.0
	fp_person = 0.0
	fn_person = 0.0
	match = 0
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
		

		set2 = set() # Set of most frequent response by the user for the 2 premises
		set2_withoutArgs = set()
		maxFreq = 0
		for premise in premises:
			mode, freq = mostFrequentResponseDict[premise]
			if freq > maxFreq:
				set2_withoutArgs = set(mode)
			elif freq == maxFreq:
				set2_withoutArgs = set2_withoutArgs|mode

		for predicate in set2_withoutArgs:
			if predicate[:4] == "rall":
				set2.add('rall' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
				set2.add('rall' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif predicate[:3] == "rno":
				set2.add('rno' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
				set2.add('rno' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif predicate[:8] == "rsomenot":
				set2.add('rsomenot' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
				set2.add('rsomenot' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif predicate[:5] == "rsome":
				set2.add('rsome' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
				set2.add('rsome' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif predicate[:4] == "rnvc":
				set2.add('rnvc' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
				

		set3 = set() # Set of most frequent response (overall) for the user
		if mostFrequentResponse == 'rnvc' + str(person):
			set3.add(mostFrequentResponse + '(a' + str(id) + ',c' + str(id) + ')')
		else:
			set3.add(mostFrequentResponse + '(c' + str(id) + ',a' + str(id) + ')')
			set3.add(mostFrequentResponse + '(a' + str(id) + ',c' + str(id) + ')')

		set4 = set() # Set of the most frequent response for the premise in the training data of the fold

		# Most Frequent Reponses in Training fold = [{'all':'rsome', 'no':'rnvc', 'some':'rsome', 'somenot':'rnvc'}]
		
		for premise in premises:
			if premise[:2] == "no" or premise[:7] == "somenot":
				set4.add('rnvc' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')
			elif premise[:3] == "all" or premise[:4] == "some":
				set4.add('rsome' + str(person) + '(c' + str(id) + ',a' + str(id) + ')')
				set4.add('rsome' + str(person) + '(a' + str(id) + ',c' + str(id) + ')')

		set5 = set(['rnvc' + str(person) + '(a' + str(id) + ',c' + str(id) + ')']) # NVC


		set6  = set() # Most Frequent Answer (MFA)
		task1 = testTasks[id][0]
		task2 = testTasks[id][1]
		encodedTask = getEncodedTask(task1, task2)
		#print("Encoded Task of " + str(task1) + ' and ' + str(task2) + 'is \t:' + str(encodedTask))

		
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
		#print('MFA of ' + encodedTask + ' in fold ' + str(fold) + ' is \t: ' + str(mfa))	

		#print('Set1 \t: ' + str(set1))
		#print('Set2 \t: ' + str(set2))
		#print('Set3 \t: ' + str(set3))
		#print('Set4 \t: ' + str(set4))
		#print('Set5 \t: ' + str(set5))
		#print('Set6 \t: ' + str(set6))

		responseNumList = []
		#print(precedence)
		for possibleResponse in possibleResponses:
			responseNumber = 0.0
			if possibleResponse in set1:
				responseNumber += 10**(precedence[0])
			if possibleResponse in set2:
				responseNumber += 10**(precedence[1])
			if possibleResponse in set3:
				responseNumber += 10**(precedence[2])
			if possibleResponse in set4:
				responseNumber += 10**(precedence[3])
			if possibleResponse in set5:
				responseNumber += 10**(precedence[4])
			if possibleResponse in set6:
				responseNumber += 10**(precedence[5])
			responseNumList.append(responseNumber)
			#print(str(id) + '\t:' + possibleResponse + '\t:' + str(responseNumber))


		tp_id = 0.0
		tn_id = 0.0
		fp_id = 0.0
		fn_id = 0.0
		for possibleResponse in possibleResponses:
			if possibleResponse in set1:
				if possibleResponse == testAnswers[id]:
					tp_id += 1
				else:
					fp_id += 1
			else:
				if possibleResponse == testAnswers[id]:
					fn_id += 1
				else:
					tn_id += 1
		
		#print(str(id) + '\t: possibleResponses = ' + str(possibleResponses))
		#print(str(id) + '\t: set1 = ' + str(set1))
		#print(str(id) + '\t: tp = ' + str(tp_id))
		#print(str(id) + '\t: tn = ' + str(tn_id))
		#print(str(id) + '\t: fp = ' + str(fp_id))
		#print(str(id) + '\t: fn = ' + str(fn_id))

		pfPrecision_id = 0.0
		if tp_id + fp_id > 0:
			pfPrecision_id = tp_id/(tp_id+fp_id)
		
		pfRecall_id = 0.0
		if tp_id + fn_id > 0:
			pfRecall_id = tp_id/(tp_id+fn_id)
		
		pfAccuracy_id = (tp_id+tn_id)/(tp_id+tn_id+fp_id+fn_id)

		#print(str(id) + '\t: pfPrecision = ' + str(pfPrecision_id))
		#print(str(id) + '\t: pfRecall = ' + str(pfRecall_id))
		#print(str(id) + '\t: pfAccuracy = ' + str(pfAccuracy_id))

		testPredictions[id] = possibleResponses[max(enumerate(responseNumList), key=lambda x: x[1])[0]]

		#print('Person ' + str(person) + '\t Syllogism ' + str(id) + '\t Predicted ' + testPredictions[id] + '\t Actual ' + testAnswers[id])
	
		if testPredictions[id] == testAnswers[id]:
			match += 1
		total += 1
		tp_person += tp_id
		tn_person += tn_id
		fp_person += fp_id
		fn_person += fn_id

	pfPrecision_person = 0.0
	if tp_person + fp_person > 0:
		pfPrecision_person = tp_person/(tp_person+fp_person)
	
	pfRecall_person = 0.0
	if tp_person + fn_person > 0:
		pfRecall_person = tp_person/(tp_person+fn_person)
	
	pfAccuracy_person = (tp_person+tn_person)/(tp_person+tn_person+fp_person+fn_person)

	#print('Person ' + str(person) + ' : tp = ' + str(tp_person))
	#print('Person ' + str(person) + ' : tn = ' + str(tn_person))
	#print('Person ' + str(person) + ' : fp = ' + str(fp_person))
	#print('Person ' + str(person) + ' : fn = ' + str(fn_person))
	#print('Person ' + str(person) + ' : pfPrecision = ' + str(pfPrecision_person))
	#print('Person ' + str(person) + ' : pfRecall = ' + str(pfRecall_person))
	#print('Person ' + str(person) + ' : pfAccuracy = ' + str(pfAccuracy_person))
	#print('Learned Rule \t: ' + str(rules))
	#print('testSyllogisms \t: ' + str(testSyllogisms))
	#print('testPremises \t: ' + str(testPremises))
	#print('testFacts \t: ' + str(testFacts))
	#print('testAnswers \t: ' + str(testAnswers))
	#print('testPredictions \t: ' + str(testPredictions))
	#print(str(match) + ' matches out of ' + str(total))
	return (match, total, tp_person, tn_person, fp_person, fn_person)



#precedences = list(itertools.permutations([1, 2, 3, 4, 5]))

#precedences = [(6,0,0,0,0,5)]

for precedence in precedences:
	def foldAccuracy(fold):
		matchSum = 0.0
		totalSum = 0.0
		ruleDir = rd + 'Class' + str(fold) + '/'
		
		tp_fold = 0.0
		tn_fold = 0.0
		fp_fold = 0.0
		fn_fold = 0.0

		#for person in range(136, 140):
		for person in range(1, 140):
			(match, total, tp_person, tn_person, fp_person, fn_person) = matchAccuracy(fold, person, ruleDir, precedence)
			matchSum += match
			totalSum += total
			tp_fold += tp_person
			tn_fold += tn_person
			fp_fold += fp_person
			fn_fold += fn_person
		
		pfPrecision_fold = 0.0
		if tp_fold + fp_fold > 0:
			pfPrecision_fold = tp_fold/(tp_fold+fp_fold)
		
		pfRecall_fold = 0.0
		if tp_fold + fn_fold > 0:
			pfRecall_fold = tp_fold/(tp_fold+fn_fold)
		
		pfAccuracy_fold = (tp_fold+tn_fold)/(tp_fold+tn_fold+fp_fold+fn_fold)

		#print('\n')
		#print('Fold ' + str(fold) + ' : tp = ' + str(tp_fold))
		#print('Fold ' + str(fold) + ' : tn = ' + str(tn_fold))
		#print('Fold ' + str(fold) + ' : fp = ' + str(fp_fold))
		#print('Fold ' + str(fold) + ' : fn = ' + str(fn_fold))
		#print('Fold ' + str(fold) + ' : pfPrecision = ' + str(pfPrecision_fold))
		#print('Fold ' + str(fold) + ' : pfRecall = ' + str(pfRecall_fold))
		#print('Fold ' + str(fold) + ' : pfAccuracy = ' + str(pfAccuracy_fold))

		#print('Accuracy for fold ' + str(fold) + ' = ' + str(matchSum) + '/' + str(totalSum) + ' = ' + str(matchSum/totalSum))
		return matchSum/totalSum
	pool = Pool(processes = 10)
	accuracyList = pool.map(foldAccuracy, range(0,10))
	#accuracyList = [foldAccuracy(0)]
	print(str(rulesIndicator) + ': Net Accuracy for precedence ' + str(precedence) + '\t: ' + str(sum(accuracyList)/len(accuracyList)))
