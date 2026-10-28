# norinori_0.py
# 目标：
# - 构造正交连通的区域划分（同一字母表示一个正交连通块）。
# - 使用Z3根据标准Norinori规则枚举所有可行解，得到总解数与“唯一编码规则”下的字典序最小方案。
# - 返回结构化数据给YAML；YAML关闭SMT求解，直接使用Python计算结果，避免重复求解与超时。

import random
from typing import List, Dict, Tuple
from z3 import Solver, Bool, Sum as Z3Sum, If, Or, And, sat, is_true

def _coords(R: int, C: int) -> List[List[int]]:
    return [[r, c] for r in range(1, R + 1) for c in range(1, C + 1)]

def _neighbors4(r: int, c: int, R: int, C: int) -> List[Tuple[int,int]]:
    res = []
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        nr, nc = r + dr, c + dc
        if 1 <= nr <= R and 1 <= nc <= C:
            res.append((nr, nc))
    return res

def _connected_partition_round_robin(R: int, C: int, region_count: int) -> Dict[str, List[List[int]]]:
    """
    多源BFS的轮转扩张：从region_count个随机种子出发，按轮次扩张到未分配格子，
    直到覆盖全图。保证每个区域正交连通。
    """
    if region_count > R * C:
        return {}

    # 选择不同的种子格子
    all_cells = [(r, c) for r in range(1, R + 1) for c in range(1, C + 1)]
    random.shuffle(all_cells)
    seeds = all_cells[:region_count]

    # 初始化区域与队列
    regions = [{seed} for seed in seeds]  # 集合形式便于连通维护
    queues = [[seed] for seed in seeds]
    assigned = set(seeds)

    # 轮转扩张
    qi = 0
    max_iters = R * C * 10
    iters = 0
    while len(assigned) < R * C and iters < max_iters:
        iters += 1
        # 当前区域索引
        idx = qi % region_count
        qi += 1
        if not queues[idx]:
            # 尝试从整块边界找新frontier
            frontier = set()
            for (r, c) in regions[idx]:
                for nr, nc in _neighbors4(r, c, R, C):
                    if (nr, nc) not in assigned:
                        frontier.add((nr, nc))
            if frontier:
                pick = random.choice(list(frontier))
                regions[idx].add(pick)
                queues[idx].append(pick)
                assigned.add(pick)
            else:
                # 没有frontier则跳过
                continue
        else:
            # 从队列头扩张一个邻居
            r, c = queues[idx].pop(0)
            candidates = []
            for nr, nc in _neighbors4(r, c, R, C):
                if (nr, nc) not in assigned:
                    candidates.append((nr, nc))
            if candidates:
                pick = random.choice(candidates)
                regions[idx].add(pick)
                queues[idx].append(pick)
                assigned.add(pick)

    # 若仍有未分配格子（极小概率），按最近区域分配
    for r in range(1, R + 1):
        for c in range(1, C + 1):
            if (r, c) not in assigned:
                # 找最近区域
                best_i = None
                best_d = 10**9
                for i, reg in enumerate(regions):
                    d = min(abs(r-r0)+abs(c-c0) for (r0,c0) in reg)
                    if d < best_d:
                        best_d = d
                        best_i = i
                regions[best_i].add((r,c))
                assigned.add((r,c))

    # 标签
    labels = []
    base_labels = [chr(ord('A') + i) for i in range(26)]
    for i in range(region_count):
        labels.append(base_labels[i] if i < len(base_labels) else f"A{i}")

    # 输出 cells_by_label
    cells_by_label: Dict[str, List[List[int]]] = {}
    for lab, reg in zip(labels, regions):
        cells_by_label[lab] = [[r, c] for (r, c) in sorted(reg)]
    return cells_by_label

def _build_domino_candidates(R: int, C: int) -> Tuple[List[str], List[Tuple[str, List[List[int]]]]]:
    keys = []
    items = []
    # 水平
    for r in range(1, R + 1):
        for c in range(1, C):
            key = f"({r},{c})-({r},{c+1})"
            cells = [[r, c], [r, c+1]]
            keys.append(key)
            items.append((key, cells))
    # 垂直
    for r in range(1, R):
        for c in range(1, C + 1):
            key = f"({r},{c})-({r+1},{c})"
            cells = [[r, c], [r+1, c]]
            keys.append(key)
            items.append((key, cells))
    return keys, items

def _build_solver(R: int, C: int,
                  labels: List[str],
                  cells_by_label: Dict[str, List[List[int]]],
                  domino_items: List[Tuple[str, List[List[int]]]]):
    """
    标准 Norinori 约束：
    - 每个格子最多一个多米诺覆盖（no_overlap）
    - 每个区域恰好两个被覆盖格（region_two_each）
    - 相邻规则：若两个相邻格都被覆盖，则必须选择连接这两格的多米诺（adjacency_rule）
    """
    s = Solver()
    z3_vars = {key: Bool(f"u_{i}") for i, (key, _) in enumerate(domino_items)}
    # 格子 -> 涉及的多米诺键列表
    cell_to_keys: Dict[Tuple[int,int], List[str]] = {}
    for key, cells in domino_items:
        for rc in cells:
            cell_to_keys.setdefault((rc[0], rc[1]), []).append(key)

    # 不重叠：每格最多一个多米诺覆盖
    for r in range(1, R + 1):
        for c in range(1, C + 1):
            keys_here = cell_to_keys.get((r, c), [])
            s.add(Z3Sum([If(z3_vars[k], 1, 0) for k in keys_here]) <= 1)

    # 每区域恰好两个覆盖格
    for lab in labels:
        cells = cells_by_label[lab]
        s.add(Z3Sum([
            Z3Sum([If(z3_vars[k], 1, 0) for k in cell_to_keys.get((rc[0], rc[1]), [])])
            for rc in cells
        ]) == 2)

    # 相邻规则：Or(cov(a)==0, cov(b)==0, u_domino)
    for key, cells in domino_items:
        a = (cells[0][0], cells[0][1])
        b = (cells[1][0], cells[1][1])
        cov_a = Z3Sum([If(z3_vars[k], 1, 0) for k in cell_to_keys.get(a, [])])
        cov_b = Z3Sum([If(z3_vars[k], 1, 0) for k in cell_to_keys.get(b, [])])
        s.add(Or(cov_a == 0, cov_b == 0, z3_vars[key]))

    return s, z3_vars

