from __future__ import print_function
from problog.logic import Var, Term
from logging import getLogger
import time
import psycopg2
from math import exp
from eval import evaluate_expression
from getExpression import getExpression  # Get SQL Expression for UCQ


class KnownError(Exception):
    pass


class LearnEntail(object):
    def __init__(self, data, target=None, logger=None, **kwargs):

        if target is not None:
            try:
                t_func, t_arity = target.split("/")
                arguments = []
                i = 0
                while i < int(t_arity):
                    arguments.append(Var(chr(65 + i)))
                    i += 1
                target = Term(t_func, *arguments)
            except Exception:
                raise KnownError("Invalid target specification '%s'" % target)

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

    def get_canonical_form(self, query):
        # Eg: if query = 'author_0_all' then new_query = 'table0(A,B)'
        new_query = ""
        table_list = []
        variable_list = []
        variable_mapping = {}
        i = 0
        while i < len(query):
            start = i
            while query[i] != "(":
                i += 1
            table = query[start:i]
            actual_table = table.split("_")[0]
            arg_list = table.split("_")[1:]
            all_indices = []
            for j, arg in enumerate(arg_list):
                if arg == "all":
                    all_indices.append(j)

            if table not in table_list:
                table_list.append(table)
            new_query = new_query + "table" + str(table_list.index(table)) + "("
            i += 1
            arg_count = 0
            while query[i] != ")":
                if query[i] != ",":
                    if query[i] == "V":
                        j = 1
                        while query[i + j].isdigit():
                            j += 1
                        var = query[i : i + j]
                        i += j - 1
                    else:
                        var = query[i]
                    if var not in variable_list:  # Change
                        variable_list.append(var)

                    new_query = new_query + "V" + str(variable_list.index(var))
                    if "V" + str(variable_list.index(var)) not in variable_mapping:
                        if actual_table == "p":
                            variable_mapping["V" + str(variable_list.index(var))] = "p"
                        elif "all" not in arg_list:
                            variable_mapping[
                                "V" + str(variable_list.index(var))
                            ] = "all"
                        else:
                            variable_mapping[
                                "V" + str(variable_list.index(var))
                            ] = self.predicate_dict[actual_table][
                                all_indices[arg_count]
                            ]

                    arg_count += 1
                else:
                    new_query = new_query + ","
                i += 1

            new_query = new_query + ")"

            if i + 1 < len(query):
                i += 1

                if query[i] == "," and query[i - 1] == ")":
                    new_query = new_query + ","

                if i + 2 < len(query) and query[i : i + 3] == " v ":
                    new_query = new_query + " v "
                    i += 3
                    continue

            i += 1
        return new_query, table_list, variable_mapping

    def partition_ucq(self, query):
        conjunct_list = query.split(" v ")
        # new_conjunct_list = copy(conjunct_list)
        predicate_dict = {}
        id_list = []
        merge_list = []

        for conjunct in conjunct_list:
            # Get all literals of this conjunct into a Literal List
            i = 2
            literal_list = []
            start = 0
            while i < len(conjunct):
                if conjunct[i] == "," and conjunct[i - 1] == ")":
                    literal_list.append(conjunct[start:i])
                    start = i + 1
                elif conjunct[i] == ")" and i == len(conjunct) - 1:
                    literal_list.append(conjunct[start:i])
                i += 1

            # Assign an conjunct_id to this conjunct
            id_set = set()
            conjunct_id = None
            for literal in literal_list:
                predicate = literal.split("(")[0]
                if predicate not in predicate_dict:
                    if conjunct_id is None:
                        conjunct_id = len(predicate_dict)
                        predicate_dict[predicate] = len(predicate_dict)
                    else:
                        predicate_dict[predicate] = conjunct_id
                else:
                    if conjunct_id is None:
                        conjunct_id = predicate_dict[predicate]
                        id_set.add(conjunct_id)
                    else:
                        id_set.add(conjunct_id)
                        id_set.add(predicate_dict[predicate])
            id_list.append(conjunct_id)
            if len(id_set) > 1:
                merge_list.append(id_set)

        if len(merge_list) > 0:
            # Update all the ids in the IdList on the basis of MergeList
            min_list = []
            for id_set in merge_list:
                min_list.append(min(id_set))

            a = zip(min_list, merge_list)
            b = sorted(a, reverse=True)
            min_list, merge_list = zip(*b)

            for minId, id_set in zip(min_list, merge_list):
                for conjunct_id in id_set:
                    if conjunct_id != minId:
                        id_list = [minId if x == conjunct_id else x for x in id_list]

        # Make NewConjunctList on the basis of IdList
        new_conjunct_list = []
        new_conjunct_ids = []
        for conjunct_id, conjunct in zip(id_list, conjunct_list):
            if conjunct_id not in new_conjunct_ids:
                new_conjunct_list.append(conjunct)
                new_conjunct_ids.append(conjunct_id)
            else:
                new_conjunct_list[new_conjunct_ids.index(conjunct_id)] += (
                    " v " + conjunct
                )

        return new_conjunct_list

    def check_unsafe_rule(self, rule_query):
        if rule_query in ["", "true", "fail", "false"]:
            return False

        condition = False
        time_start = time.time()
        rule_sql_query = getExpression(rule_query)
        self.time_getExpression = self.time_getExpression + time.time() - time_start
        self.stats_getExpression += 1

        if rule_sql_query == "Query is unsafe":
            getLogger("log").log(9, "Rule unsafe\t\t\t\t\t\t:" + rule_query)
            condition = True

        return condition
