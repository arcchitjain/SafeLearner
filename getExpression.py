from __future__ import division
from sympy import symbols

import re

from symbolic_slimshot import query_exp, query_sym, algorithm


class ParseError(Exception):
    def __init__(self, arg):
        self.args = arg


def parseRelation(relString, constantString, varString, useConstraintClass=False):
    relName = relString
    relDet = False
    relNeg = False
    relSampled = False
    if len(relString) > 1 and relString[-1] == "!" and relString[-2] == "*":
        relName = relName[:-2]
        relDet = True
        relSampled = True
    if relString[-1] == "*":
        relName = relName[:-1]
        relDet = True
    if relString[0] == "~":
        relName = relName[1:]
        relNeg = True
    if len(varString):
        relVars = list(map(lambda x: query_sym.Variable(x), varString.split(",")))
    else:
        relVars = []
    constraints = []
    if constantString:
        constantString = constantString[1:-1]
        constants = constantString.split(",")
        for (i, c) in enumerate(constants):
            if useConstraintClass:
                constraints.append(query_sym.Constraint(c))
            else:
                if c == "*":
                    constraints.append(None)
                    continue
                if c == "c" or c == "-c":
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
                        "unique for non-joined variables",
                    )
                inequalityGenericConstants.add(constraint.getConstant())
            if constraint.isInequality():
                relVars[varIndex].setInequality(constraint)
            if not constraint.isEquality():
                varIndex += 1

    if relName == "A":
        raise Exception(
            "A is a reserved relation name ", "(used for active domain in sampling)"
        )
    return query_sym.Relation(
        relName,
        relVars,
        deterministic=relDet,
        negated=relNeg,
        sampled=relSampled,
        constraints=constraints,
    )


def parseConjunct(conjunct):
    relations = []
    regex = re.compile("(~?[A-Za-z_0-9]+\*?\!?)(\[[,\-0-9c\*]+\])?\((.*?)\)")
    if not regex.match(conjunct):
        raise ParseError("Failed to parse")
    for (relString, constantString, varString) in regex.findall(conjunct):
        relations.append(parseRelation(relString, constantString, varString))

    return query_exp.ConjunctiveQuery(
        query_exp.decomposeComponent(query_exp.Component(relations))
    )


def parseConjunctUsingConstraintClass(conjunct):
    relations = []
    regex = re.compile("(~?[A-Za-z_0-9]+\*?\!?)(\[[,\-0-9a-z\*]+\])?\((.*?)\)")
    if not regex.match(conjunct):
        raise ParseError("Failed to parse")
    for (relString, constantString, varString) in regex.findall(conjunct):
        relations.append(
            parseRelation(relString, constantString, varString, useConstraintClass=True)
        )
    return query_exp.ConjunctiveQuery(
        query_exp.decomposeComponent(query_exp.Component(relations))
    )


def parse(queryStr, useConstraintClass=False):
    conjunctsRaw = queryStr.split(" v ")
    if useConstraintClass:
        conjunctsParsed = list(map(parseConjunctUsingConstraintClass, conjunctsRaw))
    else:
        conjunctsParsed = list(map(parseConjunct, conjunctsRaw))
    return query_exp.DNF(conjunctsParsed)


def getExpression(query):

    algorithm.lam = symbols("z")
    algorithm.dom = symbols("y")
    algorithm.resetCounters()

    try:
        queryStr = query
        queryDNF = parse(queryStr)
        try:
            plan = algorithm.getSafeOpenQueryPlanNaive(queryDNF)
            querySQL = plan.generateSQL_DNF()
            return querySQL
        except algorithm.UnsafeException:
            return "Query is unsafe"

    except ParseError:
        return "Failed to parse"
