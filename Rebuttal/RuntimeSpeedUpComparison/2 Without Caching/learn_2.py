
from __future__ import print_function
from problog.logic import Var, Term, Constant
from itertools import product
from logging import getLogger
from problog.util import Timer
import logging
from getSQLQuery import getSQLQuery
#from sympy.parsing.sympy_parser import parse_expr
#from sympy import lambdify, symbols
from numpy import errstate
import time
import psycopg2
from math import exp
from eval import getLogList, evaluateExpression
#from numericSS import numericSS         # Numeric Safe Sample
from copy import copy

class KnownError(Exception):
    pass

class LearnEntail(object):

    def __init__(self, data, language, target=None, logger=None, **kwargs):
        self._language = language

        if target is not None:
            try:
                t_func, t_arity = target.split('/')
                arguments = []
                i = 0
                while i < int(t_arity):
                    arguments.append(Var(chr(65+i)))
                    i += 1
                target = Term(t_func, *arguments)
            except Exception:
                raise KnownError('Invalid target specification \'%s\'' % target)

        self._target = target
        self._examples = None
        self._logger = logger

        self._data = data
        self._scores_correct = None

    @property
    def target(self):
        """The target predicate of the learning problem."""
        return self._target

    @property
    def examples(self):
        """The examples (tuple of target arguments) of the learning problem."""
        return self._examples

    @property
    def language(self):
        """Language specification of the learning problem."""
        return self._language

    def load(self, data):
        """Load the settings from a data file.

        Initializes language, target and examples.

        :param data: data file
        :type data: DataFile
        """
        self.language.load(data)  # for types and modes

        if self._target is None:
            try:
                target = data.query('learn', 1)[0]
                target_functor, target_arity = target[0].args
            except IndexError:
                raise KnownError('No target specification found!')
        else:
            target_functor, target_arity = self._target.functor, self._target.args[0]
        target_arguments = [Var(chr(65 + i)) for i in range(0, int(target_arity))]
        self._target = Term(str(target_functor), *target_arguments)

        # Find examples:
        #  if example_mode is closed, we will only use examples that are defined in the data
        #      this includes facts labeled with probability 0.0 (i.e. negative example)
        #  otherwise, the examples will consist of all combinations of values appearing in the data
        #      (taking into account type information)
        example_mode = data.query(Term('example_mode'), 1)
        if example_mode and str(example_mode[0][0]) == 'auto':
            types = self.language.get_argument_types(self._target.functor, self._target.arity)
            values = [self.language.get_type_values(t) for t in types]
            self._examples = list(product(*values))
        elif example_mode and str(example_mode[0][0]) == 'balance':
            # Balancing based on count only
            pos_examples = [r for r in data.query(self._target.functor, self._target.arity)]
            pos_count = len(pos_examples)
            types = self.language.get_argument_types(self._target.functor, self._target.arity)
            values = [self.language.get_type_values(t) for t in types]
            from random import shuffle
            neg_examples = list(product(*values))
            shuffle(neg_examples)
            logger = logging.getLogger(self._logger)
            logger.debug('Generated negative examples:')
            for ex in neg_examples[:pos_count]:
                logger.debug(Term(self._target(*ex).with_probability(0.0)))

            self._examples = pos_examples + neg_examples[:pos_count]
        else:
            self._examples = [r for r in data.query(self._target.functor, self._target.arity)]

        with Timer('Time - computing scores\t\t\t', logger=self._logger):
            self._scores_correct = self._compute_scores_correct()
    
    def getRuleAscii(self, rule):
        # This method is used for standardizing free variables in the rules
        ruleAscii = 64 + self.targetArity
        k = 1
        while k < len(str(rule)):
            if str(rule)[k-1]=="(" or (str(rule)[k-1]=="," and str(rule)[k-2]!=")"):
                if ord(str(rule)[k]) > ruleAscii:
                    ruleAscii = ord(str(rule)[k])
            k = k + 1
        return ruleAscii
    

    def getTotalFreeVars(self, rule):
        # This method is used for standardizing free variables in the rules
        freeVars = 0
        k = 1
        while k < len(str(rule)):
            if str(rule)[k-1]=="(" or (str(rule)[k-1]=="," and str(rule)[k-2]!=")"):
                if str(rule)[k] == "V":
                    j = 1
                    while str(rule)[k+j].isdigit():
                        j += 1
                    freeVars = max(freeVars, int(str(rule)[k+1:k+j]))
                    k += j - 1
            k = k + 1
        return freeVars
    
    def transformFreeVars(self, rule, ascii):
        ruleString = str(rule)
        if ascii <= 64 + self.targetArity:
            return ruleString
        k = 2
        newRuleString = ruleString[0:2]
        while k < len(ruleString):
            if ruleString[k-1]=="(" or (ruleString[k-1]=="," and ruleString[k-2]!=")"):
                if ord(ruleString[k]) <= 64 + self.targetArity:
                    newRuleString = newRuleString + ruleString[k]
                else:
                    newRuleString = newRuleString + chr(ord(ruleString[k]) - 64 - self.targetArity + ascii)
            else:
                newRuleString = newRuleString + ruleString[k]
            k = k + 1
        if ruleString != newRuleString:
            getLogger(self._logger).debug('transformFreeVars: Changing %s to %s' % (ruleString, newRuleString))
        return newRuleString    
    
    
    def incrementFreeVars(self, rule, step):
        ruleString = str(rule)
        if step == 0:
            return ruleString
        k = 2
        newRuleString = ruleString[0:2]
        while k < len(ruleString):
            if ruleString[k-1]=="(" or (ruleString[k-1]=="," and ruleString[k-2]!=")"):
                if ord(ruleString[k]) <= 64 + self.targetArity:
                    newRuleString += ruleString[k]
                elif ruleString[k] == "V":
                    j = 1
                    while ruleString[k+j].isdigit():
                        j += 1
                    freeVar = int(str(rule)[k+1:k+j])
                    newFreeVar = freeVar + step
                    newRuleString += "V" + str(newFreeVar)
                    k += j - 1
                else:
                    #newRuleString = newRuleString + chr(ord(ruleString[k]) - 64 - self.targetArity + ascii)
                    getLogger(self._logger).error('incrementFreeVars: Error changing %s to %s' % (ruleString, newRuleString))
            else:
                newRuleString = newRuleString + ruleString[k]
            k = k + 1
        if ruleString != newRuleString:
            getLogger(self._logger).debug('incrementFreeVars: Changing %s to %s' % (ruleString, newRuleString))
        return newRuleString   
    
    def getCanonicalForm(self, query):
        #Eg: if query = 'author_0_all' then newQuery = 'table0(A,B)'
        newQuery = ""
        tableList = []
        variableList = []
        variableMapping = {}
        i = 0
        while i < len(query):
            start = i
            while query[i] != "(":
                i += 1
            table = query[start:i]
            actualTable = table.split("_")[0]
            argList = table.split("_")[1:]
            allIndices = []
            for j, arg in enumerate(argList):
                if arg == "all":
                    allIndices.append(j)
                
            if table not in tableList:
                tableList.append(table)
            newQuery = newQuery + "table" + str(tableList.index(table)) + "("
            i += 1
            argCount = 0
            while query[i] != ")":
                if query[i] != ",":
                    if query[i] == "V":
                        j = 1
                        while query[i+j].isdigit():
                            j += 1
                        var = query[i:i+j]
                        i += j - 1
                    else:
                        var = query[i]
                    if var not in variableList: #Change
                        variableList.append(var)
                    '''
                    newQuery = newQuery + chr(65+variableList.index(query[i]))
                    if chr(65+variableList.index(query[i])) not in variableMapping:
                        if actualTable == "p":
                            variableMapping[chr(65+variableList.index(query[i]))] = "p"
                        elif "all" not in argList:
                            variableMapping[chr(65+variableList.index(query[i]))] = "all"
                        else:
                            variableMapping[chr(65+variableList.index(query[i]))] = self.predicateDict[actualTable][allIndices[argCount]]
                    '''
                    newQuery = newQuery + 'V' + str(variableList.index(var))
                    if 'V' + str(variableList.index(var)) not in variableMapping:
                        if actualTable == "p":
                            variableMapping['V' + str(variableList.index(var))] = "p"
                        elif "all" not in argList:
                            variableMapping['V' + str(variableList.index(var))] = "all"
                        else:
                            variableMapping['V' + str(variableList.index(var))] = self.predicateDict[actualTable][allIndices[argCount]]
                    
                    argCount += 1
                else:
                    newQuery = newQuery + ","
                i += 1
                
            newQuery = newQuery + ")"    
            
            if i + 1 < len(query):
                i += 1
                
                if query[i] == "," and query[i-1] == ")":
                    newQuery = newQuery + ","
                
                if i + 2 < len(query) and query[i:i+3] == " v ":
                    newQuery = newQuery + " v "
                    i += 3
                    continue
            
            i += 1    
        return (newQuery, tableList, variableMapping)
    
    def executeCanonicalSQLQuery(self, SQLQuery, tableList, variableMapping):
        if SQLQuery in ["Failed to parse", None, "Query is unsafe"]:
            return None
        
        #SQLQuery = "\n select COALESCE(q9.pUse,<log(exp(y_C*log(-z_table2 + 1)) + exp(y_D*log(-z_table3 + 1)) - exp(y_C*log(-z_table2 + 1) + y_D*log(-z_table3 + 1)))>)+COALESCE(q18.pUse,<log(exp(y_A*log(-z_table0 + 1)) + exp(y_B*log(-z_table1 + 1)) - exp(y_A*log(-z_table0 + 1) + y_B*log(-z_table1 + 1)))>) as pUse from (\n select l1prod_n(COALESCE(q4.pUse, <y_C*log(-z_table2 + 1)>),COALESCE(q8.pUse, <y_D*log(-z_table3 + 1)>)) as pUse from (\n select pUse + <log(-z_table2 + 1)> * (<y_C> - ct ) as pUse from (\n select l_ior_n(COALESCE(pUse,0)) as pUse, count(*) as ct from (\n select <table2>.v0 as c1, ln(1-p) as pUse from <table2>  \n) as q2 \n  \n) as q3 \n\n) as q4 \n FULL OUTER JOIN (\n select pUse + <log(-z_table3 + 1)> * (<y_D> - ct ) as pUse from (\n select l_ior_n(COALESCE(pUse,0)) as pUse, count(*) as ct from (\n select <table3>.v0 as c2, ln(1-p) as pUse from <table3>  \n) as q6 \n  \n) as q7 \n\n) as q8 \n ON TRUE) as q9 \n FULL OUTER JOIN (\n select l1prod_n(COALESCE(q13.pUse, <y_A*log(-z_table0 + 1)>),COALESCE(q17.pUse, <y_B*log(-z_table1 + 1)>)) as pUse from (\n select pUse + <log(-z_table0 + 1)> * (<y_A> - ct ) as pUse from (\n select l_ior_n(COALESCE(pUse,0)) as pUse, count(*) as ct from (\n select <table0>.v0 as c3, ln(1-p) as pUse from <table0>  \n) as q11 \n  \n) as q12 \n\n) as q13 \n FULL OUTER JOIN (\n select pUse + <log(-z_table1 + 1)> * (<y_B> - ct ) as pUse from (\n select l_ior_n(COALESCE(pUse,0)) as pUse, count(*) as ct from (\n select <table1>.v0 as c4, ln(1-p) as pUse from <table1>  \n) as q15 \n  \n) as q16 \n\n) as q17 \n ON TRUE) as q18 \n ON true"
        
        
        #tableList = ['athleteledsportsteam_0_0', 'p_0', 'athleteplayssport_0_all', 'athleteledsportsteam_0_all']
        #variableMapping = {'A': 'athlete', 'C': 'athlete', 'B': 'p', 'D': 'athlete'}
        
        prob = None
        trueSQLQuery = ""
        i = 0
        #z = symbols('z')
        #y = symbols('y')
        while i < len(SQLQuery):
            if SQLQuery[i] == "<":
                start = i + 1
                while SQLQuery[i] != ">":
                    i += 1
                expression = SQLQuery[start:i]
                
                trueExpression = ""
                if expression[0:5] == "table":
                    tableNumber = int(expression[5:])
                    trueExpression = tableList[tableNumber]
                else:
                    # Replace Domains and Lambdas appropriately
                    # Eg:z_table2 >> z_author_0_0 >> z_author
                    # Eg:y_A >> y_researcher; y_B >> y_paper >> Actual value of number of different constants as 'papers'
                    substitutedExpression = ""
                    j = 0
                    lastEnd = 0
                    while j < len(expression)-1:
                        if expression[j:j+2] == "z_": #Lambda identified
                            substitutedExpression = substitutedExpression + expression[lastEnd:j] 
                            start = j
                            j += 2
                            while (expression[j].isalpha() or expression[j].isdigit()) and j < len(expression):
                                j += 1
                            tableString = expression[start+2:j]
                            tableNumber = int(tableString[5:])
                            table = tableList[tableNumber]
                            actualTable = table.split('_')[0]
                            if actualTable == "p":
                               #substitutedExpression = substitutedExpression + "0"
                               substitutedExpression = substitutedExpression + str(self.lams[table])
                            else: 
                                substitutedExpression = substitutedExpression + str(self.lams[actualTable])
                            lastEnd = j
                            continue
                        elif expression[j:j+2] == "y_": #Domain identified
                            substitutedExpression = substitutedExpression + expression[lastEnd:j] 
                            start = j
                            
                            #var = expression[start+2:start+3]
                            var = expression[start+2]
                            k = 3
                            while expression[start+k].isdigit():
                                var = var + expression[start+k] 
                                k += 1
                                if start + k == len(expression):
                                    break 
                            j += k
                            
                            if variableMapping[var] in ["p", "all"]:
                                domain = 1
                            else:
                                domain = len(self.constantDict[variableMapping[var]])
                            substitutedExpression = substitutedExpression + str(domain)
                            #j += 3
                            lastEnd = j
                            continue
                        j += 1
                    substitutedExpression = substitutedExpression + expression[lastEnd:]
                    
                    # To Do: Evaluate 'substitutedExpression' based on actual values of author.lam, location.lam, researcher.dom, paper.dom, university.dom
                    with errstate(divide='ignore', invalid='ignore'):
                        value = evaluateExpression(substitutedExpression)
                    if str(value) != '-inf':
                        trueExpression = str(value)
                    else:
                        trueExpression = '-999999999999'
                    
                trueSQLQuery = trueSQLQuery + trueExpression
            else:
                trueSQLQuery = trueSQLQuery + SQLQuery[i]
            
            i += 1
        
        try:
            self.cursor.execute(trueSQLQuery)
            output = self.cursor.fetchall()
                
            if output[0][0] not in ["Failed to parse", None, "Query is unsafe"]:
                if self.open_world:
                    prob = 1 - exp(float(output[0][0]))
                else:
                    prob = output[0][0]
                
        except psycopg2.Error as e:
            getLogger(self._logger).log(8, "Execute SQL >> SQL error \t: " + e.pgerror[:-1].replace('\n','\t'))
            getLogger(self._logger).warning("Execute SQL >> Uninstantiated Query \t: " + SQLQuery) 
            getLogger(self._logger).warning("Execute SQL >> Instantiated Query \t: " + trueSQLQuery)
            
        return prob
    
    def partitionUCQ(self, query):
        conjunctList = query.split(' v ')
        #newConjunctList = copy(conjunctList)
        predicateDict = {}
        querySetList = []
        idList = []
        mergeList = []
        
        for conjunct in conjunctList:
            # Get all literals of this conjunct into a Literal List
            i = 2
            literalList = []
            start = 0
            while i < len(conjunct):
                if conjunct[i] == ',' and conjunct[i-1] == ')':
                    literalList.append(conjunct[start:i])
                    start = i + 1
                elif conjunct[i] == ')' and i == len(conjunct) - 1:
                    literalList.append(conjunct[start:i])
                i += 1
            
            # Assign an id to this conjunct
            idSet = set()
            id = None
            for literal in literalList:
                predicate = literal.split('(')[0]
                if predicate not in predicateDict:
                    if id == None:
                        id = len(predicateDict)
                        predicateDict[predicate] = len(predicateDict)
                    else:
                        predicateDict[predicate] = id
                else:
                    if id == None:
                        id = predicateDict[predicate]
                        idSet.add(id)
                    else:
                        idSet.add(id)
                        idSet.add(predicateDict[predicate])
            idList.append(id)
            if len(idSet) > 1:
                mergeList.append(idSet)
        
        if len(mergeList) > 0:
            # Update all the ids in the IdList on the basis of MergeList
            minList = []
            for idSet in mergeList:
                minList.append(min(idSet))
            
            a = zip(minList, mergeList)
            b = sorted(a, reverse=True)
            minList, mergeList = zip(*b)
            
            for minId, idSet in zip(minList, mergeList):
                for id in idSet:
                    if id != minId:
                        idList = [minId if x==id else x for x in idList]
        
        # Make NewConjunctList on the basis of IdList
        newConjunctList = []
        newConjunctIds = []
        for id, conjunct in zip(idList, conjunctList):
            if id not in newConjunctIds:
                newConjunctList.append(conjunct)
                newConjunctIds.append(id)
            else:
                newConjunctList[newConjunctIds.index(id)] += ' v ' + conjunct
        '''
        for idSet in mergeList:    
            # Merge these id's in the idSet together
            # Merge the rules from conjucntList.index whose id's are present in the idSet
            minId = min(idSet)
            minConjunctNumber = idList.index(minId)
            
            for id in idSet:
                if id != minId:
                    conjunctNumber = idList.index(id)
                    newConjunctList[minConjunctNumber] = newConjunctList[minConjunctNumber] + ' v ' + newConjunctList[conjunctNumber]
                    newConjunctList.pop(conjunctNumber)
                    idList.pop(conjunctNumber)
        '''
        return newConjunctList
    
    def getQueryProbability(self, query):
        #query = "r1(A) v r2(B),r3(C) v r4(D),r5(E),r3(F) v r6(G),r1(H),r7(I)"  #Test
        
        if query in ["", "true"]:
            return 1.0
        
        conjunctList = query.split(' v ')
        if len(conjunctList) > 1:
            
            newConjunctList = self.partitionUCQ(query)
            
            unsafe = True
            mainProbability = 1.0
            for conjunct in newConjunctList:
                probability = self.getConjunctProbability(conjunct)
                if probability != None:
                    mainProbability = mainProbability*(1 - probability)
                    unsafe = False
            
            if unsafe == False:
                mainProbability = 1 - mainProbability
            else:
                mainProbability = None
        else:
            mainProbability = self.getConjunctProbability(query)
        
        if  mainProbability < 1e-15:
            mainProbability = 0.0
        return mainProbability
    
    def getConjunctProbability(self, query):
        '''canonicalQuery, tableList, variableMapping = self.getCanonicalForm(query)
        canonicalSQLQuery = ""
        if canonicalQuery in self.queryDict:        
            canonicalSQLQuery = self.queryDict[canonicalQuery]
        else:
            time_start = time.time()
            canonicalSQLQuery = getSQLQuery(canonicalQuery, self.open_world)
            self._time_getSQLQuery = self._time_getSQLQuery + time.time() - time_start
            self._stats_getSQLQuery += 1
            self.queryDict[canonicalQuery] = canonicalSQLQuery
        
        prob = self.executeCanonicalSQLQuery(canonicalSQLQuery, tableList, variableMapping)
        return prob'''
        SQLQuery = getSQLQuery(query, self.open_world)
        self.cursor.execute(SQLQuery)
        output = self.cursor.fetchall()
            
        if output[0][0] not in ["Failed to parse", None, "Query is unsafe"]:
            if self.open_world:
                prob = 1 - exp(float(output[0][0]))
            else:
                prob = output[0][0]
        return prob

    def checkIsomorphicRule(self, rule):
        if rule in ["", "true", "fail", "false"]:
            return False
        
        condition = False
        canonicalRule = ""
        variableList = []
        i = 0
        
        while i < len(rule):
            start = i
            while rule[i] != "(":
                i += 1
            canonicalRule = canonicalRule + rule[start:i] + "("
            i += 1
            while rule[i] != ")":
                if rule[i] != ",":
                    if ord(rule[i]) < 65 + self.targetArity:
                        canonicalRule = canonicalRule + rule[i]
                    else:
                        if rule[i] not in variableList:
                            variableList.append(rule[i])
                        canonicalRule = canonicalRule + chr(65 + self.targetArity + variableList.index(rule[i]))
                else:
                    canonicalRule = canonicalRule + ","
                i += 1
            canonicalRule = canonicalRule + ")"    
            
            if i + 1 < len(rule):
                i += 1
                
                if rule[i] == "," and rule[i-1] == ")":
                    canonicalRule = canonicalRule + ","
                
                if i + 2 < len(rule) and rule[i:i+3] == " v ":
                    canonicalRule = canonicalRule + " v "
                    i += 3
                    continue
            i += 1    
        
        oldUCQ = canonicalRule.split(' v ')
        newUCQ = []
        for conjunct in oldUCQ:
            clauseList = conjunct.split('),')
            clauseList[-1] = clauseList[-1][:-1]
            sortedClause = list(set(clauseList))
            sortedClause.sort()
            newUCQ.append('),'.join(sortedClause))
            newUCQ[-1] = newUCQ[-1] + ')'
        sortedUCQ = list(set(newUCQ))
        sortedUCQ.sort()
        newCanonicalRule = ' v '.join(sortedUCQ)
        
        #print("canonicalRule \t= " + newCanonicalRule)
        
        if newCanonicalRule in self.canonicalRuleList:
            condition = True
            getLogger(self._logger).log(9, "Rule Isomorphic\t\t\t\t\t: " + rule)
            getLogger(self._logger).log(9, "Canonical Rule\t\t\t\t\t: " + newCanonicalRule)
        else:
            self.canonicalRuleList.append(newCanonicalRule)
            
        return condition
    
    def checkUnsafeRule(self, ruleQuery):
        if ruleQuery in ["", "true", "fail", "false"]:
            return False
        
        condition = False
        time_start = time.time()
        ruleSQLQuery = getSQLQuery(ruleQuery, self.open_world)
        self._time_getSQLQuery = self._time_getSQLQuery + time.time() - time_start
        self._stats_getSQLQuery += 1
        
        if ruleSQLQuery == "Query is unsafe":
            getLogger(self._logger).log(9, "Rule unsafe\t\t\t\t\t\t:" + ruleQuery)
            condition = True
            
        return condition
    
    def _compute_scores_correct(self):
        """Computes the score for each example."""
        pl = self._data._database._ClauseDB__nodes
        examples = {}
        for item in pl:
            if item.functor == self.target.functor and hasattr(item, 'probability'):
                examples[item.args] = item.probability
                
        scores_correct = []
        for j, i in enumerate(self.examples):
            if examples.has_key(i):
                scores_correct.append(float(examples[i]))
                if float(examples[i]) < self.negativeThreshold:
                    self.negatives.add(j)
            else:
                # This branch will be accessed when 'example_mode(auto).' is given in input file. So actual number of examples would be a lot more.
                scores_correct.append(0.0)
                #print("Error: " + str(i) + " is not present in the list of examples in self._data._database._ClauseDB_nodes")
        
        return scores_correct
    
    def _compute_scores_predict(self, rule):
        return self._compute_scores_predict_ground(rule)

    def _compute_scores_predict_ground(self, rule):
        # Don't evaluate examples that are guaranteed to evaluate to 0.0 or 1.0.
        set_one = []
        set_zero = []
        if rule.previous is not None:
            set_one = [i for i, s in enumerate(rule.previous.scores) if s > 1 - 1e-8]
        if rule.parent is not None:
            set_zero = [i for i, s in enumerate(rule.parent.scores) if s < 1e-8]

        to_eval = list(set(range(0, self.totalExamples)) - set(set_one) - set(set_zero))
        to_eval.sort()
        examples = [self.examples[i] for i in to_eval]

        ruleString = (str(rule)).replace(" ", "")
        bodyString = ruleString.split(":-")[1].replace("\\+", "~")
        
        if bodyString == "true":
            scores_predict = [1] * self.totalExamples
            return scores_predict
        elif bodyString in ["false","fail"]:
            scores_predict = rule.previous.scores
            return scores_predict
        else:
            fullBodyString = ""
            temp = rule
            #maxAscii = 64 + self.targetArity
            totalFreeVars = 0
            count = 0
            while temp.previous is not None:
                body = (str(temp)).replace(" ", "").split(":-")[1].replace("\\+", "~")
                if body in ["", "true", "false", "fail"]:
                    temp = temp.previous
                    continue
                #hypothesisAscii = self.getRuleAscii(body)
                hypothesisFreeVars = self.getTotalFreeVars(body)
                
                if fullBodyString == "":
                    #maxAscii = hypothesisAscii
                    totalFreeVars = hypothesisFreeVars
                    fullBodyString = body
                else:
                    #if hypothesisAscii > 64 + self.targetArity:
                    if hypothesisFreeVars > 0:
                        #maxAscii = maxAscii + hypothesisAscii - 64 - self.targetArity
                        totalFreeVars += hypothesisFreeVars
                        #newBody = self.transformFreeVars(body, maxAscii - self.targetArity + 1)
                        newBody = self.incrementFreeVars(body, hypothesisFreeVars)
                        fullBodyString = fullBodyString + ' v ' + newBody
                    else:
                        fullBodyString = fullBodyString + ' v ' + body 
                temp = temp.previous
            
            '''
            # fullBodyString = "athleteledsportsteam(C,B),teamplaysinleague(B,D) v teamplaysinleague(B,E),athleteplaysinleague(A,E)"
            # freeBodyString = "athleteledsportsteam(C),teamplaysinleague(D) v teamplaysinleague(E),athleteplaysinleague(E)"
            
            freeBodyString = fullBodyString
            for i in range(0, self,targetArity):
                var = chr(65 + i)
                freeBodyString = freeBodyString.replace(var, "")
            
            freeBodyString = freeBodyString.replace(",,", ",")
            freeBodyString = freeBodyString.replace(",)", ")")
            freeBodyString = freeBodyString.replace("(,", "(")
            '''
                
            scores_predict = [0.0] * self.totalExamples
            predicationError = False
            
            #if not self.checkIsomorphicRule(fullBodyString) and not self.checkUnsafeRule(freeBodyString):
            if not self.checkIsomorphicRule(fullBodyString):
                
                for i, example in zip(to_eval, examples):
                    #ruleAscii = maxAscii
                    freeVars = totalFreeVars
                    
                    instantiatedQueryString = ""
                    j = 0
                    while j < len(bodyString): 
                        negation = False
                        if bodyString[j] == "~":
                            negation = True
                            j = j + 1
                            continue
                        if bodyString[j-1] == ")" and bodyString[j] == ",":
                            j += 1
                            continue
                        start = j
                        while bodyString[j] != "(":
                            j += 1
                        newTable = bodyString[start:j]   
                        replacePredicate = False
                        startRound = j
                        j += 1
                        whereList = []
                        l = 0
                        while bodyString[j] != ")":
                            if bodyString[j] != ",": 
                                if ord(bodyString[j]) <= 64 + self.targetArity:
                                    replacePredicate = True
                                    baseNumber = ord(bodyString[j]) - 65
                                    base = self.predicateDict[self.targetPredicate][baseNumber]
                                    #value = self.targetFactList[i][baseNumber]
                                    value = example[baseNumber]
                                    newTable = newTable + "_" + str(self.universalConstantId[value])
                                    whereList.append((l,self.universalConstantId[value]))
                                else:
                                    newTable = newTable + "_all"
                                l += 1
                            j += 1
                        
                        endRound = j
                        
                        if replacePredicate == True: #This means that the literal contains at least 1 fixed variable that needs instantiation
                        
                            #Replace 'bodyString[left:k+1]' by only free variables
                            # If variableString = '(A,B,C)' ==> '(C)'
                            # If variableString = '(A,B)' or '(A)' ==> then don't add the newTable. Instead execute a query to get the probability of a tuple when A and B are instantiated.
                            
                            tableNames = newTable.split("_")
                            table = tableNames[0]
                            argList = tableNames[1:]
                            varList = bodyString[startRound+1:endRound].split(",")
                            reallyReplacePredicate = False
                            instantiatedLiteral = ""
                            
                            varString = ""
                            for k, arg in enumerate(argList):
                                if arg == "all":
                                    reallyReplacePredicate = True
                                    if varString == "":
                                        varString = varList[k]
                                    else:
                                        varString = varString + "," + varList[k]
                            instantiatedLiteral = newTable + "(" + varString + ")"
                                
                            if newTable not in self.previousInstantiatedTableSet:
                                if reallyReplacePredicate == True: #Eg: '(A,B,C)' ==> '(C)'
                                    selectString = ""
                                    whereString = ""
                                    count = 0
                                    for k,arg in enumerate(argList):
                                        if arg != "all":
                                            if whereString == "":
                                                whereString = "v" + str(k) + " = " + str(arg)
                                            else:
                                                whereString = whereString + " AND v" + str(k) + " = " + str(arg)
                                        else:
                                            if selectString == "":
                                                selectString = "v" + str(k) + " as v" + str(count)
                                            else:
                                                selectString = selectString + ", v" + str(k) + " as v" + str(count)
                                            count += 1
                                    
                                    if selectString != "":
                                        selectString = selectString + ", p"
                                        
                                        #getLogger(self._logger).log(8, 'Probfoil: CREATE TABLE IF NOT EXISTS %s AS (SELECT %s FROM %s WHERE %s);' % (newTable, selectString, table, whereString))
                                        self.cursor.execute("CREATE TABLE IF NOT EXISTS " + newTable + " AS (SELECT " + selectString + " FROM " + table + " WHERE " + whereString + ");")
                                         
                                    self.previousInstantiatedTableSet.add(newTable)
                                
                                
                                else:  #This means that the literal contains only fixed variables which needs instantiation, Eg: (A,B) or (A)
                                    
                                    #Calculate the probability of a tuple from a fully instantiated table name
                                    #'author_0_1' ==> Create and execute a psql query which subsets 'author' on v0 = 0 and v1 = 1 and then aggregate by ior_n 
                                    
                                    whereString = ""
                                    for k, arg in enumerate(argList):    
                                        if whereString == "":
                                            whereString = "v" + str(k) + " = " + str(arg)
                                        else:
                                            whereString = whereString + " AND v" + str(k) + " = " + str(arg)
                                    
                                    self.cursor.execute("Select ior_n(p) from " + table + " where " + whereString +";")
                                    prob = self.cursor.fetchone()[0]
                                    
                                    # Create a table by the name 'newTable' which will have exactly 1 free variable
                                    self.cursor.execute("CREATE TABLE IF NOT EXISTS " + newTable + " (v0 integer, p double precision);")
                                    self.cursor.execute("INSERT INTO " + newTable + " VALUES (0, "+str(prob)+");")
                                
                            
                                    #instantiatedLiteral = newTable + "(" + chr(ruleAscii + 1) +")"
                                    #ruleAscii += 1
                                    instantiatedLiteral = newTable + "(V" + str(freeVars) +")"
                                    freeVars
                                
                            if instantiatedQueryString == "":
                                if negation == False:
                                    instantiatedQueryString = instantiatedLiteral
                                else:
                                    instantiatedQueryString = "~" + instantiatedLiteral
                            else:
                                if negation == False:
                                    instantiatedQueryString = instantiatedQueryString + "," + instantiatedLiteral
                                else:
                                    instantiatedQueryString = instantiatedQueryString + ",~" + instantiatedLiteral
                        else:
                            if instantiatedQueryString == "":
                                if negation == False:
                                    instantiatedQueryString = bodyString[start:endRound+1]
                                else:
                                    instantiatedQueryString = "~" + bodyString[start:endRound+1]
                            else:
                                if negation == False:
                                    instantiatedQueryString = instantiatedQueryString + "," + bodyString[start:endRound+1]
                                else:
                                    instantiatedQueryString = instantiatedQueryString + ",~" + bodyString[start:endRound+1]
                        j = j + 1
                    
                    if instantiatedQueryString == "":
                        prob = 1
                        if self.querySS[i] != "":
                            fullString = self.querySS[i]
                        else:
                            fullString = "true"
                    else:
                        if self.querySS[i] != "":
                            #hypothesisAscii = self.getRuleAscii(self.querySS[i])
                            #newQueryString = self.transformFreeVars(instantiatedQueryString, hypothesisAscii)
                            
                            hypothesisFreeVars = self.getTotalFreeVars(self.querySS[i])
                            newQueryString = self.incrementFreeVars(instantiatedQueryString, hypothesisFreeVars)
                            fullString = self.querySS[i] + ' v ' + newQueryString
                        else: 
                            fullString = instantiatedQueryString
                        
                        prob = self.getQueryProbability(fullString)
      
                    if prob in ["Failed to parse", None, "Query is unsafe"]:  
                        getLogger(self._logger).log(8, '%d.\t%s\t: %s\t= %s' % (i, fullString, str(example), str(prob)))
                        scores_predict = rule.previous.scores
                        predicationError = True
                        break
                    else: 
                        scores_predict[i] = prob     # Not Rounding to 12 decimal places to avoid float precision error
                        if scores_predict[i] <= self.tolerance:
                            scores_predict[i] = 0.0
                        elif scores_predict[i] >= 1 - self.tolerance:
                            scores_predict[i] = 1.0
                        getLogger(self._logger).log(7, '%s\t: %d.\t%s\t= %s' % (fullString, i, str(example), str(scores_predict[i])))

            if predicationError == False:
                for i in set_one:
                    scores_predict[i] = 1.0
        
            return scores_predict

    def _compute_scores_predict_again(self, rule):
        # This method is used when Lambda is just updated and the probabilistic weights of all the rules are getting recalibrated 
        
        ruleString = (str(rule)).replace(" ", "")
        bodyString = ruleString.split(":-")[1].replace("\\+", "~")
        
        if bodyString == "true":
            scores_predict = [1] * self.totalExamples
            return scores_predict
        elif bodyString in ["false","fail"]:
            scores_predict = rule.previous.scores
            return scores_predict
        else:
            scores_predict = [0.0] * self.totalExamples
            for i, example in enumerate(self.examples):
                
                prob = self.getQueryProbability(self.querySS[i])
                if prob in ["Failed to parse", None, "Query is unsafe"]:  
                    getLogger(self._logger).log(8, '%d.\t%s\t: %s\t= %s' % (i, self.querySS[i], str(example), str(prob)))
                    scores_predict[i] = rule.previous.scores[i]
                else: 
                    scores_predict[i] = prob     # Not Rounding to 12 decimal places to avoid float precision error
                    if scores_predict[i] <= self.tolerance:
                        scores_predict[i] = 0.0
                    elif scores_predict[i] >= 1 - self.tolerance:
                        scores_predict[i] = 1.0
                    getLogger(self._logger).log(7, '%s\t: %d.\t%s\t= %s' % (self.querySS[i], i, str(example), str(scores_predict[i])))
        
            return scores_predict


    # def _compute_scores_predict_nonground(self, rule):
    #     """Evaluate the current rule using a non-ground query.
    #
    #       This is not possible because we can't properly distribute the weight of the
    #        non-ground query over the possible groundings.
    #       So this only works when all rules in the ruleset are range-restricted.
    #
    #     :param rule:
    #     :return:
    #     """
    #     functor = 'eval_rule'
    #     result = self._data.evaluate(rule, functor=functor, arguments=[self._target.args])
    #
    #     types = None
    #     values = None
    #
    #     from collections import defaultdict
    #     from problog.logic import is_variable
    #
    #     index = defaultdict(dict)
    #     for key, value in result.items():
    #         if not key.is_ground():
    #             if values is None:
    #                 types = self.language.get_argument_types(self._target.functor, self._target.arity)
    #                 values = [len(self.language.get_type_values(t)) for t in types]
    #             c = 1
    #
    #             gi = []
    #             gk = []
    #             for i, arg, vals in zip(range(0, len(key.arity)), key.args, values):
    #                 if is_variable(key.args):
    #                     c *= vals
    #                 else:
    #                     gi.append(i)
    #                     gk.append(arg)
    #             import math
    #             p = 1.0 - value ** (1.0 / c)
    #             p = 1 - math.exp(math.log(1 - value) / c)
    #             index[tuple(gi)][tuple(gk)] = [p, c]
    #
    #     scores_predict = [0.0]
    #     for i, arg in enumerate(self.examples):
    #         for gi, idx in index.items():
    #             gk = tuple(arg[j] for j in gi)
    #             res = idx.get(gk, [0.0, 0])
    #             scores_predict
    #
    #     print (rule, result)
    #     print (self.examples)


