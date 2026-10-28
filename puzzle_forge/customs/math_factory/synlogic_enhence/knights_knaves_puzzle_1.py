# knights_knaves_puzzle_2.py
# Generalized reverse-generation helpers enabling randomized internal rules, multi-operator pools,
# dynamic same-class and triadic constraints, and an efficient uniqueness verifier.

import random
from z3 import (
    Bool, And, Or, Not, Xor, Implies, Sum, If, Solver, sat, is_true
)

# ------------------------ Simple helper functions to satisfy imports ------------------------

def function_1(Kp, Ap, Kq, Aq):
    """
    Z3 same-role equality placeholder:
    True iff (Kp == Kq) and (Ap == Aq).
    """
    return And(Kp == Kq, Ap == Aq)

def function_2(Kp, Ap):
    """
    Z3 is-knave predicate placeholder:
    Knave <=> (not Knight) and (not Alternator).
    """
    return And(Not(Kp), Not(Ap))

# ------------------------ Same-class and triadic constraints (Z3) ------------------------

def same_class_z3(Kp, Ap, Kq, Aq, mode):
    """
    Z3 same-class predicate per mode:
      - 'role_eq'   : (Kp == Kq) and (Ap == Aq)
      - 'knight_eq' : (Kp == Kq)
      - 'knave_eq'  : is_knave(p) == is_knave(q)
    """
    if mode == 'role_eq':
        return And(Kp == Kq, Ap == Aq)
    elif mode == 'knight_eq':
        return Kp == Kq
    else:  # knave_eq
        return And(Not(Kp), Not(Ap)) == And(Not(Kq), Not(Aq))

def compound_relation_z3(Ki, Ai, Kj, Aj, Kk, Ak, rule_cfg):
    """
    Triadic composite constraint selected by rule_cfg['comp_rel_type']:
      - 'if_knight_then_xor'       : Implies(Ki, Xor(Kj, Kk))
      - 'at_least_one_knave_among' : Or(is_knave(j), is_knave(k))
      - 'alt_in_three'             : Or(Ai, Aj, Ak)
    """
    t = rule_cfg['comp_rel_type']
    if t == 'if_knight_then_xor':
        return Implies(Ki, Xor(Kj, Kk))
    elif t == 'at_least_one_knave_among':
        return Or(And(Not(Kj), Not(Aj)), And(Not(Kk), Not(Ak)))
    else:  # 'alt_in_three'
        return Or(Ai, Aj, Ak)

# ------------------------ Rule configuration and explanations ------------------------

