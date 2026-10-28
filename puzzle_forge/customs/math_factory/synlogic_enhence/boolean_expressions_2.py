# boolean_expressions_6.py
import random
import math
from typing import List


def is_leap(year: int) -> bool:
    """
    闰年定义：
    - 能被4整除且不能被100整除，或
    - 能被400整除
    """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def is_prime(k: int) -> bool:
    """
    质数判定：k >= 2 且仅能被1与自身整除。
    """
    if k < 2:
        return False
    if k == 2:
        return True
    if k % 2 == 0:
        return False
    d = 3
    while d * d <= k:
        if k % d == 0:
            return False
        d += 2
    return True


def is_even(k: int) -> bool:
    """
    偶数判定：k % 2 == 0
    """
    return k % 2 == 0


def gcd(a: int, b: int) -> int:
    """
    最大公因数
    """
    while b:
        a, b = b, a % b
    return abs(a)


def is_coprime(a: int, b: int) -> bool:
    """
    互素判定：gcd(a, b) == 1
    """
    return gcd(a, b) == 1


def is_square(x: int) -> bool:
    """
    平方数判定：存在整数 t 使 t*t == x 且 x >= 0
    """
    if x < 0:
        return False
    t = int(math.isqrt(x))
    return t * t == x


def _xor(a: bool, b: bool) -> bool:
    """
    布尔异或：恰有一个为真
    """
    return (a and not b) or (b and not a)


def eval_statements(y1: int, y2: int, m: int, n: int) -> List[str]:
    """
    计算命题 A 到 F 的真值，并返回为真的命题标签列表（按字母序）。
    命题定义（与题面保持一致，除法比较按实数意义）：
    - A: (is_leap(y1)) and is_even(m*n)
    - B: not (is_leap(y2) or ((n - m*m) > -10))
    - C: ((not is_leap(y2)) and is_prime(m)) and is_even(n)
    - D: (is_even(m + n) and ((y1 / y2) > 1))
    - E: ((gcd(m, n) == 1) and (y1 % (m + n) == 0)) or (is_even(y1 + y2) and (abs(m - n) <= 2))
    - F: (is_coprime(y1, y2) and is_square(m + n)) or (not _xor(m % 3 == 0, n % 3 == 0))
    """
    # y2 > 0 在生成时保证，避免除零
    A = is_leap(y1) and is_even(m * n)
    B = not (is_leap(y2) or ((n - m * m) > -10))
    C = ((not is_leap(y2)) and is_prime(m)) and is_even(n)
    D = is_even(m + n) and ((y1 / y2) > 1)
    E = ((gcd(m, n) == 1) and (y1 % (m + n) == 0)) or (is_even(y1 + y2) and (abs(m - n) <= 2))
    F = (is_coprime(y1, y2) and is_square(m + n)) or (not _xor(m % 3 == 0, n % 3 == 0))

    labels = []
    if A:
        labels.append('A')
    if B:
        labels.append('B')
    if C:
        labels.append('C')
    if D:
        labels.append('D')
    if E:
        labels.append('E')
    if F:
        labels.append('F')
    return sorted(labels)


def format_answer(labels: List[str]) -> str:
    """
    将为真的命题标签列表格式化为要求的字符串：
    - 若为空返回 'NONE'（在题面约束下理论上不会出现）
    - 否则用逗号加空格分隔，按字母序输出（例如 'A, C, E'）
    """
    if not labels:
        return 'NONE'
    return ', '.join(sorted(labels))


def _rand_non_leap(low: int, high: int) -> int:
    """在区间内随机选取一个非闰年，若多次失败则回退为任意年份。"""
    for _ in range(200):
        y = random.randint(low, high)
        if not is_leap(y):
            return y
    return random.randint(low, high)


def _rand_leap(low: int, high: int) -> int:
    """在区间内随机选取一个闰年，若多次失败则回退为任意年份。"""
    for _ in range(200):
        y = random.randint(low, high)
        if is_leap(y):
            return y
    return random.randint(low, high)


def _rand_prime(low: int, high: int) -> int:
    """在区间内随机选取一个质数，若多次失败则回退为任意整数。"""
    low = max(2, low)
    for _ in range(1000):
        k = random.randint(low, high)
        if is_prime(k):
            return k
    return random.randint(low, high)


def _nudge_to_even(x: int, low: int, high: int) -> int:
    """调整到偶数且保持在区间内"""
    if x % 2 == 0:
        return x
    return x + 1 if x + 1 <= high else x - 1


def verify_unique_truthset(y1: int, y2: int, m: int, n: int) -> bool:
    """
    一致性验证（与题面公开规则一致）：
    - A..D 中恰有2条为真；
    - E..F 中至少有1条为真；
    - 若 D 为真，则 B 必为假；
    - 若 C 为真，则 A 或 E 至少一条为真。
    """
    labels = eval_statements(y1, y2, m, n)
    s = set(labels)

    ad_true = len([x for x in s if x in ('A', 'B', 'C', 'D')])
    ef_true = len([x for x in s if x in ('E', 'F')])
    if ad_true != 2:
        return False
    if ef_true < 1:
        return False
    if 'D' in s and 'B' in s:
        return False
    if 'C' in s and (('A' not in s) and ('E' not in s)):
        return False
    return True


def verify_output_possible(y1: int, y2: int, m: int, n: int) -> bool:
    """
    输出可行性验证：确保题面要求的格式对应的真集合非空且非全真。
    在题面约束下，'NONE' 与 'A, B, C, D, E, F' 都不应出现。
    """
    labels = eval_statements(y1, y2, m, n)
    if len(labels) == 0:
        return False
    if len(labels) == 6:
        return False
    return True


