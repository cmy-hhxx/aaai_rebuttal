# knights_knaves_puzzle_4.py
# 复合逻辑与文本函数（题面只呈现规则，不含生成逻辑与唯一性提示）

import random
from z3 import And, Or, Not, Implies, If, Xor, Sum

def function_1(_sym, role_s, vow_s, group_s, names, is_day, mix_mode):
    """
    构造单条陈述的约束：
    - 根据模板生成陈述真值 statement_truth
    - 根据陈述解释模式 mix_mode 对陈述真值进行变换：
        direct: 无变换
        xor_vow: 若说话者受誓约则陈述真值按 XOR 翻转（等价于反向解释）
        flip_group: 若说话者分组编号为0则陈述真值反向解释
    - 时段映射：
        白天: role[speaker] == mapped_truth
        夜晚: role[speaker] != mapped_truth
    """
    speaker = _sym[0][0]
    a = _sym[1][0]
    b = _sym[2][0]
    tpl = _sym[3][0]

    # 生成陈述真值
    if tpl == 'eq':
        statement_truth = (role_s[a] == role_s[b])
    elif tpl == 'neq':
        statement_truth = (role_s[a] != role_s[b])
    elif tpl == 'impl_ab':
        statement_truth = Implies(role_s[a], Not(role_s[b]))
    elif tpl == 'impl_ba':
        statement_truth = Implies(role_s[b], Not(role_s[a]))
    elif tpl == 'iff_same':
        statement_truth = (role_s[a] == role_s[b])
    elif tpl == 'iff_neg':
        statement_truth = (role_s[a] == Not(role_s[b]))
    elif tpl == 'or_knave':
        statement_truth = Or(Not(role_s[a]), Not(role_s[b]))
    elif tpl == 'and_knight':
        statement_truth = And(role_s[a], role_s[b])
    elif tpl == 'speaker_eq_a':
        statement_truth = (role_s[speaker] == role_s[a])
    elif tpl == 'speaker_neq_a':
        statement_truth = (role_s[speaker] != role_s[a])
    elif tpl == 'speaker_impl_b':
        statement_truth = Implies(role_s[speaker], Not(role_s[b]))
    elif tpl == 'b_impl_speaker':
        statement_truth = Implies(role_s[b], Not(role_s[speaker]))
    elif tpl == 'speaker_iff_neg_a':
        statement_truth = (role_s[speaker] == Not(role_s[a]))
    else:
        statement_truth = (role_s[a] == role_s[b])

    # 按解释模式变换
    if mix_mode == 'xor_vow':
        mapped_truth = Xor(statement_truth, vow_s[speaker])
    elif mix_mode == 'flip_group':
        mapped_truth = If(group_s[speaker].get('gid') == 0, Not(statement_truth), statement_truth)
    else:  # direct
        mapped_truth = statement_truth

    # 日夜映射
    return (role_s[speaker] == mapped_truth) if is_day else (role_s[speaker] != mapped_truth)


def function_2(_sym, names):
    """
    生成陈述文本（不包含任何内部提示；题面规则已在主描述中说明）。
    """
    speaker = _sym[0][0]
    a = _sym[1][0]
    b = _sym[2][0]
    tpl = _sym[3][0]

    phr = {
        'eq': [
            f"{speaker}: {a} 与 {b} 是同类。",
            f"{speaker}: 我认为 {a} 和 {b} 类型相同。"
        ],
        'neq': [
            f"{speaker}: {a} 与 {b} 不是同类。",
            f"{speaker}: 我认为 {a} 和 {b} 类型不同。"
        ],
        'impl_ab': [
            f"{speaker}: 如果 {a} 是昼骑士夜骗子, 那么 {b} 是昼骗子夜骑士。",
            f"{speaker}: 若 {a} 白天说真话, 则 {b} 白天说假话。"
        ],
        'impl_ba': [
            f"{speaker}: 如果 {b} 是昼骑士夜骗子, 那么 {a} 是昼骗子夜骑士。",
            f"{speaker}: 若 {b} 白天说真话, 则 {a} 白天说假话。"
        ],
        'iff_same': [
            f"{speaker}: {a} 与 {b} 当且仅当同类。",
            f"{speaker}: {a} 和 {b} 类型相同当且仅当成立。"
        ],
        'iff_neg': [
            f"{speaker}: {a} 与 {b} 当且仅当不同类。",
            f"{speaker}: {a} 和 {b} 类型不同当且仅当成立。"
        ],
        'or_knave': [
            f"{speaker}: {a} 与 {b} 至少一位是昼骗子夜骑士。",
            f"{speaker}: {a} 或 {b} 至少一人白天说假话。"
        ],
        'and_knight': [
            f"{speaker}: {a} 与 {b} 都是昼骑士夜骗子。",
            f"{speaker}: 我认为 {a} 和 {b} 白天都说真话。"
        ],
        'speaker_eq_a': [
            f"{speaker}: 我的类型与 {a} 相同。",
            f"{speaker}: 我和 {a} 是同类。"
        ],
        'speaker_neq_a': [
            f"{speaker}: 我的类型与 {a} 不同。",
            f"{speaker}: 我和 {a} 不是同类。"
        ],
        'speaker_impl_b': [
            f"{speaker}: 如果我是昼骑士夜骗子, 那么 {b} 是昼骗子夜骑士。",
            f"{speaker}: 若我白天说真话, 则 {b} 白天说假话。"
        ],
        'b_impl_speaker': [
            f"{speaker}: 如果 {b} 是昼骑士夜骗子, 那么我就是昼骗子夜骑士。",
            f"{speaker}: 若 {b} 白天说真话, 则我白天说假话。"
        ],
        'speaker_iff_neg_a': [
            f"{speaker}: 我当且仅当与 {a} 不同类。",
            f"{speaker}: 我与 {a} 类型不同当且仅当成立。"
        ],
        'default': [
            f"{speaker}: {a} 与 {b} 是同类。",
            f"{speaker}: 我认为 {a} 和 {b} 类型相同。"
        ]
    }
    return random.choice(phr.get(tpl, phr['default']))


def function_3(group_relation, group_num, names, role_s, group_s):
    """
    分组角色关系约束生成：
    - dominant: 分组0的骑士数 >= 其他分组
    - balanced: 分组0与分组1骑士数相等（若group_num==2刚好；若==3忽略组2）
    - none: 返回 True（不加约束）
    """
    roles_in_group = []
    for g in range(group_num):
        roles_in_group.append(Sum([
            If(group_s[names[i]].get('gid') == g, If(role_s[names[i]], 1, 0), 0)
            for i in range(len(names))
        ]))

    if group_relation == 'dominant':
        return And([roles_in_group[0] >= roles_in_group[g] for g in range(1, group_num)]) if group_num > 1 else True
    elif group_relation == 'balanced':
        return (roles_in_group[0] == roles_in_group[1]) if group_num >= 2 else True
    else:
        return True


def function_4(names, role_s, vow_s, monk_num, chain_strength):
    """
    链式隐式约束：
    对随机选取的 chain_strength 个索引 i：
        Implies(vow[i], Or(role[(i+1)%n], Not(role[(i+2)%n])))
    构成环形链式影响。
    """
    idxs = list(range(monk_num))
    chosen = random.sample(idxs, k=min(chain_strength, monk_num))
    clauses = []
    for i in chosen:
        next1 = names[(i + 1) % monk_num]
        next2 = names[(i + 2) % monk_num]
        me = names[i]
        clauses.append(Implies(vow_s[me], Or(role_s[next1], Not(role_s[next2]))))
    return And(clauses) if len(clauses) > 0 else True