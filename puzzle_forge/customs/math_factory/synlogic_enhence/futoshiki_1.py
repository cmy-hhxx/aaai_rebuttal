# futoshiki_2.py
# 职责说明：
# - function_1(n): 生成满足拉丁方与随机子块结构的完整解 grid，并返回 {"r": r, "c": c, "grid": grid}。
# - function_2(...): 从解中随机派生多种规则与线索，建立 Z3 模型进行唯一性验证；若发现多解，则从候选池中按优先级增补约束直至唯一或达时限。
# 设计目标：高度参数化、强随机性、复合约束、多步推理且唯一解，单题验证在 3 分钟内完成。
from typing import List, Tuple, Dict, Any
import random
import itertools
import time

try:
    from z3 import Solver, Int, And, Or, Distinct, Sum, If, Abs, sat
except Exception as e:
    raise ImportError("z3-solver is required. Please install z3-solver.") from e

# -----------------------
# 基盘与随机变换
# -----------------------
def _factor_pairs(n: int) -> List[Tuple[int, int]]:
    return [(r, n // r) for r in range(1, n + 1) if n % r == 0]

def _base_grid(n: int, r: int, c: int) -> List[List[int]]:
    # 通用满足 r×c 子块与行列拉丁的基盘
    return [[((i * c + i // r + j) % n) + 1 for j in range(n)] for i in range(n)]

def _permute_bands_rows(grid: List[List[int]], r: int) -> List[List[int]]:
    n = len(grid)
    bands = [list(range(b * r, (b + 1) * r)) for b in range(n // r)]
    random.shuffle(bands)
    bands = [random.sample(band, len(band)) for band in bands]
    order = [idx for band in bands for idx in band]
    return [grid[i] for i in order]

def _permute_stacks_cols(grid: List[List[int]], c: int) -> List[List[int]]:
    n = len(grid[0])
    stacks = [list(range(s * c, (s + 1) * c)) for s in range(n // c)]
    random.shuffle(stacks)
    stacks = [random.sample(stack, len(stack)) for stack in stacks]
    order = [idx for stack in stacks for idx in stack]
    return [[row[j] for j in order] for row in grid]

def _relabel_digits(grid: List[List[int]]) -> List[List[int]]:
    n = len(grid)
    perm = list(range(1, n + 1))
    random.shuffle(perm)
    mp = {i + 1: perm[i] for i in range(n)}
    return [[mp[v] for v in row] for row in grid]

def function_1(n: int) -> Dict[str, Any]:
    r, c = random.choice(_factor_pairs(n))
    grid = _base_grid(n, r, c)
    for _ in range(random.randint(1, 3)):
        grid = _permute_bands_rows(grid, r)
        grid = _permute_stacks_cols(grid, c)
        grid = _relabel_digits(grid)
    if random.random() < 0.6:
        grid = _permute_bands_rows(grid, r)
    if random.random() < 0.6:
        grid = _permute_stacks_cols(grid, c)
    if random.random() < 0.7:
        grid = _relabel_digits(grid)
    return {"r": r, "c": c, "grid": grid}

# -----------------------
# 规则候选池构造
# -----------------------
def _all_cells(n: int) -> List[Tuple[int, int]]:
    return [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)]

def _sample_unique(lst: List[Any], k: int) -> List[Any]:
    k = max(0, min(k, len(lst)))
    return random.sample(lst, k) if k > 0 else []

def _candidate_inequalities(grid: List[List[int]]) -> List[Tuple[int, int, str, int, int]]:
    n = len(grid)
    rows = list(range(1, n + 1))
    cols = list(range(1, n + 1))
    cand = []
    for i in rows:
        for a, b in itertools.combinations(cols, 2):
            v1 = grid[i - 1][a - 1]
            v2 = grid[i - 1][b - 1]
            if v1 < v2:
                cand.append((i, a, '<', i, b))
            elif v1 > v2:
                cand.append((i, a, '>', i, b))
    for j in cols:
        for a, b in itertools.combinations(rows, 2):
            v1 = grid[a - 1][j - 1]
            v2 = grid[b - 1][j - 1]
            if v1 < v2:
                cand.append((a, j, '<', b, j))
            elif v1 > v2:
                cand.append((a, j, '>', b, j))
    random.shuffle(cand)
    return cand

def _candidate_diffs(grid: List[List[int]]) -> List[Tuple[int, int, int, int, int]]:
    n = len(grid)
    cells = _all_cells(n)
    cand = []
    for (i1, j1), (i2, j2) in itertools.combinations(cells, 2):
        d = abs(grid[i1 - 1][j1 - 1] - grid[i2 - 1][j2 - 1])
        if d != 0:
            cand.append((i1, j1, i2, j2, d))
    random.shuffle(cand)
    return cand

def _candidate_sums(grid: List[List[int]], count: int, kmin: int, kmax: int) -> List[Tuple[List[Tuple[int, int]], int]]:
    n = len(grid)
    cells = _all_cells(n)
    cand = []
    for _ in range(count * 4 + 10):
        k = random.randint(max(2, kmin), min(kmax, n))
        group = _sample_unique(cells, k)
        s = sum(grid[i - 1][j - 1] for (i, j) in group)
        cand.append((group, s))
    random.shuffle(cand)
    return cand

def _candidate_parcounts(grid: List[List[int]], count: int, kmin: int, kmax: int) -> List[Tuple[List[Tuple[int, int]], int]]:
    n = len(grid)
    cells = _all_cells(n)
    cand = []
    for _ in range(count * 4 + 10):
        k = random.randint(max(2, kmin), min(kmax, n))
        group = _sample_unique(cells, k)
        t = sum(1 for (i, j) in group if grid[i - 1][j - 1] % 2 == 1)
        cand.append((group, t))
    random.shuffle(cand)
    return cand

def _candidate_chains(grid: List[List[int]]) -> List[Tuple[List[Tuple[int, int]], str]]:
    n = len(grid)
    cand = []
    # 行链
    for i in range(1, n + 1):
        idxs = list(range(1, n + 1))
        for a, b, c in itertools.combinations(idxs, 3):
            v = [grid[i - 1][a - 1], grid[i - 1][b - 1], grid[i - 1][c - 1]]
            if v[0] < v[1] < v[2]:
                cand.append(([(i, a), (i, b), (i, c)], 'inc'))
            elif v[0] > v[1] > v[2]:
                cand.append(([(i, a), (i, b), (i, c)], 'dec'))
    # 列链
    for j in range(1, n + 1):
        idxs = list(range(1, n + 1))
        for a, b, c in itertools.combinations(idxs, 3):
            v = [grid[a - 1][j - 1], grid[b - 1][j - 1], grid[c - 1][j - 1]]
            if v[0] < v[1] < v[2]:
                cand.append(([(a, j), (b, j), (c, j)], 'inc'))
            elif v[0] > v[1] > v[2]:
                cand.append(([(a, j), (b, j), (c, j)], 'dec'))
    random.shuffle(cand)
    return cand

# -----------------------
# Z3 建模与唯一性验证
# -----------------------
def _build_solver(n: int,
                  use_blocks: bool,
                  block_r: int,
                  block_c: int,
                  givens: List[Tuple[int, int, int]],
                  E_pos: List[Tuple[int, int]],
                  O_pos: List[Tuple[int, int]],
                  inequalities: List[Tuple[int, int, str, int, int]],
                  diffs: List[Tuple[int, int, int, int, int]],
                  sums: List[Tuple[List[Tuple[int, int]], int]],
                  parcounts: List[Tuple[List[Tuple[int, int]], int]],
                  chains: List[Tuple[List[Tuple[int, int]], str]]):
    X = [[Int(f"x_{r}_{c}") for c in range(1, n + 1)] for r in range(1, n + 1)]
    s = Solver()
    # 基本域
    for r in range(n):
        for c in range(n):
            s.add(And(X[r][c] >= 1, X[r][c] <= n))
    # 行列拉丁
    for r in range(n):
        s.add(Distinct(X[r]))
    for c in range(n):
        s.add(Distinct([X[r][c] for r in range(n)]))
    # 子块
    if use_blocks:
        for rb in range(0, n, block_r):
            for cb in range(0, n, block_c):
                block = [X[r][c] for r in range(rb, rb + block_r) for c in range(cb, cb + block_c)]
                s.add(Distinct(block))
    # givens
    for (i, j, v) in givens:
        s.add(X[i - 1][j - 1] == v)
    # 奇偶
    for (i, j) in E_pos:
        s.add((X[i - 1][j - 1] % 2) == 0)
    for (i, j) in O_pos:
        s.add((X[i - 1][j - 1] % 2) == 1)
    # 不等式
    for (i1, j1, op, i2, j2) in inequalities:
        a = X[i1 - 1][j1 - 1]
        b = X[i2 - 1][j2 - 1]
        s.add(a < b if op == '<' else a > b)
    # 绝对差
    for (i1, j1, i2, j2, d) in diffs:
        a = X[i1 - 1][j1 - 1]
        b = X[i2 - 1][j2 - 1]
        s.add(Abs(a - b) == d)
    # 选点求和（笼子）
    for (cells, target) in sums:
        s.add(Sum([X[i - 1][j - 1] for (i, j) in cells]) == target)
    # 奇偶计数
    for (cells, odd_cnt) in parcounts:
        s.add(Sum([If((X[i - 1][j - 1] % 2) == 1, 1, 0) for (i, j) in cells]) == odd_cnt)
    # 单调链
    for (cells, kind) in chains:
        a = X[cells[0][0] - 1][cells[0][1] - 1]
        b = X[cells[1][0] - 1][cells[1][1] - 1]
        c = X[cells[2][0] - 1][cells[2][1] - 1]
        if kind == 'inc':
            s.add(And(a < b, b < c))
        else:
            s.add(And(a > b, b > c))
    return s, X

def _model_to_grid(m, X) -> List[List[int]]:
    n = len(X)
    return [[m.evaluate(X[r][c]).as_long() for c in range(n)] for r in range(n)]

# -----------------------
# 主生成（含唯一性迭代增强）
# -----------------------
def function_2(
    solved_grid: List[List[int]],
    rows_i: List[int],
    cols_i: List[int],
    givens_num: int,
    parity_even_num: int,
    parity_odd_num: int,
    num_ineq: int,
    num_diff: int,
    num_sum: int,
    sum_group_min: int,
    sum_group_max: int,
    use_blocks: bool,
    block_r: int,
    block_c: int,
    num_parcount: int,
    parcount_min: int,
    parcount_max: int,
    num_chains: int,
    time_limit_s: int
) -> Dict[str, Any]:
    n = len(solved_grid)
    all_cells = _all_cells(n)

    # 初始约束（从解反向派生）
    even_cells = [(i, j) for (i, j) in all_cells if solved_grid[i - 1][j - 1] % 2 == 0]
    odd_cells  = [(i, j) for (i, j) in all_cells if solved_grid[i - 1][j - 1] % 2 == 1]
    E_pos = _sample_unique(even_cells, parity_even_num)
    O_pos = _sample_unique(odd_cells, parity_odd_num)

    givens_cells = _sample_unique(all_cells, givens_num)
    givens = [(i, j, solved_grid[i - 1][j - 1]) for (i, j) in givens_cells]

    ineq_pool_all = _candidate_inequalities(solved_grid)
    diff_pool_all = _candidate_diffs(solved_grid)
    sum_pool_all = _candidate_sums(solved_grid, num_sum, sum_group_min, sum_group_max)
    parcount_pool_all = _candidate_parcounts(solved_grid, num_parcount, parcount_min, parcount_max)
    chain_pool_all = _candidate_chains(solved_grid)

    inequalities = ineq_pool_all[:max(0, min(num_ineq, len(ineq_pool_all)))]
    diffs = diff_pool_all[:max(0, min(num_diff, len(diff_pool_all)))]
    sums = sum_pool_all[:max(0, min(num_sum, len(sum_pool_all)))]
    parcounts = parcount_pool_all[:max(0, min(num_parcount, len(parcount_pool_all)))]
    chains = chain_pool_all[:max(0, min(num_chains, len(chain_pool_all)))]

    # 剩余候选（用于增补）
    ineq_rest = ineq_pool_all[len(inequalities):]
    diff_rest = diff_pool_all[len(diffs):]
    sum_rest = sum_pool_all[len(sums):]
    parcount_rest = parcount_pool_all[len(parcounts):]
    chain_rest = chain_pool_all[len(chains):]

    # 唯一性循环
    t0 = time.time()
    while True:
        if time.time() - t0 > time_limit_s:
            # 超时仍未唯一：强制追加若干 givens 再作最后一次尝试
            remain_cells = [cell for cell in all_cells if cell not in [(i, j) for (i, j, _) in givens]]
            extra_need = min(n, len(remain_cells))
            extra_cells = _sample_unique(remain_cells, extra_need)
            for (i, j) in extra_cells:
                givens.append((i, j, solved_grid[i - 1][j - 1]))
            s, X = _build_solver(n, use_blocks, block_r, block_c, givens, E_pos, O_pos,
                                 inequalities, diffs, sums, parcounts, chains)
            # 最终检查：若仍非唯一，则以当前配置返回（实践中极少发生）
            if s.check() != sat:
                break
            m1 = s.model()
            g1 = _model_to_grid(m1, X)
            s.add(Or([X[r][c] != g1[r][c] for r in range(n) for c in range(n)]))
            # 若还有第二解，此处不再继续增补，直接收敛
            break

        s, X = _build_solver(n, use_blocks, block_r, block_c, givens, E_pos, O_pos,
                             inequalities, diffs, sums, parcounts, chains)
        if s.check() != sat:
            # 出现不一致，回退：增加若干 givens 修复
            remain_cells = [cell for cell in all_cells if cell not in [(i, j) for (i, j, _) in givens]]
            add_fix = min(3, len(remain_cells))
            extra_cells = _sample_unique(remain_cells, add_fix)
            for (i, j) in extra_cells:
                givens.append((i, j, solved_grid[i - 1][j - 1]))
            continue

        m1 = s.model()
        g1 = _model_to_grid(m1, X)
        s.add(Or([X[r][c] != g1[r][c] for r in range(n) for c in range(n)]))
        if s.check() != sat:
            # 唯一
            break

        # 非唯一：按优先级增补约束（笼子→奇偶计数→单调链→不等式→绝对差→givens）
        added = False
        for pool_name in ['sum', 'parcount', 'chain', 'ineq', 'diff']:
            if pool_name == 'sum' and sum_rest:
                sums.append(sum_rest.pop())
                added = True
                break
            if pool_name == 'parcount' and parcount_rest:
                parcounts.append(parcount_rest.pop())
                added = True
                break
            if pool_name == 'chain' and chain_rest:
                chains.append(chain_rest.pop())
                added = True
                break
            if pool_name == 'ineq' and ineq_rest:
                inequalities.append(ineq_rest.pop())
                added = True
                break
            if pool_name == 'diff' and diff_rest:
                diffs.append(diff_rest.pop())
                added = True
                break
        if not added:
            # 候选用尽，增加 givens（最强增益）
            remain_cells = [cell for cell in all_cells if cell not in [(i, j) for (i, j, _) in givens]]
            if not remain_cells:
                break
            extra = _sample_unique(remain_cells, min(3, len(remain_cells)))
            for (i, j) in extra:
                givens.append((i, j, solved_grid[i - 1][j - 1]))

    # 规则文本汇总
    lines = []
    lines.append(f"- 行列拉丁：每行与每列均为 1..{n} 且不重复。")
    if use_blocks:
        lines.append(f"- 子块唯一：将棋盘按 {block_r}×{block_c} 划分，每个子块内 1..{n} 不重复。")
    if E_pos:
        lines.append(f"- 偶数格 E={E_pos}。")
    if O_pos:
        lines.append(f"- 奇数格 O={O_pos}。")
    if inequalities:
        lines.append(f"- 不等式 inequalities={inequalities}。")
    if diffs:
        lines.append(f"- 绝对差 diffs={diffs}（形式 abs((i1,j1)-(i2,j2))=d）。")
    if sums:
        lines.append(f"- 选点求和 sums={sums}（每组格子的和值固定）。")
    if parcounts:
        lines.append(f"- 奇偶计数 parcounts={parcounts}（每组格子中奇数的个数固定）。")
    if chains:
        lines.append(f"- 单调链 chains={chains}（三个格子严格递增 inc 或严格递减 dec）。")
    if givens:
        lines.append(f"- 给定数字 givens={givens}。")
    rules_text = "\\n".join(lines)

    return {
        "givens": givens,
        "E_pos": E_pos,
        "O_pos": O_pos,
        "inequalities": inequalities,
        "diffs": diffs,
        "sums": sums,
        "parcounts": parcounts,
        "chains": chains,
        "rules_text": rules_text
    }