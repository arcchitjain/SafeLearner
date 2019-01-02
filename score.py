"""
Module name
"""

from __future__ import print_function

import math

def rates(rule):
    tp = 0.0
    fp = 0.0
    p = 0.0
    m = 0
    
    for c, pr in zip(rule.correct, rule.scores):
        tp += min(c, pr)
        fp += max(0, pr - c)
        p += c
        m += 1
    n = m - p
    return tp, fp, n - fp, p - tp


def m_estimate(rule, m=1):
    """Compute the m-estimate of the rule.

    :param rule: rule to score
    :param m: m parameter for m-estimate
    :return: value of m-estimate
    """
    tp, fp, tn, fn = rates(rule)
    p = tp + fn
    n = tn + fp
    return (tp + (m * p / (p + n))) / (tp + fp + m)


def m_estimate_future(rule, m=1):
    """Compute the m-estimate for the optimal extension of this rule.

    The optimal extension has the same TP-rate and zero FP-rate.

    :param rule: rule to score
    :param m: m parameter for m-estimate
    :return: value of m-estimate assuming an optimal extension
    """

    tp, fp, tn, fn = rates(rule)
    p = tp + fn
    n = tn + fp
    fp = 0.0
    return (tp + (m * p / (p + n))) / (tp + fp + m)


def m_estimate_relative(rule, m=1):
    """Compute the m-estimate of the rule relative to the previous ruleset.

    :param rule: rule to score
    :param m: m parameter for m-estimate
    :return: value of m-estimate
    """

    if rule.previous:
        tp_p, fp_p, tn_p, fn_p = rates(rule.previous)
    else:
        tp_p, fp_p, tn_p, fn_p = 0.0, 0.0, 0.0, 0.0   # last two are irrelevant

    tp, fp, tn, fn = rates(rule)
    p = tp + fn - tp_p
    n = tn + fp - fp_p
    return (tp - tp_p + (m * p / (p + n))) / (tp + fp - tp_p - fp_p + m)


def m_estimate_future_relative(rule, m=1):
    """Compute the m-estimate for the optimal extension of this rule relative to the previous ruleset.

    The optimal extension has the same TP-rate and zero FP-rate.

    :param rule: rule to score
    :param m: m parameter for m-estimate
    :return: value of m-estimate assuming an optimal extension
    """

    if rule.previous:
        tp_p, fp_p, tn_p, fn_p = rates(rule.previous)
    else:
        tp_p, fp_p, tn_p, fn_p = 0.0, 0.0, 0.0, 0.0  # last two are irrelevant

    tp, fp, tn, fn = rates(rule)
    p = tp + fn - tp_p
    n = tn + fp - fp_p
    fp = fp_p
    return (tp - tp_p + (m * p / (p + n))) / (tp + fp - tp_p - fp_p + m)


def accuracy(rule):
    tp, fp, tn, fn = rates(rule)
    return (tp + tn) / (tp + fp + tn + fn)


def precision(rule):
    tp, fp, tn, fn = rates(rule)
    if tp + fp == 0:
        return 0.0
    else:
        return tp / (tp + fp)


def recall(rule):
    tp, fp, tn, fn = rates(rule)
    return tp / (tp + fn)


def chi2_cdf(x):
    return math.erf(math.sqrt(x / 2))


def pvalue2chisquare(s, low=0.0, high=100.0, precision=1e-8):
    """Helper function for transforming significance p-value into ChiSquare decision value."""
    v = (low + high) / 2
    r = chi2_cdf(v)
    if -precision < r - s < precision:
        return v
    elif r > s:
        return pvalue2chisquare(s, low, v)
    else:
        return pvalue2chisquare(s, v, high)


def significance(rule, calc_max=False):
    """Compute the significance of a rule (chi-square distributed)."""

    c_tp, c_fp, c_tn, c_fn = rates(rule)

    pos = c_tp + c_fn
    neg = c_fp + c_tn

    if rule.previous:
        p_tp, p_fp, p_tn, p_fn = rates(rule.previous)
    else:
        p_tp, p_fp, p_tn, p_fn = 0.0, 0.0, neg, pos

    if calc_max:
        s_tp_max = c_tp     # TODO
        s_tp = s_tp_max - p_tp
        s_fp = 0
    else:
        s_tp = c_tp - p_tp
        s_fp = c_fp - p_fp

    s_pos = c_tp + c_fn
    s_neg = c_fp + c_tn
    s_all = s_pos + s_neg

    c = s_tp + s_fp     # max: c = s_tp
    if c == 0:
        return 0

    f_pos_c = s_tp / c     # max: f_pos_c = 1
    f_neg_c = 1 - f_pos_c  # max: f_neg_c == 0

    f_pos = s_pos / s_all
    f_neg = s_neg / s_all

    pos_log = math.log(f_pos_c / f_pos) if f_pos_c > 0 else 0  # max: pos_log = -log(sP / sM)
    neg_log = math.log(f_neg_c / f_neg) if f_neg_c > 0 else 0  # max: neg_log = 0

    l = 2 * c * (f_pos_c * pos_log + f_neg_c * neg_log)  # max: 2 * sTP * -log(sP/sM)

    return l
