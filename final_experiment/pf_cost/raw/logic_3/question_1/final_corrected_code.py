# pf_logic_3_0.py
# 说明：
# - YAML 中的 expr_q*_ascii 必须是字符串（例如 "'(~p&~q&r)|(...)'"），
#   否则生成的 output.py 会把 (~p&...) 当成 Python 位运算表达式执行，触发 NameError。
# - 本文件负责解析字符串并计算 m_i / M_i 及分类。

import re

HEX_DIGITS = "0123456789ABCDEF"

def _normalize(s: str) -> str:
    """统一符号并去空白：支持 ~ & | 以及 ¬ ∧ ∨ V ^"""
    s = s.replace(" ", "")
    # not
    s = s.replace("¬", "~")
    # and
    s = s.replace("∧", "&")
    s = s.replace("^", "&")  # 兼容 ^ 表示 ∧
    # or
    s = s.replace("V", "|")
    s = s.replace("∨", "|")
    return s

def parse_term(expr: str, kind: str):
    """
    kind:
      - 'dnf': 用 | 分割得到“配对合取项”（每项内部用 & 连接）
      - 'cnf': 用 & 分割得到“配对析取项”（每项内部用 | 连接）
    返回：项列表（字符串），不做一般逻辑化简。
    """
    expr = _normalize(expr)
    if kind == "dnf":
        parts = re.split(r"\|", expr)
    elif kind == "cnf":
        parts = re.split(r"&", expr)
    else:
        raise ValueError("kind must be 'dnf' or 'cnf'")
    cleaned = []
    for p in parts:
        if p.startswith("(") and p.endswith(")"):
            p = p[1:-1]
        cleaned.append(p)
    return cleaned

def _lit_value_for_m(lit: str) -> int:
    """配对合取项里：p 表示1，~p 表示0"""
    return 0 if lit.startswith("~") else 1

def _lit_value_for_M(lit: str) -> int:
    """配对析取项的“假赋值”：p 在假赋值下为0，~p 在假赋值下为1"""
    return 1 if lit.startswith("~") else 0

def _split_literals(term: str, sep: str):
    term = _normalize(term)
    return term.split(sep) if term else []

def mi_index_of_conj_term(conj_term: str, vars_order):
    """配对合取项 -> m_i 的 i（int）"""
    lits = _split_literals(conj_term, "&")
    m = {v: None for v in vars_order}
    for lit in lits:
        v = lit[1:] if lit.startswith("~") else lit
        m[v] = _lit_value_for_m(lit)
    if any(m[v] is None for v in vars_order):
        raise ValueError("Not a paired conjunctive term (missing variable).")
    bits = "".join(str(m[v]) for v in vars_order)
    return int(bits, 2)

def Mi_index_of_disj_term(disj_term: str, vars_order):
    """配对析取项 -> M_i 的 i（int）"""
    lits = _split_literals(disj_term, "|")
    m = {v: None for v in vars_order}
    for lit in lits:
        v = lit[1:] if lit.startswith("~") else lit
        m[v] = _lit_value_for_M(lit)
    if any(m[v] is None for v in vars_order):
        raise ValueError("Not a paired disjunctive term (missing variable).")
    bits = "".join(str(m[v]) for v in vars_order)
    return int(bits, 2)

def denote_m_terms(indices, joiner="∨"):
    idxs = sorted(indices)
    return joiner.join([f"m{HEX_DIGITS[i]}" for i in idxs])

def denote_M_terms(indices, joiner="^"):
    idxs = sorted(indices)
    return joiner.join([f"M{HEX_DIGITS[i]}" for i in idxs])

def classify_by_m_indices(indices, n: int):
    idxs = sorted(indices)
    opts = []
    if len(idxs) == 2**n:
        opts.append("A")
    if len(idxs) == 0:
        opts.append("B")
    if 0 in idxs:
        opts.append("C")
    if len(idxs) > 0 and all(i % 2 == 0 for i in idxs):
        opts.append("D")
    if len(idxs) > 0 and all(i % 2 == 1 for i in idxs):
        opts.append("E")
    if len(opts) == 0:
        opts.append("F")
    return opts

def is_pdnf_text(expr: str, vars_order):
    """
    判断是否为主析取范式（PDNF）。
    若是：返回 ['A', 'm...']；否则：返回 ['B', '']。
    """
    expr = _normalize(expr)
    terms = re.split(r"\|", expr)
    conj_terms = []
    for t in terms:
        t = t.strip()
        if t.startswith("(") and t.endswith(")"):
            t = t[1:-1]
        lits = _split_literals(t, "&")
        if len(lits) != len(vars_order):
            return ["B", ""]
        seen = []
        for lit in lits:
            v = lit[1:] if lit.startswith("~") else lit
            seen.append(v)
        if seen != list(vars_order):
            return ["B", ""]
        conj_terms.append(t)

    idxs = [mi_index_of_conj_term(t, vars_order) for t in conj_terms]
    return ["A", denote_m_terms(idxs, joiner="∨")]