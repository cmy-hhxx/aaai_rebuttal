# einsteins_riddle_18.py
import random
import time
from z3 import Solver, Bool, And, Or, Not, Sum, If, sat, unsat

# -------- 基本布尔映射与双射约束 --------
def _mk_var_map(pos_keys, names, prefix):
    m = {}
    for i, pk in enumerate(pos_keys):
        for nm in names:
            m[(i, nm)] = Bool(f"{prefix}_{pk}_{nm}")
    return m

def _exactly_one_per_pos(s, varmap, pos_num, names):
    for i in range(pos_num):
        s.add(Sum([If(varmap[(i, nm)], 1, 0) for nm in names]) == 1)

def _each_name_once(s, varmap, pos_num, names):
    for nm in names:
        s.add(Sum([If(varmap[(i, nm)], 1, 0) for i in range(pos_num)]) == 1)

# -------- 通用访问与文本模板工具 --------
def _get_assign_map(attr, assign_func, assign_equip, assign_safe, assign_rank):
    if attr == 'func':
        return assign_func
    if attr == 'equip':
        return assign_equip
    if attr == 'safe':
        return assign_safe
    if attr == 'rank':
        return assign_rank
    raise ValueError('未知属性类型')

def _label(attr, val):
    if attr == 'func':
        return f"职能{val}"
    if attr == 'equip':
        return f"设备{val}"
    if attr == 'safe':
        return f"安全等级{val}"
    if attr == 'rank':
        return f"军衔{val}"
    return f"{attr}{val}"

def _line_right_of(x_label, y_label):
    return f"{x_label}在{y_label}右侧"

def _line_left_of(x_label, y_label):
    return f"{x_label}在{y_label}左侧"

def _line_not_same(x_label, y_label):
    return f"{x_label}与{y_label}不在同一隔舱"

def _line_adjacent(x_label, y_label):
    return f"{x_label}与{y_label}相邻"

def _line_not_adjacent(x_label, y_label):
    return f"{x_label}与{y_label}不相邻"

def _line_not_ends(label):
    return f"{label}不在两端"

def _line_at_end(label):
    return f"{label}在某一端"

def _line_parity(label, parity):
    return f"{label}位于{'奇数位' if parity == 'odd' else '偶数位'}"

def _line_parity_both(label_a, label_b, parity):
    return f"{label_a}和{label_b}均位于{'奇数位' if parity == 'odd' else '偶数位'}"

def _line_opposite_parity(a_label, b_label):
    return f"{a_label}与{b_label}的位置奇偶性不同"

def _line_distance(a_label, b_label, k):
    return f"{a_label}与{b_label}编号差为{k}"

def _line_between(mid_label, a_label, b_label):
    return f"{mid_label}在{a_label}与{b_label}之间"

# -------- 关系编码（Z3约束） --------
def _cons_right_of(pos_num, assign_x, x_val, assign_y, y_val):
    cons = []
    for i in range(pos_num):
        left_has_y = Or([assign_y[(k, y_val)] for k in range(i)]) if i > 0 else False
        cons.append(Or(Not(assign_x[(i, x_val)]), left_has_y))
    return cons

def _cons_left_of(pos_num, assign_x, x_val, assign_y, y_val):
    cons = []
    for i in range(pos_num):
        right_has_y = Or([assign_y[(k, y_val)] for k in range(i + 1, pos_num)]) if i < pos_num - 1 else False
        cons.append(Or(Not(assign_x[(i, x_val)]), right_has_y))
    return cons

def _cons_not_same(pos_num, assign_x, x_val, assign_y, y_val):
    cons = []
    for i in range(pos_num):
        cons.append(Or(Not(assign_x[(i, x_val)]), Not(assign_y[(i, y_val)])))
    return cons

def _cons_adjacent(pos_num, assign_x, x_val, assign_y, y_val):
    exist_pairs = []
    for i in range(pos_num - 1):
        p1 = And(assign_x[(i, x_val)], assign_y[(i + 1, y_val)])
        p2 = And(assign_x[(i + 1, x_val)], assign_y[(i, y_val)])
        exist_pairs.append(Or(p1, p2))
    if not exist_pairs:
        return [False]
    return [Or(exist_pairs)]

def _cons_not_adjacent(pos_num, assign_x, x_val, assign_y, y_val):
    cons = []
    for i in range(pos_num):
        left_ok = True if i == 0 else Not(assign_y[(i - 1, y_val)])
        right_ok = True if i == pos_num - 1 else Not(assign_y[(i + 1, y_val)])
        cons.append(Or(Not(assign_x[(i, x_val)]), And(left_ok, right_ok)))
    return cons

def _cons_not_ends_gen(pos_num, assign_map, val):
    return [Not(assign_map[(0, val)]), Not(assign_map[(pos_num - 1, val)])]

def _cons_at_end_gen(pos_num, assign_map, val):
    return [Or(assign_map[(0, val)], assign_map[(pos_num - 1, val)])]

def _cons_parity(assign_map, val, parity, odd_idx, even_idx):
    idxs = odd_idx if parity == 'odd' else even_idx
    if not idxs:
        return [False]
    return [Or([assign_map[(i, val)] for i in idxs])]

