from __future__ import division
import psycopg2
import re
from math import exp
from algorithm1 import algorithm, query_exp, query_sym
import safe

class ParseError(Exception):

    def __init__(self, arg):
        self.args = arg


def getPlan(queryDNF):
    return algorithm.getSafeQueryPlan(queryDNF)


def getOpenPlan(queryDNF):
    return algorithm.getSafeOpenQueryPlanNaive(queryDNF)


def executeSQL(conn, sql, query):
    prob = None
    cur = conn.cursor()
    try:
        cur.execute(sql)
        prob = cur.fetchone()[0]
        cur.close()
    except psycopg2.Error as e:
        print "NumericSS >> SQL error \t: " + e.pgerror[:-1] 
        print "NumericSS >> Query \t: " + query
        print "NumericSS >> SQL Query \t: " + sql
        cur.close()
    return prob


def printProbability(conn, sql, query):
    prob = executeSQL(conn, sql, query)
    if prob is not None:
        #print "Query probability: %f (exact)" % prob
        return prob


def parseRelation(
        relString,
        constantString,
        varString,
        useConstraintClass=False):
    relName = relString
    relDet = False
    relNeg = False
    relSampled = False
    if len(relString) > 1 and relString[-1] == '!' and relString[-2] == '*':
        relName = relName[:-2]
        relDet = True
        relSampled = True
    if relString[-1] == '*':
        relName = relName[:-1]
        relDet = True
    if relString[0] == '~':
        relName = relName[1:]
        relNeg = True
    if len(varString):
        relVars = map(lambda x: query_sym.Variable(x), varString.split(','))
    else:
        relVars = []
    constraints = []
    if constantString:
        constantString = constantString[1:-1]
        constants = constantString.split(',')
        for (i, c) in enumerate(constants):
            if useConstraintClass:
                constraints.append(query_sym.Constraint(c))
            else:
                if c == '*':
                    constraints.append(None)
                    continue
                if c == 'c' or c == '-c':
                    constraints.append(c)
                    continue
                cInt = int(c)
                constraints.append(cInt)
    if useConstraintClass:
        varIndex = 0
        inequalityGenericConstants = set()
        for constraint in constraints:
            if constraint.isInequality() and constraint.isGeneric():
                if constraint.getConstant() in inequalityGenericConstants:
                    raise Exception(
                        "Inequality generic constraints must be ",
                        "unique for non-joined variables")
                inequalityGenericConstants.add(constraint.getConstant())
            if constraint.isInequality():
                relVars[varIndex].setInequality(constraint)
            if not constraint.isEquality():
                varIndex += 1

    if relName == 'A':
        raise Exception(
            "A is a reserved relation name ",
            "(used for active domain in sampling)")
    return query_sym.Relation(
        relName,
        relVars,
        deterministic=relDet,
        negated=relNeg,
        sampled=relSampled,
        constraints=constraints)


def parseConjunct(conjunct):
    relations = []
    regex = re.compile("(~?[A-Za-z_0-9]+\*?\!?)(\[[,\-0-9c\*]+\])?\((.*?)\)")
    if not regex.match(conjunct):
        raise ParseError("Failed to parse")
    for (relString, constantString, varString) in regex.findall(conjunct):
        relations.append(parseRelation(relString, constantString, varString))
    return query_exp.ConjunctiveQuery(
        query_exp.decomposeComponent(
            query_exp.Component(relations)))


def parseConjunctUsingConstraintClass(conjunct):
    relations = []
    regex = re.compile("(~?[A-Za-z_0-9]+\*?\!?)(\[[,\-0-9a-z\*]+\])?\((.*?)\)")
    if not regex.match(conjunct):
        raise ParseError("Failed to parse")
    for (relString, constantString, varString) in regex.findall(conjunct):
        relations.append(
            parseRelation(
                relString,
                constantString,
                varString,
                useConstraintClass=True))
    return query_exp.ConjunctiveQuery(
        query_exp.decomposeComponent(
            query_exp.Component(relations)))


def parse(queryStr, useConstraintClass=False):
    conjunctsRaw = queryStr.split(' v ')
    if useConstraintClass:
        conjunctsParsed = map(parseConjunctUsingConstraintClass, conjunctsRaw)
    else:
        conjunctsParsed = map(parseConjunct, conjunctsRaw)
    return query_exp.DNF(conjunctsParsed)


def numericSS(query, lam = 0, domain = 1, database = "postgres", openworld = False):     
    algorithm.lam = lam
    algorithm.dom = float(domain)

    conn = psycopg2.connect(dbname=database)
    conn.autocommit = True
    algorithm.resetCounters()
    
    try:
        exactProb = 0
        queryStr = query
        queryDNF = parse(queryStr)
        try:
            if(openworld):
                plan = getOpenPlan(queryDNF)
            else:
                plan = getPlan(queryDNF)

            querySQL = plan.generateSQL_DNF()
            #print "PrettySQL:"
            #print algorithm1.getPrettySQL(querySQL), "\n"
            exactProb = printProbability(conn, querySQL, query)
            if openworld == False or exactProb == None:
                return exactProb
            else:
                return 1 - exp(exactProb)
        except algorithm.UnsafeException:
            #(relationsToSample, residualDNF, querySQL, relsObjects) = algorithm.findSafeResidualQuery(queryDNF)
            #ssExecutor = safe.SafeSample(conn)
            #estimate = ssExecutor.safeSample(relationsToSample, relsObjects, querySQL, 1000, 0.1, 0.1)
            #return estimate
            return "Query is unsafe"
        
    except ParseError:
        return "Failed to parse"

if __name__ == "__main__":
    #Returns error: ERROR:  column reference "c1" is ambiguous
    #print(numericSS("teammate_all_881(C,A),athletebeatathlete_881_881(A,A)", lam = 0, domain = 4071456, database = "athleteplaysforteam_testv2", openworld = True))
    #print(query_parser1("author_33_all(B,C),location_32_all(B,D),location_30_all(A,D)", lam = 0.5, domain = 7, database = "coauthor50", openworld = True))
    #print(query_parser1("location(B,C),location(A,C),author(A,D)", lam = 0.5, domain = 7, database = "coauthor50", openworld = False))
    #print(numericSS("U(X),V(X,Y),W(Y)", database = "sampling", lam = 0, domain = 7, openworld = False))
    #print(numericSS("alst(A,B),apft(A,B)", database = "athleteplaysforteam_850_agg_positive3", lam = 0, domain = 7, openworld = False))
    print(numericSS("athleteplaysforteam(A,B),teamplaysagainstteam(B,C),teamplayssport(C,D)", database = "aps_1110", lam = 0, domain = 7, openworld = False))