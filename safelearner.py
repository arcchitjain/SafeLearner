"""Implementation of the OpenProbFOIL algorithm.
"""

from __future__ import print_function
from ad import gh
from ad.admath import *
import argparse
from copy import copy
from data import DataFile
from getExpression import (
    getExpression,
)  # Get SQL Query that outputs a probabilistic expression for UCQ
from learn import LearnEntail
from logging import getLogger
import logging
import os
from problog.program import PrologFile
from problog.logic import term2str, Term, Var
import psycopg2
import random
from rule import FOILRule
from subprocess import Popen, PIPE
import sys
from time import time


class SafeLearner(LearnEntail):
    def __init__(
        self,
        input_file,  # Input File
        cost=1,  # Misclassification cost
        db_localhost="localhost",  # Name of localhost for connection to the database
        db_name="postgres",  # Name of the database
        db_pass="postgres",  # Password of user for connection to the database
        db_user="postgres",  # Username for connection to the database
        disable_typing=False,  #
        score="cross_entropy",
        # Which global scoring function should be used: "cross_entropy", "squared_loss", "accuracy"
        iterations=10000,  # Total number of iterations for SGD for parameter learning
        l=None,  # Maximum rule length
        lr=0.00001,  # Learning rate for rule weights
        max_amie_rules=None,  # Maximum number of AMIE learned rules to consider as candidates
        minhc=0.00001,  # Parameter of AMIE: Minimum head coverage
        minpca=0.00001,  # Parameter of AMIE: Minimum PCA Confidence
        quotes=False,  # Parameter to denote an input file with facts enclosed in double quotes
        allow_recursion=False,  # Allow recursive rules; Allow target literal to be in body
        **kwargs
    ):
        self.pad = 33
        self.logFile = kwargs["log"]

        # Load input file
        data = DataFile(PrologFile(input_file))
        LearnEntail.__init__(self, data, logger="log", **kwargs)

        self.max_length = l
        self.global_score = score
        self.minpca = minpca
        self.minhc = minhc
        self.tolerance = 1e-12
        self.max_increment = [0.001, 0.0002]
        self.input_file = input_file
        self.iterations = iterations
        self.misclassification_cost = cost
        self.learning_rate = lr
        self.step_check = 500
        self.cw_negatives_factor = 1
        self.ow_negatives_factor = 1
        self.enforce_type_constraints = not disable_typing
        self.allow_recursion = allow_recursion
        self.facts_with_quotes = quotes
        self.max_amie_rules = max_amie_rules
        self.fixed_point = (
            False
        )  # Specify if SGD should be terminated if it reaches/oscillates around a fixed point
        self.db_localhost = db_localhost
        self.db_name = db_name
        self.db_pass = db_pass
        self.db_user = db_user

        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Tolerance Parameter", str(self.tolerance))
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Max Increments", str(self.max_increment))
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Learning Rate", str(self.learning_rate))
        )
        getLogger("log").info(
            "%-*s: %s"
            % (
                self.pad,
                "Closed World Negatives' Factor",
                str(self.cw_negatives_factor),
            )
        )
        getLogger("log").info(
            "%-*s: %s"
            % (self.pad, "Open World Negatives' Factor", str(self.ow_negatives_factor))
        )
        getLogger("log").info(
            "%-*s: %d" % (self.pad, "Number of SGD iterations", self.iterations)
        )
        getLogger("log").info(
            "%-*s: %s"
            % (
                self.pad,
                "Misclassification Cost of -ves",
                str(self.misclassification_cost),
            )
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Max Rule Length", str(self.max_length))
        )

        self.predicate_dict = {}
        self.constant_dict = {}
        self.cw_total = {}
        self.canonical_rule_list = []
        self.query_dict = {}
        self.symbolic_query_dict = {}
        self.already_instantiated_tables = set()
        self.weights = {}
        self.negative_weight = 1  # Remove later
        self.total_positive_examples = 0
        self.constant_id = {}
        self.constant_count = 0
        self.mode_set = set()

        self.stats_getExpression = 0

        self.time_optimization = 0
        self.time_getExpression = 0
        self.time_learn = 0
        self.time_read = 0

    def _select_rule(self, rule):
        # set rule probability and update scores
        if hasattr(rule, "max_x"):
            # x = round(rule.max_x, 8)
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

    def regularize(self, a, factor=1):
        if isinstance(a, float) or isinstance(a, int):
            if a > 1 - factor * self.tolerance:
                return 1 - factor * self.tolerance
            elif a < factor * self.tolerance:
                return factor * self.tolerance
            else:
                return a
        elif isinstance(a, str):
            a = float(a)
            if a > 1 - factor * self.tolerance:
                return str(eval("1 - " + str(factor * self.tolerance)))
            elif a < factor * self.tolerance:
                return str(factor * self.tolerance)
            else:
                return str(a)

    def initial_hypothesis(self):
        initial = FOILRule(self.target)
        initial = initial & Term("fail")
        initial.accuracy = 0
        initial.scores = [0.0] * self.total_examples
        initial.expression_list = [""] * self.total_examples
        initial.replaceableQuery = ""
        initial.avoid_literals = set()

        true_rule = FOILRule(self.target, previous=initial)
        true_rule.accuracy = 0
        true_rule.scores = [1.0] * self.total_examples
        true_rule.expression_list = [""] * self.total_examples
        true_rule.replaceableQuery = ""
        self._select_rule(true_rule)
        true_rule.avoid_literals = set()

        return true_rule

    def connect_psqldb(self):
        return psycopg2.connect(
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_pass,
            host=self.db_localhost,
        )

    def initialize_psqldb(self):
        # ----------------------------------- Initialize PSQL Database -----------------------------------
        time_start = time()

        try:
            self.conn = psycopg2.connect(
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_pass,
                host=self.db_localhost,
            )
        except Exception as e:
            getLogger("log").warning(
                "The database " + self.db_name + " is not initialized before."
            )
            getLogger("log").warning(e)
            return

        self.conn.autocommit = True
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.conn.cursor()
        self.cursor.execute("SET client_min_messages = error;")

        # Aggregate functions for Symbolic Safe Sample
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior (text);")
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS ior_sfunc (text, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_sfunc (text, double precision) returns text AS $$select concat($1, '*(1 - ', cast($2 AS text), ')')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_finalfunc (text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_finalfunc (text) returns text AS $$select concat('(1 - ', $1, ')')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE ior (double precision) (sfunc = ior_sfunc, stype = text, finalfunc = ior_finalfunc, initcond = '1');"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_sfunc (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_sfunc (text, text) returns text AS $$select concat($1, '*(1 - ', $2, ')')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE ior (text) (sfunc = ior_sfunc, stype = text, finalfunc = ior_finalfunc, initcond = '1');"
        )
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior (text);")
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS l_ior_sfunc (text, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_sfunc (text, double precision) returns text AS $$select concat($1, ' + ', cast($2 AS text))$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_finalfunc (text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_finalfunc (text) returns text AS $$select concat('(', $1, ')')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE l_ior (double precision) (sfunc = l_ior_sfunc, stype = text, finalfunc = l_ior_finalfunc, initcond = '0');"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_sfunc (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_sfunc (text, text) returns text AS $$select concat($1, ' + ', $2)$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE l_ior (text) (sfunc = l_ior_sfunc, stype = text, finalfunc = l_ior_finalfunc, initcond = '0');"
        )
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS l1prod (double precision, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1prod (double precision, double precision) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', cast($2 AS text), ') - exp(', cast($1 AS text),'+', cast($2 AS text),'))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (text, double precision);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1prod (text, double precision) returns text AS $$select concat('log(exp(', $1, ') + exp(', cast($2 AS text), ') - exp(', $1,'+', cast($2 AS text),'))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (double precision, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1prod (double precision, text) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', $2, ') - exp(', cast($1 AS text),'+', $2,'))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1prod (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1prod (text, text) returns text AS $$select concat('log(exp(', $1, ') + exp(', $2, ') - exp(', $1,'+', $2,'))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS l1diff (double precision, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1diff (double precision, double precision) returns text AS $$select concat('log(1 - exp(', cast($2 AS text), ') + exp(', cast($1 AS text), '))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (text, double precision);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1diff (text, double precision) returns text AS $$select concat('log(1 - exp(', cast($2 AS text), ') + exp(', $1, '))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (double precision, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1diff (double precision, text) returns text AS $$select concat('log(1 - exp(', $2, ') + exp(', cast($1 AS text), '))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1diff (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1diff (text, text) returns text AS $$select concat('log(1 - exp(', $2, ') + exp(', $1, '))')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS l1sum (double precision, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1sum (double precision, double precision) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', cast($2 AS text), ') - 1)')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (text, double precision);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1sum (text, double precision) returns text AS $$select concat('log(exp(', $1, ') + exp(', cast($2 AS text), ') - 1)')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (double precision, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1sum (double precision, text) returns text AS $$select concat('log(exp(', cast($1 AS text), ') + exp(', $2, ') - 1)')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l1sum (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1sum (text, text) returns text AS $$select concat('log(exp(', $1, ') + exp(', $2, ') - 1)')$$ LANGUAGE SQL;"
        )

        # Aggregate functions for Numeric Safe Sample
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_sfunc_n (double precision, double precision) RETURNS double precision AS 'select max(val) from (VALUES($1 * (1.0 - $2)), (0.00001)) AS Vals(val)' LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_finalfunc_n (double precision) RETURNS double precision AS 'select 1.0 - $1' LANGUAGE SQL;"
        )
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior_n (double precision);")
        self.cursor.execute(
            "CREATE AGGREGATE ior_n (double precision) (sfunc = ior_sfunc_n, stype = double precision, finalfunc = ior_finalfunc_n, initcond = '1.0');"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_sfunc_n (double precision, double precision) RETURNS double precision AS 'select $1 + $2' LANGUAGE SQL;"
        )
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior_n (double precision);")
        self.cursor.execute(
            "CREATE AGGREGATE l_ior_n (double precision) (sfunc = l_ior_sfunc_n, stype = double precision, initcond = '0.0');"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1prod_n (double precision, double precision) RETURNS double precision AS 'select case when $1 > -745 AND $2 > -745 then m + ln(exp($1-m) + exp($2-m) - exp($1+$2-m)) else m end from(select max(val) as m from (VALUES($1), ($2)) AS Vals(val)) as foo' LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1diff_n (double precision, double precision) RETURNS double precision AS 'select case when $1 >= -745 and $2 >= -745 and 1+exp($1)-exp($2) > 0 then ln(1 - exp($2) + exp($1)) when $1 >= -745 and $2 >= -745 and 1+exp($1)-exp($2) <= 0 then NULL when $1 >= -745 and $2 < -745 then ln(1+exp($1)) when $1 < -745 and $2 > 0 then NULL when $1 < -745 and $2 <= 0 and $2 >= -745 then ln(1-exp($2)) else 0 end' LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l1sum_n (double precision, double precision) RETURNS double precision AS 'select case when $1 >= -745 and $2 >= -745 and exp($1)+exp($2)-1 > 0 then ln(exp($1) + exp($2) - 1) when $1 >= -745 and $2 >= -745 and exp($1)+exp($2)-1 <= 0 then NULL when $1 > 0 and $2 < -745 then ln(exp($1)-1) when $1 < -745 and $2 > 0 then ln(exp($2)-1) else NULL end' LANGUAGE SQL;"
        )

        # Aggregate functions for Automatic Differentiation
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior_ad (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS ior_ad (text);")
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS ior_sfunc_ad (text, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_sfunc_ad (text, double precision) returns text AS $$select concat($1, ' a = a*(1 - ', cast($2 AS text), ');')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_finalfunc_ad (text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_finalfunc_ad (text) returns text AS $$select concat($1, ' p = 1 - a;')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE ior_ad (double precision) (sfunc = ior_sfunc_ad, stype = text, finalfunc = ior_finalfunc_ad, initcond = '');"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS ior_sfunc_ad (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION ior_sfunc_ad (text, text) returns text AS $$select concat($1, ' a = a*(1 - ', $2, ');')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE ior_ad (text) (sfunc = ior_sfunc_ad, stype = text, finalfunc = ior_finalfunc_ad, initcond = '');"
        )
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior_ad (double precision);")
        self.cursor.execute("DROP AGGREGATE IF EXISTS l_ior_ad (text);")
        self.cursor.execute(
            "DROP FUNCTION IF EXISTS l_ior_sfunc_ad (text, double precision);"
        )
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_sfunc_ad (text, double precision) returns text AS $$select concat($1, ' p = p + ', cast($2 AS text), ';')$$ LANGUAGE SQL;"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_finalfunc_ad (text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_finalfunc_ad (text) returns text AS $$select $1 $$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE l_ior_ad (double precision) (sfunc = l_ior_sfunc_ad, stype = text, finalfunc = l_ior_finalfunc_ad, initcond = '');"
        )
        self.cursor.execute("DROP FUNCTION IF EXISTS l_ior_sfunc_ad (text, text);")
        self.cursor.execute(
            "CREATE OR REPLACE FUNCTION l_ior_sfunc_ad (text, text) returns text AS $$select concat($1, ' p = p + ', $2, ';')$$ LANGUAGE SQL;"
        )
        self.cursor.execute(
            "CREATE AGGREGATE l_ior_ad (text) (sfunc = l_ior_sfunc_ad, stype = text, finalfunc = l_ior_finalfunc_ad, initcond = '');"
        )

        time_total = time() - time_start
        getLogger("log").debug(
            "%-*s: %.1fs" % (self.pad - 1, "Time - initialize PSQLDB", time_total)
        )

    def learn_read_file(self, input_file=None):

        # ------------------------------------- Read the input file --------------------------------------
        time_start = time()
        self.initialize_psqldb()

        self._scores_correct = []
        self._examples = []

        self.target_predicate = ""

        def read(file):
            inputf = open(file, "r")
            for line in inputf:
                # Pre-processing
                line = line.replace(" ", "")
                if line == "\n":
                    continue
                elif line[0] == "%":
                    continue
                # Reading Lines
                if line[:5] == "base(":
                    predicate = line[5:].split("(")[0]
                    types = line[5:].split("(")[1].split(")")[-3].split(",")
                    arity = len(types)

                    if arity != 2:
                        getLogger("log").error(
                            "Arity of Predicate ("
                            + predicate
                            + ") is "
                            + str(arity)
                            + " instead of 2."
                        )
                        return

                    for type in types:
                        if type not in self.constant_dict:
                            self.constant_dict[type] = {}

                    self.predicate_dict[predicate] = types
                    self.cw_total[predicate] = 0
                    self.weights[predicate] = 0

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
                    self.target_predicate = line.split("(")[1].split("/")[0]
                    target_arity = int(line.split("/")[1].split(")")[0])

                    arguments = [Var("A"), Var("B")]
                    self._target = Term(str(self.target_predicate), *arguments)

                    # self.hypothesisAscii = 64 + self.targetArity
                    self.hypothesis_free_vars = 0
                    if target_arity != 2:
                        getLogger("log").error(
                            "Arity of Target Predicate ("
                            + self.target_predicate
                            + ") is "
                            + str(target_arity)
                            + " instead of 2."
                        )
                        return

                elif line[:5] == "mode(":
                    # Mode is not required when generating candidates from AMIE
                    continue

                else:
                    # Read Probabilistic Fact
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

                    self.cw_total[predicate] += 1
                    if self.facts_with_quotes:
                        subject = line.split("(")[1].split('","')[0] + '"'
                        object = (
                            '"' + "(".join(line.split("(")[1:]).split('","')[1][:-3]
                        )
                    else:
                        subject = line.split("(")[1].split(",")[0]
                        object = line.split(")")[-2].split(",")[1]

                    if subject not in self.constant_id:
                        self.constant_id[subject] = self.constant_count
                        self.constant_dict[self.predicate_dict[predicate][0]][
                            subject
                        ] = self.constant_count
                        self.constant_count += 1

                    if object not in self.constant_id:
                        self.constant_id[object] = self.constant_count
                        self.constant_dict[self.predicate_dict[predicate][1]][
                            object
                        ] = self.constant_count
                        self.constant_count += 1

                    subject_index = self.constant_id[subject]
                    object_index = self.constant_id[object]
                    self.cursor.execute(
                        "INSERT INTO "
                        + predicate
                        + " VALUES ("
                        + str(subject_index)
                        + ", "
                        + str(object_index)
                        + ", "
                        + prob
                        + ");"
                    )

                    if predicate == self.target_predicate:
                        args = [subject, object]
                        prob = float(prob)
                        if args in self.examples:
                            old_prob = self._scores_correct[self.examples.index(args)]
                            new_prob = prob + old_prob - prob * old_prob
                            self._scores_correct[self.examples.index(args)] = new_prob
                        else:
                            self._examples.append(args)
                            self._scores_correct.append(prob)
            inputf.close()

        if self.target is not None:
            target_arity = self._target._Term__arity
            self.target_predicate = self._target._Term__functor
            # self.hypothesisAscii = 64 + self.targetArity
            self.hypothesis_free_vars = 0
            if target_arity != 2:
                getLogger("log").error(
                    "Arity of Target Predicate ("
                    + self.target_predicate
                    + ") is "
                    + str(target_arity)
                    + " instead of 2."
                )
                return

        if input_file is None:
            read(self.input_file)
        else:
            read(input_file)

        self.total_examples = len(self.examples)
        getLogger("log").info(
            "%-*s: %d" % (self.pad, "Number of examples (M)", self.total_examples)
        )
        getLogger("log").info(
            "%-*s: %.4f"
            % (self.pad, "Positive probabilistic part (P)", sum(self._scores_correct))
        )
        getLogger("log").info(
            "%-*s: %.4f"
            % (
                self.pad,
                "Negative probabilistic part (N)",
                self.total_examples - sum(self._scores_correct),
            )
        )

        self.predicate_list = list(self.predicate_dict.keys())
        self.predicate_list.remove(self.target_predicate)
        self.weights.pop(self.target_predicate, None)

        self.time_read = time() - time_start

        getLogger("log").info(
            "%-*s: %s"
            % (
                self.pad,
                "Target Base List",
                str(self.predicate_dict[self.target_predicate]),
            )
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Predicate Dict", str(self.predicate_dict))
        )
        getLogger("log").log(
            8, "%-*s: %s" % (self.pad, "Universal Constant Dict", str(self.constant_id))
        )
        getLogger("log").debug(
            "%-*s: %.1fs" % (self.pad - 1, "Time - readFile", self.time_read)
        )

    def convert_problog_to_amie(self):
        if not (os.path.exists(self.tsv_file)):
            input_file = open(self.input_file, "r")
            output_file = open(self.tsv_file, "w+")

            for line in input_file:
                line = line.replace(" ", "")
                if (
                    line == "\n"
                    or line[0] == "%"
                    or line[:4] == "mode"
                    or line[:5] == "learn"
                ):
                    continue
                elif line[:4] == "base":
                    predicate = line.split("(")[1]
                    attributes = line.split("(")[2].split(")")[0].split(",")
                    output_file.write(
                        "<"
                        + predicate
                        + ">\t<http://www.w3.org/2000/01/rdf-schema#domain>\t<"
                        + attributes[0]
                        + ">\n"
                    )
                    output_file.write(
                        "<"
                        + predicate
                        + ">\t<http://www.w3.org/2000/01/rdf-schema#range>\t<"
                        + attributes[1]
                        + ">\n"
                    )
                else:
                    # Read Probabilistic Fact
                    if self.facts_with_quotes:
                        if "::" in line.split('"')[0]:
                            predicate = line.split("::")[1].split("(")[0]
                        else:
                            predicate = line.split("(")[0]
                        subject = line.split("(")[1].split('","')[0] + '"'
                        object = (
                            '"' + "(".join(line.split("(")[1:]).split('","')[1][:-3]
                        )
                        attributes = [subject, object]
                    else:

                        if "::" in line:
                            predicate = line.split("::")[1].split("(")[0]
                            attributes = (
                                line.split("::")[1]
                                .split("(")[1]
                                .split(")")[0]
                                .split(",")
                            )
                            prob = line.split("::")[0]
                            if (
                                float(prob) < self.tolerance
                            ):  # Skip writing the super-unlikely facts
                                continue
                        else:
                            predicate = line.split("(")[0]
                            attributes = line.split("(")[1].split(")")[0].split(",")
                    output_file.write(
                        "<"
                        + attributes[0]
                        + ">\t<"
                        + predicate
                        + ">\t<"
                        + attributes[1]
                        + ">\n"
                    )

            input_file.close()
            output_file.close()

    def get_amie_rules(self):

        if self.allow_recursion:
            if self.max_length is not None:
                amie_query = (
                    "java -jar amie_plus.jar -maxad "
                    + str(self.max_length)
                    + " -minhc "
                    + str(self.minhc)
                    + " -minpca "
                    + str(self.minpca)
                    + " -htr '<"
                    + self.target_predicate
                    + ">' -oute "
                    + self.tsv_file
                )
            else:
                amie_query = (
                    "java -jar amie_plus.jar -minhc "
                    + str(self.minhc)
                    + " -minpca "
                    + str(self.minpca)
                    + " -htr '<"
                    + self.target_predicate
                    + ">' -oute "
                    + self.tsv_file
                )
        else:
            if self.max_length is not None:
                amie_query = (
                    "java -jar amie_plus.jar -maxad "
                    + str(self.max_length)
                    + " -minhc "
                    + str(self.minhc)
                    + " -minpca "
                    + str(self.minpca)
                    + " -htr '<"
                    + self.target_predicate
                    + ">' -bexr '<"
                    + self.target_predicate
                    + ">' -oute "
                    + self.tsv_file
                )
            else:
                amie_query = (
                    "java -jar amie_plus.jar -minhc "
                    + str(self.minhc)
                    + " -minpca "
                    + str(self.minpca)
                    + " -htr '<"
                    + self.target_predicate
                    + ">' -bexr '<"
                    + self.target_predicate
                    + ">' -oute "
                    + self.tsv_file
                )

        getLogger("log").debug("Running AMIE+ : %s" % amie_query)
        output_string = Popen(amie_query, stdout=PIPE, shell=True).communicate()
        output_list = output_string[0].decode("utf-8").split("\n")[13:-4]

        rule_list = []
        coverage_list = []
        std_confidence_list = []
        pca_confidence_list = []

        for row in output_list:
            line = row.split("\t")[0]
            confidence = row.split("\t")[1].replace(",", ".")
            std_confidence = row.split("\t")[2].replace(",", ".")
            pca_confidence = row.split("\t")[3].replace(",", ".")

            head = line.split("=>")[1].split("<")[1].split(">")[0]

            body = line.split("=>")[0]
            i = 0
            body_items = []
            while i < len(body):
                if body[i] == "?":
                    body_items.append(body[i + 1].upper())
                    i += 2
                    continue
                elif body[i] == "<":
                    start = i + 1
                    while body[i] != ">":
                        i += 1
                    body_items.append(body[start:i])
                i += 1

            head_var1 = line.split("=>")[1].split("?")[1][0].upper()
            head_var2 = line.split("=>")[1].split("?")[2][0].upper()
            replace_variable = False
            head_dict = {}
            max_ascii = 65

            if head_var1 != "A" or head_var2 != "B":
                i = 0
                while i < len(body_items):
                    if i % 3 == 0:
                        rule_ascii = ord(body_items[i])
                        max_ascii = max(max_ascii, rule_ascii)
                        i += 2
                    elif i % 3 == 2:
                        rule_ascii = ord(body_items[i])
                        max_ascii = max(max_ascii, rule_ascii)
                        i += 1
                if head_var1 != "A":
                    head_dict[head_var1] = "A"
                    head_dict["A"] = chr(max_ascii + 1)
                    max_ascii += 1
                if head_var1 != "B":
                    head_dict[head_var1] = "B"
                    head_dict["B"] = chr(max_ascii + 1)
                    max_ascii += 1
                replace_variable = True

            i = 0
            body_list = []
            body_dict = {"A": "A", "B": "B"}
            max_ascii = 66
            while i < len(body_items):
                if i % 3 == 0:
                    var1 = body_items[i]
                    if replace_variable is True and body_items[i] in head_dict:
                        var1 = head_dict[body_items[i]]
                    if var1 in body_dict:
                        var1 = body_dict[var1]
                    else:
                        body_dict[var1] = chr(max_ascii + 1)
                        var1 = chr(max_ascii + 1)
                        max_ascii += 1
                elif i % 3 == 1:
                    relation = body_items[i]
                elif i % 3 == 2:
                    var2 = body_items[i]
                    if replace_variable is True and body_items[i] in head_dict:
                        var2 = head_dict[body_items[i]]
                    if var2 in body_dict:
                        var2 = body_dict[var2]
                    else:
                        body_dict[var2] = chr(max_ascii + 1)
                        var2 = chr(max_ascii + 1)
                        max_ascii += 1

                    arguments = [Var(var1), Var(var2)]
                    literal = Term(str(relation), *arguments)
                    body_list.append(literal)
                i += 1

            head_arguments = [Var(head_var1), Var(head_var2)]
            head_literal = Term(str(head), *head_arguments)

            rule = (head_literal, body_list)

            add_rule = True
            if self.enforce_type_constraints:
                var_dict = {}
                for literal in body_list:
                    for i, arg in enumerate(literal.args):
                        predicate_type = self.predicate_dict[literal.functor][i]
                        rule_ascii = ord(str(arg))
                        if rule_ascii < 65 + 2:
                            if (
                                predicate_type
                                != self.predicate_dict[self.target_predicate][
                                    rule_ascii - 65
                                ]
                            ):
                                # Type Mismatch in the Rule
                                getLogger("log").info(
                                    "%-*s: %s"
                                    % (
                                        self.pad,
                                        "Removing Rule from AMIE List",
                                        str(rule),
                                    )
                                )
                                add_rule = False
                        if arg in var_dict:
                            if predicate_type != var_dict[arg]:
                                # Type Mismatch in the Rule
                                getLogger("log").info(
                                    "%-*s: %s"
                                    % (
                                        self.pad,
                                        "Removing Rule from AMIE List",
                                        str(rule),
                                    )
                                )
                                add_rule = False
                        else:
                            var_dict[arg] = predicate_type

            if add_rule:
                rule_list.append(rule)
                coverage_list.append(confidence)
                std_confidence_list.append(std_confidence)
                pca_confidence_list.append(pca_confidence)

        if len(rule_list) == 0:
            getLogger("log").error(
                "%-*s"
                % (
                    self.pad,
                    "No significant and predicate_type consistent rules returned by AMIE",
                )
            )
            return rule_list, coverage_list, std_confidence_list, pca_confidence_list
        else:
            index = list(range(len(std_confidence_list)))
            index.sort(key=std_confidence_list.__getitem__, reverse=True)
            std_confidence_list = [std_confidence_list[i] for i in index]
            rule_list = [rule_list[i] for i in index]
            coverage_list = [coverage_list[i] for i in index]
            pca_confidence_list = [pca_confidence_list[i] for i in index]

            if self.max_amie_rules is not None:
                i = int(self.max_amie_rules)
                return (
                    rule_list[:i],
                    coverage_list[:i],
                    std_confidence_list[:i],
                    pca_confidence_list[:i],
                )
            else:
                return (
                    rule_list,
                    coverage_list,
                    std_confidence_list,
                    pca_confidence_list,
                )

    def get_amie_hypothesis(self, amie_rule_list):
        old_rule = FOILRule(self.target)
        old_rule = old_rule & Term("fail")
        old_rule = FOILRule(self.target, previous=old_rule)
        for (headLiteral, amieLiteralList) in amie_rule_list:
            new_rule = FOILRule(target=self.target, previous=old_rule)
            for literal in amieLiteralList:
                new_rule = new_rule & literal
            old_rule = new_rule

        self.learn_parse_rules(old_rule)
        self.learn_get_query_string(old_rule)
        if self.check_unsafe_rule(old_rule.query_string):
            # If current hypothesis is unsafe, then first check for unsafe rules, else remove the last rule and recurse.
            getLogger("log").info("Query Unsafe\t:" + str(old_rule.query_string))
            subqueries = old_rule.query_string.split(" v ")
            new_rule_list = []
            for i, subquery in enumerate(subqueries[1:]):
                if not self.check_unsafe_rule(subquery):
                    new_rule_list.append(amie_rule_list[i])
            if new_rule_list == amie_rule_list:
                return self.get_amie_hypothesis(amie_rule_list[:-1])
            else:
                return self.get_amie_hypothesis(new_rule_list)
        else:
            # Return the safe hypothesis
            getLogger("log").info("Query Safe\t:" + str(old_rule.query_string))

            return old_rule

    def learn_parse_rules(self, hypothesis, merge=True):
        time_start = time()
        rule_list = []
        hypothesis.probability_list = []
        hypothesis.confidenceList = []
        hypothesis.body_list = []
        literal_set_list = []
        hypothesis.predicate_list = []

        rule = hypothesis
        while rule.previous is not None:
            rule_list.append(rule)
            prob = rule.get_rule_probability()
            if prob is None:
                prob = 1 - self.tolerance
            hypothesis.probability_list.append(prob)
            # hypothesis.confidenceList.append(rule.confidence)
            body = rule.get_literals()[1:]
            hypothesis.body_list.append(body)

            literal_set = set()
            for literal in body:
                literal_set.add(literal)
                predicate = literal.functor
                if predicate not in hypothesis.predicate_list and predicate not in [
                    "true",
                    "fail",
                    "false",
                ]:
                    hypothesis.predicate_list.append(predicate)

            literal_set_list.append(literal_set)
            rule = rule.previous

        if merge:
            i = 0
            i_rule = hypothesis
            while i < len(hypothesis.body_list):
                j = i + 1
                previous_j_rule = i_rule
                j_rule = i_rule.previous
                while j < len(hypothesis.body_list):
                    if literal_set_list[i] == literal_set_list[j]:
                        # Merge rules i and j

                        # Update Prob of first rule
                        p1 = hypothesis.probability_list[i]
                        p2 = hypothesis.probability_list[j]
                        p = p1 + p2 - p1 * p2
                        hypothesis.probability_list[i] = p
                        if p > 1 - self.tolerance:
                            i_rule.set_rule_probability(None)
                        else:
                            i_rule.set_rule_probability(p)

                        # Delete second rule
                        previous_j_rule.previous = j_rule.previous
                        del hypothesis.body_list[j]
                        del hypothesis.probability_list[j]
                        del literal_set_list[j]
                        continue
                    j += 1
                    previous_j_rule = j_rule
                    j_rule = j_rule.previous
                i_rule = i_rule.previous
                i += 1

        hypothesis.probability_list.reverse()
        hypothesis.body_list.reverse()
        hypothesis.predicate_list.reverse()
        for i, prob in enumerate(hypothesis.probability_list):
            hypothesis.predicate_list.append("p_" + str(i))
            table_name = "p_" + str(i)
            self.cursor.execute("DROP TABLE IF EXISTS " + table_name + ";")
            self.cursor.execute(
                "CREATE TABLE " + table_name + " (v0 integer, p double precision);"
            )

            if table_name not in self.weights:
                if prob < 1 - self.tolerance:
                    self.weights[table_name] = prob
                else:
                    self.weights[table_name] = 1 - self.tolerance

        time_total = time() - time_start

        getLogger("log").info(
            "%-*s: %s"
            % (self.pad, "Probability List", str(hypothesis.probability_list))
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Body List", str(hypothesis.body_list))
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Predicate List", str(hypothesis.predicate_list))
        )
        getLogger("log").info(
            "%-*s: %.1fs" % (self.pad, "Time - parseRules", time_total)
        )

        return hypothesis

    def learn_get_query_string(self, hypothesis):

        time_start = time()
        # --------------------------- Make a single query out of the hypothesis ---------------------------

        # ruleAscii = 64 + self.targetArity
        free_var_id = 0
        for i, body in enumerate(hypothesis.body_list):
            replace_dict = {}
            for j, literal in enumerate(body):
                var_list = []
                for arg in literal.args:
                    if ord(str(arg)) > 64 + 2:
                        if str(arg) in replace_dict:
                            var_list.append(Var(replace_dict[str(arg)]))
                        else:
                            # replace_dict[str(arg)] = chr(ruleAscii + 1)
                            # var_list.append(Var(chr(ruleAscii + 1)))
                            # ruleAscii += 1

                            replace_dict[str(arg)] = "V" + str(free_var_id)
                            var_list.append(Var("V" + str(free_var_id)))
                            free_var_id += 1
                    else:
                        var_list.append(arg)
                body[j] = Term(literal.functor, *var_list)

            # p = Term("p_" + str(i), *[Var(chr(ruleAscii+1))])
            # ruleAscii += 1
            p = Term("p_" + str(i), *[Var("V" + str(free_var_id))])
            free_var_id += 1

            body.append(p)

        # hypothesis.maxAscii = ruleAscii
        hypothesis.total_free_vars = free_var_id
        hypothesis.query_string = " v ".join(
            [str(item)[1:-1].replace(" ", "") for item in hypothesis.body_list]
        )

        time_total = time() - time_start

        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Body List", str(hypothesis.body_list))
        )
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Query String", hypothesis.query_string)
        )
        getLogger("log").info(
            "%-*s: %.1fs" % (self.pad, "Time - getQueryString", time_total)
        )
        return hypothesis

    def instantiate_tables(self, instantiated_table_set):
        # ---------------------------------- Create Instantiated Tables ----------------------------------

        getLogger("log").log(
            8, "Instantiated Table Set\t\t\t: %s" % str(instantiated_table_set)
        )
        getLogger("log").log(
            8,
            "Previous Instantiated Table Set\t: %s"
            % str(self.already_instantiated_tables),
        )

        for table_item in instantiated_table_set - self.already_instantiated_tables:
            table_names = table_item.split("_")
            table = table_names[0]
            arg_list = table_names[1:]

            select_string = ""
            where_string = ""
            count = 0
            for i, arg in enumerate(arg_list):
                if arg != "all":
                    if where_string == "":
                        where_string = "v" + str(i) + " = " + str(arg)
                    else:
                        where_string = (
                            where_string + " AND v" + str(i) + " = " + str(arg)
                        )
                else:
                    if select_string == "":
                        select_string = "v" + str(i) + " as v" + str(count)
                    else:
                        select_string = (
                            select_string + ", v" + str(i) + " as v" + str(count)
                        )
                    count += 1

            if select_string == "":
                self.cursor.execute(
                    "Select ior(p) from " + table + " where " + where_string + ";"
                )
                prob = self.cursor.fetchone()[0]

                # Create a table by the name 'newTable' which will have exactly 1 free variable
                self.cursor.execute("DROP TABLE IF EXISTS " + table_item + ";")
                self.cursor.execute(
                    "CREATE TABLE " + table_item + " (v0 integer, p double precision);"
                )
                if prob != "(1 - 1)":
                    prob = eval(prob)
                    if prob > 1 - self.tolerance:
                        prob = 1 - self.tolerance
                    self.cursor.execute(
                        "INSERT INTO " + table_item + " VALUES (0, " + str(prob) + ");"
                    )

            elif where_string == "":
                getLogger("log").error(
                    "Exception Occurred: Empty select_string or where_string in "
                    % table_item
                )
                return
            else:
                select_string = select_string + ", p"

                getLogger("log").log(
                    8,
                    "Probfoil: CREATE TABLE IF NOT EXISTS %s AS (SELECT %s FROM %s WHERE %s);"
                    % (table_item, select_string, table, where_string),
                )
                self.cursor.execute(
                    "CREATE TABLE IF NOT EXISTS "
                    + table_item
                    + " AS (SELECT "
                    + select_string
                    + " FROM "
                    + table
                    + " WHERE "
                    + where_string
                    + ");"
                )

            self.already_instantiated_tables.add(table_item)

    def get_query_for_example(self, hypothesis, example):

        if hypothesis.replaceableQuery == "":
            hypothesis.replaceableTables = set()
            free_var_id = hypothesis.total_free_vars
            k = 1
            start = 0
            l = 0
            new_table = ""
            replace_predicate = False
            self.replace_body = False
            instantiated_query_string = ""
            while k < len(hypothesis.query_string):
                if hypothesis.query_string[k - 1] == "(":
                    replace_predicate = False
                    table = hypothesis.query_string[start : k - 1]
                    new_table = table
                    left = k - 1
                    l = 0
                    if ord(hypothesis.query_string[k]) <= 64 + 2:
                        new_table += "_" + hypothesis.query_string[k]
                        self.replace_body = True
                        replace_predicate = True
                    else:
                        new_table = new_table + "_all"

                elif (
                    hypothesis.query_string[k - 1] == ","
                    and hypothesis.query_string[k - 2] != ")"
                ):
                    l = l + 1
                    if ord(hypothesis.query_string[k]) <= 64 + 2:
                        new_table += "_" + hypothesis.query_string[k]
                        self.replace_body = True
                        replace_predicate = True
                    else:
                        new_table = new_table + "_all"

                elif hypothesis.query_string[k] == ")":
                    if (
                        replace_predicate is True
                    ):  # This means that the literal contains at least 1 fixed variable that needs instantiation

                        # Replace 'hypothesis.query_string[left:k+1]' by only free variables
                        # If variableString = '(A,B,C)' ==> '(C)'
                        # If variableString = '(A,B)' or '(A)' ==> then don't add the new_table. Instead execute a query to get the probability of a tuple when A and B are instantiated.

                        table_names = new_table.split("_")
                        arg_list = table_names[1:]
                        var_list = hypothesis.query_string[left + 1 : k].split(",")
                        really_replace_predicate = False

                        var_string = ""
                        for j, arg in enumerate(arg_list):
                            if arg == "all":
                                really_replace_predicate = True
                                if var_string == "":
                                    var_string = var_list[j]
                                else:
                                    try:
                                        var_string = var_string + "," + var_list[j]
                                    except:
                                        print(hypothesis.query_string)
                                        print(new_table)
                                        print(arg_list)
                                        print(var_list)
                                        raise

                        if really_replace_predicate is True:  # Eg: '(A,B,C)' ==> '(C)'
                            hypothesis.replaceableTables.add(new_table)
                            instantiated_query_string = (
                                instantiated_query_string
                                + new_table
                                + "("
                                + var_string
                                + ")"
                            )
                            # instantiated_query_string = instantiated_query_string + new_table + hypothesis.query_string[left:k+1]
                        else:  # This means that the literal contains only fixed variables which needs instantiation, Eg: (A,B) or (A)

                            # Calculate the probability of a tuple from a fully instantiated table name
                            #'author_0_1' ==> Create and execute a psql query which subsets 'author' on v0 = 0 and v1 = 1 and then aggregate by ior

                            hypothesis.replaceableTables.add(new_table)

                            instantiated_query_string = (
                                instantiated_query_string
                                + new_table
                                + "(V"
                                + str(free_var_id)
                                + ")"
                            )
                            free_var_id += 1
                    else:
                        instantiated_query_string = (
                            instantiated_query_string
                            + hypothesis.query_string[start : k + 1]
                        )
                    start = k + 1
                elif (
                    hypothesis.query_string[k] == ","
                    and hypothesis.query_string[k - 1] == ")"
                ) or hypothesis.query_string[k] == "~":
                    instantiated_query_string = (
                        instantiated_query_string + hypothesis.query_string[k]
                    )
                    start = k + 1
                elif hypothesis.query_string[k - 3 : k] == " v ":
                    # Add a dummy variable wrt to current prob. Later reset the prob to 1
                    instantiated_query_string = instantiated_query_string + " v "
                    start = k
                k = k + 1

            clause_list = instantiated_query_string.split(" v ")
            if "" not in clause_list:
                instantiated_query_string = ""
                for clause in clause_list:
                    clause_split = clause.split(",")
                    clause_split[:] = (value for value in clause_split if value != "")
                    if instantiated_query_string == "":
                        instantiated_query_string = ",".join(clause_split)
                    else:
                        instantiated_query_string = (
                            instantiated_query_string + " v " + ",".join(clause_split)
                        )
                hypothesis.replaceableQuery = instantiated_query_string
            else:
                hypothesis.replaceableQuery = ""

        query = copy(hypothesis.replaceableQuery)
        for i, value in enumerate(example):
            query = query.replace(chr(65 + i), str(self.constant_id[value]))

        instantiated_tables = set()
        for element in hypothesis.replaceableTables:
            table = copy(element)
            for i, value in enumerate(example):
                table = table.replace(chr(65 + i), str(self.constant_id[value]))
            instantiated_tables.add(table)

        self.instantiate_tables(instantiated_tables)

        return query

    def execute_canonical_expression(self, SQLQuery, tableList, variableMapping):

        if SQLQuery in ["Failed to parse", None, "Query is unsafe"]:
            return None

        output_string = None
        true_sql_query = ""
        i = 0
        while i < len(SQLQuery):
            if SQLQuery[i] == "<":
                start = i + 1
                while SQLQuery[i] != ">":
                    i += 1
                expression = SQLQuery[start:i]

                true_expression = ""
                if expression[0:5] == "table":
                    table_number = int(expression[5:])
                    true_expression = tableList[table_number]
                else:
                    # Replace Domains and Lambdas appropriately
                    # Eg:z_table2 >> z_author_0_0 >> z_author
                    # Eg:y_A >> y_researcher; y_B >> y_paper >> Actual value of number of different constants as 'papers'
                    j = 0
                    last_end = 0

                    while j < len(expression) - 1:
                        if expression[j : j + 2] == "z_":
                            true_expression = true_expression + expression[last_end:j]
                            start = j
                            j += 2
                            while (
                                expression[j].isalpha() or expression[j].isdigit()
                            ) and j < len(expression):
                                j += 1
                            table_string = expression[start + 2 : j]
                            table_number = int(table_string[5:])
                            table = tableList[table_number]
                            actual_table = table.split("_")[0]
                            if actual_table == "p":
                                # true_expression = true_expression + "0"
                                true_expression = true_expression + "z_" + str(table)
                            else:
                                true_expression = (
                                    true_expression + "z_" + str(actual_table)
                                )
                            last_end = j
                            continue
                        elif expression[j : j + 2] == "y_":

                            true_expression = true_expression + expression[last_end:j]
                            start = j

                            variable_string = expression[start + 2]
                            k = 3
                            while expression[start + k].isdigit():
                                variable_string = (
                                    variable_string + expression[start + k]
                                )
                                k += 1
                                if start + k == len(expression):
                                    break

                            j += k
                            if variableMapping[variable_string] == "p":
                                domain = 1
                            elif variableMapping[variable_string] == "all":
                                domain = 1
                            else:
                                domain = len(
                                    self.constant_dict[variableMapping[variable_string]]
                                )

                            true_expression = true_expression + str(domain)

                            last_end = j
                            continue
                        j += 1
                    true_expression = true_expression + expression[last_end:]

                true_sql_query = true_sql_query + true_expression
            else:
                true_sql_query = true_sql_query + SQLQuery[i]

            i += 1

        try:
            self.cursor.execute(true_sql_query)
            output = self.cursor.fetchall()

            if output[0][0] not in ["Failed to parse", None, "Query is unsafe"]:
                output_string = "(1 - exp(" + output[0][0] + "))"

        except psycopg2.Error as e:
            getLogger("log").error("Exception Occurred\t\t\t\t: %s" % str(e))
            getLogger("log").warning(
                "Execute Expression >> SQL error \t: " + e.pgerror[:-1]
            )
            getLogger("log").warning(
                "Execute Expression >> Query \t: " + true_sql_query
            )

        return output_string

    def get_query_expression(self, query):
        # query = "r1(A) v r2(B),r3(C) v r4(D),r5(E),r3(F) v r6(G),r1(H),r7(I)"  #Test

        if query in ["true", ""]:
            return "1"

        conjunct_list = query.split(" v ")

        if len(conjunct_list) > 1:

            new_conjunct_list = self.partition_ucq(query)
            main_expression = ""
            for conjunct in new_conjunct_list:
                expression = self.get_conjunct_expression(conjunct)
                if expression is not None:
                    if main_expression == "":
                        main_expression = "(1 - " + expression + ")"
                    else:
                        main_expression = main_expression + "*(1 - " + expression + ")"

            if main_expression != "":
                main_expression = "(1 - " + main_expression + ")"
            else:
                main_expression = None
        else:
            main_expression = self.get_conjunct_expression(query)

        return main_expression

    def get_conjunct_expression(self, query):
        canonical_query, table_list, variable_mapping = self.get_canonical_form(query)
        if canonical_query in self.symbolic_query_dict:
            canonical_expression = self.symbolic_query_dict[canonical_query]
        else:
            time_start = time()
            canonical_expression = getExpression(canonical_query)
            self.time_getExpression = self.time_getExpression + time() - time_start
            self.stats_getExpression += 1
            self.symbolic_query_dict[canonical_query] = canonical_expression

        output_string = self.execute_canonical_expression(
            canonical_expression, table_list, variable_mapping
        )

        return output_string

    def get_loss_for_example(self, hypothesis, i):

        if hypothesis.expression_list[i] == "":
            example = self.examples[i]
            query = self.get_query_for_example(hypothesis, example)
            output_string = self.get_query_expression(query)
            if output_string in ["Failed to parse", None, "Query is unsafe"]:
                return "0"

            if output_string != "1":
                term = "(" + output_string + ")"
            else:
                term = "1"

            for j, predicate in enumerate(
                sorted(hypothesis.predicate_list, reverse=True)
            ):
                term = term.replace("z_" + predicate, "y[" + str(j) + "]")
            hypothesis.expression_list[i] = term
        else:
            term = hypothesis.expression_list[i]

        loss = "0"
        correct = self._scores_correct[i]

        if self.global_score == "accuracy":
            if i in self.cw_negatives:
                loss = loss + " +" + str(self.cw_negative_weight) + "*" + term + ""
            elif i in self.ow_negatives:
                loss = loss + " +" + str(self.ow_negative_weight) + "*" + term + ""
            else:
                loss = loss + " +abs(" + str(correct) + " -" + term + ")"
            return loss[3:]

        elif self.global_score == "squared_loss":
            if i in self.cw_negatives:
                loss = loss + " +" + str(self.cw_negative_weight) + "*(" + term + ")**2"
            elif i in self.ow_negatives:
                loss = loss + " +" + str(self.ow_negative_weight) + "*(" + term + ")**2"
            else:
                loss = loss + " + (" + str(correct) + " -" + term + ")**2"
            return loss[3:]

        elif self.global_score == "cross_entropy":
            if i in self.cw_negatives:
                loss = (
                    loss
                    + " -"
                    + str(self.cw_negative_weight)
                    + "*log(max(1-("
                    + term
                    + "),"
                    + str(self.tolerance)
                    + "))"
                )
            elif i in self.ow_negatives:
                loss = (
                    loss
                    + " -"
                    + str(self.ow_negative_weight)
                    + "*log(max(1-("
                    + term
                    + "),"
                    + str(self.tolerance)
                    + "))"
                )
            else:
                loss = (
                    loss
                    + " -"
                    + str(correct)
                    + "*log(max("
                    + term
                    + ","
                    + str(self.tolerance)
                    + ")) -(1-"
                    + str(correct)
                    + ")*log(max(1-("
                    + term
                    + "),"
                    + str(self.tolerance)
                    + "))"
                )
            return loss[2:]

    def learn_initialize_weights(self, hypothesis):

        getLogger("log").log(9, str(hypothesis.to_clauses()))

        y = []
        for j, predicate in enumerate(hypothesis.predicate_list):
            if len(predicate) > 2 and predicate[:3] == "p_0":
                y.append(self.regularize(self.weights[predicate], 5))
            elif len(predicate) > 2 and predicate[:2] == "p_":

                i = 2
                while i < len(predicate) and predicate[i].isdigit():
                    i += 1
                index = int(predicate[2:i])

                confidence = float(self.std_confidence_list[index - 1])
                prob = self.rule_get_conditional_probability(index - 1)
                if confidence != prob:
                    getLogger("log").log(
                        9,
                        "Amie Confidence Value for %s is %s"
                        % (str(hypothesis.to_clauses()[index + 1]), str(confidence)),
                    )
                    getLogger("log").log(
                        9,
                        "Conditional Probability for %s is %s"
                        % (str(hypothesis.to_clauses()[index + 1]), str(prob)),
                    )
                else:
                    getLogger("log").log(
                        9,
                        "Conditional Probability for %s is %s"
                        % (str(hypothesis.to_clauses()[index + 1]), str(prob)),
                    )
                y.append(self.regularize(prob, 5))
            elif predicate in self.weights:
                y.append(self.regularize(self.weights[predicate], 5))
            else:
                y.append(0.0)

        getLogger("log").info("%-*s: %s" % (self.pad, "Lambdas initialized to", str(y)))
        return y

    def learn_stochastic_gradient_descent(self, hypothesis):
        time_start = time()

        old_weight_list = self.learn_initialize_weights(hypothesis)
        new_weight_list = old_weight_list
        iterations = self.iterations

        # Full Batch
        fixed_point_reached = False
        same_count = 0
        super_old_weight_list = copy(old_weight_list)
        error_count = 0
        for k in range(0, iterations):
            i = random.randint(0, self.total_examples - 1)

            term = self.get_loss_for_example(hypothesis, i)

            if self.global_score == "cross_entropy":
                if term not in ["Failed to parse", None, "Query is unsafe"]:

                    if i in self.cw_negatives:
                        loss = (
                            " -"
                            + str(self.cw_negative_weight)
                            + "*log(max(1-("
                            + term
                            + "),"
                            + str(self.tolerance)
                            + "))"
                        )
                    elif i in self.ow_negatives:
                        loss = (
                            " -"
                            + str(self.ow_negative_weight)
                            + "*log(max(1-("
                            + term
                            + "),"
                            + str(self.tolerance)
                            + "))"
                        )
                    else:
                        correct = self._scores_correct[i]
                        loss = (
                            " -"
                            + str(correct)
                            + "*log(max("
                            + term
                            + ","
                            + str(self.tolerance)
                            + ")) -(1-"
                            + str(correct)
                            + ")*log(max(1-("
                            + term
                            + "),"
                            + str(self.tolerance)
                            + "))"
                        )

                else:
                    continue

            elif self.global_score == "accuracy":
                if term not in ["Failed to parse", None, "Query is unsafe"]:
                    if i in self.cw_negatives:
                        loss = str(self.cw_negative_weight) + "*" + term + ""
                    elif i in self.ow_negatives:
                        loss = str(self.ow_negative_weight) + "*" + term + ""
                    else:
                        loss = "abs(" + str(self._scores_correct[i]) + " -" + term + ")"
                else:
                    continue

            elif self.global_score == "squared_loss":
                if term not in ["Failed to parse", None, "Query is unsafe"]:
                    if i in self.cw_negatives:
                        loss = str(self.cw_negative_weight) + "*(" + term + ")**2"
                    elif i in self.ow_negatives:
                        loss = str(self.ow_negative_weight) + "*(" + term + ")**2"
                    else:
                        loss = "(" + str(self._scores_correct[i]) + " -" + term + ")**2"
                else:
                    continue

            expression = loss
            # getLogger('probfoil').debug('%d.\tLoss = %s' % (i, str(loss)))
            exec("evalFunc = lambda y : " + expression, globals())
            gradient, hessian = gh(evalFunc)

            try:
                # Update Lambdas for Rule Weights
                grad = gradient(old_weight_list)
                # grad = evalFunc(old_weight_list).gradient(old_weight_list)

                oldgrad = grad
                grad = [self.learning_rate * component for component in grad]
                max_ratio = 1
                for j, predicate in enumerate(hypothesis.predicate_list):
                    if len(predicate) > 2 and predicate[:2] == "p_":
                        if max_ratio < abs(grad[j] / self.max_increment[0]):
                            max_ratio = abs(grad[j] / self.max_increment[0])
                for j, predicate in enumerate(hypothesis.predicate_list):
                    if len(predicate) > 2 and predicate[:2] == "p_":
                        new_weight_list[j] = old_weight_list[j] - grad[j] / max_ratio
                        # new_weight_list[j] = old_weight_list[j] - grad[j]
                        if new_weight_list[j] < 5 * self.tolerance:
                            new_weight_list[j] = 5 * self.tolerance
                        elif new_weight_list[j] > 1 - 5 * self.tolerance:
                            new_weight_list[j] = 1 - 5 * self.tolerance

                if self.fixed_point and new_weight_list == super_old_weight_list:
                    if same_count == 100:
                        fixed_point_reached = True
                    else:
                        same_count += 1
                else:
                    same_count = 0

                super_old_weight_list = copy(new_weight_list)

                if k % self.step_check == 0:
                    getLogger("log").debug(
                        str(round(time() - time_start))
                        + "s : "
                        + str(k)
                        + " iterations completed out of "
                        + str(iterations)
                    )

                if self.fixed_point and fixed_point_reached:
                    getLogger("log").debug("Fixed point reach at iteration: " + str(k))
                    break

            except Exception as e:
                error_count += 1
                getLogger("log").warning(
                    str(error_count)
                    + " Exception encountered in "
                    + str(k)
                    + "th iteration of SGD: "
                    + str(e)
                )
            old_weight_list = copy(new_weight_list)

        selected_weight_list = new_weight_list

        new_weight = copy(self.weights)
        for predicate, weight in zip(hypothesis.predicate_list, selected_weight_list):
            new_weight[predicate] = weight

        getLogger("log").debug("Updated Lambda\t\t\t\t\t: " + str(new_weight))

        time_total = time() - time_start
        self.time_optimization += time_total
        getLogger("log").debug("Time - SGD\t\t\t\t\t\t: %.1fs" % time_total)

        return new_weight

    def learn_update_scores(self, hypothesis, new_weight):

        rule = hypothesis
        rule_count = len(hypothesis.to_clauses()) - 2
        while rule.previous is not None:
            rule.max_x = new_weight["p_" + str(rule_count)]
            if rule.max_x > 1 - self.tolerance:
                rule.set_rule_probability(None)
            else:
                rule.set_rule_probability(rule.max_x)
            rule_count -= 1
            rule = rule.previous

        return hypothesis

    def learn_prune_hypothesis(self, hypothesis):
        getLogger("log").info(
            "%-*s: %s"
            % (self.pad, "Semi - Final Hypothesis", str(hypothesis.to_clauses()))
        )
        # Edit the weights of the rules to 1 from 1-self.tolerance and remove those rules whose weights are <= self.tolerance
        rule = hypothesis
        previous_rule = rule
        prune_indicator = False
        while rule.previous is not None:
            prob = rule.get_rule_probability()
            if prob is None:
                prob = 1
            if prob >= 1 - 6 * self.tolerance:
                rule.set_rule_probability(None)
            elif prob <= 6 * self.tolerance:
                # No need to update weighted accuracy when the rule is dropped. The dropped rule was inconsequential.
                previous_rule.previous = rule.previous
                rule = rule.previous
                prune_indicator = True
                continue
            previous_rule = rule
            rule = rule.previous

        # Drop first rule if it's probability is insignificant
        prob = hypothesis.get_rule_probability()
        if prob is None:
            prob = 1
        if hypothesis.previous.previous is not None and prob <= 6 * self.tolerance:
            hypothesis = hypothesis.previous
            prune_indicator = True

        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Final Hypothesis", str(hypothesis.to_clauses()))
        )
        return hypothesis, prune_indicator

    def learn(self):
        self.learn_read_file()
        start_learn = time()

        # ------------------------------ Get Negative Examples using AMIE+ -------------------------------
        self.tsv_file = (
            self.input_file[: self.input_file.rfind(".")].replace(".", "_")
            + "_amie.tsv"
        )
        self.convert_problog_to_amie()
        self.amie_rule_list, self.coverage_list, self.std_confidence_list, self.pca_confidence_list = (
            self.get_amie_rules()
        )
        s = "================ Candidate Rules obtained from AMIE+ ================\n"
        for candidate, coverage, std_confidence, pca_confidence in zip(
            self.amie_rule_list,
            self.coverage_list,
            self.std_confidence_list,
            self.pca_confidence_list,
        ):
            s += (
                str(candidate)
                + "\t"
                + str(coverage)
                + "\t"
                + str(std_confidence)
                + "\t"
                + str(pca_confidence)
                + "\n"
            )
        s += "===================================================================="
        getLogger("log").debug(s)

        hypothesis = self.get_amie_hypothesis(self.amie_rule_list)
        self.rule_get_negative_examples(hypothesis)
        # ---------------------------------------- Start Learning ----------------------------------------

        k = 1
        for base in self.predicate_dict[self.target_predicate]:
            k = k * len(self.constant_dict[base])

        self.weights["p_0"] = self.regularize(
            float(self.cw_total[self.target_predicate]) / k, 1
        )
        for i, confidence in enumerate(self.std_confidence_list):
            self.weights["p_" + str(i + 1)] = self.regularize(float(confidence), 1)
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Self.weights", str(self.weights))
        )

        hypothesis.accuracy = 0
        hypothesis.scores = [1.0] * self.total_examples
        hypothesis.expression_list = [""] * self.total_examples
        hypothesis.replaceableQuery = ""

        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Hypothesis", str(hypothesis.to_clauses()))
        )

        if len(hypothesis.predicate_list) > 0:
            new_weight = self.learn_stochastic_gradient_descent(hypothesis)
            self.learn_update_scores(hypothesis, new_weight)
        else:
            new_weight = copy(self.weights)

        self.weights = new_weight

        hypothesis, prune_indicator = self.learn_prune_hypothesis(hypothesis)

        self.cursor.close()
        self.conn.close()

        self.time_learn = time() - start_learn

        return hypothesis

    def rule_intersect2_tables(
        self, main_table, main_var_list, new_table, new_var_list
    ):

        unified_table_name = "dummy" + str(self.dummy_count)
        self.dummy_count += 1

        unified_var_list = main_var_list

        if main_table != new_table:
            first_table_identifier = main_table
            second_table_identifier = new_table
        else:
            first_table_identifier = "table0"
            second_table_identifier = "table1"

        where_list = []
        select_list = []
        for i, var in enumerate(main_var_list):
            select_list.append(first_table_identifier + ".v" + str(i))
        for i, var in enumerate(new_var_list):
            if var not in main_var_list:
                unified_var_list.append(new_var_list[i])
                select_list.append(second_table_identifier + ".v" + str(i))
            else:
                where_list.append(
                    first_table_identifier
                    + ".v"
                    + str(main_var_list.index(var))
                    + " = "
                    + second_table_identifier
                    + ".v"
                    + str(i)
                )
        select_list = [item + " as v" + str(i) for i, item in enumerate(select_list)]

        select_string = ", ".join(select_list)
        where_string = " and ".join(where_list)

        if where_string == "":
            # Take Cross join of both tables
            self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
            sql_query = (
                "CREATE TABLE "
                + unified_table_name
                + " AS (select distinct "
                + select_string
                + " from "
                + main_table
                + " as "
                + first_table_identifier
                + " cross join "
                + new_table
                + " as "
                + second_table_identifier
                + ");"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)
        else:
            # Take Inner join with respect to where_string
            self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
            sql_query = (
                "CREATE TABLE "
                + unified_table_name
                + " AS (select distinct "
                + select_string
                + " from "
                + main_table
                + " as "
                + first_table_identifier
                + " inner join "
                + new_table
                + " as "
                + second_table_identifier
                + " on "
                + where_string
                + ");"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)

        return unified_table_name, unified_var_list

    def rule_unify_2_tables(self, first_table, second_table):
        unified_table_name = "dummy" + str(self.dummy_count)
        self.dummy_count += 1

        # Unify both tables
        self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
        sql_query = (
            "CREATE TABLE "
            + unified_table_name
            + " AS (select distinct "
            + first_table
            + ".v0 as v0, "
            + first_table
            + ".v1 as v1 from "
            + first_table
            + " union select distinct "
            + second_table
            + ".v0 as v0, "
            + second_table
            + ".v1 as v1 from "
            + second_table
            + ");"
        )
        getLogger("log").log(9, sql_query)
        self.cursor.execute(sql_query)

        return unified_table_name

    def rule_predict1rule(self, rule):
        # r(A,B):-r1(A,C),r2(B,C),r3(C,D),r4(E).
        # Assuming target arity = 2
        # varDict = {'A':[(r1,0)], 'B':[(r2,0)], 'C':[(r1,1),(r2,1),(r3,0)], 'D':[(r3,1)], 'E':[(r4,0)]}
        # var_list = [['A','C'],['B','C'],['C','D'],['E']]
        # table_list = ['r1','r2','r3',r4']
        # Get prediction set for this rule by running a nested inner join SQL query
        literal_list = rule.get_literals()[1:]

        var_list = []
        table_list = []
        for i, literal in enumerate(literal_list):
            table_list.append(literal.functor)
            # table_list.append(literal._Term__functor)
            arg_list = literal.args
            var_list.append([])
            for j, arg in enumerate(arg_list):
                variable = term2str(arg)
                var_list[i].append(variable)

        unified_var_set = set()
        for variables in var_list:
            unified_var_set = unified_var_set.union(set(variables))

        if "A" not in unified_var_set and "B" not in unified_var_set:
            unified_table_name = "dummy" + str(self.dummy_count)
            self.dummy_count += 1
            self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
            sql_query = (
                "CREATE TABLE "
                + unified_table_name
                + " AS (select distinct dummyA.v0 as v0, dummyB.v0 as v1 from dummyA cross join dummyB);"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)
            return unified_table_name

        new_table = table_list[0]
        unified_var_list = var_list[0]
        for (table, variables) in zip(table_list[1:], var_list[1:]):
            new_table, unified_var_list = self.rule_intersect2_tables(
                new_table, unified_var_list, table, variables
            )

        if "A" not in unified_var_set:
            unified_table_name = "dummy" + str(self.dummy_count)
            self.dummy_count += 1
            self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
            unified_var_list.append("A")
            sql_query = (
                "CREATE TABLE "
                + unified_table_name
                + " AS (select distinct dummyA.v0 as v0, "
                + new_table
                + ".v"
                + str(unified_var_list.index("B"))
                + " as v1 from "
                + new_table
                + " cross join dummyA);"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)
            return unified_table_name
        elif "B" not in unified_var_set:
            unified_table_name = "dummy" + str(self.dummy_count)
            self.dummy_count += 1
            self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
            unified_var_list.append("B")
            sql_query = (
                "CREATE TABLE "
                + unified_table_name
                + " AS (select distinct "
                + new_table
                + ".v"
                + str(unified_var_list.index("A"))
                + " as v0, dummyB.v0 as v1 from "
                + new_table
                + " cross join dummyB);"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)
            return unified_table_name
        else:
            # Prune new_table to keep only A and B columns
            unified_table_name = "dummy" + str(self.dummy_count)
            self.dummy_count += 1
            self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
            sql_query = (
                "CREATE TABLE "
                + unified_table_name
                + " AS (select distinct v"
                + str(unified_var_list.index("A"))
                + " as v0, v"
                + str(unified_var_list.index("B"))
                + " as v1 from "
                + new_table
                + ");"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)
            return unified_table_name

    def rule_predict_all_rules(self, rules):
        self.dummy_count = 0

        # Creating DummyA and DummyB
        for i in range(0, 2):
            sql_query = (
                "select distinct "
                + self.target_predicate
                + ".v"
                + str(i)
                + " as v0 from "
                + self.target_predicate
            )
            entity = self.predicate_dict[self.target_predicate][i]
            for pred in self.predicate_dict:
                if pred == self.target_predicate:
                    continue
                entity_list = self.predicate_dict[pred]
                for j, predEntity in enumerate(entity_list):
                    if predEntity == entity:
                        sql_query = (
                            sql_query
                            + " union select distinct "
                            + pred
                            + ".v"
                            + str(j)
                            + " as v0 from "
                            + pred
                        )

            self.cursor.execute("DROP TABLE IF EXISTS dummy" + chr(65 + i) + ";")
            sql_query = (
                "CREATE TABLE dummy"
                + chr(65 + i)
                + " AS (select distinct * from ("
                + sql_query
                + ") as a);"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)

        # negativeExamples = set()
        while len(rules.get_literals()) <= 1 or Term("fail") in rules.get_literals():
            rules = rules.previous

        if rules is None:
            empty_table = "dummy" + str(self.dummy_count)
            self.dummy_count += 1
            self.cursor.execute("DROP TABLE IF EXISTS " + empty_table + ";")
            sql_query = (
                "CREATE TABLE "
                + empty_table
                + " (v0 integer, v1 interger, p double precision);"
            )
            getLogger("log").log(9, sql_query)
            self.cursor.execute(sql_query)
            return empty_table

        table = self.rule_predict1rule(rules)
        if rules.previous is not None:
            rule = rules.previous
            while rule is not None:
                if (
                    len(rule.get_literals()) > 1
                    and Term("fail") not in rule.get_literals()
                ):
                    new_table = self.rule_predict1rule(rule)
                    table = self.rule_unify_2_tables(table, new_table)
                rule = rule.previous

        unified_table_name = "dummy" + str(self.dummy_count)
        self.dummy_count += 1
        self.cursor.execute("DROP TABLE IF EXISTS " + unified_table_name + ";")
        sql_query = (
            "CREATE TABLE "
            + unified_table_name
            + " AS (select distinct v0, v1 from "
            + table
            + ");"
        )
        getLogger("log").log(9, sql_query)
        self.cursor.execute(sql_query)

        return unified_table_name

    def rule_get_negative_examples(self, rules):
        start_negative = time()

        subject_constant_list = {
            v: k
            for k, v in self.constant_dict[
                self.predicate_dict[self.target_predicate][0]
            ].items()
        }
        object_constant_list = {
            v: k
            for k, v in self.constant_dict[
                self.predicate_dict[self.target_predicate][1]
            ].items()
        }
        universal_constant_list = {v: k for k, v in self.constant_id.items()}

        self.total_positive_examples = len(self._examples)
        getLogger("log").info(
            "%-*s: %d"
            % (self.pad, "Total positive examples (#P)", self.total_positive_examples)
        )

        # ------------------------------------ Get Closed World Negatives ------------------------------------
        table = self.rule_predict_all_rules(rules)
        self.cursor.execute("select count(*) from " + table + ";")
        total_predictions = str(self.cursor.fetchone()[0])
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Total CW Predictions", total_predictions)
        )

        cw_prediction = "dummy" + str(self.dummy_count)
        self.dummy_count += 1
        self.cursor.execute("DROP TABLE IF EXISTS " + cw_prediction + ";")
        sql_query = (
            "CREATE TABLE "
            + cw_prediction
            + " AS (select distinct "
            + table
            + ".v0, "
            + table
            + ".v1 from "
            + table
            + " where not exists (select 1 from "
            + self.target_predicate
            + " where "
            + self.target_predicate
            + ".v0 = "
            + table
            + ".v0 and "
            + self.target_predicate
            + ".v1 = "
            + table
            + ".v1));"
        )
        getLogger("log").log(9, sql_query)
        self.cursor.execute(sql_query)
        self.cursor.execute("select count(*) from " + cw_prediction + ";")
        total_predictions = str(self.cursor.fetchone()[0])
        getLogger("log").info(
            "%-*s: %s" % (self.pad, "Total CW Negative Predictions", total_predictions)
        )
        sql_query = (
            "select * from "
            + cw_prediction
            + " order by random() limit "
            + str(self.cw_negatives_factor * self.total_positive_examples * 2)
            + ";"
        )
        getLogger("log").log(9, sql_query)
        self.cursor.execute(sql_query)
        prediction_list = self.cursor.fetchall()

        cw_negative_examples = []
        counter = 0
        # random.shuffle(prediction_list)
        for (a, b) in prediction_list:
            if counter == self.cw_negatives_factor * self.total_positive_examples:
                break
            example = [universal_constant_list[a], universal_constant_list[b]]
            if example not in self.examples:
                cw_negative_examples.append(example)
                counter += 1

        self.cw_negatives = set(
            range(self.total_positive_examples, self.total_positive_examples + counter)
        )
        self.total_cw_negative_examples = len(cw_negative_examples)
        self.cw_negatives = set(
            range(
                self.total_positive_examples,
                self.total_positive_examples + self.total_cw_negative_examples,
            )
        )

        getLogger("log").info(
            "%-*s: %d"
            % (self.pad, "Total CW negative examples", self.total_cw_negative_examples)
        )

        self.cursor.execute("select count(*) from " + cw_prediction + ";")
        total_cw_negative_tuples = self.cursor.fetchone()[0]

        if self.total_cw_negative_examples != 0:
            self.cw_negative_weight = (
                float(total_cw_negative_tuples)
                * self.misclassification_cost
                / self.total_cw_negative_examples
            )
        else:
            self.cw_negative_weight = 1

        getLogger("log").log(
            9,
            "%-*s: %s" % (self.pad, "CW Negative Weight", str(self.cw_negative_weight)),
        )
        getLogger("log").log(
            9,
            "%-*s: %s"
            % (self.pad, "#CW Negative Examples", str(self.total_cw_negative_examples)),
        )

        # ------------------------------------- Get Open World Negatives --------------------------------------
        table = self.rule_unify_2_tables(table, self.target_predicate)
        self.cursor.execute("select count(*) from " + table + ";")
        total_cw_tuples = self.cursor.fetchone()[0]
        # total_cw_tuples contains both positives and negatives

        self.cursor.execute("select * from " + table + ";")
        total_cw_list = self.cursor.fetchall()

        number_of_subjects = len(subject_constant_list)
        number_of_objects = len(object_constant_list)

        ow_negative_examples = []
        sample = 0
        sample_cap = self.ow_negatives_factor * self.total_positive_examples
        iteration = 0
        iteration_cap = 2 * number_of_subjects * number_of_objects

        sub_list = list(subject_constant_list.keys())
        obj_list = list(object_constant_list.keys())
        while True:
            if sample == sample_cap or iteration == iteration_cap:
                break
            j = random.randint(0, number_of_subjects - 1)
            k = random.randint(0, number_of_objects - 1)
            example = [
                subject_constant_list[sub_list[j]],
                object_constant_list[obj_list[k]],
            ]
            if (j, k) not in total_cw_list:
                ow_negative_examples.append(example)
                sample += 1
            iteration += 1

        self.total_ow_negative_examples = len(ow_negative_examples)
        self.ow_negatives = set(
            range(
                self.total_positive_examples + self.total_cw_negative_examples,
                self.total_positive_examples
                + self.total_cw_negative_examples
                + self.total_ow_negative_examples,
            )
        )

        k = 1
        for base in self.predicate_dict[self.target_predicate]:
            k = k * len(self.constant_dict[base])

        total_ow_negative_examples = k - total_cw_tuples

        getLogger("log").info(
            "%-*s: %d"
            % (self.pad, "Total OW negative examples", total_ow_negative_examples)
        )

        if self.total_ow_negative_examples != 0:
            self.ow_negative_weight = (
                float(total_ow_negative_examples)
                * self.misclassification_cost
                / self.total_ow_negative_examples
            )
        else:
            self.ow_negative_weight = 1

        getLogger("log").log(
            9,
            "%-*s: %s" % (self.pad, "OW Negative Weight", str(self.ow_negative_weight)),
        )
        getLogger("log").log(
            9,
            "%-*s: %s"
            % (self.pad, "#OW Negative Examples", str(self.total_ow_negative_examples)),
        )

        self._scores_correct = (
            self._scores_correct
            + [0] * self.total_cw_negative_examples
            + [0] * self.total_ow_negative_examples
        )

        self._examples = self._examples + cw_negative_examples + ow_negative_examples

        self.total_examples = (
            self.total_positive_examples
            + self.total_cw_negative_examples
            + self.total_ow_negative_examples
        )
        self.total_weighted_examples = (
            self.total_positive_examples
            + self.cw_negative_weight * self.total_cw_negative_examples
            + self.ow_negative_weight * self.total_ow_negative_examples
        )
        self.query_ss = [""] * self.total_examples

        total_negative = time() - start_negative
        getLogger("log").log(
            9,
            "%-*s: %ss"
            % (self.pad, "Total time in getting negatives", str(total_negative)),
        )

        iteration = int(table[5:])
        while iteration != -1:
            self.cursor.execute("drop table dummy" + str(iteration) + ";")
            iteration -= 1

    def rule_get_conditional_probability(self, rule_index):

        # Numerator = |Prediction of Rule (intersection) Positive Examples|
        # Denominator = |Prediction of Rule|

        # table, varList = self.rulewisePredictions[self.selectedAmieRules[-1]]

        (headLiteral, amieLiteralList) = self.amie_rule_list[rule_index]
        rule = FOILRule(headLiteral)
        for literal in amieLiteralList:
            rule = rule & literal

        table = self.rule_predict1rule(rule)
        target_table = self.target_predicate

        joined_table, joined_var_list = self.rule_intersect2_tables(
            target_table, ["A", "B"], table, ["A", "B"]
        )

        self.cursor.execute("select count(*) from " + joined_table + ";")
        numerator = float(str(self.cursor.fetchone()[0]))

        self.cursor.execute("select count(*) from " + table + ";")
        denominator = float(str(self.cursor.fetchone()[0]))

        if denominator == 0:
            # Bogus Rule
            return 1 - self.tolerance
        else:
            prob = numerator / denominator
            getLogger("log").log(
                9,
                "%-*s: %s"
                % (
                    self.pad,
                    "# Predictions of Rule"
                    + str(rule_index)
                    + " intersected with examples",
                    str(numerator),
                ),
            )
            getLogger("log").log(
                9,
                "%-*s: %s"
                % (
                    self.pad,
                    "# Predictions of Rule" + str(rule_index),
                    str(denominator),
                ),
            )
            # return self.regularize(prob, 5)
            return prob

    def statistics(self):
        stat_list = []
        stat_list.append(("Get Expression calls", self.stats_getExpression))
        stat_list.append(("Read Time", str(round(self.time_read, 2)) + "s"))
        stat_list.append(
            ("Get Expression Time", str(round(self.time_getExpression, 2)) + "s")
        )
        stat_list.append(
            ("Optimization Time", str(round(self.time_optimization, 2)) + "s")
        )
        stat_list.append(("Learn time", str(round(self.time_learn, 2)) + "s"))
        return stat_list

    def print_rules(self, hypothesis):
        print_list = ["================ LEARNED RULES ================="]

        rule = hypothesis
        rules = rule.to_clauses()

        # First rule is failing rule: don't print it if there are other rules.
        if len(rules) > 1:
            for rule in rules[1:]:
                print_list.append(str(rule))
        else:
            print_list.append(str(rules[0]))

        for line in print_list:
            getLogger("log").info(line)
            print(line)


