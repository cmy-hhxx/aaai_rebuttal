# blood_donation_puzzle_15.py
# 生成器与辅助函数（优化版：降低显见线索比例 + 强制非等式线索 + 唯一性保持）
import random
from typing import List, Dict, Any, Tuple
try:
    from z3 import Solver, Int, Distinct, And, Or, Not, Abs, Implies, sat
except Exception as e:
    raise

def choose_k(seq: List[Any], k: int) -> List[Any]:
    if k > len(seq):
        raise ValueError('k cannot be larger than len(seq)')
    return random.sample(list(seq), k)

def _build_z3_model(n: int):
    pv = [Int(f'pv_{i}') for i in range(n)]  # volunteer -> pos
    pd = [Int(f'pd_{i}') for i in range(n)]  # drink -> pos
    pc = [Int(f'pc_{i}') for i in range(n)]  # color -> pos
    s = Solver()
    try:
        s.set('timeout', 12000)
    except Exception:
        pass
    for arr in [pv, pd, pc]:
        for v in arr:
            s.add(And(v >= 0, v < n))
        s.add(Distinct(arr))
    return s, pv, pd, pc

def _add_clue_to_solver(s: Solver, pv: List[Any], pd: List[Any], pc: List[Any], n: int,
                        clue: Tuple[str, Tuple[int, ...]]):
    ctype, payload = clue[0], clue[1]
    if ctype == 'eq_mv':
        m, v = payload
        s.add(pv[v] == m)
    elif ctype == 'eq_md':
        m, d = payload
        s.add(pd[d] == m)
    elif ctype == 'eq_mc':
        m, c = payload
        s.add(pc[c] == m)
    elif ctype == 'neq_mv':
        m, v = payload
        s.add(pv[v] != m)
    elif ctype == 'neq_md':
        m, d = payload
        s.add(pd[d] != m)
    elif ctype == 'neq_mc':
        m, c = payload
        s.add(pc[c] != m)
    elif ctype == 'adj_dc':
        d, c = payload
        s.add(Abs(pd[d] - pc[c]) == 1)
    elif ctype == 'nadj_dc':
        d, c = payload
        s.add(Abs(pd[d] - pc[c]) != 1)
    elif ctype == 'lof_cc':
        a, b = payload
        s.add(pc[a] < pc[b])
    elif ctype == 'lof_dd':
        a, b = payload
        s.add(pd[a] < pd[b])
    elif ctype == 'lof_cd':
        a, b = payload
        s.add(pc[a] < pd[b])
    elif ctype == 'two_dd':
        a, b = payload
        s.add(pd[a] + 2 == pd[b])
    elif ctype == 'end_nc':
        (c,) = payload
        s.add(pc[c] != 0, pc[c] != n - 1)
    elif ctype == 'end_nd':
        (d,) = payload
        s.add(pd[d] != 0, pd[d] != n - 1)
    elif ctype == 'end_nv':
        (v,) = payload
        s.add(pv[v] != 0, pv[v] != n - 1)
    elif ctype == 'bet_cdc':
        cA, dX, cB = payload
        s.add(And(pc[cA] < pd[dX], pd[dX] < pc[cB]))
    elif ctype == 'dist_vd1':
        v, d = payload
        s.add(Abs(pv[v] - pd[d]) == 1)
    elif ctype == 'dist_vd2':
        v, d = payload
        s.add(Abs(pv[v] - pd[d]) == 2)
    elif ctype == 'iff_adj_dc_vv':
        d, c, v1, v2 = payload
        s.add(And(
            Implies(Abs(pd[d] - pc[c]) == 1, pv[v1] < pv[v2]),
            Implies(Abs(pd[d] - pc[c]) != 1, Not(pv[v1] < pv[v2]))
        ))
    elif ctype == 'chain_cc3':
        c1, c2, c3 = payload
        s.add(And(pc[c1] < pc[c2], pc[c2] < pc[c3]))
    elif ctype == 'chain_dd3':
        d1, d2, d3 = payload
        s.add(And(pd[d1] < pd[d2], pd[d2] < pd[d3]))
    else:
        pass

