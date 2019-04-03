from problog.program import PrologFile, PrologString
from problog.core import ProbLog
from problog import get_evaluatable

from probfoil import learn
from probfoil.data import DataFile
from probfoil.probfoil import ProbFOIL2

import sys
from collections import Counter 
from multiprocessing import Process, Pool
import itertools

#fold = sys.argv[1]
#person = sys.argv[2]
mainDir = sys.argv[1]

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
			pf = open(ruleDir + '/cv' + str(fold) + '_' + response + str(person) + '.out').readlines()[12:-7]
			if pf == []:
				emptyResponses.append(response)
			for rule in pf:
				rules.append(rule[:-1]+'.')
		

	testFile = DataFile(PrologFile(mainDir + "/cv" + str(fold) + "_test_" + str(person) + ".pl"))._database._ClauseDB__nodes

	testFacts = []
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
				else:
					testPremises[id].add(str(line.functor))


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

	problogQuery = '\n'.join(init)
	problogQuery += '\n'
	problogQuery += '\n'.join([str(item[0])+str(item[1])+'.' for item in testFacts])
	problogQuery += '\n'
	problogQuery += '\n'.join(rules)
	problogQuery += '\n'
	problogQuery += '\n'.join(queries)

	p = PrologString(problogQuery)
	inferences = get_evaluatable().create_from(p).evaluate()

	inferenceDict = {}
	for term, probability in inferences.items():
		inferenceDict[str(term)] = probability
		#if probability > 1 - 1e-8:
			#print('Fact inferred \t:' + str(term))
	#Get predictions from inferences by fitting in the most frequence response

	testPredictions = {}
	total = 0
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


		set1 = set() # Set of all possible responses with 1 probability.
		for possibleResponse in possibleResponses:
			if possibleResponse.split('(')[0][:-1*len(str(person))] in emptyResponses:
				continue
			if possibleResponse not in inferenceDict:
				print('Error:' + possibleResponse + ' not in the inference dict: ' + str(inferenceDict))
			if inferenceDict[possibleResponse] > 1 - 1e-8:
				set1.add(possibleResponse)
		
		#TO DO: Add arguments to the premises in set2
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

		#print('Set1 \t: ' + str(set1))
		#print('Set2 \t: ' + str(set2))
		#print('Set3 \t: ' + str(set3))
		#print('Set4 \t: ' + str(set4))
		#print('Set5 \t: ' + str(set5))

		responseNumList = []
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
				responseNumber += 1e0**(precedence[4])
			responseNumList.append(responseNumber)
			#print(str(id) + '\t:' + possibleResponse + '\t:' + str(responseNumber))

		testPredictions[id] = possibleResponses[max(enumerate(responseNumList), key=lambda x: x[1])[0]]

		if testPredictions[id] == testAnswers[id]:
			match += 1
		total += 1

	#print('Learned Rule \t: ' + str(rules))
	#print('testSyllogisms \t: ' + str(testSyllogisms))
	#print('testPremises \t: ' + str(testPremises))
	#print('testFacts \t: ' + str(testFacts))
	#print('testAnswers \t: ' + str(testAnswers))
	#print('testPredictions \t: ' + str(testPredictions))
	#print(str(match) + ' matches out of ' + str(total))
	return (match, total)

def foldAccuracy(fold):
	print("precedence = " + str(precedence))
	matchSum = 0.0
	totalSum = 0.0
	ruleDir = 'Class' + str(fold) + '/'
	for person in range(1, 140):
		(match, total) = matchAccuracy(fold, person, ruleDir, precedence)
		matchSum += match
		totalSum += total
	#print('Accuracy for fold ' + str(fold) + ' = ' + str(matchSum) + '/' + str(totalSum) + ' = ' + str(matchSum/totalSum))
	return matchSum/totalSum

#precedences = list(itertools.permutations([1, 2, 3, 4, 5]))

#precedences = [(5,4,3,2,1), (5,3,4,2,1), (5,4,2,3,1), (5,2,4,3,1), (5,2,3,4,1), (5,3,2,4,1), (4,3,2,1,5), (4,2,3,1,5), (4,2,1,3,5), (4,3,1,2,5), (4,1,2,3,5), (4,1,3,2,5)]
precedences = [(5,4,3,2,1)]

def precedenceAccuracy(precedence):
	with Pool(processes = 10) as pool2:
		accuracyList = pool2.map(foldAccuracy, range(0,10))
	print('Net Accuracy for precedence ' + str(precedence) + '\t: ' + str(sum(accuracyList)/len(accuracyList)))

with Pool() as pool1:
	results = pool1.map(precedenceAccuracy, precedences)
