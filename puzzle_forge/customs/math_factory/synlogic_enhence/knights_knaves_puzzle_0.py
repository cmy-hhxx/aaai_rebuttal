# knights_knaves_puzzle_0.py
# Advanced generalized helpers for Knights & Knaves puzzle generation with layered composite reasoning.
# Exposes:
# - function_1, function_2: simple placeholders per spec
# - build_knights_instance: reference instance generator returning [[knaves],[knights]]
# - build_statements: synthesize per-speaker statements consistent with ground truth and groups
# - truth_expr: build Z3 Bool expression for one statement config
# - build_meta_rules: randomized global facts consistent with ground truth and groups
# - meta_rule_expr: build Z3 Bool expression for one meta rule
from typing import List, Tuple, Dict, Any
import random
from z3 import And, Or, Not, Implies, Xor, Sum, If, BoolVal, IntVal  # Removed Mod import; use % operator

def function_1(x):
    """Placeholder custom operator function."""
    return x

def function_2(x, y=None):
    """Placeholder custom operator function with two parameters."""
    return (x, y)

# -------------------------
# Statement synthesis utils
# -------------------------
def _pick_two_distinct(n: int, exclude: int = None) -> Tuple[int, int]:
    pool = [i for i in range(n) if (exclude is None or i != exclude)]
    if len(pool) < 2:
        pool = [i for i in range(n)]
    a = random.choice(pool)
    b_choices = [i for i in pool if i != a]
    b = random.choice(b_choices) if b_choices else a
    return a, b

def _pick_one(n: int, exclude: int = None) -> int:
    choices = [i for i in range(n) if (exclude is None or i != exclude)] or [i for i in range(n)]
    return random.choice(choices)

def _pick_subset(n: int, min_size: int, max_size: int, exclude: int = None) -> List[int]:
    cand = [i for i in range(n) if (exclude is None or i != exclude)]
    size = random.randint(min_size, min(max_size, len(cand)))
    random.shuffle(cand)
    return cand[:size]

def _subset_text(names: List[str], idxs: List[int]) -> str:
    return '[' + ', '.join(names[i] for i in idxs) + ']'

def _truth_of_tpl(tpl: str, K: List[bool], args: Tuple[int, ...], subset: List[int] = None,
                  count: int = None, parity: str = None, group: int = None,
                  cond_type: str = None, cons_index: int = None, cons_polarity: bool = True,
                  group_assignment: List[int] = None) -> bool:
    """Compute truth of a statement template under ground truth K (non-Z3, used to decide neg)."""
    a = args[0] if args else None
    b = args[1] if args and len(args) > 1 else None
    if tpl == 'OR': return K[a] or K[b]
    if tpl == 'AND': return K[a] and K[b]
    if tpl == 'XOR': return (K[a] != K[b])
    if tpl == 'IFF_KNAVE': return (K[a] == (not K[b]))
    if tpl == 'IFF_KNIGHT': return (K[a] == K[b])
    if tpl == 'IMPLIES_KNAVE_THEN_KNIGHT': return ((not K[a]) or K[b])
    if tpl == 'ASSERT_KNIGHT': return K[a]
    if tpl == 'ASSERT_KNAVE': return (not K[a])
    if tpl in ('COUNT_EQ','COUNT_GE','COUNT_LE','PARITY_SUBSET'):
        cnt = sum(1 for i in subset if K[i])
        if tpl == 'COUNT_EQ': return (cnt == count)
        if tpl == 'COUNT_GE': return (cnt >= count)
        if tpl == 'COUNT_LE': return (cnt <= count)
        if tpl == 'PARITY_SUBSET': return (cnt % 2 == (0 if parity == 'even' else 1))
    if tpl in ('GROUP_MAJORITY','GROUP_MINORITY') and group is not None:
        members = [i for i, g in enumerate(group_assignment) if g == group]
        cnt = sum(1 for i in members if K[i])
        m = len(members)
        if tpl == 'GROUP_MAJORITY': return cnt > (m - cnt)
        if tpl == 'GROUP_MINORITY': return cnt < (m - cnt)
    if tpl == 'COND_COUNT_IMPLIES':
        cnt = sum(1 for i in subset if K[i])
        cond_ok = (cnt == count) if cond_type == 'EQ' else (cnt >= count) if cond_type == 'GE' else (cnt <= count)
        cons_truth = (K[cons_index] if cons_polarity else (not K[cons_index]))
        return (not cond_ok) or cons_truth  # implication truth
    return True

