# norinori_0.py
# -*- coding: utf-8 -*-
"""
高级广义 Norinori 生成器与工具（改进版）
- build_norinori_instance(n_rows, n_cols): 随机生成满足规则的实例（网格标签、唯一解、复合线索与可见性标记）。
- format_rules(...): 生成清晰一致的规则与线索文本（含“一格至多属于一块多米诺”的基础限制）。
- function_1(grid_labels, cell): 取1基坐标的区域标签字符。
- function_2(domino_list, grid_labels): 多米诺列表规范化与稳定排序（仅用于答案展示）。
"""

import random
from typing import List, Tuple, Dict

Cell = Tuple[int, int]
Domino = Tuple[Cell, Cell]


def _neighbors4(cell: Cell) -> List[Cell]:
    r, c = cell
    return [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]


def _neighbors_diag(cell: Cell) -> List[Cell]:
    r, c = cell
    return [(r - 1, c - 1), (r - 1, c + 1), (r + 1, c - 1), (r + 1, c + 1)]


def _in_bounds(cell: Cell, n_rows: int, n_cols: int) -> bool:
    r, c = cell
    return 1 <= r <= n_rows and 1 <= c <= n_cols


def _candidate_edges(n_rows: int, n_cols: int) -> List[Domino]:
    edges = []
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols):
            edges.append(((r, c), (r, c + 1)))
    for r in range(1, n_rows):
        for c in range(1, n_cols + 1):
            edges.append(((r, c), (r + 1, c)))
    return edges


