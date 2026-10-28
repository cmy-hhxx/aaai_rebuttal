# customs/Polynomial.py

from math import factorial, log, isclose
from functools import reduce
import operator
def no_zero(l):
    return all(x != 0 for x in l)
def product(lst):
    """计算列表元素乘积"""
    return reduce(operator.mul, lst, 1)

def multinomial(n, *ks):
    """计算多项式系数: n! / (k1! k2! ... kr!)"""
    denom = 1
    for k in ks:
        if k < 0:
            raise ValueError("Negative exponent")
        denom *= factorial(k)
    return factorial(n) // denom

def log_coeff_value(n, exponents, abs_coeffs):
    """
    计算 log(|C|) 的近似值（用于比较大小，避免溢出）
    使用斯特林近似：log(m!) ≈ m*log(m) - m + 0.5*log(2πm)
    """
    from math import log as ln, pi
    def stirling(m):
        if m == 0:
            return 0
        if m == 1:
            return 0
        return m*ln(m) - m + 0.5*ln(2*pi*m)

    log_factorial_n = stirling(n)
    log_denom = sum(stirling(k) for k in exponents)
    log_power_part = sum(e * ln(c) if c > 0 and e > 0 else 0 for e, c in zip(exponents, abs_coeffs))
    
    return log_factorial_n - log_denom + log_power_part

def adjust_to_sum(target_sum, arr):
    """调整数组使其和等于 target_sum，每次 ±1"""
    arr = [max(0, int(round(x))) for x in arr]  # 强制非负整数
    while sum(arr) != target_sum:
        if sum(arr) < target_sum:
            # 找最接近理想比例但偏低的位置加1
            idx = None
            best_ratio_diff = -float('inf')
            for i in range(len(arr)):
                ratio = arr[i] / (abs_coeffs[i] if abs_coeffs[i] != 0 else 1e-6)
                diff = (target_sum * abs_coeffs[i] / total_coeff) - arr[i]
                if arr[i] >= 0:
                    if diff > best_ratio_diff:
                        best_ratio_diff = diff
                        idx = i
            if idx is not None:
                arr[idx] += 1
        elif sum(arr) > target_sum:
            idx = None
            worst_ratio_diff = -float('inf')
            for i in range(len(arr)):
                diff = arr[i] - (target_sum * abs_coeffs[i] / total_coeff)
                if arr[i] > 0:
                    if diff > worst_ratio_diff:
                        worst_ratio_diff = diff
                        idx = i
            if idx is not None:
                arr[idx] -= 1
    return tuple(arr)

# 全局变量（仅用于内部）
abs_coeffs = None
total_coeff = None

def find_max_coeff_exponent_tuple(n, coeffs):
    """
    精确查找使 |C| 最大的指数元组 (a1, a2, ..., ak)
    方法：
      1. 初始猜测：a_i ∝ |c_i|
      2. Hill Climbing：尝试将一个单位从 i 移到 j，看是否提升 log|C|
      3. 直到无法再改进 → 收敛到全局最优
    """
    global abs_coeffs, total_coeff
    k = len(coeffs)
    abs_coeffs = [abs(c) for c in coeffs]
    total_coeff = sum(abs_coeffs)

    # 步骤 1：初始猜测（按比例分配）
    ideal = [n * ac / total_coeff for ac in abs_coeffs]
    exponents = [round(x) for x in ideal]
    
    # 调整总和为 n
    current_sum = sum(exponents)
    while current_sum != n:
        if current_sum < n:
            # 找偏差最大的（理想值更高）
            diffs = [(ideal[i] - exponents[i], i) for i in range(k)]
            _, idx = max(diffs)
            exponents[idx] += 1
        else:
            diffs = [(exponents[i] - ideal[i], i) for i in range(k)]
            _, idx = max(diffs)
            if exponents[idx] > 0:
                exponents[idx] -= 1
            else:
                # 若已为0，则找其他可减的
                candidates = [i for i in range(k) if exponents[i] > 0]
                if candidates:
                    diffs = [(exponents[i] - ideal[i], i) for i in candidates]
                    _, idx = max(diffs)
                    exponents[idx] -= 1
                else:
                    break
        current_sum = sum(exponents)

    exponents = tuple(max(0, e) for e in exponents)

    # 步骤 2：局部优化（hill climbing）
    improved = True
    visited = set()
    while improved:
        improved = False
        current_log = log_coeff_value(n, exponents, abs_coeffs)
        if exponents in visited:
            break
        visited.add(exponents)

        # 尝试所有 i -> j 的转移：从 i 减1，j 加1
        for i in range(k):
            if exponents[i] <= 0:
                continue
            for j in range(k):
                if i == j:
                    continue
                new_exp = list(exponents)
                new_exp[i] -= 1
                new_exp[j] += 1
                new_exp = tuple(new_exp)

                if sum(new_exp) != n or any(e < 0 for e in new_exp):
                    continue

                if new_exp in visited:
                    continue

                new_log = log_coeff_value(n, new_exp, abs_coeffs)
                if new_log > current_log + 1e-8:  # 显著提升
                    exponents = new_exp
                    improved = True
                    break
            if improved:
                break

    # 最终验证：确保是最优
    return exponents

# customs/Polynomial.py （追加此函数）

def format_monomial(coeff, var):
    """
    格式化单个项：如 (2, 'x') -> '2x'
                   (-1, 'y') -> '-y'
                   (1, 'z') -> 'z'
                   (0, 't') -> '0' （但一般不会出现）
    """
    if coeff == 0:
        return "0"
    elif coeff == 1:
        return var
    elif coeff == -1:
        return f"-{var}"
    else:
        return f"{coeff}{var}"


def format_polynomial(coeffs, vars):
    """
    将系数列表和变量列表格式化为美观的多项式字符串。
    
    参数:
        coeffs (list of int): 系数列表，如 [2, -3, 1]
        vars (list of str): 变量名列表，如 ['x', 'y', 'z']
    
    返回:
        str: 如 "2x - 3y + z"
    
    示例:
        format_polynomial([2, -3, 1], ['x', 'y', 'z']) -> "2x - 3y + z"
        format_polynomial([-1, 5], ['a', 'b']) -> "-a + 5b"
    """
    if len(coeffs) != len(vars):
        raise ValueError("系数数量必须等于变量数量")

    if len(coeffs) == 0:
        return "0"

    # 构造每一项
    terms = []
    for c, v in zip(coeffs, vars):
        term = format_monomial(c, v)
        terms.append(term)

    # 合并项：先拼接，再处理符号
    expression = ""
    for i, term in enumerate(terms):
        if i == 0:
            expression += term
        else:
            # 手动处理正负号显示
            if term.startswith('-'):
                expression += f" - {term[1:]}"
            else:
                expression += f" + {term}"

    # 特殊情况：首项是 -x 开头
    if expression.startswith(" - "):
        expression = "-" + expression[3:]

    return expression.strip()