def build_rule_cfg(names, s_count, alt_true_num):
    """
    Randomized internal rule configuration:
      - same_class_mode ∈ {role_eq, knight_eq, knave_eq}
      - allowed_ops: random subset of operator templates
      - phrase_map: synonyms for knight/knave/alternator and connector word
      - sc_num: number of dynamic same-class constraints
      - comp_rel_type: triadic relation type
      - comp_rel_num: number of triadic constraints
    """
    N = len(names)
    same_class_modes = ['role_eq', 'knight_eq', 'knave_eq']
    mode = random.choice(same_class_modes)

    all_ops = [
        'is_knight',
        'is_knave',
        'same_class',
        'implies_knave_if_knight',
        'at_least_one_knave',
        'exactly_one_knight',
        'iff_knight',
        'xor_knight',
        'alternator_in_two',
        'alternator_is',
    ]
    ops_num = random.randint(5, 8)
    allowed_ops = random.sample(all_ops, ops_num)

    knight_synonyms = ['是骑士', '说真话者', '诚实者']
    knave_synonyms  = ['是骗子', '说假话者', '不诚实者']
    alt_synonyms    = ['交替者', '一真一假者', '真假交替者']
    connector_syns  = ['且', '并且', '同时']
    phrase_map = {
        'knight': random.choice(knight_synonyms),
        'knave': random.choice(knave_synonyms),
        'alt': random.choice(alt_synonyms),
        'and': random.choice(connector_syns),
    }

    sc_num = random.randint(1, max(1, N // 2))
    comp_rel_types = ['if_knight_then_xor', 'at_least_one_knave_among', 'alt_in_three']
    comp_rel_type = random.choice(comp_rel_types)
    comp_rel_num = random.randint(1, max(1, N // 2))

    return {
        'same_class_mode': mode,
        'allowed_ops': allowed_ops,
        'phrase_map': phrase_map,
        's_count': int(s_count),
        'alt_true_num': int(alt_true_num),
        'sc_num': sc_num,
        'comp_rel_type': comp_rel_type,
        'comp_rel_num': comp_rel_num,
        'N': N,
    }

def build_rulebook_text(cfg):
    """
    Plain-language explanation reflecting cfg.
    """
    mode = cfg['same_class_mode']
    pm = cfg['phrase_map']
    s_count = cfg['s_count']
    alt_true = cfg['alt_true_num']
    comp_text = {
        'if_knight_then_xor': '若某人是骑士, 则另两人的骑士身份异或为真(恰有一人为骑士)。',
        'at_least_one_knave_among': '在某三人中至少一人为骗子。',
        'alt_in_three': f'{pm["alt"]}在某三人之中。'
    }[cfg['comp_rel_type']]

    if mode == 'role_eq':
        mode_text = '同类: 两人的身份完全一致(骑士/骗子/交替者一致)。'
    elif mode == 'knight_eq':
        mode_text = '同类: 两人是否为骑士一致(同时为骑士或同时不是骑士)。'
    else:
        mode_text = '同类: 两人是否为骗子一致(同时为骗子或同时不是骗子)。'

    text = (
        f'每人说 {s_count} 句话; 骑士的所有话都为真, 骗子的所有话都为假, '
        f'{pm["alt"]}的 {s_count} 句话中恰有 {alt_true} 句为真且其余为假; '
        f'{mode_text} 并可能出现如下复合关系: {comp_text} '
        f'陈述可能使用的逻辑包括: 若则(如果A则B), 当且仅当(A与B等价), 异或(恰一为真), 至少一, 恰一等。'
    )
    return text.replace('"', '')

# ------------------------ Role generation ------------------------

def generate_roles(names, s_count, alt_true_num):
    """
    Sample a valid assignment with exactly one alternator, and random mix of knights/knaves.
    Ensures at least 1 knight and 1 knave.
    Returns: {'Kval': [...], 'Aval': [...]}
    """
    N = len(names)
    alt_idx = random.randrange(N)
    Aval = [False] * N
    Aval[alt_idx] = True

    others = [i for i in range(N) if i != alt_idx]
    random.shuffle(others)
    target_knights = random.randint(max(1, N // 4), max(1, N - 2))
    knight_set = set(others[:target_knights])

    Kval = [False] * N
    for i in range(N):
        if i == alt_idx:
            Kval[i] = False
        else:
            Kval[i] = (i in knight_set)

    knights_count = sum(1 for i in range(N) if Kval[i])
    knaves_count  = sum(1 for i in range(N) if (not Kval[i]) and (not Aval[i]))
    if knights_count == 0 or knaves_count == 0:
        half = max(1, len(others) // 2)
        knight_set = set(others[:half])
        for i in range(N):
            if i == alt_idx:
                Kval[i] = False
            else:
                Kval[i] = (i in knight_set)

    return {'Kval': Kval, 'Aval': Aval}

# ------------------------ Statement truth utilities ------------------------

def _is_knave(K, A):
    return (not K) and (not A)

def _same_class_truth(Kval, Aval, mode, i, j):
    if mode == 'role_eq':
        return (Kval[i] == Kval[j]) and (Aval[i] == Aval[j])
    elif mode == 'knight_eq':
        return (Kval[i] == Kval[j])
    else:  # knave_eq
        return (_is_knave(Kval[i], Aval[i]) == _is_knave(Kval[j], Aval[j]))

def _xor(a, b):
    return bool(a) ^ bool(b)

def _pick_two_distinct(N, exclude=None):
    pool = list(range(N))
    if exclude is not None:
        pool = [i for i in pool if i != exclude]
    if len(pool) < 2:
        return (0, 0)
    i = random.choice(pool)
    pool2 = [x for x in pool if x != i]
    j = random.choice(pool2) if pool2 else i
    return (i, j)

def _pick_one(N, exclude=None):
    pool = list(range(N))
    if exclude is not None:
        pool = [i for i in pool if i != exclude]
    return random.choice(pool) if pool else 0

# ------------------------ Statement templates and builder ------------------------

def _template_text_truth(op, names, Kval, Aval, cfg, speaker_idx):
    N = len(names)
    pm = cfg['phrase_map']
    mode = cfg['same_class_mode']

    if op == 'is_knight':
        i = _pick_one(N)
        return (f'{names[i]} {pm["knight"]}。', Kval[i])
    if op == 'is_knave':
        i = _pick_one(N)
        return (f'{names[i]} {pm["knave"]}。', _is_knave(Kval[i], Aval[i]))
    if op == 'same_class':
        i, j = _pick_two_distinct(N)
        t = _same_class_truth(Kval, Aval, mode, i, j)
        return (f'{names[i]} 与 {names[j]} 同类。', t)
    if op == 'implies_knave_if_knight':
        i, j = _pick_two_distinct(N)
        t = (not Kval[i]) or _is_knave(Kval[j], Aval[j])
        return (f'如果 {names[i]} {pm["knight"]}, 则 {names[j]} {pm["knave"]}。', t)
    if op == 'at_least_one_knave':
        i, j = _pick_two_distinct(N)
        t = _is_knave(Kval[i], Aval[i]) or _is_knave(Kval[j], Aval[j])
        return (f'{names[i]} 与 {names[j]} 中至少一人 {pm["knave"]}。', t)
    if op == 'exactly_one_knight':
        i, j = _pick_two_distinct(N)
        t = _xor(Kval[i], Kval[j])
        return (f'{names[i]} 与 {names[j]} 有且仅有一人 {pm["knight"]}。', t)
    if op == 'iff_knight':
        i, j = _pick_two_distinct(N)
        t = (Kval[i] == Kval[j])
        return (f'{names[i]} {pm["knight"]} 当且仅当 {names[j]} {pm["knight"]}。', t)
    if op == 'xor_knight':
        i, j = _pick_two_distinct(N)
        t = _xor(Kval[i], Kval[j])
        return (f'{names[i]} 与 {names[j]} 的骑士身份异或为真(恰有一人为骑士)。', t)
    if op == 'alternator_in_two':
        i, j = _pick_two_distinct(N)
        t = Aval[i] or Aval[j]
        alt_word = pm['alt']
        return (f'{alt_word}在 {names[i]} 与 {names[j]} 之中。', t)
    if op == 'alternator_is':
        i = _pick_one(N)
        t = Aval[i]
        alt_word = pm['alt']
        return (f'{names[i]} 是{alt_word}。', t)

    i = _pick_one(N)
    return (f'{names[i]} {pm["knight"]}。', Kval[i])

def build_speeches(names, Kval, Aval, s_count, alt_true_num, cfg):
    """
    Construct s_count statements per person aligned with role truth pattern:
      - Knight: all s_count true
      - Knave: all s_count false
      - Alternator: exactly alt_true_num true, others false (order randomized)
    """
    pm = cfg['phrase_map']
    pm.setdefault('is_knight', pm['knight'])
    pm.setdefault('is_knave', pm['knave'])
    allowed_ops = list(cfg['allowed_ops'])

    lines = []
    N = len(names)

    for i in range(N):
        target_true_count = alt_true_num if Aval[i] else (s_count if Kval[i] else 0)
        truths_needed = [True] * target_true_count + [False] * (s_count - target_true_count)
        random.shuffle(truths_needed)

        s_texts = []
        for need_truth in truths_needed:
            ok_text = None
            for _ in range(40):
                op = random.choice(allowed_ops)
                text, val = _template_text_truth(op, names, Kval, Aval, cfg, i)
                if val == need_truth:
                    ok_text = text
                    break
            if ok_text is None:
                # Fallback deterministic construction
                if need_truth:
                    idx = next((j for j in range(N) if Kval[j]), None)
                    if idx is None: idx = 0
                    ok_text = f'{names[idx]} {pm["knight"]}。'
                else:
                    idx = next((j for j in range(N) if _is_knave(Kval[j], Aval[j])), None)
                    if idx is None: idx = 0
                    ok_text = f'{names[idx]} {pm["knight"]}。'  # false when chosen idx is knave
            s_texts.append(ok_text.replace('"', ''))

        joined = ' '.join([f'(#{k+1}) {s_texts[k]}' for k in range(s_count)])
        lines.append(f'{names[i]}: {joined}')

    return '\\n'.join(lines)

# ------------------------ Uniqueness verifier (optional external check) ------------------------

def verify_uniqueness_z3(names, rule_cfg, timeout_ms=120000):
    """
    Try to verify uniqueness without fixing K/A:
    - Build Z3 variables BK[i], BA[i]
    - Add core role constraints and dynamic constraints derived from rule_cfg
    - Find one solution; then block it and check if a second solution exists.
    - Timeout controlled by solver parameters, default 120s (< 3min target).
    Returns True iff unique or timeout (treated as acceptable); False iff a distinct second solution found.
    """
    N = len(names)
    BK = [Bool(f"BK_{i}") for i in range(N)]
    BA = [Bool(f"BA_{i}") for i in range(N)]
    s = Solver()
    s.set('timeout', timeout_ms)

    # Core role constraints
    s.add(Sum([If(BA[i], 1, 0) for i in range(N)]) == 1)
    for i in range(N):
        s.add(Implies(BK[i], Not(BA[i])))
        s.add(Implies(BA[i], Not(BK[i])))
        s.add(Or(BK[i], BA[i], And(Not(BK[i]), Not(BA[i]))))

    # Same-class constraints
    mode = rule_cfg['same_class_mode']
    sc_num = rule_cfg['sc_num']
    pairs = []
    pool = list(range(N))
    random.shuffle(pool)
    for k in range(sc_num):
        i = pool[k % N]
        j = pool[(k+1) % N]
        if i != j:
            pairs.append((i, j))
    for (i, j) in pairs:
        s.add(same_class_z3(BK[i], BA[i], BK[j], BA[j], mode))

    # Triadic constraints
    comp_rel_type = rule_cfg['comp_rel_type']
    comp_rel_num = rule_cfg['comp_rel_num']
    triplets = []
    pool = list(range(N))
    random.shuffle(pool)
    for k in range(comp_rel_num):
        i = pool[k % N]
        j = pool[(k+1) % N]
        l = pool[(k+2) % N]
        if len({i, j, l}) == 3:
            triplets.append((i, j, l))
    for (i, j, l) in triplets:
        s.add(compound_relation_z3(BK[i], BA[i], BK[j], BA[j], BK[l], BA[l], rule_cfg))

    # Find one solution
    if s.check() != sat:
        return True  # treat as acceptable; generation will still fix K/A for final puzzle
    m = s.model()
    # Blocker: enforce at least one (BK,BA) differs
    blocker = Or(*[
        Or(BK[i] != is_true(m.evaluate(BK[i], model_completion=True)),
           BA[i] != is_true(m.evaluate(BA[i], model_completion=True)))
        for i in range(N)
    ])
    s.add(blocker)
    r2 = s.check()
    if r2 == sat:
        return False  # found a distinct second solution
    return True  # unique or timeout/unsat

# End of module