# skyscraper_puzzle_2.py
# 高阶泛化辅助库：逆向生成答案矩阵，派生颜色/可见度/不等式/片段和/进阶约束，独立唯一性验证（≤3分钟）
from typing import List, Dict, Tuple
import random
from z3 import And, If, IntVal, Sum, Solver, Int, Distinct, Or, sat

# -----------------------------
# 可见度计算（具体序列与符号序列）
# -----------------------------
def _visibility_count_expr_seq(seq: List[int]) -> int:
    count = 0
    current_max = -1
    for x in seq:
        if x > current_max:
            count += 1
            current_max = x
    return count

def _visibility_count_expr(sym_seq):
    assert len(sym_seq) > 0, '序列长度必须为正'
    current_max = sym_seq[0]
    count = IntVal(1)
    for i in range(1, len(sym_seq)):
        higher = sym_seq[i] > current_max
        count = count + If(higher, 1, 0)
        current_max = If(higher, sym_seq[i], current_max)
    return count

# -----------------------------
# 约束构造（保留以备扩展验证）
# -----------------------------
def function_1(h, top: List[int], bottom: List[int], left: List[int], right: List[int], n: int):
    """
    四边可见度约束（符号版），返回 Z3 Bool 表达式列表。
    使用键 ('r{i}', 'c{j}')
    """
    cons = []
    for r in range(n):
        row = [h[(f"r{r}", f"c{c}")] for c in range(n)]
        cons.append(_visibility_count_expr(row) == left[r])
        cons.append(_visibility_count_expr(list(reversed(row))) == right[r])
    for c in range(n):
        col = [h[(f"r{r}", f"c{c}")] for r in range(n)]
        cons.append(_visibility_count_expr(col) == top[c])
        cons.append(_visibility_count_expr([h[(f"r{r}", f"c{c}")] for r in list(reversed(range(n)))]) == bottom[c])
    return cons

def function_2(h, inequalities: List[Dict]):
    """
    不等式约束（符号版），返回 Z3 Bool 表达式列表。
    输入坐标为 1 基，符号键 ('r{i}', 'c{j}')
    """
    cons = []
    for item in inequalities:
        t = item['type']
        ar, ac = item['a']
        br, bc = item['b']
        ar0, ac0 = ar - 1, ac - 1
        br0, bc0 = br - 1, bc - 1
        akey = (f"r{ar0}", f"c{ac0}")
        bkey = (f"r{br0}", f"c{bc0}")
        if t == '<':
            cons.append(h[akey] < h[bkey])
        elif t == '>':
            cons.append(h[akey] > h[bkey])
        else:
            raise ValueError(f'未知不等式类型: {t}')
    return cons

# -----------------------------
# 颜色规则与派生
# -----------------------------
def pick_parity_scheme() -> str:
    """
    随机选择颜色规则：
    - 'odd_red': 红格为奇数，蓝格为偶数
    - 'even_red': 红格为偶数，蓝格为奇数
    """
    return random.choice(['odd_red', 'even_red'])

def derive_color(grid: List[List[int]], parity_scheme: str) -> List[List[str]]:
    """
    根据 parity_scheme 派生颜色矩阵。
    """
    n = len(grid)
    color = []
    for r in range(n):
        row = []
        for c in range(n):
            v = grid[r][c]
            odd = (v % 2 == 1)
            if parity_scheme == 'odd_red':
                row.append('R' if odd else 'B')
            else:
                row.append('R' if not odd else 'B')
        color.append(row)
    return color

# -----------------------------
# 文本模板与词汇风格
# -----------------------------
def pick_phrases() -> Dict[str, str]:
    """
    随机选择文本风格，返回题目标题与词汇用法。
    """
    titles = [
        '商务区风向摩天楼逻辑挑战',
        '彩色地块高度谜题',
        '红蓝地块可见度与风向约束题',
        '城市摩天楼高度分配',
        '风道规划下的摩天楼布局'
    ]
    gt_words = ['大于', '更高于', '高于']
    lt_words = ['小于', '低于', '矮于']
    vis_terms = ['可见度线索', '观测线索', '视野线索']
    return {
        'title': random.choice(titles),
        'gt_word': random.choice(gt_words),
        'lt_word': random.choice(lt_words),
        'vis_term': random.choice(vis_terms),
    }

# -----------------------------
# 可见度线索子集的构造与描述
# -----------------------------
def random_visibility_mask(min_count: int = 1) -> List[str]:
    """
    随机选择至少 min_count 个可见度边：从 ['top','bottom','left','right'] 中抽样。
    """
    edges = ['top', 'bottom', 'left', 'right']
    k = random.randint(min_count, len(edges))
    random.shuffle(edges)
    return edges[:k]

