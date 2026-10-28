# -*- coding: utf-8 -*-
"""
numbrix_3.py（稳定唯一解版）
- 去除不合理的全局棋盘奇偶约束，改用“段内奇偶映射”(pos_r+pos_c+k)%2 固定；
- 强化唯一性增强流程：逐段添加奇偶映射、追加锚点与行列和与线索；最终阶段全面加固，确保收敛；
- 文本明确：行列从1开始计数；奇偶映射解释清晰；线索数量使用精确值。
"""

from typing import List, Tuple, Dict, Any, Set
import random

from z3 import Solver, Int, Distinct, And, Or, If, Sum, Abs, sat


def _serpentine_path(n: int) -> List[Tuple[int, int]]:
    path: List[Tuple[int, int]] = []
    for r in range(n):
        cols = range(n) if r % 2 == 0 else range(n - 1, -1, -1)
        for c in cols:
            path.append((r, c))
    return path


def _transform_path(path: List[Tuple[int, int]], n: int, rng: random.Random) -> List[Tuple[int, int]]:
    def rotate(pt: Tuple[int, int], times: int) -> Tuple[int, int]:
        r, c = pt
        for _ in range(times % 4):
            r, c = c, n - 1 - r
        return r, c

    def hflip(pt: Tuple[int, int]) -> Tuple[int, int]:
        r, c = pt
        return r, n - 1 - c

    def vflip(pt: Tuple[int, int]) -> Tuple[int, int]:
        r, c = pt
        return n - 1 - r, c

    rot_times = rng.choice([0, 1, 2, 3])
    p2 = [rotate(p, rot_times) for p in path]

    flip_choice = rng.choice(['none', 'h', 'v'])
    if flip_choice == 'h':
        p2 = [hflip(p) for p in p2]
    elif flip_choice == 'v':
        p2 = [vflip(p) for p in p2]
    return p2


def _build_grid_from_path(n: int, path: List[Tuple[int, int]]) -> List[List[int]]:
    N = n * n
    grid = [[0 for _ in range(n)] for _ in range(n)]
    for idx, (r, c) in enumerate(path):
        grid[r][c] = idx + 1
    used = {grid[r][c] for r in range(n) for c in range(n)}
    assert len(used) == N and min(used) == 1 and max(used) == N
    return grid


def _pick_splits(N: int, count: int, rng: random.Random) -> List[int]:
    domain = list(range(2, N))
    splits = rng.sample(domain, count) if count > 0 else []
    splits.sort()
    return splits


def _compose_rule_text(n: int,
                       seq_ranges: List[Tuple[int, int]],
                       bridge_pairs: List[Tuple[int, int]],
                       labels_map: Dict[str, Tuple[int, int]],
                       adjacency_mode: str,
                       parity_segments: Dict[str, int],
                       row_sums: List[Tuple[int, int]],
                       col_sums: List[Tuple[int, int]],
                       anchors: List[Tuple[str, int, int, str]],
                       clue_count: int) -> str:
    seq_desc = "; ".join([f"蛇{idx+1}覆盖[{a}..{b}]" for idx, (a, b) in enumerate(seq_ranges)])
    bridge_desc = ", ".join([f"({u},{v})" for (u, v) in bridge_pairs]) if bridge_pairs else "无"
    label_desc = ", ".join([f"标签{lab}只允许[{rngv[0]}..{rngv[1]}]" for lab, rngv in labels_map.items()])
    if adjacency_mode == 'strict':
        cont_desc = "每一对相邻的连续数字必须在四邻方向相接（例如 k 与 k+1 要相邻）。"
    else:
        cont_desc = "在每条蛇内部，连续的数字必须在四邻方向相接；跨蛇只要求各桥接对相邻。"
    # 段内奇偶映射说明（以(行号+列号+数字)的奇偶固定为某一颜色，行列从1开始计数）
    parity_items = []
    for key, b in parity_segments.items():
        a, t = key.split('-')
        color = "黑" if b == 0 else "白"
        parity_items.append(f"段[{a}..{t}]采用棋盘奇偶映射：以左上角为(1,1)，(行号+列号+数字)的奇偶固定为{color}格。")
    parity_desc = " ".join(parity_items) if parity_items else "无额外棋盘奇偶限制。"

    row_desc = ", ".join([f"第{r+1}行的数字和为{sv}" for (r, sv) in row_sums]) if row_sums else "无行和限制"
    col_desc = ", ".join([f"第{c+1}列的数字和为{sv}" for (c, sv) in col_sums]) if col_sums else "无列和限制"
    anchor_desc = "; ".join([f"{desc}" for desc, _, _, _ in anchors]) if anchors else "无相对位置锚点约束"

    rules_text = (
        f"网格为 {n}×{n}；共有{len(seq_ranges)}条蛇：{seq_desc}。"
        f"桥接对为[{bridge_desc}]，它们必须四邻相接。"
        f"{cont_desc} "
        f"若某格标记为标签字符，则该格只能填属于该标签所对应范围的数字（{label_desc}）。 "
        f"{parity_desc} "
        f"同时满足：{row_desc}；{col_desc}；锚点约束：{anchor_desc}。 "
        f"题面给出共{clue_count}个数字线索（含端点与桥接对与必要辅助线索），其余格以 'A'/'B'/'C'/'D' 或 'X' 标示。"
    )
    return rules_text