def compute_code(y1: int, y2: int, m: int, n: int) -> int:
    """
    安全码计算规则（与题面公开一致）：
    - 字母位置值：A=1, B=2, ..., F=6
    - 令 base 为所有为真命题的字母位置值之和
    - code = base + gcd(y1, y2) + (m*n) % 97
    - 若 y1 + y2 为偶数，再加 1；否则加 0
    - 若 m 与 n 互素，加 0；否则加 3
    """
    labels = eval_statements(y1, y2, m, n)
    base = sum((ord(ch) - ord('A') + 1) for ch in labels)
    code = base + gcd(y1, y2) + (m * n) % 97
    code += 1 if is_even(y1 + y2) else 0
    code += 0 if is_coprime(m, n) else 3
    return int(code)


def combined_answer(y1: int, y2: int, m: int, n: int) -> str:
    """
    组合最终答案为单一字符串：左侧固定字符串====右侧整数
    例如：'A, B, E, F====123'
    """
    left = format_answer(eval_statements(y1, y2, m, n))
    right = compute_code(y1, y2, m, n)
    return f"{left}===={right}"


def generate_valid_pack(year_low: int, year_high: int,
                        m_low: int, m_high: int,
                        n_low: int, n_high: int,
                        diff_mode: int) -> List[int]:
    """
    依据区间与难度模式，生成满足公开规则约束的参数包 [y1, y2, m, n]。
    仅使用题面公开的全局约束进行筛选：
    - A..D 恰有2条为真；
    - E..F 至少有1条为真；
    - 若 D 为真则 B 必为假；
    - 若 C 为真则 A 或 E 至少一真。
    diff_mode 仅用于采样偏置，不引入额外硬性约束。
    """
    # 第一步：随机采样，带偏置
    def sample_once():
        if diff_mode == 0:
            # 偏向中小范围、简单性质
            y1 = random.randint(year_low, year_high)
            y2 = random.randint(max(1, year_low), year_high)
            # 偏向偶数与质数
            m = _rand_prime(m_low, m_high) if random.random() < 0.5 else random.randint(m_low, m_high)
            n = _nudge_to_even(random.randint(n_low, n_high), n_low, n_high)
        elif diff_mode == 1:
            # 中庸随机
            y1 = random.randint(year_low, year_high)
            y2 = random.randint(max(1, year_low), year_high)
            m = random.randint(m_low, m_high)
            n = random.randint(n_low, n_high)
        else:
            # 偏向闰年/非闰年交替、m 质数、n 偶数
            y1 = _rand_leap(year_low, year_high) if random.random() < 0.5 else _rand_non_leap(year_low, year_high)
            y2 = _rand_non_leap(max(1, year_low), year_high)
            m = _rand_prime(m_low, m_high)
            n = _nudge_to_even(random.randint(n_low, n_high), n_low, n_high)
        return y1, y2, m, n

    for _ in range(12000):
        y1, y2, m, n = sample_once()
        if verify_unique_truthset(y1, y2, m, n) and verify_output_possible(y1, y2, m, n):
            return [y1, y2, m, n]

    # 第二步：启发式微调回退
    # 先构造一个较容易满足规则的起点
    y2 = _rand_non_leap(max(1, year_low), year_high)
    m = _rand_prime(m_low, m_high)
    n = _nudge_to_even(random.randint(n_low, n_high), n_low, n_high)
    y1 = random.randint(max(y2 + 1, year_low), year_high)  # 倾向 y1/y2 > 1 以利 D 的一半
    if (m + n) % 2 != 0:
        n = _nudge_to_even(n, n_low, n_high)

    # 调整 gcd 或整除，帮助 E 更容易满足
    if gcd(m, n) != 1:
        mm = m + 1 if m + 1 <= m_high else m - 1
        nn = n + 1 if n + 1 <= n_high else n - 1
        if gcd(mm, n) == 1:
            m = mm
        elif gcd(m, nn) == 1:
            n = nn
    if (m + n) != 0 and y1 % (m + n) != 0:
        cand = (y1 // (m + n)) * (m + n)
        if cand < year_low or cand > year_high:
            cand = ((y1 // (m + n)) + 1) * (m + n)
        if year_low <= cand <= year_high:
            y1 = cand

    for _ in range(4000):
        if verify_unique_truthset(y1, y2, m, n) and verify_output_possible(y1, y2, m, n):
            return [y1, y2, m, n]
        # 轻微扰动
        choice = random.random()
        if choice < 0.25:
            y1 = _rand_leap(year_low, year_high) if not is_leap(y1) else _rand_non_leap(year_low, year_high)
        elif choice < 0.5:
            y2 = _rand_leap(max(1, year_low), year_high) if not is_leap(y2) else _rand_non_leap(max(1, year_low), year_high)
        elif choice < 0.75:
            m = _rand_prime(m_low, m_high) if random.random() < 0.7 else random.randint(m_low, m_high)
        else:
            n = _nudge_to_even(random.randint(n_low, n_high), n_low, n_high)

    # 第三步：全局随机搜索兜底
    for _ in range(30000):
        y1, y2, m, n = sample_once()
        if verify_unique_truthset(y1, y2, m, n) and verify_output_possible(y1, y2, m, n):
            return [y1, y2, m, n]

    raise ValueError("Failed to generate a valid parameter pack under given ranges and diff_mode.")