def _tpl_text(tpl: str, names: List[str], args: Tuple[int, ...], subset: List[int] = None,
              count: int = None, parity: str = None, group: int = None, group_names: List[str] = None,
              cond_type: str = None, cons_index: int = None, cons_polarity: bool = True) -> str:
    """Human-readable statement text, single-quote safe."""
    a = args[0] if args else None
    b = args[1] if args and len(args) > 1 else None
    if tpl == 'OR': return f'{names[a]} is a knight or {names[b]} is a knight'
    if tpl == 'AND': return f'{names[a]} is a knight and {names[b]} is a knight'
    if tpl == 'XOR': return f'Exactly one of {names[a]} and {names[b]} is a knight'
    if tpl == 'IFF_KNAVE': return f'{names[a]} is a knight if and only if {names[b]} is a knave'
    if tpl == 'IFF_KNIGHT': return f'{names[a]} is a knight if and only if {names[b]} is a knight'
    if tpl == 'IMPLIES_KNAVE_THEN_KNIGHT': return f'If {names[a]} is a knave then {names[b]} is a knight'
    if tpl == 'ASSERT_KNIGHT': return f'{names[a]} is a knight'
    if tpl == 'ASSERT_KNAVE': return f'{names[a]} is a knave'
    if tpl == 'COUNT_EQ': return f'Exactly {count} of the people in the subset { _subset_text(names, subset) } are knights'
    if tpl == 'COUNT_GE': return f'At least {count} of the people in the subset { _subset_text(names, subset) } are knights'
    if tpl == 'COUNT_LE': return f'At most {count} of the people in the subset { _subset_text(names, subset) } are knights'
    if tpl == 'PARITY_SUBSET': return f'The number of knights in the subset { _subset_text(names, subset) } is {parity}'
    if tpl == 'GROUP_MAJORITY': return f'In {group_names[group]}, there are more knights than knaves'
    if tpl == 'GROUP_MINORITY': return f'In {group_names[group]}, there are fewer knights than knaves'
    if tpl == 'COND_COUNT_IMPLIES':
        cond_word = 'equal to' if cond_type == 'EQ' else 'at least' if cond_type == 'GE' else 'at most'
        cons_text = (f'{names[cons_index]} is a knight' if cons_polarity else f'{names[cons_index]} is a knave')
        return f'If the number of knights in subset { _subset_text(names, subset) } is {cond_word} {count}, then {cons_text}'
    return 'True'

