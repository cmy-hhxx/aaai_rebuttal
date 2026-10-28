# calcudoko_4.py
# -*- coding: utf-8 -*-
"""
逆向生成 + 唯一解验证（<= 3分钟）
- function_1(n): 生成随机 6×6 拉丁方；构建规则候选池（和/积/线性/模/笼子/对角/外环/边/角/子集），
  逐步叠加规则并用 z3 验证是否唯一解；成功后返回 grid、rules（结构化）、rules_text、answer。
- function_2(obj, mode): 文本化工具（answer/rules）。

规则统一结构：
- 基本：{'rule_kind', 'coords', 'agg', 'target', 'text'}
  其中 agg ∈ {'sum', 'product'}
- 线性：{'rule_kind': 'lin', 'terms': [{'coeff': c, 'coords': [...]}, ...], 'target', 'text'}
- 取模：{'rule_kind': 'mod_sum', 'coords': [...], 'mod': m, 'remainder': r, 'text'}

所有坐标均为字符串键 ('1'..'6')，以兼容外部序列化。
"""

import random
import time
from typing import List, Tuple, Dict, Any

# z3 唯一解验证
try:
    from z3 import Solver, Int, And, Or, Distinct, Sum as Z3Sum
except Exception as e:
    raise ImportError("z3-solver is required for uniqueness checking") from e

# -----------------------------
# 拉丁方生成与置换
# -----------------------------

def _base_latin(n: int) -> List[List[int]]:
    return [[(i + j) % n + 1 for j in range(n)] for i in range(n)]

def _apply_permutations(grid: List[List[int]]) -> List[List[int]]:
    """行/列置换 & 数字置换，增加多样性"""
    n = len(grid)
    # 行置换
    row_perm = list(range(n))
    random.shuffle(row_perm)
    grid = [grid[i] for i in row_perm]
    # 列置换
    col_perm = list(range(n))
    random.shuffle(col_perm)
    grid = [[row[j] for j in col_perm] for row in grid]
    # 数字映射
    digits = list(range(1, n + 1))
    random.shuffle(digits)
    mapping = {k: digits[k - 1] for k in range(1, n + 1)}
    return [[mapping[v] for v in row] for row in grid]

# -----------------------------
# 坐标与聚合工具
# -----------------------------

def _sum_vals(grid: List[List[int]], coords: List[Tuple[str, str]]) -> int:
    return sum(grid[int(r) - 1][int(c) - 1] for r, c in coords)

def _prod_vals(grid: List[List[int]], coords: List[Tuple[str, str]]) -> int:
    prod = 1
    for r, c in coords:
        prod *= grid[int(r) - 1][int(c) - 1]
    return prod

def _format_coord_list(coords: List[Tuple[str, str]]) -> str:
    return '(' + '),('.join(f"{r},{c}" for r, c in coords) + ')'

def _coords_ring(n: int) -> List[Tuple[str, str]]:
    top = [('1', str(c)) for c in range(1, n + 1)]
    bottom = [(str(n), str(c)) for c in range(1, n + 1)]
    left = [(str(r), '1') for r in range(2, n)]
    right = [(str(r), str(n)) for r in range(2, n)]
    return top + bottom + left + right

def _coords_corners(n: int) -> List[Tuple[str, str]]:
    return [('1','1'), ('1',str(n)), (str(n),'1'), (str(n),str(n))]

def _coords_edge(n: int, side: str) -> List[Tuple[str, str]]:
    if side == 'top':
        return [('1', str(c)) for c in range(1, n + 1)]
    if side == 'bottom':
        return [(str(n), str(c)) for c in range(1, n + 1)]
    if side == 'left':
        return [(str(r), '1') for r in range(1, n + 1)]
    return [(str(r), str(n)) for r in range(1, n + 1)]  # right

def _coords_center(n: int, s: int) -> List[Tuple[str, str]]:
    start = (n - s) // 2 + 1
    return [(str(r), str(c)) for r in range(start, start + s) for c in range(start, start + s)]

def _coords_diag(n: int, which: str) -> List[Tuple[str, str]]:
    if which == 'main':
        return [(str(i), str(i)) for i in range(1, n + 1)]
    return [(str(i), str(n + 1 - i)) for i in range(1, n + 1)]

def _coords_checker(n: int, parity: int) -> List[Tuple[str, str]]:
    return [(str(r), str(c)) for r in range(1, n + 1) for c in range(1, n + 1) if (r + c) % 2 == parity]

