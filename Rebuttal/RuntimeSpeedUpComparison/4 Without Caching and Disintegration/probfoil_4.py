"""Implementation of the OpenProbFOIL algorithm.
"""

from __future__ import print_function
from problog.program import PrologFile
from problog.logic import term2str, Term, Var
from data import DataFile
from language import TypeModeLanguage
from rule import FOILRule, FOILRuleB
from learn_4 import CandidateBeam, LearnEntail
from scipy.optimize import minimize
from ad import gh
from ad.admath import *
from numpy import seterr, arange, concatenate
from logging import getLogger
import logging
from subprocess import Popen, PIPE
from time import time
import argparse
import sys
import os
import random
import psycopg2 
from score import rates, accuracy, m_estimate_relative, precision, recall, m_estimate_future_relative, significance, pvalue2chisquare
import rule
from eval import getLogList
from getSQLQuery import getSQLQuery      # Get SQL Query for Numeric SS 
from getExpression import getExpression  # Get Expression for Symbolic SS
from copy import copy
from itertools import product
import pickle

class ProbFOIL(LearnEntail):

    def __init__(self, data, beam_size=5, logger='probfoil', minhc = 0.00001, minpca = 0.00001, lr1 = 0.001, lr2 = 0.0001, iterations = 10000, maxAmieRules = None, ssh = False, cwLearning = False, quotes = False, m=1, cost=1, l=None, p=None, disableTypeConstraints = False, closed_world=False, global_score = 'cross_entropy', optimization_method = 'incremental', candidate_rules = 'amie', **kwargs):
        self.candidate_rules = candidate_rules
        self.pad = 33
        self.logFile = kwargs['log']
        
        LearnEntail.__init__(self, data, TypeModeLanguage(**kwargs), logger=logger, **kwargs)
        
        read_start = time()
        #self.negatives = set()
        #self.negativeThreshold = 0.9
        if self.candidate_rules != "amie":
            self.load(data)   # for types and modes
            self.totalExamples = len(self._examples)
            getLogger('probfoil').info('%-*s: %d' % (self.pad, "Number of examples (M)", self.totalExamples))
            getLogger('probfoil').info('%-*s: %.4f' % (self.pad, "Positive probabilistic part (P)", sum(self._scores_correct)))
            getLogger('probfoil').info('%-*s: %.4f' % (self.pad, "Negative probabilistic part (N)", self.totalExamples - sum(self._scores_correct)))
        else:
            self.data = data
        self._time_read = time() - read_start
        
        self._beamsize = beam_size
        self._m_estimate = m
        self._max_length = l
        self.open_world = not(closed_world)
        self.global_score = global_score
        self.optimization_method = optimization_method
        self.minpca = minpca
        self.minhc = minhc
        self.tolerance = 1e-12
        #self.maxIncrement = [0.001, 0.0002]
        self.maxIncrement = [0.00001, 0.00001]
        self.iterations = iterations
        self.misclassificationCost = 1
        #self.testFile = test
        self.learningRate = [lr1, lr2]
        self.stepCheck = 500
        self.closedWorldNegativesFactor = 1
        self.openWorldNegativesFactor = 1
        self.loadRule = None
        self.learnAllRules = True
        self.ssh = ssh
        self.replaceDB = True
        self.enforceTypeConstraints = not(disableTypeConstraints)
        self.allowRecursion = False
        self.factsWithQuotes = quotes
        self.cwLearning = cwLearning
        self.maxAmieRules = maxAmieRules
        self.terminateAtFixedPoint = False
        
        if p is None:
            self._min_significance = None
        else:
            self._min_significance = pvalue2chisquare(p)
        
        getLogger('probfoil').info('%-*s: %d' % (self.pad, "Beam Size", self._beamsize))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "m-estimate Parameter", str(self._m_estimate)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Tolerance Parameter", str(self.tolerance)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Max Increments", str(self.maxIncrement)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Learning Rate", str(self.learningRate)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Closed World Negatives' Factor", str(self.closedWorldNegativesFactor)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Open World Negatives' Factor", str(self.openWorldNegativesFactor)))
        getLogger('probfoil').info('%-*s: %d' % (self.pad, "#Iterations in SGD", self.iterations))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Misclassification Cost of -ves", str(self.misclassificationCost)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Min Significance", str(self._min_significance)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Max Rule Length", str(self._max_length)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Open World Setting", self.open_world))
        #getLogger('probfoil').info('%-*s: %s' % (self.pad, "Test File", str(self.testFile)))
        
        self.interrupted = False                 # Set it as True if you want to force it to learn just 1 rule
        self.lastRuleMerged = False
        self._stats_evaluations = 0
        self._stats_numericSS = 0
        self._stats_symbolicSS = 0
        self._stats_getSQLQuery = 0
        self._stats_getExpression = 0
        
        self._time_numericSS = 0
        self._time_symbolicSS = 0
        self._time_optimization = 0
        self._time_getSQLQuery = 0
        self._time_getCanonicalForm = 0
        self._time_executeQuery = 0
        self._time_executePSQL = 0
        self._time_getQueryProbability = 0
        self._time_getExpression = 0
        self._time_getQueryExpression = 0
        self._time_learn = 0
        
    def best_rule(self, current):
        """Find the best rule to extend the current rule set.

        :param current:
        :return:
        """
        timeStartOverall = time()
        current_rule = FOILRule(target=self.target, previous=current, correct = self._scores_correct)
        current_rule.scores = [1.0] * self.totalExamples
        current_rule.score = self._compute_rule_score(current_rule)
        c_tp, c_fp, c_tn, c_fn = rates(current_rule)
        current_rule.score_cmp = (current_rule.score, c_tp)
        current_rule.processed = False
        current_rule.probation = False
        current_rule.avoid_literals = set()
        if current:
            prev_tp = rates(current)[0]
        else:
            prev_tp = 0.0
        
        current_rule.query = [""]*self.totalExamples
        current_rule.lossStringAcc = ""
        current_rule.lossStringSL = ""
        current_rule.lossStringCE = ""
        current_rule.expressionList = [""]*self.totalExamples
        best_rule = current_rule
        
        self.canonicalRuleList = []
        
        if self.candidate_rules == "amie":
            selectedRule = None
            if self.scoreList == [None]*len(self.AmieRuleList):
                ruleList = []
                for i, (headLitral, amieLiteralList) in enumerate(self.AmieRuleList):
                    if i in self.selectedAmieRules:
                        ruleList.append(None)
                        continue
                    self.canonicalRuleList = []
                    rule = current_rule
                    for literal in amieLiteralList:
                        rule = rule & literal
                        rule.scores = [1.0] * len(self._scores_correct)
                        rule.expressionList = [""]*self.totalExamples
                        rule.lossStringAcc = ""
                        rule.lossStringSL = ""
                        rule.lossStringCE = ""
                        rule.expressionList = [""]*self.totalExamples
                    
                    #rule.confidence = self.stdConfidenceList[i]
                    getLogger('probfoil').debug('Evaluating Rule\t\t\t\t\t: %s' % rule)
                    #rule.scores = self._compute_scores_predict(rule)
                    rule.scores = [1.0] * len(self._scores_correct)
                    #getLogger('probfoil').log(9, 'Predicted scores\t\t\t\t\t: %s' % str([0 if round(item,1) == 0 else 1 if round(item,1) == 1 else round(item,1) for item in rule.scores]))
                    self._stats_evaluations += 1
                    #rule.score = self._compute_rule_score(rule)
                    rule.score = 1.0
                    
                    self.scoreList[i] = rule.score
                    ruleList.append(rule)
                    
                    if rule.score > best_rule.score:
                        best_rule = rule
                        selectedRule = i
            
                getLogger('probfoil').debug('Candidate Score List\t\t\t: ' + str(self.scoreList))
                
            else:
                #maxIndex, maxScore = max(enumerate(self.scoreList), key=lambda v: v[1])
                maxIndex = None
                maxScore = None
                for i, score in enumerate(self.scoreList):
                    if i in self.selectedAmieRules:
                        continue
                    if score > maxScore:
                        maxScore = score
                        maxIndex = i
                
                if maxIndex == None or maxIndex >= len(self.AmieRuleList):
                    self.breakNow = True
                    return None
                selectedRule = maxIndex
                headLitral, amieLiteralList = self.AmieRuleList[maxIndex]
                self.canonicalRuleList = []
                best_rule = current_rule
                for literal in amieLiteralList:
                    best_rule = best_rule & literal
                    best_rule.scores = [1.0] * len(self._scores_correct)
                    best_rule.expressionList = [""]*self.totalExamples
                    best_rule.lossStringAcc = ""
                    best_rule.lossStringSL = ""
                    best_rule.lossStringCE = ""
                    best_rule.expressionList = [""]*self.totalExamples
                
                #rule.confidence = self.stdConfidenceList[i]
                getLogger('probfoil').debug('Evaluating Rule\t\t\t\t\t: %s' % best_rule)
                #best_rule.scores = self._compute_scores_predict(best_rule)
                best_rule.scores = [1.0] * len(self._scores_correct)
                #getLogger('probfoil').log(9, 'Predicted scores\t\t\t\t\t: %s' % str([0 if round(item,1) == 0 else 1 if round(item,1) == 1 else round(item,1) for item in best_rule.scores]))
                self._stats_evaluations += 1
                #best_rule.score = self._compute_rule_score(best_rule)
                best_rule.score = 1.0
                best_rule.max_x = 1.0
            
            if len(best_rule.get_literals()) == 1:
                if not self.trueAdded:
                    self.trueAdded = True
                else: #Select another rule
                    maxIndex, maxScore = max(enumerate(self.scoreList), key=lambda v: v[1])
                    best_rule = ruleList[maxIndex]
                    selectedRule = maxIndex
            elif str(best_rule.get_literals()[1]) == 'fail':
                if not self.failAdded:
                    self.failAdded = True
                else: #Select another rule
                    maxIndex, maxScore = max(enumerate(self.scoreList), key=lambda v: v[1])
                    best_rule = ruleList[maxIndex]
                    selectedRule = maxIndex
            if selectedRule != None:
                self.selectedAmieRules.append(selectedRule)
            if best_rule == None:
                self.breakNow = True
                return None
            self._select_rule(best_rule)
            return best_rule
        
        try:
            candidates = CandidateBeam(self._beamsize)
            candidates.push(current_rule)
            iteration = 1
            time_start = time()
            while candidates:
                next_candidates = CandidateBeam(self._beamsize)

                getLogger('probfoil').debug('\n%-*s: %s [%s]' % (self.pad-1, "Best rule so far", best_rule, best_rule.score))
                time_total = time() - time_start
                getLogger('probfoil').debug('%-*s: %.1fs' % (self.pad-1, "Time - intermediate rule", time_total))
                time_start = time()
                getLogger('probfoil').debug('%-*s: %s' % (self.pad-1, "Candidates - iteration", str(iteration)))
                getLogger('probfoil').debug(candidates)
                iteration += 1
                while candidates:
                    current_rule = candidates.pop()
                    current_rule_literal_avoid = set(current_rule.avoid_literals)
                    getLogger('probfoil').debug('TO AVOID: %s => %s' % (current_rule, current_rule.avoid_literals))
                    c_tp, c_fp, c_tn, c_fn = rates(current_rule)
                    if self._max_length and len(current_rule) >= self._max_length:
                        pass
                    else:
                        for ref in self.language.refine(current_rule):
                            if ref in current_rule.avoid_literals:  # or ref.prototype in current_rule.avoid_literals:
                                getLogger('probfoil').debug('SKIPPED literal %s for rule %s' % (ref, current_rule))
                                continue
                            rule = current_rule & ref
                            rule.expressionList = [""]*self.totalExamples
                            rule.lossStringAcc = ""
                            rule.lossStringSL = ""
                            rule.lossStringCE = ""
                            #rule.ruleAscii = self.getRuleAscii(rule)
                            getLogger('probfoil').debug('%-*s: %s' % (self.pad-1, "Evaluating Rule", str(rule)))
                            time_start1 = time()
                            rule.scores = self._compute_scores_predict(rule)
                            time_total1 = time() - time_start1
                            getLogger('probfoil').log(8,'%-*s: %.1fs' % (self.pad, "Time - scores prediction", time_total1))
                            getLogger('probfoil').log(9,'%-*s: %s' % (self.pad, "Predicted scores", str([0 if round(item,1) == 0 else 1 if round(item,1) == 1 else round(item,1) for item in rule.scores])))
                            self._stats_evaluations += 1
                            rule.score = self._compute_rule_score(rule)
                            r_tp, r_fp, r_tn, r_fn = rates(rule)
                            rule.score_cmp = (rule.score, r_tp)
                            rule.score_future = self._compute_rule_future_score(rule)
                            rule.processed = False
                            rule.avoid_literals = current_rule_literal_avoid

                            if prev_tp > r_tp - self.tolerance:       # new rule has no tp improvement over previous
                                getLogger('probfoil').debug('%s %s %s %s [REJECT coverage] %s' % (rule, rule.score, rates(rule), rule.score_future, prev_tp))
                                # remove this literal for all sibling self.rules
                                current_rule_literal_avoid.add(ref)
                                current_rule_literal_avoid.add(ref.prototype)
                            elif rule.score_future <= best_rule.score:
                                getLogger('probfoil').debug('%s %s %s %s [REJECT potential] %s' % (rule, rule.score, rates(rule), rule.score_future, best_rule.score))
                                # remove this literal for all sibling self.rules
                                current_rule_literal_avoid.add(ref)
                                current_rule_literal_avoid.add(ref.prototype)
                            elif r_fp > c_fp - self.tolerance:  # and not rule.has_new_variables():
                                # no fp eliminated and no new variables
                                getLogger('probfoil').debug('%s %s %s %s [REJECT noimprov] %s' % (rule, rule.score, rates(rule), rule.score_future, best_rule.score))
                                # remove this literal for all sibling self.rules
                                # current_rule_literal_avoid.add(ref)
                                # current_rule_literal_avoid.add(ref.prototype)
                            elif r_fp > c_fp - self.tolerance and current_rule.probation:
                                getLogger('probfoil').debug('%s %s %s %s [REJECT probation] %s' % (rule, rule.score, rates(rule), rule.score_future, best_rule.score))
                            elif r_fp < self.tolerance:
                                # This rule can not be improved by adding a literal.
                                # We reject it for future exploration,
                                #  but we do consider it for best rule.
                                getLogger('probfoil').debug('%s %s %s %s [REJECT* fp] %s' % (rule, rule.score, rates(rule), rule.score_future, prev_tp))
                                if rule.score_cmp > best_rule.score_cmp:
                                    getLogger('probfoil').debug('BETTER RULE %s %s > %s' % (rule, rule.score_cmp, best_rule.score_cmp))
                                    best_rule = rule
                                    #self.queryCurrentRule = rule.query
                            else:
                                if r_fp > c_fp - self.tolerance:
                                    rule.probation = True
                                else:
                                    rule.probation = False
                                if next_candidates.push(rule):
                                    getLogger('probfoil').debug('%s %s %s %s [ACCEPT]' % (rule, rule.score, rates(rule), rule.score_future))
                                else:
                                    getLogger('probfoil').debug('%s %s %s %s [REJECT beam]' % (rule, rule.score, rates(rule), rule.score_future))

                                if rule.score_cmp > best_rule.score_cmp:
                                    getLogger('probfoil').debug('BETTER RULE %s %s > %s' % (rule, rule.score_cmp, best_rule.score_cmp))
                                    best_rule = rule
                                    #self.queryCurrentRule = rule.query
                                    
                candidates = next_candidates
        except KeyboardInterrupt:
            self.interrupted = True
            getLogger('probfoil').info('LEARNING INTERRUPTED BY USER')

        while best_rule.parent and best_rule.parent.score > best_rule.score - self.tolerance:
            best_rule = best_rule.parent
            #self.queryCurrentRule = best_rule.query

        self._select_rule(best_rule)
    
        timeOverall = time() - timeStartOverall
        getLogger('probfoil').debug('%-*s: %.1fs' % (self.pad-1, "Time - best_rule", timeOverall))
        return best_rule
    
    def regularize(self, a, factor = 1):
        if isinstance(a, float) or isinstance(a, int):
            if a > 1-factor*self.tolerance:
                return 1-factor*self.tolerance
            elif a < factor*self.tolerance:
                return factor*self.tolerance
            else:
                return a
        elif isinstance(a, str):
            a = float(a)
            if a > 1-factor*self.tolerance:
                return str(eval("1 - " + str(factor*self.tolerance)))
            elif a < factor*self.tolerance:
                return str(factor*self.tolerance)
            else:
                return str(a)

    def initial_hypothesis(self):
        initial = FOILRule(self.target)
        initial = initial & Term('fail')
        initial.accuracy = 0
        initial.scores = [0.0] * self.totalExamples
        if self.learnAllRules == False:
            initial.correct = self._scores_correct
        initial.expressionList = [""]*self.totalExamples
        initial.replaceableQuery = ''
        initial.lossStringAcc = ''
        initial.lossStringSL = ''
        initial.lossStringCE = ''
        initial.score = self._compute_rule_score(initial)
        initial.avoid_literals = set()
        
        trueRule = FOILRule(self.target, previous = initial)
        trueRule.accuracy = 0
        trueRule.scores = [1.0] * self.totalExamples
        if self.learnAllRules == False:
            trueRule.correct = self._scores_correct
        trueRule.expressionList = [""]*self.totalExamples
        trueRule.replaceableQuery = ''
        trueRule.lossStringAcc = ''
        trueRule.lossStringSL = ''
        trueRule.lossStringCE = ''
        trueRule.score = self._compute_rule_score(trueRule)
        self._select_rule(trueRule)
        trueRule.avoid_literals = set()
        self.trueAdded = True
        
        return trueRule

    def connect_PSQLDB(self, name = None):        
        if self.ssh:
            if name == None:
                conn = psycopg2.connect(user = "arcchit", password = "arcchit", host = "localhost")
            else:
                conn = psycopg2.connect(dbname = name, user = "arcchit", password = "arcchit", host = "localhost")
        else:
            if name == None:
                conn = psycopg2.connect(dbname = 'postgres', user = self.user)
            else:
                conn = psycopg2.connect(dbname = name, user = self.user)
        return conn

    def initialize_PSQLDB(self):
        # ----------------------------------- Initialize PSQL Database -----------------------------------
        time_start = time()
        outputString = Popen("echo $USER", stdout=PIPE, shell=True).communicate()
        self.user = outputString[0][0:len(outputString[0])-1] 
        
        conn = self.connect_PSQLDB(None)
        conn.autocommit = True
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        counter = 0
        
        if self.replaceDB:
            try:
                cursor.execute("DROP DATABASE IF EXISTS " + self.name +";")
                cursor.execute("CREATE DATABASE " + self.name + ";")
            except:
                self.replaceDB = False
                
        if self.replaceDB == False:
            replaceName = False
            while True:
                try:
                    if counter == 0:
                        cursor.execute("CREATE DATABASE " + self.name + ";")
                    else:
                        cursor.execute("CREATE DATABASE " + self.name + str(counter) + ";")
                        replaceName = True
                    break
                except Exception as e:
                    getLogger('probfoil').error('%-*s: %s' % (self.pad-1, "Exception Occurred", str(e)[:-1]))
                    counter += 1
            if replaceName:
                self.name = self.name + str(counter)

        getLogger('probfoil').debug('%-*s: %s' % (self.pad-1, "Created PSQL Database", self.name)) 
        cursor.close();
        conn.close();
        
        self.conn = self.connect_PSQLDB(self.name)
        #self.conn = psycopg2.connect(dbname = self.name, user = self.user)
        self.conn.autocommit = True
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.conn.cursor()
        self.cursor.execute("SET client_min_messages = error;")
        
        # Aggregate functions for Symbolic Safe Sample
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior (text);")
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_sfunc (text, double precision);")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc (text, double precision) returns text AS $$select concat('max(', $1, '*(1 - ', cast($2 AS text), '), 0.00001)')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc (text, double precision) returns text AS $$select concat($1, '*(1 - ', cast($2 AS text), ')')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_finalfunc (text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_finalfunc (text) returns text AS $$select concat('(1 - ', $1, ')')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE ior (double precision) (sfunc = ior_sfunc, stype = text, finalfunc = ior_finalfunc, initcond = '1');")
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_sfunc (text, text);")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc (text, text) returns text AS $$select concat('max(', $1, '*(1 - ', $2, '), 0.00001)')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc (text, text) returns text AS $$select concat($1, '*(1 - ', $2, ')')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE ior (text) (sfunc = ior_sfunc, stype = text, finalfunc = ior_finalfunc, initcond = '1');")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior (text);")
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_sfunc (text, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_sfunc (text, double precision) returns text AS $$select concat($1, ' + ', cast($2 AS text))$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_finalfunc (text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_finalfunc (text) returns text AS $$select concat('(', $1, ')')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE l_ior (double precision) (sfunc = l_ior_sfunc, stype = text, finalfunc = l_ior_finalfunc, initcond = '0');")
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_sfunc (text, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_sfunc (text, text) returns text AS $$select concat($1, ' + ', $2)$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE l_ior (text) (sfunc = l_ior_sfunc, stype = text, finalfunc = l_ior_finalfunc, initcond = '0');")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (double precision, double precision);")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (double precision, double precision) returns text AS $$select concat('(max(', cast($1 AS text), ',', cast($2 AS text), ') + log(exp(', cast($1 AS text), ' - max(', cast($1 AS text), ',', cast($2 AS text), ')) + exp(', cast($2 AS text), ' - max(', cast($1 AS text), ',', cast($2 AS text), ')) - exp(', cast($1 AS text), '+', cast($2 AS text), '- max(', cast($1 AS text), ',', cast($2 AS text), '))))')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (double precision, double precision) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', cast($2 AS text), ') - exp(', cast($1 AS text),'+', cast($2 AS text),'))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (text, double precision);")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (text, double precision) returns text AS $$select concat('(max(', $1, ',', cast($2 AS text), ') + log(exp(', $1, ' - max(', $1, ',', cast($2 AS text), ')) + exp(', cast($2 AS text), ' - max(', $1, ',', cast($2 AS text), ')) - exp(', $1, '+', cast($2 AS text), '- max(', $1, ',', cast($2 AS text), '))))')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (text, double precision) returns text AS $$select concat('log(exp(', $1, ') + exp(', cast($2 AS text), ') - exp(', $1,'+', cast($2 AS text),'))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (double precision, text);")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (double precision, text) returns text AS $$select concat('(max(', cast($1 AS text), ',', $2, ') + log(exp(', cast($1 AS text), ' - max(', cast($1 AS text), ',', $2, ')) + exp(', $2, ' - max(', cast($1 AS text), ',', $2, ')) - exp(', cast($1 AS text), '+', $2, '- max(', cast($1 AS text), ',', $2, '))))')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (double precision, text) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', $2, ') - exp(', cast($1 AS text),'+', $2,'))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (text, text);")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (text, text) returns text AS $$select concat('(max(',$1, ',', $2, ') + log(exp(', $1, ' - max(', $1, ',', $2, ')) + exp(', $2, ' - max(', $1, ',', $2, ')) - exp(', $1, '+', $2, '- max(', $1, ',', $2, '))))')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod (text, text) returns text AS $$select concat('log(exp(', $1, ') + exp(', $2, ') - exp(', $1,'+', $2,'))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (double precision, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1diff (double precision, double precision) returns text AS $$select concat('log(1 - exp(', cast($2 AS text), ') + exp(', cast($1 AS text), '))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (text, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1diff (text, double precision) returns text AS $$select concat('log(1 - exp(', cast($2 AS text), ') + exp(', $1, '))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (double precision, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1diff (double precision, text) returns text AS $$select concat('log(1 - exp(', $2, ') + exp(', cast($1 AS text), '))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (text, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1diff (text, text) returns text AS $$select concat('log(1 - exp(', $2, ') + exp(', $1, '))')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (double precision, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1sum (double precision, double precision) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', cast($2 AS text), ') - 1)')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (text, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1sum (text, double precision) returns text AS $$select concat('log(exp(', $1, ') + exp(', cast($2 AS text), ') - 1)')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (double precision, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1sum (double precision, text) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', $2, ') - 1)')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (text, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1sum (text, text) returns text AS $$select concat('log(exp(', $1, ') + exp(', $2, ') - 1)')$$ LANGUAGE SQL;")
        
        # Aggregate functions for Numeric Safe Sample
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc_n (double precision, double precision) RETURNS double precision AS 'select max(val) from (VALUES($1 * (1.0 - $2)), (0.00001)) AS Vals(val)' LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_finalfunc_n (double precision) RETURNS double precision AS 'select 1.0 - $1' LANGUAGE SQL;")
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior_n (double precision);")
        self.cursor.execute("CREATE AGGREGATE ior_n (double precision) (sfunc = ior_sfunc_n, stype = double precision, finalfunc = ior_finalfunc_n, initcond = '1.0');")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_sfunc_n (double precision, double precision) RETURNS double precision AS 'select $1 + $2' LANGUAGE SQL;")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior_n (double precision);")
        self.cursor.execute("CREATE AGGREGATE l_ior_n (double precision) (sfunc = l_ior_sfunc_n, stype = double precision, initcond = '0.0');")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod_n (double precision, double precision) RETURNS double precision AS 'select m + ln(exp($1-m) + exp($2-m) - exp($1+$2-m)) from(select max(val) as m from (VALUES($1), ($2)) AS Vals(val)) as foo' LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1prod_n (double precision, double precision) RETURNS double precision AS 'select case when $1 > -745 AND $2 > -745 then m + ln(exp($1-m) + exp($2-m) - exp($1+$2-m)) else m end from(select max(val) as m from (VALUES($1), ($2)) AS Vals(val)) as foo' LANGUAGE SQL;")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1diff_n (double precision, double precision) RETURNS double precision AS 'select ln(1 - exp($2) + exp($1))' LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1diff_n (double precision, double precision) RETURNS double precision AS 'select case when $1 >= -745 and $2 >= -745 and 1+exp($1)-exp($2) > 0 then ln(1 - exp($2) + exp($1)) when $1 >= -745 and $2 >= -745 and 1+exp($1)-exp($2) <= 0 then NULL when $1 >= -745 and $2 < -745 then ln(1+exp($1)) when $1 < -745 and $2 > 0 then NULL when $1 < -745 and $2 <= 0 and $2 >= -745 then ln(1-exp($2)) else 0 end' LANGUAGE SQL;")
        #self.cursor.execute("CREATE OR REPLACE FUNCTION l1sum_n (double precision, double precision) RETURNS double precision AS 'select ln(exp($1) + exp($2) - 1)' LANGUAGE SQL;")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l1sum_n (double precision, double precision) RETURNS double precision AS 'select case when $1 >= -745 and $2 >= -745 and exp($1)+exp($2)-1 > 0 then ln(exp($1) + exp($2) - 1) when $1 >= -745 and $2 >= -745 and exp($1)+exp($2)-1 <= 0 then NULL when $1 > 0 and $2 < -745 then ln(exp($1)-1) when $1 < -745 and $2 > 0 then ln(exp($2)-1) else NULL end' LANGUAGE SQL;")
        
        # Aggregate functions for Automatic Differentiation
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior_ad (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior_ad (text);")
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_sfunc_ad (text, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc_ad (text, double precision) returns text AS $$select concat($1, ' a = a*(1 - ', cast($2 AS text), ');')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_finalfunc_ad (text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_finalfunc_ad (text) returns text AS $$select concat($1, ' p = 1 - a;')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE ior_ad (double precision) (sfunc = ior_sfunc_ad, stype = text, finalfunc = ior_finalfunc_ad, initcond = '');")
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_sfunc_ad (text, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION ior_sfunc_ad (text, text) returns text AS $$select concat($1, ' a = a*(1 - ', $2, ');')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE ior_ad (text) (sfunc = ior_sfunc_ad, stype = text, finalfunc = ior_finalfunc_ad, initcond = '');")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior_ad (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior_ad (text);")
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_sfunc_ad (text, double precision);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_sfunc_ad (text, double precision) returns text AS $$select concat($1, ' p = p + ', cast($2 AS text), ';')$$ LANGUAGE SQL;")
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_finalfunc_ad (text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_finalfunc_ad (text) returns text AS $$select $1 $$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE l_ior_ad (double precision) (sfunc = l_ior_sfunc_ad, stype = text, finalfunc = l_ior_finalfunc_ad, initcond = '');")
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_sfunc_ad (text, text);")
        self.cursor.execute("CREATE OR REPLACE FUNCTION l_ior_sfunc_ad (text, text) returns text AS $$select concat($1, ' p = p + ', $2, ';')$$ LANGUAGE SQL;")
        self.cursor.execute("CREATE AGGREGATE l_ior_ad (text) (sfunc = l_ior_sfunc_ad, stype = text, finalfunc = l_ior_finalfunc_ad, initcond = '');")
        
        time_total = time() - time_start
        getLogger('probfoil').debug('%-*s: %.1fs' % (self.pad-1, "Time - initialize PSQLDB", time_total)) 
                
    def learn_readFile(self, inputFile = None, initializePSQLDB = True):
        
        # ------------------------------------- Read the input file --------------------------------------
        time_start = time() 
        self.predicateDict = {}
        self.constantDict = {}
        self.closedWorldTotal = {} 
        self.canonicalRuleList = []
        self.queryDict = {}
        self.symbolicQueryDict = {}
        self.previousInstantiatedTableSet = set()
        self.lams = {}
        self.negativeWeight = 1 #Remove later
        self.totalPositiveExamples = 0
        self.universalConstantId = {}
        self.universalConstantCount = 0
        
        if self.candidate_rules != "amie":
            if inputFile == None:
                self.InputFile = str(self._data._source_files[0])
            else:
                self.InputFile = inputFile
            self.name = self.InputFile[self.InputFile.rfind("/")+1:self.InputFile.rfind(".")].replace(".","_").lower()     
            if initializePSQLDB:
                self.initialize_PSQLDB()
            else:
                outputString = Popen("echo $USER", stdout=PIPE, shell=True).communicate()
                self.user = outputString[0][0:len(outputString[0])-1]
                #self.conn = psycopg2.connect(dbname = self.name, user = self.user)
                self.conn = self.connect_PSQLDB(self.name)
                self.conn.autocommit = True
                self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                self.cursor = self.conn.cursor()
                self.cursor.execute("SET client_min_messages = error;")
            
            self.modeSet = set()
            self.targetArity = self._target._Term__arity
            self.targetPredicate = self._target._Term__functor
            #self.hypothesisAscii = 64 + self.targetArity
            self.hypothesisFreeVars = 0
            
            for predicate, modes in self._language._modes:
                self.modeSet.add(predicate)
            
            for predicate, types in self._language._types.items():
                    
                if predicate[0] != self.targetPredicate:
                    sql_query = "CREATE TABLE IF NOT EXISTS " + predicate[0] + " ("
                    i = 0
                    while i < predicate[1]:
                        sql_query = sql_query + "v" + str(i) + " integer, "
                        i = i + 1 
                    sql_query = sql_query + "p double precision);"
                    self.cursor.execute(sql_query)
                #else:
                    #self.targetBaseList =  types
                
                if predicate[0] not in self.predicateDict:
                    self.predicateDict[predicate[0]] = types
                    self.closedWorldTotal[predicate[0]] = 0
                    if predicate[0] != self.targetPredicate:
                        self.lams[predicate[0]] = 0
                    
                for type in types:
                    if type not in self.constantDict:
                        #TODO: Old
                        self.constantDict[type] = self.language.get_type_values(type)
            
            for item in self._data._database._ClauseDB__nodes:
                if hasattr(item, 'probability') and item.functor in self.modeSet:
                    self.closedWorldTotal[item.functor] += 1
                    factString = ""
                    for i, arg in enumerate(item.args):
                        if factString == "":
                            factString = str(self.constantDict[self.predicateDict[item.functor][i]].index(arg))
                        else:
                            factString = factString + ", " + str(self.constantDict[self.predicateDict[item.functor][i]].index(arg))
                    
                    if item.probability is None:
                        prob  = str(eval("1 - " + str(self.tolerance)))
                    elif item.probability._Term__functor >= 1 - self.tolerance:
                        prob = str(eval("1 - " + str(self.tolerance)))
                    else:
                        prob = str(item.probability._Term__functor)    
                    
                    self.cursor.execute("INSERT INTO " + item.functor + " VALUES (" + factString + ", " + prob + ");")
        else:
            self._scores_correct = []
            self._examples = []
            if inputFile == None:
                self.InputFile = self.data[0]
            else:
                self.InputFile = inputFile
            self.name = self.InputFile[self.InputFile.rfind("/")+1:self.InputFile.rfind(".")].replace(".","_").lower()
            try:
                outputString = Popen("echo $USER", stdout=PIPE, shell=True).communicate()
                self.user = outputString[0][0:len(outputString[0])-1]
                if not initializePSQLDB:
                    #conn = psycopg2.connect(dbname = self.name, user = self.user)
                    conn = self.connect_PSQLDB(self.name)
            except Exception as e:
                getLogger('probfoil').warning("The database " + self.name + " is not initialized before.")
                getLogger('probfoil').warning(e)
                initializePSQLDB = True
                
            if initializePSQLDB:
                self.initialize_PSQLDB()
            else:
                #self.conn = psycopg2.connect(dbname = self.name, user = self.user)
                self.conn = self.connect_PSQLDB(self.name)
                self.conn.autocommit = True
                self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                self.cursor = self.conn.cursor()
                self.cursor.execute("SET client_min_messages = error;")
            self.targetPredicate = ""
            
            def read(file):
                inputf = open(file, 'r')
                for line in inputf:
                    #Pre-processing
                    line = line.replace(" ","")
                    if line == "\n":
                        continue
                    elif line[0] == "%":
                        continue
                    #Reading Lines
                    if line[:5] == "base(":
                        predicate = line[5:].split("(")[0]
                        types = line[5:].split("(")[1].split(")")[-3].split(",")
                        arity = len(types)
                        
                        if arity != 2:
                            getLogger('probfoil').error("Arity of Predicate (" + predicate + ") is " + str(arity) + " instead of 2.")
                            return
                        
                        for type in types:
                            if type not in self.constantDict:
                                self.constantDict[type] = {}
                        
                        self.predicateDict[predicate] = types
                        self.closedWorldTotal[predicate] = 0
                        self.lams[predicate] = 0
                        
                        if initializePSQLDB:
                            sql_query = "CREATE TABLE IF NOT EXISTS " + predicate + " ("
                            i = 0
                            while i < arity:
                                sql_query = sql_query + "v" + str(i) + " integer, "
                                i += 1 
                            sql_query = sql_query + "p double precision);"
                            self.cursor.execute(sql_query)
                        
                    elif line[:6] == "learn(":
                        if self.target is not None:
                            continue
                        self.targetPredicate = line.split("(")[1].split("/")[0]
                        self.targetArity = int(line.split("/")[1].split(")")[0])
                        
                        arguments = [Var("A"), Var("B")]
                        self._target = Term(str(self.targetPredicate), *arguments)
                                                
                        #self.hypothesisAscii = 64 + self.targetArity
                        self.hypothesisFreeVars = 0
                        if self.targetArity != 2:
                            getLogger('probfoil').error("Arity of Target Predicate (" + self.targetPredicate + ") is " + str(self.targetArity) + " instead of 2.")
                            return
                        
                    elif line[:5] == "mode(":
                        #Mode is not required when generating candidates from AMIE
                        continue
                    
                    else:
                        #Read Probabilistic Fact
                        prob = "0"
                        predicate = ""
                        if "::" in line.split('"')[0]:
                            predicate = line.split("::")[1].split("(")[0]
                            prob = line.split("::")[0]
                            if float(prob) > 1 - self.tolerance:
                                prob = str(eval("1 - " + str(self.tolerance)))
                        else:
                            predicate = line.split("(")[0]
                            prob = str(eval("1 - " + str(self.tolerance)))
                        
                        self.closedWorldTotal[predicate] += 1
                        if self.factsWithQuotes:
                            subject = line.split('(')[1].split('","')[0] +'"' 
                            object = '"' + '('.join(line.split('(')[1:]).split('","')[1][:-3]
                        else:
                            subject = line.split('(')[1].split(",")[0]
                            object = line.split(')')[-2].split(",")[1]
                        
                        if subject not in self.universalConstantId:
                            self.universalConstantId[subject] = self.universalConstantCount
                            self.constantDict[self.predicateDict[predicate][0]][subject] = self.universalConstantCount
                            self.universalConstantCount += 1
                        
                        if object not in self.universalConstantId:
                            self.universalConstantId[object] = self.universalConstantCount
                            self.constantDict[self.predicateDict[predicate][1]][object] = self.universalConstantCount
                            self.universalConstantCount += 1
                            
                        if initializePSQLDB:
                            #subjectIndex = self.constantDict[self.predicateDict[predicate][0]][subject]
                            #objectIndex = self.constantDict[self.predicateDict[predicate][1]][object]
                            subjectIndex = self.universalConstantId[subject]
                            objectIndex = self.universalConstantId[object]
                            self.cursor.execute("INSERT INTO " + predicate + " VALUES (" + str(subjectIndex) + ", " + str(objectIndex) + ", " + prob + ");")
                        
                        if predicate == self.targetPredicate:
                            args = [subject,object]
                            prob = float(prob)
                            if args in self.examples:
                                oldProb = self._scores_correct[self.examples.index(args)]
                                newProb = prob + oldProb - prob*oldProb
                                self._scores_correct[self.examples.index(args)] = newProb
                                #if oldProb < self.negativeThreshold and newProb >= self.negativeThreshold:
                                #    self.negatives.remove(self.examples.index(args))
                            else:
                                self._examples.append(args)
                                self._scores_correct.append(prob)
                                #if prob < self.negativeThreshold:
                                #   self.negatives.add(len(self.examples)-1)
                inputf.close()
            
            if self.target is not None:
                self.targetArity = self._target._Term__arity
                self.targetPredicate = self._target._Term__functor
                #self.hypothesisAscii = 64 + self.targetArity
                self.hypothesisFreeVars = 0
                if self.targetArity != 2:
                    getLogger('probfoil').error("Arity of Target Predicate (" + self.targetPredicate + ") is " + str(self.targetArity) + " instead of 2.")
                    return
                    
            if inputFile == None:
                for file in self.data:
                    read(file)
            else:
                read(inputFile)
            
            self.totalExamples = len(self.examples)
            getLogger('probfoil').info('%-*s: %d' % (self.pad, "Number of examples (M)", self.totalExamples))
            getLogger('probfoil').info('%-*s: %.4f' % (self.pad, "Positive probabilistic part (P)", sum(self._scores_correct)))
            getLogger('probfoil').info('%-*s: %.4f' % (self.pad, "Negative probabilistic part (N)", self.totalExamples - sum(self._scores_correct)))
        
            
        self.predicateList = self.predicateDict.keys()
        self.predicateList.remove(self.targetPredicate)
        self.lams.pop(self.targetPredicate, None)
        
        time_total = time() - time_start
        self._time_read = self._time_read + time_total 
        
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Target Base List", str(self.predicateDict[self.targetPredicate])))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Predicate Dict", str(self.predicateDict)))
        getLogger('probfoil').log(8, '%-*s: %s' % (self.pad, "Universal Constant Dict", str(self.universalConstantId)))
        getLogger('probfoil').debug('%-*s: %.1fs' % (self.pad-1, "Time - readFile", time_total))
    
    def convertProblogToAmie(self):
        if not(os.path.exists(self.TSVFile)):
            inputf = open(self.InputFile, 'r')
            outputf = open(self.TSVFile, 'w+')
            
            for line in inputf:
                line = line.replace(" ","")
                if line == "\n" or line[0] == "%" or line[:4] == "mode" or line[:5] == "learn":
                    continue
                elif line[:4] == "base":
                    predicate = line.split('(')[1]
                    attributes = line.split('(')[2].split(')')[0].split(',')
                    outputf.write("<" + predicate + ">\t<http://www.w3.org/2000/01/rdf-schema#domain>\t<" + attributes[0] + ">\n")
                    outputf.write("<" + predicate + ">\t<http://www.w3.org/2000/01/rdf-schema#range>\t<" + attributes[1] + ">\n")
                else:
                    #Read Probabilistic Fact
                    if self.factsWithQuotes:
                        if "::" in line.split('"')[0]:
                            predicate = line.split("::")[1].split("(")[0]
                        else:
                            predicate = line.split("(")[0]
                        subject = line.split('(')[1].split('","')[0] +'"' 
                        object = '"' + '('.join(line.split('(')[1:]).split('","')[1][:-3]
                        attributes = [subject, object]
                    else:
                        predicate = line.split(':')[2].split('(')[0]
                        attributes = line.split(':')[2].split('(')[1].split(')')[0].split(',')
                    outputf.write("<" + attributes[0] + ">\t<" + predicate + ">\t<" + attributes[1] + ">\n")
            
            inputf.close()
            outputf.close()
    
    def getAmieRules(self):
        
        minhc = self.minhc
        minpca = self.minpca
        if self.ssh:
            path = "Documents/OpenProbFOIL/"
            if self.allowRecursion:
                if self._max_length != None:
                    amieQuery = "ssh himec04 " + '"' + "java -jar " + path + "amie_plus.jar -maxad " + str(self._max_length) + " -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -oute " + path + self.TSVFile + '"'
                else:
                    amieQuery = "ssh himec04 " + '"' + "java -jar " + path + "amie_plus.jar -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -oute " + path+ self.TSVFile + '"'
            else:
                if self._max_length != None:
                    amieQuery = "ssh himec04 " + '"' + "java -jar " + path + "amie_plus.jar -maxad " + str(self._max_length) + " -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -bexr '<" + self.targetPredicate + ">' -oute " + path + self.TSVFile + '"'
                else:
                    amieQuery = "ssh himec04 " + '"' + "java -jar " + path + "amie_plus.jar -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -bexr '<" + self.targetPredicate + ">' -oute " + path+ self.TSVFile + '"'
        else:
            if self.allowRecursion:
                if self._max_length != None:
                    amieQuery = "java -jar amie_plus.jar -maxad " + str(self._max_length) + " -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -oute " + self.TSVFile
                else:
                    amieQuery = "java -jar amie_plus.jar -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -oute " + self.TSVFile
            else:
                if self._max_length != None:
                    amieQuery = "java -jar amie_plus.jar -maxad " + str(self._max_length) + " -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -bexr '<" + self.targetPredicate + ">' -oute " + self.TSVFile
                else:
                    amieQuery = "java -jar amie_plus.jar -minhc " + str(minhc) + " -minpca " + str(minpca) + " -htr '<" + self.targetPredicate + ">' -bexr '<" + self.targetPredicate + ">' -oute " + self.TSVFile
                    
        getLogger('probfoil').debug('Running AMIE+ : %s' % amieQuery)
        outputString = Popen(amieQuery, stdout=PIPE, shell=True).communicate()
        outputList = outputString[0].split('\n')[13:-4] 
        
        ruleList = []
        coverageList = []
        stdConfidenceList = []
        pcaConfidenceList = []
        
        for row in outputList:
            line = row.split("\t")[0]
            confidence = row.split("\t")[1].replace(",", ".")
            stdConfidence = row.split("\t")[2].replace(",", ".")
            pcaConfidence = row.split("\t")[3].replace(",", ".")
        
            head = line.split("=>")[1].split("<")[1].split(">")[0]
            
            body = line.split("=>")[0]
            i = 0
            bodyItems = []
            while i < len(body):
                if body[i] == "?":
                    bodyItems.append(body[i+1].upper())
                    i += 2
                    continue
                elif body[i] == "<":
                    start = i+1
                    while body[i] != ">":
                        i += 1
                    bodyItems.append(body[start:i])
                i += 1
                
            headVar1 = line.split("=>")[1].split("?")[1][0].upper()
            headVar2 = line.split("=>")[1].split("?")[2][0].upper()
            replaceVariable = False
            headDict = {}
            bodyDict = {}
            maxAscii = 65
            
            if headVar1 != "A" or headVar2 != "B":
                i = 0
                while i < len(bodyItems):
                    if i % 3 == 0:
                        ascii = ord(bodyItems[i])
                        maxAscii = max(maxAscii, ascii)
                        i += 2
                    elif i % 3 == 2:
                        ascii = ord(bodyItems[i])
                        maxAscii = max(maxAscii, ascii)
                        i += 1
                if headVar1 != "A":
                    headDict[headVar1] = "A"
                    headDict["A"] = chr(maxAscii + 1)
                    maxAscii += 1
                if headVar1 != "B":
                    headDict[headVar1] = "B"
                    headDict["B"] = chr(maxAscii + 1)
                    maxAscii += 1
                replaceVariable = True
                
            i = 0
            bodyList = []
            bodyDict = {}
            bodyDict["A"] = "A"
            bodyDict["B"] = "B"
            maxAscii = 66
            while i < len(bodyItems):
                if i % 3 == 0:
                    var1 = bodyItems[i]
                    if replaceVariable == True and bodyItems[i] in headDict:
                        var1 = headDict[bodyItems[i]]
                    if var1 in bodyDict:
                        var1 = bodyDict[var1]
                    else:
                        bodyDict[var1] = chr(maxAscii + 1)
                        var1 = chr(maxAscii + 1)
                        maxAscii += 1
                elif i % 3 == 1:
                    relation = bodyItems[i]
                elif i % 3 == 2:
                    var2 = bodyItems[i]
                    if replaceVariable == True and bodyItems[i] in headDict:
                        var2 = headDict[bodyItems[i]]
                    if var2 in bodyDict:
                        var2 = bodyDict[var2]
                    else:
                        bodyDict[var2] = chr(maxAscii + 1)
                        var2 = chr(maxAscii + 1)
                        maxAscii += 1
                    
                    arguments = [Var(var1), Var(var2)]
                    literal = Term(str(relation), *arguments)
                    bodyList.append(literal)
                i += 1
            
        
            headArguments = [Var(headVar1), Var(headVar2)]
            headLiteral = Term(str(head), *headArguments)

            rule = (headLiteral, bodyList)
            
            addRule = True
            if self.enforceTypeConstraints:
                varDict = {}
                for literal in bodyList:
                    for i, arg in enumerate(literal.args):
                        type = self.predicateDict[literal.functor][i]
                        ascii = ord(str(arg))
                        if ascii < 65 + self.targetArity:
                            if type != self.predicateDict[self.targetPredicate][ascii-65]:
                                #Type Mismatch in the Rule
                                getLogger('probfoil').info('%-*s: %s' % (self.pad, "Removing Rule from AMIE List", str(rule)))
                                addRule = False
                        if arg in varDict:
                            if type != varDict[arg]:
                                #Type Mismatch in the Rule
                                getLogger('probfoil').info('%-*s: %s' % (self.pad, "Removing Rule from AMIE List", str(rule)))
                                addRule = False
                        else:
                            varDict[arg] = type
            
            if addRule:
                ruleList.append(rule)
                coverageList.append(confidence)
                stdConfidenceList.append(stdConfidence)
                pcaConfidenceList.append(pcaConfidence)
        
        if len(ruleList) == 0:
            getLogger('probfoil').error('%-*s' % (self.pad, "No significant and type consistent rules returned by AMIE"))
            self.breakNow = True
            return (ruleList, coverageList, stdConfidenceList, pcaConfidenceList)
        else:
            a = zip(stdConfidenceList, ruleList, coverageList, pcaConfidenceList)
            b = sorted(a, reverse=True)
            stdConfidenceList, ruleList, coverageList, pcaConfidenceList = zip(*b)
            if self.maxAmieRules != None:
                i = int(self.maxAmieRules)
                return (ruleList[:i], coverageList[:i], stdConfidenceList[:i], pcaConfidenceList[:i])
            else:
                return (ruleList, coverageList, stdConfidenceList, pcaConfidenceList)
        
    def getAmieHypothesis(self):
        oldRule = FOILRule(self.target)
        oldRule = oldRule & Term('fail')
        oldRule = FOILRule(self.target, previous = oldRule)
        for (headLiteral, amieLiteralList) in self.AmieRuleList:
            newRule = FOILRule(target=self.target, previous=oldRule)
            for literal in amieLiteralList:
                newRule = newRule & literal
            oldRule = newRule
        
        return oldRule    
    
    def getPRCurves(self, cscores, pscores, deterministic = True):

        a = zip(pscores, cscores)
        b = sorted(a, reverse=True)
        pscores, cscores = zip(*b)
        thresholdList = sorted(list(set(pscores)), reverse = True)
        
        #Incremental Deterministic Precision
        precisionList = []
        recallList = []
        tplist = []
        tnlist = []
        fplist = []
        fnlist = []
        
        tp = 0.0
        fp = 0.0
        #tn = sum(weights) - len(self.old_examples)
        fn = float(sum([1 if item > 0 else 0 for item in cscores]))
        
        counter = 0
        for threshold in thresholdList:
            for predicted, correct in zip(pscores[counter:], cscores[counter:]):
                if predicted >= threshold:
                    #This is a predicted positive example
                    if correct > 0:
                        tp += 1
                        fn -= 1
                    else:
                        #tn -= 1
                        fp += 1
                    
                    counter += 1
                else:
                    break
        
            tplist.append(tp)
            #tnlist.append(tn)
            fplist.append(fp)
            fnlist.append(fn)
            
            if tp + fp == 0:
                precision = 0.0
            else:
                precision = tp / (tp + fp)
            
            if tp + fn == 0:
                recall = 0.0
            else:
                recall = tp / (tp + fn)
            
            precisionList.append(precision)
            recallList.append(recall)    
        
        getLogger('probfoil').log(9, "tpList : " + str(tplist))
        getLogger('probfoil').log(9, "fpList : " + str(fplist))
        getLogger('probfoil').log(9, "fnList : " + str(fnlist))
        #getLogger('probfoil').log(9, "tnList : " + str(tnlist) + "\n")
        
        getLogger('probfoil').log(9, "recallList : " + str(recallList))
        getLogger('probfoil').log(9, "precisionList : " + str(precisionList) + "\n")
        
        return (recallList, precisionList)
            
    def learn_parseRules(self, hypothesis, merge = True):
        time_start = time()
        clauses = hypothesis.to_clauses()
        ruleList = []
        hypothesis.probabilityList = []
        hypothesis.confidenceList = []
        hypothesis.bodyList = []
        literalSetList = []
        hypothesis.predicateList = []
        
        rule = hypothesis
        while rule.previous != None:
            ruleList.append(rule)
            prob = rule.get_rule_probability()
            if prob == None:
                prob = 1 - self.tolerance
            hypothesis.probabilityList.append(prob)
            #hypothesis.confidenceList.append(rule.confidence)
            body = rule.get_literals()[1:]
            hypothesis.bodyList.append(body)
            
            literalSet = set()
            for literal in body:
                literalSet.add(literal)
                predicate = literal.functor
                if predicate not in hypothesis.predicateList and predicate not in ["true", "fail", "false"]:
                    hypothesis.predicateList.append(predicate) 
            
            literalSetList.append(literalSet)
            rule = rule.previous
        
        if merge :
            i = 0
            iRule = hypothesis    
            while i < len(hypothesis.bodyList):
                j = i + 1
                previousjRule = iRule
                jRule = iRule.previous
                while j < len(hypothesis.bodyList):
                    if literalSetList[i] == literalSetList[j]:
                        # Merge rules i and j
                        
                        # Update Prob of first rule
                        p1 = hypothesis.probabilityList[i]
                        p2 = hypothesis.probabilityList[j]
                        p = p1 + p2 - p1*p2
                        hypothesis.probabilityList[i] = p
                        if p > 1-self.tolerance:
                            iRule.set_rule_probability(None)
                        else:
                            iRule.set_rule_probability(p)
                        
                        # Delete second rule
                        previousjRule.previous = jRule.previous
                        if j == len(hypothesis.bodyList) - 1:
                            self.lastRuleMerged = True
                        del hypothesis.bodyList[j]
                        del hypothesis.probabilityList[j]
                        del literalSetList[j]
                        continue
                    j += 1
                    previousjRule = jRule
                    jRule = jRule.previous
                iRule = iRule.previous
                i += 1
        
        hypothesis.probabilityList.reverse()
        hypothesis.bodyList.reverse()
        hypothesis.predicateList.reverse()
        for i, prob in enumerate(hypothesis.probabilityList):
            hypothesis.predicateList.append("p_" + str(i)) 
            tableName = "p_" + str(i)
            self.cursor.execute("DROP TABLE IF EXISTS " + tableName + ";")
            self.cursor.execute("CREATE TABLE " + tableName + " (v0 integer, p double precision);")
        
            if tableName not in self.lams:
                if prob < 1 - self.tolerance:
                    self.lams[tableName] = prob
                else:
                    self.lams[tableName] = 1 - self.tolerance

        time_total = time() - time_start
        
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Probability List", str(hypothesis.probabilityList)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Body List", str(hypothesis.bodyList)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Predicate List", str(hypothesis.predicateList)))
        getLogger('probfoil').info('%-*s: %.1fs' % (self.pad, "Time - parseRules", time_total))
        
    def learn_getQueryString(self, hypothesis):
        
        time_start = time()
        # --------------------------- Make a single query out of the hypothesis ---------------------------
        
        #ruleAscii = 64 + self.targetArity
        freeVarId = 0
        for i, body in enumerate(hypothesis.bodyList):
            replaceDict = {}
            for j, literal in enumerate(body):
                varList = []
                for arg in literal.args:
                    if ord(str(arg)) > 64 + self.targetArity:
                        if str(arg) in replaceDict:
                            varList.append(Var(replaceDict[str(arg)]))
                        else:
                            #replaceDict[str(arg)] = chr(ruleAscii + 1)
                            #varList.append(Var(chr(ruleAscii + 1)))
                            #ruleAscii += 1
                            
                            replaceDict[str(arg)] = "V" + str(freeVarId)
                            varList.append(Var("V" + str(freeVarId)))
                            freeVarId += 1
                    else:
                        varList.append(arg)
                body[j] = Term(literal.functor, *varList)
            
            #p = Term("p_" + str(i), *[Var(chr(ruleAscii+1))])
            #ruleAscii += 1
            p = Term("p_" + str(i), *[Var("V" + str(freeVarId))])
            freeVarId += 1
            
            body.append(p)
        
        #hypothesis.maxAscii = ruleAscii
        hypothesis.totalFreeVars = freeVarId
        hypothesis.queryString = " v ".join([str(item)[1:-1].replace(" ","") for item in hypothesis.bodyList])
    
        time_total = time() - time_start
        
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Body List", str(hypothesis.bodyList)))
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Query String", hypothesis.queryString))
        getLogger('probfoil').info('%-*s: %.1fs' % (self.pad, "Time - getQueryString", time_total))
        
    def instantiateTables(self, instantiatedTableSet):
        # ---------------------------------- Create Instantiated Tables ----------------------------------
        
        getLogger('probfoil').log(8, 'Instantiated Table Set\t\t\t: %s' % str(instantiatedTableSet))
        getLogger('probfoil').log(8, 'Previous Instantiated Table Set\t: %s' % str(self.previousInstantiatedTableSet))
        
        for tableItem in instantiatedTableSet - self.previousInstantiatedTableSet:                
            tableNames = tableItem.split("_")
            table = tableNames[0]
            argList = tableNames[1:]
            
            selectString = ""
            whereString = ""
            count = 0
            for i,arg in enumerate(argList):
                if arg != "all":
                    if whereString == "":
                        whereString = "v" + str(i) + " = " + str(arg)
                    else:
                        whereString = whereString + " AND v" + str(i) + " = " + str(arg)
                else:
                    if selectString == "":
                        selectString = "v" + str(i) + " as v" + str(count)
                    else:
                        selectString = selectString + ", v" + str(i) + " as v" + str(count)
                    count += 1
            
            if selectString == "":
                self.cursor.execute("Select ior(p) from " + table + " where " + whereString +";")
                prob = self.cursor.fetchone()[0]
                
                # Create a table by the name 'newTable' which will have exactly 1 free variable
                self.cursor.execute("DROP TABLE IF EXISTS " + tableItem + ";")
                self.cursor.execute("CREATE TABLE " + tableItem + " (v0 integer, p double precision);")
                if prob != "(1 - 1)":
                    prob = eval(prob)
                    if prob > 1 - self.tolerance:
                        prob = 1 - self.tolerance
                    self.cursor.execute("INSERT INTO " + tableItem + " VALUES (0, "+str(prob)+");")
                
            elif whereString == "":
                getLogger('probfoil').error('Exception Occurred: Empty selectString or whereString in ' % tableItem)
                return
            else:    
                selectString = selectString + ", p"
                
                getLogger('probfoil').log(8, 'Probfoil: CREATE TABLE IF NOT EXISTS %s AS (SELECT %s FROM %s WHERE %s);' % (tableItem, selectString, table, whereString))
                self.cursor.execute("CREATE TABLE IF NOT EXISTS " + tableItem + " AS (SELECT " + selectString + " FROM " + table + " WHERE " + whereString + ");")
                 
            self.previousInstantiatedTableSet.add(tableItem)
    
    def getQueryForExample(self, hypothesis, example):
        
        instantiatedTableSet = set()
        
        if hypothesis.replaceableQuery == '':
            hypothesis.replaceableTables = set()
            #ruleAscii = hypothesis.maxAscii
            freeVarId = hypothesis.totalFreeVars
            k = 1
            start = 0
            self.replaceBody = False
            instantiatedQueryString = ""
            while k < len(hypothesis.queryString):
                if hypothesis.queryString[k-1]=="(":
                    replacePredicate = False
                    table = hypothesis.queryString[start:k-1]
                    newTable = table
                    left = k-1
                    l = 0
                    if ord(hypothesis.queryString[k]) <= 64 + self.targetArity:
                        #baseNumber = ord(hypothesis.queryString[k]) - 65
                        #base = self.predicateDict[self.targetPredicate][baseNumber]
                        #value = example[baseNumber]
                        #newTable = newTable + "_" + str(self.universalConstantId[value])
                        newTable += "_" + hypothesis.queryString[k]
                        self.replaceBody = True
                        replacePredicate = True
                    else:
                        newTable = newTable + "_all"
                
                elif hypothesis.queryString[k-1]=="," and hypothesis.queryString[k-2]!=")":
                    l = l + 1
                    if ord(hypothesis.queryString[k]) <= 64 + self.targetArity:
                        #baseNumber = ord(hypothesis.queryString[k]) - 65
                        #base = self.predicateDict[self.targetPredicate][baseNumber]
                        #value = example[baseNumber]
                        #newTable = newTable + "_" + str(self.universalConstantId[value])
                        newTable += "_" + hypothesis.queryString[k]
                        self.replaceBody = True
                        replacePredicate = True
                    else:
                        newTable = newTable + "_all"
                
                elif hypothesis.queryString[k]==")":
                    if replacePredicate == True: #This means that the literal contains at least 1 fixed variable that needs instantiation
                        
                        #Replace 'hypothesis.queryString[left:k+1]' by only free variables
                        # If variableString = '(A,B,C)' ==> '(C)'
                        # If variableString = '(A,B)' or '(A)' ==> then don't add the newTable. Instead execute a query to get the probability of a tuple when A and B are instantiated.
                        
                        tableNames = newTable.split("_")
                        table = tableNames[0]
                        argList = tableNames[1:]
                        varList = hypothesis.queryString[left+1:k].split(",")
                        reallyReplacePredicate = False
                        
                        varString = ""
                        for j, arg in enumerate(argList):
                            if arg == "all":
                                reallyReplacePredicate = True
                                if varString == "":
                                    varString = varList[j]
                                else:
                                    varString = varString + "," + varList[j]
                    
                        if reallyReplacePredicate == True: #Eg: '(A,B,C)' ==> '(C)'
                            hypothesis.replaceableTables.add(newTable)
                            instantiatedQueryString = instantiatedQueryString + newTable + "(" + varString + ")"
                            #instantiatedQueryString = instantiatedQueryString + newTable + hypothesis.queryString[left:k+1]
                        else:  #This means that the literal contains only fixed variables which needs instantiation, Eg: (A,B) or (A)
                            
                            #Calculate the probability of a tuple from a fully instantiated table name
                            #'author_0_1' ==> Create and execute a psql query which subsets 'author' on v0 = 0 and v1 = 1 and then aggregate by ior
                            
                            hypothesis.replaceableTables.add(newTable)
                            '''
                            whereString = ""
                            for j, arg in enumerate(argList):    
                                if whereString == "":
                                    whereString = "v" + str(j) + " = " + str(arg)
                                else:
                                    whereString = whereString + " AND v" + str(j) + " = " + str(arg)
                            
                            self.cursor.execute("Select ior(p) from " + table + " where " + whereString +";")
                            prob = self.cursor.fetchone()[0]
                            
                            # Create a table by the name 'newTable' which will have exactly 1 free variable
                            self.cursor.execute("DROP TABLE IF EXISTS " + newTable + ";")
                            self.cursor.execute("CREATE TABLE " + newTable + " (v0 integer, p double precision);")
                            if prob != "(1 - 1)":
                                prob = eval(prob)
                                if prob > 1 - self.tolerance:
                                    prob = 1 - self.tolerance
                                self.cursor.execute("INSERT INTO " + newTable + " VALUES (0, "+str(prob)+");")
                            '''
                            #instantiatedQueryString = instantiatedQueryString + newTable + "(" + chr(ruleAscii + 1) +")"
                            #ruleAscii += 1
                            instantiatedQueryString = instantiatedQueryString + newTable + "(V" + str(freeVarId) +")"
                            freeVarId += 1
                    else:
                        '''
                        if table in self.deterministicFactDict and len(self.deterministicFactDict[table]) != 0:
                            getLogger('probfoil').log(8, table + " has deterministic tuples.")
                        else:
                        '''
                        instantiatedQueryString = instantiatedQueryString + hypothesis.queryString[start:k+1]
                    start = k+1
                elif (hypothesis.queryString[k]=="," and hypothesis.queryString[k-1]==")") or hypothesis.queryString[k]=="~":
                    instantiatedQueryString = instantiatedQueryString + hypothesis.queryString[k] 
                    start = k+1
                elif hypothesis.queryString[k-3:k] == " v ":
                    # Add a dummy variable wrt to current prob. Later reset the prob to 1
                    instantiatedQueryString = instantiatedQueryString + " v "
                    start = k
                k = k + 1
            
            clauseList = instantiatedQueryString.split(' v ')
            if '' not in clauseList:
                instantiatedQueryString = ''
                for clause in clauseList:
                    clauseSplit = clause.split(',')
                    clauseSplit[:] = (value for value in clauseSplit if value != '')
                    if instantiatedQueryString == '':
                        instantiatedQueryString = ','.join(clauseSplit)
                    else: 
                        instantiatedQueryString = instantiatedQueryString + ' v ' + ','.join(clauseSplit)
                hypothesis.replaceableQuery =  instantiatedQueryString
            else:
                hypothesis.replaceableQuery = ''
        
        query = copy(hypothesis.replaceableQuery)
        for i, value in enumerate(example):
            query = query.replace(chr(65+i), str(self.universalConstantId[value]))
        
        instantiatedTables = set()
        for element in hypothesis.replaceableTables:
            table = copy(element)
            for i, value in enumerate(example):
                table = table.replace(chr(65+i), str(self.universalConstantId[value]))
            instantiatedTables.add(table)
                
        self.instantiateTables(instantiatedTables)
        
        return query
        
    def learn_getQueryList(self, hypothesis):
        
        time_start = time()
        # ------------------------ Query for each of the examples using SafeSapmle -----------------------
        i = 0
        while i < self.totalExamples:
            example = self.examples[i]
            self.querySS[i] = self.getQueryForExample(hypothesis, example)
            i = i + 1
        
        #hypothesis.maxAscii = ruleAscii
        hypothesis.totalFreeVars = freeVarId
        
        getLogger('probfoil').log(9, 'Query List\t\t\t\t\t\t: %s' % str(self.querySS[0]))
        
        hypothesis.querySS = copy(self.querySS) # TO DO: Need to Speed up
        
        time_total = time() - time_start
        getLogger('probfoil').debug('Time - getQueryList\t\t\t\t: %.1fs' % time_total)

    def executeCanonicalExpression(self, SQLQuery, tableList, variableMapping):
        
        if SQLQuery in ["Failed to parse", None, "Query is unsafe"]:
            return None
        
        outputString = None
        trueSQLQuery = ""
        i = 0
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
                    j = 0
                    lastEnd = 0
                    
                    while j < len(expression)-1:
                        if expression[j:j+2] == "z_":
                            trueExpression = trueExpression + expression[lastEnd:j] 
                            start = j
                            j += 2
                            while (expression[j].isalpha() or expression[j].isdigit()) and j < len(expression):
                                j += 1
                            tableString = expression[start+2:j]
                            tableNumber = int(tableString[5:])
                            table = tableList[tableNumber]
                            actualTable = table.split('_')[0]
                            if actualTable == "p":
                                #trueExpression = trueExpression + "0"
                                trueExpression = trueExpression + "z_" + str(table)
                            else: 
                                trueExpression = trueExpression + "z_" + str(actualTable)
                            lastEnd = j
                            continue
                        elif expression[j:j+2] == "y_":
                            
                            trueExpression = trueExpression + expression[lastEnd:j] 
                            start = j
                            
                            variableString = expression[start+2]
                            k = 3
                            while expression[start+k].isdigit():
                                variableString = variableString + expression[start+k] 
                                k += 1
                                if start + k == len(expression):
                                    break 
                            
                            j += k
                            if variableMapping[variableString] == "p":
                                domain = 1
                            elif variableMapping[variableString] == "all":
                                domain = 1
                            else:
                                domain = len(self.constantDict[variableMapping[variableString]])
                                
                            trueExpression = trueExpression + str(domain)
                            
                            lastEnd = j
                            continue
                        j += 1
                    trueExpression = trueExpression + expression[lastEnd:]
                    
                trueSQLQuery = trueSQLQuery + trueExpression
            else:
                trueSQLQuery = trueSQLQuery + SQLQuery[i]
            
            i += 1
        
        try:
            self.cursor.execute(trueSQLQuery)
            output = self.cursor.fetchall()
                
            if output[0][0] not in ["Failed to parse", None, "Query is unsafe"]:
                outputString = "(1 - exp(" + output[0][0] + "))"
                
        except psycopg2.Error as e:
            getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e))
            getLogger('probfoil').warning("Execute Expression >> SQL error \t: " + e.pgerror[:-1]) 
            getLogger('probfoil').warning("Execute Expression >> Query \t: " + trueSQLQuery)
            
        return outputString

    def simpleEval(self, l):
        l = l.replace("log(-0 + 1)", "0")
        l = l.replace("*1 ", " ")
        l = l.replace(" 1*", " ")
        l = l.replace("(0 + ", "(")
        l = l.replace("(0 - ", "(-")
        l = l.replace(" - 0)", ")")
        l = l.replace(" + 0)", ")")
        l = l.replace(",0 + ", ",")
        l = l.replace(",0 - ", ",-")
        l = l.replace(" - 0,", ",")
        l = l.replace(" + 0,", ",")
        l = l.replace(")*1)", "))")
        
        i = 0
        consecutiveBracket = False
        multiplicativeIndicator = False
        operatorStack = []
        
        while i < len(l):
            if i + 3 < len(l) and l[i:i+3] in ['exp', 'log', 'max', 'Max']:
                operatorStack.append('o')
                i += 3
                continue
            
            if l[i] == "(":
                operatorStack.append('(')
                left = i+1
                consecutiveBracket = True
                if l[i-1] == "*":
                    multiplicativeIndicator = True
                
            elif l[i] == ",":
                if consecutiveBracket == False:
                    consecutiveBracket = True
                    left = i+1
                elif consecutiveBracket == True:
                    #print("Old i \t\t\t= " + str(i))
                    right = i
                    expression = l[left:right]
                    #print("Expression \t\t= " + expression)
                    try:
                        ans = eval(expression)
                        l = l[:left] + str(ans) + l[right:]
                        i = left + len(str(ans)) + 1
                        left = i
                        continue
                    except:
                        expression = expression.replace("- ","-")
                        expression = expression.replace("+ ","+")
                        expression = expression.replace("+-","-")
    
                        exprList = expression.split(" ")
                        numericExprList = []
                        symbolicExpr = ""
                        for j, expr in enumerate(exprList):
                            try:
                                number = eval(expr)
                                numericExprList.append(number)
                            except:
                                if symbolicExpr == "":
                                    if expr[0] == '+':
                                        symbolicExpr = expr[1:]
                                    else:
                                        symbolicExpr = expr
                                else:
                                    if expr[0] == '+':
                                        symbolicExpr = symbolicExpr + " + " + expr[1:]
                                    elif expr[0] == '-':
                                        symbolicExpr = symbolicExpr + " - " + expr[1:]
                                    else:
                                        symbolicExpr = symbolicExpr + " + " + expr
    
                        if symbolicExpr != "" and numericExprList != []:
                            newExpression = symbolicExpr + " + " + str(sum(numericExprList))
                        elif symbolicExpr == "":
                            newExpression = str(sum(numericExprList))
                        elif numericExprList == []:
                            newExpression = symbolicExpr
    
                        #print("New Expression \t\t\t= " + newExpression)
                        
                        l = l[:left] + newExpression + l[right:]
                        i = left + len(newExpression) + 1
                        left = i
                        continue
    
            elif l[i] == ")":
                if i + 1 < len(l) and l[i+1] == "*":
                    multiplicativeIndicator = True
                
                if consecutiveBracket == True:
                    right = i
                    expression = l[left:right]
                    try:
                        ans = eval(expression)
    
                        if len(operatorStack) > 1 and operatorStack[-1] == "(" and operatorStack[-2] == "o":
                            l = l[:left] + str(ans) + l[right:]
                            i = left + len(str(ans))
                            operatorStack.pop()
                            operatorStack.pop()
                        elif multiplicativeIndicator == True:
                            l = l[:left] + str(ans) + l[right:]
                            i = left + len(str(ans))
                            multiplicativeIndicator = False
                        else:
                            l = l[:left-1] + str(ans) + l[right+1:]
                            i = left - 1 + len(str(ans))
                            operatorStack.pop()
    
                        consecutiveBracket = False
                        continue
                    except:
                        expression = expression.replace("- ","-")
                        expression = expression.replace("+ ","+")
                        expression = expression.replace("+-","-")
    
                        exprList = expression.split(" ")
                        numericExprList = []
                        symbolicExpr = ""
                        for j, expr in enumerate(exprList):
                            try:
                                number = eval(expr)
                                numericExprList.append(number)
                            except:
                                if symbolicExpr == "":
                                    if expr[0] == '+':
                                        symbolicExpr = expr[1:]
                                    else:
                                        symbolicExpr = expr
                                else:
                                    if expr[0] == '+':
                                        symbolicExpr = symbolicExpr + " + " + expr[1:]
                                    elif expr[0] == '-':
                                        symbolicExpr = symbolicExpr + " - " + expr[1:]
                                    else:
                                        symbolicExpr = symbolicExpr + " + " + expr
    
                        if symbolicExpr != "" and numericExprList != []:
                            newExpression = symbolicExpr + " + " + str(sum(numericExprList))
                        elif symbolicExpr == "":
                            newExpression = str(sum(numericExprList))
                        elif numericExprList == []:
                            newExpression = symbolicExpr
    
                        if len(operatorStack) >= 2 and operatorStack[-1] == "(" and operatorStack[-2] == "o":
                            l = l[:left] + newExpression + l[right:]
                            i = left + len(newExpression) + 1
                            operatorStack.pop()
                            operatorStack.pop()
                        elif multiplicativeIndicator == True:
                            l = l[:left] + newExpression + l[right:]
                            i = left + len(newExpression) + 1
                            multiplicativeIndicator = False
                        else:
                            l = l[:left-1] + newExpression + l[right+1:]
                            i = left + len(newExpression)
                            operatorStack.pop()
                        consecutiveBracket = False
                        continue
            i += 1
        return l
    
    def getQueryExpression(self, query):
        #query = "r1(A) v r2(B),r3(C) v r4(D),r5(E),r3(F) v r6(G),r1(H),r7(I)"  #Test
        
        if query in ['true', '']:
            return '1'
        '''
        conjunctList = query.split(' v ')
        
        if len(conjunctList) > 1:
            
            newConjunctList = self.partitionUCQ(query)
            mainExpression = ''
            for conjunct in newConjunctList:
                expression = self.getConjunctExpression(conjunct)
                if expression != None:
                    if mainExpression == '':
                        mainExpression = '(1 - ' + expression + ')'
                    else:
                        mainExpression = mainExpression + '*(1 - ' + expression + ')'
            
            if mainExpression != '':
                mainExpression = '(1 - ' + mainExpression + ')'
            else:
                mainExpression = None
        else:
            mainExpression = self.getConjunctExpression(query)
            
        return mainExpression
        '''
        time_start = time()
        canonicalQuery, tableList, variableMapping = self.getCanonicalForm(query)
        canonicalExpression = getExpression(canonicalQuery, self.open_world)
        self._time_getExpression = self._time_getExpression + time() - time_start
        self._stats_getExpression += 1
        outputString = self.executeCanonicalExpression(canonicalExpression, tableList, variableMapping)
        return outputString

    def getConjunctExpression(self, query):
        # query = subpartof_10_14([),p_11(N) #Test
        
        canonicalQuery, tableList, variableMapping = self.getCanonicalForm(query)
        canonicalExpression = ""
        if canonicalQuery in self.symbolicQueryDict:
            canonicalExpression = self.symbolicQueryDict[canonicalQuery]
        else:
            time_start = time()
            canonicalExpression = getExpression(canonicalQuery, self.open_world)
            self._time_getExpression = self._time_getExpression + time() - time_start
            self._stats_getExpression += 1
            self.symbolicQueryDict[canonicalQuery] = canonicalExpression
            
        outputString = self.executeCanonicalExpression(canonicalExpression, tableList, variableMapping)
        
        return outputString
        
    
    def getLossForExample(self, hypothesis, i):
        
        if hypothesis.expressionList[i] == '':
            example = self.examples[i]
            query = self.getQueryForExample(hypothesis, example)
            outputString = self.getQueryExpression(query)
            if outputString in ["Failed to parse", None, "Query is unsafe"]:
                return "0"
            
            if outputString != "1":
                term = "(" + outputString + ")"
            else:
                term = "1"
            
            for j, predicate in enumerate(sorted(hypothesis.predicateList, reverse=True)):
                term = term.replace("z_"+predicate,"y["+str(j)+"]")
            hypothesis.expressionList[i] = term
        else:
            term = hypothesis.expressionList[i]
        
        loss = '0'
        correct = self._scores_correct[i]
        
        if self.global_score == "accuracy":    
            if i in self.CWNegatives:
                loss = loss + " +" + str(self.CWNegativeWeight) +"*" + term + ""
            elif i in self.OWNegatives:
                loss = loss + " +" + str(self.OWNegativeWeight) +"*" + term + ""
            else:
                loss = loss + " +abs(" + str(correct) + " -" + term + ")"   
            return loss[3:]
        
        elif self.global_score == "squared_loss":
            if i in self.CWNegatives:
                loss = loss + " +" + str(self.CWNegativeWeight) +"*(" + term + ")**2"
            elif i in self.OWNegatives:
                loss = loss + " +" + str(self.OWNegativeWeight) +"*(" + term + ")**2"
            else:
                loss = loss + " + (" + str(correct) + " -" + term + ")**2"
            return loss[3:] 
            
        elif self.global_score == "cross_entropy":
            if i in self.CWNegatives:
                loss = loss + " -" + str(self.CWNegativeWeight) + "*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
            elif i in self.OWNegatives:
                loss = loss + " -" + str(self.OWNegativeWeight) + "*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
            else:
                loss = loss + " -" + str(correct) + "*log(max(" + term + "," + str(self.tolerance) + ")) -(1-" + str(correct) + ")*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
            return loss[2:] 
    
    
    def learn_getLossString(self, hypothesis, scoreType = None, withTolerance = False):
        time_start = time()
        getLogger('loss').log(8, 'Hypothesis\t\t\t\t\t\t: %s \n' % str(hypothesis))
        loss = "0"
        predicateList = sorted(hypothesis.predicateList, reverse=True)
        
        if scoreType == "accuracy" or (scoreType == None and self.global_score == "accuracy"):
            if hypothesis.lossStringAcc != "":
                getLogger('probfoil').log(9, 'Returning old loss string for accuracy')
                return hypothesis.lossStringAcc
            #getLogger('probfoil').log(9, 'Query List\t\t\t\t\t\t: %s' % str(hypothesis.querySS[:10]))
            for i, correct in enumerate(self._scores_correct):
                query = hypothesis.querySS[i]
                outputString = self.getQueryExpression(query)
                
                if outputString not in ["Failed to parse", None, "Query is unsafe"]:
                    if outputString != "1":
                        term = "(" + outputString + ")"
                    else:
                        term = "1"
                    
                    for j, predicate in enumerate(predicateList):
                        term = term.replace("z_"+predicate,"y["+str(j)+"]")
                    hypothesis.expressionList[i] = term
                    
                    if i in self.CWNegatives:
                        loss = loss + " +" + str(self.CWNegativeWeight) +"*" + term + ""
                    elif i in self.OWNegatives:
                        loss = loss + " +" + str(self.OWNegativeWeight) +"*" + term + ""
                    else:
                        loss = loss + " +abs(" + str(correct) + " -" + term + ")"
                        
                else:
                    continue
        
            hypothesis.lossStringAcc = loss[3:] 
            getLogger('loss').log(8, 'Loss String\t\t\t\t\t\t: %s \n' % hypothesis.lossStringAcc)
            return hypothesis.lossStringAcc
        
        if scoreType == "squared_loss" or (scoreType == None and self.global_score == "squared_loss"):
            if hypothesis.lossStringSL != "":
                getLogger('probfoil').log(9, 'Returning old loss string for squared_loss')
                return hypothesis.lossStringSL
            #getLogger('probfoil').log(9, 'Query List\t\t\t\t\t\t: %s' % str(hypothesis.querySS[:10]))
            for i, correct in enumerate(self._scores_correct):
                query = hypothesis.querySS[i]
                outputString = self.getQueryExpression(query)
                
                if outputString not in ["Failed to parse", None, "Query is unsafe"]:
                    if outputString != "1":
                        term = "(" + outputString + ")"
                    else:
                        term = "1"
                    
                    for j, predicate in enumerate(predicateList):
                        term = term.replace("z_"+predicate,"y["+str(j)+"]")
                    hypothesis.expressionList[i] = term
                    
                    if i in self.CWNegatives:
                        loss = loss + " +" + str(self.CWNegativeWeight) +"*(" + term + ")**2"
                    elif i in self.OWNegatives:
                        loss = loss + " +" + str(self.OWNegativeWeight) +"*(" + term + ")**2"
                    else:
                        loss = loss + " + (" + str(correct) + " -" + term + ")**2"
                        
                else:
                    continue
        
            hypothesis.lossStringSL = loss[3:] 
            getLogger('loss').log(8, 'Loss String\t\t\t\t\t\t: %s \n' % hypothesis.lossStringSL)
            return hypothesis.lossStringSL
        
        elif scoreType == "cross_entropy" or (scoreType == None and self.global_score == "cross_entropy"):
            if hypothesis.lossStringCE != "":
                getLogger('probfoil').log(9, 'Returning old loss string for cross entropy')
                return hypothesis.lossStringCE
            #getLogger('probfoil').log(9, 'Query List\t\t\t\t\t\t: %s' % str(hypothesis.querySS[:10]))
            for i, correct in enumerate(self._scores_correct):
                query = hypothesis.querySS[i]
                outputString = self.getQueryExpression(query)
                if outputString not in ["Failed to parse", None, "Query is unsafe"]:
                    if outputString != "1":
                        term = outputString
                        for j, predicate in enumerate(predicateList):
                            term = term.replace("z_"+predicate,"y["+str(j)+"]")
                        
                        if i in self.CWNegatives:
                            loss = loss + " -" + str(self.CWNegativeWeight) + "*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
                        elif i in self.OWNegatives:
                            loss = loss + " -" + str(self.OWNegativeWeight) + "*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
                        else:
                            loss = loss + " -" + str(correct) + "*log(max(" + term + "," + str(self.tolerance) + ")) -(1-" + str(correct) + ")*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
                        
                        hypothesis.expressionList[i] = term
                    else:
                        continue
                else:
                    continue

            hypothesis.lossStringCE = loss[2:] 
            getLogger('loss').log(8, 'Loss String\t\t\t\t\t\t: %s \n' % hypothesis.lossStringCE)
            return hypothesis.lossStringCE

    def getGlobalScoreCE(self, hypothesis, expression, lam):
        if 'y' not in expression:
            # The expression does not contain any variables
            return -1*eval(expression)
        
        y =[]
        for predicate in hypothesis.predicateList:
            y.append(lam[predicate])
            
        try:
            entropy = -1*eval(expression)
        except Exception as e:
            getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e)[:-1])
            entropy = None
            getLogger('probfoil').log(8, 'Exception in Global Score for entropy\t: %s' % expression)
            getLogger('probfoil').warning('y = %s' % str(y))
        return entropy
    
    def getGlobalScore(self, hypothesis, lam, scoreType = None):
        lossString = self.learn_getLossString(hypothesis, scoreType)
        gScore = 0
        
        if scoreType == "accuracy" or (scoreType == None and self.global_score == "accuracy"):
            lambdaString = lossString
            
            def evalFunc(y):
                if not isinstance(y, list):
                    y = [y]
                
                if len(y) != len(hypothesis.predicateList):
                    getLogger('probfoil').warning("Length of 'y' = %d isn't same as length of Clause List = %d" % (len(y), len(hypothesis.predicateList)))
                    return 0
                ans = 0
                predicateList = sorted(hypothesis.predicateList, reverse=True)
                    
                try:
                    expression = lambdaString
                    ans = eval(expression)
                except:
                    expression1 = lambdaString
                    for i, predicate in enumerate(predicateList):
                        if y[i] < 1:
                            logString = str(float(log(1-y[i])))
                        else:
                            logString = "-float('inf')"
                        expression1 = expression1.replace("log(-z_"+ predicate + " + 1)",logString)
                    #logValue = float(log(1-y))
                    #expression1 = lambdaString.replace("log(-z + 1)", str(logValue))
                    logList, logLocation = getLogList(expression1)
                    logOutput = []
                    for item in logList:
                        try:
                            for i, predicate in enumerate(predicateList):
                                item = item.replace("z_" + predicate,str(y[i]))
                            output = eval(item)
                        except:
                            getLogger('probfoil').warning("Exception occurred in logOutput")
                            getLogger('probfoil').warning("item\t\t\t\t:" + item)
                            getLogger('probfoil').warning("Lambda Values\t\t\t\t:" + str(y))
                            output = 0.0
                        logOutput.append(output)     
                    #At each logLocation, replace the log with either the output or with -Inf
                    start = 0
                    expression2 = ""
                    for i, (j, k) in enumerate(logLocation):
                        expression2 = expression2 + expression1[start:j]
                        if logOutput[i] > 0:
                            expression2 = expression2 + "log(" + str(logOutput[i]) + ")"
                        else:
                            expression2 = expression2 + "-float('inf')"
                        start = k
                    expression2 = expression2 + expression1[start:]
                    try:
                        ans = eval(expression2)
                    except Exception as e:
                        getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e)[:-1])
                        getLogger('probfoil').warning('Exception\t\t\t\t\t: %s' % expression2)
                return ans
            
            lamList = []
            for predicate in hypothesis.predicateList:
                lamList.append(lam[predicate])

            try:
                loss = evalFunc(lamList)
            except Exception as e:
                getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e)[:-1])
                loss = None
                getLogger('probfoil').log(8, 'Exception in Global Score for accuracy\t: %s' % lossString)
                getLogger('probfoil').warning('y = %s' % str(y))
                
            gScore = 1 - (loss/(self.totalWeightedExamples))
            getLogger('probfoil').debug('GScore - Accuracy\t\t\t\t: %s' % str(gScore))
            
        if scoreType == "squared_loss" or (scoreType == None and self.global_score == "squared_loss"):
            lambdaString = lossString
            
            def evalFunc1(y):
                if not isinstance(y, list):
                    y = [y]
                
                if len(y) != len(hypothesis.predicateList):
                    getLogger('probfoil').warning("Length of 'y' = %d isn't same as length of Clause List = %d" % (len(y), len(hypothesis.predicateList)))
                    return 0
                ans = 0
                predicateList = sorted(hypothesis.predicateList, reverse=True)
                
                try:
                    expression = lambdaString
                    ans = eval(expression)
                except:
                    expression1 = lambdaString
                    for i, predicate in enumerate(predicateList):
                        if y[i] < 1:
                            logString = str(float(log(1-y[i])))
                        else:
                            logString = "-float('inf')"
                        expression1 = expression1.replace("log(-z_"+ predicate + " + 1)",logString)
                    #logValue = float(log(1-y))
                    #expression1 = lambdaString.replace("log(-z + 1)", str(logValue))
                    logList, logLocation = getLogList(expression1)
                    logOutput = []
                    for item in logList:
                        try:
                            for i, predicate in enumerate(predicateList):
                                item = item.replace("z_" + predicate,str(y[i]))
                            output = eval(item)
                        except:
                            getLogger('probfoil').warning("Exception occurred in logOutput")
                            getLogger('probfoil').warning("item\t\t\t\t:" + item)
                            getLogger('probfoil').warning("Lambda Values\t\t\t\t:" + str(y))
                            output = 0.0
                        logOutput.append(output)     
                    #At each logLocation, replace the log with either the output or with -Inf
                    start = 0
                    expression2 = ""
                    for i, (j, k) in enumerate(logLocation):
                        expression2 = expression2 + expression1[start:j]
                        if logOutput[i] > 0:
                            expression2 = expression2 + "log(" + str(logOutput[i]) + ")"
                        else:
                            expression2 = expression2 + "-float('inf')"
                        start = k
                    expression2 = expression2 + expression1[start:]
                    try:
                        ans = eval(expression2)
                    except Exception as e:
                        getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e)[:-1])
                        getLogger('probfoil').warning('Exception\t\t\t\t\t: %s' % expression2)
                return ans
            
            lamList = []
            for predicate in hypothesis.predicateList:
                lamList.append(lam[predicate])

            try:
                loss = evalFunc1(lamList)
            except Exception as e:
                getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e)[:-1])
                loss = None
                getLogger('probfoil').log(8, 'Exception in Global Score for squared_loss\t: %s' % lossString)
                getLogger('probfoil').warning('y = %s' % str(y))
                
            gScore = -1*loss
            getLogger('probfoil').debug('GScore - Squared Loss\t\t\t: %s' % str(gScore))
            
        elif scoreType == "cross_entropy" or (scoreType == None and self.global_score == "cross_entropy"):
            gScore = self.getGlobalScoreCE(hypothesis, lossString, lam)
            getLogger('probfoil').debug('GScore - Cross Entropy\t\t\t: %s' % str(gScore))
            
        return gScore
    
    def getGlobalScore_again(self, hypothesis, lam, scoreType = None):
        
        time_start = time()
        getLogger('loss').log(8, 'Hypothesis\t\t\t\t\t\t: %s \n' % str(hypothesis))
        loss = 0
        gScore = 0
        
        y =[]
        for predicate in hypothesis.predicateList:
            y.append(lam[predicate])
        
        if scoreType == "accuracy" or (scoreType == None and self.global_score == "accuracy"):
            for i, (correct, term) in enumerate(zip(hypothesis.scores, self._scores_correct)):
                term = hypothesis.scores[i]
                if i in self.CWNegatives:
                    loss = loss + self.CWNegativeWeight*term
                elif i in self.OWNegatives:
                    loss = loss + self.OWNegativeWeight*term
                else:
                    loss = loss + abs(correct-term)
            
            gScore = 1 - (loss/(self.totalWeightedExamples))
            getLogger('probfoil').debug('Loss - Absolute Error\t\t\t: %s' % str(loss))
            getLogger('probfoil').debug('GScore - totalWeightedExamples\t: %s' % str(self.totalWeightedExamples))
            getLogger('probfoil').debug('GScore - Weighted Accuracy\t\t: %s' % str(gScore))
            
        elif scoreType == "squared_loss" or (scoreType == None and self.global_score == "squared_loss"):
            for i, (correct, term) in enumerate(zip(hypothesis.scores, self._scores_correct)):
                term = hypothesis.scores[i]
                if i in self.CWNegatives:
                    loss = loss + self.CWNegativeWeight*(term**2)
                elif i in self.OWNegatives:
                    loss = loss + self.OWNegativeWeight*(term**2)
                else:
                    loss = loss + abs(correct-term)**2
            
            gScore = -1*loss
            getLogger('probfoil').debug('Loss - squared_loss\t\t\t: %s' % str(loss))
            getLogger('probfoil').debug('GScore - squared_loss\t\t\t: %s' % str(gScore))    
            
        elif scoreType == "cross_entropy" or (scoreType == None and self.global_score == "cross_entropy"):
            for i, (correct, term) in enumerate(zip(hypothesis.scores, self._scores_correct)):
                term = hypothesis.scores[i]
                if i in self.CWNegatives:
                    loss = loss - self.CWNegativeWeight*log(max(1-(term),self.tolerance))
                elif i in self.OWNegatives:
                    loss = loss - self.OWNegativeWeight*log(max(1-(term),self.tolerance))
                else:
                    loss = loss - correct*log(max(term,self.tolerance)) - (1-correct)*log(max(1-term,self.tolerance))
            
            gScore = -1*loss
            getLogger('probfoil').debug('Loss - cross_entropy\t\t\t: %s' % str(loss))
            getLogger('probfoil').debug('GScore - cross_entropy\t\t\t: %s' % str(gScore))
        
        getLogger('loss').log(8, 'Loss Value\t\t\t\t\t\t: %s \n' % str(loss))
        return gScore
    
    def learn_getGradient(self, lossString):
        exec("lossFunc = lambda y : " + lossString)
        gradient, hessian = gh(lossFunc)
        return gradient
    
    def learn_initializeLambdas(self, hypothesis, learnAllRules = False):
        oldLamList = []
        getLogger('probfoil').log(9, str(hypothesis.to_clauses()))
        
        if learnAllRules:
            y = []
            for j, predicate in enumerate(hypothesis.predicateList):
                if len(predicate) > 2 and predicate[:3] == "p_0":
                    y.append(self.regularize(self.lams[predicate], 5))
                elif len(predicate) > 2 and predicate[:2] == "p_":
                    
                    i = 2
                    while i < len(predicate) and predicate[i].isdigit():
                        i += 1
                    index = int(predicate[2:i])

                    confidence = float(self.stdConfidenceList[index-1])
                    prob = self.rule_getConditionalProbability(index-1)
                    if confidence != prob:
                        getLogger('probfoil').log(9, 'Amie Confidence Value for %s is %s' % (str(hypothesis.to_clauses()[index+1]), str(confidence)))
                        getLogger('probfoil').log(9, 'Conditional Probability for %s is %s' % (str(hypothesis.to_clauses()[index+1]), str(prob)))
                    else:    
                        getLogger('probfoil').log(9, 'Conditional Probability for %s is %s' % (str(hypothesis.to_clauses()[index+1]), str(prob)))
                    y.append(self.regularize(prob, 5))
                    #y.append(prob)
                else:
                    if self.cwLearning:
                        y.append(0.0)
                        continue
                    k = 1
                    for base in self.predicateDict[predicate]:
                        k = k*len(self.constantDict[base])
                    y.append(self.regularize(float(self.closedWorldTotal[predicate])/k, 5))
            getLogger('probfoil').info('%-*s: %s' % (self.pad, "Lambdas initialized to", str(y)))
            return y
        
        if len(hypothesis.to_clauses()) == 3:
            # Hypothesis has 'Fail','True' and 1st Rule. Running SGD for the first time.
            #indices = {0:hypothesis.predicateList.index('p_0'), 1:hypothesis.predicateList.index('p_1')}
            
            y = []
            for j, predicate in enumerate(hypothesis.predicateList):
                if len(predicate) > 2 and predicate[:3] == "p_0":
                    k = 1
                    for base in self.predicateDict[self.targetPredicate]:
                        k = k*len(self.constantDict[base])
                    
                    y.append(self.regularize(float(self.closedWorldTotal[self.targetPredicate])/k, 5))
                elif len(predicate) > 2 and predicate[:3] == "p_1":
                    prob = float(self.stdConfidenceList[self.selectedAmieRules[-1]])
                    getLogger('probfoil').log(9, 'Conditional Probability for %s is %s' % (str(hypothesis.to_clauses()[2]), str(prob)))
                    y.append(self.regularize(prob, 5))
                else:
                    if self.cwLearning:
                        y.append(0.0)
                        continue
                    k = 1
                    for base in self.predicateDict[predicate]:
                        k = k*len(self.constantDict[base])
                    y.append(self.regularize(float(self.closedWorldTotal[predicate])/k, 5))
            getLogger('probfoil').info('%-*s: %s' % (self.pad, "Lambdas initialized to", str(y)))
            return y
        else:
            y = []
            for j, predicate in enumerate(hypothesis.predicateList):
                if len(predicate) > 2 and predicate[:2] == "p_":
                    index = int(predicate[2:])
                    if index == len(hypothesis.to_clauses()) - 2:
                        prob = float(self.stdConfidenceList[self.selectedAmieRules[-1]])
                        getLogger('probfoil').log(9, 'Conditional Probability for %s is %s' % (str(hypothesis.to_clauses()[index+1]), str(prob)))
                        y.append(self.regularize(prob, 5))
                    else:
                        y.append(self.regularize(self.lams[predicate], 5))
                else:
                    if self.cwLearning:
                        y.append(0.0)
                        continue
                    if self.lams[predicate] == 0:
                        k = 1
                        for base in self.predicateDict[predicate]:
                            k = k*len(self.constantDict[base])
                        y.append(self.regularize(float(self.closedWorldTotal[predicate])/k, 5))
                    else:
                        y.append(self.regularize(self.lams[predicate], 5))
            getLogger('probfoil').info('%-*s: %s' % (self.pad, "Lambdas initialized to", str(y)))
            return y
    
    def learn_stochasticGradientDescent(self, hypothesis):
        time_start = time()
        
        oldLamList = self.learn_initializeLambdas(hypothesis, self.learnAllRules)
        newLamList = oldLamList
        iterations = self.iterations
        
        #globalLoss = self.learn_getLossString(hypothesis) 
        #lossList = []
        #lamList = []
        
        # Full Batch
        fixedPointReached = False
        sameCount = 0
        superOldLamList = copy(oldLamList)
        errorCount = 0
        updateCount = 0
        for k in range(0, iterations):
            i = random.randint(0, self.totalExamples - 1)
            
            #term = hypothesis.expressionList[i]
            term = self.getLossForExample(hypothesis, i)
            
            if self.global_score == "cross_entropy":
                if term not in ["Failed to parse", None, "Query is unsafe"]:
                
                    if i in self.CWNegatives:
                        loss = " -" + str(self.CWNegativeWeight) + "*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
                    elif i in self.OWNegatives:
                        loss = " -" + str(self.OWNegativeWeight) + "*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
                    else:
                        correct = self._scores_correct[i]
                        loss = " -" + str(correct) + "*log(max(" + term + "," + str(self.tolerance) + ")) -(1-" + str(correct) + ")*log(max(1-(" + term + ")," + str(self.tolerance) + "))"
                    
                else:
                    continue
            
            elif self.global_score == "accuracy":
                if term not in ["Failed to parse", None, "Query is unsafe"]:
                    if i in self.CWNegatives:
                        loss = str(self.CWNegativeWeight) +"*" + term + ""
                    elif i in self.OWNegatives:
                        loss = str(self.OWNegativeWeight) +"*" + term + ""
                    else:
                        loss = "abs(" + str(self._scores_correct[i]) + " -" + term + ")"
                else:
                    continue
            
            elif self.global_score == "squared_loss":
                if term not in ["Failed to parse", None, "Query is unsafe"]:
                    if i in self.CWNegatives:
                        loss = str(self.CWNegativeWeight) +"*(" + term + ")**2"
                    elif i in self.OWNegatives:
                        loss = str(self.OWNegativeWeight) +"*(" + term + ")**2"
                    else:
                        loss = "(" + str(self._scores_correct[i]) + " -" + term + ")**2"
                else:
                    continue
            
            expression = loss
            #getLogger('probfoil').debug('%d.\tLoss = %s' % (i, str(loss)))
            exec("evalFunc = lambda y : " + expression)
            gradient, hessian = gh(evalFunc)
            
            try:
                #Update Lambdas for Rule Weights
                grad = gradient(oldLamList)
                #grad = evalFunc(oldLamList).gradient(oldLamList)
                
                oldgrad = grad
                grad = [self.learningRate[0]*component for component in grad]
                maxRatio = 1
                for j, predicate in enumerate(hypothesis.predicateList):
                    if len(predicate) > 2 and predicate[:2] == "p_":
                        if maxRatio < abs(grad[j]/self.maxIncrement[0]):
                            maxRatio = abs(grad[j]/self.maxIncrement[0])
                for j, predicate in enumerate(hypothesis.predicateList):
                    if len(predicate) > 2 and predicate[:2] == "p_":
                        newLamList[j] = oldLamList[j] - grad[j]/maxRatio
                        #newLamList[j] = oldLamList[j] - grad[j]
                        if newLamList[j] < 5*self.tolerance:
                            newLamList[j] = 5*self.tolerance
                        elif newLamList[j] > 1 - 5*self.tolerance:
                            newLamList[j] = 1-5*self.tolerance
                    elif self.cwLearning == False:
                        if newLamList[j] < 5*self.tolerance:
                            newLamList[j] = 5*self.tolerance
                        elif newLamList[j] > 1 - 5*self.tolerance:
                            newLamList[j] = 1-5*self.tolerance
                        
                oldLamList = copy(newLamList)
                
                #getLogger('probfoil').debug('%d.\tOld Gradient = %s.\tNew Gradient = %s' % (i, str(oldgrad), str(grad)))
                #getLogger('probfoil').debug('%d.\tOld = %s.\tRatio = %s.\tNew = %s' % (i, str(grad), maxRatio, str([item/maxRatio for item in grad])))
                
                if self.cwLearning == False:
                    #Update Lambdas for Non-target Predicates
                    grad = gradient(oldLamList)
                    #grad = evalFunc(oldLamList).gradient(oldLamList)
                    
                    oldgrad = grad
                    grad = [self.learningRate[1]*component for component in grad]
                    
                    maxRatio = 1
                    for j, predicate in enumerate(hypothesis.predicateList):
                        if len(predicate) <= 2 or predicate[:2] != "p_":
                            if maxRatio < abs(grad[j]/self.maxIncrement[1]):
                                maxRatio = abs(grad[j]/self.maxIncrement[1])
                    
                    for j, predicate in enumerate(hypothesis.predicateList):
                        if len(predicate) <= 2 or predicate[:2] != "p_":
                            newLamList[j] = oldLamList[j] - grad[j]/maxRatio
                            #newLamList[j] = oldLamList[j] - grad[j]
                        if newLamList[j] < 5*self.tolerance:
                            newLamList[j] = 5*self.tolerance
                        elif newLamList[j] > 1 - 5*self.tolerance:
                            newLamList[j] = 1-5*self.tolerance
                
                if self.terminateAtFixedPoint and newLamList == superOldLamList:
                    if sameCount == 100:
                        fixedPointReached = True
                    else:
                        sameCount += 1
                else:
                    sameCount = 0
                oldLamList = copy(newLamList)
                superOldLamList = copy(newLamList)
                #getLogger('probfoil').debug('%d.\tOld Gradient = %s.\tNew Gradient = %s' % (i, str(oldgrad), str(grad)))
                #getLogger('probfoil').debug('%d.\tOld = %s.\tRatio = %s.\tNew = %s' % (i, str(grad), maxRatio, str([item/maxRatio for item in grad])))
                #getLogger('probfoil').debug('%d.\tLambdas = %s' % (i, str(newLamList)))
                
                if k % self.stepCheck == 0:
                    getLogger('probfoil').debug(str(time()) + ' : ' + str(k) + ' iterations completed out of ' + str(iterations))
                '''
                if k % self.stepCheck == 0 or k == iterations - 1 or fixedPointReached:
                    y = newLamList
                    loss = eval(globalLoss)
                    getLogger('probfoil').debug('%d Loss: %s ==> %s' % (k, str(newLamList), str(loss)))
                    lamList.append(copy(newLamList))
                    lossList.append(loss)
                    if k == iterations - 1:
                        # Hard checking for loss in closed world scenario 
                        y = []
                        for predicate in hypothesis.predicateList:
                            if predicate[:2] == "p_":
                                ruleNumber = int(predicate[2])
                                prob = hypothesis.probabilityList[ruleNumber]
                                if prob > 1 - self.tolerance:
                                    prob = 1 - self.tolerance
                                y.append(prob)
                            else:
                                y.append(0)
                        loss = eval(globalLoss)
                        getLogger('probfoil').debug('%s Loss: %s ==> %s' % ("Closed World", str(y), str(loss)))
                        #lamList.append(copy(y))
                        #lossList.append(loss)
                '''
                
                if self.terminateAtFixedPoint and fixedPointReached:
                    getLogger('probfoil').debug('Fixed point reach at iteration: ' + str(k))
                    break
                
                updateCount += 1
            except Exception as e:
                #getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e))
                #getLogger('probfoil').warning('Exception in gradient\t\t\t: %s, %s' % (str(oldLamList), expression))
                #getLogger('probfoil').warning('Example[%s] : %s' % (str(i), str(self.examples[i])))
                errorCount += 1
            oldLamList = newLamList
        
        selectedLamList = newLamList
        #selectedLamList, minLoss = min(zip(lamList, lossList), key=lambda v: v[1])
        #minIndex, minLoss = min(enumerate(lossList), key=lambda v: v[1])
        #selectedLamList = lamList[minIndex]
        #getLogger('probfoil').debug('Loss List\t\t\t\t\t\t: ' + str(lossList))
        #getLogger('probfoil').debug('Selected Iteration of SGD \t\t: ' + str(minIndex*self.stepCheck))
        
        newLam = copy(self.lams)
        for predicate, lam in zip(hypothesis.predicateList, selectedLamList):
            newLam[predicate] = lam
        
        getLogger('probfoil').debug('Updated Lambda\t\t\t\t\t: ' + str(newLam))
        
        time_total = time() - time_start
        self._time_optimization += time_total
        getLogger('probfoil').debug('Time - SGD\t\t\t\t\t\t: %.1fs' % time_total)
        
        return newLam#, minLoss
    
    def learn_updateScores(self, hypothesis, newLam):
        
        if self.learnAllRules:
            rule = hypothesis
            ruleCount = len(hypothesis.to_clauses()) - 2
            while rule.previous != None:
                rule.max_x = newLam["p_"+str(ruleCount)]
                if rule.max_x > 1 - self.tolerance:
                    rule.set_rule_probability(None)
                else:
                    rule.set_rule_probability(rule.max_x)
                ruleCount -= 1
                rule = rule.previous
        else:
            def getUpdatedScores(rule, ruleCount):
                if rule.previous is None:
                    ruleCount = -1
                    return ruleCount, rule.scores
                else:
                    ruleCount, updatedScores = getUpdatedScores(rule.previous, ruleCount)
                    ruleCount += 1
                    
                    self.canonicalRuleList = []
                    if self.learnAllRules == False:
                        rule.oldProb = rule.max_x
                        rule.oldScores = rule.scores
                    rule.max_x = newLam["p_"+str(ruleCount)]
                    self._select_rule(rule)
                    
                    if (self.global_score == "accuracy" and rule.lossStringAcc == "") or (self.global_score == "cross_entropy" and rule.lossStringCE == ""):
                        rule.scores = self._compute_scores_predict_again(rule)
                    else:
                        y =[]
                        for predicate in hypothesis.predicateList:
                            y.append(newLam[predicate])
                            
                        for i, expression in enumerate(rule.expressionList):
                            try:
                                if expression != '':
                                    rule.scores[i] = eval(expression)
                            except Exception as e:
                                getLogger('probfoil').error('Exception Occurred\t\t\t\t: %s' % str(e))
                                getLogger('probfoil').warning('Exception occurred in self.learn_updateScores with %dth expression: (y = %s) %s' %(i, str(y), expression))
                    
                    return ruleCount, rule.scores
            
            
            ruleCount, hypothesis.scores = getUpdatedScores(hypothesis, -1)
        
        return hypothesis
    
    def learn_pruneHypothesis(self, hypothesis):
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Semi - Final Hypothesis", str(hypothesis.to_clauses())))
        # Edit the weights of the rules to 1 from 1-self.tolerance and remove those rules whose weights are <= self.tolerance
        rule = hypothesis
        previousRule = rule
        pruneIndicator = False
        while rule.previous != None:
            prob = rule.get_rule_probability()
            if prob == None:
                prob = 1
            if prob >= 1 - 6*self.tolerance:
                rule.set_rule_probability(None)
            elif prob <= 6*self.tolerance:
                #No need to update weighted accuracy when the rule is dropped. The dropped rule was inconsequential.
                previousRule.previous = rule.previous
                rule = rule.previous
                pruneIndicator = True
                continue
            previousRule = rule    
            rule = rule.previous
        
        # Drop first rule if it's probability is insignificant
        prob = hypothesis.get_rule_probability()
        if prob == None:
            prob = 1
        if hypothesis.previous.previous != None and prob <= 6*self.tolerance:
            hypothesis = hypothesis.previous
            pruneIndicator = True
        
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Final Hypothesis", str(hypothesis.to_clauses())))
        return hypothesis, pruneIndicator
    
    def learn_closePSQLDB(self, drop = False):
        # ----------------------- Close the PSQL connection and drop the database ------------------------
        
        self.cursor.close()
        self.conn.close()
        
        #conn = psycopg2.connect(dbname = 'postgres', user = self.user)
        conn = self.connect_PSQLDB(None)
        conn.autocommit = True
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        if drop:
            cursor.execute("DROP DATABASE " + self.name + ";")
            getLogger('probfoil').info('DROP DATABASE\t\t\t\t\t: %s' % self.name)
        cursor.close()
        conn.close()
        
    def learn(self):
        self.learn_readFile()
        startLearn = time()
        
        # ------------------------------ Get Negative Examples using AMIE+ -------------------------------
        self.TSVFile = self.InputFile[:self.InputFile.rfind(".")].replace(".","_") + "_amie.tsv"
        self.breakNow = False
        self.convertProblogToAmie()
        self.AmieRuleList, self.coverageList, self.stdConfidenceList, self.pcaConfidenceList = self.getAmieRules()
        s = '================ Candidate Rules obtained from AMIE+ ================\n'
        for candidate, coverage, stdConfidence, pcaConfidence in zip(self.AmieRuleList, self.coverageList, self.stdConfidenceList, self.pcaConfidenceList):
            s += str(candidate) + '\t' + str(coverage) + '\t' + str(stdConfidence) + '\t' + str(pcaConfidence) + '\n'
        s += '===================================================================='
        getLogger('probfoil').debug(s)
        
        self.selectedAmieRules = []
        self.trueAdded = False
        self.failAdded = True
        failedAttempts = 0
        self.scoreList = self.stdConfidenceList
        
        amieHypothesis = self.getAmieHypothesis()
        if self.breakNow:
            return amieHypothesis
        self.train_examples = copy(self._examples)
        self.rule_getNegativeExamples(amieHypothesis)
        # ---------------------------------------- Start Learning ----------------------------------------
        
        if self.learnAllRules:
            k = 1
            for base in self.predicateDict[self.targetPredicate]:
                k = k*len(self.constantDict[base])
            
            self.lams['p_0'] = self.regularize(float(self.closedWorldTotal[self.targetPredicate])/k, 1) 
            for i, confidence in enumerate(self.stdConfidenceList):
                self.lams['p_'+str(i+1)] = self.regularize(float(confidence), 1)
            getLogger('probfoil').info('%-*s: %s' % (self.pad, "Self.lams", str(self.lams)))
            
            
            next_hypothesis = amieHypothesis
            next_hypothesis.accuracy = 0
            next_hypothesis.scores = [1.0] * self.totalExamples
            #next_hypothesis.correct = self._scores_correct
            next_hypothesis.expressionList = [""]*self.totalExamples
            next_hypothesis.replaceableQuery = ''
            next_hypothesis.lossStringAcc = ''
            next_hypothesis.lossStringSL = ''
            next_hypothesis.lossStringCE = ''
            next_hypothesis.score = 0.0
            #getLogger('probfoil').info('%-*s: %s' % (self.pad, "Hypothesis", str(next_hypothesis.to_clauses())))
            self.trueAdded = True
            hypothesis = next_hypothesis
        else:
            hypothesis = self.initial_hypothesis()
            counter = self.loadRule
            name = self.InputFile[self.InputFile.rfind("/")+1:self.InputFile.rfind(".")].replace(".","_").lower()
        
        current_score = None
        
        while True:
            if self.learnAllRules == False:
                if self.loadRule != None:
                    try:
                        filename = 'Logs/' + name + "_" + str(counter)+'.pckl'
                        f = open(filename, 'rb')
                        obj = pickle.load(f)
                        self._examples = obj[0]
                        self._scores_correct = obj[1]
                        self.constantDict = obj[2]
                        self.closedWorldTotal = obj[3]
                        self.targetPredicate = obj[4]
                        self.targetArity = obj[5]
                        #self.hypothesisAscii = obj[6]
                        self.hypothesisFreeVars = obj[6]
                        self._target = obj[7]
                        self.predicateDict = obj[8]
                        self.lams = obj[9]
                        f.close()
                    except:
                        filename = 'Logs/' + name + "_" + str(counter)+'.pckl'
                        f = open(filename, 'wb')
                        obj = []
                        obj.append(self._examples)
                        obj.append(self._scores_correct)
                        obj.append(self.constantDict)
                        obj.append(self.closedWorldTotal)
                        obj.append(self.targetPredicate)
                        obj.append(self.targetArity)
                        #obj.append(self.hypothesisAscii)
                        obj.append(self.hypothesisFreeVars)
                        obj.append(self._target)
                        obj.append(self.predicateDict)
                        obj.append(self.lams)
                        obj.append(hypothesis)
                        pickle.dump(obj, f)
                        f.close()
                    counter += 1
                
                next_hypothesis = self.best_rule(hypothesis)
                if self.candidate_rules == "amie" and self.breakNow:
                    break
            
            getLogger('probfoil').info('%-*s: %s' % (self.pad, "Hypothesis", str(next_hypothesis.to_clauses())))
            
            self.learn_parseRules(next_hypothesis)
            self.learn_getQueryString(next_hypothesis)
            if self.open_world:
                #self.learn_getQueryList(next_hypothesis)
                #start = time()
                #next_hypothesis.gscore = self.getGlobalScore(next_hypothesis, self.lams)
                #end = time() - start
                #getLogger('probfoil').info('GScore before optimization\t\t: %s' % str(next_hypothesis.gscore))
                #getLogger('probfoil').info('Got GScore in\t\t\t\t\t: %ss' % str(end))
                
                newLam = self.lams
                if len(next_hypothesis.predicateList) > 0:
                    if self.optimization_method == "incremental":
                        #newLam, loss = self.learn_stochasticGradientDescent(next_hypothesis)
                        newLam = self.learn_stochasticGradientDescent(next_hypothesis)
                        #next_hypothesis.gscore = -1*loss
                    elif self.optimization_method == "batch":
                        newLam = self.learn_optimizeLambda(next_hypothesis)
                    
                    self.learn_updateScores(next_hypothesis, newLam)
                    # Update the rule scores one by one based on the updated probabilities of rules
                    # Why? To select the next rule properly from the candidate rules
                    # Should I update the rule.scores with new Lambdas too? Yes
                else:
                    newLam = copy(self.lams)
                    
                #next_hypothesis.gscore = self.getGlobalScore(next_hypothesis, newLam)
               # next_hypothesis.accuracy = accuracy(next_hypothesis)
                #getLogger('probfoil').info('GScore after optimization\t\t: %s' % str(next_hypothesis.gscore))
                
            # --------------------------------------- Continue Learning --------------------------------------
            time_start = time()
            if self.learnAllRules == False:
                getLogger('probfoil').info('Rule Learned\t\t\t\t\t\t: %s' % next_hypothesis)
            
            #s = significance(next_hypothesis)
            #if self._min_significance is not None and s < self._min_significance:
            #    getLogger('probfoil').warning('Significance of %s < Minimum Significance Threshold of %s' % (s, self._min_significance))
            #    break
            
            #getLogger('probfoil').debug('Current Score\t\t\t\t\t: ' + str(current_score))
            #getLogger('probfoil').debug('New Score\t\t\t\t\t\t: ' + str(next_hypothesis.gscore))
            
            hypothesis = next_hypothesis
            
            if self.open_world:
                self.lams = newLam
                
            time_total = time() - time_start
            getLogger('probfoil').debug('Time - deciding on hypothesis\t: %.1fs\n' % time_total)
            
            if self.interrupted or self.learnAllRules:
                break
            if hypothesis.get_literal() and hypothesis.get_literal().functor == '_recursive':
                break   # can't extend after recursive
        
        '''
        if hasattr(hypothesis, 'gscore'):
            gscore = hypothesis.gscore
        else:
            gscore = None
        '''
 
        hypothesis, pruneIndicator = self.learn_pruneHypothesis(hypothesis)
        '''
        if pruneIndicator:
            #if gscore != None:
            #    hypothesis.gscore = gscore
            
            self.learn_parseRules(hypothesis)
            self.learn_getQueryString(hypothesis)
            hypothesis.replaceableQuery = ''
            self.learn_getQueryList(hypothesis)
        
            if hypothesis.previous is not None:
                hypothesis.previous.scores = [0.0]*self.totalExamples
            if hypothesis.parent is not None:
                hypothesis.parent.scores = [1.0]*self.totalExamples
        
        hypothesis.scores = self._compute_scores_predict_again(hypothesis)
        
        if hasattr(hypothesis, 'gscore'):
            if self.global_score == "accuracy" and hypothesis.gscore != None:
                hypothesis.weightedAccuracy = hypothesis.gscore
            elif self.global_score == "cross_entropy" and hypothesis.gscore != None:
                hypothesis.crossEntropy = hypothesis.gscore
            elif self.global_score == "squared_loss" and hypothesis.gscore != None:
                hypothesis.squaredLoss = hypothesis.gscore
        
        if not(hasattr(hypothesis, 'weightedAccuracy') and hypothesis.weightedAccuracy != ""):
            hypothesis.weightedAccuracy = self.getGlobalScore_again(hypothesis, self.lams, scoreType = "accuracy")
        if not(hasattr(hypothesis, 'crossEntropy') and hypothesis.crossEntropy != ""):
            hypothesis.crossEntropy = self.getGlobalScore_again(hypothesis, self.lams, scoreType = "cross_entropy")
        if not(hasattr(hypothesis, 'squaredLoss') and hypothesis.squaredLoss != ""):
            hypothesis.squaredLoss = self.getGlobalScore_again(hypothesis, self.lams, scoreType = "squared_loss")
        
        hypothesis.correct = self._scores_correct
        hypothesis.tp, hypothesis.fp, hypothesis.tn, hypothesis.fn = rates(hypothesis)
        hypothesis.precision = precision(hypothesis)
        hypothesis.recall = recall(hypothesis)
        '''
        self.learn_closePSQLDB(drop = True)
        self._time_learn = time() - startLearn
        
        return hypothesis

    def rule_intersect2Tables(self, mainTable, mainVarList, newTable, newVarList):
        
        unifiedTableName = "dummy" + str(self.dummyCount)
        self.dummyCount += 1
        
        unifiedVarList = mainVarList
        
        if mainTable != newTable:
            firstTableIdentifier = mainTable
            secondTableIdentifier = newTable
        else:
            firstTableIdentifier = 'table0'
            secondTableIdentifier = 'table1'
        
        whereList = []
        selectList = []
        for i, var in enumerate(mainVarList):
            selectList.append(firstTableIdentifier + '.v' + str(i)) 
        for i, var in enumerate(newVarList):
            if var not in mainVarList:
                unifiedVarList.append(newVarList[i])
                selectList.append(secondTableIdentifier + '.v' + str(i))
            else:
                whereList.append(firstTableIdentifier + '.v' + str(mainVarList.index(var)) + ' = ' + secondTableIdentifier + '.v' + str(i))
        selectList = [ item + ' as v' + str(i) for i, item in enumerate(selectList)]

        selectString = ', '.join(selectList)
        whereString = ' and '.join(whereList)
        
        if whereString == '':
            #Take Cross join of both tables
            self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
            sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct ' + selectString + ' from ' + mainTable + ' as ' + firstTableIdentifier + ' cross join ' + newTable + ' as ' + secondTableIdentifier + ');'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
        else:
            #Take Inner join with respect to whereString
            self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
            sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct ' + selectString + ' from ' + mainTable + ' as ' + firstTableIdentifier + ' inner join ' + newTable + ' as ' + secondTableIdentifier + ' on ' + whereString + ');'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
            
        return unifiedTableName, unifiedVarList
    
    def rule_unify2Tables(self, firstTable, firstVarList, secondTable, secondVarList):
        unifiedTableName = "dummy" + str(self.dummyCount)
        self.dummyCount += 1
        
        #Align the first and second select strings to ['A','B']
        firstSelectList = ["", ""]
        for i, var in enumerate(firstVarList):
            if var == 'A':
                firstSelectList[0] = firstTable + '.v' + str(i) + ' as v0'
            elif var == 'B':
                firstSelectList[1] = firstTable + '.v' + str(i) + ' as v1' 
        firstSelectString = ', '.join(firstSelectList)
        
        secondSelectList = ["", ""]
        for i, var in enumerate(secondVarList):
            if var == 'A':
                secondSelectList[0] = secondTable + '.v' + str(i) + ' as v0'
            elif var == 'B':
                secondSelectList[1] = secondTable + '.v' + str(i) + ' as v1' 
        secondSelectString = ', '.join(secondSelectList)
        
        #Unify both tables
        self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
        #sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct ' + firstSelectString + ' from ' + firstTable + ' union select distinct ' + secondSelectString + ' from ' + secondTable + ');'
        sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct ' + firstTable + '.v0 as v0, ' + firstTable + '.v1 as v1 from ' + firstTable + ' union select distinct ' + secondTable + '.v0 as v0, ' + secondTable + '.v1 as v1 from ' + secondTable + ');'
        getLogger('probfoil').log(9, sqlQuery)
        self.cursor.execute(sqlQuery)
            
        return unifiedTableName
        
        
    def rule_predict1rule(self, rule):
        # r(A,B):-r1(A,C),r2(B,C),r3(C,D),r4(E).
        # Assuming target arity = 2
        # varDict = {'A':[(r1,0)], 'B':[(r2,0)], 'C':[(r1,1),(r2,1),(r3,0)], 'D':[(r3,1)], 'E':[(r4,0)]}
        # varList = [['A','C'],['B','C'],['C','D'],['E']]
        # tableList = ['r1','r2','r3',r4']
        # Get prediction set for this rule by running a nested inner join SQL query
        literalList = rule.get_literals()[1:]
        
        count = 0
        table1 = literalList[0].functor
        
        varList = []
        tableList = []
        for i, literal in enumerate(literalList):
            tableList.append(literal.functor)
            #tableList.append(literal._Term__functor)
            argList = literal.args
            varList.append([])
            for j, arg in enumerate(argList):
                variable = term2str(arg)
                varList[i].append(variable)
                    
        unifiedVarSet = set()
        for vars in varList:
            unifiedVarSet = unifiedVarSet.union(set(vars))
        
        if 'A' not in unifiedVarSet and 'B' not in unifiedVarSet:
            unifiedTableName = "dummy" + str(self.dummyCount)
            self.dummyCount += 1
            self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
            sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct dummyA.v0 as v0, dummyB.v0 as v1 from dummyA cross join dummyB);'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
            return unifiedTableName
        
        newTable = tableList[0]
        unifiedVarList = varList[0]
        for (table, vars) in zip(tableList[1:], varList[1:]):
            newTable, unifiedVarList = self.rule_intersect2Tables(newTable, unifiedVarList, table, vars)
        
        if 'A' not in unifiedVarSet:
            unifiedTableName = "dummy" + str(self.dummyCount)
            self.dummyCount += 1
            self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
            AIndex = len(unifiedVarList)
            unifiedVarList.append('A')
            sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct dummyA.v0 as v0, ' + newTable + '.v' + str(unifiedVarList.index('B')) + ' as v1 from ' + newTable + ' cross join dummyA);'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
            return unifiedTableName
        elif 'B' not in unifiedVarSet:
            unifiedTableName = "dummy" + str(self.dummyCount)
            self.dummyCount += 1
            self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
            BIndex = len(unifiedVarList)
            unifiedVarList.append('B')
            sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct ' + newTable + '.v' + str(unifiedVarList.index('A')) + ' as v0, dummyB.v0 as v1 from ' + newTable + ' cross join dummyB);'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
            return unifiedTableName
        else:
            #Prune newTable to keep only A and B columns
            unifiedTableName = "dummy" + str(self.dummyCount)
            self.dummyCount += 1
            self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
            sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct v' + str(unifiedVarList.index('A')) + ' as v0, v' + str(unifiedVarList.index('B'))  + ' as v1 from ' + newTable + ');'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
            return unifiedTableName
    
    def rule_predictAllRules(self, rules):
        self.dummyCount = 0
        
        #Creating DummyA and DummyB
        for i in range(0,self.targetArity):
            sqlQuery = 'select distinct ' + self.targetPredicate + '.v' + str(i) + ' as v0 from ' + self.targetPredicate
            entity = self.predicateDict[self.targetPredicate][i]
            for pred in self.predicateDict:
                if pred == self.targetPredicate:
                    continue
                entityList = self.predicateDict[pred]
                for j, predEntity in enumerate(entityList):
                    if predEntity == entity:
                        sqlQuery = sqlQuery + ' union select distinct ' + pred + '.v' + str(j) + ' as v0 from ' + pred
            
            self.cursor.execute('DROP TABLE IF EXISTS dummy' + chr(65+i) + ';')
            sqlQuery = 'CREATE TABLE dummy' + chr(65+i) + ' AS (select distinct * from (' + sqlQuery + ') as a);'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
        
        #negativeExamples = set()
        while len(rules.get_literals()) <= 1 or Term('fail') in rules.get_literals():
            rules = rules.previous
        
        if rules == None:
            emptyTable = "dummy" + str(self.dummyCount)
            self.dummyCount += 1
            self.cursor.execute('DROP TABLE IF EXISTS ' + emptyTable + ';')
            sqlQuery = 'CREATE TABLE ' + emptyTable + ' (v0 integer, v1 interger, p double precision);'
            getLogger('probfoil').log(9, sqlQuery)
            self.cursor.execute(sqlQuery)
            return emptyTable
        
        table = self.rule_predict1rule(rules)
        if rules.previous != None:
            rule = rules.previous
            while rule != None:
                if len(rule.get_literals()) > 1 and Term('fail') not in rule.get_literals():
                    newTable = self.rule_predict1rule(rule)
                    table = self.rule_unify2Tables(table, ['A','B'], newTable, ['A','B'])
                rule = rule.previous
        
        unifiedTableName = "dummy" + str(self.dummyCount)
        self.dummyCount += 1
        self.cursor.execute('DROP TABLE IF EXISTS ' + unifiedTableName + ';')
        sqlQuery = 'CREATE TABLE ' + unifiedTableName + ' AS (select distinct v0, v1 from ' + table + ');'
        getLogger('probfoil').log(9, sqlQuery)
        self.cursor.execute(sqlQuery)
        
        return unifiedTableName
    
    def rule_getNegativeExamples(self, rules):
        startNegative = time()
        
        subjectConstantList = {v: k for k, v in self.constantDict[self.predicateDict[self.targetPredicate][0]].iteritems()}
        objectConstantList = {v: k for k, v in self.constantDict[self.predicateDict[self.targetPredicate][1]].iteritems()}
        universalConstantList = {v: k for k, v in self.universalConstantId.iteritems()}
        #subjectConstantList = self.constantDict[self.predicateDict[self.targetPredicate][0]]
        #objectConstantList = self.constantDict[self.predicateDict[self.targetPredicate][1]]
        
        self.totalPositiveExamples = len(self._examples)
        getLogger('probfoil').info('%-*s: %d' % (self.pad, "Total positive examples (#P)", self.totalPositiveExamples))
        
        #------------------------------------ Get Closed World Negatives ------------------------------------
        table = self.rule_predictAllRules(rules)
        self.cursor.execute('select count(*) from ' + table + ';')
        totalPredictions = str(self.cursor.fetchone()[0])
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Total CW Predictions", totalPredictions))
        
        CWPrediction = "dummy" + str(self.dummyCount)
        self.dummyCount += 1
        self.cursor.execute('DROP TABLE IF EXISTS ' + CWPrediction + ';')
        sqlQuery = 'CREATE TABLE ' + CWPrediction + ' AS (select distinct ' + table + '.v0, ' + table + '.v1 from ' + table + ' where not exists (select 1 from ' + self.targetPredicate + ' where ' + self.targetPredicate + '.v0 = ' + table + '.v0 and ' +  self.targetPredicate + '.v1 = ' + table + '.v1));'
        getLogger('probfoil').log(9, sqlQuery)
        self.cursor.execute(sqlQuery)
        self.cursor.execute('select count(*) from ' + CWPrediction + ';')
        totalPredictions = str(self.cursor.fetchone()[0])
        getLogger('probfoil').info('%-*s: %s' % (self.pad, "Total CW Negative Predictions", totalPredictions))
        sqlQuery = 'select * from ' + CWPrediction + ' order by random() limit ' + str(self.closedWorldNegativesFactor*self.totalPositiveExamples*2) + ';'
        getLogger('probfoil').log(9, sqlQuery)
        self.cursor.execute(sqlQuery)
        predictionList = self.cursor.fetchall()
        
        start = time()
        
        CWNegativeExamples = []
        counter = 0
        #random.shuffle(predictionList)
        for (a,b) in predictionList:
            if counter == self.closedWorldNegativesFactor*self.totalPositiveExamples:
                break
            example = [universalConstantList[a], universalConstantList[b]]
            if example not in self.examples:
                CWNegativeExamples.append(example)
                counter += 1
        
        self.CWNegatives = set(range(self.totalPositiveExamples,self.totalPositiveExamples+counter))
        self.totalCWNegativeExamples = len(CWNegativeExamples)
        self.CWNegatives = set(range(self.totalPositiveExamples,self.totalPositiveExamples + self.totalCWNegativeExamples))
        
        getLogger('probfoil').info('%-*s: %d' % (self.pad, "Total CW negative examples", self.totalCWNegativeExamples))
        
        self.cursor.execute('select count(*) from ' + CWPrediction + ';')
        totalCWNegativeTuples = self.cursor.fetchone()[0]
        
        if self.totalCWNegativeExamples != 0:
            self.CWNegativeWeight = float(totalCWNegativeTuples)*self.misclassificationCost/self.totalCWNegativeExamples
        else:
            self.CWNegativeWeight = 1
        
        getLogger('probfoil').log(9, '%-*s: %s' % (self.pad, "CW Negative Weight", str(self.CWNegativeWeight)))
        getLogger('probfoil').log(9, '%-*s: %s' % (self.pad, "#CW Negative Examples", str(self.totalCWNegativeExamples)))
                                                   
        #------------------------------------- Get Open World Negatives --------------------------------------
        table = self.rule_unify2Tables(table, ['A','B'], self.targetPredicate, ['A','B'])
        self.cursor.execute('select count(*) from ' + table + ';')
        totalCWTuples = self.cursor.fetchone()[0]
        # totalCWTuples contains both positives and negatives
        
        self.cursor.execute('select * from ' + table + ';')
        totalCWList = self.cursor.fetchall()
        
        numberOfSubjects = len(subjectConstantList)
        numberOfObjects = len(objectConstantList)
        
        OWNegativeExamples = []
        sample = 0
        sampleCap = self.openWorldNegativesFactor*self.totalPositiveExamples
        iteration = 0
        iterationCap = 2*numberOfSubjects*numberOfObjects
        
        while True:
            if sample == sampleCap or iteration == iterationCap:
                break
            j = random.randint(0, numberOfSubjects - 1)
            k = random.randint(0, numberOfObjects - 1)
            example = [subjectConstantList[subjectConstantList.keys()[j]], objectConstantList[objectConstantList.keys()[k]]]
            if (j,k) not in totalCWList:
                OWNegativeExamples.append(example)
                sample += 1
            iteration += 1
        
        self.totalOWNegativeExamples = len(OWNegativeExamples)
        self.OWNegatives = set(range(self.totalPositiveExamples + self.totalCWNegativeExamples, self.totalPositiveExamples + self.totalCWNegativeExamples + self.totalOWNegativeExamples))
        
        k = 1
        for base in self.predicateDict[self.targetPredicate]:
            k = k*len(self.constantDict[base])
        
        totalOWNegativeExamples = k - totalCWTuples
        
        getLogger('probfoil').info('%-*s: %d' % (self.pad, "Total OW negative examples", totalOWNegativeExamples))
        
        if self.totalOWNegativeExamples != 0:
            self.OWNegativeWeight = float(totalOWNegativeExamples)*self.misclassificationCost/self.totalOWNegativeExamples
        else:
            self.OWNegativeWeight = 1
        
        getLogger('probfoil').log(9, '%-*s: %s' % (self.pad, "OW Negative Weight", str(self.OWNegativeWeight)))
        getLogger('probfoil').log(9, '%-*s: %s' % (self.pad, "#OW Negative Examples", str(self.totalOWNegativeExamples)))
        
        self._scores_correct = self._scores_correct + [0]*self.totalCWNegativeExamples + [0]*self.totalOWNegativeExamples
        
        getLogger('loss').log(8, '%-*s: %s' % (self.pad, "self._examples", str(self._examples)))
        getLogger('loss').log(8, '%-*s: %s' % (self.pad, "CWNegativeExamples", str(CWNegativeExamples)))
        getLogger('loss').log(8, '%-*s: %s' % (self.pad, "OWNegativeExamples", str(OWNegativeExamples)))
        self._examples = self._examples + CWNegativeExamples + OWNegativeExamples
        
        self.totalExamples = self.totalPositiveExamples + self.totalCWNegativeExamples + self.totalOWNegativeExamples
        self.totalWeightedExamples = (self.totalPositiveExamples + self.CWNegativeWeight*self.totalCWNegativeExamples + self.OWNegativeWeight*self.totalOWNegativeExamples)
        self.querySS = [""]*self.totalExamples
        
        totalNegative = time() - startNegative
        getLogger('probfoil').log(9, '%-*s: %ss' % (self.pad, "Total time in getting negatives", str(totalNegative)))
        
        
        iteration = int(table[5:])
        while iteration != -1:
            self.cursor.execute('drop table dummy' + str(iteration) + ';')
            iteration -= 1
    
    def rule_getConditionalProbability(self, ruleIndex):
        
        # Numerator = |Prediction of Rule (intersection) Positive Examples|
        # Denominator = |Prediction of Rule|
        
        #table, varList = self.rulewisePredictions[self.selectedAmieRules[-1]]
        
        
        (headLiteral, amieLiteralList) = self.AmieRuleList[ruleIndex]
        rule = FOILRule(headLiteral)
        for literal in amieLiteralList:
            rule = rule & literal
        
        table = self.rule_predict1rule(rule)
        targetTable = self.targetPredicate
        
        joinedTable, joinedVarList = self.rule_intersect2Tables(targetTable, ['A','B'], table, ['A','B'])
        
        self.cursor.execute('select count(*) from ' + joinedTable + ';')
        numerator = float(str(self.cursor.fetchone()[0]))
        
        self.cursor.execute('select count(*) from ' + table + ';')
        denominator = float(str(self.cursor.fetchone()[0]))
        
        if denominator == 0:
            # Bogus Rule
            return 1-self.tolerance
        else:
            prob = numerator/denominator
            getLogger('probfoil').log(9, '%-*s: %s' % (self.pad, "# Predictions of Rule" + str(ruleIndex) + " intersected with examples", str(numerator)))
            getLogger('probfoil').log(9, '%-*s: %s' % (self.pad, "# Predictions of Rule" + str(ruleIndex), str(denominator)))
            #return self.regularize(prob, 5)
            return prob
    
    def _compute_rule_score(self, rule):
        return m_estimate_relative(rule, self._m_estimate)

    def _compute_rule_future_score(self, rule):
        return m_estimate_future_relative(rule, self._m_estimate)

    def _select_rule(self, rule):
        pass

    def statistics(self):
        statList = []
        if self.learnAllRules == False:
            statList.append(('Rule evaluations', self._stats_evaluations))
        #statList.append(('Numeric SS calls', self._stats_numericSS))
        #statList.append(('Symbolic SS calls', self._stats_symbolicSS))
        statList.append(('Get SQL Query calls', self._stats_getSQLQuery))
        if self.open_world:
            statList.append(('Get Expression calls', self._stats_getExpression))
        statList.append(('Read Time', str(round(self._time_read,2)) + "s"))
        #statList.append(('Numeric SS', str(round(self._time_numericSS,2)) + "s"))
        #statList.append(('Symbolic SS', str(round(self._time_symbolicSS,2)) + "s"))
        #statList.append(('Get SQL Query', str(round(self._time_getSQLQuery,2)) + "s"))
        #statList.append(('Get Canonical Form', str(round(self._time_getCanonicalForm,2)) + "s"))
        #statList.append(('Execute Query', str(round(self._time_executeQuery,2)) + "s"))
        #statList.append(('Execute PSQL', str(round(self._time_executePSQL,2)) + "s"))
        #statList.append(('Probability - Total', str(round(self._time_getQueryProbability,2)) + "s"))
        if self.open_world:
            statList.append(('Get Expression', str(round(self._time_getExpression,2)) + "s"))
            #statList.append(('Expression - Total', str(round(self._time_getQueryExpression,2)) + "s"))
            statList.append(('Optimization', str(round(self._time_optimization,2)) + "s"))
        
        statList.append(('Learn time', str(round(self._time_learn,2)) + "s"))
        return statList
        
    def print_output(self, hypothesis):
        printList = []
        if self.interrupted:
            printList.append('================ PARTIAL THEORY ================')
        else:
            printList.append('================= FINAL THEORY =================')
        
        if self.open_world:
            lamDict = {}
            for predicate in self.lams:
                if len(predicate) > 2 and predicate[:2] == "p_":
                    continue
                elif self.lams[predicate] == 0:
                    continue
                else:
                    lamDict[predicate] = self.lams[predicate]
                    
            if len(lamDict) == 1:
                printList.append('Open World Probability = ' + str(lamDict))
            elif len(lamDict) > 1:
                printList.append('Open World Probabilities = ' + str(lamDict))
                
        rule = hypothesis
        rules = rule.to_clauses(rule.target.functor)
    
        # First rule is failing rule: don't print it if there are other rules.
        if len(rules) > 1:
            for rule in rules[1:]:
                printList.append(str(rule))
        else:
            printList.append(str(rules[0]))
        '''
        printList.append('==================== SCORES ====================')
        printList.append('   Weighted Accuracy:\t%s' % str(hypothesis.weightedAccuracy))
        printList.append('       Cross Entropy:\t%s' % str(hypothesis.crossEntropy))
        printList.append('        Squared Loss:\t%s' % str(hypothesis.squaredLoss))
        printList.append('           Precision:\t%s' % str(hypothesis.precision))
        printList.append('              Recall:\t%s' % str(hypothesis.recall))
        printList.append('      True Positives:\t%s' % str(hypothesis.tp))
        printList.append('      True Negatives:\t%s' % str(hypothesis.tn))
        printList.append('     False Positives:\t%s' % str(hypothesis.fp))
        printList.append('     False Negatives:\t%s' % str(hypothesis.fn))
        '''
        for line in printList:
            getLogger('probfoil').info(line)
            print(line)
            