def _count_solutions_at_most_two_inplace(s: Solver, pv: List[Any], pd: List[Any], pc: List[Any]) -> int:
    s.push()
    try:
        if s.check() != sat:
            return 0
        m = s.model()
        block = Or([v != m[v] for arr in [pv, pd, pc] for v in arr])
        s.add(block)
        return 2 if s.check() == sat else 1
    finally:
        s.pop()

def _perm_inverse(perm: List[int]) -> List[int]:
    inv = [0] * len(perm)
    for pos, ent in enumerate(perm):
        inv[ent] = pos
    return inv

def _unique_solution_with_clues(n: int, clues: List[Tuple[str, Tuple[int, ...]]]) -> bool:
    s, pv, pd, pc = _build_z3_model(n)
    for ctype, payload in clues:
        _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
    cnt = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
    return cnt == 1

def _reduce_clues(n: int, chosen: List[Tuple[str, Tuple[int, ...], str]], min_clues: int, max_clues: int) -> List[Tuple[str, Tuple[int, ...], str]]:
    if len(chosen) <= max_clues:
        return chosen
    if not _unique_solution_with_clues(n, [(ct, pl) for ct, pl, _ in chosen]):
        return chosen
    order = list(range(len(chosen)))
    random.shuffle(order)
    kept = chosen[:]
    for idx in order:
        if len(kept) <= max_clues:
            break
        trial = [item for j, item in enumerate(kept) if j != idx]
        if len(trial) >= min_clues and _unique_solution_with_clues(n, [(ct, pl) for ct, pl, _ in trial]):
            kept = trial
    return kept

def _weights() -> Dict[str, int]:
    # 下调等式类别，提升多步推理类别权重
    return {
        'eq_mv': 80, 'eq_md': 80, 'eq_mc': 80,
        'chain_cc3': 98, 'chain_dd3': 98,
        'adj_dc': 95, 'nadj_dc': 74,
        'two_dd': 90,
        'lof_cc': 88, 'lof_dd': 88, 'lof_cd': 85,
        'bet_cdc': 85,
        'dist_vd2': 92, 'dist_vd1': 90,
        'end_nv': 70, 'end_nd': 70, 'end_nc': 70,
        'neq_mv': 20, 'neq_md': 20, 'neq_mc': 20,
        'iff_adj_dc_vv': 86
    }

def _cap_list(lst: List[Any], cap: int) -> List[Any]:
    if len(lst) <= cap:
        return lst
    return random.sample(lst, cap)