def _select_edges_with_mode(n_rows: int, n_cols: int, adjacency_mode: str) -> List[Domino]:
    """
    按接触策略选择不冲突的边集合（贪心 + 禁区扩张）。
    """
    edges = _candidate_edges(n_rows, n_cols)
    random.shuffle(edges)

    forbid: set = set()

    def expand_forbid(c: Cell):
        cells = {c}
        if adjacency_mode in ('no_orth', 'no_orth_and_diag'):
            cells.update([x for x in _neighbors4(c) if _in_bounds(x, n_rows, n_cols)])
        if adjacency_mode in ('no_diag', 'no_orth_and_diag'):
            cells.update([x for x in _neighbors_diag(c) if _in_bounds(x, n_rows, n_cols)])
        return cells

    selected: List[Domino] = []
    for e in edges:
        a, b = e
        if a in forbid or b in forbid:
            continue
        selected.append(e)
        forbid.update(expand_forbid(a))
        forbid.update(expand_forbid(b))

    # 若数量偏少，放宽一次（仅检查端点不在禁区）
    min_need = max(2, (n_rows * n_cols) // 6)
    if len(selected) < min_need:
        edges2 = _candidate_edges(n_rows, n_cols)
        random.shuffle(edges2)
        for e in edges2:
            a, b = e
            if a in forbid or b in forbid:
                continue
            selected.append(e)
            forbid.update(expand_forbid(a))
            forbid.update(expand_forbid(b))
            if len(selected) >= min_need:
                break

    return selected


def build_norinori_instance(n_rows: int, n_cols: int) -> Dict[str, object]:
    """
    逆向构造一个满足多层次随机规则的实例：
    - 随机选择 adjacency_mode ∈ {no_orth, no_diag, no_orth_and_diag, allow_all}
    - 随机选择 x_policy ∈ {must_use, forbid, optional}
    - 随机选择 cover_per_region ∈ {1,2,3}
    - 按模式筛选不冲突的边集 answer_edges
    - 构造区域标签与网格，确保每区恰有K个覆盖格；按策略分配X（与区域计数一致）
    - 生成复合线索：行/列覆盖计数（最多展示2行2列）、H/V计数、跨区计数、棋盘黑格覆盖计数，并随机选择最多2项高级线索展示
    """
    adjacency_mode = random.choice(['no_orth', 'no_diag', 'no_orth_and_diag', 'allow_all'])
    x_policy = random.choice(['must_use', 'forbid', 'optional'])
    cover_per_region = random.choice([1, 2, 3])

    answer_edges = _select_edges_with_mode(n_rows, n_cols, adjacency_mode)

    covered_cells: List[Cell] = []
    for (a, b) in answer_edges:
        covered_cells.append(a)
        covered_cells.append(b)

    attempts = 0
    while len(covered_cells) < cover_per_region * 2 and attempts < 3:
        answer_edges = _select_edges_with_mode(n_rows, n_cols, adjacency_mode)
        covered_cells = []
        for (a, b) in answer_edges:
            covered_cells.append(a)
            covered_cells.append(b)
        attempts += 1

    max_regions_possible = max(1, min(10, len(covered_cells) // max(cover_per_region, 1)))
    num_regions = random.randint(1, max_regions_possible)

    alphabet = [chr(ord('A') + i) for i in range(26)]
    random.shuffle(alphabet)
    region_labels = alphabet[:num_regions] if num_regions > 0 else ['A']

    random.shuffle(covered_cells)
    needed = cover_per_region * num_regions
    reserve = covered_cells[:needed]
    leftovers = covered_cells[needed:]

    region_cov: Dict[str, List[Cell]] = {lab: [] for lab in region_labels}
    ptr = 0
    for lab in region_labels:
        region_cov[lab] = reserve[ptr: ptr + cover_per_region]
        ptr += cover_per_region

    default_lab = region_labels[0] if region_labels else 'A'
    grid_labels: List[List[str]] = [[default_lab for _ in range(n_cols)] for _ in range(n_rows)]

    for lab, cells in region_cov.items():
        for (r, c) in cells:
            grid_labels[r - 1][c - 1] = lab

    # X 策略一致性
    if x_policy == 'forbid':
        if leftovers:
            x_policy = 'optional'
            for (r, c) in leftovers:
                grid_labels[r - 1][c - 1] = 'X'
    else:
        for (r, c) in leftovers:
            grid_labels[r - 1][c - 1] = 'X'

    covered_set = set(covered_cells)
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            if (r, c) in covered_set:
                continue
            grid_labels[r - 1][c - 1] = random.choice(region_labels)

    # 线索生成
    def covered_count_in_row(row: int) -> int:
        return sum(1 for (rr, cc) in covered_cells if rr == row)

    def covered_count_in_col(col: int) -> int:
        return sum(1 for (rr, cc) in covered_cells if cc == col)

    all_rows = list(range(1, n_rows + 1))
    all_cols = list(range(1, n_cols + 1))
    random.shuffle(all_rows)
    random.shuffle(all_cols)
    row_sel_num = random.randint(1, min(2, n_rows))
    col_sel_num = random.randint(1, min(2, n_cols))
    row_targets = [(r, covered_count_in_row(r)) for r in all_rows[:row_sel_num]]
    col_targets = [(c, covered_count_in_col(c)) for c in all_cols[:col_sel_num]]

    h_target = sum(1 for (a, b) in answer_edges if a[0] == b[0])
    v_target = sum(1 for (a, b) in answer_edges if a[1] == b[1])

    def lab(cell: Cell) -> str:
        return grid_labels[cell[0] - 1][cell[1] - 1]

    cross_target = sum(1 for (a, b) in answer_edges if lab(a) != lab(b))
    black_target = sum(1 for (r, c) in covered_cells if (r + c) % 2 == 0)

    # 高级线索可见性：最多展示2项
    advanced = ['orientation', 'cross', 'black']
    random.shuffle(advanced)
    show_k = random.choice([0, 1, 2])
    chosen = set(advanced[:show_k])
    use_orientation = 'orientation' in chosen
    use_cross = 'cross' in chosen
    use_black = 'black' in chosen

    return {
        'grid_labels': grid_labels,
        'answer_edges': answer_edges,
        'adjacency_mode': adjacency_mode,
        'x_policy': x_policy,
        'cover_per_region': cover_per_region,
        'row_targets': row_targets,
        'col_targets': col_targets,
        'h_target': h_target,
        'v_target': v_target,
        'cross_target': cross_target,
        'black_target': black_target,
        'use_orientation': use_orientation,
        'use_cross': use_cross,
        'use_black': use_black,
    }


def format_rules(adjacency_mode: str, x_policy: str, cover_per_region: int,
                 row_targets: List[Tuple[int, int]], col_targets: List[Tuple[int, int]],
                 h_target: int, v_target: int, cross_target: int, black_target: int,
                 use_orientation: bool, use_cross: bool, use_black: bool) -> str:
    """
    生成清晰一致的规则与线索文本，包含基础定义与启用线索；解释沿边/对角相邻；明确“一格至多属于一块多米诺”。
    """
    adj_text = {
        'no_orth': '不同多米诺不得沿边相邻（沿边相邻指上下或左右相邻；允许对角接触）',
        'no_diag': '不同多米诺不得在对角方向相邻（对角相邻指斜对角接触；允许沿边相邻）',
        'no_orth_and_diag': '不同多米诺既不得沿边相邻，也不得在对角方向相邻',
        'allow_all': '不同多米诺之间接触不作限制',
    }[adjacency_mode]

    x_text = {
        'must_use': '所有标记为X的格子都必须属于某个多米诺',
        'forbid': '所有标记为X的格子都不得属于任何多米诺',
        'optional': '标记为X的格子是否属于多米诺不作强制要求',
    }[x_policy]

    base = (f'同一字母表示同一个区域，不同字母表示不同区域；每个区域恰有{cover_per_region}个格子被多米诺覆盖；'
            f'一格至多属于一块多米诺；{adj_text}；{x_text}。')

    hints = []
    if row_targets:
        hints.append('；'.join([f'第{r}行覆盖数为{t}' for (r, t) in row_targets]))
    if col_targets:
        hints.append('；'.join([f'第{c}列覆盖数为{t}' for (c, t) in col_targets]))
    if use_orientation:
        hints.append(f'水平多米诺数量为{h_target}、垂直多米诺数量为{v_target}')
    if use_cross:
        hints.append(f'跨区域的多米诺数量为{cross_target}')
    if use_black:
        hints.append(f'棋盘黑格被覆盖的数量为{black_target}')
    hint_text = '；'.join(hints) if hints else '无额外线索'

    tail = ('多米诺为1×2或2×1的矩形块，可跨越区域边界。'
            '答案格式为 [[(r1,c1),(r1,c2)],[(r2,c1),(r2,c2)],...]，坐标从1开始。')

    return f'{base}附加线索：{hint_text}。{tail}'


def function_1(grid_labels: List[List[str]], cell: Cell) -> str:
    r, c = cell
    return grid_labels[r - 1][c - 1]


def _normalize_domino(e: Domino) -> Domino:
    a, b = e
    return (a, b) if a <= b else (b, a)


def function_2(domino_list: List[Domino], grid_labels: List[List[str]]) -> List[Domino]:
    """
    对求解得到的多米诺列表进行端点规范化与稳定排序：
    1) 端点标签优先级：X 最优先，其次 A..Z，其余字符靠后（取两端点的最小优先级）；
    2) 再按坐标字典序排序（先行后列）。
    """
    def label_rank(cell: Cell) -> int:
        ch = function_1(grid_labels, cell)
        if ch == 'X':
            return 0
        if 'A' <= ch <= 'Z':
            return ord(ch) - ord('A') + 1
        return 100

    normed = [_normalize_domino(e) for e in domino_list]

    def sort_key(e: Domino):
        a, b = e
        prio = min(label_rank(a), label_rank(b))
        return (prio, a, b)

    normed.sort(key=sort_key)
    return normed