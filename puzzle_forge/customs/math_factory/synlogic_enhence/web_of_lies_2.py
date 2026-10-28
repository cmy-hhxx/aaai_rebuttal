# web_of_lies_7.py
import random
from z3 import And, Or, Not, If, Sum, Implies

# 模块级缓存：用于在 format_answer 仅接收 groups 时回溯站名
_LAST_STATIONS = None

def _letters(n):
    base = [chr(ord('A') + i) for i in range(26)]
    if n <= len(base):
        return base[:n]
    out = []
    k = 0
    while len(out) < n:
        prefix = base[k % 26]
        idx = k // 26
        out.append(prefix if idx == 0 else f'{prefix}{idx}')
        k += 1
    return out[:n]

def _station_pool(s_num):
    pool = ['中央', '东站', '西站', '北站', '南站', '花园', '海湾', '河畔', '山岭', '金融城', '科创谷', '体育馆']
    return random.sample(pool, s_num)

def _balanced_assignment(people, s_num, team_size):
    ps = people[:]
    random.shuffle(ps)
    assign = {}
    for s in range(s_num):
        for j in range(team_size):
            assign[ps[s * team_size + j]] = s
    return assign

def _gen_roles(s_num, team_size):
    roles = []
    for _ in range(s_num):
        t = random.choices(
            population=['same', 'xor', 'exact_k', 'at_least_one', 'parity_even', 'parity_odd'],
            weights=[0.22, 0.22, 0.18, 0.14, 0.12, 0.12],
            k=1
        )[0]
        lr = random.choices(
            population=['free', 'leader_truth', 'leader_lie', 'leader_unique_truth_if_xor'],
            weights=[0.35, 0.25, 0.2, 0.2],
            k=1
        )[0]
        role = {'type': t, 'leader_rule': lr}
        if t == 'exact_k':
            if lr == 'leader_lie':
                role['k'] = random.randrange(0, max(1, team_size))
            elif lr == 'leader_truth':
                role['k'] = random.randrange(1, team_size + 1)
            else:
                role['k'] = random.randrange(0, team_size + 1)
        roles.append(role)
    return roles

def role_text(role):
    typ = role.get('type', 'same')
    if typ == 'same':
        return '该站所有人真值相同（要么都真要么都假）'
    if typ == 'xor':
        return '该站恰有一人说真话'
    if typ == 'exact_k':
        return f'该站恰有{role.get("k", 1)}人说真话'
    if typ == 'at_least_one':
        return '该站至少有一人说真话'
    if typ == 'parity_even':
        return '该站说真话的人数为偶数'
    if typ == 'parity_odd':
        return '该站说真话的人数为奇数'
    return '该站真话模式未定义'

def leader_rule_text(role):
    lr = role.get('leader_rule', 'free')
    if lr == 'free':
        return '站长无额外限制'
    if lr == 'leader_truth':
        return '站长必须说真话'
    if lr == 'leader_lie':
        return '站长必须说谎'
    if lr == 'leader_unique_truth_if_xor':
        return '若该站为“恰一真”，则唯一说真话者必须是站长'
    return '站长规则未定义'

def _truth_assignment_general(people, assign, roles, s_num, team_size):
    by_s = {s: [] for s in range(s_num)}
    for p in people:
        by_s[assign[p]].append(p)
    truth = {}
    for s in range(s_num):
        role = roles[s]
        lr = role.get('leader_rule', 'free')
        typ = role['type']
        ps = by_s[s]

        if typ == 'same':
            if lr == 'leader_truth':
                val = True
            elif lr == 'leader_lie':
                val = False
            else:
                val = random.choice([True, False])
            for p in ps:
                truth[p] = val

        elif typ == 'xor':
            idx = random.randrange(team_size)
            for j, p in enumerate(ps):
                truth[p] = (j == idx)

        elif typ == 'exact_k':
            k = max(0, min(team_size, role.get('k', 1)))
            idxs = list(range(team_size))
            random.shuffle(idxs)
            true_set = set(idxs[:k])
            for j, p in enumerate(ps):
                truth[p] = (j in true_set)

        elif typ == 'at_least_one':
            if lr == 'leader_lie':
                k = random.randrange(1, team_size)
            else:
                k = random.randrange(1, team_size + 1)
            idxs = list(range(team_size))
            random.shuffle(idxs)
            true_set = set(idxs[:k])
            for j, p in enumerate(ps):
                truth[p] = (j in true_set)

        elif typ == 'parity_even':
            if team_size == 2:
                k = 2 if lr == 'leader_truth' else random.choice([0, 2])
            else:
                k = 2 if lr == 'leader_truth' else random.choice([0, 2])
            idxs = list(range(team_size))
            random.shuffle(idxs)
            true_set = set(idxs[:min(k, team_size)])
            for j, p in enumerate(ps):
                truth[p] = (j in true_set)

        elif typ == 'parity_odd':
            if team_size == 2:
                k = 1
            else:
                if lr == 'leader_lie':
                    k = 1
                else:
                    k = random.choice([1, 3])
            idxs = list(range(team_size))
            random.shuffle(idxs)
            true_set = set(idxs[:min(k, team_size)])
            for j, p in enumerate(ps):
                truth[p] = (j in true_set)

        else:
            for p in ps:
                truth[p] = False
    return truth