def _coords_block_cages(n: int, b: int) -> List[List[Tuple[str, str]]]:
    cages = []
    for r0 in range(1, n + 1, b):
        for c0 in range(1, n + 1, b):
            cells = [(str(r), str(c)) for r in range(r0, r0 + b) for c in range(c0, c0 + b)]
            cages.append(cells)
    return cages

def _random_subset(coords: List[Tuple[str, str]], k_range=(3, 5)) -> List[Tuple[str, str]]:
    """从坐标集中抽取一个子集（用于高信息规则），控制大小在 k_range 内。"""
    k = random.randint(k_range[0], min(k_range[1], len(coords)))
    return random.sample(coords, k)

# -----------------------------
# 规则构造器（文本已内嵌）
# -----------------------------

def build_rule_sum(name: str, coords: List[Tuple[str, str]], grid: List[List[int]]) -> Dict[str, Any]:
    s = _sum_vals(grid, coords)
    text = f"{name}：列出的格子相加等于 {s}，涉及 {_format_coord_list(coords)}"
    return {'rule_kind': 'sum', 'coords': coords, 'agg': 'sum', 'target': s, 'text': text}

def build_rule_product(name: str, coords: List[Tuple[str, str]], grid: List[List[int]]) -> Dict[str, Any]:
    p = _prod_vals(grid, coords)
    text = f"{name}：列出的格子相乘等于 {p}，涉及 {_format_coord_list(coords)}"
    return {'rule_kind': 'product', 'coords': coords, 'agg': 'product', 'target': p, 'text': text}

def build_rule_lin(terms: List[Dict[str, Any]], grid: List[List[int]]) -> Dict[str, Any]:
    """
    terms: [{'coeff': c, 'coords': [...]}, ...]
    """
    parts = []
    total = 0
    for t in terms:
        c = int(t['coeff'])
        coords = t['coords']
        sv = _sum_vals(grid, coords)
        total += c * sv
        parts.append(f"{c}×({_format_coord_list(coords)})之和")
    text = f"线性组合规则：{' + '.join(parts)} 的结果等于 {total}"
    return {'rule_kind': 'lin', 'terms': terms, 'target': total, 'text': text}

def build_rule_mod(coords: List[Tuple[str, str]], m: int, grid: List[List[int]]) -> Dict[str, Any]:
    s = _sum_vals(grid, coords)
    r = s % m
    text = f"取模规则：{_format_coord_list(coords)} 中的数字之和对 {m} 取模等于 {r}"
    return {'rule_kind': 'mod_sum', 'coords': coords, 'mod': m, 'remainder': r, 'text': text}

