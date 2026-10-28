# calcudoko_0.py
import random
from functools import reduce
import operator
# 引入Z3算子：在自定义运算符中构造Z3表达式
from z3 import And, Or, Sum

def gen_latin(N):
    """
    生成一个 NxN 的随机拉丁方：每行每列均为1..N的排列。
    基于循环拉丁方并随机打乱行列，保证合法与多样。
    返回：grid_sol（二维列表，1-based数值）。
    """
    base = [[(i + j) % N + 1 for j in range(N)] for i in range(N)]
    row_perm = list(range(N))
    col_perm = list(range(N))
    random.shuffle(row_perm)
    random.shuffle(col_perm)
    grid = [[base[row_perm[i]][col_perm[j]] for j in range(N)] for i in range(N)]
    return grid

def _neighbors(r, c, N):
    """四邻接（上、下、左、右），r,c为1-based。"""
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        nr, nc = r + dr, c + dc
        if 1 <= nr <= N and 1 <= nc <= N:
            yield (nr, nc)

def make_cages(grid, N, max_cage_size=4):
    """
    基于给定的正确解grid，随机生成覆盖整个网格的笼划分与目标。
    每个笼包含若干相邻格（1~max_cage_size），运算∈ {'+','*','-','÷','='}。
      - 大小1：'='
      - 大小2：可用 '-','÷','+','*'（除法须整除）
      - 大小≥3：仅用 '+' 或 '*'
    返回：cages 列表，每项为 {"cells":[(r,c),...], "op":op, "target":int}
    """
    unassigned = {(r, c) for r in range(1, N+1) for c in range(1, N+1)}
    cages = []

    while unassigned:
        r0, c0 = random.choice(list(unassigned))
        cage_cells = [(r0, c0)]
        unassigned.remove((r0, c0))
        size_target = random.randint(1, max_cage_size)

        # 保持连通地增长笼
        while len(cage_cells) < size_target and unassigned:
            candidates = set()
            for (r, c) in cage_cells:
                for (nr, nc) in _neighbors(r, c, N):
                    if (nr, nc) in unassigned:
                        candidates.add((nr, nc))
            if not candidates:
                break
            nr, nc = random.choice(list(candidates))
            cage_cells.append((nr, nc))
            unassigned.remove((nr, nc))

        vals = [grid[r-1][c-1] for (r, c) in cage_cells]
        if len(cage_cells) == 1:
            op = '='
            target = vals[0]
        elif len(cage_cells) == 2:
            a, b = vals[0], vals[1]
            # 随机择优选择四种之一；优先考虑'-'与'÷'（更具约束性），但保持随机性
            ops = ['-','÷','+','*']
            random.shuffle(ops)
            chosen = None
            for cand in ops:
                if cand == '÷':
                    big, small = (a, b) if a >= b else (b, a)
                    if small != 0 and big % small == 0:
                        chosen = '÷'
                        target = big // small
                        break
                elif cand == '-':
                    chosen = '-'
                    target = abs(a - b)
                    break
                elif cand == '+':
                    chosen = '+'
                    target = a + b
                    break
                elif cand == '*':
                    chosen = '*'
                    target = a * b
                    break
            if chosen is None:
                chosen = '+'
                target = a + b
            op = chosen
        else:
            op = random.choice(['+','*'])
            target = sum(vals) if op == '+' else reduce(operator.mul, vals, 1)

        cages.append({"cells": cage_cells, "op": op, "target": int(target)})

    return cages

def build_cage_constraint(x, cages):
    """
    将cages转换为Z3约束表达式 And([...])。
    解释：
      '+'：Sum(vars) == target
      '*'：乘积 == target
      '-'：二元差值：Or(a - b == target, b - a == target)
      '÷'：二元整除：Or(a == target*b, b == target*a)
      '='：单元格值 == target
    """
    exprs = []
    for cage in cages:
        cells = cage["cells"]
        op = cage["op"]
        target = cage["target"]
        vars_in_cage = [x[('r' + str(r), 'c' + str(c))] for (r, c) in cells]

        if op == '+':
            exprs.append(Sum(vars_in_cage) == target)
        elif op == '*':
            prod_expr = reduce(operator.mul, vars_in_cage, 1)
            exprs.append(prod_expr == target)
        elif op == '-':
            assert len(vars_in_cage) == 2, "Subtraction cage must have exactly 2 cells"
            a, b = vars_in_cage
            exprs.append(Or(a - b == target, b - a == target))
        elif op == '÷':
            assert len(vars_in_cage) == 2, "Division cage must have exactly 2 cells"
            a, b = vars_in_cage
            exprs.append(Or(a == target * b, b == target * a))
        elif op == '=':
            assert len(vars_in_cage) == 1, "Equality cage must have exactly 1 cell"
            exprs.append(vars_in_cage[0] == target)
        else:
            raise ValueError(f"Unknown cage op: {op}")

    return And(exprs)

def cages_to_desc(cages):
    """
    将cages转换为题面描述字符串，格式统一：
      ((r1,c1),(r2,c2),...):target<op>
    其中 op ∈ {+,*, -, ÷, =}
    """
    lines = []
    for cage in cages:
        cells_txt = ",".join([f"({r},{c})" for (r, c) in cage["cells"]])
        op = cage["op"]
        target = cage["target"]
        if op == '=':
            suffix = f"{target}="
        elif op == '+':
            suffix = f"{target}+"
        elif op == '*':
            suffix = f"{target}*"
        elif op == '-':
            suffix = f"{target}-"
        elif op == '÷':
            suffix = f"{target}÷"
        else:
            suffix = f"{target}?"
        lines.append(f"(({cells_txt})):{suffix}")
    return "\n" + "\n".join(lines)