def function_3(grid: List[List[int]]) -> Dict[str, List[int]]:
    """
    从矩阵计算四侧可见度线索。
    返回 {'top': [...], 'bottom': [...], 'left': [...], 'right': [...]}。
    """
    n = len(grid)
    top = []
    bottom = []
    left = []
    right = []
    # 列方向
    for c in range(n):
        col = [grid[r][c] for r in range(n)]
        top.append(_visibility_count_expr_seq(col))
        bottom.append(_visibility_count_expr_seq(list(reversed(col))))
    # 行方向
    for r in range(n):
        row = grid[r][:]
        left.append(_visibility_count_expr_seq(row))
        right.append(_visibility_count_expr_seq(list(reversed(row))))
    return {'top': top, 'bottom': bottom, 'left': left, 'right': right}

def build_visibility_subset(clues: Dict[str, List[int]], vis_mask: List[str]) -> Dict[str, object]:
    """
    从完整可见度线索中选择子集，并构造描述文本。
    返回：
      {'vals': {'top': [...], ...}, 'desc': '可见度线索: top=[...], left=[...]'}
    """
    parts = []
    vals = {}
    for key in vis_mask:
        vals[key] = clues[key]
        arr_str = str(clues[key])
        parts.append(f"{key}={arr_str}")
    desc = '可见度线索: ' + ', '.join(parts)
    return {'vals': vals, 'desc': desc}

# -----------------------------
# 随机拉丁方答案生成（大规模多样性）
# -----------------------------
def build_grid(n: int) -> List[List[int]]:
    """
    随机生成 n×n 拉丁方：
    1) 基础循环拉丁方 base[i][j] = ((i * k + j) % n) + 1，其中 k 与 n 互素；随机 k
    2) 随机置换行/列
    3) 随机置换数值 1..n
    """
    coprimes = [k for k in range(1, n) if _gcd(k, n) == 1]
    k = random.choice(coprimes)
    base = [[((i * k + j) % n) + 1 for j in range(n)] for i in range(n)]
    row_perm = list(range(n))
    col_perm = list(range(n))
    random.shuffle(row_perm)
    random.shuffle(col_perm)
    permuted = [[base[row_perm[i]][col_perm[j]] for j in range(n)] for i in range(n)]
    val_perm = list(range(1, n + 1))
    random.shuffle(val_perm)
    mapping = {v: val_perm[v - 1] for v in range(1, n + 1)}
    grid = [[mapping[permuted[i][j]] for j in range(n)] for i in range(n)]
    return grid

def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a

# -----------------------------
# 从矩阵派生相邻不等式（风向约束）
# -----------------------------
def gen_inequalities(grid: List[List[int]], ineq_num: int) -> List[Dict]:
    """
    从矩阵真实大小关系派生相邻不等式，保证无重复，坐标为 1 基。
    随机抽样相邻边 ineq_num 条；方向表达随机化增强多样性。
    """
    n = len(grid)
    edges: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    # 水平相邻
    for r in range(n):
        for c in range(n - 1):
            edges.append(((r + 1, c + 1), (r + 1, c + 2)))
    # 垂直相邻
    for r in range(n - 1):
        for c in range(n):
            edges.append(((r + 1, c + 1), (r + 2, c + 1)))
    total = len(edges)
    k = min(max(1, ineq_num), total)
    random.shuffle(edges)
    chosen = edges[:k]
    ineqs: List[Dict] = []
    for a, b in chosen:
        ar, ac = a
        br, bc = b
        va = grid[ar - 1][ac - 1]
        vb = grid[br - 1][bc - 1]
        if va < vb:
            if random.random() < 0.5:
                ineqs.append({'type': '<', 'a': a, 'b': b})
            else:
                ineqs.append({'type': '>', 'a': b, 'b': a})
        else:
            if random.random() < 0.5:
                ineqs.append({'type': '>', 'a': a, 'b': b})
            else:
                ineqs.append({'type': '<', 'a': b, 'b': a})
    return ineqs

def format_inequalities(inequalities: List[Dict], phrases: Dict[str, str]) -> str:
    """
    将不等式列表渲染为自然语言片段，使用随机词汇风格。
    示例：(a lt b); (a gt b)
    """
    parts = []
    lt = phrases.get('lt_word', '小于')
    gt = phrases.get('gt_word', '大于')
    for it in inequalities:
        a = it['a']
        b = it['b']
        op = it['type']
        if op == '<':
            parts.append(f"({a} {lt} {b})")
        else:
            parts.append(f"({a} {gt} {b})")
    return '; '.join(parts)