def _cons_opposite_parity(assign_a, a_val, assign_b, b_val, odd_idx, even_idx):
    if not odd_idx and not even_idx:
        return [False]
    odd_any_a = Or([assign_a[(i, a_val)] for i in odd_idx]) if odd_idx else False
    even_any_a = Or([assign_a[(i, a_val)] for i in even_idx]) if even_idx else False
    odd_any_b = Or([assign_b[(i, b_val)] for i in odd_idx]) if odd_idx else False
    even_any_b = Or([assign_b[(i, b_val)] for i in even_idx]) if even_idx else False
    return [Or(And(odd_any_a, even_any_b), And(even_any_a, odd_any_b))]

def _cons_parity_both(assign_map, a_val, b_val, parity, odd_idx, even_idx):
    idxs = odd_idx if parity == 'odd' else even_idx
    if not idxs:
        return [False]
    ca = Or([assign_map[(i, a_val)] for i in idxs])
    cb = Or([assign_map[(i, b_val)] for i in idxs])
    return [ca, cb]

def _cons_distance(pos_num, assign_a, a_val, assign_b, b_val, k):
    if k <= 0 or k >= pos_num:
        return [False]
    pairs = []
    for i in range(pos_num):
        j1 = i + k
        j2 = i - k
        if 0 <= j1 < pos_num:
            pairs.append(And(assign_a[(i, a_val)], assign_b[(j1, b_val)]))
        if 0 <= j2 < pos_num:
            pairs.append(And(assign_a[(i, a_val)], assign_b[(j2, b_val)]))
    if not pairs:
        return [False]
    return [Or(pairs)]

def _cons_between(pos_num, assign_mid, mid_val, assign_a, a_val, assign_b, b_val):
    trios = []
    for i in range(pos_num):
        for j in range(i + 1, pos_num):
            for k in range(j + 1, pos_num):
                trios.append(And(assign_a[(i, a_val)], assign_mid[(j, mid_val)], assign_b[(k, b_val)]))
                trios.append(And(assign_b[(i, b_val)], assign_mid[(j, mid_val)], assign_a[(k, a_val)]))
    if not trios:
        return [False]
    return [Or(trios)]

# -------- 额外排除对生成 --------
def _make_extras(rnd, functions, equipments, safeties, ranks, extra_excl_num):
    cand_fe = [(f, e) for f in functions for e in equipments]
    cand_rs = [(r, s) for r in ranks for s in safeties]
    cand_fr = [(f, r) for f in functions for r in ranks]
    cand_es = [(e, s) for e in equipments for s in safeties]
    rnd.shuffle(cand_fe)
    rnd.shuffle(cand_rs)
    rnd.shuffle(cand_fr)
    rnd.shuffle(cand_es)

    extra_func_equip_pairs = []
    fe_need = min(max(4, int(extra_excl_num) + 2), 8)
    for pair in cand_fe:
        if pair not in extra_func_equip_pairs:
            extra_func_equip_pairs.append(pair)
            if len(extra_func_equip_pairs) >= fe_need:
                break

    extra_rank_safe_pairs = []
    while len(extra_rank_safe_pairs) < min(4, len(cand_rs)) and cand_rs:
        p = cand_rs.pop()
        if p not in extra_rank_safe_pairs:
            extra_rank_safe_pairs.append(p)

    extra_func_rank_pairs = []
    while len(extra_func_rank_pairs) < min(3, len(cand_fr)) and cand_fr:
        p = cand_fr.pop()
        if p not in extra_func_rank_pairs:
            extra_func_rank_pairs.append(p)

    extra_equip_safe_pairs = []
    while len(extra_equip_safe_pairs) < min(3, len(cand_es)) and cand_es:
        p = cand_es.pop()
        if p not in extra_equip_safe_pairs:
            extra_equip_safe_pairs.append(p)

    return extra_func_equip_pairs, extra_rank_safe_pairs, extra_func_rank_pairs, extra_equip_safe_pairs