def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="Input File")
    parser.add_argument(
        "-l", "--length", dest="l", type=int, default=None, help="maximum rule length"
    )
    parser.add_argument(
        "-v",
        action="count",
        dest="verbosity_level",
        default=None,
        help="increase verbosity (repeat for more)",
    )
    parser.add_argument(
        "-t",
        "--target",
        type=str,
        help="specify predicate/arity to learn (overrides settings file)",
    )
    parser.add_argument("--log", help="write log to file", default=None)
    parser.add_argument(
        "-s",
        "--score",
        type=str,
        default="cross_entropy",
        help="specify global scoring function as either 'accuracy', 'squared_loss', or 'cross_entropy' (Default is 'cross_entropy')",
    )
    parser.add_argument(
        "-c",
        "--cost",
        type=float,
        default=1.0,
        help="Misclassification Cost for negative examples",
    )
    parser.add_argument(
        "--minpca",
        type=float,
        default=0.00001,
        help="Minimum PCA Confidence Threshold for Amie",
        dest="minpca",
    )
    parser.add_argument(
        "--minhc",
        type=float,
        default=0.00001,
        help="Minimum Standard Confidence Threshold for Amie",
        dest="minhc",
    )
    parser.add_argument(
        "-q",
        "--quotes",
        action="store_true",
        help="Input -q to denote an input file with facts enclosed in double quotes",
    )
    parser.add_argument(
        "-r",
        "--allow_recursion",
        action="store_true",
        help="Allow recursive rules to be learned",
    )
    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=10000,
        help="Number of iterations of SGD",
        dest="iterations",
    )
    parser.add_argument(
        "-a",
        "--max_amie_rules",
        type=int,
        default=None,
        help="Maximum number of candidate rules to be learned from AMIE",
        dest="max_amie_rules",
    )
    parser.add_argument(
        "-d",
        "--disable_typing",
        action="store_true",
        help="Input -d to ignore type constraints for learned rules",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001,
        help="Learning Rate for Rule Weights in SGD",
        dest="lr",
    )
    parser.add_argument(
        "--db_name",
        type=str,
        default="postgres",
        help="specify name of the database to be used",
    )
    parser.add_argument(
        "--db_user",
        type=str,
        default="postgres",
        help="specify username of the database",
    )
    parser.add_argument(
        "--db_pass",
        type=str,
        default="postgres",
        help="specify password of the database",
    )
    parser.add_argument(
        "--db_localhost",
        type=str,
        default="localhost",
        help="specify localhost of the database",
    )

    return parser


