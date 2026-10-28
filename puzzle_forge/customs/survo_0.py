# survo_0.py
# 自定义算子：
# - build_matrix(m, n, min_val, max_val, seed): 随机生成符合 Survo 规则的完整矩阵
# - compute_unknown_num(m, n, difficulty_level, seed): 依据难度与 seed 选择未知数，绑定 seed 提升复现性
# - choose_unknowns(m, n, filled_total, unknown_num, difficulty_level, seed): 依据难度选择未知格位置，导出已知三元组与可用数字

from typing import List, Dict, Any, Tuple
import random

def build_matrix(m: int, n: int, min_val: int, max_val: int, seed: int) -> List[List[int]]:
    """
    随机生成一个 m x n 的 Survo 矩阵：
    - 内部 (0..m-2, 0..n-2) 使用随机正整数值
    - 行末 (r, n-1) 为该行内部之和
    - 列末 (m-1, c) 为该列内部之和
    - 右下角 (m-1, n-1) 为最后一行之前各列和之和（与最后一列之前各行和一致）
    """
    assert m >= 4 and n >= 4, "Survo矩阵至少为 4x4"
    assert min_val >= 1 and max_val >= min_val + 3, "数值范围需合理"

    rnd = random.Random(seed)

    # 生成内部值
    interior = [[rnd.randint(min_val, max_val) for _ in range(n - 1)] for __ in range(m - 1)]
    filled = [[0 for _ in range(n)] for __ in range(m)]

    # 填内部与行末（行和）
    for r in range(m - 1):
        row_sum = 0
        for c in range(n - 1):
            val = interior[r][c]
            filled[r][c] = val
            row_sum += val
        filled[r][n - 1] = row_sum

    # 填列末（列和）
    for c in range(n - 1):
        col_sum = 0
        for r in range(m - 1):
            col_sum += filled[r][c]
        filled[m - 1][c] = col_sum

    # 右下角一致性（最后一行前 n-1 列之和）
    bottom_right = sum(filled[m - 1][c] for c in range(n - 1))
    filled[m - 1][n - 1] = bottom_right
    return filled

def compute_unknown_num(m: int, n: int, difficulty_level: int, seed: int) -> int:
    """
    依据难度与 seed 选择未知格数量，完全绑定 seed 以保证复现。
    - 设 cap = min(m-1, n-1)，内部格的行/列上限；
    - easy(0)   : 3..min(4, cap)
    - medium(1) : 4..min(6, cap)
    - hard(2)   : max(5, cap-2)..cap （尽可能接近 cap）
    """
    R = max(1, m - 1)
    C = max(1, n - 1)
    cap = min(R, C)
    rnd = random.Random(seed * 131 + 7)

    if difficulty_level == 0:  # easy
        lo = 3
        hi = min(cap, 4)
    elif difficulty_level == 1:  # medium
        lo = min(4, cap)
        hi = min(cap, 6) if cap >= 6 else cap
    else:  # hard
        lo = max(5, cap - 2)
        hi = cap
    if lo > hi:
        lo, hi = hi, hi
    return rnd.randint(lo, hi)

def _candidate_internal_positions(m: int, n: int) -> List[Tuple[int, int]]:
    """返回所有内部位置坐标列表 (i, j)，不含最后一行/列。"""
    return [(i, j) for i in range(m - 1) for j in range(n - 1)]

def choose_unknowns(m: int, n: int, filled_total: List[List[int]], unknown_num: int,
                    difficulty_level: int, seed: int) -> Dict[str, Any]:
    """
    依据难度选择内部未知格位置，并输出：
      - unknown: [[i, j], ...]
      - known: [(i, j, val), ...] 仅内部已知位置的三元组
      - avail: [v1, v2, ...] 未知位置的值组成的多重集（用于题面展示与约束）

    难度映射（保证唯一性与可控难度）：
      - easy(0)   : 每行/列未知格数上限=1（最稳妥，直接可唯一）
      - medium(1) : 每行/列上限=2（适度耦合，仍保证可唯一的一一匹配+少量加注）
      - hard(2)   : 每行/列上限=2，优先在已使用的行或列上加第二个未知，制造更强耦合

    生成策略：
      1) 基础一一匹配（行列互不重复的配对），保证初始可唯一。
      2) 若为 medium/hard，尝试额外加注到部分行/列（不超过上限），提升耦合。
      3) 最终未知位置数达到 unknown_num；解的唯一性由外部 SMT 求解器验证（max_solution=1）。
    """
    assert difficulty_level in (0, 1, 2), "difficulty_level must be 0/1/2"
    rnd = random.Random(seed * 133 + 17)

    max_per_row = 1 if difficulty_level == 0 else 2
    max_per_col = 1 if difficulty_level == 0 else 2

    R = m - 1
    C = n - 1
    k = max(3, min(unknown_num, min(R, C)))  # 至少3、至多内部行列的最小值

    # 基础一一匹配：保证初始唯一结构
    rows = list(range(R))
    cols = list(range(C))
    rnd.shuffle(rows)
    rnd.shuffle(cols)
    base_pairs = list(zip(rows, cols))[:min(k, min(R, C))]

    # 若需要在 medium/hard 做加注（增加耦合），尝试给某行或某列再加一个未知（不超过上限）
    extra_pairs: List[Tuple[int, int]] = []
    if difficulty_level in (1, 2) and len(base_pairs) < k:
        leftovers = [(i, j) for i in range(R) for j in range(C)
                     if (i, j) not in set(base_pairs)]
        rnd.shuffle(leftovers)

        row_cnt = {}
        col_cnt = {}
        for (i, j) in base_pairs:
            row_cnt[i] = row_cnt.get(i, 0) + 1
            col_cnt[j] = col_cnt.get(j, 0) + 1

        # hard(2)：优先在已使用的行或列上加第二个未知；medium(1)：优先在未使用的行或列上补齐
        bias_used = (difficulty_level == 2)

        def candidate_ok(i, j):
            return row_cnt.get(i, 0) < max_per_row and col_cnt.get(j, 0) < max_per_col

        # 先尝试偏好策略
        for (i, j) in leftovers:
            if len(base_pairs) + len(extra_pairs) >= k:
                break
            prefer_used = (row_cnt.get(i, 0) > 0 or col_cnt.get(j, 0) > 0)
            if (prefer_used and bias_used) or (not prefer_used and not bias_used):
                if candidate_ok(i, j):
                    extra_pairs.append((i, j))
                    row_cnt[i] = row_cnt.get(i, 0) + 1
                    col_cnt[j] = col_cnt.get(j, 0) + 1

        # 若不足，再填充剩余
        if len(base_pairs) + len(extra_pairs) < k:
            for (i, j) in leftovers:
                if len(base_pairs) + len(extra_pairs) >= k:
                    break
                if candidate_ok(i, j):
                    extra_pairs.append((i, j))
                    row_cnt[i] = row_cnt.get(i, 0) + 1
                    col_cnt[j] = col_cnt.get(j, 0) + 1

    chosen = base_pairs + extra_pairs
    # 若仍不足 k，则降级为一一匹配的前 k 个
    if len(chosen) < k:
        chosen = base_pairs[:k]

    unknown = [[i, j] for (i, j) in chosen]

    # 构造已知内部三元组与可用数字（未知位置的真实值）
    unknown_set = {(i, j) for i, j in chosen}
    known = []
    avail = []
    for i in range(R):
        for j in range(C):
            val = filled_total[i][j]
            if (i, j) in unknown_set:
                avail.append(val)
            else:
                known.append((i, j, val))

    return {'unknown': unknown, 'known': known, 'avail': avail}