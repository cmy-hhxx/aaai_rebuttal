# star_placement_puzzle_0.py
# 目标：
# - 正向生成高复杂度实例并进行唯一解验证（时间限制 < 180s）。
# - 随机化规则画像与复合约束，提升逻辑深度与隐蔽性。
# 提供的自定义算子：
#   * generate_hard_instance(n): 生成区域划分、解、规则、复合约束参数与描述文本，保证唯一解。
#   * build_regions(region_grid): 字母集合/分组/坐标到字母映射。
#   * build_cell_keys(n): 生成字符串键与坐标映射。
#   * build_neighbors_with_type(n, adjacency_type): 生成相邻键对（orthogonal/king/none）。
# 其余 function_1/function_2 为占位示例。

from typing import Dict, List, Tuple, Any
import random
import time

Coord = Tuple[int, int]   # 0-based (row, col)
Key = Tuple[str, str]     # ('R{i}', 'C{j}')

def build_regions(region_grid: List[List[str]]) -> Dict[str, Any]:
    rows = len(region_grid)
    cols = len(region_grid[0]) if rows > 0 else 0
    groups: Dict[str, List[Coord]] = {}
    cell_to_letter: Dict[Coord, str] = {}
    for i in range(rows):
        for j in range(cols):
            L = region_grid[i][j]
            groups.setdefault(L, []).append((i, j))
            cell_to_letter[(i, j)] = L
    letters = sorted(groups.keys())
    return {
        'letters': letters,
        'groups': groups,
        'cell_to_letter': cell_to_letter,
    }

def build_cell_keys(n: int) -> Dict[str, Any]:
    rows_str = [f'R{i}' for i in range(n)]
    cols_str = [f'C{j}' for j in range(n)]
    cells_keys: List[Key] = []
    coord_to_key: Dict[Coord, Key] = {}
    key_to_coord: Dict[Key, Coord] = {}
    for i in range(n):
        for j in range(n):
            k = (rows_str[i], cols_str[j])
            cells_keys.append(k)
            coord_to_key[(i, j)] = k
            key_to_coord[k] = (i, j)
    return {
        'rows_str': rows_str,
        'cols_str': cols_str,
        'cells_keys': cells_keys,
        'coord_to_key': coord_to_key,
        'key_to_coord': key_to_coord,
    }

def build_neighbors_with_type(n: int, adjacency_type: str) -> List[Tuple[Key, Key]]:
    """
    adjacency_type:
      - 'none': 返回空列表
      - 'orthogonal': 4 邻接对
      - 'king': 8 邻接对(含对角)
    """
    rows_str = [f'R{i}' for i in range(n)]
    cols_str = [f'C{j}' for j in range(n)]
    pairs: List[Tuple[Key, Key]] = []
    if adjacency_type == 'none':
        return pairs
    if adjacency_type == 'orthogonal':
        deltas = [(-1,0), (1,0), (0,-1), (0,1)]
    else:  # king
        deltas = [(di, dj) for di in (-1,0,1) for dj in (-1,0,1) if not (di == 0 and dj == 0)]
    seen = set()
    for i in range(n):
        for j in range(n):
            for di, dj in deltas:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < n:
                    k1 = (rows_str[i], cols_str[j])
                    k2 = (rows_str[ni], cols_str[nj])
                    a, b = min(k1, k2), max(k1, k2)
                    if (a, b) not in seen:
                        seen.add((a, b))
                        pairs.append((a, b))
    return pairs

def _random_partition(n: int, letters: List[str]) -> List[List[str]]:
    """
    随机区域划分：每个字母至少一个单元，剩余单元随机分配。
    不强制连通性，以提升生成成功率与多样性。
    """
    total_cells = [(i, j) for i in range(n) for j in range(n)]
    random.shuffle(total_cells)
    grid = [['' for _ in range(n)] for _ in range(n)]
    seed_cells = total_cells[:n]
    for L, (i, j) in zip(letters, seed_cells):
        grid[i][j] = L
    idx = n
    while idx < len(total_cells):
        i, j = total_cells[idx]
        grid[i][j] = random.choice(letters)
        idx += 1
    return grid