def build_statements(names: List[str], assignment: List[bool],
                     group_assignment: List[int], group_num: int, group_names: List[str]) -> List[Dict[str, Any]]:
    """
    Build per-speaker statement configs consistent with the given ground truth 'assignment' and groups.
    Each config contains rich fields and guarantees truth(statement_i) == assignment[i].
    """
    n = len(names)
    K = assignment[:]
    templates_pool = [
        'OR','AND','XOR','IFF_KNAVE','IMPLIES_KNAVE_THEN_KNIGHT','IFF_KNIGHT',
        'ASSERT_KNIGHT','ASSERT_KNAVE',
        'COUNT_EQ','COUNT_GE','COUNT_LE','PARITY_SUBSET',
        'GROUP_MAJORITY','GROUP_MINORITY',
        'COND_COUNT_IMPLIES'
    ]
    configs: List[Dict[str, Any]] = []

    for i in range(n):
        speaker = names[i]
        tpl_candidates = templates_pool[:]
        random.shuffle(tpl_candidates)
        chosen_tpl = None
        args: Tuple[int, ...] = tuple()
        subset: List[int] = []
        count = None
        parity = None
        group = None
        cond_type = None
        cons_index = None
        cons_polarity = True
        neg = bool(random.getrandbits(1))
        found = False

        for tpl in tpl_candidates:
            if tpl in ('OR','AND','XOR','IFF_KNAVE','IMPLIES_KNAVE_THEN_KNIGHT','IFF_KNIGHT'):
                a, b = _pick_two_distinct(n, exclude=None)
                args = (a, b)
            elif tpl in ('ASSERT_KNIGHT','ASSERT_KNAVE'):
                a = _pick_one(n, exclude=None)
                args = (a,)
            elif tpl in ('COUNT_EQ','COUNT_GE','COUNT_LE','PARITY_SUBSET'):
                subset = _pick_subset(n, min_size=2, max_size=min(5, n), exclude=None)
                if tpl == 'PARITY_SUBSET':
                    parity = 'even' if random.getrandbits(1) == 0 else 'odd'
                else:
                    count = random.randint(0, len(subset))
            elif tpl in ('GROUP_MAJORITY','GROUP_MINORITY'):
                group = random.randint(0, group_num - 1)
            elif tpl == 'COND_COUNT_IMPLIES':
                subset = _pick_subset(n, min_size=2, max_size=min(5, n), exclude=None)
                cond_type = random.choice(['EQ','GE','LE'])
                count = random.randint(0, len(subset))
                cons_index = _pick_one(n, exclude=None)
                cons_polarity = (random.getrandbits(1) == 1)

            base_truth = _truth_of_tpl(
                tpl, K, args, subset, count, parity, group, cond_type, cons_index, cons_polarity, group_assignment
            )
            final_truth = (not base_truth) if neg else base_truth
            if final_truth != K[i]:
                neg = not neg
                final_truth = (not base_truth) if neg else base_truth
            if final_truth == K[i]:
                chosen_tpl = tpl
                found = True
                break

        if not found:
            chosen_tpl = 'ASSERT_KNIGHT'
            a = _pick_one(n, exclude=None)
            args = (a,)
            base_truth = _truth_of_tpl(chosen_tpl, K, args, group_assignment=group_assignment)
            neg = (base_truth != K[i])

        text_raw = _tpl_text(chosen_tpl, names, args, subset, count, parity, group, group_names, cond_type, cons_index, cons_polarity)
        text = ('not ' + text_raw) if neg else text_raw

        configs.append({
            'speaker': speaker,
            'tpl': chosen_tpl,
            'args': args,
            'subset': subset,
            'count': count,
            'parity': parity,
            'group': group,
            'cond_type': cond_type,
            'cons_index': cons_index,
            'cons_polarity': cons_polarity,
            'neg': neg,
            'text': text
        })

    return configs

# -------------------------
# Z3 expression builders
# -------------------------
def _subset_sum_knights(knights: Dict[str, Any], inhabitants: List[str], idxs: List[int]):
    return Sum([If(knights[inhabitants[i]], IntVal(1), IntVal(0)) for i in idxs])

def _group_members_indices(group_assignment: List[int], g: int) -> List[int]:
    return [i for i, gg in enumerate(group_assignment) if gg == g]

def truth_expr(knights: Dict[str, Any], inhabitants: List[str], cfg: Dict[str, Any],
               group_assignment: List[int], group_num: int):
    """Return a Z3 Bool expression for the truth value of one statement config."""
    tpl = cfg['tpl']
    args = cfg.get('args', tuple())
    subset = cfg.get('subset', [])
    count = cfg.get('count', None)
    parity = cfg.get('parity', None)
    group = cfg.get('group', None)
    cond_type = cfg.get('cond_type', None)
    cons_index = cfg.get('cons_index', None)
    cons_polarity = cfg.get('cons_polarity', True)

    def K(i): return knights[inhabitants[i]]

    if tpl == 'OR':
        expr = Or(K(args[0]), K(args[1]))
    elif tpl == 'AND':
        expr = And(K(args[0]), K(args[1]))
    elif tpl == 'XOR':
        expr = Xor(K(args[0]), K(args[1]))
    elif tpl == 'IFF_KNAVE':
        expr = (K(args[0]) == Not(K(args[1])))
    elif tpl == 'IFF_KNIGHT':
        expr = (K(args[0]) == K(args[1]))
    elif tpl == 'IMPLIES_KNAVE_THEN_KNIGHT':
        expr = Implies(Not(K(args[0])), K(args[1]))
    elif tpl == 'ASSERT_KNIGHT':
        expr = K(args[0])
    elif tpl == 'ASSERT_KNAVE':
        expr = Not(K(args[0]))
    elif tpl in ('COUNT_EQ','COUNT_GE','COUNT_LE'):
        s = _subset_sum_knights(knights, inhabitants, subset)
        c = IntVal(count if count is not None else 0)
        if tpl == 'COUNT_EQ':
            expr = (s == c)
        elif tpl == 'COUNT_GE':
            expr = (s >= c)
        else:
            expr = (s <= c)
    elif tpl == 'PARITY_SUBSET':
        s = _subset_sum_knights(knights, inhabitants, subset)
        expr = ((s % 2) == IntVal(0 if parity == 'even' else 1))  # use % operator instead of Mod
    elif tpl in ('GROUP_MAJORITY','GROUP_MINORITY'):
        idxs = _group_members_indices(group_assignment, group)
        s = _subset_sum_knights(knights, inhabitants, idxs)
        m = IntVal(len(idxs))
        if tpl == 'GROUP_MAJORITY':
            expr = (s > (m - s))
        else:
            expr = (s < (m - s))
    elif tpl == 'COND_COUNT_IMPLIES':
        s = _subset_sum_knights(knights, inhabitants, subset)
        c = IntVal(count if count is not None else 0)
        cond = (s == c) if cond_type == 'EQ' else (s >= c) if cond_type == 'GE' else (s <= c)
        cons = K(cons_index) if cons_polarity else Not(K(cons_index))
        expr = Implies(cond, cons)
    else:
        expr = BoolVal(True)

    return Not(expr) if cfg.get('neg', False) else expr

