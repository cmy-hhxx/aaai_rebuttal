import random
from fractions import Fraction
import re

# 全局缓存
_cache = None

# ----------------- 基础数据 -----------------
facts_true = [
    "人类每只手有五个手指", "水在标准大气压下100℃沸腾", "地球绕太阳转",
    "三角形内角和为180度", "光速约为每秒3×10^8米", "大多数植物能够进行光合作用",
    "海平面上水的冰点是0℃", "中国的首都是北京", "地球自转一周约24小时",
    "氧气是人类呼吸所必需的气体", "黄金的化学符号是Au", "铁在潮湿空气中容易生锈",
    "数学中的圆周率大约为3.14", "声音在空气中的传播速度约为340米每秒",
    "鲸鱼是哺乳动物", "地球有一个天然卫星即月球", "太阳是一颗恒星",
    "电流的单位是安培", "水由氢和氧组成", "成都位于中国的四川省"
]
facts_false = [
    "太阳绕地球转", "所有偶数都是质数", "中国的首都是上海",
    "1等于2", "地球是平的", "企鹅生活在北极",
    "水在常温下会自发沸腾", "月球由奶酪构成", "人类有三只眼睛",
    "金子比羽毛轻", "数学中的圆周率等于3", "空气主要由二氧化碳组成",
    "海水比淡水更淡", "鲸鱼是鱼类", "地球有四个太阳",
    "太阳是一颗行星", "冰在加热后会变成石头", "北京位于中国的最南端",
    "水由碳构成", "声音在真空中传播速度最快"
]

# ----------------- 工具函数 -----------------
def _rand_int(low=-12, high=12):
    return random.randint(low, high)

def _rand_nonzero_int(low=-12, high=12):
    """生成非零整数，用于分母"""
    x = 0
    while x == 0:
        x = random.randint(low, high)
    return x