def _station_truth_count(people, assign, s_num, truth):
    counts = [0] * s_num
    for p in people:
        if truth[p]:
            counts[assign[p]] += 1
    return counts

def _choose_leaders(people, assign, roles, s_num, team_size, truth):
    by_s = {s: [] for s in range(s_num)}
    for p in people:
        by_s[assign[p]].append(p)
    leaders = {}
    for s in range(s_num):
        lr = roles[s].get('leader_rule', 'free')
        typ = roles[s].get('type', 'same')
        ps = by_s[s]

        def eligible_person(pname):
            if lr == 'leader_truth':
                return truth[pname]
            elif lr == 'leader_lie':
                return not truth[pname]
            elif lr == 'leader_unique_truth_if_xor' and typ == 'xor':
                return truth[pname]
            else:
                return True

        cand = [p for p in ps if eligible_person(p)]
        if cand:
            leaders[s] = cand[0]
        else:
            fallback = ps[0]
            if lr == 'leader_truth':
                truth[fallback] = True
            elif lr == 'leader_lie':
                truth[fallback] = False
            elif lr == 'leader_unique_truth_if_xor':
                truth[fallback] = True
            leaders[s] = fallback
    return leaders

def _build_clause_text(ct, a0, a1, speaker, people, stations, team_size):
    if ct == 0:
        return f'我在{stations[a0]}站'
    if ct == 10:
        return f'我不在{stations[a0]}站'
    if ct == 1:
        return f'{people[a0]}在{stations[a1]}站'
    if ct == 11:
        return f'{people[a0]}不在{stations[a1]}站'
    if ct == 2:
        return f'{stations[a0]}站的所有人都在说谎'
    if ct == 3:
        return f'{stations[a0]}站至少有一人说真话'
    if ct == 4:
        return '与我同站的人中至少有一人说真话'
    if ct == 5:
        return '与我同站的其他人都在说谎'
    if ct == 6:
        return f'{people[a0]}在说真话'
    if ct == 7:
        return f'{people[a0]}在说谎'
    if ct == 8:
        return f'{people[a0]}和我在同一站'
    if ct == 9:
        return f'{people[a0]}和我不在同一站'
    if ct == 12:
        return f'{stations[a0]}站恰有{a1}人说真话'
    if ct == 13:
        return f'我所在站的站长是{people[a0]}'
    if ct == 14:
        return f'{people[a0]}是站长'
    if ct == 15:
        return '与我同站的站长在说真话'
    if ct == 16:
        return f'我们站说真话的人数为{"偶数" if a1 == 0 else "奇数"}'
    if ct == 17:
        return f'{stations[a0]}站的站长在说真话'
    return '……'

def _eval_clause_truth_gen(ct, a0, a1, speaker_idx, people, stations, assign, truth, leaders, s_num, team_size):
    me = people[speaker_idx]
    if ct == 0:
        return assign[me] == a0
    if ct == 10:
        return assign[me] != a0
    if ct == 1:
        return assign[people[a0]] == a1
    if ct == 11:
        return assign[people[a0]] != a1
    if ct == 2:
        s = a0
        ps = [p for p in people if assign[p] == s]
        return all(not truth[p] for p in ps)
    if ct == 3:
        s = a0
        ps = [p for p in people if assign[p] == s]
        return any(truth[p] for p in ps)
    if ct == 4:
        s = assign[me]
        others = [p for p in people if assign[p] == s and p != me]
        return any(truth[p] for p in others)
    if ct == 5:
        s = assign[me]
        others = [p for p in people if assign[p] == s and p != me]
        return all(not truth[p] for p in others)
    if ct == 6:
        return truth[people[a0]]
    if ct == 7:
        return not truth[people[a0]]
    if ct == 8:
        return assign[people[a0]] == assign[me]
    if ct == 9:
        return assign[people[a0]] != assign[me]
    if ct == 12:
        s = a0
        ps = [p for p in people if assign[p] == s]
        k = sum(1 for p in ps if truth[p])
        return k == a1
    if ct == 13:
        return assign[people[a0]] == assign[me] and leaders[assign[me]] == people[a0]
    if ct == 14:
        return any(leaders[s] == people[a0] for s in range(s_num))
    if ct == 15:
        s = assign[me]
        return truth[leaders[s]]
    if ct == 16:
        s = assign[me]
        ps = [p for p in people if assign[p] == s]
        k = sum(1 for p in ps if truth[p])
        return (k % 2) == a1
    if ct == 17:
        s = a0
        return truth[leaders[s]]
    return False