# -------------------------
# Meta rules synthesis and Z3 builders
# -------------------------
def build_meta_rules(names: List[str], assignment: List[bool], group_assignment: List[int],
                     group_num: int, group_names: List[str]) -> List[Dict[str, Any]]:
    """
    Randomize global meta rules consistent with the ground truth and groups.
    """
    n = len(names)
    k_count = sum(1 for x in assignment if x)
    t_count = k_count  # In our construction, true statements count equals knight count

    rule_pool = [
        'EXACT_KNIGHTS','AT_LEAST_KNIGHTS','AT_MOST_KNIGHTS',
        'EXACT_TRUTHS','AT_LEAST_TRUTHS','AT_MOST_TRUTHS',
        'PARITY_KNIGHTS','RELATE_TRUTH_KNIGHT',
        'GROUP_BALANCE','GROUP_PARITY','GROUP_COUNT_EQ'
    ]
    m = random.randint(1, 4)  # ensure at least one global fact for depth
    random.shuffle(rule_pool)
    chosen = rule_pool[:m]
    rules: List[Dict[str, Any]] = []

    per_group_counts = []
    for g in range(group_num):
        members = [i for i, gg in enumerate(group_assignment) if gg == g]
        cnt = sum(1 for i in members if assignment[i])
        per_group_counts.append((members, cnt))

    for tpl in chosen:
        if tpl == 'EXACT_KNIGHTS':
            rules.append({'tpl': tpl, 'count': k_count, 'text': f'Exactly {k_count} people are knights'})
        elif tpl == 'AT_LEAST_KNIGHTS':
            c = random.randint(0, k_count)
            rules.append({'tpl': tpl, 'count': c, 'text': f'At least {c} people are knights'})
        elif tpl == 'AT_MOST_KNIGHTS':
            c = random.randint(k_count, n)
            rules.append({'tpl': tpl, 'count': c, 'text': f'At most {c} people are knights'})
        elif tpl == 'EXACT_TRUTHS':
            rules.append({'tpl': tpl, 'count': t_count, 'text': f'Exactly {t_count} of the statements are true'})
        elif tpl == 'AT_LEAST_TRUTHS':
            c = random.randint(0, t_count)
            rules.append({'tpl': tpl, 'count': c, 'text': f'At least {c} of the statements are true'})
        elif tpl == 'AT_MOST_TRUTHS':
            c = random.randint(t_count, n)
            rules.append({'tpl': tpl, 'count': c, 'text': f'At most {c} of the statements are true'})
        elif tpl == 'PARITY_KNIGHTS':
            parity = 'even' if (k_count % 2 == 0) else 'odd'
            rules.append({'tpl': tpl, 'parity': parity, 'text': f'The number of knights is {parity}'})
        elif tpl == 'RELATE_TRUTH_KNIGHT':
            rules.append({'tpl': tpl, 'text': 'The number of knights equals the number of true statements'})
        elif tpl == 'GROUP_BALANCE':
            if group_num >= 2:
                g1, g2 = random.sample(range(group_num), 2)
                cnt1 = per_group_counts[g1][1]
                cnt2 = per_group_counts[g2][1]
                possible_delta = 1 if cnt1 >= cnt2 + 1 else 0
                delta = possible_delta if random.getrandbits(1) == 1 else 0
                rules.append({'tpl': tpl, 'g1': g1, 'g2': g2, 'delta': delta,
                              'text': f'Knights in {group_names[g1]} are at least knights in {group_names[g2]} plus {delta}'})
        elif tpl == 'GROUP_PARITY':
            g = random.randint(0, group_num - 1)
            cnt = per_group_counts[g][1]
            parity = 'even' if (cnt % 2 == 0) else 'odd'
            rules.append({'tpl': tpl, 'group': g, 'parity': parity,
                          'text': f'The number of knights in {group_names[g]} is {parity}'})
        elif tpl == 'GROUP_COUNT_EQ':
            g = random.randint(0, group_num - 1)
            cnt = per_group_counts[g][1]
            rules.append({'tpl': tpl, 'group': g, 'count': cnt,
                          'text': f'Exactly {cnt} people are knights in {group_names[g]}'})

    return rules

