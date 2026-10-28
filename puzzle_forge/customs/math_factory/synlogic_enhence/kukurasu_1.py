# kukurasu_2.py
# --------------------------------------------------------------
# Custom operators for advanced generalized Kakurasu generation.
# - gen_obstacles / pick_row_ones_count / pick_row_range
# - gen_weights / choose_family_flags / choose_alpha_beta / gen_regions
# 目标：保证 3 分钟内高概率求解，仍能生成 200+ 不同题目
# --------------------------------------------------------------

import random

def gen_obstacles(n: int, max_obs: int):
    """
    Generate obstacle cells (1-based) for an n x n board.
    - Choose k in [0, max_obs].
    - Sample k distinct cells without replacement from full grid.
    Returns: list[(r, c)], integers in [1..n].
    """
    total_cells = [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
    k = 0 if max_obs <= 0 else random.randint(0, max_obs)
    k = min(k, len(total_cells))
    if k == 0:
        return []
    return random.sample(total_cells, k)

def pick_row_ones_count(n: int):
    """
    Exact per-row ones count for an n x n grid.
    Heuristic:
      - Avoid extremes (0 or n).
      - Favor moderate densities for uniqueness and solvability.
      - If n <= 6: choose from {2,3}; else choose from {2,3,4}.
    """
    feasible = list(range(1, n))  # 1..n-1
    candidates = [2, 3] if n <= 6 else [2, 3, 4]
    candidates = [x for x in candidates if x in feasible]
    if not candidates:
        return random.choice(feasible)
    return random.choice(candidates)

def pick_row_range(n: int):
    """
    Inclusive range [row_min, row_max] for per-row ones.
    Strategy:
      - Baseline k = pick_row_ones_count(n).
      - Narrow window [max(1, k-1), min(n-1, k+1)].
      - Fix degenerate cases by minimal widening.
    """
    k = pick_row_ones_count(n)
    row_min = max(1, k - 1)
    row_max = min(n - 1, k + 1)
    if row_min >= row_max:
        row_min = max(1, min(k, n - 2))
        row_max = min(n - 1, max(k + 1, 2))
        if row_min >= row_max:
            row_min, row_max = 1, min(2, n - 1)
    return [row_min, row_max]

def gen_weights(n: int, do_permute: bool):
    """
    Generate a weight sequence of length n from integers 1..n.
    - If do_permute is False: [1,2,...,n]
    - If do_permute is True: random permutation of 1..n
    """
    seq = list(range(1, n + 1))
    if do_permute:
        random.shuffle(seq)
    return seq

def choose_family_flags():
    """
    Choose a boolean list of target-family flags:
    Index map:
      0: use_row_weight_sums
      1: use_col_weight_sums
      2: use_main_diag
      3: use_anti_diag
      4: use_total_ones
      5: use_adj_h
      6: use_adj_v
      7: use_global_mixed
      8: use_regions
    Constraints:
      - At least 3 flags are True.
      - At least one of (row_weight_sums, col_weight_sums) is True.
      - Bias towards 3~5 active families to keep solver fast.
    """
    # base random pick
    flags = [False] * 9
    # decide target count
    target_true = random.randint(3, 5)
    # ensure at least one of row/col
    # pick which one to enforce first
    if random.random() < 0.5:
        flags[0] = True  # row_weight_sums
    else:
        flags[1] = True  # col_weight_sums
    # now randomly turn on other flags until reaching target_true
    indices = list(range(9))
    random.shuffle(indices)
    for idx in indices:
        if sum(1 for f in flags if f) >= target_true:
            break
        if not flags[idx]:
            flags[idx] = (random.random() < 0.6)
    # final check: if still fewer than target_true, force on from remaining
    rem = [i for i in range(9) if not flags[i]]
    while sum(1 for f in flags if f) < target_true and rem:
        i = rem.pop()
        flags[i] = True
    # sanity: if both row/col off due to randomness, flip one
    if not (flags[0] or flags[1]):
        flags[random.choice([0,1])] = True
    return flags

def choose_alpha_beta():
    """
    Choose small integer coefficients (alpha, beta) for a global mixed linear weight.
    Keep them small to avoid excessive numeric range, e.g., 1..3.
    """
    alpha = random.randint(1, 3)
    beta = random.randint(1, 3)
    return [alpha, beta]

def gen_regions(n: int, max_regions: int):
    """
    Generate up to max_regions non-overlapping rectangular regions on an n x n grid.
    Return a list of rectangles, each as (r1, c1, r2, c2), with 1-based inclusive bounds.
    Strategy:
      - Attempt to sample rectangles with random size (height 1..n, width 1..n) and position.
      - Ensure non-overlap by rejecting rectangles intersecting existing ones.
      - Limit total attempts to keep runtime bounded.
    """
    max_regions = max(1, min(max_regions, 3))
    regions = []
    occupied = set()
    attempts = 0
    max_attempts = 50

    def rect_cells(r1, c1, r2, c2):
        return [(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]

    while len(regions) < max_regions and attempts < max_attempts:
        attempts += 1
        h = random.randint(1, n)
        w = random.randint(1, n)
        r1 = random.randint(1, n - h + 1)
        c1 = random.randint(1, n - w + 1)
        r2 = r1 + h - 1
        c2 = c1 + w - 1
        cells = rect_cells(r1, c1, r2, c2)
        if any((r, c) in occupied for (r, c) in cells):
            continue
        regions.append((r1, c1, r2, c2))
        for (r, c) in cells:
            occupied.add((r, c))
    if not regions:
        r1 = max(1, n // 2)
        c1 = max(1, n // 2)
        r2 = min(n, r1 + 1)
        c2 = min(n, c1 + 1)
        regions = [(r1, c1, r2, c2)]
    return regions