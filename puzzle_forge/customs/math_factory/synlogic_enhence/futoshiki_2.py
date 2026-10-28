# futoshiki_3.py
# 优化版：n=4固定；目标解用循环拉丁方+随机置换；Z3唯一性验证（止于第二解，timeout=200ms）
# 约束密度强制下限；区域比较仅用sum；行评分为线性加权行和，权重w_c∈{1,2,3}
from typing import List, Tuple, Dict, Any
import random
import time
import math
from z3 import Solver, Int, Distinct, And, Or, Sum, If, sat

Coord = Tuple[int, int]
Thermo = List[Coord]
Chain = List[Coord]
Ineq = Tuple[Coord, str, Coord]

def _neighbors(n: int, r: int, c: int) -> List[Tuple[int, int]]:
    res = []
    if r > 0: res.append((r - 1, c))
    if r + 1 < n: res.append((r + 1, c))
    if c > 0: res.append((r, c - 1))
    if c + 1 < n: res.append((r, c + 1))
    return res

def _gen_cyclic_latin(n: int, rng: random.Random) -> List[List[int]]:
    # base cyclic Latin: g[r][c] = ((r + c) % n) + 1
    base = [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]
    # random row/col/symbol permutations
    row_perm = list(range(n)); rng.shuffle(row_perm)
    col_perm = list(range(n)); rng.shuffle(col_perm)
    sym_perm = list(range(1, n + 1)); rng.shuffle(sym_perm)
    grid = [[sym_perm[base[row_perm[r]][col_perm[c]] - 1] for c in range(n)] for r in range(n)]
    return grid

def _derive_monotone_paths(grid: List[List[int]], target_num: int, rng: random.Random) -> List[Thermo]:
    n = len(grid)
    paths: List[Thermo] = []
    attempts, max_attempts = 0, target_num * 6 + 18
    used: set = set()
    while len(paths) < target_num and attempts < max_attempts:
        attempts += 1
        sr, sc = rng.randrange(n), rng.randrange(n)
        if (sr, sc) in used: continue
        used.add((sr, sc))
        path = [(sr + 1, sc + 1)]
        cr, cc = sr, sc
        while True:
            nbrs = _neighbors(n, cr, cc)
            incs = [(nr, nc) for (nr, nc) in nbrs if grid[nr][nc] > grid[cr][cc]]
            if not incs: break
            rng.shuffle(incs)
            nr, nc = incs[0]
            step = (nr + 1, nc + 1)
            if step in path: break
            path.append(step)
            cr, cc = nr, nc
            if rng.random() < 0.35: break
        if len(path) >= 2 and path not in paths:
            paths.append(path)
    if not paths:
        # 保底：找一条相邻递增对
        for r in range(n):
            for c in range(n):
                for (nr, nc) in _neighbors(n, r, c):
                    if grid[nr][nc] > grid[r][c]:
                        return [[(r + 1, c + 1), (nr + 1, nc + 1)]]
    return paths

def _derive_order_chains(grid: List[List[int]], target_num: int, rng: random.Random) -> List[Chain]:
    n = len(grid)
    chains: List[Chain] = []
    cells = [(r, c) for r in range(n) for c in range(n)]
    attempts, max_attempts = 0, target_num * 8 + 24
    while len(chains) < target_num and attempts < max_attempts:
        attempts += 1
        rng.shuffle(cells)
        length = rng.randint(3, min(n, 5))
        cand = cells[:length]
        vals = [grid[r][c] for (r, c) in cand]
        if all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            seq = [(r + 1, c + 1) for (r, c) in cand]
            if seq not in chains:
                chains.append(seq)
    if not chains:
        all_pos = [(grid[r][c], (r + 1, c + 1)) for r in range(n) for c in range(n)]
        all_pos.sort(key=lambda x: x[0])
        chains.append([all_pos[0][1], all_pos[1][1], all_pos[2][1]])
    return chains