def gen_marathon_puzzle(volunteers: List[str],
                        drinks: List[str],
                        colors: List[str],
                        miles: List[str],
                        min_clues: int = 9,
                        max_clues: int = 14) -> Dict[str, Any]:
    n = len(miles)
    if not (len(volunteers) == len(drinks) == len(colors) == n and n >= 5):
        raise ValueError('This generator expects n>=5 and lists of equal length.')

    style = {
        'eq_mv': [
            '{mile}位置由{vol}负责',
            '{vol}在{mile}负责补给'
        ],
        'eq_md': [
            '{mile}位置发放{drink}',
            '{drink}被安排在{mile}'
        ],
        'eq_mc': [
            '{mile}位置为{color}横幅',
            '{color}横幅出现在{mile}'
        ],
        'neq_mv': [
            '{vol}不在{mile}',
            '{mile}没有{vol}'
        ],
        'neq_md': [
            '{drink}不在{mile}',
            '{mile}没有提供{drink}'
        ],
        'neq_mc': [
            '{color}横幅不在{mile}',
            '{mile}不是{color}横幅'
        ],
        'adj_dc': [
            '{drink}与{color}横幅相邻',
            '{drink}和{color}横幅紧挨着'
        ],
        'nadj_dc': [
            '{drink}与{color}横幅不相邻',
            '{drink}和{color}横幅不相邻'
        ],
        'lof_cc': [
            '{colorA}横幅在{colorB}横幅左侧 可隔人',
            '{colorA}横幅位于{colorB}之前'
        ],
        'lof_dd': [
            '{drinkA}在{drinkB}左侧 可隔人',
            '{drinkA}位于{drinkB}之前'
        ],
        'lof_cd': [
            '{colorA}横幅对应里程早于{drinkB}',
            '{colorA}横幅在{drinkB}之前'
        ],
        'two_dd': [
            '{drinkA}在{drinkB}左侧且恰隔一位',
            '{drinkA}与{drinkB}相隔一位且{drinkA}在左'
        ],
        'end_nv': [
            '{vol}不在端点'
        ],
        'end_nd': [
            '{drink}不在端点'
        ],
        'end_nc': [
            '{color}横幅不在端点'
        ],
        'bet_cdc': [
            '{colorA}横幅在左且{drinkX}夹在{colorA}与{colorB}之间',
            '{drinkX}位于{colorA}与{colorB}之间 且{colorA}在左'
        ],
        'dist_vd1': [
            '{vol}与{drink}相邻',
            '{vol}在{drink}旁边'
        ],
        'dist_vd2': [
            '{vol}与{drink}相隔一位',
            '{vol}与{drink}之间正好隔一人'
        ],
        'iff_adj_dc_vv': [
            '{drink}与{color}横幅相邻当且仅当 {volA}在{volB}左侧',
            '仅当{drink}与{color}横幅相邻时 {volA}在{volB}左侧 否则不在其左侧'
        ],
        'chain_cc3': [
            '从左到右依次出现{c1} {c2} {c3} 可隔人',
            '{c1}在{c2}左侧且{c2}在{c3}左侧'
        ],
        'chain_dd3': [
            '从左到右依次出现{d1} {d2} {d3} 可隔人',
            '{d1}在{d2}左侧且{d2}在{d3}左侧'
        ],
    }

    def sorted_indices_by_pos(pos_map: List[int]) -> List[int]:
        return sorted(range(n), key=lambda idx: pos_map[idx])

    def add_unique(cands: List[Tuple[str, Tuple[int, ...], str]], seen: set, item: Tuple[str, Tuple[int, ...], str]):
        key = (item[0], item[1])
        if key not in seen:
            cands.append(item)
            seen.add(key)

    def extend_unique(cands: List[Tuple[str, Tuple[int, ...], str]], seen: set, items: List[Tuple[str, Tuple[int, ...], str]], cap: int = None):
        to_iter = items if cap is None else _cap_list(items, cap)
        for it in to_iter:
            add_unique(cands, seen, it)

    tries = 0
    max_tries = 180
    while tries < max_tries:
        tries += 1

        extend_limit = max_clues + 2

        # 随机目标解
        vol_assign = list(range(n))
        drink_assign = list(range(n))
        color_assign = list(range(n))
        random.shuffle(vol_assign)
        random.shuffle(drink_assign)
        random.shuffle(color_assign)
        pos_of_vol = _perm_inverse(vol_assign)
        pos_of_drink = _perm_inverse(drink_assign)
        pos_of_color = _perm_inverse(color_assign)

        candidates: List[Tuple[str, Tuple[int, ...], str]] = []
        seen_keys = set()

        # 等式类：强制三类各一条作为锚定
        eq_mv_all = [('eq_mv', (pos_of_vol[v], v), random.choice(style['eq_mv']).format(mile=miles[pos_of_vol[v]], vol=volunteers[v])) for v in range(n)]
        eq_md_all = [('eq_md', (pos_of_drink[d], d), random.choice(style['eq_md']).format(mile=miles[pos_of_drink[d]], drink=drinks[d])) for d in range(n)]
        eq_mc_all = [('eq_mc', (pos_of_color[c], c), random.choice(style['eq_mc']).format(mile=miles[pos_of_color[c]], color=colors[c])) for c in range(n)]

        must_mv = random.choice(eq_mv_all)
        must_md = random.choice(eq_md_all)
        must_mc = random.choice(eq_mc_all)
        # 预加入候选集，后续构建时会强制选入
        add_unique(candidates, seen_keys, must_mv)
        add_unique(candidates, seen_keys, must_md)
        add_unique(candidates, seen_keys, must_mc)

        # 适量再加入等式（严格限流）
        eq_pool = [x for x in (eq_mv_all + eq_md_all + eq_mc_all) if x not in (must_mv, must_md, must_mc)]
        random.shuffle(eq_pool)
        extra_eq_cap = max(1, n // 4)  # 显著降低
        extend_unique(candidates, seen_keys, eq_pool, extra_eq_cap)

        # 不等式类（限流）
        neg_mv_pool, neg_md_pool, neg_mc_pool = [], [], []
        for v in range(n):
            for m in range(n):
                if pos_of_vol[v] != m:
                    t = random.choice(style['neq_mv']).format(mile=miles[m], vol=volunteers[v])
                    neg_mv_pool.append(('neq_mv', (m, v), t))
        for d in range(n):
            for m in range(n):
                if pos_of_drink[d] != m:
                    t = random.choice(style['neq_md']).format(mile=miles[m], drink=drinks[d])
                    neg_md_pool.append(('neq_md', (m, d), t))
        for c in range(n):
            for m in range(n):
                if pos_of_color[c] != m:
                    t = random.choice(style['neq_mc']).format(mile=miles[m], color=colors[c])
                    neg_mc_pool.append(('neq_mc', (m, c), t))
        neg_cap = max(2, n // 2)
        extend_unique(candidates, seen_keys, neg_mv_pool, neg_cap)
        extend_unique(candidates, seen_keys, neg_md_pool, neg_cap)
        extend_unique(candidates, seen_keys, neg_mc_pool, neg_cap)

        # 相邻/不相邻（至少一条）
        adj_pool, nadj_pool = [], []
        for d in range(n):
            for c in range(n):
                if abs(pos_of_drink[d] - pos_of_color[c]) == 1:
                    txt = random.choice(style['adj_dc']).format(drink=drinks[d], color=colors[c])
                    adj_pool.append(('adj_dc', (d, c), txt))
                else:
                    txt = random.choice(style['nadj_dc']).format(drink=drinks[d], color=colors[c])
                    nadj_pool.append(('nadj_dc', (d, c), txt))
        if adj_pool:
            add_unique(candidates, seen_keys, random.choice(adj_pool))
        elif nadj_pool:
            add_unique(candidates, seen_keys, random.choice(nadj_pool))
        extend_unique(candidates, seen_keys, adj_pool, max(1, n // 2))
        extend_unique(candidates, seen_keys, nadj_pool, max(1, n // 2))

        # 左右关系
        lof_cc_pool, lof_dd_pool, lof_cd_pool = [], [], []
        colors_sorted = sorted_indices_by_pos(pos_of_color)
        drinks_sorted = sorted_indices_by_pos(pos_of_drink)
        for i in range(n - 1):
            a, b = colors_sorted[i], colors_sorted[i + 1]
            txt = random.choice(style['lof_cc']).format(colorA=colors[a], colorB=colors[b])
            lof_cc_pool.append(('lof_cc', (a, b), txt))
        for i in range(n - 1):
            a, b = drinks_sorted[i], drinks_sorted[i + 1]
            txt = random.choice(style['lof_dd']).format(drinkA=drinks[a], drinkB=drinks[b])
            lof_dd_pool.append(('lof_dd', (a, b), txt))
        for a in range(n):
            for b in range(n):
                if pos_of_color[a] < pos_of_drink[b]:
                    txt = random.choice(style['lof_cd']).format(colorA=colors[a], drinkB=drinks[b])
                    lof_cd_pool.append(('lof_cd', (a, b), txt))
        if lof_cc_pool:
            add_unique(candidates, seen_keys, random.choice(lof_cc_pool))
        elif lof_dd_pool:
            add_unique(candidates, seen_keys, random.choice(lof_dd_pool))
        elif lof_cd_pool:
            add_unique(candidates, seen_keys, random.choice(lof_cd_pool))
        extend_unique(candidates, seen_keys, lof_cc_pool, max(2, n // 2))
        extend_unique(candidates, seen_keys, lof_dd_pool, max(2, n // 2))
        extend_unique(candidates, seen_keys, lof_cd_pool, max(2, n // 2))

        # 恰隔一位
        two_dd_pool = []
        for a in range(n):
            for b in range(n):
                if pos_of_drink[a] + 2 == pos_of_drink[b]:
                    txt = random.choice(style['two_dd']).format(drinkA=drinks[a], drinkB=drinks[b])
                    two_dd_pool.append(('two_dd', (a, b), txt))
        extend_unique(candidates, seen_keys, two_dd_pool, max(2, n // 2))

        # 端点不在（至少一条）
        end_nv_pool = [('end_nv', (v,), random.choice(style['end_nv']).format(vol=volunteers[v])) for v in range(n) if pos_of_vol[v] not in (0, n - 1)]
        end_nd_pool = [('end_nd', (d,), random.choice(style['end_nd']).format(drink=drinks[d])) for d in range(n) if pos_of_drink[d] not in (0, n - 1)]
        end_nc_pool = [('end_nc', (c,), random.choice(style['end_nc']).format(color=colors[c])) for c in range(n) if pos_of_color[c] not in (0, n - 1)]
        forced_end_added = False
        for pool in [end_nv_pool, end_nd_pool, end_nc_pool]:
            if pool and not forced_end_added:
                add_unique(candidates, seen_keys, random.choice(pool))
                forced_end_added = True
        extend_unique(candidates, seen_keys, end_nv_pool, 2)
        extend_unique(candidates, seen_keys, end_nd_pool, 2)
        extend_unique(candidates, seen_keys, end_nc_pool, 2)

        # 夹在（限流）
        bet_pool: List[Tuple[str, Tuple[int, ...], str]] = []
        for i in range(n - 1):
            cA, cB = colors_sorted[i], colors_sorted[i + 1]
            mids = [d for d in range(n) if pos_of_drink[d] > pos_of_color[cA] and pos_of_drink[d] < pos_of_color[cB]]
            for dX in _cap_list(mids, 2):
                txt = random.choice(style['bet_cdc']).format(colorA=colors[cA], drinkX=drinks[dX], colorB=colors[cB])
                bet_pool.append(('bet_cdc', (cA, dX, cB), txt))
        extend_unique(candidates, seen_keys, bet_pool, max(2, n // 2))

        # 志愿者-饮品距离（至少一条）
        dist1_pool, dist2_pool = [], []
        for v in range(n):
            for d in range(n):
                diff = abs(pos_of_vol[v] - pos_of_drink[d])
                if diff == 1:
                    txt = random.choice(style['dist_vd1']).format(vol=volunteers[v], drink=drinks[d])
                    dist1_pool.append(('dist_vd1', (v, d), txt))
                elif diff == 2:
                    txt = random.choice(style['dist_vd2']).format(vol=volunteers[v], drink=drinks[d])
                    dist2_pool.append(('dist_vd2', (v, d), txt))
        if dist1_pool:
            add_unique(candidates, seen_keys, random.choice(dist1_pool))
        elif dist2_pool:
            add_unique(candidates, seen_keys, random.choice(dist2_pool))
        extend_unique(candidates, seen_keys, dist1_pool, max(2, n // 2))
        extend_unique(candidates, seen_keys, dist2_pool, max(2, n // 2))

        # 当且仅当（限流）
        iff_pool: List[Tuple[str, Tuple[int, ...], str]] = []
        v_pairs = [(v1, v2) for v1 in range(n) for v2 in range(n) if v1 != v2]
        random.shuffle(v_pairs)
        dc_pairs = [(d, c) for d in range(n) for c in range(n)]
        random.shuffle(dc_pairs)
        take_cnt = min(2, max(1, n // 3))
        for i in range(min(take_cnt * 2, len(v_pairs), len(dc_pairs))):
            v1, v2 = v_pairs[i]
            d, c = dc_pairs[i]
            adj_truth = (abs(pos_of_drink[d] - pos_of_color[c]) == 1)
            order_truth = (pos_of_vol[v1] < pos_of_vol[v2])
            if adj_truth == order_truth:
                txt = random.choice(style['iff_adj_dc_vv']).format(drink=drinks[d], color=colors[c], volA=volunteers[v1], volB=volunteers[v2])
                iff_pool.append(('iff_adj_dc_vv', (d, c, v1, v2), txt))
        extend_unique(candidates, seen_keys, iff_pool, take_cnt)

        # 链式约束（至少一个）
        chain_cc_pool, chain_dd_pool = [], []
        for i in range(n - 2):
            c1, c2, c3 = colors_sorted[i], colors_sorted[i + 1], colors_sorted[i + 2]
            txt = random.choice(style['chain_cc3']).format(c1=colors[c1], c2=colors[c2], c3=colors[c3])
            chain_cc_pool.append(('chain_cc3', (c1, c2, c3), txt))
        for i in range(n - 2):
            d1, d2, d3 = drinks_sorted[i], drinks_sorted[i + 1], drinks_sorted[i + 2]
            txt = random.choice(style['chain_dd3']).format(d1=drinks[d1], d2=drinks[d2], d3=drinks[d3])
            chain_dd_pool.append(('chain_dd3', (d1, d2, d3), txt))
        if chain_cc_pool:
            add_unique(candidates, seen_keys, random.choice(chain_cc_pool))
        elif chain_dd_pool:
            add_unique(candidates, seen_keys, random.choice(chain_dd_pool))
        extend_unique(candidates, seen_keys, chain_cc_pool, 2)
        extend_unique(candidates, seen_keys, chain_dd_pool, 2)

        # 额外强化：在构建前强制加入1条链式与1条距离
        forced_chain = None
        if chain_cc_pool:
            forced_chain = random.choice(chain_cc_pool)
        elif chain_dd_pool:
            forced_chain = random.choice(chain_dd_pool)
        if forced_chain:
            add_unique(candidates, seen_keys, forced_chain)

        forced_dist = None
        if dist1_pool:
            forced_dist = random.choice(dist1_pool)
        elif dist2_pool:
            forced_dist = random.choice(dist2_pool)
        if forced_dist:
            add_unique(candidates, seen_keys, forced_dist)

        random.shuffle(candidates)

        # 随机构建：先强制加入三类等式锚定，再按权重选取
        def _try_random_build(n: int,
                              candidates: List[Tuple[str, Tuple[int, ...], str]],
                              min_clues: int,
                              extend_limit: int,
                              pre_items: List[Tuple[str, Tuple[int, ...], str]]):
            w = _weights()
            def score(item):
                ct = item[0]
                base = w.get(ct, 10)
                return base + random.uniform(-2.5, 2.5)

            limited_cands = _cap_list(candidates, 100)
            sorted_cands = sorted(limited_cands, key=score, reverse=True)

            s, pv, pd, pc = _build_z3_model(n)
            chosen: List[Tuple[str, Tuple[int, ...], str]] = []

            # 强制加入锚定等式以及一条链式与一条距离（已在候选中）
            for ctype, payload, txt in pre_items:
                _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
                chosen.append((ctype, payload, txt))

            unique = False
            for ctype, payload, txt in sorted_cands:
                # 避免重复添加pre_items
                if (ctype, payload, txt) in pre_items:
                    continue
                s.push()
                _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
                cnt = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
                s.pop()
                if cnt == 0:
                    continue
                _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
                chosen.append((ctype, payload, txt))
                if len(chosen) >= min_clues:
                    cnt_now = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
                    if cnt_now == 1:
                        unique = True
                        break
                if len(chosen) >= extend_limit:
                    cnt_now = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
                    if cnt_now == 1:
                        unique = True
                    break
            return unique, chosen

        def _try_greedy_build(n: int,
                              candidates: List[Tuple[str, Tuple[int, ...], str]],
                              min_clues: int,
                              extend_limit: int,
                              pre_items: List[Tuple[str, Tuple[int, ...], str]]):
            w = _weights()
            remaining = _cap_list(candidates[:], 150)
            s, pv, pd, pc = _build_z3_model(n)
            chosen: List[Tuple[str, Tuple[int, ...], str]] = []

            # 先加入pre_items
            for ctype, payload, txt in pre_items:
                # 从remaining移除相同项
                try:
                    remaining.remove((ctype, payload, txt))
                except ValueError:
                    pass
                _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
                chosen.append((ctype, payload, txt))

            for _ in range(min(len(remaining), extend_limit)):
                best_idx = -1
                best_cnt = 999
                best_weight = -999
                probe_indices = _cap_list(list(range(len(remaining))), 30)
                for i in probe_indices:
                    ctype, payload, _txt = remaining[i]
                    s.push()
                    _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
                    cnt = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
                    s.pop()
                    wt = w.get(ctype, 10)
                    if cnt < best_cnt or (cnt == best_cnt and wt > best_weight):
                        best_cnt = cnt
                        best_idx = i
                        best_weight = wt
                    if cnt == 1 and len(chosen) + 1 >= min_clues:
                        best_idx = i
                        best_cnt = cnt
                        best_weight = wt
                        break
                if best_idx == -1:
                    break
                ctype, payload, txt = remaining.pop(best_idx)
                _add_clue_to_solver(s, pv, pd, pc, n, (ctype, payload))
                chosen.append((ctype, payload, txt))
                if len(chosen) >= min_clues:
                    cnt_now = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
                    if cnt_now == 1:
                        return True, chosen
                if len(chosen) >= extend_limit:
                    cnt_now = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
                    return (cnt_now == 1), chosen
            cnt_final = _count_solutions_at_most_two_inplace(s, pv, pd, pc)
            return (cnt_final == 1), chosen

        pre_items = [must_mv, must_md, must_mc]
        if forced_chain:
            pre_items.append(forced_chain)
        if forced_dist:
            pre_items.append(forced_dist)

        unique, chosen = _try_random_build(n, candidates, min_clues, extend_limit, pre_items)
        if not unique:
            unique, chosen = _try_greedy_build(n, candidates, min_clues, extend_limit, pre_items)
        if not unique:
            continue

        reduced = _reduce_clues(n, chosen, min_clues, max_clues)
        if not _unique_solution_with_clues(n, [(ct, pl) for ct, pl, _ in reduced]):
            continue

        # 分类输出
        eq_mv, eq_md, eq_mc = [], [], []
        neq_mv, neq_md, neq_mc = [], [], []
        adj_dc, nadj_dc = [], []
        lof_cc, lof_dd, lof_cd = [], [], []
        two_dd = []
        end_nv, end_nd, end_nc = [], [], []
        bet_cdc = []
        dist_vd1, dist_vd2 = [], []
        iff_adj_dc_vv = []
        chain_cc3, chain_dd3 = [], []
        lines = []
        for idx, (ctype, payload, txt) in enumerate(reduced, 1):
            lines.append(f'{idx} {txt}')
            if ctype == 'eq_mv': eq_mv.append([payload[0], payload[1]])
            elif ctype == 'eq_md': eq_md.append([payload[0], payload[1]])
            elif ctype == 'eq_mc': eq_mc.append([payload[0], payload[1]])
            elif ctype == 'neq_mv': neq_mv.append([payload[0], payload[1]])
            elif ctype == 'neq_md': neq_md.append([payload[0], payload[1]])
            elif ctype == 'neq_mc': neq_mc.append([payload[0], payload[1]])
            elif ctype == 'adj_dc': adj_dc.append([payload[0], payload[1]])
            elif ctype == 'nadj_dc': nadj_dc.append([payload[0], payload[1]])
            elif ctype == 'lof_cc': lof_cc.append([payload[0], payload[1]])
            elif ctype == 'lof_dd': lof_dd.append([payload[0], payload[1]])
            elif ctype == 'lof_cd': lof_cd.append([payload[0], payload[1]])
            elif ctype == 'two_dd': two_dd.append([payload[0], payload[1]])
            elif ctype == 'end_nv': end_nv.append([payload[0]])
            elif ctype == 'end_nd': end_nd.append([payload[0]])
            elif ctype == 'end_nc': end_nc.append([payload[0]])
            elif ctype == 'bet_cdc': bet_cdc.append([payload[0], payload[1], payload[2]])
            elif ctype == 'dist_vd1': dist_vd1.append([payload[0], payload[1], 1])
            elif ctype == 'dist_vd2': dist_vd2.append([payload[0], payload[1], 2])
            elif ctype == 'iff_adj_dc_vv': iff_adj_dc_vv.append([payload[0], payload[1], payload[2], payload[3]])
            elif ctype == 'chain_cc3': chain_cc3.append([payload[0], payload[1], payload[2]])
            elif ctype == 'chain_dd3': chain_dd3.append([payload[0], payload[1], payload[2]])
        return {
            'eq_mile_vol': eq_mv,
            'eq_mile_drink': eq_md,
            'eq_mile_color': eq_mc,
            'not_mile_vol': neq_mv,
            'not_mile_drink': neq_md,
            'not_mile_color': neq_mc,
            'adj_drink_color': adj_dc,
            'not_adj_drink_color': nadj_dc,
            'leftof_color_color': lof_cc,
            'leftof_drink_drink': lof_dd,
            'leftof_color_drink': lof_cd,
            'two_left_drink_drink': two_dd,
            'endpoint_not_vol': end_nv,
            'endpoint_not_drink': end_nd,
            'endpoint_not_color': end_nc,
            'between_cdc': bet_cdc,
            'dist_vol_drink_1': dist_vd1,
            'dist_vol_drink_2': dist_vd2,
            'iff_adj_dc_vv': iff_adj_dc_vv,
            'chain_color3': chain_cc3,
            'chain_drink3': chain_dd3,
            'clue_text': '\n'.join(lines)
        }
    raise RuntimeError('Failed to generate a unique puzzle within attempts')

def pick_query_indices(eq_mv: List[List[int]],
                       eq_md: List[List[int]],
                       eq_mc: List[List[int]],
                       pos_num: int) -> List[int]:
    mv_pos = {m for m, _ in eq_mv} if eq_mv else set()
    md_pos = {m for m, _ in eq_md} if eq_md else set()
    mc_pos = {m for m, _ in eq_mc} if eq_mc else set()
    color_to_mile = {c: m for m, c in eq_mc} if eq_mc else {}

    all_positions = list(range(pos_num))

    safe_a = [p for p in all_positions if p not in mv_pos]
    mile_a = random.choice(safe_a) if safe_a else random.choice(all_positions)

    safe_b = [p for p in all_positions if p not in md_pos and p != mile_a]
    mile_b = random.choice(safe_b) if safe_b else random.choice([p for p in all_positions if p != mile_a] or all_positions)

    safe_c = [p for p in all_positions if p not in mc_pos and p not in (mile_a, mile_b)]
    mile_c = random.choice(safe_c) if safe_c else random.choice([p for p in all_positions if p not in (mile_a, mile_b)] or all_positions)

    all_colors = list(range(pos_num))
    safe_colors = []
    for c in all_colors:
        m = color_to_mile.get(c, None)
        if m is None or (m is not None and m not in md_pos and m not in (mile_a, mile_b, mile_c)):
            safe_colors.append(c)
    color_idx = random.choice(safe_colors) if safe_colors else random.choice(all_colors)

    return [mile_a, mile_b, mile_c, color_idx]

def who_at_mile(vol_list: List[int], mile_list: List[int], volunteers: List[str], target_mile_idx: int) -> str:
    for i in range(len(mile_list)):
        if mile_list[i] == target_mile_idx:
            return volunteers[vol_list[i]]
    return ''

def drink_for_color(drink_list: List[int], color_list: List[int], drinks: List[str], target_color_idx: int) -> str:
    for i in range(len(color_list)):
        if color_list[i] == target_color_idx:
            return drinks[drink_list[i]]
    return ''

def drink_at_mile(drink_list: List[int], mile_list: List[int], drinks: List[str], target_mile_idx: int) -> str:
    for i in range(len(mile_list)):
        if mile_list[i] == target_mile_idx:
            return drinks[drink_list[i]]
    return ''

def color_at_mile(color_list: List[int], mile_list: List[int], colors: List[str], target_mile_idx: int) -> str:
    for i in range(len(mile_list)):
        if mile_list[i] == target_mile_idx:
            return colors[color_list[i]]
    return ''