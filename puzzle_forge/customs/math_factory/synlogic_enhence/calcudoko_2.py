# calcudoko_0.py
# 自定义算子与实例生成器：用于在 YAML 中构建乘积、两格减法/除法约束、Distinct 约束
# 以及根据 N 随机生成 Calcudoku 实例（拉丁方答案 + 连通笼划分 + 运算与目标 + 随机全局规则）
from functools import reduce
import random

try:
    from z3 import And, Or, Distinct, IntVal, Sum
except Exception:
    # 运行时由 PuzzleClone 注入 z3；此处兜底以免静态检查报错
    And = Or = Distinct = IntVal = None
    def Sum(x): return None

def prod(lst):
    """
    返回列表中所有 Z3 整数表达式的乘积。
    空列表返回 1（IntVal(1)）。
    """
    if lst is None:
        raise ValueError("prod expects a list")
    if len(lst) == 0:
        return IntVal(1)
    return reduce(lambda a, b: a * b, lst)

def sub2(a, b, target):
    """
    两格减法约束：绝对差等于 target。
    即 Or(a - b == target, b - a == target)。
    """
    return Or(a - b == target, b - a == target)

def div2(a, b, target):
    """
    两格“整除商”约束的无除法实现：
    乘法等价形式避免 Z3 的 div0/mod0：
    Or(a == b * target, b == a * target)。
    """
    return Or(a == b * target, b == a * target)

def all_diff(lst):
    """
    Distinct 约束的封装：列表中的所有表达式两两不相等。
    """
    return Distinct(*lst)

def sandwich_row_clause(grid_s, row, cols, tgt, N):
    """
    行 Sandwich 约束子句：
    存在一对不同列 (c1, c2)，使得 grid[row, c1] == 1 且 grid[row, c2] == N，
    并且两者之间（不含端点）的格子数值之和等于 tgt。
    返回 Or( ... ) 公式；若无任意对，返回 True。
    """
    terms = []
    for i, c1 in enumerate(cols):
        for j, c2 in enumerate(cols):
            if c1 == c2:
                continue
            lo = i + 1 if i < j else j + 1
            hi = j if i < j else i
            between_cells = [grid_s[(row, cols[k])] for k in range(lo, hi)]
            s_between = Sum(between_cells) if between_cells else IntVal(0)
            terms.append(And(grid_s[(row, c1)] == 1, grid_s[(row, c2)] == N, s_between == tgt))
    return Or(terms) if terms else And(IntVal(1) == IntVal(1))

def sandwich_col_clause(grid_s, col, rows, tgt, N):
    """
    列 Sandwich 约束子句：
    存在一对不同行 (r1, r2)，使得 grid[r1, col] == 1 且 grid[r2, col] == N，
    并且两者之间（不含端点）的格子数值之和等于 tgt。
    返回 Or( ... ) 公式；若无任意对，返回 True。
    """
    terms = []
    for i, r1 in enumerate(rows):
        for j, r2 in enumerate(rows):
            if r1 == r2:
                continue
            lo = i + 1 if i < j else j + 1
            hi = j if i < j else i
            between_cells = [grid_s[(rows[k], col)] for k in range(lo, hi)]
            s_between = Sum(between_cells) if between_cells else IntVal(0)
            terms.append(And(grid_s[(r1, col)] == 1, grid_s[(r2, col)] == N, s_between == tgt))
    return Or(terms) if terms else And(IntVal(1) == IntVal(1))

# ------------------ 内部生成工具 ------------------

def _make_base_latin(n):
    # 基础拉丁方：L[i][j] = (i + j) % n + 1
    return [[(i + j) % n + 1 for j in range(n)] for i in range(n)]

def _permute_latin(grid):
    n = len(grid)
    rows = list(range(n))
    cols = list(range(n))
    syms = list(range(1, n + 1))
    random.shuffle(rows)
    random.shuffle(cols)
    random.shuffle(syms)
    # 行列置换
    g2 = [[grid[rows[i]][cols[j]] for j in range(n)] for i in range(n)]
    # 符号重标
    m = {k: syms[k - 1] for k in range(1, n + 1)}
    return [[m[g2[i][j]] for j in range(n)] for i in range(n)]

def _neighbors(r, c, n):
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n:
            yield nr, nc

