from __future__ import division
from sympy import symbols

import psycopg2
import re

from algorithm3 import query_exp, query_sym, algorithm

class ParseError(Exception):

    def __init__(self, arg):
        self.args = arg

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


def getSQLQuery(query, openworld):

    algorithm.lam = symbols('z')
    algorithm.dom = symbols('y')
    algorithm.resetCounters()
    
    try:
        exactProb = 0
        queryStr = query
        queryDNF = parse(queryStr)
        try:
            if(openworld):
                plan = algorithm.getSafeOpenQueryPlanNaive(queryDNF)
            else:
                plan = algorithm.getSafeQueryPlan(queryDNF)

            querySQL = plan.generateSQL_DNF()
            return querySQL
        except algorithm.UnsafeException:
            return "Query is unsafe"

    except ParseError:
        return "Failed to parse"

if __name__ == "__main__":
    #print(getSQLQuery("table0(A,B),table1(C,B) v table2(A,D),table3(C,D)", True))
    #print(getSQLQuery("table0(A,A),table1(A,A) v table2(A,A),table3(A,A)", True))
    #print(getSQLQuery("table0(A,B),table0(C,B) v table0(A,D),table0(C,D)", True))
    #print(getSQLQuery("table0(A,B),table0(C,B)", True))
    #print(getSQLQuery("table0(A),table1(B),table2(A)", True))
    #print(getSQLQuery("table0(A,B,C)", True))
    #print(getSQLQuery("table0(A,A)", True))
    #print(getSQLQuery("R1(v3),R2(v4),R3(v0) v R4(v5),R1(v6),R5(v1) v R6(v7),R1(v8),R6(v2) v R1(v9),R7(v10),R8(v11)", True))
    #print(getSQLQuery("table0(V0),table1(V0),table2(V1) v table3(V2),table4(V2),table5(V3) v table3(V4),table1(V4),table6(V5) v table7(V6),table3(V6),table8(V7) v table0(V8),table7(V8),table9(V9)", True))
    print(getSQLQuery("table0(V0),table1(V1),table2(V2) v table3(V3),table4(V4),table5(V5) v table3(V6),table1(V7),table6(V8) v table7(V9),table3(V10),table8(V11) v table0(V12),table7(V13),table9(V14)", True))

    