class ProbFOIL2(ProbFOIL):

    def __init__(self, *args, **kwargs):
        ProbFOIL.__init__(self, *args, **kwargs)

    def _select_rule(self, rule):
        # set rule probability and update scores
        if hasattr(rule, 'max_x'):
            #x = round(rule.max_x, 8)
            x = rule.max_x
        else:
            x = 1.0

        if x > 1 - self.tolerance:
            rule.set_rule_probability(None)
        else:
            rule.set_rule_probability(x)
        if rule.previous is None:
            scores_previous = [0.0] * len(rule.scores)
        else:
            scores_previous = rule.previous.scores

        for i, lu in enumerate(zip(scores_previous, rule.scores)):
            l, u = lu
            s = u - l
            rule.scores[i] = l + x * s

    def _compute_rule_future_score(self, rule):
        return self._compute_rule_score(rule, future=True)

    def _compute_rule_score(self, rule, future=False):
        return self._compute_rule_score_slow(rule, future)

    def _compute_rule_score_slow(self, rule, future=False):
        if rule.previous is None:
            scores_previous = [0.0] * len(rule.scores)
        else:
            scores_previous = rule.previous.scores

        data = list(zip(self._scores_correct, scores_previous, rule.scores))

        max_x = 0.0
        max_score = 0.0
        max_tp = 0.0
        max_fp = 0.0

        def eval_x(x, data, future=False):
            pos = 0.0
            all = 0.0
            tp = 0.0
            fp = 0.0
            tp_p = 0.0
            fp_p = 0.0
            for p, l, u in data:
                pr = l + x * (u - l)
                tp += min(p, pr)
                fp += max(0, pr - p)
                tp_p += min(p, l)
                fp_p += max(0, l - p)
                pos += p
                all += 1

            if future:
                fp = fp_p
            m = self._m_estimate
            if pos - tp_p == 0 and all - tp_p - fp_p == 0:
                mpnp = 1
            else:
                mpnp = m * ((pos - tp_p) / (all - tp_p - fp_p))
            score = (tp - tp_p + mpnp) / (tp + fp - tp_p - fp_p + m)
            return tp, fp, round(score, 12) # Rounding to 12 decimal places to avoid float precision error

        tp_x, fp_x, score_x = eval_x(1.0, data, future)
        if score_x > max_score:
            max_x = 1.0
            max_tp = tp_x
            max_fp = fp_x
            max_score = score_x
            if not future:
                getLogger('probfoil').log(7, '%s: x=%s (%s %s) -> %s' % (rule, 1.0, tp_x, fp_x, score_x))

        xSet = set()
        for p, l, u in data:
            if u - l < self.tolerance:
                continue
            x = (p - l) / (u - l)

            if x > 1.0 or x < 0.0 or x in xSet:
                # Don't check for absurd probabilities
                # Don't check for those possible probabilities which have already been checked
                continue
            
            xSet.add(x)
            tp_x, fp_x, score_x = eval_x(x, data, future)
            if not future:
                getLogger('probfoil').log(7, '%s: x=%s (%s %s %s) (%s %s) -> %s' % (rule, x, p, l, u, tp_x, fp_x, score_x))
            if score_x > max_score:
                max_x = x
                max_tp = tp_x
                max_fp = fp_x
                max_score = score_x
        '''
        xCandidates = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
        for x in xCandidates:
            if x in xSet:
                continue
            
            xSet.add(x)
            tp_x, fp_x, score_x = eval_x(x, data, future)
            if not future:
                getLogger('probfoil').log(9, '%s: x=%s (%s %s) -> %s' % (rule, x, tp_x, fp_x, score_x))
            if score_x > max_score:
                max_x = x
                max_tp = tp_x
                max_fp = fp_x
                max_score = score_x
        '''
        if not future:
            getLogger('probfoil').log(9, '%s\t: [BEST] x=%s (%s %s) -> %s' % (rule, max_x, max_tp, max_fp, max_score))
            rule.max_x = max_x
            rule.max_tp = max_tp
            rule.max_fp = max_fp

        #if max_x < self.tolerance:
        #    return 0.0

        return max_score

    def _compute_rule_score_fast(self, rule, future=False):
        if rule.previous is None:
            scores_previous = [0.0] * len(rule.scores)
        else:
            scores_previous = rule.previous.scores

        pos = 0.0
        all = 0.0

        tp_prev = 0.0
        fp_prev = 0.0
        fp_base = 0.0
        tp_base = 0.0
        ds_total = 0.0
        pl_total = 0.0

        if not future:
            getLogger('probfoil').log(5, '%s: %s' % (rule, list(zip(self._scores_correct, scores_previous, rule.scores))))

        values = []
        for p, l, u in zip(self._scores_correct, scores_previous, rule.scores):
            pos += p
            all += 1.0

            tp_prev += min(l, p)
            fp_prev += max(0, l - p)

            ds = u - l  # improvement on previous prediction (note: ds >= 0)
            if ds == 0:  # no improvement
                pass
            elif p < l:  # lower is overestimate
                fp_base += ds
            elif p > u:  # upper is underestimate
                tp_base += ds
            else:   # correct value still achievable
                ds_total += ds
                pl_total += p - l
                y = (p - l) / (u - l)   # for x equal to this value, prediction == correct
                values.append((y, p, l, u))

        neg = all - pos
        mpnp = self._m_estimate * (pos / all)

        def comp_m_estimate(tp, fp):
            score = (tp + mpnp) / (tp + fp + self._m_estimate)
            # print (self._m_estimate, mpnp, tp, fp, score)
            return score

        max_x = 1.0
        tp_x = pl_total + tp_base + tp_prev
        if future:
            fp_x = fp_prev + fp_base
        else:
            fp_x = ds_total - pl_total + fp_base + fp_prev
        score_x = comp_m_estimate(tp_x, fp_x)
        max_score = score_x
        max_tp = tp_x
        max_fp = fp_x

        if values:
            values = sorted(values)
            if not future:
                getLogger('probfoil').log(5, '%s: %s' % (rule, [map(lambda vv: round(vv, 3), vvv) for vvv in values]))

            tp_x, fp_x, tn_x, fn_x = 0.0, 0.0, 0.0, 0.0
            ds_running = 0.0
            pl_running = 0.0
            prev_y = None
            for y, p, l, u in values + [(None, 0.0, 0.0, 0.0)]:     # extra element forces compute at end
                if y is None or prev_y is not None and y > prev_y:
                    # There is a change in y-value.
                    x = prev_y  # set current value of x
                    tp_x = pl_running + x * (ds_total - ds_running) + x * tp_base + tp_prev
                    if future:
                        fp_x = fp_prev
                    else:
                        fp_x = x * ds_running - pl_running + x * fp_base + fp_prev

                    score_x = comp_m_estimate(tp_x, fp_x)

                    if not future:
                        getLogger('probfoil').log(6, '%s: x=%s (%s %s) -> %s' % (rule, x, tp_x, fp_x, score_x))
                    if max_score is None or score_x > max_score:
                        max_score = score_x
                        max_x = x
                        max_tp = tp_x
                        max_fp = fp_x

                        # if not future:
                        #     rts = rates(rule)
                        #     est = m_estimate(rule)
                        #     print(x, tp_x, fp_x, rts, score_x, est)
                        #     # assert abs(tp_x - rts[0]) < self.tolerance
                        #     # assert abs(fp_x - rts[1]) < self.tolerance
                        #     # assert abs(est - score_x) < self.tolerance

                prev_y = y
                pl_running += p - l
                ds_running += u - l

            assert abs(ds_running - ds_total) < self.tolerance
            assert abs(pl_running - pl_total) < self.tolerance

        if not future:
            getLogger('probfoil').log(6, '%s: [BEST] x=%s (%s %s) -> %s' % (rule, max_x, tp_x, fp_x, score_x))
            rule.max_x = max_x
            rule.max_tp = max_tp
            rule.max_fp = max_fp
        return max_score

