# pf_operation_5_0.py

def op_inf(a: int, b: int) -> int:
    """
    自定义运算：a∞b = a^2 + b^2 （a,b为正整数）
    """
    return a * a + b * b


def solve_x_inf_6_eq_45() -> int:
    """
    解方程：X∞6 = 45，即 X^2 + 6^2 = 45
    返回满足条件的正整数 X（若无正整数解则抛异常）
    """
    b = 6
    target = 45
    rhs = target - b * b  # X^2
    if rhs <= 0:
        raise ValueError("No positive integer solution.")
    x = int(rhs ** 0.5)
    if x * x != rhs or x <= 0:
        raise ValueError("No positive integer solution.")
    return x