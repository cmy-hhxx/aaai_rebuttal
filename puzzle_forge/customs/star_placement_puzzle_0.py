import random
from typing import Dict, List, Tuple, Any
from collections import deque

def generate_star_battle(n: int, seed: int, level: str) -> Dict[str, Any]:
    """
    高质量 Star Battle 生成器（1 星/行列/区）。
    修改说明：'stars' 返回值现为 List[List[int]]，按字母序 A, B, C... 排列。
    例如: [[1, 2], [3, 4], ...]
    """
    rnd = random.Random(seed)
    level = level.lower().strip()
    if level not in ('easy', 'medium', 'hard'):
        level = 'medium'

    def difficulty_ranges(n_: int) -> Dict[str, Tuple[int, int]]:
        base = n_ * n_ * 3
        return {
            'easy':   (0,            int(4.0 * base)),
            'medium': (int(4.0 * base), int(12.0 * base)),
            'hard':   (int(12.0 * base), int(40.0 * base)),
        }

    ranges = difficulty_ranges(n)
    target_min, target_max = ranges[level]

    # 辅助函数：将解字典转换为按字母序排列的坐标列表
    def format_stars_as_list(letters_grid, perm_list):
        # 1. 先构建 {字母: [行, 列]} 的字典
        # 注意：perm_list[r] 是第 r 行选中的列索引 (0-based)
        temp_stars = {}
        for r in range(n):
            c = perm_list[r]
            region_char = letters_grid[r][c]
            # 转换为 1-based 坐标，并使用 list 格式 [row, col]
            temp_stars[region_char] = [r + 1, c + 1]
        
        # 2. 按字母键排序 (A, B, C...) 提取坐标
        sorted_keys = sorted(temp_stars.keys())
        return [temp_stars[k] for k in sorted_keys]

    # 主循环
    for attempt in range(300):
        cols = _gen_nonadj_columns(n, rnd)
        try:
            letters = _build_balanced_connected_regions(n, cols, rnd)
        except RuntimeError:
            continue
        metrics_eval = _evaluate_uniqueness_and_difficulty(letters)
        connectivity_ok = _check_all_connected(letters)
        metrics_eval['connectivity'] = connectivity_ok
        metrics_eval['n'] = n

        unique, valid = metrics_eval['unique'], metrics_eval['valid']
        if not (unique and valid and connectivity_ok):
            continue
        
        score = metrics_eval['score']
        selected = target_min <= score <= target_max
        metrics_eval['level_target'] = level
        metrics_eval['level_actual'] = _classify_level(score, ranges)
        metrics_eval['level_selected'] = bool(selected)

        if selected:
            perm = _get_unique_solution_perm(letters)
            # 修改点：返回列表格式
            stars_list = format_stars_as_list(letters, perm)
            return {'letters': letters, 'stars': stars_list, 'metrics': metrics_eval}

    # 兜底循环
    for attempt in range(300):
        cols = _gen_nonadj_columns(n, rnd)
        try:
            letters = _build_balanced_connected_regions(n, cols, rnd)
        except RuntimeError:
            continue
        metrics_eval = _evaluate_uniqueness_and_difficulty(letters)
        connectivity_ok = _check_all_connected(letters)
        metrics_eval['connectivity'] = connectivity_ok
        metrics_eval['n'] = n

        unique, valid = metrics_eval['unique'], metrics_eval['valid']
        if unique and valid and connectivity_ok:
            perm = _get_unique_solution_perm(letters)
            score = metrics_eval['score']
            metrics_eval['level_target'] = level
            metrics_eval['level_actual'] = _classify_level(score, ranges)
            metrics_eval['level_selected'] = False
            # 修改点：返回列表格式
            stars_list = format_stars_as_list(letters, perm)
            return {'letters': letters, 'stars': stars_list, 'metrics': metrics_eval}

    raise RuntimeError("生成唯一解失败，请更换种子或参数。")


# ---------- 生成非相邻列排列 ----------

def _gen_nonadj_columns(n: int, rnd: random.Random) -> List[int]:
    """
    生成满足：
      - 每行恰好一星（行 r 选列 c[r]）；
      - 每列恰好一星（c 为 0..n-1 的排列）；
      - 任意相邻行 r 与 r±1 的列差 >= 2（从而避免正交与对角相邻）。
    的列排列。采用回溯 + 随机顺序。
    """
    candidates = list(range(n))
    rnd.shuffle(candidates)
    used = [False] * n

    def backtrack(seq: List[int]) -> List[int]:
        if len(seq) == n:
            return seq
        order = [c for c in candidates if not used[c]]
        rnd.shuffle(order)
        for c in order:
            if not seq or abs(seq[-1] - c) >= 2:
                used[c] = True
                res = backtrack(seq + [c])
                if res:
                    return res
                used[c] = False
        return []

    res = backtrack([])
    if res:
        return res

    # 兜底：交错排列（偶数列后奇数列），并随机调整
    seq = list(range(0, n, 2)) + list(range(1, n, 2))
    for _ in range(200):
        if all(abs(seq[i] - seq[i - 1]) >= 2 for i in range(1, n)):
            break
        i, j = rnd.randrange(n), rnd.randrange(n)
        seq[i], seq[j] = seq[j], seq[i]
    return seq


