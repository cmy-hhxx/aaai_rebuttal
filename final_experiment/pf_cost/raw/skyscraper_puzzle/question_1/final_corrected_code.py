# pf_skyscraper_puzzle_0.py
from z3 import If, Sum

def visible_count(seq):
    """
    从左到右计算可见楼数（Z3 友好版本）。
    seq: List[z3.ArithRef]
    return: z3.ArithRef
    """
    max_h = 0
    terms = []
    for x in seq:
        seen = If(x > max_h, 1, 0)
        terms.append(seen)
        max_h = If(x > max_h, x, max_h)
    return Sum(terms)

def visible_count_rev(seq):
    """反向视野（从右到左/从下到上）"""
    return visible_count(list(reversed(seq)))