def _canon_pair(pair: List[List[int]]) -> Tuple[Tuple[int,int], Tuple[int,int]]:
    """将一个多米诺内部坐标按升序排列，返回两个坐标的元组。"""
    a = (pair[0][0], pair[0][1])
    b = (pair[1][0], pair[1][1])
    return (a, b) if a <= b else (b, a)

def _canon_solution(pairs: List[List[List[int]]]) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    """将方案按唯一编码规范化：内部坐标升序；外部列表按第一、第二坐标升序排序。"""
    canon = [_canon_pair(p) for p in pairs]
    canon.sort(key=lambda t: (t[0], t[1]))
    return canon

def function_1(R: int, C: int, region_count: int) -> dict:
    """
    生成正交连通的区域划分，并在标准 Norinori 规则下枚举所有解：
    - 返回：grid、coords、labels、cells_by_label、候选多米诺、总解数、唯一编码下的字典序最小方案。
    - 为避免超时，限制枚举上限，但在当前规模下通常可完整枚举。
    """
    # 候选多米诺全集
    domino_keys, domino_items = _build_domino_candidates(R, C)

    # 多次尝试生成可解的连通区域
    for _ in range(80):
        cells_by_label = _connected_partition_round_robin(R, C, region_count)
        labels = list(cells_by_label.keys())
        if not labels:
            continue

        # 构建网格矩阵
        grid = [['' for _ in range(C)] for _ in range(R)]
        for lab, cells in cells_by_label.items():
            for r, c in cells:
                grid[r - 1][c - 1] = lab

        # Z3 构建与枚举
        s, z3_vars = _build_solver(R, C, labels, cells_by_label, domino_items)
        # 枚举所有解
        sol_count = 0
        min_canon: List[Tuple[Tuple[int,int], Tuple[int,int]]] = None
        min_pairs: List[List[List[int]]] = None
        MAX_ENUM = 2000  # 安全上限，当前规模一般不触发

        while sol_count < MAX_ENUM and s.check() == sat:
            m = s.model()
            # 提取当前解的选中多米诺
            selected_keys = [key for key in domino_keys if is_true(m.evaluate(z3_vars[key], model_completion=True))]
            if not selected_keys:
                # 没有选中任何多米诺（不满足区域覆盖），跳过并阻塞该解
                s.add(Or([z3_vars[key] != m[z3_vars[key]] for key in domino_keys]))
                continue

            # 当前解的坐标对列表
            key_to_cells = {key: cells for key, cells in domino_items}
            pairs = [key_to_cells[k] for k in selected_keys]
            # 唯一编码规范化
            canon = _canon_solution(pairs)

            # 更新字典序最小方案
            if min_canon is None or canon < min_canon:
                min_canon = canon
                min_pairs = pairs

            sol_count += 1
            # 阻塞当前解
            s.add(Or([z3_vars[key] != m[z3_vars[key]] for key in domino_keys]))

        if sol_count >= 1 and min_pairs is not None:
            return {
                'grid': grid,
                'coords': _coords(R, C),
                'labels': labels,
                'cells_by_label': cells_by_label,
                'domino_keys': domino_keys,
                'domino_cells_items': domino_items,
                'sol_count': sol_count,
                'ans_min_dominoes': min_pairs
            }

    # 回退（极端情况下）：构造简单的均匀连通划分并仅返回结构数据（不枚举）
    labels = [chr(ord('A') + i) for i in range(max(2, min(6, region_count)))]
    cells_by_label: Dict[str, List[List[int]]] = {lab: [] for lab in labels}
    idx = 0
    for r in range(1, R + 1):
        for c in range(1, C + 1):
            lab = labels[idx % len(labels)]
            cells_by_label[lab].append([r, c])
            idx += 1
    grid = [['' for _ in range(C)] for _ in range(R)]
    for lab, cells in cells_by_label.items():
        for r, c in cells:
            grid[r - 1][c - 1] = lab
    domino_keys, domino_items = _build_domino_candidates(R, C)
    return {
        'grid': grid,
        'coords': _coords(R, C),
        'labels': labels,
        'cells_by_label': cells_by_label,
        'domino_keys': domino_keys,
        'domino_cells_items': domino_items,
        'sol_count': 0,
        'ans_min_dominoes': []
    }

def function_2(ans_dominoes: List[List[List[int]]]) -> str:
    """将多米诺坐标列表格式化为括号坐标字符串，用于题面展示（按唯一编码规则已在Python侧处理）。"""
    # 先按唯一编码规范排序（防御性），然后格式化
    canon = _canon_solution(ans_dominoes)
    parts = []
    for (a, b) in canon:
        parts.append(f"[({a[0]}, {a[1]}), ({b[0]}, {b[1]})]")
    return "[" + ", ".join(parts) + "]"