# -----------------------------
# 片段和提示（派生自矩阵）
# -----------------------------
def gen_segment_sum_clues(grid: List[List[int]], seg_num: int) -> Dict[str, object]:
    """
    随机生成片段和提示：在某行或某列上选取长度为 2 或 3 的位置集合，给出这些位置的和。
    返回：
      {'clues': [{'axis':'row'|'col','idx':i,'pos':[p1,p2,...],'sum':S}, ...],
       'desc': '片段和提示: row i at cols [..] sum=S; col j at rows [..] sum=T; ...'}
    """
    n = len(grid)
    if seg_num <= 0:
        return {'clues': [], 'desc': '无片段和提示'}
    candidates = []
    # 行片段
    for r in range(n):
        for length in [2, 3]:
            for c in range(n - length + 1):
                pos = list(range(c + 1, c + length + 1))
                S = sum(grid[r][p - 1] for p in pos)
                candidates.append(('row', r + 1, pos, S))
    # 列片段
    for c in range(n):
        for length in [2, 3]:
            for r in range(n - length + 1):
                pos = list(range(r + 1, r + length + 1))
                S = sum(grid[p - 1][c] for p in pos)
                candidates.append(('col', c + 1, pos, S))
    random.shuffle(candidates)
    k = min(seg_num, len(candidates))
    chosen = candidates[:k]
    clues = []
    parts = []
    for axis, idx, pos, S in chosen:
        if axis == 'row':
            clues.append({'axis': 'row', 'idx': idx, 'pos': pos, 'sum': S})
            parts.append(f"row {idx} 在列 {pos} 的楼高和为 {S}")
        else:
            clues.append({'axis': 'col', 'idx': idx, 'pos': pos, 'sum': S})
            parts.append(f"col {idx} 在行 {pos} 的楼高和为 {S}")
    desc = '片段和提示: ' + '; '.join(parts)
    return {'clues': clues, 'desc': desc}

# -----------------------------
# 进阶复合约束（派生自矩阵）
# -----------------------------
def gen_advanced_constraints(grid: List[List[int]], n: int) -> Dict[str, object]:
    """
    随机生成 1..min(5, 2n) 条进阶约束，类型包括：
    - peak_pos_row: 某行的最大值 n 位于指定列
    - peak_pos_col: 某列的最大值 n 位于指定行
    - band_sum_row: 某行相邻两格之和为特定值
    - chain_order_row: 某行两个位置形成严格大小关系
    返回：
      {'data': [{'type':..., <args>}, ...], 'desc': '进阶约束: ...'}
    """
    kmax = min(5, 2 * n)
    k = random.randint(1, kmax)
    constraints = []
    parts = []
    types = ['peak_pos_row', 'peak_pos_col', 'band_sum_row', 'chain_order_row']
    for _ in range(k):
        t = random.choice(types)
        if t == 'peak_pos_row':
            r = random.randrange(n)
            c = grid[r].index(n)
            constraints.append({'type': 'peak_pos_row', 'row': r + 1, 'col': c + 1})
            parts.append(f"row {r + 1} 的最高楼位于列 {c + 1}")
        elif t == 'peak_pos_col':
            c = random.randrange(n)
            col_vals = [grid[r][c] for r in range(n)]
            r = col_vals.index(n)
            constraints.append({'type': 'peak_pos_col', 'col': c + 1, 'row': r + 1})
            parts.append(f"col {c + 1} 的最高楼位于行 {r + 1}")
        elif t == 'band_sum_row':
            r = random.randrange(n)
            c = random.randrange(n - 1)
            Sval = grid[r][c] + grid[r][c + 1]
            constraints.append({'type': 'band_sum_row', 'row': r + 1, 'c1': c + 1, 'c2': c + 2, 'sum': Sval})
            parts.append(f"row {r + 1} 的列 {c + 1} 与列 {c + 2} 之和为 {Sval}")
        elif t == 'chain_order_row':
            r = random.randrange(n)
            c1 = random.randrange(n)
            c2 = random.randrange(n)
            while c2 == c1:
                c2 = random.randrange(n)
            v1 = grid[r][c1]
            v2 = grid[r][c2]
            if v1 == v2:
                continue
            op = '<' if v1 < v2 else '>'
            constraints.append({'type': 'chain_order_row', 'row': r + 1, 'c1': c1 + 1, 'c2': c2 + 1, 'op': op})
            parts.append(f"row {r + 1} 的列 {c1 + 1} {('小于' if op=='<' else '大于')} 列 {c2 + 1}")
    if not parts:
        parts = ['无进阶约束']
    return {'data': constraints, 'desc': '进阶约束: ' + '; '.join(parts)}