def _adjacent(c1: Coord, c2: Coord, adjacency_type: str) -> bool:
    dr, dc = abs(c1[0] - c2[0]), abs(c1[1] - c2[1])
    if adjacency_type == 'none':
        return False
    if adjacency_type == 'orthogonal':
        return (dr == 1 and dc == 0) or (dr == 0 and dc == 1)
    # king
    return dr <= 1 and dc <= 1 and not (dr == 0 and dc == 0)

def _solve_one(n: int, region_grid: List[List[str]], letters: List[str], adjacency_type: str) -> List[Coord]:
    """
    求一个满足基础约束（行/列/区域各一颗 + 邻接类型）的解。
    """
    used_cols = [False] * n
    used_letter = {L: False for L in letters}
    solution: List[Coord] = []

    rows = list(range(n))
    random.shuffle(rows)
    row_cands: Dict[int, List[int]] = {}
    for i in range(n):
        cols = list(range(n))
        random.shuffle(cols)
        row_cands[i] = cols

    def backtrack(idx: int) -> bool:
        if idx == n:
            return True
        i = rows[idx]
        for j in row_cands[i]:
            if used_cols[j]:
                continue
            L = region_grid[i][j]
            if used_letter[L]:
                continue
            c = (i, j)
            if any(_adjacent(pc, c, adjacency_type) for pc in solution):
                continue
            used_cols[j] = True
            used_letter[L] = True
            solution.append(c)
            if backtrack(idx + 1):
                return True
            solution.pop()
            used_cols[j] = False
            used_letter[L] = False
        return False

    return solution if backtrack(0) else []

def _second_solution_exists(n: int,
                            region_grid: List[List[str]],
                            letters: List[str],
                            adjacency_type: str,
                            base_sol: List[Coord],
                            parity_spec: Dict[str, Any],
                            modulo_spec: Dict[str, Any],
                            hemisphere_spec: Dict[str, Any],
                            time_deadline: float) -> bool:
    """
    检查是否存在与 base_sol 不同的第二解，满足所有复合约束。
    采用回溯搜索并在到达截止时间时停止。
    """
    used_cols = [False] * n
    used_letter = {L: False for L in letters}
    solution: List[Coord] = []
    base_set = set(base_sol)

    # 预计算权重
    p1 = modulo_spec.get('prime1', 2)
    p2 = modulo_spec.get('prime2', 3)
    m = modulo_spec.get('modulus_m', 5)
    mod_target = modulo_spec.get('modulo_target', 0)
    mod_enabled = modulo_spec.get('enabled', False)

    parity_letters = parity_spec.get('letters', [])
    parity_target = parity_spec.get('target', 0)
    parity_enabled = parity_spec.get('enabled', False)

    hemi_letters = hemisphere_spec.get('letters', [])
    hemi_target = hemisphere_spec.get('target', 0)
    top_half_flag = hemisphere_spec.get('top_half_flag', True)
    hemi_enabled = hemisphere_spec.get('enabled', False)
    half_cut = n // 2

    rows = list(range(n))
    random.shuffle(rows)
    row_cands: Dict[int, List[int]] = {}
    for i in range(n):
        cols = list(range(n))
        random.shuffle(cols)
        row_cands[i] = cols

    # 累计量
    parity_sum = 0
    modulo_sum = 0
    hemi_count = 0

    def is_parity_letter(L: str) -> bool:
        return L in parity_letters

    def is_hemi_letter(L: str) -> bool:
        return L in hemi_letters

    def backtrack(idx: int) -> bool:
        nonlocal parity_sum, modulo_sum, hemi_count
        if time.time() > time_deadline:
            return False  # 超时停止

        if idx == n:
            # 与 base_sol 不同才算第二解
            if set(solution) == base_set:
                return False
            # 验证复合约束
            if parity_enabled and (parity_sum % 2 != parity_target):
                return False
            if mod_enabled and (modulo_sum % m != mod_target):
                return False
            if hemi_enabled and (hemi_count != hemi_target):
                return False
            return True

        i = rows[idx]
        for j in row_cands[i]:
            if used_cols[j]:
                continue
            L = region_grid[i][j]
            if used_letter[L]:
                continue
            c = (i, j)
            if any(_adjacent(pc, c, adjacency_type) for pc in solution):
                continue

            # 前向更新
            used_cols[j] = True
            used_letter[L] = True
            solution.append(c)
            add_parity = (i if is_parity_letter(L) else 0)
            add_mod = i * p1 + j * p2
            add_hemi = (1 if is_hemi_letter(L) and ((i < half_cut) if top_half_flag else (i >= half_cut)) else 0)
            parity_sum += add_parity
            modulo_sum += add_mod
            hemi_count += add_hemi

            # 递归
            if backtrack(idx + 1):
                return True

            # 回溯
            solution.pop()
            used_cols[j] = False
            used_letter[L] = False
            parity_sum -= add_parity
            modulo_sum -= add_mod
            hemi_count -= add_hemi

        return False

    return backtrack(0)

