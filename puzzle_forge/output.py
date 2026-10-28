# -*- coding: utf-8 -*-
from z3 import *
from random import randint, uniform, sample, choice
import itertools
from utils import *
from collections.abc import Iterable
from functools import reduce
import re
import os
import sys
set_option(timeout=15000)
INDEX_PATTERN = re.compile(r'^__(\d+)__$')

# Custom exception classes for better error handling
class PuzzleGenerationError(Exception):
    pass

class NoSolutionError(PuzzleGenerationError):
    pass

class TooManySolutionsError(PuzzleGenerationError):
    pass

class AnswerAssertionError(PuzzleGenerationError):
    pass

class RandomGenerationError(PuzzleGenerationError):
    pass
config = {}
sys.path.append("")
from pf_skyscraper_puzzle_0 import visible_count
sys.path.append("")
from pf_skyscraper_puzzle_0 import visible_count_rev


n = randint(int(4), int(4))
config["n"] = n
rows = [f'r{i}' for i in range(n)]
config["rows"] = rows
cols = [f'c{i}' for i in range(n)]
config["cols"] = cols
r_ids = list(range(n))
config["r_ids"] = r_ids
c_ids = list(range(n))
config["c_ids"] = c_ids
top_clues = [3, 2, 3, 1]
config["top_clues"] = top_clues
bottom_clues = [1, 3, 2, 3]
config["bottom_clues"] = bottom_clues
left_clues = [3, 2, 2, 1]
config["left_clues"] = left_clues
right_clues = [1, 2, 2, 3]
config["right_clues"] = right_clues


cell = CustomSym("cell", {"rows": rows, "cols": cols}, None, "int", "第{int(_rows[1:])+1}行第{int(_cols[1:])+1}列的高度")





_conditions = []
conditions = ""
domain_1_to_n = ''
conditions += domain_1_to_n
_conditions.append(And([And(cell[(rows[r], cols[c])] >= 1, cell[(rows[r], cols[c])] <= n) for r in r_ids for c in c_ids]))


row_distinct = ''
conditions += row_distinct
_conditions.append(And([Distinct([cell[(rows[r], cols[c])] for c in c_ids]) for r in r_ids]))


col_distinct = ''
conditions += col_distinct
_conditions.append(And([Distinct([cell[(rows[r], cols[c])] for r in r_ids]) for c in c_ids]))


left_visibility = ''
conditions += left_visibility
_conditions.append(And([visible_count([cell[(rows[r], cols[c])] for c in c_ids]) == left_clues[r] for r in r_ids]))


right_visibility = ''
conditions += right_visibility
_conditions.append(And([visible_count_rev([cell[(rows[r], cols[c])] for c in c_ids]) == right_clues[r] for r in r_ids]))


top_visibility = ''
conditions += top_visibility
_conditions.append(And([visible_count([cell[(rows[r], cols[c])] for r in r_ids]) == top_clues[c] for c in c_ids]))


bottom_visibility = ''
conditions += bottom_visibility
_conditions.append(And([visible_count_rev([cell[(rows[r], cols[c])] for r in r_ids]) == bottom_clues[c] for c in c_ids]))




_solver = Solver()
for cond in _conditions:
    _solver.add(cond)
_solver_size = len(_solver.assertions())
_solutions = []
try:
    while _solver.check() == sat:
        model = _solver.model()  # 获取当前解
        _solutions.append(model)  # 保存解
        if(len(_solutions) > 1):
            raise TooManySolutionsError(f"Found {len(_solutions)} solutions, which exceeds the maximum allowed (1). This typically means the constraints are too loose. Please retry, use '-c' for continuous mode, or consider adding more specific constraints to reduce the solution space, or increase the max_solution limit if appropriate.")
        
        # 添加排除条件：排除当前解的所有变量赋值
        block = []
        for var in model:
            block.append(var() != model[var])  # 对每个变量添加反向约束
        _solver.add(Or(block))  # 要求至少有一个变量与当前解不同
except Exception as e:
    if isinstance(e, TooManySolutionsError):
        raise e
    else:
        raise RandomGenerationError(f"Z3 solver encountered an error during solution generation: {str(e)}. This might be due to timeout or resource constraints. Please retry, use '-c' for continuous mode, or try again or simplify the constraints.")

if len(_solutions) == 0:
    # Get more detailed information about why there's no solution
    _unsat_core = _solver.unsat_core() if hasattr(_solver, 'unsat_core') else []
    _core_info = f" Unsatisfiable core: {[str(c) for c in _unsat_core]}" if _unsat_core else ""
    raise NoSolutionError(f"Z3 solver could not find any solution that satisfies all the given constraints. This means the constraints are contradictory or too restrictive.{_core_info} Please retry, use '-c' for continuous mode, or review your puzzle specification and ensure the constraints are consistent and achievable.")
print("solution number:", len(_solutions)) 
queries = ''
ans = []
config['_queries'] = {}

_ans = [[get_value(_solutions[0], cell[(rows[r], cols[c])]) for c in c_ids] for r in r_ids]
try:
    assert(len(_solutions) == 1)
except AssertionError as e:
    raise AnswerAssertionError(f"Answer assertion failed for query 'q1': {str(e) if str(e) else 'Assertion condition not met'}. The generated answer '{_ans}' does not satisfy the assertion 'len(_solutions) == 1'. This indicates that the constraints or answer formula may be inconsistent. Please retry, use '-c' for continuous mode, or review and revise the query specification.")
except Exception as e:
    raise AnswerAssertionError(f"Answer assertion evaluation failed for query 'q1': {str(e)}. There may be an error in the assertion formula 'len(_solutions) == 1' or the answer formula '[[get_value(_solutions[0], cell[(rows[r], cols[c])]) for c in c_ids] for r in r_ids]'. Please retry, use '-c' for continuous mode, or check the syntax and logic in your specification.")
q1 = CustomCond(desc=f"请解出所有格子的高度，并用Python二维列表（list of lists）输出。" + '\n')
queries += "1. " + q1.desc
ans.append(str(str(_ans)))
ans = '===='.join([str(v) for v in ans])


problem = f"""在这个 {n}×{n} 的摩天楼谜题中，每个格子需填入 1 到 {n} 的数字，代表摩天楼高度。每行每列的数字不能重复。
上边提示(top)={top_clues}，下边提示(bottom)={bottom_clues}，
左边提示(left)={left_clues}，右边提示(right)={right_clues}。
{q1}"""
print(problem)
print('answer: ', ans)