def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('-1', '--det-rules', action='store_true', dest='probfoil1', help='learn deterministic rules')
    parser.add_argument('-m', help='parameter m for m-estimate', type=float, default=argparse.SUPPRESS)
    parser.add_argument('-b', '--beam-size', type=int, default=5, help='size of beam for beam search')
    parser.add_argument('-p', '--significance', type=float, default=None, help='rule significance threshold', dest='p')
    parser.add_argument('-l', '--length', dest='l', type=int, default=None, help='maximum rule length')
    parser.add_argument('-v', action='count', dest='verbose', default=None, help='increase verbosity (repeat for more)')
    parser.add_argument('--symmetry-breaking', action='store_true', help='avoid symmetries in refinement operator')
    parser.add_argument('-t', '--target', type=str, help='specify predicate/arity to learn (overrides settings file)')
    parser.add_argument('--log', help='write log to file', default=None)
    parser.add_argument('-c', '--closed-world', action='store_true', help='Closed World Indicator (Input -c to learn on closed world setting)')
    parser.add_argument('-g', '--global-score', type=str, default = 'cross_entropy', help="specify global scoring function as either 'accuracy' or 'cross_entropy' (Default is 'cross_entropy')")
    parser.add_argument('-o', '--optimization-method', type=str, default = 'incremental', help="specify optimization method of lambda as either 'batch' or 'incremental' (Default is 'incremental')")
    parser.add_argument('-r', '--candidate-rules', type=str, default = 'amie', help="specify generation method of candidate rules as either 'probfoil' or 'amie' (Default is 'amie')")
    parser.add_argument('-w', '--cost', type=float, default = 1.0, help="Misclassification Cost for negative examples")
    #parser.add_argument('--test', type = str, help='Test Dataset File', default=None)
    parser.add_argument('--minpca', type=float, default=0.00001, help='Minimum PCA Confidence Threshold for Amie', dest='minpca')
    parser.add_argument('--minhc', type=float, default=0.00001, help='Minimum Standard Confidence Threshold for Amie', dest='minhc')
    parser.add_argument('-q', '--quotes', action='store_true', help='Input -q to denote an input file with facts enclosed in double quotes')
    parser.add_argument('--ssh', action='store_true', help='Input --ssh if the code is running on PINACS/HIMECS')
    parser.add_argument('--cwLearning', action='store_true', help='Input --cwLearning for learning rule weights with SGD in Closed World')
    parser.add_argument('-i', '--iterations', type=int, default=10000, help='Number of iterations of SGD', dest='iterations')
    parser.add_argument('-a', '--maxAmieRules', type=int, default=None, help='Maximum number of candidate rules to be learned from AMIE', dest='maxAmieRules')
    parser.add_argument('-d','--disableTypeConstraints', action='store_true', help='Input -d to ignore type constraints for learned rules')
    parser.add_argument('--lr1', type=float, default=0.001, help='Learning Rate for Rule Weights', dest='lr1')
    parser.add_argument('--lr2', type=float, default=0.0001, help='Learning Rate for Lambdas', dest='lr2')
    return parser