class ProbLogLogFormatter(logging.Formatter):
    def __init__(self):
        logging.Formatter.__init__(self)

    def format(self, message):
        msg = str(message.msg) % message.args
        lines = msg.split("\n")
        if message.levelno < 10:
            line_start = "[LVL%s] " % message.levelno
        else:
            line_start = "[%s] " % message.levelname
        return line_start + ("\n" + line_start).join(lines)


def init_logger(verbose=None, name="problog", out=None):
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
    formatter = ProbLogLogFormatter()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    if not verbose:
        logger.setLevel(logging.WARNING)
    elif verbose == 1:
        logger.setLevel(logging.INFO)
        logger.info("Output level\t\t\t\t\t\t: INFO")
    elif verbose == 2:
        logger.setLevel(logging.DEBUG)
        logger.debug("Output level\t\t\t\t\t: DEBUG")
    else:
        level = max(1, 12 - verbose)  # between 9 and 1
        logger.setLevel(level)
        logger.log(level, "Output level\t\t\t\t\t\t: %s" % level)
    return logger


def main(argv=sys.argv[1:]):
    args = argparser().parse_args(argv)

    if args.log is None:
        log_file = None
    else:
        log_file = open(args.log, "w")

    log = init_logger(verbose=args.verbosity_level, name="log", out=log_file)

    log.info("Arguments\t\t\t\t\t\t: %s" % " ".join(argv))

    time_start = time()
    learn = SafeLearner(args.file, **vars(args))
    hypothesis = learn.learn()
    time_total = time() - time_start

    log.info("\n==================== OUTPUT ====================")
    print("\n=================== SETTINGS ===================")
    log.info("\n=================== SETTINGS ===================")
    for kv in vars(args).items():
        print("%20s:\t%s" % kv)
        log.info("%20s:\t%s" % kv)

    learn.print_rules(hypothesis)

    print_list = ["================== STATISTICS =================="]
    for name, value in learn.statistics():
        print_list.append("%20s:\t%s" % (name, value))
    print_list.append("          Total time:\t%.4fs" % time_total)

    for line in print_list:
        log.info(line)
        print(line)

    if log_file:
        log_file.close()


if __name__ == "__main__":
    main()