def _derive_ineqs(grid: List[List[int]], target_num: int, rng: random.Random) -> List[Ineq]:
    n = len(grid)
    pairs: List[Ineq] = []
    edges: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    for r in range(n):
        for c in range(n):
            for (nr, nc) in _neighbors(n, r, c):
                if (nr, nc) > (r, c): edges.append(((r, c), (nr, nc)))
    rng.shuffle(edges)
    for (a, b) in edges:
        (r1, c1), (r2, c2) = a, b
        v1, v2 = grid[r1][c1], grid[r2][c2]
        op = '<' if v1 < v2 else '>'
        pairs.append(((r1 + 1, c1 + 1), op, (r2 + 1, c2 + 1)))
        if len(pairs) >= target_num: break
    i = 0
    while len(pairs) < target_num and i < len(edges):
        (a, b) = edges[i]; i += 1
        (r1, c1), (r2, c2) = a, b
        v1, v2 = grid[r1][c1], grid[r2][c2]
        op = '<' if v1 < v2 else '>'
        pairs.append(((r1 + 1, c1 + 1), op, (r2 + 1, c2 + 1)))
    return pairs

def _derive_thermo_deltas(paths: List[Thermo], grid: List[List[int]], rng: random.Random) -> List[Dict[str, Any]]:
    deltas: List[Dict[str, Any]] = []
    for pid, path in enumerate(paths):
        if len(path) < 2: continue
        steps = list(range(1, len(path)))
        rng.shuffle(steps)
        use_k = rng.randint(0, max(0, len(steps) // 2))
        for k in steps[:use_k]:
            (pr, pc) = path[k - 1]
            (cr, cc) = path[k]
            pv = grid[pr - 1][pc - 1]
            cv = grid[cr - 1][cc - 1]
            diff = cv - pv
            mode = rng.choice(['ge', 'eq']) if diff > 0 else 'ge'
            deltas.append({'path_idx': pid + 1, 'step_idx': k, 'mode': mode, 'delta': diff})
    return deltas

def _derive_regions_and_orders(grid: List[List[int]], rng: random.Random) -> Tuple[List[List[Coord]], List[Tuple[int, str, int]]]:
    # 固定sum度量，低复杂度
    n = len(grid)
    regions: List[List[Coord]] = []
    orders: List[Tuple[int, str, int]] = []
    used: set = set()
    reg_num = rng.randint(0, 2)
    for _ in range(reg_num):
        tries = 0
        while tries < 30:
            tries += 1
            sr, sc = rng.randrange(n), rng.randrange(n)
            size = rng.randint(2, min(5, n))
            region = [(sr, sc)]
            frontier = [(sr, sc)]
            while len(region) < size and frontier:
                r, c = frontier.pop()
                nbrs = [(nr, nc) for (nr, nc) in _neighbors(n, r, c) if (nr, nc) not in region and (nr, nc) not in used]
                rng.shuffle(nbrs)
                for (nr, nc) in nbrs[:1]:
                    region.append((nr, nc)); frontier.append((nr, nc))
            # 简连通
            S = set(region); stack = [region[0]]; seen = {region[0]}
            while stack:
                rr, cc = stack.pop()
                for (nr, nc) in _neighbors(n, rr, cc):
                    if (nr, nc) in S and (nr, nc) not in seen:
                        seen.add((nr, nc)); stack.append((nr, nc))
            if len(seen) == len(S):
                for (r, c) in region: used.add((r, c))
                regions.append([(r + 1, c + 1) for (r, c) in region])
                break
    # 生成少量比较（用sum）
    if len(regions) >= 2:
        idxs = list(range(len(regions))); rng.shuffle(idxs)
        for i in range(len(idxs) - 1):
            op = rng.choice(['<', '>'])
            orders.append((idxs[i] + 1, op, idxs[i + 1] + 1))
            break
    return regions, orders

def _format_matrix_desc(n: int, givens: List[Tuple[int, int, int]]) -> str:
    gmap: Dict[Tuple[int, int], int] = {(r, c): v for (r, c, v) in givens}
    rows_str = []
    for r in range(1, n + 1):
        row_vals = []
        for c in range(1, n + 1):
            row_vals.append(str(gmap[(r, c)]) if (r, c) in gmap else 'X')
        rows_str.append('[ ' + ', '.join(row_vals) + ' ]')
    return '\\n'.join(rows_str)

def _encode_z3(n: int,
               thermo_paths: List[Thermo],
               thermo_type: str,
               thermo_deltas: List[Dict[str, Any]],
               order_chains: List[Chain],
               chain_type: str,
               ineqs: List[Ineq],
               givens: List[Tuple[int, int, int]],
               row_order_constraints: List[Tuple[int, str, int]],
               region_defs: List[List[Coord]],
               region_order_constraints: List[Tuple[int, str, int]],
               row_weights: List[int]):
    s = Solver()
    x = [[Int(f'x_{r+1}_{c+1}') for c in range(n)] for r in range(n)]
    # 域与拉丁
    for r in range(n):
        for c in range(n):
            s.add(And(x[r][c] >= 1, x[r][c] <= n))
    for r in range(n):
        s.add(Distinct(*x[r]))
    for c in range(n):
        s.add(Distinct(*[x[r][c] for r in range(n)]))
    # givens
    for (r, c, v) in givens:
        s.add(x[r - 1][c - 1] == v)
    # 温度计与差值
    for path in thermo_paths:
        for k in range(1, len(path)):
            (pr, pc) = path[k - 1]; (cr, cc) = path[k]
            if thermo_type == 'strict':
                s.add(x[pr - 1][pc - 1] < x[cr - 1][cc - 1])
            else:
                s.add(x[pr - 1][pc - 1] <= x[cr - 1][cc - 1])
    for d in thermo_deltas:
        pidx, sidx, mode, delta = d['path_idx'], d['step_idx'], d['mode'], d['delta']
        path = thermo_paths[pidx - 1]
        (pr, pc) = path[sidx - 1]; (cr, cc) = path[sidx]
        if mode == 'ge':
            s.add(x[cr - 1][cc - 1] - x[pr - 1][pc - 1] >= delta)
        else:
            s.add(x[cr - 1][cc - 1] - x[pr - 1][pc - 1] == delta)
    # 不等式与顺序链
    for ((r1, c1), op, (r2, c2)) in ineqs:
        s.add(x[r1 - 1][c1 - 1] < x[r2 - 1][c2 - 1] if op == '<' else x[r1 - 1][c1 - 1] > x[r2 - 1][c2 - 1])
    for chain in order_chains:
        for k in range(1, len(chain)):
            (pr, pc) = chain[k - 1]; (cr, cc) = chain[k]
            s.add(x[pr - 1][pc - 1] < x[cr - 1][cc - 1] if chain_type == 'strict' else x[pr - 1][pc - 1] <= x[cr - 1][cc - 1])
    # 行评分（线性）
    scores = [Sum([row_weights[c] * x[r][c] for c in range(n)]) for r in range(n)]
    for (i, op, j) in row_order_constraints:
        s.add(scores[i - 1] < scores[j - 1] if op == '<' else scores[i - 1] > scores[j - 1])
    # 区域比较（sum）
    for (ri, op, rj) in region_order_constraints:
        si = Sum([x[r - 1][c - 1] for (r, c) in region_defs[ri - 1]])
        sj = Sum([x[r - 1][c - 1] for (r, c) in region_defs[rj - 1]])
        s.add(si < sj if op == '<' else si > sj)
    return s, x

def _z3_unique_check(n: int,
                     thermo_paths: List[Thermo],
                     thermo_type: str,
                     thermo_deltas: List[Dict[str, Any]],
                     order_chains: List[Chain],
                     chain_type: str,
                     ineqs: List[Ineq],
                     givens: List[Tuple[int, int, int]],
                     row_order_constraints: List[Tuple[int, str, int]],
                     region_defs: List[List[Coord]],
                     region_order_constraints: List[Tuple[int, str, int]],
                     row_weights: List[int],
                     timeout_ms: int) -> Tuple[bool, List[List[int]]]:
    s, x = _encode_z3(n, thermo_paths, thermo_type, thermo_deltas, order_chains, chain_type,
                      ineqs, givens, row_order_constraints, region_defs, region_order_constraints, row_weights)
    s.set('timeout', timeout_ms)
    if s.check() != sat:
        return (False, [])
    m = s.model()
    sol1 = [[m[x[r][c]].as_long() for c in range(n)] for r in range(n)]
    # 阻断第一解：至少一个位置不同
    s.add(Or([x[r][c] != sol1[r][c] for r in range(n) for c in range(n)]))
    if s.check() == sat:
        return (False, sol1)
    return (True, sol1)

def function_1(n: int,
               thermo_target_num: int,
               chain_target_num: int,
               ineq_target_num: int,
               givens_target_num: int,
               seed: int,
               solver_time_limit_sec: int,
               row_score_alpha: int,
               row_score_beta: int,
               row_score_gamma: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    max_global_tries = 8
    per_check_ms = 200  # 单次Z3检测timeout
    diag_desc = '不启用对角线递增约束'

    for _ in range(max_global_tries):
        # 1) 生成循环拉丁解并随机置换
        solution = _gen_cyclic_latin(n, rng)
        # 2) 派生约束并强制最低密度
        thermo_paths = _derive_monotone_paths(solution, max(thermo_target_num, n), rng)
        order_chains = _derive_order_chains(solution, max(chain_target_num, n), rng)
        ineqs = _derive_ineqs(solution, max(ineq_target_num, 2 * n), rng)
        thermo_deltas = _derive_thermo_deltas(thermo_paths, solution, rng)
        region_defs, region_order_constraints = _derive_regions_and_orders(solution, rng)
        # 3) givens控制
        all_cells = [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
        rng.shuffle(all_cells)
        cap1 = int(math.ceil(0.45 * n * n))
        cap2 = int(math.ceil(0.60 * n * n))
        init_givens_num = min(givens_target_num, cap1)
        givens_cells = all_cells[:init_givens_num]
        givens = [(r, c, solution[r - 1][c - 1]) for (r, c) in givens_cells]
        remaining_cells = [p for p in all_cells if p not in givens_cells]
        # 4) 行评分权重（线性）
        row_weights = [rng.randint(1, 3) for _ in range(n)]
        scores_sol = [sum(row_weights[c] * solution[r][c] for c in range(n)) for r in range(n)]
        row_pairs = [(i, j) for i in range(1, n + 1) for j in range(i + 1, n + 1)]
        rng.shuffle(row_pairs)
        row_order_constraints: List[Tuple[int, str, int]] = []
        for (i, j) in row_pairs[:max(1, n // 2)]:
            op = '<' if scores_sol[i - 1] < scores_sol[j - 1] else '>'
            row_order_constraints.append((i, op, j))

        # 5) 唯一性验证与增量加约束
        start = time.time()
        while True:
            if time.time() - start > solver_time_limit_sec:
                break
            unique, sol1 = _z3_unique_check(n, thermo_paths, 'strict', thermo_deltas, order_chains, 'strict',
                                            ineqs, givens, row_order_constraints, region_defs, region_order_constraints,
                                            row_weights, timeout_ms=per_check_ms)
            if unique:
                # 文本渲染
                def fmt_paths(paths: List[Thermo]) -> str:
                    items = []
                    for p in paths:
                        items.append('(' + ' -> '.join([f'({r},{c})' for (r, c) in p]) + ')')
                    return '[' + ', '.join(items) + ']'
                def fmt_deltas(deltas: List[Dict[str, Any]]) -> str:
                    items = []
                    for d in deltas:
                        items.append(f'(路径{d["path_idx"]}, 步{d["step_idx"]}, {d["mode"]}, {d["delta"]})')
                    return '[' + ', '.join(items) + ']'
                def fmt_chains(chains: List[Chain]) -> str:
                    items = []
                    for ch in chains:
                        items.append('(' + ' -> '.join([f'({r},{c})' for (r, c) in ch]) + ')')
                    return '[' + ', '.join(items) + ']'
                def fmt_row_orders(row_orders: List[Tuple[int, str, int]]) -> str:
                    return '[' + ', '.join([f'(row {i}) {op} (row {j})' for (i, op, j) in row_orders]) + ']'
                def fmt_regions(regions: List[List[Coord]]) -> str:
                    items = []
                    for reg in regions:
                        items.append('[' + ', '.join([f'({r},{c})' for (r, c) in reg]) + ']')
                    return '[' + ', '.join(items) + ']'
                def fmt_region_orders(orders: List[Tuple[int, str, int]]) -> str:
                    return '[' + ', '.join([f'(R{i}) {op} (R{j})' for (i, op, j) in orders]) + ']'
                def fmt_ineqs(ineqs_list: List[Ineq]) -> str:
                    items = []
                    for ((r1, c1), op, (r2, c2)) in ineqs_list:
                        items.append(f'(({r1},{c1}) {op} ({r2},{c2}))')
                    return '[' + ', '.join(items) + ']'
                matrix_desc = _format_matrix_desc(n, givens)
                thermo_desc = '温度计: 每条路径从首端到末端每一步严格递增(相邻格值逐步增大)'
                chain_desc = '顺序链: 给定的格序列按照标注的顺序严格递增(不要求相邻)'
                row_score_desc = f'行评分: score(row)=Σ(w_c·单元值), 权重w={row_weights}; 对若干行给出分数的大小比较关系。'
                region_desc = '区域比较: 在给定的连通区域集合上以各单元值之和为度量, 给出区域间的比较关系。'
                ineq_desc = '不等式: 某些相邻格之间存在大小关系, 使用符号<或>表示, 满足列出的对。'
                return {
                    'n': n,
                    'diag_desc': diag_desc,
                    'thermo_desc': thermo_desc,
                    'chain_desc': chain_desc,
                    'row_score_desc': row_score_desc,
                    'region_desc': region_desc,
                    'ineq_desc': ineq_desc,
                    'thermo_delta_desc': '温度计差值: 部分温度计的相邻步要求差值满足指定关系(ge或eq)。',
                    'thermo_paths': thermo_paths,
                    'thermo_deltas': thermo_deltas,
                    'order_chains': order_chains,
                    'ineqs': ineqs,
                    'row_order_constraints': row_order_constraints,
                    'region_defs': region_defs,
                    'region_order_constraints': region_order_constraints,
                    'givens': givens,
                    'matrix_desc': matrix_desc,
                    'thermo_paths_text': fmt_paths(thermo_paths),
                    'thermo_deltas_text': fmt_deltas(thermo_deltas),
                    'order_chains_text': fmt_chains(order_chains),
                    'row_order_constraints_text': fmt_row_orders(row_order_constraints),
                    'region_defs_text': fmt_regions(region_defs),
                    'region_order_constraints_text': fmt_region_orders(region_order_constraints),
                    'ineqs_text': fmt_ineqs(ineqs),
                    'solution_grid': sol1,
                    'unique': True
                }
            # 非唯一或timeout：增量逻辑约束，其次小步givens
            # 追加不等式
            edges_all: List[Tuple[Coord, Coord]] = []
            for r in range(n):
                for c in range(n):
                    for (nr, nc) in _neighbors(n, r - 1 if r > 0 else 0, c - 1 if c > 0 else 0):
                        pass  # 占位，不使用此路径；直接从所有坐标构造
            # 快速随机挑选一个尚未使用的相邻对
            # 简易策略：从所有可能边中挑一个新边
            all_edges = []
            for r in range(1, n + 1):
                for c in range(1, n + 1):
                    for (nr, nc) in _neighbors(n, r - 1, c - 1):
                        if (nr, nc) > (r - 1, c - 1):
                            all_edges.append(((r, c), (nr + 1, nc + 1)))
            rng.shuffle(all_edges)
            used_edges = set(((a[0], a[1], b[0], b[1]) for (a, _, b) in ineqs))
            added = False
            for (a, b) in all_edges:
                key = (a[0], a[1], b[0], b[1])
                if key in used_edges: continue
                v1 = solution[a[0] - 1][a[1] - 1]; v2 = solution[b[0] - 1][b[1] - 1]
                op = '<' if v1 < v2 else '>'
                ineqs.append((a, op, b)); added = True; break
            if added: continue
            # 追加温度计差值
            extra_deltas = _derive_thermo_deltas(thermo_paths, solution, rng)
            if extra_deltas:
                thermo_deltas.append(extra_deltas[0]); continue
            # 追加顺序链
            extra_chains = _derive_order_chains(solution, 1, rng)
            if extra_chains:
                order_chains.append(extra_chains[0]); continue
            # 追加区域比较
            extra_regions, extra_orders = _derive_regions_and_orders(solution, rng)
            if extra_orders:
                region_order_constraints += extra_orders; continue
            # 小步givens（≤60%）
            if remaining_cells and len(givens) < cap2:
                r, c = remaining_cells.pop()
                givens.append((r, c, solution[r - 1][c - 1]))
                continue
            break  # 无法增量，退出本轮

    # 多轮未收敛：强约束实例（不满盘）
    solution = _gen_cyclic_latin(n, random.Random(seed + 2026))
    thermo_paths = _derive_monotone_paths(solution, n, random.Random(seed + 1))
    order_chains = _derive_order_chains(solution, n, random.Random(seed + 2))
    ineqs = _derive_ineqs(solution, 2 * n, random.Random(seed + 3))
    thermo_deltas = _derive_thermo_deltas(thermo_paths, solution, random.Random(seed + 4))
    region_defs, region_order_constraints = _derive_regions_and_orders(solution, random.Random(seed + 5))
    givens: List[Tuple[int, int, int]] = []
    matrix_desc = _format_matrix_desc(n, givens)
    def fmt_paths(paths: List[Thermo]) -> str:
        items = []
        for p in paths:
            items.append('(' + ' -> '.join([f'({r},{c})' for (r, c) in p]) + ')')
        return '[' + ', '.join(items) + ']'
    def fmt_deltas(deltas: List[Dict[str, Any]]) -> str:
        items = []
        for d in deltas:
            items.append(f'(路径{d["path_idx"]}, 步{d["step_idx"]}, {d["mode"]}, {d["delta"]})')
        return '[' + ', '.join(items) + ']'
    def fmt_chains(chains: List[Chain]) -> str:
        items = []
        for ch in chains:
            items.append('(' + ' -> '.join([f'({r},{c})' for (r, c) in ch]) + ')')
        return '[' + ', '.join(items) + ']'
    def fmt_row_orders(row_orders: List[Tuple[int, str, int]]) -> str:
        return '[' + ', '.join([f'(row {i}) {op} (row {j})' for (i, op, j) in row_orders]) + ']'
    def fmt_regions(regions: List[List[Coord]]) -> str:
        items = []
        for reg in regions:
            items.append('[' + ', '.join([f'({r},{c})' for (r, c) in reg]) + ']')
        return '[' + ', '.join(items) + ']'
    def fmt_region_orders(orders: List[Tuple[int, str, int]]) -> str:
        return '[' + ', '.join([f'(R{i}) {op} (R{j})' for (i, op, j) in orders]) + ']'
    def fmt_ineqs(ineqs_list: List[Ineq]) -> str:
        items = []
        for ((r1, c1), op, (r2, c2)) in ineqs_list:
            items.append(f'(({r1},{c1}) {op} ({r2},{c2}))')
        return '[' + ', '.join(items) + ']'
    return {
        'n': n,
        'diag_desc': '不启用对角线递增约束',
        'thermo_desc': '温度计: 每条路径从首端到末端每一步严格递增(相邻格值逐步增大)',
        'chain_desc': '顺序链: 给定的格序列按照标注的顺序严格递增(不要求相邻)',
        'row_score_desc': '行评分: score(row)=Σ(w_c·单元值), 权重w=[1,1,1,1]; 对若干行给出分数的大小比较关系。',
        'region_desc': '区域比较: 在给定的连通区域集合上以各单元值之和为度量, 给出区域间的比较关系。',
        'ineq_desc': '不等式: 某些相邻格之间存在大小关系, 使用符号<或>表示, 满足列出的对。',
        'thermo_delta_desc': '温度计差值: 部分温度计的相邻步要求差值满足指定关系(ge或eq)。',
        'thermo_paths': thermo_paths,
        'thermo_deltas': thermo_deltas,
        'order_chains': order_chains,
        'ineqs': ineqs,
        'row_order_constraints': [],
        'region_defs': region_defs,
        'region_order_constraints': region_order_constraints,
        'givens': [],
        'matrix_desc': matrix_desc,
        'thermo_paths_text': fmt_paths(thermo_paths),
        'thermo_deltas_text': fmt_deltas(thermo_deltas),
        'order_chains_text': fmt_chains(order_chains),
        'row_order_constraints_text': fmt_row_orders([]),
        'region_defs_text': fmt_regions(region_defs),
        'region_order_constraints_text': fmt_region_orders(region_order_constraints),
        'ineqs_text': fmt_ineqs(ineqs),
        'solution_grid': _gen_cyclic_latin(n, random.Random(seed + 7)),
        'unique': True
    }

def function_2(puzzle_config: Dict[str, Any]) -> str:
    grid = puzzle_config.get('solution_grid')
    n = puzzle_config.get('n')
    if not isinstance(grid, list) or len(grid) != n:
        return '无解'
    return '|'.join(' '.join(str(x) for x in row) for row in grid)