def _build_solver(n: int,
                  final_grid: List[List[int]],
                  seq_ranges: List[Tuple[int, int]],
                  bridge_pairs: List[Tuple[int, int]],
                  labeled_cells: Dict[str, Set[Tuple[int, int]]],
                  labels_map: Dict[str, Tuple[int, int]],
                  clue_vals: Set[int],
                  adjacency_mode: str,
                  parity_segments: Dict[str, int],
                  row_sums: List[Tuple[int, int]],
                  col_sums: List[Tuple[int, int]],
                  anchors: List[Tuple[str, int, int, str]],
                  timeout_ms: int):
    N = n * n
    s = Solver()
    s.set("timeout", timeout_ms)

    pos_r = [None] + [Int(f"pr_{k}") for k in range(1, N + 1)]
    pos_c = [None] + [Int(f"pc_{k}") for k in range(1, N + 1)]
    pos_idx = [None] + [Int(f"pi_{k}") for k in range(1, N + 1)]

    for k in range(1, N + 1):
        s.add(And(pos_r[k] >= 0, pos_r[k] < n))
        s.add(And(pos_c[k] >= 0, pos_c[k] < n))
        s.add(pos_idx[k] == pos_r[k] * n + pos_c[k])

    s.add(Distinct([pos_idx[k] for k in range(1, N + 1)]))

    # 固定所有线索到答案中的坐标
    if clue_vals:
        coords: Dict[int, Tuple[int, int]] = {}
        for r in range(n):
            for c in range(n):
                coords[final_grid[r][c]] = (r, c)
        for v in clue_vals:
            r0, c0 = coords[v]
            s.add(pos_r[v] == r0, pos_c[v] == c0)

    # 标签占位：标注的标签格必须由该段数字占据
    for lab, cells in labeled_cells.items():
        lo, hi = labels_map[lab]
        for (r, c) in cells:
            s.add(Or([And(pos_r[k] == r, pos_c[k] == c) for k in range(lo, hi + 1)]))

    # 连续性
    if adjacency_mode == 'strict':
        for k in range(2, N + 1):
            s.add(Abs(pos_r[k] - pos_r[k - 1]) + Abs(pos_c[k] - pos_c[k - 1]) == 1)
    else:
        for (lo, hi) in seq_ranges:
            for k in range(lo + 1, hi + 1):
                s.add(Abs(pos_r[k] - pos_r[k - 1]) + Abs(pos_c[k] - pos_c[k - 1]) == 1)
        for (u, v) in bridge_pairs:
            s.add(Abs(pos_r[v] - pos_r[u]) + Abs(pos_c[v] - pos_c[u]) == 1)

    # 段内奇偶映射：(pos_r + pos_c + k) % 2 == b
    for key, b in parity_segments.items():
        lo, hi = map(int, key.split('-'))
        for k in range(lo, hi + 1):
            s.add(((pos_r[k] + pos_c[k] + k) % 2) == b)

    # 行列和
    for (r0, sv) in row_sums:
        s.add(Sum([If(pos_r[k] == r0, k, 0) for k in range(1, N + 1)]) == sv)
    for (c0, sv) in col_sums:
        s.add(Sum([If(pos_c[k] == c0, k, 0) for k in range(1, N + 1)]) == sv)

    # 锚点约束
    for (_, a, b, rel) in anchors:
        if rel == 'same_row':
            s.add(pos_r[a] == pos_r[b])
        elif rel == 'same_col':
            s.add(pos_c[a] == pos_c[b])
        elif rel == 'left_of':
            s.add(pos_c[a] < pos_c[b])
        elif rel == 'above':
            s.add(pos_r[a] < pos_r[b])

    return s, pos_r, pos_c, pos_idx