# -------- 规则池生成（自然语言规则输出，含去重与互斥防护） --------
def _gen_rule_pool(rnd, pos_num, odd_positions, even_positions,
                   functions, equipments, safeties, ranks,
                   assign_func, assign_equip, assign_safe, assign_rank,
                   target_func, base_rule_num):
    odd_idx = [p - 1 for p in odd_positions if 1 <= p <= pos_num]
    even_idx = [p - 1 for p in even_positions if 1 <= p <= pos_num]

    rule_constraints = []
    rule_lines = []
    used_pairs = set()
    used_texts = set()
    pair_relation = {}  # 记录某对象对是否已经出现相邻/不相邻，避免互斥矛盾

    def add_rule(cons_list, line_text, relation_key=None, relation_type=None):
        if line_text in used_texts:
            return
        if relation_key is not None and relation_type is not None:
            if relation_key in pair_relation:
                if (pair_relation[relation_key] == 'adjacent' and relation_type == 'not_adjacent') or \
                   (pair_relation[relation_key] == 'not_adjacent' and relation_type == 'adjacent'):
                    return
            else:
                pair_relation[relation_key] = relation_type
        for c in cons_list:
            rule_constraints.append(c)
        rule_lines.append(line_text)
        used_texts.add(line_text)

    # 职能两两固定相对顺序（字典序最小的两个）
    if len(functions) >= 2:
        f1, f2 = sorted(functions)[:2]
        cons_ord_f = _cons_left_of(pos_num,
                                   _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank), f1,
                                   _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank), f2)
        add_rule(cons_ord_f, _line_left_of(_label('func', f1), _label('func', f2)))

    # 设备两两固定相对顺序（字典序最小的两个）
    if len(equipments) >= 2:
        e1, e2 = sorted(equipments)[:2]
        cons_ord_e = _cons_left_of(pos_num,
                                   _get_assign_map('equip', assign_func, assign_equip, assign_safe, assign_rank), e1,
                                   _get_assign_map('equip', assign_func, assign_equip, assign_safe, assign_rank), e2)
        add_rule(cons_ord_e, _line_left_of(_label('equip', e1), _label('equip', e2)))

    # 字典序最小的安全等级位于奇数位
    if safeties:
        s_min = sorted(safeties)[0]
        cons_par_smin = _cons_parity(_get_assign_map('safe', assign_func, assign_equip, assign_safe, assign_rank),
                                     s_min, 'odd', odd_idx, even_idx)
        add_rule(cons_par_smin, _line_parity(_label('safe', s_min), 'odd'))

    # 军衔两两固定相对顺序（字典序最小的两个）
    if len(ranks) >= 2:
        r1, r2 = sorted(ranks)[:2]
        cons_ord_r = _cons_left_of(pos_num,
                                   _get_assign_map('rank', assign_func, assign_equip, assign_safe, assign_rank), r1,
                                   _get_assign_map('rank', assign_func, assign_equip, assign_safe, assign_rank), r2)
        add_rule(cons_ord_r, _line_left_of(_label('rank', r1), _label('rank', r2)))

    # 字典序最小的职能不在两端（破坏对称）
    if functions:
        f_min = sorted(functions)[0]
        cons_fmin_not_ends = _cons_not_ends_gen(pos_num,
                                                _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank),
                                                f_min)
        add_rule(cons_fmin_not_ends, _line_not_ends(_label('func', f_min)))

    # 字典序最小的设备不在两端（进一步破坏对称）
    if equipments:
        e_min = sorted(equipments)[0]
        cons_emin_not_ends = _cons_not_ends_gen(pos_num,
                                                _get_assign_map('equip', assign_func, assign_equip, assign_safe, assign_rank),
                                                e_min)
        add_rule(cons_emin_not_ends, _line_not_ends(_label('equip', e_min)))

    # 目标相关位置规则（打破镜像）
    fD = rnd.choice([x for x in functions if x != target_func])
    cons = _cons_right_of(pos_num, _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank), fD,
                          _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank), target_func)
    add_rule(cons, _line_right_of(_label('func', fD), _label('func', target_func)))

    templates = []

    # 函数不与设备同舱（少量）
    for _ in range(2):
        f = rnd.choice(functions)
        e = rnd.choice(equipments)
        if (('func', f), ('equip', e)) in used_pairs:
            continue
        templates.append(('not_same', ('func', f), ('equip', e)))

    # 设备不与安全同舱（少量）
    for _ in range(2):
        e = rnd.choice(equipments)
        s = rnd.choice(safeties)
        if (('equip', e), ('safe', s)) in used_pairs:
            continue
        templates.append(('not_same', ('equip', e), ('safe', s)))

    # 职能与军衔不相邻（避免互斥冲突）
    for _ in range(1):
        f = rnd.choice(functions)
        r = rnd.choice(ranks)
        templates.append(('not_adjacent', ('func', f), ('rank', r)))

    # 军衔不在端点 或 在端点
    rTop = rnd.choice(ranks)
    templates.append(('not_ends_gen', ('rank', rTop), None))
    if len(ranks) >= 2:
        rEnd = rnd.choice([x for x in ranks if x != rTop])
        templates.append(('at_end_gen', ('rank', rEnd), None))

    # 奇偶位约束（安全、职能）
    s_par = rnd.choice(safeties)
    templates.append(('parity', ('safe', s_par), ('odd',)))
    if len(functions) >= 2:
        f_par = rnd.choice(functions)
        templates.append(('parity', ('func', f_par), ('even',)))

    # 两者奇偶相反
    if len(safeties) >= 2:
        sX, sY = rnd.sample(safeties, 2)
        templates.append(('opposite_parity', ('safe', sX), ('safe', sY)))

    # 左右关系（跨属性）
    eL = rnd.choice(equipments)
    fL = rnd.choice([x for x in functions if x != fD])
    templates.append(('left_of', ('equip', eL), ('func', fL)))

    # 相邻约束（记录相邻关系，避免与不相邻矛盾）
    if len(equipments) >= 1 and len(ranks) >= 1:
        eAdj = rnd.choice(equipments)
        rAdj = rnd.choice(ranks)
        templates.append(('adjacent', ('equip', eAdj), ('rank', rAdj)))

    # 编号差为k（优先2或3）
    if pos_num >= 5:
        k_choices = [2] if pos_num == 5 else [2, 3]
        k = rnd.choice(k_choices)
        fD2 = rnd.choice(functions)
        eD2 = rnd.choice(equipments)
        templates.append(('distance', ('func', fD2), ('equip', eD2), k))

    # 在两者之间（跨属性）
    if pos_num >= 5:
        mid_attr, left_attr, right_attr = 'equip', 'func', 'safe'
        mid_v = rnd.choice(equipments)
        left_v = rnd.choice(functions)
        right_v = rnd.choice(safeties)
        templates.append(('between', (mid_attr, mid_v), (left_attr, left_v), (right_attr, right_v)))

    # 左侧且不相邻（合取）
    f_ln = rnd.choice(functions)
    s_ln = rnd.choice(safeties)
    templates.append(('left_of_not_adjacent', ('func', f_ln), ('safe', s_ln)))

    # 端点/非端点（安全或设备）
    if rnd.random() < 0.5:
        x = rnd.choice(safeties)
        templates.append(('at_end_gen', ('safe', x), None))
    else:
        x = rnd.choice(equipments)
        templates.append(('not_ends_gen', ('equip', x), None))

    # 双重奇偶（同奇或同偶）
    if len(safeties) >= 2:
        a, b = rnd.sample(safeties, 2)
        templates.append(('parity_both', ('safe', a), ('safe', b), rnd.choice(['odd', 'even'])))

    rnd.shuffle(templates)
    need = max(0, base_rule_num - len(rule_lines))
    pick = templates[:need]

    for tp in pick:
        kind = tp[0]
        a = tp[1]
        b = tp[2] if len(tp) > 2 else None

        if kind == 'not_same':
            (a_attr, a_val), (b_attr, b_val) = a, b
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_not_same(pos_num, assign_a, a_val, assign_b, b_val)
            line = _line_not_same(_label(a_attr, a_val), _label(b_attr, b_val))
            add_rule(cons, line)
            used_pairs.add(((a_attr, a_val), (b_attr, b_val)))

        elif kind == 'not_adjacent':
            (a_attr, a_val), (b_attr, b_val) = a, b
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_not_adjacent(pos_num, assign_a, a_val, assign_b, b_val)
            rk = (a_attr, a_val, b_attr, b_val)
            add_rule(cons, _line_not_adjacent(_label(a_attr, a_val), _label(b_attr, b_val)), relation_key=rk, relation_type='not_adjacent')

        elif kind == 'not_ends_gen':
            (a_attr, a_val) = a
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_not_ends_gen(pos_num, assign_a, a_val)
            add_rule(cons, _line_not_ends(_label(a_attr, a_val)))

        elif kind == 'at_end_gen':
            (a_attr, a_val) = a
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_at_end_gen(pos_num, assign_a, a_val)
            add_rule(cons, _line_at_end(_label(a_attr, a_val)))

        elif kind == 'parity':
            (attr, val) = a
            parity = b[0]
            assign_map = _get_assign_map(attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_parity(assign_map, val, parity, odd_idx, even_idx)
            add_rule(cons, _line_parity(_label(attr, val), parity))

        elif kind == 'opposite_parity':
            (a_attr, a_val), (b_attr, b_val) = a, b
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_opposite_parity(assign_a, a_val, assign_b, b_val, odd_idx, even_idx)
            add_rule(cons, _line_opposite_parity(_label(a_attr, a_val), _label(b_attr, b_val)))

        elif kind == 'left_of':
            (a_attr, a_val), (b_attr, b_val) = a, b
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_left_of(pos_num, assign_a, a_val, assign_b, b_val)
            add_rule(cons, _line_left_of(_label(a_attr, a_val), _label(b_attr, b_val)))

        elif kind == 'adjacent':
            (a_attr, a_val), (b_attr, b_val) = a, b
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_adjacent(pos_num, assign_a, a_val, assign_b, b_val)
            rk = (a_attr, a_val, b_attr, b_val)
            add_rule(cons, _line_adjacent(_label(a_attr, a_val), _label(b_attr, b_val)), relation_key=rk, relation_type='adjacent')

        elif kind == 'distance':
            (a_attr, a_val), (b_attr, b_val) = a, b
            k = tp[3]
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_distance(pos_num, assign_a, a_val, assign_b, b_val, k)
            add_rule(cons, _line_distance(_label(a_attr, a_val), _label(b_attr, b_val), k))

        elif kind == 'between':
            (mid_attr, mid_val) = a
            (left_attr, left_val) = b
            (right_attr, right_val) = tp[3]
            assign_mid = _get_assign_map(mid_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_left = _get_assign_map(left_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_right = _get_assign_map(right_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_between(pos_num, assign_mid, mid_val, assign_left, left_val, assign_right, right_val)
            add_rule(cons, _line_between(_label(mid_attr, mid_val), _label(left_attr, left_val), _label(right_attr, right_val)))

        elif kind == 'left_of_not_adjacent':
            (a_attr, a_val), (b_attr, b_val) = a, b
            assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons1 = _cons_left_of(pos_num, assign_a, a_val, assign_b, b_val)
            cons2 = _cons_not_adjacent(pos_num, assign_a, a_val, assign_b, b_val)
            rk = (a_attr, a_val, b_attr, b_val)
            add_rule(cons1 + cons2, f"{_label(a_attr, a_val)}在{_label(b_attr, b_val)}左侧且不相邻", relation_key=rk, relation_type='not_adjacent')

        elif kind == 'parity_both':
            (a_attr, a_val), (b_attr, b_val) = a, b
            parity = tp[3]
            assign_map = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
            cons = _cons_parity_both(assign_map, a_val, b_val, parity, odd_idx, even_idx)
            add_rule(cons, _line_parity_both(_label(a_attr, a_val), _label(b_attr, b_val), parity))

    return rule_constraints, rule_lines

# -------- 结构化兜底（可复用，前置与后置均可调用） --------
def _add_structured_boosters(rnd, pos_num, odd_positions, even_positions,
                             functions, equipments, safeties, ranks,
                             assign_func, assign_equip, assign_safe, assign_rank,
                             rule_constraints, rule_lines):
    odd_idx = [p - 1 for p in odd_positions if 1 <= p <= pos_num]
    even_idx = [p - 1 for p in even_positions if 1 <= p <= pos_num]
    used_texts = set(rule_lines)

    def add(cons, text):
        if text in used_texts:
            return
        for c in cons:
            rule_constraints.append(c)
        rule_lines.append(text)
        used_texts.add(text)

    booster_max = 10
    count = 0

    # 左右约束（跨属性）
    for _ in range(3):
        if count >= booster_max: break
        a_attr, b_attr = rnd.choice(['func', 'equip']), rnd.choice(['safe', 'rank'])
        a_val = rnd.choice(functions if a_attr == 'func' else equipments)
        b_val = rnd.choice(safeties if b_attr == 'safe' else ranks)
        assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
        assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
        cons = _cons_left_of(pos_num, assign_a, a_val, assign_b, b_val)
        text = _line_left_of(_label(a_attr, a_val), _label(b_attr, b_val))
        add(cons, text)
        count += 1

    # 相邻约束（设备-军衔）
    if count < booster_max:
        a_attr, b_attr = 'equip', 'rank'
        a_val = rnd.choice(equipments)
        b_val = rnd.choice(ranks)
        assign_a = _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank)
        assign_b = _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank)
        cons = _cons_adjacent(pos_num, assign_a, a_val, assign_b, b_val)
        add(cons, _line_adjacent(_label(a_attr, a_val), _label(b_attr, b_val)))
        count += 1

    # 距离约束
    if count < booster_max and pos_num >= 5:
        a_attr, b_attr = 'func', 'equip'
        a_val = rnd.choice(functions)
        b_val = rnd.choice(equipments)
        k = rnd.choice([2, 3])
        cons = _cons_distance(pos_num,
                              _get_assign_map(a_attr, assign_func, assign_equip, assign_safe, assign_rank), a_val,
                              _get_assign_map(b_attr, assign_func, assign_equip, assign_safe, assign_rank), b_val, k)
        add(cons, _line_distance(_label(a_attr, a_val), _label(b_attr, b_val), k))
        count += 1

    # 奇偶相反
    if count < booster_max and len(safeties) >= 2:
        a, b = rnd.sample(safeties, 2)
        cons = _cons_opposite_parity(_get_assign_map('safe', assign_func, assign_equip, assign_safe, assign_rank), a,
                                     _get_assign_map('safe', assign_func, assign_equip, assign_safe, assign_rank), b,
                                     odd_idx, even_idx)
        add(cons, _line_opposite_parity(_label('safe', a), _label('safe', b)))
        count += 1

    # 介于（跨属性）
    if count < booster_max and pos_num >= 5:
        mid_attr, left_attr, right_attr = 'equip', 'func', 'safe'
        mid_v = rnd.choice(equipments)
        left_v = rnd.choice(functions)
        right_v = rnd.choice(safeties)
        cons = _cons_between(pos_num,
                             _get_assign_map(mid_attr, assign_func, assign_equip, assign_safe, assign_rank), mid_v,
                             _get_assign_map(left_attr, assign_func, assign_equip, assign_safe, assign_rank), left_v,
                             _get_assign_map(right_attr, assign_func, assign_equip, assign_safe, assign_rank), right_v)
        add(cons, _line_between(_label(mid_attr, mid_v), _label(left_attr, left_v), _label(right_attr, right_v)))
        count += 1

    # 左侧且不相邻（合取）
    if count < booster_max:
        f_ln = rnd.choice(functions)
        s_ln = rnd.choice(safeties)
        cons1 = _cons_left_of(pos_num,
                              _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank), f_ln,
                              _get_assign_map('safe', assign_func, assign_equip, assign_safe, assign_rank), s_ln)
        cons2 = _cons_not_adjacent(pos_num,
                                   _get_assign_map('func', assign_func, assign_equip, assign_safe, assign_rank), f_ln,
                                   _get_assign_map('safe', assign_func, assign_equip, assign_safe, assign_rank), s_ln)
        add(cons1 + cons2, f"{_label('func', f_ln)}在{_label('safe', s_ln)}左侧且不相邻")
        count += 1

    # 端点/非端点（安全或设备）
    if count < booster_max:
        if rnd.random() < 0.5:
            x = rnd.choice(safeties)
            cons = _cons_at_end_gen(pos_num,
                                    _get_assign_map('safe', assign_func, assign_equip, assign_safe, assign_rank), x)
            add(cons, _line_at_end(_label('safe', x)))
        else:
            x = rnd.choice(equipments)
            cons = _cons_not_ends_gen(pos_num,
                                      _get_assign_map('equip', assign_func, assign_equip, assign_safe, assign_rank), x)
            add(cons, _line_not_ends(_label('equip', x)))
        count += 1

    return rule_constraints, rule_lines

# -------- 模型与唯一性 --------
def _apply_bijections(s, pos_num, functions, equipments, safeties, ranks,
                      assign_func, assign_equip, assign_safe, assign_rank):
    _exactly_one_per_pos(s, assign_func, pos_num, functions)
    _each_name_once(s, assign_func, pos_num, functions)
    _exactly_one_per_pos(s, assign_equip, pos_num, equipments)
    _each_name_once(s, assign_equip, pos_num, equipments)
    _exactly_one_per_pos(s, assign_safe, pos_num, safeties)
    _each_name_once(s, assign_safe, pos_num, safeties)
    _exactly_one_per_pos(s, assign_rank, pos_num, ranks)
    _each_name_once(s, assign_rank, pos_num, ranks)

def _extract_solution(m, pos_num, functions, equipments, safeties, ranks,
                      assign_func, assign_equip, assign_safe, assign_rank):
    func_at_pos = []
    equip_at_pos = []
    safe_at_pos = []
    rank_at_pos = []
    for i in range(pos_num):
        fi = next(f for f in functions if bool(m.eval(assign_func[(i, f)])))
        ei = next(e for e in equipments if bool(m.eval(assign_equip[(i, e)])))
        si = next(s for s in safeties if bool(m.eval(assign_safe[(i, s)])))
        ri = next(r for r in ranks if bool(m.eval(assign_rank[(i, r)])))
        func_at_pos.append(fi)
        equip_at_pos.append(ei)
        safe_at_pos.append(si)
        rank_at_pos.append(ri)
    return func_at_pos, equip_at_pos, safe_at_pos, rank_at_pos

def _add_anchor_constraint(s, pos_idx, attr, value, assign_func, assign_equip, assign_safe, assign_rank):
    if attr == 'func':
        s.add(assign_func[(pos_idx, value)])
    elif attr == 'equip':
        s.add(assign_equip[(pos_idx, value)])
    elif attr == 'safe':
        s.add(assign_safe[(pos_idx, value)])
    elif attr == 'rank':
        s.add(assign_rank[(pos_idx, value)])
    else:
        raise ValueError('未知锚定属性类型')

def _block_functions(s, assign_func, m):
    # 仅阻断职能布置，保证答案（目标职能位置）唯一
    equalities = []
    for v in assign_func.values():
        val = bool(m.eval(v))
        equalities.append(v if val else Not(v))
    s.add(Not(And(equalities)))

def _build_solver(pos_num, odd_positions, even_positions,
                  assign_func, assign_equip, assign_safe, assign_rank,
                  functions, equipments, safeties, ranks,
                  rule_constraints,
                  extra_func_equip_pairs, extra_rank_safe_pairs,
                  extra_func_rank_pairs, extra_equip_safe_pairs,
                  anchors, timeout_ms):
    s = Solver()
    s.set(timeout=timeout_ms)
    _apply_bijections(s, pos_num, functions, equipments, safeties, ranks,
                      assign_func, assign_equip, assign_safe, assign_rank)

    for c in rule_constraints:
        s.add(c)

    # 额外排除对（全部渲染到题面，且用于求解）
    for (f, e) in extra_func_equip_pairs:
        for i in range(pos_num):
            s.add(Or(Not(assign_func[(i, f)]), Not(assign_equip[(i, e)])))
    for (r, sa) in extra_rank_safe_pairs:
        for i in range(pos_num):
            s.add(Or(Not(assign_rank[(i, r)]), Not(assign_safe[(i, sa)])))
    for (f, r) in extra_func_rank_pairs:
        for i in range(pos_num):
            s.add(Or(Not(assign_func[(i, f)]), Not(assign_rank[(i, r)])))
    for (e, sa) in extra_equip_safe_pairs:
        for i in range(pos_num):
            s.add(Or(Not(assign_equip[(i, e)]), Not(assign_safe[(i, sa)])))

    for (pi, attr, val) in anchors:
        _add_anchor_constraint(s, pi, attr, val, assign_func, assign_equip, assign_safe, assign_rank)
    return s

def _check_unique_functions(pos_num, odd_positions, even_positions,
                            assign_func, assign_equip, assign_safe, assign_rank,
                            functions, equipments, safeties, ranks,
                            rule_constraints,
                            extra_func_equip_pairs, extra_rank_safe_pairs,
                            extra_func_rank_pairs, extra_equip_safe_pairs,
                            anchors, timeout_ms_find, timeout_ms_check):
    s = _build_solver(pos_num, odd_positions, even_positions,
                      assign_func, assign_equip, assign_safe, assign_rank,
                      functions, equipments, safeties, ranks,
                      rule_constraints,
                      extra_func_equip_pairs, extra_rank_safe_pairs,
                      extra_func_rank_pairs, extra_equip_safe_pairs,
                      anchors, timeout_ms_find)
    r0 = s.check()
    if r0 != sat:
        return False, None
    m1 = s.model()
    _block_functions(s, assign_func, m1)
    s.set(timeout=timeout_ms_check)
    r = s.check()
    if r == unsat:
        return True, m1
    else:
        return False, m1

# -------- 主入口：构建实例并保证答案唯一（职能布置唯一） --------
def build_submarine_instance(pos_num, positions, pos_keys, odd_positions, even_positions,
                             function_pool, equipment_pool, safety_pool, rank_pool,
                             extra_excl_num, anchor_base_count, base_rule_num):
    MAX_TRY = 480
    Z3_TIMEOUT_FIND = 5000
    Z3_TIMEOUT_CHECK = 14000
    TIME_BUDGET_SEC = 180
    start_time = time.time()
    rnd = random.Random()

    def sample_names(pool, k):
        pool = list(pool)
        rnd.shuffle(pool)
        if len(pool) < k:
            raise ValueError('池大小不足以采样所需数量')
        return pool[:k]

    letters = [chr(ord('A') + i) for i in range(26)]

    for _ in range(MAX_TRY):
        if time.time() - start_time > TIME_BUDGET_SEC:
            raise RuntimeError('生成超时 请稍后重试')

        functions = sample_names(function_pool, pos_num)
        equipments = sample_names(equipment_pool, pos_num)
        safeties = sample_names(safety_pool, pos_num)
        ranks = sample_names(rank_pool, pos_num)

        target_func = rnd.choice(functions)

        assign_func = _mk_var_map(pos_keys, functions, "F")
        assign_equip = _mk_var_map(pos_keys, equipments, "E")
        assign_safe = _mk_var_map(pos_keys, safeties, "S")
        assign_rank = _mk_var_map(pos_keys, ranks, "R")

        # 基础规则池
        rule_constraints, rule_lines = _gen_rule_pool(
            rnd, pos_num, odd_positions, even_positions,
            functions, equipments, safeties, ranks,
            assign_func, assign_equip, assign_safe, assign_rank,
            target_func, base_rule_num
        )

        # 额外排除对
        extra_func_equip_pairs, extra_rank_safe_pairs, extra_func_rank_pairs, extra_equip_safe_pairs = _make_extras(
            rnd, functions, equipments, safeties, ranks, extra_excl_num
        )

        # 结构化约束前置注入（降低初始解空间）
        rule_constraints, rule_lines = _add_structured_boosters(
            rnd, pos_num, odd_positions, even_positions,
            functions, equipments, safeties, ranks,
            assign_func, assign_equip, assign_safe, assign_rank,
            rule_constraints, rule_lines
        )

        # 首次可满足性
        s0 = _build_solver(pos_num, odd_positions, even_positions,
                           assign_func, assign_equip, assign_safe, assign_rank,
                           functions, equipments, safeties, ranks,
                           rule_constraints,
                           extra_func_equip_pairs, extra_rank_safe_pairs,
                           extra_func_rank_pairs, extra_equip_safe_pairs,
                           anchors=[], timeout_ms=Z3_TIMEOUT_FIND)
        if s0.check() != sat:
            continue
        m0 = s0.model()
        func_at_pos, equip_at_pos, safe_at_pos, rank_at_pos = _extract_solution(
            m0, pos_num, functions, equipments, safeties, ranks,
            assign_func, assign_equip, assign_safe, assign_rank
        )

        # 基础锚定（避免直接公开目标职能），至少包含一条“职能”锚定
        anchors = []
        anchor_lines = []
        already = set()
        attr_choices = ['safe', 'equip', 'rank', 'func']
        letters_idx = 0

        pos_candidates = list(range(pos_num))
        rnd.shuffle(pos_candidates)
        for pi in pos_candidates:
            if len(anchors) >= anchor_base_count:
                break
            rnd.shuffle(attr_choices)
            for attr in attr_choices:
                key = (pi, attr)
                if key in already:
                    continue
                if attr == 'func' and func_at_pos[pi] == target_func:
                    continue
                if attr == 'func':
                    val = func_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的职能是{val}"
                elif attr == 'equip':
                    val = equip_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的设备是{val}"
                elif attr == 'safe':
                    val = safe_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的安全等级是{val}"
                else:
                    val = rank_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的军衔是{val}"
                anchors.append((pi, attr, val))
                already.add(key)
                anchor_lines.append(line)
                letters_idx += 1
                break

        # 若尚无职能锚定，额外补一条（避开目标）
        if not any(a[1] == 'func' for a in anchors):
            candidates_func = [i for i in range(pos_num) if func_at_pos[i] != target_func and (i, 'func') not in already]
            if candidates_func:
                pi = candidates_func[0]
                val = func_at_pos[pi]
                line = f"{letters[letters_idx]} {pi+1}号隔舱的职能是{val}"
                anchors.append((pi, 'func', val))
                already.add((pi, 'func'))
                anchor_lines.append(line)
                letters_idx += 1

        def try_unique_functions():
            return _check_unique_functions(pos_num, odd_positions, even_positions,
                                           assign_func, assign_equip, assign_safe, assign_rank,
                                           functions, equipments, safeties, ranks,
                                           rule_constraints,
                                           extra_func_equip_pairs, extra_rank_safe_pairs,
                                           extra_func_rank_pairs, extra_equip_safe_pairs,
                                           anchors, Z3_TIMEOUT_FIND, Z3_TIMEOUT_CHECK)

        # 先判断职能布置是否唯一
        is_unique, m1 = try_unique_functions()

        # 若不唯一，优先增强额外排除对（严格但上限控制）
        if not is_unique:
            def conflict_fe(pair):
                f, e = pair
                return any(func_at_pos[i] == f and equip_at_pos[i] == e for i in range(pos_num))
            def conflict_rs(pair):
                rnk, sa = pair
                return any(rank_at_pos[i] == rnk and safe_at_pos[i] == sa for i in range(pos_num))
            def conflict_fr(pair):
                f, rnk = pair
                return any(func_at_pos[i] == f and rank_at_pos[i] == rnk for i in range(pos_num))
            def conflict_es(pair):
                e, sa = pair
                return any(equip_at_pos[i] == e and safe_at_pos[i] == sa for i in range(pos_num))

            fe_limit_add = 6
            rs_limit_add = 5
            fr_limit_add = 5
            es_limit_add = 5
            fe_added = rs_added = fr_added = es_added = 0

            cand_fe = [(f, e) for f in functions for e in equipments]
            cand_rs = [(r, s) for r in ranks for s in safeties]
            cand_fr = [(f, r) for f in functions for r in ranks]
            cand_es = [(e, s) for e in equipments for s in safeties]
            rnd.shuffle(cand_fe)
            rnd.shuffle(cand_rs)
            rnd.shuffle(cand_fr)
            rnd.shuffle(cand_es)

            for (f, e) in cand_fe:
                if fe_added >= fe_limit_add:
                    break
                if (f, e) in extra_func_equip_pairs or conflict_fe((f, e)):
                    continue
                extra_func_equip_pairs.append((f, e))
                fe_added += 1

            for (rnk, sa) in cand_rs:
                if rs_added >= rs_limit_add:
                    break
                if (rnk, sa) in extra_rank_safe_pairs or conflict_rs((rnk, sa)):
                    continue
                extra_rank_safe_pairs.append((rnk, sa))
                rs_added += 1

            for (f, rnk) in cand_fr:
                if fr_added >= fr_limit_add:
                    break
                if (f, rnk) in extra_func_rank_pairs or conflict_fr((f, rnk)):
                    continue
                extra_func_rank_pairs.append((f, rnk))
                fr_added += 1

            for (e, sa) in cand_es:
                if es_added >= es_limit_add:
                    break
                if (e, sa) in extra_equip_safe_pairs or conflict_es((e, sa)):
                    continue
                extra_equip_safe_pairs.append((e, sa))
                es_added += 1

            is_unique, m1 = try_unique_functions()

        # 若仍不唯一，增加结构化约束（再注入一批）
        if not is_unique:
            rule_constraints, rule_lines = _add_structured_boosters(
                rnd, pos_num, odd_positions, even_positions,
                functions, equipments, safeties, ranks,
                assign_func, assign_equip, assign_safe, assign_rank,
                rule_constraints, rule_lines
            )
            is_unique, m1 = try_unique_functions()

        # 若仍不唯一，增加兜底锚定（避开目标职能），锚定上限收敛（由4降至2）
        if not is_unique:
            add_anchors_max = 2
            add_count = 0
            candidates = []
            for pi in range(pos_num):
                for attr in ['safe', 'equip', 'rank', 'func']:
                    if (pi, attr) not in already:
                        candidates.append((pi, attr))
            rnd.shuffle(candidates)
            for (pi, attr) in candidates:
                if add_count >= add_anchors_max:
                    break
                if attr == 'func' and func_at_pos[pi] == target_func:
                    continue
                if attr == 'func':
                    val = func_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的职能是{val}"
                elif attr == 'equip':
                    val = equip_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的设备是{val}"
                elif attr == 'safe':
                    val = safe_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的安全等级是{val}"
                else:
                    val = rank_at_pos[pi]
                    line = f"{letters[letters_idx]} {pi+1}号隔舱的军衔是{val}"
                anchors.append((pi, attr, val))
                already.add((pi, attr))
                anchor_lines.append(line)
                letters_idx += 1
                add_count += 1
            is_unique, m1 = try_unique_functions()
            if not is_unique:
                continue

        # 抽取最终解（职能唯一）
        m_final = m1
        func_at_pos_f, equip_at_pos_f, safe_at_pos_f, rank_at_pos_f = _extract_solution(
            m_final, pos_num, functions, equipments, safeties, ranks,
            assign_func, assign_equip, assign_safe, assign_rank
        )
        target_pos = next(i + 1 for i in range(pos_num) if func_at_pos_f[i] == target_func)

        # 文本去重：过滤掉与基础线索重复的额外线索文本
        used_texts = set(rule_lines)

        extra_func_equip_lines = []
        for (f, e) in extra_func_equip_pairs:
            line = _line_not_same(_label('func', f), _label('equip', e))
            if line not in used_texts:
                extra_func_equip_lines.append(line)
                used_texts.add(line)

        extra_rank_safe_lines = []
        for (rnk, sa) in extra_rank_safe_pairs:
            line = _line_not_same(_label('rank', rnk), _label('safe', sa))
            if line not in used_texts:
                extra_rank_safe_lines.append(line)
                used_texts.add(line)

        extra_func_rank_lines = []
        for (f, rnk) in extra_func_rank_pairs:
            line = _line_not_same(_label('func', f), _label('rank', rnk))
            if line not in used_texts:
                extra_func_rank_lines.append(line)
                used_texts.add(line)

        extra_equip_safe_lines = []
        for (e, sa) in extra_equip_safe_pairs:
            line = _line_not_same(_label('equip', e), _label('safe', sa))
            if line not in used_texts:
                extra_equip_safe_lines.append(line)
                used_texts.add(line)

        payload = {
            'functions': functions,
            'equipments': equipments,
            'safeties': safeties,
            'ranks': ranks,
            'target_func': target_func,
            'target_pos': target_pos,
            'base_lines': rule_lines,
            'extra_func_equip_lines': extra_func_equip_lines,
            'extra_rank_safe_lines': extra_rank_safe_lines,
            'extra_func_rank_lines': extra_func_rank_lines,
            'extra_equip_safe_lines': extra_equip_safe_lines,
            'anchor_lines': anchor_lines
        }
        return payload

    raise RuntimeError('无法在时间限制内生成唯一解实例 请重试')