def gen_instance():
    global _LAST_STATIONS
    s_num = random.choice([3, 4, 5])
    team_size = random.choice([2, 3])
    p_num = s_num * team_size
    people = _letters(p_num)
    stations = _station_pool(s_num)
    roles = _gen_roles(s_num, team_size)
    assign = _balanced_assignment(people, s_num, team_size)
    # 真值分配
    truth = _truth_assignment_general(people, assign, roles, s_num, team_size)
    # 选择满足站长规则且字母序最靠前的站长
    leaders = _choose_leaders(people, assign, roles, s_num, team_size, truth)
    st_counts = _station_truth_count(people, assign, s_num, truth)
    leader_truth_total = sum(1 for s in range(s_num) if truth[leaders[s]])

    # 公开站长姓名：随机公开0或1个站的站长
    reveal_k = random.randrange(0, min(2, s_num))
    reveal_indices = sorted(random.sample(range(s_num), reveal_k))
    known_leader_indices = reveal_indices
    known_leader_names = [leaders[i] for i in reveal_indices]

    ctype, cA, cB, clause_texts = [], [], [], []

    def _candidate_true_clauses(i, people, stations, assign, truth, leaders, st_counts, s_num, team_size):
        me = people[i]
        res = []
        # 自定位（允许但降低整体比例，在选择阶段控制）
        res.append((0, assign[me], -1))
        for j in range(len(people)):
            res.append((1, j, assign[people[j]]))
            if assign[people[j]] != assign[me]:
                res.append((9, j, -1))
            else:
                res.append((8, j, -1))
        for s in range(s_num):
            if st_counts[s] == 0:
                res.append((2, s, -1))
            if st_counts[s] >= 1:
                res.append((3, s, -1))
            res.append((12, s, st_counts[s]))
        others = [p for p in people if assign[p] == assign[me] and p != me]
        if any(truth[p] for p in others):
            res.append((4, -1, -1))
        if all(not truth[p] for p in others):
            res.append((5, -1, -1))
        for j in range(len(people)):
            if truth[people[j]] and j != i:  # 剔除自证
                res.append((6, j, -1))
            elif (not truth[people[j]]) and j != i:  # 剔除自证
                res.append((7, j, -1))
        res.append((13, people.index(leaders[assign[me]]), -1))
        for s in range(s_num):
            if truth[leaders[s]]:
                res.append((17, s, -1))
        for j in range(len(people)):
            if any(leaders[s] == people[j] for s in range(s_num)):
                res.append((14, j, -1))
        k = st_counts[assign[me]]
        res.append((16, -1, k % 2))
        return list(set(res))

    def _candidate_false_clauses(i, people, stations, assign, truth, leaders, st_counts, s_num, team_size):
        me = people[i]
        res = []
        for s in range(s_num):
            if s != assign[me]:
                res.append((0, s, -1))
        res.append((10, assign[me], -1))
        for j in range(len(people)):
            for s in range(s_num):
                if s != assign[people[j]]:
                    res.append((1, j, s))
            if assign[people[j]] != assign[me]:
                res.append((8, j, -1))
            else:
                res.append((9, j, -1))
        for s in range(s_num):
            if st_counts[s] > 0:
                res.append((2, s, -1))
            if st_counts[s] == 0:
                res.append((3, s, -1))
            for k in range(team_size + 1):
                if k != st_counts[s]:
                    res.append((12, s, k))
        others = [p for p in people if assign[p] == assign[me] and p != me]
        if not any(truth[p] for p in others):
            res.append((4, -1, -1))
        if not all(not truth[p] for p in others):
            res.append((5, -1, -1))
        for j in range(len(people)):
            if j != i:  # 剔除自证
                if not truth[people[j]]:
                    res.append((6, j, -1))
                else:
                    res.append((7, j, -1))
        for j in range(len(people)):
            if not (assign[people[j]] == assign[me] and leaders[assign[me]] == people[j]):
                res.append((13, j, -1))
        for j in range(len(people)):
            if not any(leaders[s] == people[j] for s in range(s_num)):
                res.append((14, j, -1))
        if not truth[leaders[assign[me]]]:
            res.append((15, -1, -1))
        k = st_counts[assign[me]]
        res.append((16, -1, 1 - (k % 2)))
        for s in range(s_num):
            if not truth[leaders[s]]:
                res.append((17, s, -1))
        return list(set(res))

    def _is_self_truth_clause(i, ct, a0):
        return (ct in (6, 7)) and (a0 == i)

    def _choose_two_distinct(i, trues, falses, wants_true):
        # 降低直接自定位（ct=0/10）权重
        def weight_clause(tpl):
            ct = tpl[0]
            if ct in (0, 10):
                return 0.3
            if ct in (6, 7):
                return 0.5
            return 1.0

        def pick_two(pool):
            pool2 = pool[:]
            random.shuffle(pool2)
            pool2.sort(key=weight_clause, reverse=True)
            out = []
            for tpl in pool2:
                if len(out) == 0:
                    out.append(tpl)
                elif tpl != out[0]:
                    out.append(tpl)
                    break
            return out

        if wants_true:
            chosen = pick_two(trues)
            if len(chosen) < 2:
                # 构造一个安全真备选：优先同站/计数类/站长真话类
                safe_true = [tpl for tpl in trues if tpl not in chosen and tpl[0] in (8, 3, 12, 15, 16, 17, 14)]
                if safe_true:
                    chosen.append(random.choice(safe_true))
                else:
                    # 兜底：用“他人位置真句”（避免自定位）
                    others_pos_true = [tpl for tpl in trues if tpl not in chosen and tpl[0] == 1]
                    if others_pos_true:
                        chosen.append(random.choice(others_pos_true))
                    else:
                        # 极端兜底：直接自定位真句（不重复）
                        fallback = [tpl for tpl in trues if tpl not in chosen]
                        if fallback:
                            chosen.append(random.choice(fallback))
            return chosen[:2]
        else:
            # wants_false: 第一条选假，第二条选真或另外一条假，保证不重复
            first = pick_two(falses)
            base = first[:1]
            if len(base) == 0:
                # 极端场景：无假候选（很少见），则强制从真中选一条，另一条使用“与我同站的其他人都在说谎”作假
                if trues:
                    base = [trues[0]]
                else:
                    base = []
            # 第二条
            cand2 = [tpl for tpl in (trues + falses) if tpl not in base]
            if cand2:
                # 优先真句作为第二条，保持 And(False, True) == False
                true_pool = [tpl for tpl in trues if tpl in cand2]
                if true_pool:
                    base.append(random.choice(true_pool))
                else:
                    base.append(random.choice(cand2))
            # 保证两条
            if len(base) == 1:
                # 兜底：从假中再选一条不同
                cand2 = [tpl for tpl in falses if tpl != base[0]]
                if cand2:
                    base.append(random.choice(cand2))
                elif trues:
                    base.append(random.choice(trues))
            return base[:2]

    for i in range(len(people)):
        wants_true = truth[people[i]]
        trues = _candidate_true_clauses(i, people, stations, assign, truth, leaders, st_counts, s_num, team_size)
        falses = _candidate_false_clauses(i, people, stations, assign, truth, leaders, st_counts, s_num, team_size)

        # 剔除自证类（ct=6/7且a0为本人）
        trues = [tpl for tpl in trues if not _is_self_truth_clause(i, tpl[0], tpl[1])]
        falses = [tpl for tpl in falses if not _is_self_truth_clause(i, tpl[0], tpl[1])]

        chosen = _choose_two_distinct(i, trues, falses, wants_true)

        ct_list, a0_list, a1_list, txts = [], [], [], []
        for (ct, a0, a1) in chosen:
            ct_list.append(ct)
            a0_list.append(a0 if a0 is not None else -1)
            a1_list.append(a1 if a1 is not None else -1)
            txts.append(_build_clause_text(ct, a0, a1, i, people, stations, team_size))
        ctype.append(ct_list)
        cA.append(a0_list)
        cB.append(a1_list)
        clause_texts.append(txts)

    _LAST_STATIONS = stations[:]
    return {
        'people': people,
        'stations': stations,
        'roles': roles,
        'team_size': team_size,
        'ctype': ctype,
        'cA': cA,
        'cB': cB,
        'clause_texts': clause_texts,
        's_num': s_num,
        'p_num': p_num,
        'st_counts': st_counts,
        'leader_truth_total': leader_truth_total,
        'known_leader_indices': known_leader_indices,
        'known_leader_names': known_leader_names
    }

