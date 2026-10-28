# kukurasu_0.py
# 逆向生成高质量 Kakurasu 谜题实例，支持权重模式与提示注入以保证唯一性

from typing import List, Tuple, Dict, Any
import random

try:
    from z3 import Solver, Bool, Sum, If, And, Or, sat
except Exception:
    # 在某些环境中可能未预装z3，给出简要提示（PuzzleClone环境通常有z3）
    pass

def gen_col_weights(n: int, mode: str) -> List[int]:
    """
    生成列权重列表（用于行加权和）。
    mode:
      - 'linear': 1..n
      - 'odd': 1,3,5,... (长度为n)
      - 'shift': 2..n+1
    """
    if mode == 'odd':
        return [2*i + 1 for i in range(n)]
    elif mode == 'shift':
        return [i + 2 for i in range(n)]
    else:
        # default linear
        return [i + 1 for i in range(n)]

def gen_row_weights(n: int, mode: str) -> List[int]:
    """
    生成行权重列表（用于列加权和）。
    与列权重同模式，以保持对称性与多样性。
    """
    # 可以与列权重相同或不同，这里同模式，便于玩家理解。
    if mode == 'odd':
        return [2*i + 1 for i in range(n)]
    elif mode == 'shift':
        return [i + 2 for i in range(n)]
    else:
        return [i + 1 for i in range(n)]

def _count_solutions(n: int,
                     col_weights: List[int],
                     row_weights: List[int],
                     row_sums: List[int],
                     col_sums: List[int],
                     hints: List[Tuple[int, int, int]],
                     limit: int = 2) -> int:
    """
    用Z3统计满足行/列加权和与提示的解的数量（计数至limit即可）。
    返回：解数（>= limit 时提前停止）
    """
    s = Solver()
    x = [[Bool(f"x_{i}_{j}") for j in range(n)] for i in range(n)]

    # 行约束
    for i in range(n):
        s.add(Sum([If(x[i][j], col_weights[j], 0) for j in range(n)]) == row_sums[i])
    # 列约束
    for j in range(n):
        s.add(Sum([If(x[i][j], row_weights[i], 0) for i in range(n)]) == col_sums[j])
    # 提示约束
    for (i, j, v) in hints:
        s.add(x[i][j] if v == 1 else (x[i][j] == False))

    count = 0
    while s.check() == sat:
        m = s.model()
        count += 1
        if count >= limit:
            return count
        # block the current model
        s.add(Or(*[ (x[i][j] != m.eval(x[i][j])) for i in range(n) for j in range(n) ]))
    return count

def _compute_sums(sol: List[List[int]],
                  col_weights: List[int],
                  row_weights: List[int]) -> Tuple[List[int], List[int]]:
    """
    给定布尔解（0/1），计算行和与列和。
    """
    n = len(sol)
    row_sums = []
    for i in range(n):
        row_sums.append(sum(col_weights[j] for j in range(n) if sol[i][j] == 1))
    col_sums = []
    for j in range(n):
        col_sums.append(sum(row_weights[i] for i in range(n) if sol[i][j] == 1))
    return row_sums, col_sums

def build_instance(n: int,
                   col_weights: List[int],
                   row_weights: List[int],
                   hint_budget: int,
                   max_attempts: int = 50) -> Dict[str, Any]:
    """
    逆向构造：
      1) 随机生成一个0/1网格（控制密度避免退化）
      2) 计算行/列和
      3) 检查是否唯一；若多解则逐步加入提示（固定部分格为1/X），直到唯一或达到提示预算
      4) 若失败，则重新尝试不同的随机解，最多max_attempts次

    返回：
      {
        'sol_grid': [['1'/'X', ...], ...],
        'row_sums': [...],
        'col_sums': [...],
        'hints': [(i, j, v), ...]
      }
    """
    rnd = random.Random()
    attempts = 0

    while attempts < max_attempts:
        attempts += 1

        # 随机解网格（控制密度，避免全0/全1等极端）
        p = rnd.uniform(0.25, 0.6)  # 1的概率
        sol = [[1 if rnd.random() < p else 0 for _ in range(n)] for __ in range(n)]

        # 简单过滤：非全零/非全一，且行和/列和皆非全0，避免无趣题面
        if all(sum(row) == 0 for row in sol) or all(sum(row) == n for row in sol):
            continue

        row_sums, col_sums = _compute_sums(sol, col_weights, row_weights)

        # 行和/列和不可全零（否则多解且没意思）
        if sum(1 for v in row_sums if v == 0) > n - 1 and sum(1 for v in col_sums if v == 0) > n - 1:
            continue

        # 初步唯一性检查（无提示）
        hints: List[Tuple[int, int, int]] = []
        sol_count = _count_solutions(n, col_weights, row_weights, row_sums, col_sums, hints, limit=2)
        if sol_count == 1:
            # 唯一，无需提示
            sol_grid = [['1' if sol[i][j] == 1 else 'X' for j in range(n)] for i in range(n)]
            return {
                'sol_grid': sol_grid,
                'row_sums': row_sums,
                'col_sums': col_sums,
                'hints': hints
            }

        # 增量提示：随机选择若干格，固定为解中的值，直到唯一或达到预算
        positions = [(i, j) for i in range(n) for j in range(n)]
        rnd.shuffle(positions)
        for k, (i, j) in enumerate(positions[:hint_budget]):
            hints.append((i, j, sol[i][j]))
            sol_count = _count_solutions(n, col_weights, row_weights, row_sums, col_sums, hints, limit=2)
            if sol_count == 1:
                sol_grid = [['1' if sol[i][j] == 1 else 'X' for j in range(n)] for i in range(n)]
                return {
                    'sol_grid': sol_grid,
                    'row_sums': row_sums,
                    'col_sums': col_sums,
                    'hints': hints
                }

        # 若提示预算内仍非唯一，则重试新的随机解
        continue

    # 若多次尝试仍失败，退回到线性权重+稠密提示以强制唯一
    # 构造简单唯一场景：对角线为1，其余为0
    sol = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    row_sums, col_sums = _compute_sums(sol, col_weights, row_weights)
    hints = [(i, i, 1) for i in range(n)]  # 全对角提示
    sol_grid = [['1' if sol[i][j] == 1 else 'X' for j in range(n)] for i in range(n)]
    return {
        'sol_grid': sol_grid,
        'row_sums': row_sums,
        'col_sums': col_sums,
        'hints': hints
    }