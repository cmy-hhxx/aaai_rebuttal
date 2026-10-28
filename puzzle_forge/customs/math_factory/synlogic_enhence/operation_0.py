# operation_2.py
# 高阶随机规则、混合约束与评分唯一选择的数值求解器（含唯一性验证）
# 方程：
#   (t - a) ⊙L (b - t) = k * (t ⊙R c)
# 操作符：
#   op(x, y) = (Abs(x) if use_abs_x else x)^px * (Abs(y) if use_abs_y else y)^py
# 评分函数：
#   S(t) = w1*|t - b| + w2*|t - d| + w3*|t|
# 选择规则：
#   在满足硬约束的实根集合中，取评分最小者；若并列（≤score_tol），取较小 t；保证唯一答案。
# 时间限制：
#   搜索遵守 tlimit（≤ 3 分钟），通过自适应范围与步数保障效率。
# 唯一性验证：
#   ans_text 重算并核验：方程、约束与评分唯一性；不在题面文本暴露内部验证信息。

from typing import List, Tuple
import math
import time

def _op_val(x: float, y: float, use_abs_x: bool, use_abs_y: bool, px: int, py: int) -> float:
    xv = abs(x) if use_abs_x else x
    yv = abs(y) if use_abs_y else y
    return (xv ** px) * (yv ** py)

def _f_builder(a: float, b: float, c: float, k: float,
               use_abs_x_left: bool, use_abs_y_left: bool, px_left: int, py_left: int,
               use_abs_x_right: bool, use_abs_y_right: bool, px_right: int, py_right: int):
    def f(t: float) -> float:
        left = _op_val(t - a, b - t, use_abs_x_left, use_abs_y_left, px_left, py_left)
        right = _op_val(t, c, use_abs_x_right, use_abs_y_right, px_right, py_right)
        return left - k * right
    return f

def _bisection(f, lo: float, hi: float, tol: float = 1e-12, max_iter: int = 200) -> float:
    flo = f(lo)
    fhi = f(hi)
    # 容错：若端点不正常，返回中点以便后续验证过滤
    if not (math.isfinite(flo) and math.isfinite(fhi)):
        return 0.5 * (lo + hi)
    if flo == 0:
        return lo
    if fhi == 0:
        return hi
    if flo * fhi > 0:
        return 0.5 * (lo + hi)
    a, b = lo, hi
    for _ in range(max_iter):
        mid = 0.5 * (a + b)
        fmid = f(mid)
        if (b - a) < tol or abs(fmid) < 1e-13:
            return mid
        if flo * fmid <= 0:
            b = mid
            fhi = fmid
        else:
            a = mid
            flo = fmid
    return 0.5 * (a + b)

def _scan_and_bracket(f, lo: float, hi: float, steps: int, near_zero_thr: float = 1e-10):
    brackets = []
    near_zeros = []
    xs = [lo + (hi - lo) * i / steps for i in range(steps + 1)]
    prev_x = xs[0]
    prev_f = f(prev_x)
    if math.isfinite(prev_f) and abs(prev_f) < near_zero_thr:
        near_zeros.append(prev_x)
    for i in range(1, len(xs)):
        x = xs[i]
        fx = f(x)
        if math.isfinite(fx) and abs(fx) < near_zero_thr:
            near_zeros.append(x)
        if math.isfinite(prev_f) and math.isfinite(fx) and prev_f * fx <= 0:
            brackets.append((prev_x, x))
        prev_x, prev_f = x, fx
    return brackets, near_zeros

def _dedup(xs: List[float], eps: float = 1e-8) -> List[float]:
    if not xs:
        return []
    xs_sorted = sorted(xs)
    out = [xs_sorted[0]]
    for x in xs_sorted[1:]:
        if abs(x - out[-1]) > eps:
            out.append(x)
    return out

def _apply_constraints(roots: List[float], b: float, d: float,
                       c_num: int, c_types: List[str], c_params: List[Tuple]) -> List[float]:
    if c_num == 0 or not roots:
        return roots
    filtered = roots[:]
    for i in range(c_num):
        ctype = c_types[i]
        params = c_params[i]
        if ctype == 'interval':
            L, U = float(params[0]), float(params[1])
            filtered = [t for t in filtered if (t >= L - 1e-8 and t <= U + 1e-8)]
        elif ctype == 'dist_le':
            R = float(params[0])
            filtered = [t for t in filtered if abs(t - b) <= R + 1e-8]
        elif ctype == 'dist_ge':
            R = float(params[0])
            filtered = [t for t in filtered if abs(t - b) >= R - 1e-8]
        elif ctype == 'ratio_le':
            R = float(params[0])
            filtered = [t for t in filtered if (abs(t - b) / (1.0 + abs(t - d))) <= R + 1e-10]
        else:
            # 未知类型：忽略
            filtered = filtered
    return filtered

def _score(t: float, b: float, d: float, w1: float, w2: float, w3: float) -> float:
    return w1 * abs(t - b) + w2 * abs(t - d) + w3 * abs(t)

def _choose_unique(roots: List[float], b: float, d: float, w1: float, w2: float, w3: float,
                   score_tol: float) -> float:
    """
    评分唯一选择：先按评分升序，再按 t 升序；并列（≤score_tol）取较小 t。
    """
    if not roots:
        return None
    scored = [(t, _score(t, b, d, w1, w2, w3)) for t in roots]
    scored.sort(key=lambda z: (z[1], z[0]))
    best_s = scored[0][1]
    tied = [t for t, s in scored if abs(s - best_s) <= score_tol]
    return min(tied) if tied else scored[0][0]

