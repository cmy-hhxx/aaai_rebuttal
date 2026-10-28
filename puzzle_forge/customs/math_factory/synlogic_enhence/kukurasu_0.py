# kukurasu_1.py
# ------------------------------------------------
# High-complexity dual-weight Kakurasu generator with randomized multi-family rules.
# function_1: helper to create randomized integer weights
# function_2: reverse-generation + multi-layer randomized rules + uniqueness with time limits
# ------------------------------------------------
from typing import List, Tuple, Dict, Optional
import random
import time

from z3 import Solver, Bool, And, Or, Not, If, Sum, sat

def function_1(label: str, n: int, low: int, high: int, distinct: bool = True, seed: Optional[int] = None) -> List[int]:
    rng = random.Random(seed)
    if distinct and (high - low + 1) >= n:
        pool = list(range(low, high + 1))
        rng.shuffle(pool)
        return pool[:n]
    else:
        return [rng.randint(low, high) for _ in range(n)]

def _build_solver(n: int,
                  Wc: List[int],
                  Wr: List[int],
                  obstacles: List[Tuple[int, int]],
                  rules: Dict[str, object],
                  timeout_ms: int) -> Tuple[Solver, List[List['BoolRef']]]:
    s = Solver()
    s.set(timeout=timeout_ms)
    cell = [[Bool(f"cell_{i+1}_{j+1}") for j in range(n)] for i in range(n)]
    obstacle_set = {(r, c) for (r, c) in obstacles}
    for i in range(n):
        for j in range(n):
            if (i + 1, j + 1) in obstacle_set:
                s.add(Not(cell[i][j]))
    for i in range(n):
        if rules['row_mask'][i]:
            lhs = Sum([If(cell[i][j], Wc[j], 0) for j in range(n)])
            op = rules['row_ops'][i]; tgt = rules['row_targets'][i]
            s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for j in range(n):
        if rules['col_mask'][j]:
            lhs = Sum([If(cell[i][j], Wr[i], 0) for i in range(n)])
            op = rules['col_ops'][j]; tgt = rules['col_targets'][j]
            s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for i in range(n):
        if rules['rowcnt_mask'][i]:
            lhs = Sum([If(cell[i][j], 1, 0) for j in range(n)])
            op = rules['rowcnt_ops'][i]; tgt = rules['rowcnt_targets'][i]
            s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for j in range(n):
        if rules['colcnt_mask'][j]:
            lhs = Sum([If(cell[i][j], 1, 0) for i in range(n)])
            op = rules['colcnt_ops'][j]; tgt = rules['colcnt_targets'][j]
            s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for i in range(n):
        if rules['row_blend_mask'][i]:
            lhs_w = Sum([If(cell[i][j], Wc[j], 0) for j in range(n)])
            lhs_c = Sum([If(cell[i][j], 1, 0) for j in range(n)])
            lhs = rules['row_a'][i] * lhs_w + rules['row_b'][i] * lhs_c
            op = rules['row_blend_ops'][i]; tgt = rules['row_blend_targets'][i]
            s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for j in range(n):
        if rules['col_blend_mask'][j]:
            lhs_w = Sum([If(cell[i][j], Wr[i], 0) for i in range(n)])
            lhs_c = Sum([If(cell[i][j], 1, 0) for i in range(n)])
            lhs = rules['col_a'][j] * lhs_w + rules['col_b'][j] * lhs_c
            op = rules['col_blend_ops'][j]; tgt = rules['col_blend_targets'][j]
            s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (r0, c0, size, op, tgt) in rules['blocks_wcol']:
        lhs = Sum([If(cell[i-1][j-1], Wc[j-1], 0) for i in range(r0, r0 + size) for j in range(c0, c0 + size)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (r0, c0, size, op, tgt) in rules['blocks_wrow']:
        lhs = Sum([If(cell[i-1][j-1], Wr[i-1], 0) for i in range(r0, r0 + size) for j in range(c0, c0 + size)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (r0, c0, size, op, tgt) in rules['blocks_cnt']:
        lhs = Sum([If(cell[i-1][j-1], 1, 0) for i in range(r0, r0 + size) for j in range(c0, c0 + size)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (op, tgt) in rules['diag_main_wcol']:
        lhs = Sum([If(cell[i-1][i-1], Wc[i-1], 0) for i in range(1, n+1)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (op, tgt) in rules['diag_main_wrow']:
        lhs = Sum([If(cell[i-1][i-1], Wr[i-1], 0) for i in range(1, n+1)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (op, tgt) in rules['diag_main_cnt']:
        lhs = Sum([If(cell[i-1][i-1], 1, 0) for i in range(1, n+1)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (op, tgt) in rules['diag_anti_wcol']:
        lhs = Sum([If(cell[i-1][(n - i)], Wc[n - i - 1], 0) for i in range(1, n+1)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (op, tgt) in rules['diag_anti_wrow']:
        lhs = Sum([If(cell[i-1][(n - i)], Wr[i-1], 0) for i in range(1, n+1)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    for (op, tgt) in rules['diag_anti_cnt']:
        lhs = Sum([If(cell[i-1][(n - i)], 1, 0) for i in range(1, n+1)])
        s.add(lhs == tgt if op == 'eq' else (lhs <= tgt if op == 'le' else lhs >= tgt))
    if rules['global_mask']:
        total_ones = Sum([If(cell[i][j], 1, 0) for i in range(n) for j in range(n)])
        op = rules['global_op']; tgt = rules['global_target']
        s.add(total_ones == tgt if op == 'eq' else (total_ones <= tgt if op == 'le' else total_ones >= tgt))
    return s, cell

def _check_unique(n: int,
                  Wc: List[int],
                  Wr: List[int],
                  obstacles: List[Tuple[int, int]],
                  rules: Dict[str, object],
                  timeout_ms: int) -> Tuple[bool, List[List[bool]]]:
    s, cell = _build_solver(n, Wc, Wr, obstacles, rules, timeout_ms)
    if s.check() != sat:
        return (False, [])
    m = s.model()
    first_grid = [[bool(m.eval(cell[i][j])) for j in range(n)] for i in range(n)]
    s.push()
    s.add(Or([cell[i][j] != m.eval(cell[i][j]) for i in range(n) for j in range(n)]))
    is_unique = (s.check() != sat)
    s.pop()
    return (is_unique, first_grid)

def _op_symbol(op: str) -> str:
    return {'eq': '=', 'le': '≤', 'ge': '≥'}.get(op, '=')

def _choose_op_and_target(rng: random.Random, base: int) -> Tuple[str, int]:
    op = rng.choice(['eq', 'le', 'ge'])
    if op == 'eq':
        tgt = base
    elif op == 'le':
        tgt = base + rng.randint(0, 2)
    else:
        tgt = max(0, base - rng.randint(0, 2))
    return op, tgt

def _gen_rule_text_row_w(i: int, op: str, tgt: int) -> str:
    return f"第{i}行的加权和 {_op_symbol(op)} {tgt}"

def _gen_rule_text_col_w(j: int, op: str, tgt: int) -> str:
    return f"第{j}列的加权和 {_op_symbol(op)} {tgt}"

def _gen_rule_text_row_cnt(i: int, op: str, tgt: int) -> str:
    return f"第{i}行中 1 的个数 {_op_symbol(op)} {tgt}"

def _gen_rule_text_col_cnt(j: int, op: str, tgt: int) -> str:
    return f"第{j}列中 1 的个数 {_op_symbol(op)} {tgt}"

def _gen_rule_text_row_blend(i: int, a: int, b: int, op: str, tgt: int) -> str:
    return f"第{i}行满足 {a}×加权和 + {b}×1 的个数 {_op_symbol(op)} {tgt}"

def _gen_rule_text_col_blend(j: int, a: int, b: int, op: str, tgt: int) -> str:
    return f"第{j}列满足 {a}×加权和 + {b}×1 的个数 {_op_symbol(op)} {tgt}"

def _gen_rule_text_block(kind: str, r0: int, c0: int, size: int, op: str, tgt: int) -> str:
    name = {'wcol': '列权重', 'wrow': '行权重', 'cnt': '1 的个数'}[kind]
    return f"以 ({r0},{c0}) 为左上角的 {size}×{size} 子块的{name}之和 {_op_symbol(op)} {tgt}"

def _gen_rule_text_diag(which: str, kind: str, op: str, tgt: int) -> str:
    wtxt = '主对角线' if which == 'main' else '副对角线'
    ktxt = {'wcol': '列权重之和', 'wrow': '行权重之和', 'cnt': '1 的个数'}[kind]
    return f"{wtxt}上的{ktxt} {_op_symbol(op)} {tgt}"

def function_2(n_min: int,
               n_max: int,
               weight_min: int,
               weight_max: int,
               ob_ratio_min: float,
               ob_ratio_max: float,
               max_tries: int,
               distinct_weights: bool,
               rule_aggressiveness: int,
               max_time_sec: int,
               seed_opt: Optional[int] = None) -> Dict[str, object]:
    rng = random.Random(seed_opt)
    start_time = time.perf_counter()
    timeout_ms = max(1000, int(max_time_sec * 1000))

    if n_min > n_max:
        n_min, n_max = n_max, n_min
    if weight_min > weight_max:
        weight_min, weight_max = weight_max, weight_min
    ob_ratio_min = max(0.0, min(1.0, ob_ratio_min))
    ob_ratio_max = max(ob_ratio_min, min(1.0, ob_ratio_max))

    attempt = 0
    while attempt < max_tries:
        if (time.perf_counter() - start_time) > max_time_sec:
            raise RuntimeError("Global time limit exceeded while generating a unique instance.")
        attempt += 1

        n = rng.randint(n_min, n_max)
        Wr = function_1("Wr", n, weight_min, weight_max, distinct_weights, seed=None)
        Wc = function_1("Wc", n, weight_min, weight_max, distinct_weights, seed=None)

        total_cells = n * n
        ob_ratio = rng.uniform(ob_ratio_min, ob_ratio_max)
        max_obstacles = min(total_cells - 1, int(round(ob_ratio * total_cells)))
        obstacle_count = rng.randint(0, max_obstacles)
        all_positions = [(i + 1, j + 1) for i in range(n) for j in range(n)]
        rng.shuffle(all_positions)
        obstacles = sorted(all_positions[:obstacle_count])
        obstacle_set = set(obstacles)

        p_one = rng.uniform(0.25, 0.7)
        grid = [[False for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                grid[i][j] = False if ((i + 1, j + 1) in obstacle_set) else (rng.random() < p_one)

        row_wsum = [sum(Wc[j] for j in range(n) if grid[i][j]) for i in range(n)]
        col_wsum = [sum(Wr[i] for i in range(n) if grid[i][j]) for j in range(n)]
        row_cnt  = [sum(1 for j in range(n) if grid[i][j]) for i in range(n)]
        col_cnt  = [sum(1 for i in range(n) if grid[i][j]) for j in range(n)]
        total_ones = sum(row_cnt)

        row_ops = ['eq'] * n
        row_targets = [row_wsum[i] for i in range(n)]
        row_mask = [False] * n
        col_ops = ['eq'] * n
        col_targets = [col_wsum[j] for j in range(n)]
        col_mask = [False] * n
        rowcnt_ops = ['eq'] * n
        rowcnt_targets = [row_cnt[i] for i in range(n)]
        rowcnt_mask = [False] * n
        colcnt_ops = ['eq'] * n
        colcnt_targets = [col_cnt[j] for j in range(n)]
        colcnt_mask = [False] * n

        row_blend_mask = [False] * n
        row_blend_ops = ['eq'] * n
        row_a = [rng.randint(1, 3) for _ in range(n)]
        row_b = [rng.randint(0, 2) for _ in range(n)]
        row_blend_targets = [row_a[i]*row_wsum[i] + row_b[i]*row_cnt[i] for i in range(n)]
        col_blend_mask = [False] * n
        col_blend_ops = ['eq'] * n
        col_a = [rng.randint(1, 3) for _ in range(n)]
        col_b = [rng.randint(0, 2) for _ in range(n)]
        col_blend_targets = [col_a[j]*col_wsum[j] + col_b[j]*col_cnt[j] for j in range(n)]

        blocks_wcol: List[Tuple[int,int,int,str,int]] = []
        blocks_wrow: List[Tuple[int,int,int,str,int]] = []
        blocks_cnt:  List[Tuple[int,int,int,str,int]] = []
        max_blocks = rng.randint(1, max(1, min(3, n-1)))
        for _ in range(max_blocks):
            size = rng.randint(2, max(2, min(4, n)))
            r0 = rng.randint(1, n - size + 1)
            c0 = rng.randint(1, n - size + 1)
            wcol_sum = sum(Wc[j-1] for i in range(r0, r0+size) for j in range(c0, c0+size) if grid[i-1][j-1])
            wrow_sum = sum(Wr[i-1] for i in range(r0, r0+size) for j in range(c0, c0+size) if grid[i-1][j-1])
            cnt_sum  = sum(1 for i in range(r0, r0+size) for j in range(c0, c0+size) if grid[i-1][j-1])
            op_wcol, tgt_wcol = _choose_op_and_target(rng, wcol_sum)
            op_wrow, tgt_wrow = _choose_op_and_target(rng, wrow_sum)
            op_cnt,  tgt_cnt  = _choose_op_and_target(rng, cnt_sum)
            if rng.random() < 0.7:
                blocks_wcol.append((r0, c0, size, op_wcol, tgt_wcol))
            if rng.random() < 0.7:
                blocks_wrow.append((r0, c0, size, op_wrow, tgt_wrow))
            if rng.random() < 0.7:
                blocks_cnt.append((r0, c0, size, op_cnt, tgt_cnt))

        diag_main_wcol: List[Tuple[str,int]] = []
        diag_main_wrow: List[Tuple[str,int]] = []
        diag_main_cnt:  List[Tuple[str,int]] = []
        diag_anti_wcol: List[Tuple[str,int]] = []
        diag_anti_wrow: List[Tuple[str,int]] = []
        diag_anti_cnt:  List[Tuple[str,int]] = []
        main_wcol_sum = sum(Wc[i] for i in range(n) if grid[i][i])
        main_wrow_sum = sum(Wr[i] for i in range(n) if grid[i][i])
        main_cnt_sum  = sum(1 for i in range(n) if grid[i][i])
        anti_wcol_sum = sum(Wc[n - i - 1] for i in range(n) if grid[i][n - i - 1])
        anti_wrow_sum = sum(Wr[i] for i in range(n) if grid[i][n - i - 1])
        anti_cnt_sum  = sum(1 for i in range(n) if grid[i][n - i - 1])
        if rng.random() < 0.6:
            diag_main_wcol.append(_choose_op_and_target(rng, main_wcol_sum))
        if rng.random() < 0.6:
            diag_main_wrow.append(_choose_op_and_target(rng, main_wrow_sum))
        if rng.random() < 0.6:
            diag_main_cnt.append(_choose_op_and_target(rng, main_cnt_sum))
        if rng.random() < 0.6:
            diag_anti_wcol.append(_choose_op_and_target(rng, anti_wcol_sum))
        if rng.random() < 0.6:
            diag_anti_wrow.append(_choose_op_and_target(rng, anti_wrow_sum))
        if rng.random() < 0.6:
            diag_anti_cnt.append(_choose_op_and_target(rng, anti_cnt_sum))

        global_mask = (rng.random() < 0.5)
        global_op, global_target = _choose_op_and_target(rng, total_ones) if global_mask else ('eq', total_ones)

        candidates: List[Tuple[str, int, str, int]] = []
        for i in range(n):
            candidates.append(('row_w', i, *_choose_op_and_target(rng, row_wsum[i])))
        for j in range(n):
            candidates.append(('col_w', j, *_choose_op_and_target(rng, col_wsum[j])))
        for i in range(n):
            candidates.append(('row_cnt', i, *_choose_op_and_target(rng, row_cnt[i])))
        for j in range(n):
            candidates.append(('col_cnt', j, *_choose_op_and_target(rng, col_cnt[j])))
        for i in range(n):
            candidates.append(('row_blend', i, *_choose_op_and_target(rng, row_blend_targets[i])))
        for j in range(n):
            candidates.append(('col_blend', j, *_choose_op_and_target(rng, col_blend_targets[j])))
        rng.shuffle(candidates)

        rules_bundle = {
            'row_ops': row_ops, 'row_targets': row_targets, 'row_mask': row_mask,
            'col_ops': col_ops, 'col_targets': col_targets, 'col_mask': col_mask,
            'rowcnt_ops': rowcnt_ops, 'rowcnt_targets': rowcnt_targets, 'rowcnt_mask': rowcnt_mask,
            'colcnt_ops': colcnt_ops, 'colcnt_targets': colcnt_targets, 'colcnt_mask': colcnt_mask,
            'row_blend_mask': row_blend_mask, 'row_blend_ops': row_blend_ops,
            'row_blend_targets': row_blend_targets, 'row_a': row_a, 'row_b': row_b,
            'col_blend_mask': col_blend_mask, 'col_blend_ops': col_blend_ops,
            'col_blend_targets': col_blend_targets, 'col_a': col_a, 'col_b': col_b,
            'blocks_wcol': [], 'blocks_wrow': [], 'blocks_cnt': [],
            'diag_main_wcol': [], 'diag_main_wrow': [], 'diag_main_cnt': [],
            'diag_anti_wcol': [], 'diag_anti_wrow': [], 'diag_anti_cnt': [],
            'global_mask': False, 'global_op': 'eq', 'global_target': total_ones
        }
        rule_lines: List[str] = []

        added = 0
        for kind, idx, op, tgt in candidates:
            if kind == 'row_w' and not rules_bundle['row_mask'][idx]:
                rules_bundle['row_mask'][idx] = True
                rules_bundle['row_ops'][idx] = op
                rules_bundle['row_targets'][idx] = tgt
                rule_lines.append(_gen_rule_text_row_w(idx + 1, op, tgt))
                added += 1
            elif kind == 'col_w' and not rules_bundle['col_mask'][idx]:
                rules_bundle['col_mask'][idx] = True
                rules_bundle['col_ops'][idx] = op
                rules_bundle['col_targets'][idx] = tgt
                rule_lines.append(_gen_rule_text_col_w(idx + 1, op, tgt))
                added += 1
            if added >= 2:
                break

        for lst, which, kind in [
            (diag_main_wcol, 'main', 'wcol'),
            (diag_main_wrow, 'main', 'wrow'),
            (diag_main_cnt,  'main', 'cnt'),
            (diag_anti_wcol, 'anti', 'wcol'),
            (diag_anti_wrow, 'anti', 'wrow'),
            (diag_anti_cnt,  'anti', 'cnt')
        ]:
            if lst:
                op, tgt = lst[0]
                key = f"diag_{which}_{kind}"
                rules_bundle[key] = [(op, tgt)]
                rule_lines.append(_gen_rule_text_diag(which, kind, op, tgt))

        def add_blocks(src_list, dst_key, kind_name):
            if src_list:
                k = rng.randint(1, min(2, len(src_list)))
                chosen = rng.sample(src_list, k)
                rules_bundle[dst_key].extend(chosen)
                for (r0, c0, size, op, tgt) in chosen:
                    rule_lines.append(_gen_rule_text_block(kind_name, r0, c0, size, op, tgt))
        add_blocks(blocks_wcol, 'blocks_wcol', 'wcol')
        add_blocks(blocks_wrow, 'blocks_wrow', 'wrow')
        add_blocks(blocks_cnt,  'blocks_cnt',  'cnt')

        if global_mask:
            rules_bundle['global_mask'] = True
            rules_bundle['global_op'] = global_op
            rules_bundle['global_target'] = global_target
            rule_lines.append(f"全局 1 的总个数 {_op_symbol(global_op)} {global_target}")

        is_unique, _ = _check_unique(n, Wc, Wr, obstacles, rules_bundle, timeout_ms)
        t = 0
        while (not is_unique) and t < (len(candidates) + rule_aggressiveness * 3):
            if (time.perf_counter() - start_time) > max_time_sec:
                raise RuntimeError("Global time limit exceeded while refining rules to uniqueness.")
            for kind, idx, op, tgt in candidates:
                if kind == 'row_w' and not rules_bundle['row_mask'][idx]:
                    rules_bundle['row_mask'][idx] = True
                    rules_bundle['row_ops'][idx] = op
                    rules_bundle['row_targets'][idx] = tgt
                    rule_lines.append(_gen_rule_text_row_w(idx + 1, op, tgt))
                    break
                elif kind == 'col_w' and not rules_bundle['col_mask'][idx]:
                    rules_bundle['col_mask'][idx] = True
                    rules_bundle['col_ops'][idx] = op
                    rules_bundle['col_targets'][idx] = tgt
                    rule_lines.append(_gen_rule_text_col_w(idx + 1, op, tgt))
                    break
                elif kind == 'row_cnt' and not rules_bundle['rowcnt_mask'][idx]:
                    rules_bundle['rowcnt_mask'][idx] = True
                    rules_bundle['rowcnt_ops'][idx] = op
                    rules_bundle['rowcnt_targets'][idx] = tgt
                    rule_lines.append(_gen_rule_text_row_cnt(idx + 1, op, tgt))
                    break
                elif kind == 'col_cnt' and not rules_bundle['colcnt_mask'][idx]:
                    rules_bundle['colcnt_mask'][idx] = True
                    rules_bundle['colcnt_ops'][idx] = op
                    rules_bundle['colcnt_targets'][idx] = tgt
                    rule_lines.append(_gen_rule_text_col_cnt(idx + 1, op, tgt))
                    break
                elif kind == 'row_blend' and not rules_bundle['row_blend_mask'][idx]:
                    rules_bundle['row_blend_mask'][idx] = True
                    rules_bundle['row_blend_ops'][idx] = op
                    base = row_blend_targets[idx]
                    if op == 'le':
                        base += rng.randint(0, 2)
                    elif op == 'ge':
                        base = max(0, base - rng.randint(0, 2))
                    rules_bundle['row_blend_targets'][idx] = base
                    rule_lines.append(_gen_rule_text_row_blend(idx + 1, rules_bundle['row_a'][idx], rules_bundle['row_b'][idx], op, base))
                    break
                elif kind == 'col_blend' and not rules_bundle['col_blend_mask'][idx]:
                    rules_bundle['col_blend_mask'][idx] = True
                    rules_bundle['col_blend_ops'][idx] = op
                    base = col_blend_targets[idx]
                    if op == 'le':
                        base += rng.randint(0, 2)
                    elif op == 'ge':
                        base = max(0, base - rng.randint(0, 2))
                    rules_bundle['col_blend_targets'][idx] = base
                    rule_lines.append(_gen_rule_text_col_blend(idx + 1, rules_bundle['col_a'][idx], rules_bundle['col_b'][idx], op, base))
                    break
            is_unique, _ = _check_unique(n, Wc, Wr, obstacles, rules_bundle, timeout_ms)
            t += 1

        if not is_unique:
            continue

        rows_s = [str(i) for i in range(1, n + 1)]
        cols_s = [str(j) for j in range(1, n + 1)]
        if not rule_lines:
            rule_lines.append(_gen_rule_text_row_w(1, 'eq', row_wsum[0]))
            rules_bundle['row_mask'][0] = True
            rules_bundle['row_ops'][0] = 'eq'
            rules_bundle['row_targets'][0] = row_wsum[0]

        return {
            "n": n,
            "rows_s": rows_s,
            "cols_s": cols_s,
            "Wc": Wc,
            "Wr": Wr,
            "obstacles": obstacles,
            "row_ops": rules_bundle['row_ops'],
            "row_targets": rules_bundle['row_targets'],
            "row_mask": rules_bundle['row_mask'],
            "col_ops": rules_bundle['col_ops'],
            "col_targets": rules_bundle['col_targets'],
            "col_mask": rules_bundle['col_mask'],
            "rowcnt_ops": rules_bundle['rowcnt_ops'],
            "rowcnt_targets": rules_bundle['rowcnt_targets'],
            "rowcnt_mask": rules_bundle['rowcnt_mask'],
            "colcnt_ops": rules_bundle['colcnt_ops'],
            "colcnt_targets": rules_bundle['colcnt_targets'],
            "colcnt_mask": rules_bundle['colcnt_mask'],
            "row_blend_mask": rules_bundle['row_blend_mask'],
            "row_blend_ops": rules_bundle['row_blend_ops'],
            "row_blend_targets": rules_bundle['row_blend_targets'],
            "row_a": rules_bundle['row_a'],
            "row_b": rules_bundle['row_b'],
            "col_blend_mask": rules_bundle['col_blend_mask'],
            "col_blend_ops": rules_bundle['col_blend_ops'],
            "col_blend_targets": rules_bundle['col_blend_targets'],
            "col_a": rules_bundle['col_a'],
            "col_b": rules_bundle['col_b'],
            "blocks_wcol": rules_bundle['blocks_wcol'],
            "blocks_wrow": rules_bundle['blocks_wrow'],
            "blocks_cnt": rules_bundle['blocks_cnt'],
            "diag_main_wcol": rules_bundle['diag_main_wcol'],
            "diag_main_wrow": rules_bundle['diag_main_wrow'],
            "diag_main_cnt": rules_bundle['diag_main_cnt'],
            "diag_anti_wcol": rules_bundle['diag_anti_wcol'],
            "diag_anti_wrow": rules_bundle['diag_anti_wrow'],
            "diag_anti_cnt": rules_bundle['diag_anti_cnt'],
            "global_mask": rules_bundle['global_mask'],
            "global_op": rules_bundle['global_op'],
            "global_target": rules_bundle['global_target'],
            "rule_lines": rule_lines
        }

    raise RuntimeError("Failed to generate a unique high-complexity Kakurasu instance within limits; consider relaxing ranges or increasing max_tries.")