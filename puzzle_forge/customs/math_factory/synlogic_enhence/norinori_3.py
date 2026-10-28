# norinori_5.py
import random
import string

def build_block_letter_grid(br, bc, shuffle_regions):
    """
    构造 2x2 字母区域的网格，尺寸 m=2*br, n=2*bc。
    每个 2x2 区域用一个大写字母标注；可按块随机打乱字母分配。
    返回：m x n 的字母网格（不含 X）。
    """
    m = 2 * br
    n = 2 * bc
    block_cnt = br * bc
    letters = list(string.ascii_uppercase)
    if block_cnt > len(letters):
        letters = (letters * ((block_cnt // len(letters)) + 1))[:block_cnt]
    else:
        letters = letters[:block_cnt]
    if shuffle_regions:
        random.shuffle(letters)
    grid = [['' for _ in range(n)] for _ in range(m)]
    idx = 0
    for rb in range(br):
        for cb in range(bc):
            ch = letters[idx]
            idx += 1
            r0, c0 = 2 * rb, 2 * cb
            grid[r0][c0] = ch
            grid[r0][c0 + 1] = ch
            grid[r0 + 1][c0] = ch
            grid[r0 + 1][c0 + 1] = ch
    return grid

def make_cells(m, n):
    return [i for i in range(m * n)]

def make_row_cells(m, n):
    return [[r * n + c for c in range(n)] for r in range(m)]

def make_col_cells(m, n):
    return [[r * n + c for r in range(m)] for c in range(n)]

def make_adj_pairs(m, n):
    """
    返回所有正交相邻格对 (u, v)，用 (min, max) 存储，确保唯一。
    """
    pairs = []
    for r in range(m):
        for c in range(n - 1):
            a = r * n + c
            b = r * n + (c + 1)
            pairs.append((a, b) if a < b else (b, a))
    for r in range(m - 1):
        for c in range(n):
            a = r * n + c
            b = (r + 1) * n + c
            pairs.append((a, b) if a < b else (b, a))
    return pairs

def build_regions_from_grid(grid, m, n):
    regions = {}
    for r in range(m):
        for c in range(n):
            ch = grid[r][c]
            regions.setdefault(ch, []).append(r * n + c)
    return regions

def get_region_names(region_cells):
    return sorted(list(region_cells.keys()))

def format_row_counts(seq):
    return "[" + ", ".join(str(x) for x in seq) + "]"

def grid_to_one_line(grid):
    row_strs = []
    for row in grid:
        row_strs.append(" ".join(row))
    return "; ".join(row_strs)

def grid_to_one_line_with_x(letters_grid, x_cells, m, n):
    disp = [row[:] for row in letters_grid]
    for idx in x_cells:
        r = idx // n
        c = idx % n
        disp[r][c] = 'X'
    return grid_to_one_line(disp)

def pairs_to_keys(adj_pairs):
    return [f"{u}-{v}" for (u, v) in adj_pairs]

def build_pairs_map(adj_pairs):
    return {f"{u}-{v}": (u, v) for (u, v) in adj_pairs}

def cell_incidence_keys(c, pairs_map):
    return [k for k, (u, v) in pairs_map.items() if u == c or v == c]

def key_to_pair(key, pairs_map):
    return pairs_map[key]

def _neighbors_of_cell(c, m, n):
    r, c2 = divmod(c, n)
    nbrs = []
    if r > 0:
        nbrs.append((r - 1) * n + c2)
    if r + 1 < m:
        nbrs.append((r + 1) * n + c2)
    if c2 > 0:
        nbrs.append(r * n + (c2 - 1))
    if c2 + 1 < n:
        nbrs.append(r * n + (c2 + 1))
    return nbrs

def build_conflict_pairs_keys(m, n, pairs_map):
    """
    生成所有会导致“不同管道正交相邻”的多米诺键对 (k1, k2)。
    任意两个被选中的多米诺，只要其端点所占格子在四连通意义上相邻，即视为冲突。
    返回：[(key1, key2), ...]，其中 key1 != key2。
    """
    keys = list(pairs_map.keys())
    # 预计算：每个格子的包含边键
    cell_to_keys = {}
    for k in keys:
        u, v = pairs_map[k]
        cell_to_keys.setdefault(u, []).append(k)
        cell_to_keys.setdefault(v, []).append(k)
    # 预计算：每个键对应邻格集合（端点的四邻点合集）
    key_to_neighbor_cells = {}
    for k in keys:
        u, v = pairs_map[k]
        nbrs_u = _neighbors_of_cell(u, m, n)
        nbrs_v = _neighbors_of_cell(v, m, n)
        key_to_neighbor_cells[k] = set(nbrs_u + nbrs_v)
    # 构造冲突对
    conflicts = set()
    for k in keys:
        nbr_cells = key_to_neighbor_cells[k]
        # 任意邻格中若存在另一条多米诺覆盖该格，则与 k 冲突
        for c in nbr_cells:
            for k2 in cell_to_keys.get(c, []):
                if k2 != k:
                    a, b = (k, k2) if k < k2 else (k2, k)
                    conflicts.add((a, b))
    return sorted(list(conflicts))

def select_x_cells(letters_grid, m, n, k_min, k_max):
    """
    随机选择若干 X 的线性索引（可行性增强版）：
    - X 的数量 k 在 [k_min, k_max] 中随机选取（上限不超过区域总数的两倍）；
    - 每个区域最多 2 个 X；
    - 若某区域选了 2 个 X，则必须是该 2×2 区域内的相邻格对（水平或竖直），确保存在覆盖该 X 的内部多米诺；
    - 返回唯一索引列表。
    """
    regions = build_regions_from_grid(letters_grid, m, n)
    region_names = list(regions.keys())
    # 上限：不超过 2 * 区域数
    max_cap = min(k_max, 2 * len(region_names))
    k = random.randint(k_min, max_cap) if k_min <= max_cap else k_min

    chosen = set()
    # 随机决定若干区域放置“两 X 相邻对”
    max_pairs_regions = k // 2
    pair_regions = random.sample(region_names, random.randint(0, max_pairs_regions)) if max_pairs_regions > 0 else []
    for name in pair_regions:
        cells = sorted(regions[name])
        # 2×2 内的相邻对（四条候选边）
        candidates = []
        candidates.append((cells[0], cells[1]))  # 水平上边
        candidates.append((cells[2], cells[3]))  # 水平下边
        candidates.append((cells[0], cells[2]))  # 竖直左边
        candidates.append((cells[1], cells[3]))  # 竖直右边
        pair = random.choice(candidates)
        chosen.add(pair[0])
        chosen.add(pair[1])
        if len(chosen) >= k:
            break

    # 再随机填充单个 X，到达目标数量 k
    all_cells = [c for name in region_names for c in regions[name]]
    random.shuffle(all_cells)
    region_x_count = {name: 0 for name in region_names}
    # 已有对的区域计数修正
    for name in region_names:
        cnt = 0
        for c in regions[name]:
            if c in chosen:
                cnt += 1
        region_x_count[name] = cnt

    for c in all_cells:
        if len(chosen) >= k:
            break
        r = c // n
        col = c % n
        ch = letters_grid[r][col]
        if region_x_count[ch] < 2 and c not in chosen:
            chosen.add(c)
            region_x_count[ch] += 1

    return sorted(list(chosen))

def choose_visible_flags(k_min, k_max):
    """
    随机选择需要展示的主线索集合（固定长度4：行、列、两行带竖向、两列带横向），
    保证选中数量在 [k_min, k_max] 范围内。
    返回：长度为4的布尔列表。
    """
    k = random.randint(k_min, k_max)
    idxs = list(range(4))
    random.shuffle(idxs)
    chosen = set(idxs[:k])
    return [i in chosen for i in range(4)]

def choose_extra_flags(k_min, k_max):
    """
    选择扩展线索（长度2）：
    0: 是否给出总竖/横向管道数
    1: 是否给出四角覆盖布尔向量（1=覆盖，0=未覆盖）
    """
    k = random.randint(k_min, k_max)
    idxs = list(range(2))
    random.shuffle(idxs)
    chosen = set(idxs[:k])
    return [i in chosen for i in range(2)]

def compose_rules_text(use_rows, use_cols, use_vband, use_hband,
                       row_text, col_text, vband_text, hband_text,
                       m, n, br, bc, style_id):
    """
    组合题面规则文本（旧版，保留以兼容，不在 YAML 中直接使用）。
    """
    base = []
    if style_id == 0:
        base.append("基础规则：每个字母区域内部恰好放置1个管道且该区域恰有两个格子铺设管道")
        base.append("管道之间不得正交相邻但可对角接触")
        base.append("所有标注为X的格子必须并入某个管道")
        base.append("管道总数等于字母区域数")
    elif style_id == 1:
        base.append("基础约束：每个2×2字母区域内放置1个两格管道且覆盖恰好两个格子")
        base.append("不同管道之间不允许正交邻接，允许对角接触")
        base.append("所有带X的格子都属于某个管道")
        base.append("管道数量等于字母区域数量")
    else:
        base.append("基本条件：每个字母区域有且仅有一个两格管道并覆盖其中两个格子")
        base.append("任意两个管道不得在四连通意义上相邻，但可以在对角位置接触")
        base.append("所有标有X的格子必须被管道覆盖")
        base.append("管道总数与字母区域总数相等")

    extra = []
    if use_rows:
        extra.append(f"每一行被覆盖的格子数依次为 {row_text}")
    if use_cols:
        extra.append(f"每一列被覆盖的格子数依次为 {col_text}")
    if use_vband:
        extra.append(f"每两行带中的竖向管道数量依次为 {vband_text}")
    if use_hband:
        extra.append(f"每两列带中的横向管道数量依次为 {hband_text}")

    base_str = "；".join(base)
    extra_str = ("；额外线索：" + "；".join(extra)) if extra else ""
    return f"{base_str}{extra_str}"

def compose_rules_text2(use_rows, use_cols, use_vband, use_hband,
                        use_orient_totals, use_corner_flags,
                        row_text, col_text, vband_text, hband_text,
                        orient_text, corner_text,
                        m, n, br, bc, style_id):
    """
    组合题面规则文本（新版）：支持两类扩展线索：
    - orient_text：总竖/横向管道数
    - corner_text：四角覆盖布尔向量（1=覆盖，0=未覆盖）
    """
    base = []
    if style_id == 0:
        base.append("基础规则：每个字母区域内部恰好放置1个管道且该区域恰有两个格子铺设管道")
        base.append("不同管道不得在四连通意义上相邻但可在对角位置接触")
        base.append("所有标注为X的格子必须并入某个管道")
        base.append("管道总数等于字母区域数")
    elif style_id == 1:
        base.append("基础约束：每个2×2字母区域内放置1个两格管道且覆盖恰好两个格子")
        base.append("任意两管道不允许正交邻接，允许对角接触")
        base.append("所有带X的格子都属于某个管道")
        base.append("管道数量等于字母区域数量")
    else:
        base.append("基本条件：每个字母区域有且仅有一个两格管道并覆盖其中两个格子")
        base.append("不同管道不得构成四连通邻接，但可以在对角位置接触")
        base.append("所有标有X的格子必须被管道覆盖")
        base.append("管道总数与字母区域总数相等")

    extra = []
    if use_rows:
        extra.append(f"每一行被覆盖的格子数依次为 {row_text}")
    if use_cols:
        extra.append(f"每一列被覆盖的格子数依次为 {col_text}")
    if use_vband:
        extra.append(f"每两行带中的竖向管道数量依次为 {vband_text}")
    if use_hband:
        extra.append(f"每两列带中的横向管道数量依次为 {hband_text}")
    if use_orient_totals:
        extra.append(f"总竖向/横向管道数分别为 {orient_text}")
    if use_corner_flags:
        extra.append(f"四个角落的覆盖情况为 {corner_text}（1表示覆盖，0表示未覆盖）")

    base_str = "；".join(base)
    extra_str = ("；额外线索：" + "；".join(extra)) if extra else ""
    return f"{base_str}{extra_str}"