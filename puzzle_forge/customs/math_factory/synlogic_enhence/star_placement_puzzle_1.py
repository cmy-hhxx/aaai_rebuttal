# -*- coding: utf-8 -*-
"""
star_placement_puzzle_3.py

改进要点：
- 在 gen_rules 阶段加入 ensure_grouping_feasible 修正分组上下界，确保 minA+minB ≤ n ≤ maxA+maxB；
- 保持规则与题面文本一致，solve_complex 不修改规则，仅求解；
- 保留唯一性验证模块，仅在规则生成阶段使用；
- 搜索时间限制控制在 3 分钟以内。

提供算子：
- letters, gen_region_labels, unique_regions, region_cells
- rand_value_matrix, rand_cost_matrix, format_grid_labels, format_grid_values
- rand_int, choice, adjacency_pairs
- ensure_grouping_feasible（新增）
- _compute_min_row_costs, _build_adjacency, _clusters_cover_map, _region_group_map, _dfs_optimize, verify_unique
- gen_rules（规则生成与唯一性筛选）
- solve_complex（最终求解）
- extract_field
"""

from typing import List, Tuple, Dict, Any, Set, Optional
import random
import time


# 基础算子
def letters(n: int) -> List[str]:
    base = [chr(ord('A') + i) for i in range(26)]
    if n <= 26:
        return base[:n]
    res = []
    idx = 0
    while len(res) < n:
        res.append(base[idx % 26] + str(idx // 26 + 1))
        idx += 1
    return res


def gen_region_labels(data: Dict[str, Any]) -> List[List[str]]:
    n: int = int(data['n'])
    mode: str = data['mode']
    letters_list: List[str] = data['letters']
    assert len(letters_list) == n
    labels_2d: List[List[str]] = [[None for _ in range(n)] for _ in range(n)]
    if mode == 'row':
        for r in range(n):
            for c in range(n):
                labels_2d[r][c] = letters_list[r]
    elif mode == 'col':
        for r in range(n):
            for c in range(n):
                labels_2d[r][c] = letters_list[c]
    elif mode == 'diagonal':
        for r in range(n):
            for c in range(n):
                labels_2d[r][c] = letters_list[(r + c) % n]
    else:
        all_cells = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(all_cells)
        for i in range(n):
            r, c = all_cells[i]
            labels_2d[r][c] = letters_list[i]
        for k in range(n, n * n):
            r, c = all_cells[k]
            labels_2d[r][c] = random.choice(letters_list)
    return labels_2d


def unique_regions(labels_2d: List[List[str]]) -> List[str]:
    s = set()
    for row in labels_2d:
        for x in row:
            s.add(x)
    return sorted(s)


def region_cells(labels_2d: List[List[str]]) -> Dict[str, List[Tuple[int, int]]]:
    h = len(labels_2d)
    w = len(labels_2d[0]) if h > 0 else 0
    mapping: Dict[str, List[Tuple[int, int]]] = {}
    for r in range(h):
        for c in range(w):
            reg = labels_2d[r][c]
            mapping.setdefault(reg, []).append((r + 1, c + 1))
    return mapping


def rand_value_matrix(data: Dict[str, Any]) -> List[List[int]]:
    n: int = int(data['n'])
    min_v: int = int(data['min_v'])
    max_v: int = int(data['max_v'])
    assert min_v <= max_v
    return [[random.randint(min_v, max_v) for _ in range(n)] for _ in range(n)]


def rand_cost_matrix(data: Dict[str, Any]) -> List[List[int]]:
    n: int = int(data['n'])
    min_c: int = int(data['min_c'])
    max_c: int = int(data['max_c'])
    assert min_c <= max_c
    return [[random.randint(min_c, max_c) for _ in range(n)] for _ in range(n)]


def format_grid_labels(labels_2d: List[List[str]]) -> str:
    row_strs = []
    for row in labels_2d:
        inner = ','.join("'" + s + "'" for s in row)
        row_strs.append('[' + inner + ']')
    return '[' + ','.join(row_strs) + ']'


def format_grid_values(values_2d: List[List[int]]) -> str:
    row_strs = []
    for row in values_2d:
        inner = ','.join(str(x) for x in row)
        row_strs.append('[' + inner + ']')
    return '[' + ','.join(row_strs) + ']'


def rand_int(data: Dict[str, Any]) -> int:
    lo = int(data['lo']); hi = int(data['hi'])
    return random.randint(lo, hi)


def choice(data: List[Any]) -> Any:
    if not isinstance(data, list) or not data:
        raise ValueError('choice expects a non-empty list')
    return random.choice(data)


def adjacency_pairs(data: Any) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    if isinstance(data, dict):
        n = int(data.get('n')); include_diagonal = bool(data.get('include_diagonal', True))
    else:
        n = int(data); include_diagonal = True
    dirs4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    dirs8 = dirs4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    dirs = dirs8 if include_diagonal else dirs4
    pairs = []; seen = set()
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            for dr, dc in dirs:
                rr, cc = r + dr, c + dc
                if 1 <= rr <= n and 1 <= cc <= n:
                    a = (r, c); b = (rr, cc)
                    ordered = (a, b) if a < b else (b, a)
                    if ordered not in seen:
                        seen.add(ordered); pairs.append(ordered)
    return pairs


# ---------- 辅助函数 ----------
def _compute_min_row_costs(rows: List[int], cols: List[int], allowed_set: Set[Tuple[int, int]], cost_matrix: List[List[int]]) -> List[int]:
    mins = []
    for r in rows:
        cand = []
        for c in cols:
            rc = (r, c)
            if allowed_set and rc not in allowed_set:
                continue
            cand.append(cost_matrix[r - 1][c - 1])
        if not cand:
            return []
        mins.append(min(cand))
    return mins


def ensure_grouping_feasible(n: int, groupA: List[str], groupB: List[str], minA: int, maxA: int, minB: int, maxB: int) -> Tuple[int, int, int, int]:
    LA, LB = len(groupA), len(groupB)
    # 修正上下界不超过组容量
    minA = max(0, min(minA, LA)); maxA = max(minA, min(maxA, LA))
    minB = max(0, min(minB, LB)); maxB = max(minB, min(maxB, LB))
    # 保证上界和覆盖 n
    if maxA + maxB < n:
        delta = n - (maxA + maxB)
        addA = min(delta // 2 + delta % 2, LA - maxA)
        addB = min(delta // 2, LB - maxB)
        maxA += addA; maxB += addB
        if maxA + maxB < n:
            # 若仍不足，尽量再补
            rest = n - (maxA + maxB)
            takeA = min(rest, LA - maxA)
            maxA += takeA
            rest = n - (maxA + maxB)
            takeB = min(rest, LB - maxB)
            maxB += takeB
    # 保证下界不超过 n
    if minA + minB > n:
        cut = (minA + minB) - n
        # 先削大的一侧
        if minA >= minB:
            reduceA = min(cut, minA - 0)
            minA -= reduceA; cut -= reduceA
        if cut > 0:
            reduceB = min(cut, minB - 0)
            minB -= reduceB; cut -= reduceB
    # 最终再夹紧
    minA = max(0, min(minA, maxA)); minB = max(0, min(minB, maxB))
    return minA, maxA, minB, maxB


# ---------- 求解器与唯一性验证 ----------
def _build_adjacency(n: int, metric: str, dist: int) -> Dict[Tuple[int, int], Set[Tuple[int, int]]]:
    adj: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            a = (r, c)
            S = set()
            for rr in range(1, n + 1):
                for cc in range(1, n + 1):
                    if (rr, cc) == a:
                        continue
                    dr, dc = abs(rr - r), abs(cc - c)
                    if metric == 'manhattan':
                        d = dr + dc
                        if d <= dist:
                            S.add((rr, cc))
                    else:
                        d = max(dr, dc)
                        if d <= dist:
                            S.add((rr, cc))
            adj[a] = S
    return adj


def _clusters_cover_map(clusters: List[List[Tuple[int, int]]]) -> List[Set[Tuple[int, int]]]:
    return [set(block) for block in clusters] if clusters else []


def _region_group_map(regions: List[str], grouping: Dict[str, Any]) -> Dict[str, str]:
    groupA = set(grouping['groupA']); groupB = set(grouping['groupB'])
    mp = {}
    for reg in regions:
        mp[reg] = 'A' if reg in groupA else 'B'
    return mp


def _dfs_optimize(rows: List[int], cols: List[int], regions: List[str], region_cells: Dict[str, List[Tuple[int, int]]],
                  value_matrix: List[List[int]], cost_matrix: List[List[int]], rule_pack: Dict[str, Any],
                  forbid_cols_exactly_reuse: bool = False, target_cols_tuple: Optional[Tuple[int, ...]] = None,
                  time_deadline: Optional[float] = None) -> Dict[str, Any]:
    n = len(rows)
    col_rule = rule_pack['col_rule']
    region_rule = rule_pack['region_rule']
    total_rule = rule_pack['total_rule']
    adj_rule = rule_pack['adj_rule']
    allowed_cells = set(tuple(x) for x in rule_pack.get('allowed_cells', []))
    forbidden_cells = set(tuple(x) for x in rule_pack.get('forbidden_cells', []))
    budget = int(rule_pack['budget'])
    grouping = rule_pack['grouping']
    clusters = rule_pack['clusters']
    cluster_k = rule_pack['cluster_k']

    cell_to_region: Dict[Tuple[int, int], str] = {}
    for reg, cells in region_cells.items():
        for rc in cells:
            cell_to_region[rc] = reg

    adj = _build_adjacency(n, adj_rule['metric'], int(adj_rule['dist']))
    cluster_sets = _clusters_cover_map(clusters)
    reg_group_map = _region_group_map(regions, grouping)
    minA, maxA = int(grouping['minA']), int(grouping['maxA'])
    minB, maxB = int(grouping['minB']), int(grouping['maxB'])

    row_max_value: List[int] = [max(value_matrix[r - 1]) for r in rows]
    row_min_cost: List[int] = [min(cost_matrix[r - 1]) for r in rows]

    best_score = -10**9
    best_cost = 10**9
    best_cells: List[Tuple[int, int]] = []
    best_cols_tuple: Tuple[int, ...] = tuple()

    used_cols: Set[int] = set()
    used_regions: Set[str] = set()
    chosen: List[Tuple[int, int]] = []
    cur_groupA = 0
    cur_groupB = 0
    cluster_counts: List[int] = [0 for _ in cluster_sets]

    def can_place(r: int, c: int) -> bool:
        rc = (r, c)
        if allowed_cells and rc not in allowed_cells:
            return False
        if rc in forbidden_cells:
            return False
        if c in used_cols:
            return False
        reg = cell_to_region.get(rc)
        if reg is None:
            return False
        if region_rule['type'] in ('exactly', 'at_most') and reg in used_regions:
            return False
        for (pr, pc) in chosen:
            if rc in adj.get((pr, pc), set()):
                return False
        for idx, S in enumerate(cluster_sets):
            if rc in S and cluster_k is not None and cluster_counts[idx] >= cluster_k:
                return False
        return True

    def bound_feasible(r_idx: int, cur_score_local: int, cur_cost_local: int) -> bool:
        ub_value = cur_score_local + sum(row_max_value[i] for i in range(r_idx, n))
        if ub_value < best_score:
            return False
        min_cost_remain = sum(row_min_cost[i] for i in range(r_idx, n))
        if cur_cost_local + min_cost_remain > budget:
            return False
        remain = n - r_idx
        if cur_groupA > maxA or cur_groupB > maxB:
            return False
        needA = max(0, minA - cur_groupA)
        needB = max(0, minB - cur_groupB)
        if needA + needB > remain:
            return False
        return True

    def dfs(r_idx: int, cur_score_local: int, cur_cost_local: int):
        nonlocal best_score, best_cost, best_cells, best_cols_tuple, cur_groupA, cur_groupB
        if time_deadline is not None and time.time() > time_deadline:
            return
        if r_idx == n:
            if len(used_cols) != n:
                return
            if region_rule['type'] == 'exactly' and len(used_regions) != len(regions):
                return
            if len(chosen) != n:
                return
            if not (minA <= cur_groupA <= maxA and minB <= cur_groupB <= maxB):
                return
            if cur_cost_local > budget:
                return
            cols_tuple = tuple(c for (_, c) in chosen)
            if forbid_cols_exactly_reuse and target_cols_tuple is not None and cols_tuple == target_cols_tuple:
                return
            if (cur_score_local > best_score) or (cur_score_local == best_score and (best_cols_tuple == () or cols_tuple < best_cols_tuple)):
                best_score = cur_score_local
                best_cost = cur_cost_local
                best_cells = chosen.copy()
                best_cols_tuple = cols_tuple
            return
        if not bound_feasible(r_idx, cur_score_local, cur_cost_local):
            return

        r = rows[r_idx]
        for c in cols:
            if not can_place(r, c):
                continue
            rc = (r, c)
            reg = cell_to_region[rc]
            val = value_matrix[r - 1][c - 1]
            cost = cost_matrix[r - 1][c - 1]
            used_cols.add(c)
            if region_rule['type'] in ('exactly', 'at_most'):
                used_regions.add(reg)
            chosen.append(rc)
            incA = 1 if reg_group_map[reg] == 'A' else 0
            incB = 1 - incA
            bump_idxs = []
            for idx, S in enumerate(cluster_sets):
                if rc in S:
                    cluster_counts[idx] += 1
                    bump_idxs.append(idx)
            prevA, prevB = cur_groupA, cur_groupB
            cur_groupA += incA
            cur_groupB += incB

            dfs(r_idx + 1, cur_score_local + val, cur_cost_local + cost)

            cur_groupA = prevA
            cur_groupB = prevB
            chosen.pop()
            if region_rule['type'] in ('exactly', 'at_most'):
                used_regions.remove(reg)
            used_cols.remove(c)
            for idx in bump_idxs:
                cluster_counts[idx] -= 1

    dfs(0, 0, 0)
    if best_score <= -10**8:
        return {'ok': False}
    return {'ok': True, 'best_score': best_score, 'best_cost': best_cost, 'best_cells': best_cells, 'cols_tuple': best_cols_tuple}


def _build_placements(regions: List[str], region_cells: Dict[str, List[Tuple[int, int]]], chosen_cells: List[Tuple[int, int]]) -> Dict[str, Optional[Tuple[int, int]]]:
    chosen_set = set(chosen_cells)
    placements: Dict[str, Optional[Tuple[int, int]]] = {}
    for reg in sorted(regions):
        rc_sel = None
        for rc in region_cells.get(reg, []):
            if rc in chosen_set:
                rc_sel = (rc[0], rc[1]); break
        placements[reg] = rc_sel
    return placements


def verify_unique(rows: List[int], cols: List[int], regions: List[str], region_cells: Dict[str, List[Tuple[int, int]]],
                  value_matrix: List[List[int]], cost_matrix: List[List[int]], rule_pack: Dict[str, Any],
                  best: Dict[str, Any], time_limit_sec: int) -> bool:
    deadline = time.time() + max(5, time_limit_sec)
    alt = _dfs_optimize(rows, cols, regions, region_cells, value_matrix, cost_matrix, rule_pack,
                        forbid_cols_exactly_reuse=True, target_cols_tuple=tuple(best['cols_tuple']), time_deadline=deadline)
    if not alt['ok']:
        return True
    return not (alt['best_score'] == best['best_score'] and tuple(alt['cols_tuple']) != tuple(best['cols_tuple']))


# ---------- 规则生成（可行性与唯一性筛选） ----------
def gen_rules(ctx: Dict[str, Any]) -> Dict[str, Any]:
    n: int = int(ctx['n'])
    rows: List[int] = ctx['rows']
    cols: List[int] = ctx['cols']
    regions: List[str] = ctx['regions']
    region_cells: Dict[str, List[Tuple[int, int]]] = ctx['region_cells']
    col_cands: List[str] = ctx['col_rule_candidates']
    region_cands: List[str] = ctx['region_rule_candidates']
    total_cands: List[str] = ctx['total_rule_candidates']
    adj_metric_cands: List[str] = ctx['adj_metric_candidates']
    adj_dist_domain: List[int] = ctx['adj_distance_domain']
    cluster_enable_cands: List[bool] = ctx['cluster_enable_candidates']
    cluster_k_cands: List[int] = ctx['cluster_k_candidates']
    value_matrix: List[List[int]] = ctx['value_matrix']
    cost_matrix: List[List[int]] = ctx['cost_matrix']
    verify_time_limit_sec: int = int(ctx['verify_time_limit_sec'])
    max_resample_trials: int = int(ctx['max_resample_trials'])

    def sample_once() -> Dict[str, Any]:
        row_rule = {'type': 'exactly', 'quota': 1}
        col_rule = {'type': col_cands[0], 'quota': 1}
        total_rule = {'type': total_cands[0], 'quota': n}
        region_type = 'at_most' if random.random() < 0.7 else 'exactly'
        region_rule = {'type': region_type, 'quota': 1}
        adj_rule = {'metric': random.choice(adj_metric_cands), 'dist': adj_dist_domain[0]}

        allowed_cells: Set[Tuple[int, int]] = set()
        forbidden_cells: Set[Tuple[int, int]] = set()
        if random.random() < 0.3:
            for r in rows:
                c = random.choice(cols)
                allowed_cells.add((r, c))
            extra = random.randint(0, 2)
            for _ in range(extra):
                rc = (random.choice(rows), random.choice(cols))
                allowed_cells.add(rc)
        forbid_num = random.randint(0, 2)
        while len(forbidden_cells) < forbid_num:
            rc = (random.choice(rows), random.choice(cols))
            if rc not in allowed_cells:
                forbidden_cells.add(rc)

        min_row_costs = _compute_min_row_costs(rows, cols, allowed_cells, cost_matrix)
        if not min_row_costs:
            allowed_cells = set()
            min_row_costs = _compute_min_row_costs(rows, cols, allowed_cells, cost_matrix)
        base_cost = sum(min_row_costs)
        slack = random.randint(0, n)
        budget = base_cost + slack

        split = random.randint(max(1, n // 2), min(n - 1, (n + 1) // 2 + 1))
        groupA = regions[:split]; groupB = regions[split:]
        LA, LB = len(groupA), len(groupB)
        minA = random.randint(0, min(LA, n))
        minB = random.randint(0, min(LB, n - minA))
        maxA = random.randint(max(minA, 0), LA)
        maxB = random.randint(max(minB, 0), LB)
        minA, maxA, minB, maxB = ensure_grouping_feasible(n, groupA, groupB, minA, maxA, minB, maxB)
        grouping = {'groupA': groupA, 'groupB': groupB, 'minA': minA, 'maxA': maxA, 'minB': minB, 'maxB': maxB}

        clusters: List[List[Tuple[int, int]]] = []
        if random.choice(cluster_enable_cands):
            all_clusters = []
            for r in range(1, n):
                for c in range(1, n):
                    all_clusters.append([(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)])
            random.shuffle(all_clusters)
            take_num = random.randint(1, min(2, len(all_clusters))) if all_clusters else 0
            clusters = all_clusters[:take_num]
        cluster_k = random.choice(cluster_k_cands) if clusters else None

        return {
            'row_rule': row_rule, 'col_rule': col_rule, 'total_rule': total_rule,
            'region_rule': region_rule, 'adj_rule': adj_rule,
            'allowed_cells': sorted(list(allowed_cells)), 'forbidden_cells': sorted(list(forbidden_cells)),
            'budget': budget, 'grouping': grouping, 'clusters': clusters, 'cluster_k': cluster_k
        }

    trials_left = max_resample_trials
    start_deadline = time.time() + 180.0
    while trials_left > 0 and time.time() < start_deadline:
        rp = sample_once()
        best = _dfs_optimize(rows, cols, regions, region_cells, value_matrix, cost_matrix, rp)
        if not best['ok']:
            trials_left -= 1
            continue
        if verify_unique(rows, cols, regions, region_cells, value_matrix, cost_matrix, rp, best, verify_time_limit_sec):
            row_rule_text = '每行恰好 1 颗星'
            col_rule_text = '每列恰好 1 颗星'
            region_rule_text = '每个区域至多 1 颗星' if rp['region_rule']['type'] == 'at_most' else '每个区域恰好 1 颗星'
            total_rule_text = f'总星数恰好为 {n}'
            adjacency_text = f'两颗星的{ "曼哈顿" if rp["adj_rule"]["metric"] == "manhattan" else "切比雪夫" }距离必须大于 {rp["adj_rule"]["dist"]}'
            budget_text = f'总成本不得超过预算 {rp["budget"]}'
            groupA = rp['grouping']['groupA']; groupB = rp['grouping']['groupB']
            minA = rp['grouping']['minA']; maxA = rp['grouping']['maxA']
            minB = rp['grouping']['minB']; maxB = rp['grouping']['maxB']
            grouping_text = f'区域分成两组：组 A 为 {groupA}，组 B 为 {groupB}；组 A 选星数需在 [{minA},{maxA}]，组 B 选星数需在 [{minB},{maxB}] 之间'
            cluster_text = '未启用局部群集约束' if not rp['clusters'] else f'选定的 2×2 群集数为 {len(rp["clusters"])}，每个群集最多 {rp["cluster_k"]} 颗星'
            allowed_text = f'允许放置的单元格集合为 {sorted(list(rp["allowed_cells"]))}' if rp['allowed_cells'] else '未限定允许放置的单元格集合'
            forbidden_text = f'禁止放置的单元格集合为 {sorted(list(rp["forbidden_cells"]))}' if rp['forbidden_cells'] else '未设置禁止放置的单元格集合'
            rp.update({
                'row_rule_text': row_rule_text, 'col_rule_text': col_rule_text,
                'region_rule_text': region_rule_text, 'total_rule_text': total_rule_text,
                'adjacency_text': adjacency_text, 'budget_text': budget_text,
                'grouping_text': grouping_text, 'cluster_text': cluster_text,
                'allowed_text': allowed_text, 'forbidden_text': forbidden_text
            })
            return rp
        trials_left -= 1

    # 兜底：尽力返回一个规则包（已修正分组），不保证唯一
    rp = sample_once()
    row_rule_text = '每行恰好 1 颗星'
    col_rule_text = '每列恰好 1 颗星'
    region_rule_text = '每个区域至多 1 颗星' if rp['region_rule']['type'] == 'at_most' else '每个区域恰好 1 颗星'
    total_rule_text = f'总星数恰好为 {n}'
    adjacency_text = f'两颗星的{ "曼哈顿" if rp["adj_rule"]["metric"] == "manhattan" else "切比雪夫" }距离必须大于 {rp["adj_rule"]["dist"]}'
    budget_text = f'总成本不得超过预算 {rp["budget"]}'
    groupA = rp['grouping']['groupA']; groupB = rp['grouping']['groupB']
    minA = rp['grouping']['minA']; maxA = rp['grouping']['maxA']
    minB = rp['grouping']['minB']; maxB = rp['grouping']['maxB']
    grouping_text = f'区域分成两组：组 A 为 {groupA}，组 B 为 {groupB}；组 A 选星数需在 [{minA},{maxA}]，组 B 选星数需在 [{minB},{maxB}] 之间'
    cluster_text = '未启用局部群集约束' if not rp['clusters'] else f'选定的 2×2 群集数为 {len(rp["clusters"])}，每个群集最多 {rp["cluster_k"]} 颗星'
    allowed_text = f'允许放置的单元格集合为 {sorted(list(rp["allowed_cells"]))}' if rp['allowed_cells'] else '未限定允许放置的单元格集合'
    forbidden_text = f'禁止放置的单元格集合为 {sorted(list(rp["forbidden_cells"]))}' if rp['forbidden_cells'] else '未设置禁止放置的单元格集合'
    rp.update({
        'row_rule_text': row_rule_text, 'col_rule_text': col_rule_text,
        'region_rule_text': region_rule_text, 'total_rule_text': total_rule_text,
        'adjacency_text': adjacency_text, 'budget_text': budget_text,
        'grouping_text': grouping_text, 'cluster_text': cluster_text,
        'allowed_text': allowed_text, 'forbidden_text': forbidden_text
    })
    return rp


# ---------- 最终求解（不修改规则） ----------
def solve_complex(ctx: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[int] = ctx['rows']; cols: List[int] = ctx['cols']
    regions: List[str] = ctx['regions']; region_cells: Dict[str, List[Tuple[int, int]]] = ctx['region_cells']
    value_matrix: List[List[int]] = ctx['value_matrix']; cost_matrix: List[List[int]] = ctx['cost_matrix']
    rule_pack: Dict[str, Any] = ctx['rule_pack']

    best = _dfs_optimize(rows, cols, regions, region_cells, value_matrix, cost_matrix, rule_pack)
    if not best['ok']:
        placements = {reg: None for reg in regions}
        return {'placements': placements, 'score': -1, 'cost': -1}
    placements = _build_placements(regions, region_cells, best['best_cells'])
    return {'placements': placements, 'score': best['best_score'], 'cost': best['best_cost']}


# YAML 辅助：取字段
def extract_field(data: Dict[str, Any]) -> Any:
    d = data.get('dict'); k = data.get('key')
    if not isinstance(d, dict):
        raise ValueError('extract_field: dict expected')
    return d.get(k)


# 统一入口
def function_1(op: str, data: Any) -> Any:
    if op == 'letters':
        return letters(int(data))
    elif op == 'gen_region_labels':
        return gen_region_labels(data)
    elif op == 'unique_regions':
        return unique_regions(data)
    elif op == 'region_cells':
        return region_cells(data)
    elif op == 'rand_value_matrix':
        return rand_value_matrix(data)
    elif op == 'rand_cost_matrix':
        return rand_cost_matrix(data)
    elif op == 'format_grid_labels':
        return format_grid_labels(data)
    elif op == 'format_grid_values':
        return format_grid_values(data)
    elif op == 'rand_int':
        return rand_int(data)
    elif op == 'choice':
        return choice(data)
    elif op == 'adjacency_pairs':
        return adjacency_pairs(data)
    elif op == 'gen_rules':
        return gen_rules(data)
    elif op == 'solve_complex':
        return solve_complex(data)
    elif op == 'extract_field':
        return extract_field(data)
    else:
        raise ValueError(f'Unsupported op for function_1: {op}')


def function_2(op: str = 'noop', *args, **kwargs) -> Any:
    if op == 'format_answer':
        if len(args) < 3:
            raise ValueError('format_answer requires (placements_dict, score_value, cost_value)')
        placements, score, cost = args[0], args[1], args[2]
        ordered_keys = sorted(placements.keys())
        ordered = {k: placements[k] for k in ordered_keys}
        return str({'placements': ordered, 'score': score, 'cost': cost})
    elif op == 'noop':
        return None
    else:
        raise ValueError(f'Unsupported op for function_2: {op}')