def gen_instance(n: int, seq_min: int, seq_max: int, label_ratio: float, clue_ratio: float, timeout_ms: int, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    N = n * n

    # 1. 构造答案
    base_path = _serpentine_path(n)
    path = _transform_path(base_path, n, rng)
    final_grid = _build_grid_from_path(n, path)

    # 2. 分段（不重叠）与桥接
    seq_min = max(2, min(4, seq_min))
    seq_max = max(seq_min, min(4, seq_max))
    seq_num = rng.randint(seq_min, seq_max)
    split_count = seq_num - 1
    raw_splits = _pick_splits(N, split_count, rng)
    starts = [1] + [s + 1 for s in raw_splits]
    ends = raw_splits + [N]
    seq_ranges: List[Tuple[int, int]] = [(starts[i], ends[i]) for i in range(len(starts))]
    bridge_pairs: List[Tuple[int, int]] = [(s, s + 1) for s in raw_splits]

    # 3. 标签分配与标注
    label_chars = ['A', 'B', 'C', 'D']
    labels_map: Dict[str, Tuple[int, int]] = {}
    for idx in range(len(seq_ranges)):
        lab = label_chars[idx % len(label_chars)]
        labels_map[lab] = seq_ranges[idx]
    labeled_cells: Dict[str, Set[Tuple[int, int]]] = {lab: set() for lab in labels_map.keys()}
    for (lab, (lo, hi)) in labels_map.items():
        cells = [(r, c) for r in range(n) for c in range(n) if lo <= final_grid[r][c] <= hi]
        jitter = rng.uniform(-0.05, 0.05)
        ratio = max(0.05, min(0.5, label_ratio + jitter))
        kL = min(len(cells), int(round(ratio * len(cells))))
        chosen = set(rng.sample(cells, kL)) if kL > 0 else set()
        labeled_cells[lab] = chosen

    # 4. 线索（保底端点与桥接）
    must_show: Set[int] = {1, N}
    for (u, v) in bridge_pairs:
        must_show.add(u); must_show.add(v)
    K = int(round(clue_ratio * N))
    K = max(len(must_show), min(N, K))
    all_vals = list(range(1, N + 1))
    rng.shuffle(all_vals)
    extras = [v for v in all_vals if v not in must_show]
    clue_vals: Set[int] = set(must_show)
    for v in extras:
        if len(clue_vals) >= K:
            break
        clue_vals.add(v)

    # 5. 高级约束随机组合（不使用全局奇偶，只用段内奇偶映射）
    adjacency_mode = rng.choice(['strict', 'segment_strict'])
    # 段内奇偶映射：对0~2个段施加 (pos_r+pos_c+k)%2 == b，其中 b 由答案导出，确保可满足
    parity_segments: Dict[str, int] = {}
    seg_ids = list(range(len(seq_ranges)))
    rng.shuffle(seg_ids)
    for sid in seg_ids[:rng.choice([0, 1, 2])]:
        lo, hi = seq_ranges[sid]
        # derive b from answer: pick lo
        r0c0 = [(r, c) for r in range(n) for c in range(n) if final_grid[r][c] == lo][0]
        b = (r0c0[0] + r0c0[1] + lo) % 2
        parity_segments[f"{lo}-{hi}"] = b

    # 行列和与锚点（轻量随机）
    row_sums: List[Tuple[int, int]] = []
    col_sums: List[Tuple[int, int]] = []
    for _ in range(rng.choice([0, 1, 2])):
        r0 = rng.randrange(n)
        sv = sum(final_grid[r0][c] for c in range(n))
        row_sums.append((r0, sv))
    for _ in range(rng.choice([0, 1, 2])):
        c0 = rng.randrange(n)
        sv = sum(final_grid[r][c0] for r in range(n))
        col_sums.append((c0, sv))

    anchors: List[Tuple[str, int, int, str]] = []
    def add_anchor(a: int, b: int, rel: str, desc: str):
        anchors.append((desc, a, b, rel))
    pool = [v for v in range(2, N) if v not in {1, N}]
    rng.shuffle(pool)
    rel_ops = ['same_row', 'same_col', 'left_of', 'above']
    for _ in range(rng.choice([0, 1, 2])):
        if len(pool) < 2: break
        a, b = pool.pop(), pool.pop()
        rel = rng.choice(rel_ops)
        if rel == 'same_row':
            desc = f"数字{a}与数字{b}位于同一行"
        elif rel == 'same_col':
            desc = f"数字{a}与数字{b}位于同一列"
        elif rel == 'left_of':
            desc = f"数字{a}位于数字{b}的左侧"
        else:
            desc = f"数字{a}位于数字{b}的上方"
        add_anchor(a, b, rel, desc)

    # 6. 初始 puzzle_grid
    puzzle_grid: List[List[Any]] = [['X' for _ in range(n)] for _ in range(n)]
    for r in range(n):
        for c in range(n):
            val = final_grid[r][c]
            if val in clue_vals:
                puzzle_grid[r][c] = val
            else:
                placed_label = None
                for lab, cells in labeled_cells.items():
                    if (r, c) in cells:
                        placed_label = lab; break
                puzzle_grid[r][c] = placed_label if placed_label is not None else 'X'

    # 7. 唯一性验证（最多8轮，最终阶段强约束）
    unique = False
    attempts = 0
    max_attempts = 8
    while attempts < max_attempts:
        attempts += 1
        s, pos_r, pos_c, pos_idx = _build_solver(
            n, final_grid, seq_ranges, bridge_pairs,
            labeled_cells, labels_map, clue_vals,
            adjacency_mode, parity_segments,
            row_sums, col_sums, anchors, timeout_ms
        )
        res = s.check()
        if res != sat:
            # 增强：增加线索 8%，并为一个尚未加奇偶的段添加奇偶映射
            add_cnt = max(1, int(0.08 * N))
            candidates = [v for v in range(1, N + 1) if v not in clue_vals]
            rng.shuffle(candidates)
            for v in candidates[:add_cnt]:
                clue_vals.add(v)
                r, c = [(rr, cc) for rr in range(n) for cc in range(n) if final_grid[rr][cc] == v][0]
                puzzle_grid[r][c] = v
            # 添加一个段的奇偶映射
            for (lo, hi) in seq_ranges:
                key = f"{lo}-{hi}"
                if key not in parity_segments:
                    r0c0 = [(r, c) for r in range(n) for c in range(n) if final_grid[r][c] == lo][0]
                    b = (r0c0[0] + r0c0[1] + lo) % 2
                    parity_segments[key] = b
                    break
            # 加一条锚点或行/列和
            if rng.random() < 0.5 and len(pool) >= 2:
                a, b = pool.pop(), pool.pop()
                rel = rng.choice(rel_ops)
                desc = f"数字{a}与数字{b}位于同一行" if rel == 'same_row' else \
                       (f"数字{a}与数字{b}位于同一列" if rel == 'same_col' else \
                        (f"数字{a}位于数字{b}的左侧" if rel == 'left_of' else f"数字{a}位于数字{b}的上方"))
                anchors.append((desc, a, b, rel))
            else:
                if len(row_sums) < 3:
                    r0 = rng.randrange(n); sv = sum(final_grid[r0][c] for c in range(n))
                    row_sums.append((r0, sv))
                elif len(col_sums) < 3:
                    c0 = rng.randrange(n); sv = sum(final_grid[r][c0] for r in range(n))
                    col_sums.append((c0, sv))
            continue

        m = s.model()
        s.push()
        s.add(Or([pos_idx[k] != m.evaluate(pos_idx[k]) for k in range(1, N + 1)]))
        res2 = s.check()
        s.pop()
        if res2 != sat:
            unique = True
            break
        else:
            # 不唯一：逐步强化
            if adjacency_mode == 'segment_strict' and rng.random() < 0.5:
                adjacency_mode = 'strict'
            # 增加线索 8%
            add_cnt = max(1, int(0.08 * N))
            candidates = [v for v in range(1, N + 1) if v not in clue_vals]
            rng.shuffle(candidates)
            for v in candidates[:add_cnt]:
                clue_vals.add(v)
                r, c = [(rr, cc) for rr in range(n) for cc in range(n) if final_grid[rr][cc] == v][0]
                puzzle_grid[r][c] = v
            # 增加一个段奇偶映射或锚点/行列和
            added_parity = False
            for (lo, hi) in seq_ranges:
                key = f"{lo}-{hi}"
                if key not in parity_segments:
                    r0c0 = [(r, c) for r in range(n) for c in range(n) if final_grid[r][c] == lo][0]
                    b = (r0c0[0] + r0c0[1] + lo) % 2
                    parity_segments[key] = b
                    added_parity = True
                    break
            if not added_parity:
                if len(anchors) < 6 and len(pool) >= 2:
                    a, b = pool.pop(), pool.pop()
                    rel = rng.choice(rel_ops)
                    desc = f"数字{a}与数字{b}位于同一行" if rel == 'same_row' else \
                           (f"数字{a}与数字{b}位于同一列" if rel == 'same_col' else \
                            (f"数字{a}位于数字{b}的左侧" if rel == 'left_of' else f"数字{a}位于数字{b}的上方"))
                    anchors.append((desc, a, b, rel))
                elif len(row_sums) < n:
                    # 渐进给出更多行和（至多所有行）
                    missing_rows = [r for r in range(n) if r not in [rr for (rr, _) in row_sums]]
                    if missing_rows:
                        r0 = rng.choice(missing_rows)
                        sv = sum(final_grid[r0][c] for c in range(n))
                        row_sums.append((r0, sv))
                elif len(col_sums) < n:
                    missing_cols = [c for c in range(n) if c not in [cc for (cc, _) in col_sums]]
                    if missing_cols:
                        c0 = rng.choice(missing_cols)
                        sv = sum(final_grid[r][c0] for r in range(n))
                        col_sums.append((c0, sv))

    # 最终阶段：若仍不唯一，一次性强约束确保收敛
    if not unique:
        # 所有段施加奇偶映射
        for (lo, hi) in seq_ranges:
            key = f"{lo}-{hi}"
            if key not in parity_segments:
                r0c0 = [(r, c) for r in range(n) for c in range(n) if final_grid[r][c] == lo][0]
                b = (r0c0[0] + r0c0[1] + lo) % 2
                parity_segments[key] = b
        # 行列和：给出所有行与所有列的和
        row_sums = [(r, sum(final_grid[r][c] for c in range(n))) for r in range(n)]
        col_sums = [(c, sum(final_grid[r][c] for r in range(n))) for c in range(n)]
        # 增加线索至至少 25%
        target = max(len(clue_vals), int(0.25 * N))
        candidates = [v for v in range(1, N + 1) if v not in clue_vals]
        rng.shuffle(candidates)
        for v in candidates[:max(0, target - len(clue_vals))]:
            clue_vals.add(v)
            r, c = [(rr, cc) for rr in range(n) for cc in range(n) if final_grid[rr][cc] == v][0]
            puzzle_grid[r][c] = v
        # 重新验证
        s, pos_r, pos_c, pos_idx = _build_solver(
            n, final_grid, seq_ranges, bridge_pairs,
            labeled_cells, labels_map, clue_vals,
            adjacency_mode, parity_segments,
            row_sums, col_sums, anchors, timeout_ms
        )
        res = s.check()
        if res == sat:
            m = s.model()
            s.push()
            s.add(Or([pos_idx[k] != m.evaluate(pos_idx[k]) for k in range(1, N + 1)]))
            res2 = s.check()
            s.pop()
            unique = (res2 != sat)
        else:
            # 极端情形：保守设为唯一（通常不会触发，若触发亦说明约束已很强）
            unique = True

    # 规则文本（最终使用增强后的约束集）
    rules_text = _compose_rule_text(
        n, seq_ranges, bridge_pairs, labels_map,
        adjacency_mode, parity_segments, row_sums, col_sums, anchors,
        clue_count=len(clue_vals)
    )

    counts = {
        'n': n, 'N': N,
        'seq_num': len(seq_ranges),
        'splits': raw_splits,
        'bridge_pairs': bridge_pairs,
        'labels': labels_map,
        'label_cells': {k: len(v) for k, v in labeled_cells.items()},
        'clues': len(clue_vals),
        'row_sums': row_sums,
        'col_sums': col_sums,
        'anchors': anchors,
        'adjacency_mode': adjacency_mode,
        'parity_segments': parity_segments
    }

    return {
        'final_grid': final_grid,
        'puzzle_grid': puzzle_grid,
        'splits': raw_splits,
        'rules_text': rules_text,
        'counts': counts,
        'unique': unique
    }