def clause_eval(ct, a0, a1, speaker_idx, people, stations, loc, truth_s, lead, team_size):
    me = people[speaker_idx]

    def at_station(person_name, s_idx):
        return loc[(person_name, stations[s_idx])]

    def truth_count_at(s_idx):
        return Sum([If(And(at_station(p, s_idx), truth_s[p]), 1, 0) for p in people])

    def others_truth_count_at_my_station():
        return Sum([
            If(
                at_station(me, si),
                Sum([If(And(pn != me, at_station(pn, si), truth_s[pn]), 1, 0) for pn in people]),
                0
            ) for si in range(len(stations))
        ])

    def others_lie_count_at_my_station():
        return Sum([
            If(
                at_station(me, si),
                Sum([If(And(pn != me, at_station(pn, si), Not(truth_s[pn])), 1, 0) for pn in people]),
                0
            ) for si in range(len(stations))
        ])

    def leader_truth_count_at(s_idx):
        return Sum([If(And(at_station(p, s_idx), lead[p], truth_s[p]), 1, 0) for p in people])

    if ct == 0:
        return at_station(me, a0)
    if ct == 10:
        return Not(at_station(me, a0))
    if ct == 1:
        return at_station(people[a0], a1)
    if ct == 11:
        return Not(at_station(people[a0], a1))
    if ct == 2:
        return truth_count_at(a0) == 0
    if ct == 3:
        return truth_count_at(a0) >= 1
    if ct == 4:
        return others_truth_count_at_my_station() >= 1
    if ct == 5:
        return others_lie_count_at_my_station() == (team_size - 1)
    if ct == 6:
        return truth_s[people[a0]]
    if ct == 7:
        return Not(truth_s[people[a0]])
    if ct == 8:
        return Sum([
            If(And(at_station(me, si), at_station(people[a0], si)), 1, 0)
            for si in range(len(stations))
        ]) >= 1
    if ct == 9:
        return Sum([
            If(And(at_station(me, si), at_station(people[a0], si)), 1, 0)
            for si in range(len(stations))
        ]) == 0
    if ct == 12:
        return truth_count_at(a0) == a1
    if ct == 13:
        return Sum([
            If(And(at_station(me, si), at_station(people[a0], si), lead[people[a0]]), 1, 0)
            for si in range(len(stations))
        ]) >= 1
    if ct == 14:
        return lead[people[a0]]
    if ct == 15:
        return Sum([
            If(at_station(me, si), leader_truth_count_at(si), 0)
            for si in range(len(stations))
        ]) == 1
    if ct == 16:
        cnt_me = Sum([
            If(at_station(me, si), truth_count_at(si), 0)
            for si in range(len(stations))
        ])
        if team_size == 2:
            return Or(cnt_me == 0, cnt_me == 2) if a1 == 0 else (cnt_me == 1)
        else:
            return Or(cnt_me == 0, cnt_me == 2) if a1 == 0 else Or(cnt_me == 1, cnt_me == 3)
    if ct == 17:
        return leader_truth_count_at(a0) == 1
    return Not(And(True, False))

