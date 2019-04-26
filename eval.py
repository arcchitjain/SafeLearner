from __future__ import print_function
from logging import getLogger
from math import exp, log


def getLogList(expression):
    i = 4
    log_location = []
    log_list = []
    round_counter = 0
    while i < len(expression):
        if expression[i - 3 : i] == "log" and round_counter == 0:
            i += 1
            start = i
            round_counter = 1
            while round_counter != 0 and i < len(expression):
                if expression[i] == "(":
                    round_counter += 1
                elif expression[i] == ")":
                    round_counter -= 1
                i += 1
            end = i - 1
            log_location.append((start - 4, end + 1))
            log_list.append(expression[start:end])
        i += 1
    return log_list, log_location


def evaluate_expression(expression):
    try:
        ans = eval(expression)
        return ans
        # print("correct answer")
    except:
        log_list, log_location = getLogList(expression)
        log_output = []
        for item in log_list:
            try:
                output = eval(item)
            except:
                getLogger("probfoil").warning("Exception occurred in log_output")
                getLogger("probfoil").warning("item\t\t\t\t:" + item)
                output = 0.0
            log_output.append(output)

        # At each log_location, replace the log with either the output or with -Inf
        start = 0
        approximate_expression = ""
        for i, (j, k) in enumerate(log_location):
            approximate_expression = approximate_expression + expression[start:j]
            if log_output[i] > 0:
                approximate_expression = (
                    approximate_expression + "log(" + str(log_output[i]) + ")"
                )
            else:
                approximate_expression = approximate_expression + "-float('inf')"
            start = k
        approximate_expression = approximate_expression + expression[start:]
        # approximate_expression = approximate_expression + expression[k:]
        try:
            ans = eval(approximate_expression)
            return ans
        except:
            getLogger("probfoil").warning(
                "Exception\t\t\t\t\t\t: %s" % approximate_expression
            )
            return None