def clean_text(s: str) -> str:
    if not isinstance(s, str): return s
    s = re.sub(r"[。\.]{2,}", "。", s)
    s = re.sub(r"[，,]{2,}", "，", s)
    s = re.sub(r"[,，][。\.]+", "。", s)
    s = re.sub(r"[。\.]+[,，]+", "。", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.endswith("..") or s.endswith("。。"): s = s[:-1]
    if s.endswith("."): s = s[:-1] + "。"
    return s

# ----------------- 核心逻辑 -----------------
def make_arith_expr(depth=0, max_depth=3):
    if depth >= max_depth or random.random() < 0.35:
        if random.random() < 0.2: # 分数
            a = _rand_int(-12, 12)
            b = _rand_nonzero_int(-12, 12)
            if b == 0: b = 1
            return f"({a}/{b})", Fraction(a, b)
        else: # 整数
            n = _rand_int(-12, 12)
            return str(n), Fraction(n, 1)

    op = random.choice(['+', '-', '*', '/'])
    t1, v1 = make_arith_expr(depth + 1, max_depth)
    t2, v2 = make_arith_expr(depth + 1, max_depth)
    
    # 除法保护
    if op == '/':
        attempts = 0
        while v2 == 0 and attempts < 10:
            t2, v2 = make_arith_expr(depth + 1, max_depth)
            attempts += 1
        if v2 == 0: 
            t2, v2 = "1", Fraction(1, 1)

    try:
        if op == '+': val = v1 + v2
        elif op == '-': val = v1 - v2
        elif op == '*': val = v1 * v2
        elif op == '/': val = v1 / v2
    except ZeroDivisionError:
        val = Fraction(0, 1)

    text = f"({t1} {op} {t2})"
    return text, val

def make_numeric_atom():
    t1, v1 = make_arith_expr(max_depth=2)
    t2, v2 = make_arith_expr(max_depth=2)
    op = random.choice(['==','!=','>','<','>=','<='])
    op_map = {'==':'等于','!=':'不等于','>':'大于','<':'小于','>=':'大于等于','<=':'小于等于'}
    text = f"{t1} {op_map[op]} {t2}"
    
    if op == '==': val = (v1 == v2)
    elif op == '!=': val = (v1 != v2)
    elif op == '>': val = (v1 > v2)
    elif op == '<': val = (v1 < v2)
    elif op == '>=': val = (v1 >= v2)
    elif op == '<=': val = (v1 <= v2)
    
    return text, bool(val)

def make_fact_atom():
    if random.random() < 0.5:
        return random.choice(facts_true), True
    else:
        return random.choice(facts_false), False

def get_atom():
    if random.random() < 0.5:
        return make_numeric_atom()
    else:
        return make_fact_atom()

def logic_implies(p, q): return (not p) or q
def logic_iff(p, q): return p == q

def build_A():
    p_txt, p_val = get_atom()
    q_txt, q_val = get_atom()
    tpls = ["A. 若 {p}，则 {q}。", "A. 当 {p} 成立时，{q} 成立。", "A. 如果 {p}，那么 {q}。"]
    text = random.choice(tpls).format(p=p_txt, q=q_txt)
    val = logic_implies(p_val, q_val)
    if random.random() < 0.2:
        inner = text[3:].rstrip("。")
        text = f"A. 非非（{inner}）。"
    return clean_text(text), val

def build_B():
    p_txt, p_val = get_atom()
    q_txt, q_val = get_atom()
    tpls = ["B. {p} 当且仅当 {q}。", "B. 若 {p} 则 {q}；反之亦然。", "B. ({p}) 等价于 ({q})。"]
    text = random.choice(tpls).format(p=p_txt, q=q_txt)
    val = logic_iff(p_val, q_val)
    return clean_text(text), val

def build_C():
    a_txt, a_val = get_atom()
    b_txt, b_val = get_atom()
    c_txt, c_val = get_atom()
    pattern = random.choice([1, 2])
    if pattern == 1:
        text = f"C. 非（({a_txt}) 或 非（{b_txt}））。"
        val = not (a_val or (not b_val))
    else:
        text = f"C. (({a_txt}) 且 ({b_txt})) 或 ({c_txt})。"
        val = (a_val and b_val) or c_val
    if random.random() < 0.3:
        inner = text[3:].rstrip("。")
        text = f"C. not not ({inner})。" 
    return clean_text(text), val

def build_D():
    p_txt, p_val = get_atom()
    q_txt, q_val = get_atom()
    if random.random() < 0.5:
        text = f"D. {p_txt}。"
        val = p_val
    else:
        text = f"D. ({p_txt}) 并且 (({q_txt}) 或 (1等于0))。"
        val = p_val and (q_val or False)
    return clean_text(text), val

# ----------------- 新的入口函数 -----------------

def generate_core():
    """内部生成逻辑"""
    global _cache
    _cache = None
    while True:
        try:
            A_text, A_val = build_A()
            B_text, B_val = build_B()
            C_text, C_val = build_C()
            D_text, D_val = build_D()
            vals = [A_val, B_val, C_val, D_val]
            true_count = sum(vals)
            if 1 <= true_count <= 3:
                bmap = {'A': A_val, 'B': B_val, 'C': C_val, 'D': D_val}
                ans_list = [k for k in ['A','B','C','D'] if bmap[k]]
                _cache = {
                    'A_text': A_text, 'B_text': B_text, 'C_text': C_text, 'D_text': D_text,
                    'A_val': A_val, 'B_val': B_val, 'C_val': C_val, 'D_val': D_val,
                    'ans_list': ans_list, 'ans_str': ','.join(ans_list)
                }
                break
        except ZeroDivisionError:
            continue
        except Exception:
            continue
    return _cache

# 【新】万能入口，接受任何参数，避免 TypeError
def function_1(*args, **kwargs):
    global _cache
    # 检测是否请求强制刷新 (兼容 new=True 或调用 reset_and_get)
    if kwargs.get('new') is True:
        return generate_core()
    
    # 正常读取缓存
    if _cache is None:
        return generate_core()
    return _cache

# 【新】明确的重置函数，供 YAML 明确调用
def reset_and_get():
    return generate_core()

def function_2(data=None):
    if data is None: data = function_1()
    return data.get('ans_str', '')

if __name__ == "__main__":
    print(reset_and_get()['ans_str'])