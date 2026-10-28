# minesweeper_2.py
# -*- coding: utf-8 -*-
"""
高阶泛化版辅助函数：随机生成六角蜂巢感染题目与复合规则，并进行唯一解预验证。
"""

from typing import List, Tuple, Dict, Any, Optional
import random

# z3 导入与可用性检查
try:
    from z3 import Solver, Bool, Sum as Z3Sum, If as Z3If, Or, And as Z3And, sat
    Z3_AVAILABLE = True
except Exception:
    Z3_AVAILABLE = False


def _neighbors_even_r(r: int, c: int, rows: int, cols: int) -> List[Tuple[int, int]]:
    """even_r：按行奇偶确定邻域（偶行右偏）。"""
    if r % 2 == 0:
        candidates = [(r - 1, c), (r - 1, c + 1), (r, c - 1), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
    else:
        candidates = [(r - 1, c - 1), (r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c - 1), (r + 1, c)]
    return [(rr, cc) for rr, cc in candidates if 0 <= rr < rows and 0 <= cc < cols]


def _neighbors_odd_r(r: int, c: int, rows: int, cols: int) -> List[Tuple[int, int]]:
    """odd_r：按行奇偶确定邻域（奇行右偏）。"""
    if r % 2 == 1:
        candidates = [(r - 1, c), (r - 1, c + 1), (r, c - 1), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
    else:
        candidates = [(r - 1, c - 1), (r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c - 1), (r + 1, c)]
    return [(rr, cc) for rr, cc in candidates if 0 <= rr < rows and 0 <= cc < cols]


def _get_neighbors(mode: str, r: int, c: int, rows: int, cols: int) -> List[Tuple[int, int]]:
    return _neighbors_odd_r(r, c, rows, cols) if mode == 'odd_r' else _neighbors_even_r(r, c, rows, cols)


def function_1(*args, **kwargs):
    """
    兼容多签名入口：
    - (r, c, rows, cols[, neighbor_mode]) -> 邻居坐标列表
    - (grid, row_totals, col_totals) -> 一致性校验信息
    """
    if len(args) in (4, 5) and all(isinstance(x, int) for x in args[:4]):
        r, c, rows, cols = args[:4]
        neighbor_mode = kwargs.get('neighbor_mode', 'even_r')
        return _get_neighbors(neighbor_mode, r, c, rows, cols)
    elif len(args) == 3:
        grid, row_totals, col_totals = args
        try:
            row_sums = [sum(int(v) for v in row) for row in grid]
            if len(grid) == 0:
                col_sums = []
            else:
                cols = len(grid[0])
                col_sums = []
                for c in range(cols):
                    s = 0
                    for r in range(len(grid)):
                        s += int(grid[r][c])
                    col_sums.append(s)
            is_consistent = (list(row_sums) == list(row_totals)) and (list(col_sums) == list(col_totals))
            return {"row_sums": row_sums, "col_sums": col_sums, "row_totals": list(row_totals), "col_totals": list(col_totals), "is_consistent": is_consistent}
        except Exception:
            return {"row_sums": None, "col_sums": None, "row_totals": list(row_totals) if hasattr(row_totals, '__iter__') else row_totals, "col_totals": list(col_totals) if hasattr(col_totals, '__iter__') else col_totals, "is_consistent": False}
    else:
        raise TypeError("function_1 expects (r, c, rows, cols[, neighbor_mode]) or (grid, row_totals, col_totals)")


def _compute_counts(infected: List[List[bool]], neighbor_mode: str) -> List[List[int]]:
    rows = len(infected)
    cols = len(infected[0]) if rows > 0 else 0
    counts = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            neigh = _get_neighbors(neighbor_mode, r, c, rows, cols)
            counts[r][c] = sum(1 for (rr, cc) in neigh if infected[rr][cc])
    return counts


def _build_display_grid(infected: List[List[bool]], counts: List[List[int]], mask_safe_prob: float, rng: random.Random) -> List[List[Any]]:
    rows = len(infected)
    cols = len(infected[0]) if rows > 0 else 0
    grid_data: List[List[Any]] = [[None] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if infected[r][c]:
                grid_data[r][c] = 'X'
            else:
                grid_data[r][c] = counts[r][c] if rng.random() < mask_safe_prob else 'X'
    return grid_data


def _key_of(rc: Tuple[int, int]) -> str:
    return f"{rc[0]},{rc[1]}"


def _coord_of(key: str) -> Tuple[int, int]:
    rs, cs = key.split(",")
    return int(rs), int(cs)


def _collect_base_structures(grid_data: List[List[Any]], neighbor_mode: str) -> Dict[str, Any]:
    rows = len(grid_data)
    cols = len(grid_data[0]) if rows > 0 else 0
    unknown_keys: List[str] = []
    number_cells: List[Tuple[int, int, int]] = []
    neighbors_unknown_keys: List[List[str]] = []

    for r in range(rows):
        for c in range(cols):
            v = grid_data[r][c]
            if v == 'X':
                unknown_keys.append(_key_of((r, c)))
            else:
                number_cells.append((r, c, int(v)))

    for (r, c, val) in number_cells:
        neigh = _get_neighbors(neighbor_mode, r, c, rows, cols)
        unk_keys = [_key_of((rr, cc)) for (rr, cc) in neigh if grid_data[rr][cc] == 'X']
        neighbors_unknown_keys.append(unk_keys)

    return {
        "unknown_keys": unknown_keys,
        "number_cells": number_cells,
        "neighbors_unknown_keys": neighbors_unknown_keys,
    }


def _normalize_weights(weights_raw: Dict[str, float]) -> Dict[str, float]:
    keys = ["neighbor_eq", "neighbor_zero", "group_eq", "group_atleast", "group_atmost", "group_all", "group_none", "balance", "weighted_eq"]
    s = sum(weights_raw.get(k, 0.0) for k in keys)
    if s <= 0:
        return {
            "neighbor_eq": 1.0,
            "neighbor_zero": 0.6,
            "group_eq": 1.0,
            "group_atleast": 0.8,
            "group_atmost": 0.8,
            "group_all": 0.5,
            "group_none": 0.5,
            "balance": 0.6,
            "weighted_eq": 0.8,
        }
    return {k: weights_raw.get(k, 0.0) / s for k in keys}


def _gen_rules(
    rng: random.Random,
    grid_data: List[List[Any]],
    infected: List[List[bool]],
    neighbor_mode: str,
    rule_min: int,
    rule_max: int,
    use_neighbor_rules: bool,
    use_group_rules: bool,
    weights_norm: Dict[str, float],
    group_size_min: int,
    group_size_max: int,
    text_style: str,
) -> Tuple[List[str], Dict[str, Any]]:
    rows = len(grid_data)
    cols = len(grid_data[0]) if rows > 0 else 0

    def text(fmt_concise: str, fmt_verbose: str) -> str:
        return fmt_concise if text_style == 'concise' else fmt_verbose

    base_structs = _collect_base_structures(grid_data, neighbor_mode)
    unknown_keys = base_structs["unknown_keys"]
    number_cells = base_structs["number_cells"]

    rules_desc: List[str] = []
    result_structs: Dict[str, Any] = {
        "group_rules_eq": [],
        "group_rules_atleast": [],
        "group_rules_atmost": [],
        "group_rules_all": [],
        "group_rules_none": [],
        "balance_rules": [],
        "weighted_rules": [],
    }

    neighbor_eq_cells = []
    neighbor_zero_cells = []
    for (r, c, val) in number_cells:
        neigh = _get_neighbors(neighbor_mode, r, c, rows, cols)
        unknown_neigh_coords = [(rr, cc) for (rr, cc) in neigh if grid_data[rr][cc] == 'X']
        if val == 0:
            neighbor_zero_cells.append((r, c, val, unknown_neigh_coords))
        if len(unknown_neigh_coords) == val and val > 0:
            neighbor_eq_cells.append((r, c, val, unknown_neigh_coords))

    def sample_group() -> List[Tuple[int, int]]:
        if not unknown_keys:
            return []
        lo = max(1, group_size_min)
        hi = max(lo, min(group_size_max, len(unknown_keys)))
        size = rng.randint(lo, hi)
        coords = rng.sample([_coord_of(k) for k in unknown_keys], size)
        return coords

    type_pool: List[str] = []
    if use_neighbor_rules:
        type_pool.extend(["neighbor_eq"] * int(100 * weights_norm["neighbor_eq"]))
        type_pool.extend(["neighbor_zero"] * int(100 * weights_norm["neighbor_zero"]))
    if use_group_rules:
        type_pool.extend(["group_eq"] * int(100 * weights_norm["group_eq"]))
        type_pool.extend(["group_atleast"] * int(100 * weights_norm["group_atleast"]))
        type_pool.extend(["group_atmost"] * int(100 * weights_norm["group_atmost"]))
        type_pool.extend(["group_all"] * int(100 * weights_norm["group_all"]))
        type_pool.extend(["group_none"] * int(100 * weights_norm["group_none"]))
        type_pool.extend(["balance"] * int(100 * weights_norm["balance"]))
        type_pool.extend(["weighted_eq"] * int(100 * weights_norm["weighted_eq"]))
    if not type_pool:
        type_pool = ["group_eq"]

    total_rules = rng.randint(rule_min, rule_max)

    for _ in range(total_rules):
        t = rng.choice(type_pool)

        if t == "neighbor_eq" and use_neighbor_rules and neighbor_eq_cells:
            r, c, val, unk_coords = rng.choice(neighbor_eq_cells)
            rules_desc.append(text(
                f"(邻域) 位置({r},{c})数字为{val}且其未知邻居数正好为{val}，这些未知邻居全部为感染。",
                f"(邻域规则) 在六角邻域中，位置({r},{c})显示数字{val}。其未知邻居数恰好等于{val}，因此这些未知邻居均为感染。"
            ))
            result_structs["group_rules_all"].append({"keys": [_key_of(rc) for rc in unk_coords]})
            continue

        if t == "neighbor_zero" and use_neighbor_rules and neighbor_zero_cells:
            r, c, val, unk_coords = rng.choice(neighbor_zero_cells)
            rules_desc.append(text(
                f"(邻域) 位置({r},{c})数字为0，其所有未知邻居均为安全。",
                f"(邻域规则) 位置({r},{c})的邻域感染计数为0，因此该位置所有未知邻居均不是感染。"
            ))
            result_structs["group_rules_none"].append({"keys": [_key_of(rc) for rc in unk_coords]})
            continue

        if t == "group_eq":
            group = sample_group()
            if not group:
                continue
            g_inf = sum(1 for (rr, cc) in group if infected[rr][cc])
            rules_desc.append(text(
                f"(集合) 集合{group}的感染数恰好为{g_inf}。",
                f"(集合规则) 对集合{group}，感染单元的数量恰好为{g_inf}。"
            ))
            result_structs["group_rules_eq"].append({"keys": [_key_of(rc) for rc in group], "k": g_inf})
            continue

        if t == "group_atleast":
            group = sample_group()
            if not group:
                continue
            g_inf = sum(1 for (rr, cc) in group if infected[rr][cc])
            rules_desc.append(text(
                f"(集合) 集合{group}中至少有{g_inf}个感染。",
                f"(集合规则) 对于集合{group}，我们可以确认至少存在{g_inf}个感染单元。"
            ))
            result_structs["group_rules_atleast"].append({"keys": [_key_of(rc) for rc in group], "k": g_inf})
            continue

        if t == "group_atmost":
            group = sample_group()
            if not group:
                continue
            g_inf = sum(1 for (rr, cc) in group if infected[rr][cc])
            rules_desc.append(text(
                f"(集合) 集合{group}中至多有{g_inf}个感染。",
                f"(集合规则) 对于集合{group}，感染单元的数量不超过{g_inf}。"
            ))
            result_structs["group_rules_atmost"].append({"keys": [_key_of(rc) for rc in group], "k": g_inf})
            continue

        if t == "group_all":
            group = sample_group()
            if not group:
                continue
            g_inf = sum(1 for (rr, cc) in group if infected[rr][cc])
            if g_inf == len(group):
                rules_desc.append(text(
                    f"(集合) 以下坐标全部为感染: {group}。",
                    f"(集合规则) 集合{group}中每一个坐标均为感染。"
                ))
                result_structs["group_rules_all"].append({"keys": [_key_of(rc) for rc in group]})
            continue

        if t == "group_none":
            group = sample_group()
            if not group:
                continue
            g_inf = sum(1 for (rr, cc) in group if infected[rr][cc])
            if g_inf == 0:
                rules_desc.append(text(
                    f"(集合) 以下坐标全部为安全: {group}。",
                    f"(集合规则) 集合{group}内不存在感染单元。"
                ))
                result_structs["group_rules_none"].append({"keys": [_key_of(rc) for rc in group]})
            continue

        if t == "balance":
            groupA = sample_group()
            groupB = sample_group()
            if not groupA or not groupB:
                continue
            a_inf = sum(1 for (rr, cc) in groupA if infected[rr][cc])
            b_inf = sum(1 for (rr, cc) in groupB if infected[rr][cc])
            if a_inf == b_inf:
                rules_desc.append(text(
                    f"(平衡) 两集合感染数相等: {groupA} 与 {groupB}。",
                    f"(平衡规则) 集合{groupA}与集合{groupB}的感染单元数量相同。"
                ))
                result_structs["balance_rules"].append({"A": [_key_of(rc) for rc in groupA], "B": [_key_of(rc) for rc in groupB]})
            continue

        if t == "weighted_eq":
            group = sample_group()
            if not group:
                continue
            weights = [rng.randint(1, 3) for _ in group]
            g_k = sum(w for ((rr, cc), w) in zip(group, weights) if infected[rr][cc])
            rules_desc.append(text(
                f"(加权) 权重和等式成立: ∑ w·感染 = {g_k}，集合{group}，权重{weights}。",
                f"(加权规则) 对集合{group}与权重{weights}，加权的感染计数之和恰好为{g_k}。"
            ))
            result_structs["weighted_rules"].append({"keys": [_key_of(rc) for rc in group], "weights": weights, "k": g_k})
            continue

    return rules_desc, result_structs


def _precheck_uniqueness_with_z3(
    unknown_keys: List[str],
    number_cells: List[Tuple[int, int, int]],
    neighbors_unknown_keys: List[List[str]],
    structs: Dict[str, Any],
    timeout_ms: int = 15000,
) -> bool:
    """用z3进行唯一解预验证：SAT一次，阻断再SAT，若第二次不可满足则唯一。"""
    if not Z3_AVAILABLE:
        return True

    bvars = {k: Bool(f"b_{k}") for k in unknown_keys}
    s = Solver()
    s.set("timeout", timeout_ms)

    # 数字邻域约束
    for i, (r, c, val) in enumerate(number_cells):
        neigh_keys = neighbors_unknown_keys[i]
        s.add(Z3Sum([Z3If(bvars[k], 1, 0) for k in neigh_keys]) == val)

    # group_eq
    for rule in structs.get("group_rules_eq", []):
        keys = rule["keys"]; k = rule["k"]
        s.add(Z3Sum([Z3If(bvars[key], 1, 0) for key in keys]) == k)

    # group_atleast/atmost
    for rule in structs.get("group_rules_atleast", []):
        keys = rule["keys"]; k = rule["k"]
        s.add(Z3Sum([Z3If(bvars[key], 1, 0) for key in keys]) >= k)
    for rule in structs.get("group_rules_atmost", []):
        keys = rule["keys"]; k = rule["k"]
        s.add(Z3Sum([Z3If(bvars[key], 1, 0) for key in keys]) <= k)

    # group_all/group_none
    for rule in structs.get("group_rules_all", []):
        s.add(Z3And([bvars[key] for key in rule["keys"]]))
    for rule in structs.get("group_rules_none", []):
        s.add(Z3Sum([Z3If(bvars[key], 1, 0) for key in rule["keys"]]) == 0)

    # balance
    for rule in structs.get("balance_rules", []):
        Ak = rule["A"]; Bk = rule["B"]
        s.add(Z3Sum([Z3If(bvars[key], 1, 0) for key in Ak]) == Z3Sum([Z3If(bvars[key], 1, 0) for key in Bk]))

    # weighted_eq
    for rule in structs.get("weighted_rules", []):
        keys = rule["keys"]; weights = rule["weights"]; k = rule["k"]
        s.add(Z3Sum([weights[i] * Z3If(bvars[keys[i]], 1, 0) for i in range(len(keys))]) == k)

    # 第一次求解
    if s.check() != sat:
        return False

    # 若没有未知变量，直接视为唯一解（约束仅常量）
    if not unknown_keys:
        return True

    m = s.model()
    # 添加阻断约束：至少有一个变量与当前模型不同
    diff_literals = []
    for k in unknown_keys:
        v = m.eval(bvars[k], model_completion=True)
        # 构造 bvars[k] != v 的字面，v 是 BoolVal(True/False)
        diff_literals.append(bvars[k] != v)
    s.push()
    s.add(Or(diff_literals))
    second = s.check()
    s.pop()
    return second != sat  # 第二次不可满足 => 唯一


def function_2(
    rows: int,
    cols: int,
    neighbor_mode: str,
    inf_prob: float,
    mask_safe_prob: float,
    seed: Optional[int],
    ensure_forced_min: int,
    max_attempts: int,
    rule_min: int,
    rule_max: int,
    use_neighbor_rules: bool,
    use_group_rules: bool,
    w_neighbor_eq: float,
    w_neighbor_zero: float,
    w_group_eq: float,
    w_group_atleast: float,
    w_group_atmost: float,
    w_group_all: float,
    w_group_none: float,
    w_balance: float,
    w_weighted_eq: float,
    group_size_min: int,
    group_size_max: int,
    text_style: str,
) -> Dict[str, Any]:
    """
    正向生成器：
    - 生成底层感染图；
    - 计算邻域计数；
    - 构造题面显示；
    - 随机生成复合规则并进行唯一性预验证；
    - 若强推不足或不唯一，逐步提高强约束倾向重试；
    - 返回题面与约束结构。
    """
    rng = random.Random(seed)

    def gen_once(tighten: bool = False) -> Dict[str, Any]:
        infected = [[rng.random() < inf_prob for _ in range(cols)] for _ in range(rows)]
        counts = _compute_counts(infected, neighbor_mode)
        grid_data = _build_display_grid(infected, counts, mask_safe_prob, rng)

        base = _collect_base_structures(grid_data, neighbor_mode)
        unknown_keys = base["unknown_keys"]
        number_cells = base["number_cells"]
        neighbors_unknown_keys = base["neighbors_unknown_keys"]

        weights_raw = {
            "neighbor_eq": w_neighbor_eq if not tighten else max(w_neighbor_eq, 0.9),
            "neighbor_zero": w_neighbor_zero,
            "group_eq": w_group_eq if not tighten else max(w_group_eq, 0.9),
            "group_atleast": w_group_atleast,
            "group_atmost": w_group_atmost,
            "group_all": w_group_all,
            "group_none": w_group_none,
            "balance": w_balance,
            "weighted_eq": w_weighted_eq if not tighten else max(w_weighted_eq, 0.8),
        }
        weights_norm = _normalize_weights(weights_raw)

        rules_desc, structs = _gen_rules(
            rng, grid_data, infected, neighbor_mode, rule_min, rule_max,
            use_neighbor_rules, use_group_rules,
            weights_norm, group_size_min, group_size_max, text_style
        )

        # 强推集合计数（题面引导，不回传）
        forced_set: set = set()
        for rule in structs["group_rules_all"]:
            for k in rule["keys"]:
                forced_set.add(_coord_of(k))
        for rule in structs["group_rules_atleast"]:
            if len(rule["keys"]) == 1 and rule["k"] >= 1:
                forced_set.add(_coord_of(rule["keys"][0]))
        forced_count = len(forced_set)

        is_unique = _precheck_uniqueness_with_z3(unknown_keys, number_cells, neighbors_unknown_keys, structs, timeout_ms=15000)

        return {
            "grid_data": grid_data,
            "unknown_keys": unknown_keys,
            "number_cells": number_cells,
            "neighbors_unknown_keys": neighbors_unknown_keys,
            "infected_truth_coords": [(r, c) for r in range(rows) for c in range(cols) if infected[r][c]],
            "rules_desc": rules_desc,
            "group_rules_eq": structs["group_rules_eq"],
            "group_rules_atleast": structs["group_rules_atleast"],
            "group_rules_atmost": structs["group_rules_atmost"],
            "group_rules_all": structs["group_rules_all"],
            "group_rules_none": structs["group_rules_none"],
            "balance_rules": structs["balance_rules"],
            "weighted_rules": structs["weighted_rules"],
            "_is_unique": is_unique,
            "_forced_count": forced_count,
        }

    best = None
    for attempt in range(max_attempts):
        tighten = (attempt >= max_attempts // 2)
        cur = gen_once(tighten=tighten)
        if cur["_is_unique"] and cur["_forced_count"] >= ensure_forced_min:
            best = cur
            break
        best = cur

    if best is None:
        best = gen_once(tighten=True)
    best.pop("_is_unique", None)
    best.pop("_forced_count", None)
    return best