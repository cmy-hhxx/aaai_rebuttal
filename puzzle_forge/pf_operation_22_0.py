# pf_operation_22_0.py
# 原报错原因：运行环境缺少 sympy，导致 ModuleNotFoundError。
# 修复思路：不使用第三方库，针对题目给定的函数模板（x/y 与 x^3+y^3）
# 直接按定义求偏导并返回 LaTeX。

def pf_op(f_type: str, g_type: str) -> str:
    """
    计算 f■g = ∂f/∂x + ∂g/∂x
    为保证无第三方依赖，这里仅支持题面对应的两类函数模板：
      - f_type == 'x_over_y'      => f(x,y)=x/y
      - g_type == 'x3_plus_y3'    => g(x,y)=x^3 + y^3
    返回：LaTeX 主体字符串，例如 '\\frac{1}{y}+3x^2'
    """
    if f_type != "x_over_y":
        raise ValueError(f"Unsupported f_type: {f_type}")
    if g_type != "x3_plus_y3":
        raise ValueError(f"Unsupported g_type: {g_type}")

    # ∂(x/y)/∂x = 1/y
    # ∂(x^3+y^3)/∂x = 3x^2
    return r"\frac{1}{y}+3x^2"

def to_latex(s: str) -> str:
    """本题 pf_op 已返回 LaTeX 主体，这里保持接口统一直接原样返回。"""
    return s