def function_1(a: int, b: int, c: int, k: int, d: int, w1: int, w2: int, w3: int,
               tlimit: float, score_tol: float, verify_tol: float,
               use_abs_x_left: bool, use_abs_y_left: bool, px_left: int, py_left: int,
               use_abs_x_right: bool, use_abs_y_right: bool, px_right: int, py_right: int,
               c_num: int, c_types: List[str], c_params: List[Tuple]) -> List[float]:
    """
    主求解：
    1) 构造 f(t)，在 [−L,b] 与 [b,L] 扫描与二分，收集全部实根；
    2) 验证真根、去重；
    3) 应用硬约束过滤；
    4) 评分唯一选择并返回 [t*]；若无可行根，返回 []。
    时间限制：不超过 tlimit 秒。
    """
    start = time.time()
    f = _f_builder(a, b, c, k,
                   use_abs_x_left, use_abs_y_left, px_left, py_left,
                   use_abs_x_right, use_abs_y_right, px_right, py_right)

    # 自适应范围与步数
    scale = 1.0 + max(abs(a), abs(b), abs(c), k, px_left, py_left, px_right, py_right)
    L = max(12.0, 7.0 * scale)
    steps_left = int(max(300, 100 * scale))
    steps_right = int(max(300, 100 * scale))

    lo_left, hi_left = -L, float(b)
    lo_right, hi_right = float(b), L

    roots_candidates: List[float] = []

    # 左段扫描
    brackets_left, near_left = _scan_and_bracket(f, lo_left, hi_left, steps_left)
    for lo, hi in brackets_left:
        if time.time() - start > tlimit:
            break
        roots_candidates.append(_bisection(f, lo, hi))
    roots_candidates.extend(near_left)

    # 右段扫描
    brackets_right, near_right = _scan_and_bracket(f, lo_right, hi_right, steps_right)
    for lo, hi in brackets_right:
        if time.time() - start > tlimit:
            break
        roots_candidates.append(_bisection(f, lo, hi))
    roots_candidates.extend(near_right)

    # 真根过滤与去重
    verified = []
    for r in roots_candidates:
        val = f(r)
        if math.isfinite(val) and abs(val) < verify_tol:
            verified.append(r)
    roots_all = _dedup(verified)

    # 应用硬约束
    roots_feasible = _apply_constraints(roots_all, b, d, c_num, c_types, c_params)

    # 唯一选择
    if not roots_feasible:
        return []
    chosen = _choose_unique(roots_feasible, b, d, w1, w2, w3, score_tol)
    if chosen is None:
        return []
    return [chosen]

def function_2(ans: List[float], a: int, b: int, c: int, k: int, d: int, w1: int, w2: int, w3: int,
               score_tol: float, verify_tol: float,
               use_abs_x_left: bool, use_abs_y_left: bool, px_left: int, py_left: int,
               use_abs_x_right: bool, use_abs_y_right: bool, px_right: int, py_right: int,
               c_num: int, c_types: List[str], c_params: List[Tuple]) -> str:
    """
    唯一性验证与格式化：
    - 重建 f(t)，重新扫描并验证全部真根；
    - 应用硬约束，评分唯一选择；
    - 确认与入参答案一致；
    - 输出 '无实数解' 或 't = 数值'（保留6位小数）。
    """
    f = _f_builder(a, b, c, k,
                   use_abs_x_left, use_abs_y_left, px_left, py_left,
                   use_abs_x_right, use_abs_y_right, px_right, py_right)

    scale = 1.0 + max(abs(a), abs(b), abs(c), k, px_left, py_left, px_right, py_right)
    L = max(12.0, 7.0 * scale)
    steps_left = int(max(300, 100 * scale))
    steps_right = int(max(300, 100 * scale))

    lo_left, hi_left = -L, float(b)
    lo_right, hi_right = float(b), L

    roots_candidates: List[float] = []

    brackets_left, near_left = _scan_and_bracket(f, lo_left, hi_left, steps_left)
    for lo, hi in brackets_left:
        roots_candidates.append(_bisection(f, lo, hi))
    roots_candidates.extend(near_left)

    brackets_right, near_right = _scan_and_bracket(f, lo_right, hi_right, steps_right)
    for lo, hi in brackets_right:
        roots_candidates.append(_bisection(f, lo, hi))
    roots_candidates.extend(near_right)

    verified = []
    for r in roots_candidates:
        val = f(r)
        if math.isfinite(val) and abs(val) < verify_tol:
            verified.append(r)
    roots_all = _dedup(verified)

    roots_feasible = _apply_constraints(roots_all, b, d, c_num, c_types, c_params)

    if not roots_feasible:
        return '无实数解'
    unique_t = _choose_unique(roots_feasible, b, d, w1, w2, w3, score_tol)
    if unique_t is None:
        return '无实数解'

    # 一致性检查（答案必须是长度为 1 的列表）
    if not isinstance(ans, list) or len(ans) != 1:
        raise AssertionError('Answer should be a single-value list.')
    if abs(ans[0] - unique_t) > 1e-8:
        raise AssertionError(f'Answer mismatch: got {ans[0]}, expected {unique_t}')

    return f't = {unique_t:.6f}'