def meta_rule_expr(knights: Dict[str, Any], inhabitants: List[str],
                   statement_configs: List[Dict[str, Any]], mr: Dict[str, Any],
                   group_assignment: List[int], group_num: int):
    """Return a Z3 Bool expression for one meta rule mr."""
    tpl = mr['tpl']
    n = len(inhabitants)
    Ksum = Sum([If(knights[name], IntVal(1), IntVal(0)) for name in inhabitants])

    if tpl == 'EXACT_KNIGHTS':
        return (Ksum == IntVal(mr['count']))
    if tpl == 'AT_LEAST_KNIGHTS':
        return (Ksum >= IntVal(mr['count']))
    if tpl == 'AT_MOST_KNIGHTS':
        return (Ksum <= IntVal(mr['count']))
    if tpl == 'PARITY_KNIGHTS':
        return ((Ksum % 2) == IntVal(0 if mr.get('parity') == 'even' else 1))  # use % operator
    if tpl == 'RELATE_TRUTH_KNIGHT':
        Tsum = Sum([If(truth_expr(knights, inhabitants, cfg, group_assignment, group_num), IntVal(1), IntVal(0)) for cfg in statement_configs])
        return (Tsum == Ksum)
    if tpl in ('EXACT_TRUTHS','AT_LEAST_TRUTHS','AT_MOST_TRUTHS'):
        Tsum = Sum([If(truth_expr(knights, inhabitants, cfg, group_assignment, group_num), IntVal(1), IntVal(0)) for cfg in statement_configs])
        if tpl == 'EXACT_TRUTHS':
            return (Tsum == IntVal(mr['count']))
        if tpl == 'AT_LEAST_TRUTHS':
            return (Tsum >= IntVal(mr['count']))
        return (Tsum <= IntVal(mr['count']))
    if tpl == 'GROUP_BALANCE':
        g1 = mr['g1']; g2 = mr['g2']; delta = mr.get('delta', 0)
        idxs1 = [i for i, g in enumerate(group_assignment) if g == g1]
        idxs2 = [i for i, g in enumerate(group_assignment) if g == g2]
        s1 = Sum([If(knights[inhabitants[i]], IntVal(1), IntVal(0)) for i in idxs1])
        s2 = Sum([If(knights[inhabitants[i]], IntVal(1), IntVal(0)) for i in idxs2])
        return (s1 >= s2 + IntVal(delta))
    if tpl == 'GROUP_PARITY':
        g = mr['group']
        idxs = [i for i, gg in enumerate(group_assignment) if gg == g]
        s = Sum([If(knights[inhabitants[i]], IntVal(1), IntVal(0)) for i in idxs])
        return ((s % 2) == IntVal(0 if mr.get('parity') == 'even' else 1))  # use % operator
    if tpl == 'GROUP_COUNT_EQ':
        g = mr['group']
        idxs = [i for i, gg in enumerate(group_assignment) if gg == g]
        s = Sum([If(knights[inhabitants[i]], IntVal(1), IntVal(0)) for i in idxs])
        return (s == IntVal(mr['count']))

    return BoolVal(True)

# -------------------------
# Auxiliary: reference instance generator
# -------------------------
def build_knights_instance(inhabitants: List[str]) -> Tuple[List[str], List[str]]:
    """
    Reference instance generator for external tools that may import this symbol.
    Randomizes a ground truth assignment and returns sorted [knaves], [knights].
    """
    n = len(inhabitants)
    assignment = [bool(random.getrandbits(1)) for _ in range(n)]
    knaves = sorted([inhabitants[i] for i in range(n) if not assignment[i]])
    knights = sorted([inhabitants[i] for i in range(n) if assignment[i]])
    return (knaves, knights)