def station_role_constraint(roles, stations, people, loc, truth_s, team_size):
    cons = []
    for i, role in enumerate(roles):
        cnt = Sum([If(And(loc[(p, stations[i])], truth_s[p]), 1, 0) for p in people])
        typ = role.get('type', 'same')
        if typ == 'same':
            cons.append(Or(cnt == 0, cnt == team_size))
        elif typ == 'xor':
            cons.append(cnt == 1)
        elif typ == 'exact_k':
            k = role.get('k', 1)
            cons.append(cnt == k)
        elif typ == 'at_least_one':
            cons.append(cnt >= 1)
        elif typ == 'parity_even':
            if team_size == 2:
                cons.append(Or(cnt == 0, cnt == 2))
            else:
                cons.append(Or(cnt == 0, cnt == 2))
        elif typ == 'parity_odd':
            if team_size == 2:
                cons.append(cnt == 1)
            else:
                cons.append(Or(cnt == 1, cnt == 3))
        else:
            cons.append(cnt >= 0)
    return And(cons)

def leader_role_constraint(roles, stations, people, loc, truth_s, lead, team_size):
    cons = []
    for i, role in enumerate(roles):
        lr = role.get('leader_rule', 'free')
        leader_truth = Sum([If(And(loc[(p, stations[i])], lead[p], truth_s[p]), 1, 0) for p in people])
        leader_lie = Sum([If(And(loc[(p, stations[i])], lead[p], Not(truth_s[p])), 1, 0) for p in people])
        if lr == 'free':
            cons.append(Or(leader_truth == 0, leader_truth == 1))
        elif lr == 'leader_truth':
            cons.append(leader_truth == 1)
        elif lr == 'leader_lie':
            cons.append(leader_lie == 1)
        elif lr == 'leader_unique_truth_if_xor':
            typ = role.get('type')
            if typ == 'xor':
                cons.append(leader_truth == 1)
            else:
                cons.append(Or(leader_truth == 0, leader_truth == 1))
        else:
            cons.append(Or(leader_truth == 0, leader_truth == 1))
    return And(cons)