def _partition_cages(solution, max_size=4):
    """
    按连通性随机划分笼。
    - 每个笼连通
    - 笼内数在候选解中互不相同（与题目“笼内互异”一致）
    - 期望笼大小 2..max_size；少量单格笼允许但受控（概率低 + 设定上限）
    返回：cells_list（每个笼的[(r,c), ...]，0-based）
    """
    n = len(solution)
    unused = [[True]*n for _ in range(n)]
    cells_list = []
    remain = n * n
    singles_limit = max(1, n // 2)
    singles_count = 0

    while remain > 0:
        candidates = [(i,j) for i in range(n) for j in range(n) if unused[i][j]]
        sr, sc = random.choice(candidates)

        # 以低概率允许单格笼，且受上限限制
        allow_single = (singles_count < singles_limit) and (random.random() < 0.15 or remain == 1)
        if allow_single:
            want = 1
        else:
            want = random.randint(2, max_size)

        cage = [(sr, sc)]
        unused[sr][sc] = False
        remain -= 1
        used_vals = {solution[sr][sc]}
        frontier = set(_neighbors(sr, sc, n))
        while len(cage) < want and frontier:
            pr, pc = random.choice(list(frontier))
            frontier.remove((pr, pc))
            if not unused[pr][pc]:
                continue
            v = solution[pr][pc]
            if v in used_vals:
                for nr, nc in _neighbors(pr, pc, n):
                    if unused[nr][nc]:
                        frontier.add((nr, nc))
                continue
            cage.append((pr, pc))
            unused[pr][pc] = False
            remain -= 1
            used_vals.add(v)
            for nr, nc in _neighbors(pr, pc, n):
                if unused[nr][nc]:
                    frontier.add((nr, nc))
        if len(cage) == 1:
            singles_count += 1
        cells_list.append(cage)
    return cells_list

def _choose_op_and_target(values):
    """
    根据笼内值（按候选解给定）选择运算与目标。
    - size==1: eq
    - size==2: 在 diff/div/sum/prod 中按权重选择；div 需可整除且商>1，否则回退
    - size>=3: 在 sum/prod 中按权重选择
    返回 (op, target)
    """
    k = len(values)
    if k == 1:
        return 'eq', values[0]
    if k == 2:
        a, b = values
        A, B = (a, b) if a >= b else (b, a)
        pool = ['diff']*3 + ['sum']*2 + ['prod']*2 + ['div']*2
        random.shuffle(pool)
        for op in pool:
            if op == 'div':
                if B != 0 and A % B == 0 and (A // B) > 1:
                    return 'div', A // B
                else:
                    continue
            elif op == 'diff':
                return 'diff', abs(a - b)
            elif op == 'sum':
                return 'sum', a + b
            elif op == 'prod':
                return 'prod', a * b
        return 'diff', abs(a - b)
    else:
        s = sum(values)
        p = 1
        for v in values:
            p *= v
        if random.random() < 0.7:
            return 'sum', s
        else:
            return 'prod', p

def _knight_pairs(n):
    """
    生成所有 0-based 棋盘上的马步相距格对列表 [((r1,c1),(r2,c2)), ...]，每对仅出现一次。
    """
    pairs = set()
    moves = [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]
    for r in range(n):
        for c in range(n):
            for dr, dc in moves:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    a = (r, c)
                    b = (nr, nc)
                    if a < b:
                        pairs.add((a, b))
                    else:
                        pairs.add((b, a))
    return sorted(pairs)

def _make_thermometers(sol, max_count):
    """
    基于解 sol 随机生成若干 Thermometer 路径（严格递增）。
    采用贪心增长：从随机起点出发，每步选择一个值更大的相邻格，长度 3..N。
    保证路径唯一（去重）。
    """
    n = len(sol)
    thermos = []
    seen = set()  # 存储标准化路径元组
    trials = 0
    while len(thermos) < max_count and trials < n * n * 3:
        trials += 1
        sr, sc = random.randrange(n), random.randrange(n)
        cur = [(sr, sc)]
        visited = {(sr, sc)}
        while True:
            nbrs = [p for p in _neighbors(cur[-1][0], cur[-1][1], n)
                    if p not in visited and sol[p[0]][p[1]] > sol[cur[-1][0]][cur[-1][1]]]
            if not nbrs:
                break
            pr, pc = random.choice(nbrs)
            cur.append((pr, pc))
            visited.add((pr, pc))
            # 随机停止
            if len(cur) >= 3 and (len(cur) >= n or random.random() < 0.3):
                break
        if len(cur) >= 3:
            norm = tuple(cur)
            if norm in seen:
                continue
            seen.add(norm)
            # 转 1-based 字符串
            path = [(str(r+1), str(c+1)) for r, c in cur]
            thermos.append(path)
    return thermos

def _border_cells(n):
    """
    返回 0-based 外环（边框）格坐标列表，按顺序去重。
    """
    cells = []
    for j in range(n):
        cells.append((0, j))
    for j in range(n):
        cells.append((n-1, j))
    for i in range(1, n-1):
        cells.append((i, 0))
    for i in range(1, n-1):
        cells.append((i, n-1))
    # 去重保持顺序
    out = []
    seen = set()
    for rc in cells:
        if rc not in seen:
            seen.add(rc)
            out.append(rc)
    return out

def _pick_blocks(sol, max_blocks=2):
    """
    随机选择若干 2×2 连续区块并计算目标和。
    返回两个列表：
      block_cells: [ [(r,c),(r,c),(r,c),(r,c)], ... ] 1-based 字符串坐标
      block_targets: [int, ...]
    保证不越界；允许区块重叠以增加难度。
    """
    n = len(sol)
    count = random.randint(0, min(max_blocks, max(0, (n-1)*(n-1)//2)))
    offs = [(0,0),(0,1),(1,0),(1,1)]
    block_cells = []
    block_targets = []
    for _ in range(count):
        r = random.randint(0, n-2)
        c = random.randint(0, n-2)
        cells = [(r+dr, c+dc) for dr, dc in offs]
        tgt = sum(sol[rr][cc] for rr, cc in cells)
        block_cells.append([(str(rr+1), str(cc+1)) for rr, cc in cells])
        block_targets.append(int(tgt))
    return block_cells, block_targets

def _sandwich_rows(sol):
    """
    随机选取若干行，计算该行中 1 与 N 之间（不含端点）的和。
    返回列表 [(row_str, target), ...]。
    """
    n = len(sol)
    rows = [str(i+1) for i in range(n)]
    count = random.randint(0, max(1, n // 2))
    idxs = random.sample(range(n), count) if count > 0 else []
    out = []
    for r in idxs:
        row = sol[r]
        c1 = row.index(1)
        cN = row.index(n)
        start = min(c1, cN) + 1
        end = max(c1, cN)
        tgt = sum(row[start:end]) if start < end else 0
        out.append((rows[r], int(tgt)))
    return out

def _sandwich_cols(sol):
    """
    随机选取若干列，计算该列中 1 与 N 之间（不含端点）的和。
    返回列表 [(col_str, target), ...]。
    """
    n = len(sol)
    cols = [str(i+1) for i in range(n)]
    count = random.randint(0, max(1, n // 2))
    idxs = random.sample(range(n), count) if count > 0 else []
    out = []
    for c in idxs:
        col_vals = [sol[r][c] for r in range(n)]
        r1 = col_vals.index(1)
        rN = col_vals.index(n)
        start = min(r1, rN) + 1
        end = max(r1, rN)
        tgt = sum(col_vals[start:end]) if start < end else 0
        out.append((cols[c], int(tgt)))
    return out

def format_rules(extras, N):
    """
    将全局规则（extras）渲染为题面用的单行字符串。
    仅输出规则具体清单；若无则返回 'none.'。
    使用方括号/圆括号避免 YAML desc 的花括号冲突。
    """
    parts = []
    md = extras.get('main_diag_sum', None)
    ad = extras.get('anti_diag_sum', None)
    fx = extras.get('fixed_cells', [])
    th = extras.get('thermos', [])
    ak = extras.get('anti_knight', False)
    bs = extras.get('border_sum', None)
    bc = extras.get('block_cells', [])
    bt = extras.get('block_targets', [])
    sr = extras.get('sandwich_rows', [])
    sc = extras.get('sandwich_cols', [])

    if md is not None:
        parts.append(f'Main diagonal sum: {md}')
    if ad is not None:
        parts.append(f'Anti-diagonal sum: {ad}')
    if fx:
        parts.append('Fixed cells: [' + ', '.join([f'(r{rc[0]},c{rc[1]})={v}' for (rc, v) in fx]) + ']')
    if th:
        parts.append('Thermometers: [' + '; '.join(['->'.join([f'(r{r},c{c})' for (r,c) in path]) for path in th]) + ']')
    if ak:
        parts.append('Anti-knight: cells at a knight-move must be different')
    if bs is not None:
        parts.append(f'Border ring sum: {bs}')
    if bc:
        txt = []
        for i, cells in enumerate(bc):
            txt.append('[' + ', '.join([f'(r{r},c{c})' for (r,c) in cells]) + f']={bt[i]}')
        parts.append('2x2 block sums: [' + '; '.join(txt) + ']')
    if sr:
        parts.append('Sandwich rows: [' + ', '.join([f'r{r}->{t}' for (r, t) in sr]) + ']')
    if sc:
        parts.append('Sandwich cols: [' + ', '.join([f'c{c}->{t}' for (c, t) in sc]) + ']')

    if not parts:
        return 'none.'
    return '; '.join(parts) + '.'

def format_cages(cells, ops, tgts):
    """
    以更友好的方式渲染笼列表：'[(rX,cY), (rX,cY)] -> op tgt'，多个笼以逗号分隔。
    """
    items = []
    for i in range(len(tgts)):
        coords = ', '.join([f'(r{r},c{c})' for (r, c) in cells[i]])
        items.append(f'[{coords}] -> {ops[i]} {tgts[i]}')
    return ', '.join(items)

def _pick_extras(sol):
    """
    随机抽取全局约束（适度控制密度）：
    - 主对角线和/副对角线和（可选）
    - 少量“给定数”固定格（0..n//3）
    - Thermometers（少量，0..n//2 条，路径唯一）
    - Anti-knight（若 sol 已满足，则以一定概率启用）
    - 外环和（随机启用，概率 0.4）
    - 2×2 区块和（最多 2 个）
    - Sandwich 和（若干行/列）
    返回 dict
    """
    n = len(sol)
    rows = [str(i) for i in range(1, n+1)]
    cols = [str(i) for i in range(1, n+1)]

    # 对角线和（可选，降低概率）
    main_diag_sum = sum(sol[i][i] for i in range(n)) if random.random() < 0.4 else None
    anti_diag_sum = sum(sol[i][n - 1 - i] for i in range(n)) if random.random() < 0.25 else None

    # 给定数（固定格，上限约束）
    max_fixed = max(0, n // 3)
    k_fixed = random.randint(0, max_fixed)
    all_cells = [(i, j) for i in range(n) for j in range(n)]
    fixed_idx = random.sample(all_cells, k_fixed) if k_fixed > 0 else []
    fixed_cells = [((rows[i], cols[j]), int(sol[i][j])) for (i, j) in fixed_idx]

    # Thermometers（数量适度控制，路径唯一）
    thermos = _make_thermometers(sol, max_count=random.randint(0, max(0, n // 2)))

    # Anti-knight（需要 sol 已满足才启用）
    kpairs = _knight_pairs(n)
    sol_ok_knight = all(sol[r1][c1] != sol[r2][c2] for ((r1, c1), (r2, c2)) in kpairs)
    anti_knight = sol_ok_knight and (random.random() < 0.5)
    # 1-based 字符串坐标形式
    knight_pairs_str = [((str(r1+1), str(c1+1)), (str(r2+1), str(c2+1))) for ((r1,c1),(r2,c2)) in kpairs]

    # 外环和（随机启用，降低概率）
    border_sum = None
    if random.random() < 0.4:
        bcs = _border_cells(n)
        border_sum = sum(sol[r][c] for (r,c) in bcs)

    # 2×2 区块和（最多 2）
    block_cells, block_targets = _pick_blocks(sol, max_blocks=2)

    # Sandwich 和
    sandwich_rows = _sandwich_rows(sol)
    sandwich_cols = _sandwich_cols(sol)

    return {
        'main_diag_sum': main_diag_sum,
        'anti_diag_sum': anti_diag_sum,
        'fixed_cells': fixed_cells,
        'thermos': thermos,
        'anti_knight': anti_knight,
        'knight_pairs': knight_pairs_str,
        'border_sum': border_sum,
        'block_cells': block_cells,
        'block_targets': block_targets,
        'sandwich_rows': sandwich_rows,
        'sandwich_cols': sandwich_cols
    }

def gen_calcudoku_instance(N):
    """
    生成一个 Calcudoku 实例：
    - 随机拉丁方（唯一解候选）
    - 随机连通笼划分（笼内值互异，单格笼受控）
    - 为每个笼指定运算与目标（两格 diff/div 特殊；div 需可整除且商>1）
    - 随机选择全局约束（对角线和，少量固定格，thermo，anti-knight，border，2x2区块，sandwich）
    返回 dict
    """
    if N < 3:
        raise ValueError("N must be >= 3")
    base = _make_base_latin(N)
    sol = _permute_latin(base)

    # 随机控制笼最大尺寸（2..4）
    max_size = random.choice([2, 3, 4])
    cages = _partition_cages(sol, max_size=max_size)

    cells_out = []
    ops_out = []
    targets_out = []

    for cage in cages:
        vals = [sol[r][c] for r, c in cage]
        op, tgt = _choose_op_and_target(vals)
        # 输出坐标转为字符串（1-based）
        c_str = [(str(r+1), str(c+1)) for r, c in cage]
        cells_out.append(c_str)
        ops_out.append(op)
        targets_out.append(int(tgt))

    extras = _pick_extras(sol)
    rules_text = format_rules(extras, N)

    return {
        'cells': cells_out,
        'ops': ops_out,
        'targets': targets_out,
        'solution': sol,
        'extras': extras,
        'rules_text': rules_text
    }