class ProbLogLogFormatter(logging.Formatter):

    def __init__(self):
        logging.Formatter.__init__(self)

    def format(self, message):
        msg = str(message.msg) % message.args
        lines = msg.split('\n')
        if message.levelno < 10:
            linestart = '[LVL%s] ' % message.levelno
        else:
            linestart = '[%s] ' % message.levelname
        return linestart + ('\n' + linestart).join(lines)

def init_logger(verbose=None, name='problog', out=None):
    """Initialize default logger.

    :param verbose: verbosity level (0: WARNING, 1: INFO, 2: DEBUG)
    :type verbose: int
    :param name: name of the logger (default: problog)
    :type name: str
    :return: result of ``logging.getLogger(name)``
    :rtype: logging.Logger
    """
    if out is None:
        out = sys.stdout

    logger = logging.getLogger(name)
    ch = logging.StreamHandler(out)
    # formatter = logging.Formatter('[%(levelname)s] %(message)s')
    formatter = ProbLogLogFormatter()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    if not verbose:
        logger.setLevel(logging.WARNING)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
        logger.info('Output level\t\t\t\t\t\t: INFO')
    elif verbose == 2:
        logger.setLevel(logging.DEBUG)
        logger.debug('Output level\t\t\t\t\t: DEBUG')
    else:
        level = max(1, 12 - verbose)   # between 9 and 1
        logger.setLevel(level)
        logger.log(level, 'Output level\t\t\t\t\t\t: %s' % level)
    return logger