# -----------------------------
# 独立唯一性验证（≤3分钟）
# -----------------------------
def verify_unique(n: int,
                  color: List[List[str]],
                  parity_scheme: str,
                  vis_vals: Dict[str, List[int]],
                  inequalities: List[Dict],
                  seg_sum_clues: List[Dict],
                  adv_data: List[Dict]) -> bool:
    """
    独立构建 Z3 模型（不锁定答案），施加以下约束：
    - 拉丁方：行列 Distinct，值域 1..n
    - 颜色规则：根据 color 与 parity_scheme 施加奇偶约束
    - 风向不等式：相邻大小关系
    - 可见度子集：选定边的可见度等于给定值
    - 片段和提示：行或列片段的和
    - 进阶约束：peak_pos_row/peak_pos_col/band_sum_row/chain_order_row
    超时：≤180000ms；验证唯一性：找到一个解后加入阻断子句，再次求解。
    """
    s = Solver()
    s.set('timeout', 180000)  # 180秒内完成
    H = [[Int(f"Hv_{r}_{c}") for c in range(n)] for r in range(n)]
    # 值域与拉丁方
    for r in range(n):
        for c in range(n):
            s.add(H[r][c] >= 1, H[r][c] <= n)
    for r in range(n):
        s.add(Distinct(H[r]))
    for c in range(n):
        s.add(Distinct([H[r][c] for r in range(n)]))
    # 颜色奇偶
    for r in range(n):
        for c in range(n):
            if parity_scheme == 'odd_red':
                s.add(If(color[r][c] == 'R', H[r][c] % 2 == 1, H[r][c] % 2 == 0))
            else:
                s.add(If(color[r][c] == 'R', H[r][c] % 2 == 0, H[r][c] % 2 == 1))
    # 风向不等式
    for it in (inequalities or []):
        t = it['type']
        ar, ac = it['a']
        br, bc = it['b']
        ar0, ac0 = ar - 1, ac - 1
        br0, bc0 = br - 1, bc - 1
        if t == '<':
            s.add(H[ar0][ac0] < H[br0][bc0])
        else:
            s.add(H[ar0][ac0] > H[br0][bc0])
    # 可见度子集
    if vis_vals and 'left' in vis_vals:
        left = vis_vals['left']
        for r in range(n):
            s.add(_visibility_count_expr([H[r][c] for c in range(n)]) == left[r])
    if vis_vals and 'right' in vis_vals:
        right = vis_vals['right']
        for r in range(n):
            s.add(_visibility_count_expr([H[r][c] for c in list(reversed(range(n)))]) == right[r])
    if vis_vals and 'top' in vis_vals:
        top = vis_vals['top']
        for c in range(n):
            s.add(_visibility_count_expr([H[r][c] for r in range(n)]) == top[c])
    if vis_vals and 'bottom' in vis_vals:
        bottom = vis_vals['bottom']
        for c in range(n):
            s.add(_visibility_count_expr([H[r][c] for r in list(reversed(range(n)))]) == bottom[c])
    # 片段和提示
    for clue in (seg_sum_clues or []):
        axis = clue['axis']
        idx = clue['idx'] - 1
        pos = clue['pos']  # 1 基序列
        Sval = clue['sum']
        if axis == 'row':
            s.add(Sum([H[idx][p - 1] for p in pos]) == Sval)
        else:
            s.add(Sum([H[p - 1][idx] for p in pos]) == Sval)
    # 进阶约束
    for ad in (adv_data or []):
        t = ad['type']
        if t == 'peak_pos_row':
            r = ad['row'] - 1
            c = ad['col'] - 1
            s.add(H[r][c] == n)
        elif t == 'peak_pos_col':
            r = ad['row'] - 1
            c = ad['col'] - 1
            s.add(H[r][c] == n)
        elif t == 'band_sum_row':
            r = ad['row'] - 1
            c1 = ad['c1'] - 1
            c2 = ad['c2'] - 1
            Sval = ad['sum']
            s.add(H[r][c1] + H[r][c2] == Sval)
        elif t == 'chain_order_row':
            r = ad['row'] - 1
            c1 = ad['c1'] - 1
            c2 = ad['c2'] - 1
            op = ad['op']
            if op == '<':
                s.add(H[r][c1] < H[r][c2])
            else:
                s.add(H[r][c1] > H[r][c2])
    # 唯一性检查
    if s.check() != sat:
        return False
    m = s.model()
    block = Or([H[r][c] != m.evaluate(H[r][c]).as_long() for r in range(n) for c in range(n)])
    s.add(block)
    return s.check() != sat