def leader_tiebreak_constraint(roles, stations, people, loc, truth_s, lead, team_size):
    cons = []
    for i, role in enumerate(roles):
        lr = role.get('leader_rule', 'free')
        typ = role.get('type', 'same')
        for j, p in enumerate(people):
            in_station_p = loc[(p, stations[i])]
            if lr == 'leader_truth':
                eligible_p = And(in_station_p, truth_s[p])
            elif lr == 'leader_lie':
                eligible_p = And(in_station_p, Not(truth_s[p]))
            elif lr == 'leader_unique_truth_if_xor' and typ == 'xor':
                eligible_p = And(in_station_p, truth_s[p])
            else:
                eligible_p = in_station_p

            earlier_block = []
            for q in people[:j]:
                in_station_q = loc[(q, stations[i])]
                if lr == 'leader_truth':
                    eligible_q = And(in_station_q, truth_s[q])
                elif lr == 'leader_lie':
                    eligible_q = And(in_station_q, Not(truth_s[q]))
                elif lr == 'leader_unique_truth_if_xor' and typ == 'xor':
                    eligible_q = And(in_station_q, truth_s[q])
                else:
                    eligible_q = in_station_q
                earlier_block.append(Not(eligible_q))

            if earlier_block:
                cons.append(Implies(And(lead[p], in_station_p), And([eligible_p] + earlier_block)))
            else:
                cons.append(Implies(And(lead[p], in_station_p), eligible_p))

            earliest_cond = And([eligible_p] + earlier_block) if earlier_block else eligible_p
            cons.append(Implies(earliest_cond, And(lead[p], in_station_p)))
    return And(cons)

def format_answer(*args):
    """
    将解的分组渲染为规范字符串：
    - 站点顺序：按题面列出的 stations 顺序；
    - 站内顺序：按姓名字母序（A 最前，其次 B，依此类推）。
    """
    global _LAST_STATIONS
    if len(args) == 2:
        stations, groups = args
    elif len(args) == 1:
        groups = args[0]
        stations = _LAST_STATIONS if _LAST_STATIONS is not None else [f'站{i+1}' for i in range(len(groups))]
    else:
        raise TypeError('format_answer expected 1 or 2 positional arguments')

    def fmt_item(pair):
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            name, truth = pair
            return f'{name}({"T" if truth else "F"})'
        return str(pair)

    def sort_key(pair):
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            return str(pair[0])
        return str(pair)

    parts = []
    for i, lst in enumerate(groups):
        sorted_lst = sorted((lst if isinstance(lst, (list, tuple)) else []), key=sort_key)
        items = [fmt_item(it) for it in sorted_lst]
        parts.append(f'{stations[i]}: {", ".join(items)}')
    return ' | '.join(parts)

def public_counts_text(stations, st_counts, leader_truth_total):
    parts = [f'{stations[i]}: {st_counts[i]}人真话' for i in range(len(stations))]
    return f'公开提示：各站说真话人数依次为 ' + '；'.join(parts) + f'；另外，说真话的站长共有 {leader_truth_total} 名'

def build_leader_announce_text(stations, known_leader_indices, known_leader_names):
    if not known_leader_indices:
        return '公开提示：未公开任何站长姓名'
    parts = []
    for i in range(len(known_leader_indices)):
        parts.append(f'{stations[known_leader_indices[i]]}的站长是{known_leader_names[i]}')
    return '公开提示：以下站点的站长已知——' + '；'.join(parts)