def main(argv=sys.argv[1:]):
    args = argparser().parse_args(argv)
    
    if args.log is None:
        logfile = None
        lossfile = None
    else:
        logfile = open(args.log, 'w')
        if args.verbose > 3:
            lossfile = open(args.log[:-4] + ".loss", 'w')

    log = init_logger(verbose=args.verbose, name='probfoil', out=logfile)
    if args.verbose > 3:
        log_loss = init_logger(verbose=args.verbose, name='loss', out=lossfile)
    log.info('Arguments\t\t\t\t\t\t: %s' % ' '.join(argv))
    
    # Load input files
    if args.candidate_rules != "amie":
        data = DataFile(*(PrologFile(source) for source in args.files))
    else:
        data = args.files
        
    if args.probfoil1:
        learn_class = ProbFOIL
    else:
        learn_class = ProbFOIL2

    
    time_start = time()
    learn = learn_class(data, logger='probfoil', **vars(args))
    hypothesis = learn.learn()
    time_total = time() - time_start
    
    log.info('\n==================== OUTPUT ====================')
    print ('\n=================== SETTINGS ===================')
    log.info('\n=================== SETTINGS ===================')
    for kv in vars(args).items():
        print('%20s:\t%s' % kv)
        log.info('%20s:\t%s' % kv)
        
    learn.print_output(hypothesis)
    
    printList = []
    printList.append('================== STATISTICS ==================')
    for name, value in learn.statistics():
        printList.append('%20s:\t%s' % (name, value))
    printList.append('          Total time:\t%.4fs' % time_total)
    
    for line in printList:
        log.info(line)
        print(line)
    
    if logfile:
        logfile.close()

if __name__ == '__main__':
    main()
#     try:
#         main()
#         os.system('say "Your Program has Finished"')
#     except Exception as e:
#         print(e)
#         os.system('say "Your Program has encountered an error."')
