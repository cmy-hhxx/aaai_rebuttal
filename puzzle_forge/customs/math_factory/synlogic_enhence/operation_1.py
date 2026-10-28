# operation_5.py
# 正向生成 + 强凸判据唯一解验证（高效稳定）
# F(x) = α*x^2*|a - x|^r1 + β*|b - x|^r2 + γ*|x - m|^p + λ*x^2 + δ*[max(0, L - x)^t + max(0, x - U)^t]
# 参数域：a∈[0,3], alpha∈[1,2], beta∈[3,5], gamma∈[3,4], lam∈[4,5], delta∈[0,2], r1=r2=p=2, t∈{1,2}
# 唯一性依据：强凸判据 μ = 2(β + γ + λ) − α·a^2 > 0 ⇒ 全局唯一极小；加软约束仍保持强凸

import math
from typing import Tuple

def f_value(x: float, a: float, b: float, m: float,
            alpha: float, beta: float, gamma: float, lam: float, delta: float,
            r1: int, r2: int, p: int, t_pow: int, L: float, U: float) -> float:
    base = alpha * (x**2) * (abs(a - x) ** r1)        # quartic 非负
    term2 = beta * (abs(b - x) ** r2)                 # quadratic 非负
    term3 = gamma * (abs(x - m) ** p)                 # quadratic 非负
    term4 = lam * (x**2)                              # quadratic 严格凸
    out_left = (L - x) if x < L else 0.0
    out_right = (x - U) if x > U else 0.0
    penalty = delta * ((out_left ** t_pow) + (out_right ** t_pow))
    return base + term2 + term3 + term4 + penalty

def _golden_section(f, lo, hi, tol=1e-10, max_iter=160):
    # 全局单峰搜索（凸场景下有效）
    phi = (1 + 5**0.5) / 2
    invphi = 1 / phi
    x1 = hi - invphi * (hi - lo)
    x2 = lo + invphi * (hi - lo)
    f1 = f(x1)
    f2 = f(x2)
    for _ in range(max_iter):
        if abs(hi - lo) < tol:
            break
        if f1 < f2:
            hi = x2
            x2 = x1
            f2 = f1
            x1 = hi - invphi * (hi - lo)
            f1 = f(x1)
        else:
            lo = x1
            x1 = x2
            f1 = f2
            x2 = lo + invphi * (hi - lo)
            f2 = f(x2)
    xm = 0.5 * (lo + hi)
    return xm, f(xm)

def solve_minimum(a: float, b: float, m: float,
                  alpha: float, beta: float, gamma: float, lam: float, delta: float,
                  r1: int, r2: int, p: int, t_pow: int, L: float, U: float) -> Tuple[float, float]:
    # 在有限区间用黄金分割搜索全局最小（函数强凸，唯一极小）
    R = max(10.0, a + b + m + alpha + beta + gamma + lam + delta + 8.0)
    def f_local(x):
        return f_value(x, a, b, m, alpha, beta, gamma, lam, delta, r1, r2, p, t_pow, L, U)
    xg, fg = _golden_section(f_local, -R, R, tol=1e-10, max_iter=160)
    return fg, xg

def function_1(mode='pair', a=2, b=1, m=0, alpha=1, beta=3, gamma=3, lam=4, delta=1,
               r1=2, r2=2, p=2, t_pow=2, L=0.0, U=3.0, precision=5, op_symbol='⊙', explain_style='detailed'):
    a = float(a); b = float(b); m = float(m)
    alpha = float(alpha); beta = float(beta); gamma = float(gamma); lam = float(lam); delta = float(delta)
    r1 = int(r1); r2 = int(r2); p = int(p); t_pow = int(t_pow); precision = int(precision)
    L = float(L); U = float(U)
    if mode == 'derivation':
        fg, xg = solve_minimum(a, b, m, alpha, beta, gamma, lam, delta, r1, r2, p, t_pow, L, U)
        parts = []
        parts.append(f"定义自定义符号 {op_symbol}: x {op_symbol} y = x^2*|y|^{r1}。")
        parts.append(f"复合函数 F(x) = {alpha}*x^2*|{a} - x|^{r1} + {beta}*|{b} - x|^{r2} + {gamma}*|x - {m}|^{p} + {lam}*x^2 + {delta}*[max(0, {L} - x)^{t_pow} + max(0, x - {U})^{t_pow}]。")
        parts.append(f"在区间 [-R, R] 上进行全局搜索（R 由参数自适应设定），得到唯一的全局最小值。")
        parts.append(f"结论：全局最小值约为 {fg:.{precision}f}，于 x ≈ {xg:.{precision}f} 处取得。")
        return " ".join(parts)
    fg, xg = solve_minimum(a, b, m, alpha, beta, gamma, lam, delta, r1, r2, p, t_pow, L, U)
    return [f'{fg:.{precision}f}', f'{xg:.{precision}f}']

def function_2(a: int, b: int, m: int, alpha: int, beta: int, gamma: int, lam: int, delta: int,
               r1: int, r2: int, p: int, t_pow: int, L: float, U: float) -> bool:
    """
    唯一解验证（强凸判据为主）：
    - 计算 μ = 2(β + γ + λ) − α·a^2，若 μ > 1e−9 则函数为强凸，唯一极小成立 ⇒ 返回 True。
    - 参数域已收紧保证最坏情况 μ ≥ 2；因此本验证高效稳定，避免数值采样误判与超时。
    """
    a = float(a); alpha = float(alpha); beta = float(beta); gamma = float(gamma); lam = float(lam)
    mu = 2.0 * (beta + gamma + lam) - alpha * (a ** 2)
    return bool(mu > 1e-9)