class CandidateSet(object):

    def __init__(self):
        pass

    def push(self, candidate):
        raise NotImplementedError('abstract method')

    def pop(self):
        raise NotImplementedError('abstract method')

    def __bool__(self):
        raise NotImplementedError('abstract method')


class BestCandidate(CandidateSet):

    def __init__(self, candidate=None):
        CandidateSet.__init__(self)
        self.candidate = candidate

    def push(self, candidate):
        if self.candidate is None or self.candidate.score_cmp < candidate.score_cmp:
            self.candidate = candidate

    def pop(self):
        if self.candidate is not None:
            return self.candidate
        else:
            raise IndexError('Candidate set is empty!')

    def __bool__(self):
        return not self.candidate is None


class CandidateBeam(CandidateSet):

    def __init__(self, size):
        CandidateSet.__init__(self)
        self._size = size
        self._candidates = []

    def _bottom_score(self):
        if self._candidates:
            return self._candidates[-1].score_cmp
        else:
            return -1e1000

    def _insert(self, candidate):
        for i, x in enumerate(self._candidates):
            if x.is_equivalent(candidate):
                raise ValueError('duplicate')
            elif x.score_cmp < candidate.score_cmp:
                self._candidates.insert(i, candidate)
                return False
        self._candidates.append(candidate)
        return True

    def push(self, candidate):
        """Adds a candidate to the beam.

        :param candidate: candidate to add
        :return: True if candidate was accepted, False otherwise
        """
        if len(self._candidates) < self._size or candidate.score_cmp > self._bottom_score():
            #  We should add it to the beam.
            try:
                is_last = self._insert(candidate)
                if len(self._candidates) > self._size:
                    self._candidates.pop(-1)
                    return not is_last
            except ValueError:
                return False
            return True
        return False

    def pop(self):
        return self._candidates.pop(0)

    def __bool__(self):
        return bool(self._candidates)

    def __nonzero__(self):
        return bool(self._candidates)

    def __str__(self):
        s = '====================================================================\n'
        for candidate in self._candidates:
            s += str(candidate) + '\t' + str(candidate.score) + '\n'
        s += '====================================================================\n'
        return s