# ---------- 构造 4-连通均衡区域 ----------

def _build_balanced_connected_regions(n: int, cols: List[int], rnd: random.Random) -> List[List[str]]:
    """
    多源均衡扩张，构造 n 个 4-连通区域：
      - 以每行的星位 (r, cols[r]) 为区域种子；
      - 目标面积 ~ n（总面积 n*n / n）；
      - 扩张时倾向选择“紧致”的 frontier（周围自家邻居多的格子），避免细长通道；
      - 完成后保证每区 4-连通。
    返回 letters（字母网格）。
    """
    letters = [[None for _ in range(n)] for __ in range(n)]
    labels = [chr(ord('A') + i) for i in range(n)]
    fronts = {lab: set() for lab in labels}
    size = {lab: 0 for lab in labels}

    # 初始化 seeds 与 frontiers
    for r in range(n):
        lab = labels[r]
        rr, cc = r, cols[r]
        letters[rr][cc] = lab
        size[lab] += 1
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = rr + dr, cc + dc
            if 0 <= nr < n and 0 <= nc < n and letters[nr][nc] is None:
                fronts[lab].add((nr, nc))

    total = n * n
    assigned = n
    rounds = 0

    def tightness(lab: str, rr: int, cc: int) -> int:
        return sum(1 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if 0 <= rr + dr < n and 0 <= cc + dc < n and letters[rr + dr][cc + dc] == lab)

    while assigned < total and rounds < n * n * 10:
        rounds += 1
        for lab in rnd.sample(labels, len(labels)):
            if not fronts[lab]:
                continue
            # 评分 frontier：紧致度优先
            scored = []
            for (rr, cc) in fronts[lab]:
                t = tightness(lab, rr, cc)
                scored.append((t, rr, cc))
            scored.sort(reverse=True)
            rr, cc = scored[0][1], scored[0][2]
            if letters[rr][cc] is None:
                letters[rr][cc] = lab
                size[lab] += 1
                assigned += 1
                fronts[lab].discard((rr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < n and 0 <= nc < n and letters[nr][nc] is None:
                        fronts[lab].add((nr, nc))

        # 滴灌填充孤点：选择邻接最多的已分配标签
        if assigned < total:
            empties = [(i, j) for i in range(n) for j in range(n) if letters[i][j] is None]
            if empties:
                i, j = rnd.choice(empties)
                neigh = []
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = i + dr, j + dc
                    if 0 <= ni < n and 0 <= nj < n and letters[ni][nj] is not None:
                        neigh.append(letters[ni][nj])
                if neigh:
                    best = max(set(neigh), key=neigh.count)
                    letters[i][j] = best
                    size[best] += 1
                    assigned += 1
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ni, nj = i + dr, j + dc
                        if 0 <= ni < n and 0 <= nj < n and letters[ni][nj] is None:
                            fronts[best].add((ni, nj))

    # 连通性校验（每区 4-连通）
    if not _check_all_connected(letters):
        raise RuntimeError("区域连通性失败。")
    # 去除严格的面积均衡失败抛错，保留“倾向均衡”的生成策略，提升鲁棒性
    return letters


# ---------- 唯一性与难度评估（修正相邻约束） ----------

def _evaluate_uniqueness_and_difficulty(letters: List[List[str]]) -> Dict[str, object]:
    """
    MRV + 剪枝验证唯一解，并统计：
      - unique: 是否唯一解；
      - valid: 是否存在解；
      - nodes: 搜索展开节点数；
      - forced: 强制步数；
      - avg_branch: 平均分支数（nodes 上的平均候选数）；
      - score: 综合评分（nodes + avg_branch*200 - forced*50）。
    约束：
      - 每行/每列恰一星；
      - 任意两星不相邻（含对角）=> 对 1 星/行列，要求相邻行 r 与 r±1：|c[r] - c[r±1]| >= 2；
      - 每区域恰一星。
    """
    n = len(letters)
    regions = sorted(set(x for row in letters for x in row))
    used_cols = [False] * n
    used_regs: Dict[str, bool] = {reg: False for reg in regions}
    perm: List[int] = [None] * n  # 每行选定的列（None 表示未选）

    nodes = 0
    forced = 0
    total_branch = 0
    solutions = 0

    def candidates_for_row(r: int) -> List[Tuple[int, str]]:
        """为任意行 r 计算可选列，检查：列未用、区域未用、与已赋值邻行 r-1/r+1 非相邻。"""
        cands = []
        for c in range(n):
            if used_cols[c]:
                continue
            reg = letters[r][c]
            if used_regs[reg]:
                continue
            # 检查与上邻行
            if r - 1 >= 0 and perm[r - 1] is not None and abs(c - perm[r - 1]) < 2:
                continue
            # 检查与下邻行
            if r + 1 < n and perm[r + 1] is not None and abs(c - perm[r + 1]) < 2:
                continue
            cands.append((c, reg))
        return cands

    def dfs(depth: int):
        nonlocal nodes, forced, total_branch, solutions
        if solutions > 1:
            return
        if depth == n:
            solutions += 1
            return

        # MRV：选择候选最少的未赋值行
        rows = [i for i in range(n) if perm[i] is None]
        row_cands = [(r, candidates_for_row(r)) for r in rows]
        row_cands.sort(key=lambda x: len(x[1]))
        r, cands = row_cands[0]

        nodes += 1
        total_branch += len(cands)
        if len(cands) == 1:
            forced += 1

        # 按列次序尝试
        cands.sort(key=lambda x: x[0])
        for c, reg in cands:
            used_cols[c] = True
            used_regs[reg] = True
            perm[r] = c
            dfs(depth + 1)
            used_cols[c] = False
            used_regs[reg] = False
            perm[r] = None
            if solutions > 1:
                break

    dfs(0)

    avg_branch = round(total_branch / max(1, nodes), 2)
    score = nodes + int(avg_branch * 200) - forced * 50
    return {
        'unique': solutions == 1,
        'valid': solutions >= 1,
        'nodes': nodes,
        'forced': forced,
        'avg_branch': avg_branch,
        'score': score,
    }


def _get_unique_solution_perm(letters: List[List[str]]) -> List[int]:
    """返回唯一解列排列 perm（行 r 选列 perm[r]），采用与评估一致的 MRV + 邻行相邻约束。"""
    n = len(letters)
    regions = sorted(set(x for row in letters for x in row))
    used_cols = [False] * n
    used_regs: Dict[str, bool] = {reg: False for reg in regions}
    perm: List[int] = [None] * n
    solved = [False]

    def candidates_for_row(r: int) -> List[Tuple[int, str]]:
        cands = []
        for c in range(n):
            if used_cols[c]:
                continue
            reg = letters[r][c]
            if used_regs[reg]:
                continue
            if r - 1 >= 0 and perm[r - 1] is not None and abs(c - perm[r - 1]) < 2:
                continue
            if r + 1 < n and perm[r + 1] is not None and abs(c - perm[r + 1]) < 2:
                continue
            cands.append((c, reg))
        return cands

    def dfs(depth: int):
        if solved[0]:
            return
        if depth == n:
            solved[0] = True
            return
        rows = [i for i in range(n) if perm[i] is None]
        row_cands = [(r, candidates_for_row(r)) for r in rows]
        row_cands.sort(key=lambda x: len(x[1]))
        r, cands = row_cands[0]
        cands.sort(key=lambda x: x[0])
        for c, reg in cands:
            used_cols[c] = True
            used_regs[reg] = True
            perm[r] = c
            dfs(depth + 1)
            if solved[0]:
                return
            used_cols[c] = False
            used_regs[reg] = False
            perm[r] = None

    dfs(0)
    if not solved[0]:
        raise RuntimeError("无法恢复唯一解的列排列。")
    return perm


# ---------- 连通性检查与难度分类 ----------

def _check_all_connected(letters: List[List[str]]) -> bool:
    """检查每个字母区域是否为 4-连通。"""
    n = len(letters)
    regions = sorted(set(x for row in letters for x in row))
    for lab in regions:
        cells = [(i, j) for i in range(n) for j in range(n) if letters[i][j] == lab]
        if not cells:
            return False
        vis = set([cells[0]])
        q = deque([cells[0]])
        while q:
            i, j = q.popleft()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < n and letters[ni][nj] == lab and (ni, nj) not in vis:
                    vis.add((ni, nj))
                    q.append((ni, nj))
        if len(vis) != len(cells):
            return False
    return True


def _classify_level(score: int, ranges: Dict[str, Tuple[int, int]]) -> str:
    """依据综合评分 score 与阈值区间，返回实际难度等级标签。"""
    for lvl, (lo, hi) in ranges.items():
        if lo <= score <= hi:
            return lvl
    lo_min = min(r[0] for r in ranges.values())
    hi_max = max(r[1] for r in ranges.values())
    if score < lo_min:
        return 'easy-'
    if score > hi_max:
        return 'hard+'
    return 'medium'