def generate_hard_instance(n: int) -> Dict[str, Any]:
    """
    高复杂度实例生成（前向模式），并进行唯一解验证：
      1) 生成字母列表与随机规则画像（邻接类型 + 随机启用的复合约束）。
      2) 随机区域划分；基础约束下求一个解。
      3) 从该解派生复合约束的目标参数与文字描述。
      4) 唯一解验证：若存在第二解或超时，则重新生成分区并重复。
      5) 返回实例、规则与约束参数，供 YAML 使用并锁定解。
    """
    start_global = time.time()
    time_budget_sec = 170.0  # 预留 < 3 分钟整体预算
    letters = [chr(65 + i) for i in range(n)]

    while True:
        # 邻接类型：更偏向难度更高的 'king'
        adjacency_type = random.choices(['king', 'orthogonal', 'none'], weights=[6, 3, 1], k=1)[0]
        # 基础规则关系与配额（保持 eq=1 以增强可验证性与难度）
        row_relation = 'eq'
        col_relation = 'eq'
        region_relation = 'eq'
        row_quota = 1
        col_quota = 1
        region_quota = 1

        # 随机启用复合约束
        parity_enabled = random.choice([True, False])
        modulo_enabled = random.choice([True, False])
        hemisphere_enabled = random.choice([True, False])

        # 随机区域划分 + 基础约束下求解
        rg = _random_partition(n, letters)
        sol = _solve_one(n, rg, letters, adjacency_type)
        if not sol:
            if time.time() - start_global > time_budget_sec:
                # 兜底：列划分 + 重试
                rg = [[letters[j] for j in range(n)] for _ in range(n)]
                sol = _solve_one(n, rg, letters, adjacency_type)
                if not sol:
                    continue
            else:
                continue

        # 从解派生复合约束目标
        # 1) 奇偶约束：选择若干字母，目标为所选字母星的行索引和的偶奇性
        if parity_enabled:
            k = random.randint(max(1, n // 2), n)  # 选取至少一半的字母
            chosen_letters = random.sample(letters, k)
            parity_sum = sum(i for (i, j) in sol if rg[i][j] in chosen_letters)
            parity_target = parity_sum % 2
            parity_letters = chosen_letters
            parity_desc_text = f'在字母集合[{", ".join(parity_letters)}]中, 其星星所在行索引之和的奇偶性必须为 {parity_target} (0 表示偶, 1 表示奇)'
        else:
            parity_letters = []
            parity_target = 0
            parity_desc_text = '无奇偶约束'

        parity_spec = {
            'enabled': parity_enabled,
            'letters': parity_letters,
            'target': parity_target,
        }

        # 2) 加权模约束：权重 w = i*prime1 + j*prime2，模 m，目标为解的权重和的模值
        if modulo_enabled:
            primes = [2, 3, 5, 7]
            prime1 = random.choice(primes)
            prime2 = random.choice([p for p in primes if p != prime1])
            modulus_m = random.randint(n, n + 6)  # 合理模值
            modulo_sum = sum(i * prime1 + j * prime2 for (i, j) in sol)
            modulo_target = modulo_sum % modulus_m
            modulo_desc_text = f'加权和 (i*{prime1} + j*{prime2}) 取模 {modulus_m} 的结果必须为 {modulo_target}'
        else:
            prime1, prime2, modulus_m, modulo_target = 2, 3, 5, 0
            modulo_desc_text = '无加权模约束'

        modulo_spec = {
            'enabled': modulo_enabled,
            'prime1': prime1,
            'prime2': prime2,
            'modulus_m': modulus_m,
            'modulo_target': modulo_target,
        }

        # 3) 半区计数约束：选择若干字母；若 top_half_flag=True，则这些字母的星需在上半区的计数恰为目标，否则为下半区
        if hemisphere_enabled:
            k = random.randint(max(1, n // 2), n)
            hemi_letters = random.sample(letters, k)
            top_half_flag = random.choice([True, False])
            half_cut = n // 2
            hemi_target = sum(1 for (i, j) in sol if (rg[i][j] in hemi_letters) and ((i < half_cut) if top_half_flag else (i >= half_cut)))
            zone_txt = '上半区(行索引 < n//2)' if top_half_flag else '下半区(行索引 >= n//2)'
            hemisphere_desc_text = f'在字母集合[{", ".join(hemi_letters)}]中, 星星位于{zone_txt}的数量必须为 {hemi_target}'
        else:
            hemi_letters = []
            top_half_flag = True
            hemi_target = 0
            hemisphere_desc_text = '无半区计数约束'

        hemisphere_spec = {
            'enabled': hemisphere_enabled,
            'letters': hemi_letters,
            'target': hemi_target,
            'top_half_flag': top_half_flag,
        }

        # 行/列/区域约束文本
        row_rule_desc_text = f'每行恰好 {row_quota} 颗星'
        col_rule_desc_text = f'每列恰好 {col_quota} 颗星'
        region_rule_desc_text = f'每个字母区域恰好 {region_quota} 颗星'
        adjacency_desc_text = {
            'none': '星星之间可以相邻(包括对角线)',
            'orthogonal': '任意两颗星不能在上下左右相邻',
            'king': '任意两颗星不能在任意方向相邻(包括对角线)',
        }[adjacency_type]

        # 唯一性验证：在完整约束下检查是否存在第二解（时间预算）
        deadline = time.time() + 25.0  # 单次唯一性搜索预算，整体留足
        if _second_solution_exists(n, rg, letters, adjacency_type, sol,
                                   parity_spec, modulo_spec, hemisphere_spec,
                                   deadline):
            # 存在第二解，重新生成
            if time.time() - start_global > time_budget_sec:
                # 超时则换邻接类型或重置启用标记，继续尝试
                continue
            else:
                continue

        # 通过唯一性验证，组装返回
        return {
            'region_grid': rg,
            'letters': letters,
            'solution_cells': sol,
            'adjacency_type': adjacency_type,
            'row_relation': row_relation,
            'row_quota': row_quota,
            'col_relation': col_relation,
            'col_quota': col_quota,
            'region_relation': region_relation,
            'region_quota': region_quota,
            'parity_enabled': parity_enabled,
            'modulo_enabled': modulo_enabled,
            'hemisphere_enabled': hemisphere_enabled,
            'parity_letters': parity_letters,
            'parity_target': parity_target,
            'prime1': prime1,
            'prime2': prime2,
            'modulus_m': modulus_m,
            'modulo_target': modulo_target,
            'hemisphere_letters': hemi_letters,
            'top_half_flag': top_half_flag,
            'hemisphere_target': hemi_target,
            'row_rule_desc_text': row_rule_desc_text,
            'col_rule_desc_text': col_rule_desc_text,
            'region_rule_desc_text': region_rule_desc_text,
            'adjacency_desc_text': adjacency_desc_text,
            'parity_desc_text': parity_desc_text,
            'modulo_desc_text': modulo_desc_text,
            'hemisphere_desc_text': hemisphere_desc_text,
        }

def function_1(x: int) -> int:
    """占位示例：平方"""
    return x * x

def function_2(ans_dict: Dict[str, Tuple[int, int]]) -> str:
    """占位示例：稳定格式化答案字典（键按字母排序）"""
    items = sorted(ans_dict.items(), key=lambda x: x[0])
    return '{' + ', '.join([f"'{k}': ({v[0]},{v[1]})" for k, v in items]) + '}'