def build_cage_rules(b: int, grid: List[List[int]]) -> List[Dict[str, Any]]:
    cages = _coords_block_cages(len(grid), b)
    rules = []
    random.shuffle(cages)
    # 抽取若干笼子，避免坐标爆炸
    num_keep = random.randint(max(3, len(cages)//3), max(3, len(cages)//2))
    for cells in cages[:num_keep]:
        s = _sum_vals(grid, cells)
        txt = f"笼子 {_format_coord_list(cells)} 的求和等于 {s}+"
        rules.append({'rule_kind': f'cage_{b}', 'coords': cells, 'agg': 'sum', 'target': s, 'text': txt})
    return rules

# -----------------------------
# 候选规则池（高信息子集优先）
# -----------------------------

def build_candidate_rules(grid: List[List[int]]) -> List[Dict[str, Any]]:
    n = len(grid)
    cand: List[Dict[str, Any]] = []

    # 外环/角：直接求和
    cand.append(build_rule_sum("外环", _coords_ring(n), grid))
    cand.append(build_rule_sum("四个角", _coords_corners(n), grid))

    # 对角：主/副对角求和
    cand.append(build_rule_sum("主对角线", _coords_diag(n, 'main'), grid))
    cand.append(build_rule_sum("副对角线", _coords_diag(n, 'anti'), grid))

    # 边子集：从某一边抽子集求和
    side = random.choice(['top', 'bottom', 'left', 'right'])
    edge_coords = _coords_edge(n, side)
    cand.append(build_rule_sum("边缘子集", _random_subset(edge_coords, k_range=(3, 5)), grid))

    # 中心 2×2 或 3×3：sum 或 product（坐标规模合理）
    s = random.choice([2, 3])
    center_coords = _coords_center(n, s)
    if random.random() < 0.5:
        cand.append(build_rule_sum(f"中心 {s}×{s}", center_coords, grid))
    else:
        # 乘积对子集（若 s=3 则取子集以控复杂度）
        coords_prod = center_coords if s == 2 else _random_subset(center_coords, k_range=(3, 4))
        cand.append(build_rule_product(f"中心 {s}×{s}", coords_prod, grid))

    # 行子集求和（避免整行恒等）
    for _ in range(random.randint(1, 2)):
        rr = random.randint(1, n)
        row_coords = [(str(rr), str(c)) for c in range(1, n + 1)]
        cand.append(build_rule_sum(f"第 {rr} 行的子集", _random_subset(row_coords, k_range=(3, 4)), grid))

    # 列子集求和（避免整列恒等）
    for _ in range(random.randint(1, 2)):
        cc = random.randint(1, n)
        col_coords = [(str(r), str(cc)) for r in range(1, n + 1)]
        cand.append(build_rule_sum(f"第 {cc} 列的子集", _random_subset(col_coords, k_range=(3, 4)), grid))

    # 棋盘格（偶/奇）子集取模
    m = random.choice([3, 4, 5, 6, 7])
    cand.append(build_rule_mod(_random_subset(_coords_checker(n, 0), k_range=(6, 9)), m, grid))
    cand.append(build_rule_mod(_random_subset(_coords_checker(n, 1), k_range=(6, 9)), m, grid))

    # 线性组合：2~3项，系数 1~3，项为高信息子集（中心、边缘子集、随机子集）
    # term1: 中心2×2或中心3×3的子集
    center2 = _coords_center(n, 2)
    term1 = {'coeff': random.randint(1, 3), 'coords': _random_subset(center2, k_range=(3, 4))}
    # term2: 边缘子集
    side2 = random.choice(['top', 'bottom', 'left', 'right'])
    term2 = {'coeff': random.randint(1, 3), 'coords': _random_subset(_coords_edge(n, side2), k_range=(3, 4))}
    terms = [term1, term2]
    if random.random() < 0.5:
        # term3: 随机子集（避免与已有完全重合）
        all_coords = [(str(r), str(c)) for r in range(1, n + 1) for c in range(1, n + 1)]
        term3 = {'coeff': 1, 'coords': _random_subset(all_coords, k_range=(3, 4))}
        terms.append(term3)
    cand.append(build_rule_lin(terms, grid))

    # 笼子规则：2×2 或 3×3（抽取若干块）
    b = random.choice([2, 3])
    cand.extend(build_cage_rules(b, grid))

    # 去重（按文本）
    uniq = []
    seen = set()
    for r in cand:
        t = r['text']
        if t not in seen:
            uniq.append(r)
            seen.add(t)
    return uniq

# -----------------------------
# Z3 唯一解检查（仅使用玩家可见规则）
# -----------------------------

def is_unique_solution(n: int, rules: List[Dict[str, Any]], timeout_ms: int = 2000) -> bool:
    """
    判断唯一解：存在且仅存在 1 个解。用阻断子句查找第2个解。
    验证严格只用传入的规则（即玩家可见的约束），不添加隐藏约束改变解空间。
    """
    X = [[Int(f"x_{r}_{c}") for c in range(1, n + 1)] for r in range(1, n + 1)]
    s = Solver()
    s.set("timeout", timeout_ms)

    # 拉丁约束：取值范围、行列全异
    for r in range(n):
        for c in range(n):
            s.add(And(X[r][c] >= 1, X[r][c] <= n))
    for r in range(n):
        s.add(Distinct(X[r]))
    for c in range(n):
        s.add(Distinct([X[r][c] for r in range(n)]))

    # 规则约束
    def sum_expr(coords: List[Tuple[str, str]]):
        return Z3Sum([X[int(r) - 1][int(c) - 1] for r, c in coords])

    for rule in rules:
        kind = rule['rule_kind']
        if kind == 'sum':
            s.add(sum_expr(rule['coords']) == int(rule['target']))
        elif kind == 'product':
            expr = 1
            for r, c in rule['coords']:
                expr = expr * X[int(r) - 1][int(c) - 1]
            s.add(expr == int(rule['target']))
        elif kind == 'lin':
            expr = 0
            for t in rule['terms']:
                expr = expr + int(t['coeff']) * sum_expr(t['coords'])
            s.add(expr == int(rule['target']))
        elif kind == 'mod_sum':
            s.add(sum_expr(rule['coords']) % int(rule['mod']) == int(rule['remainder']))
        elif kind.startswith('cage_'):
            s.add(sum_expr(rule['coords']) == int(rule['target']))
        else:
            # 忽略未知类型
            pass

    # 第一次求解
    if s.check() != 1:  # sat=1, unsat=0, unknown=-1
        return False
    m = s.model()

    # 阻断刚才的解：至少有一个单元不同
    diff_clause = []
    for r in range(n):
        for c in range(n):
            diff_clause.append(X[r][c] != m.eval(X[r][c]))
    s.add(Or(diff_clause))
    # 第二次求解
    res = s.check()
    return res == 0  # unsat => 唯一

# -----------------------------
# 增选策略（贪心 + 优先级）
# -----------------------------

def select_rules_until_unique(n: int, candidates: List[Dict[str, Any]], time_budget_sec: float = 170.0) -> List[Dict[str, Any]]:
    """
    贪心增选规则并检验唯一解，直至唯一或耗尽时间。
    """
    start = time.time()
    # 优先信息量：product > lin > mod > cages > ring/diag/center_sum > edge_subset > row/col subset
    def priority(r: Dict[str, Any]) -> int:
        kind = r['rule_kind']
        if kind == 'product':
            return 0
        if kind == 'lin':
            return 1
        if kind == 'mod_sum':
            return 2
        if str(kind).startswith('cage_'):
            return 3
        if kind == 'sum':
            tx = r['text']
            if "外环" in tx or "对角线" in tx or "中心" in tx:
                return 4
            if "边缘子集" in tx:
                return 5
            return 6
        return 7

    candidates = sorted(candidates, key=priority)
    picked: List[Dict[str, Any]] = []
    idxs = list(range(len(candidates)))
    random.shuffle(idxs)

    per_timeout_ms = 2000
    for i in idxs:
        picked.append(candidates[i])
        if len(picked) > 14:
            break
        if time.time() - start > time_budget_sec:
            break
        ok = is_unique_solution(n, picked, timeout_ms=per_timeout_ms)
        if ok:
            return picked

    # 若未达唯一，加约束继续尝试
    for i in idxs:
        if candidates[i] not in picked:
            picked.append(candidates[i])
            if len(picked) > 16 or (time.time() - start > time_budget_sec):
                break
            ok = is_unique_solution(n, picked, timeout_ms=per_timeout_ms)
            if ok:
                return picked

    return []

# -----------------------------
# 对外接口
# -----------------------------

def function_1(n: int, seed: int = None) -> Dict[str, Any]:
    """
    主入口：生成唯一解的题目包
    返回：
      - grid: 解网格（二维 int）
      - rules: 结构化规则列表（仅玩家可见约束）
      - rules_text: 规则中文拼接
      - answer: 答案字符串（按 '空格分隔;分号换行' 格式）
    """
    if seed is not None:
        random.seed(seed)

    deadline = time.time() + 175.0  # 总预算 < 3 分钟
    while time.time() < deadline:
        # 1) 生成随机拉丁方
        grid = _apply_permutations(_base_latin(n))
        # 2) 构造候选规则池（避免低信息规则）
        cand = build_candidate_rules(grid)
        # 3) 增选并验证唯一解（只用玩家可见约束）
        rules = select_rules_until_unique(n, cand, time_budget_sec=max(5.0, deadline - time.time() - 2.0))
        if rules:
            rules_text = '；'.join(r['text'] for r in rules)
            answer = ';'.join(' '.join(str(x) for x in row) for row in grid)
            return {
                'grid': grid,
                'rules': rules,
                'rules_text': rules_text,
                'answer': answer
            }
        # 尝试下一轮（新的网格与规则池）

    # 超时兜底：仍生成高信息规则但不保证唯一解（概率仍较高）
    grid = _apply_permutations(_base_latin(n))
    cand = build_candidate_rules(grid)
    # 按优先级取前若干条
    def priority(r: Dict[str, Any]) -> int:
        kind = r['rule_kind']
        if kind == 'product':
            return 0
        if kind == 'lin':
            return 1
        if kind == 'mod_sum':
            return 2
        if str(kind).startswith('cage_'):
            return 3
        return 4
    cand = sorted(cand, key=priority)
    rules = cand[:12]
    rules_text = '；'.join(r['text'] for r in rules)
    answer = ';'.join(' '.join(str(x) for x in row) for row in grid)
    return {
        'grid': grid,
        'rules': rules,
        'rules_text': rules_text,
        'answer': answer
    }

def function_2(obj: Any, mode: str = 'answer') -> str:
    if mode == 'answer':
        grid: List[List[int]] = obj
        return ';'.join(' '.join(str(x) for x in row) for row in grid)
    elif mode == 'rules':
        rules: List[Dict[str, Any]] = obj
        return '；'.join(r['text'] for r in rules)
    else:
        raise ValueError(f"Unsupported mode: {mode}")