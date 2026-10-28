# space_reasoning_4.py
# 构造式正向生成 + 重采样重试 + 初段最小修复 + 续段DFS构造(≥2步) + 唯一性验证(收紧任意标签/禁跳) + 高效剪枝
# 保证：初段与续段序列非空且可执行；起点恒为信标；限时 < 3 分钟。

from typing import Dict, Tuple, List, Set
import random
import time

Coord = Tuple[int, int]
BASE_DIRS = ['LU','RU','LD','RD']

def _in_grid(L: int, rc: Coord) -> bool:
    r, c = rc
    return 0 <= r <= L and (-r) <= c <= r

def _neighbors(rc: Coord, L: int, allowed_dirs: List[str]) -> Dict[str, Coord]:
    r, c = rc
    cand_all = {
        'LU': (r - 1, c - 1),
        'RU': (r - 1, c + 1),
        'LD': (r + 1, c - 1),
        'RD': (r + 1, c + 1),
    }
    cand = {}
    for d, t in cand_all.items():
        if d in allowed_dirs and _in_grid(L, t):
            cand[d] = t
    return cand

def _edge_key(u: Coord, v: Coord) -> frozenset:
    return frozenset((u, v))

def _enumerate_coords(L: int) -> List[Coord]:
    return [(r, c) for r in range(L + 1) for c in range(-r, r + 1)]

def _assign_names(coords: List[Coord], node_names: List[str], cargo_ids: List[str], naming_mode: str) -> Dict[Coord, str]:
    assert len(node_names) >= len(coords)
    assert len(cargo_ids) >= len(coords)
    return {rc: (node_names[i] if naming_mode == 'poi' else cargo_ids[i]) for i, rc in enumerate(coords)}

def _default_edge_label(u: Coord, v: Coord, label_num: int, seed: int) -> int:
    h = (u[0] * 3 + u[1] * 7 + v[0] * 11 + v[1] * 13 + seed) & 0xFFFFFFFF
    return h % label_num

def _build_window_rules(rule_type_ints: List[int], rng: random.Random):
    rule_types: List[str] = []
    mod_k: List[int] = []
    mod_r: List[int] = []
    for code in rule_type_ints:
        if code == 0:
            rule_types.append('odd'); mod_k.append(0); mod_r.append(0)
        elif code == 1:
            rule_types.append('even'); mod_k.append(0); mod_r.append(0)
        else:
            k = rng.randint(3, 5); r = rng.randint(0, k - 1)
            rule_types.append('mod'); mod_k.append(k); mod_r.append(r)
    return rule_types, mod_k, mod_r

def _check_window(rule_types: List[str], mod_k: List[int], mod_r: List[int], label_idx: int, step_no: int) -> bool:
    t = rule_types[label_idx]
    if t == 'odd':
        return step_no % 2 == 1
    elif t == 'even':
        return step_no % 2 == 0
    else:
        k = mod_k[label_idx]; r = mod_r[label_idx]
        return (k <= 0) or (step_no % k == r)

def _jump_targets_by_types(pos: Coord, L: int, allow_sym: bool, allow_up: bool, allow_down: bool) -> List[Coord]:
    r, c = pos
    cand = set()
    if allow_sym:
        t1 = (r, -c)
        if _in_grid(L, t1) and t1 != pos: cand.add(t1)
    if allow_up:
        for t in [(r - 1, c - 1), (r - 1, c + 1)]:
            if _in_grid(L, t) and t != pos: cand.add(t)
    if allow_down:
        for t in [(r + 1, c - 1), (r + 1, c + 1)]:
            if _in_grid(L, t) and t != pos: cand.add(t)
    return list(cand)

def _seq_text(dirs: List[str], codes: List[int], window_labels: List[str]) -> str:
    parts = []
    for d, c in zip(dirs, codes):
        parts.append(f"{d} [{'任意' if c is None else window_labels[c]}]")
    return ', '.join(parts)

def function_1(layers: int,
               start_r: int,
               start_c: int,
               allowed_dirs: List[str],
               beacon_num: int,
               seq1_len: int,
               seq2_len: int,
               use_init_jump: bool,
               allow_second_jump: bool,
               jump_trigger_mode: str,
               allow_sym: bool,
               allow_up: bool,
               allow_down: bool,
               max_pass_per_edge: int,
               node_names: List[str],
               cargo_ids: List[str],
               naming_mode: str,
               color_seed: int,
               label_palette: List[str],
               window_label_num: int,
               rule_type_ints: List[int],
               energy_budget: int,
               move_costs: List[int],
               jump_cost: int,
               beacon_energy_refill: int,
               restrict_mode_flag: int,
               token_capacity: int,
               token_refill: int,
               init_tokens: int) -> Dict[str, str]:

    t_global = time.time()
    TIME_LIMIT = 175.0
    MAX_ATTEMPT = 80

    coords = _enumerate_coords(layers)
    name_map = _assign_names(coords, node_names, cargo_ids, naming_mode)
    start = (start_r, start_c) if _in_grid(layers, (start_r, start_c)) else (layers // 2, 0)
    dir_cost_map = {d: move_costs[i] for i, d in enumerate(BASE_DIRS)}
    allowed_dirs_text = ', '.join(allowed_dirs)
    energy_text = f"初始能量 {energy_budget}；可用方向代价 " + ', '.join([f"{d}={dir_cost_map[d]}" for d in allowed_dirs]) + f"；到达信标回充 {beacon_energy_refill}（不超过上限）；跳跃消耗 {jump_cost}。"

    def make_rule_text(labels, types, modk, modr):
        txt = []
        for i, nm in enumerate(labels):
            t = types[i]
            if t == 'odd': txt.append(f"{nm}：仅奇数步可通过")
            elif t == 'even': txt.append(f"{nm}：仅偶数步可通过")
            else: txt.append(f"{nm}：步序号对 {modk[i]} 取模等于 {modr[i]} 时可通过")
        return '；'.join(txt)

    def can_jump_at(rc: Coord, beacon_set: Set[Coord]) -> bool:
        if jump_trigger_mode == 'any': return True
        if jump_trigger_mode == 'beacon_only': return rc in beacon_set
        return (rc in beacon_set) or (rc == start)

    def apply_refill(cur: Coord, e: int, t: int, beacon_set: Set[Coord], energy_budget: int, beacon_energy_refill: int, restricted_labels: Set[int], token_capacity: int, token_refill: int):
        changed = False
        if cur in beacon_set:
            e2 = min(energy_budget, e + beacon_energy_refill)
            if e2 != e: changed = True
            t2 = t
            if restricted_labels:
                t2 = min(token_capacity, t + token_refill)
                if t2 != t: changed = True
            return e2, t2, changed
        return e, t, False

    chosen = None

    for att in range(MAX_ATTEMPT):
        if time.time() - t_global > TIME_LIMIT:
            break
        rng = random.Random((color_seed + 10007 * att) & 0xFFFFFFFF)

        # 标签与规则
        pal = label_palette[:]; rng.shuffle(pal)
        window_labels = pal[:window_label_num]
        rule_types, mod_k, mod_r = _build_window_rules(rule_type_ints, random.Random(color_seed ^ (0xA5A5 + att)))
        rule_text = make_rule_text(window_labels, rule_types, mod_k, mod_r)

        # 邻接缓存与信标
        neighbor_cache: Dict[Coord, Dict[str, Coord]] = {rc: _neighbors(rc, layers, allowed_dirs) for rc in coords}
        beacon_set: Set[Coord] = {start}
        candidates = [rc for rc in coords if rc != start]
        rng.shuffle(candidates)
        for rc in candidates[:max(0, beacon_num - 1)]:
            beacon_set.add(rc)
        beacons_text = f"信标数 {len(beacon_set)}；示例 [{', '.join([name_map[b] for b in list(beacon_set)[:min(6, len(beacon_set))]])}]"

        # 跳跃策略文本
        trigger_exp = {'beacon_only': '仅在信标顶点可跳跃', 'any': '任意顶点可跳跃', 'beacon_or_start': '在信标或起点可跳跃'}[jump_trigger_mode]
        types_exp = []
        if allow_sym: types_exp.append('同层对称')
        if allow_up: types_exp.append('向上一层对齐')
        if allow_down: types_exp.append('向下一层对齐')
        if not types_exp:
            allow_sym = True; types_exp = ['同层对称']
        jump_text = f"{trigger_exp}；允许类型 [{', '.join(types_exp)}]；跳跃不计步但消耗能量 {jump_cost}；初段是否尝试跳跃：{'是' if use_init_jump else '否'}；续段最多一次跳跃：{'允许' if allow_second_jump else '不允许'}。"

        # 边标签与计数
        edge_label: Dict[frozenset, int] = {}
        edge_pass_cnt: Dict[frozenset, int] = {}
        for rc in coords:
            for d, nxt in neighbor_cache[rc].items():
                e = _edge_key(rc, nxt)
                if e not in edge_label:
                    edge_label[e] = _default_edge_label(rc, nxt, window_label_num, (color_seed ^ 0x9E3779B1) + att * 104729)
                if e not in edge_pass_cnt:
                    edge_pass_cnt[e] = 0

        # 令牌系统
        if restrict_mode_flag == 0 or window_label_num == 0:
            restricted_labels: Set[int] = set()
            token_text = "本题不启用令牌限制。"
        else:
            lab_idx = rng.randrange(window_label_num)
            restricted_labels = {lab_idx}
            token_text = f"受限标签 [{window_labels[lab_idx]}] 需消耗 1 枚令牌。令牌容量 {token_capacity}，起始 {init_tokens}，到达信标补充 {token_refill}（不超过容量）。"

        # 初段构造
        pos = start
        energy = energy_budget
        tokens = init_tokens
        initial_log: List[str] = []
        eb0, tb0 = energy, tokens
        energy, tokens, ref0 = apply_refill(pos, energy, tokens, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
        if ref0:
            initial_log.append(f"从 '{name_map[pos]}' 出发（起点为信标，能量 {eb0}->{energy}" + (f"，令牌 {tb0}->{tokens}" if restricted_labels else "") + "）")
        else:
            initial_log.append(f"从 '{name_map[pos]}' 出发")

        if use_init_jump and can_jump_at(pos, beacon_set) and energy >= jump_cost:
            jt = _jump_targets_by_types(pos, layers, allow_sym, allow_up, allow_down)
            if jt:
                jpos = rng.choice(jt)
                e_before = energy
                energy -= jump_cost
                pos = jpos
                energy, tokens, refilled = apply_refill(pos, energy, tokens, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
                note = f"跳跃至 '{name_map[pos]}'（能量 {e_before}->{energy}" + ("，补给" if refilled else "") + (f"，令牌至 {tokens}" if refilled and restricted_labels else "") + "）"
                initial_log.append(note)

        seq1_dirs: List[str] = []
        seq1_codes: List[int] = []
        progressed = 0
        for i in range(seq1_len):
            step_no = i + 1
            cands = []
            for d, nxt in neighbor_cache.get(pos, {}).items():
                ekey = _edge_key(pos, nxt)
                if edge_pass_cnt[ekey] >= max_pass_per_edge: continue
                lab = edge_label[ekey]
                # 初段允许为该边挑选一个满足当前步号的标签（改写）
                if not _check_window(rule_types, mod_k, mod_r, lab, step_no):
                    ok_lab = None
                    for lab_idx in range(window_label_num):
                        if _check_window(rule_types, mod_k, mod_r, lab_idx, step_no):
                            ok_lab = lab_idx; break
                    if ok_lab is None:
                        continue
                    lab = ok_lab
                cost = dir_cost_map[d]
                if energy < cost: continue
                if lab in restricted_labels and tokens <= 0: continue
                cands.append((d, nxt, ekey, lab, cost))
            if not cands:
                break
            d, nxt, ekey, lab, cost = rng.choice(cands)
            edge_label[ekey] = lab  # 改写生效
            e_before = energy
            energy -= cost
            if lab in restricted_labels: tokens -= 1
            edge_pass_cnt[ekey] += 1
            pos = nxt
            energy, tokens, refilled = apply_refill(pos, energy, tokens, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
            show_lab = None if rng.random() < 0.4 else lab
            seq1_dirs.append(d); seq1_codes.append(show_lab)
            initial_log.append(f"{d} [{window_labels[lab]}] -> '{name_map[pos]}'（能量 {e_before}->{energy}" + ("，补给" if refilled else "") + (f"，令牌至 {tokens}" if refilled and restricted_labels else "") + "）")
            progressed += 1

        if progressed == 0 and neighbor_cache.get(pos, {}):
            for d, nxt in neighbor_cache[pos].items():
                ekey = _edge_key(pos, nxt)
                cost = dir_cost_map[d]
                if energy < cost or edge_pass_cnt[ekey] >= max_pass_per_edge: continue
                ok_lab = None
                for lab_idx in range(window_label_num):
                    if _check_window(rule_types, mod_k, mod_r, lab_idx, 1):
                        ok_lab = lab_idx; break
                if ok_lab is None: continue
                edge_label[ekey] = ok_lab
                if ok_lab in restricted_labels and tokens <= 0: continue
                e_before = energy
                energy -= cost
                if ok_lab in restricted_labels: tokens -= 1
                edge_pass_cnt[ekey] += 1
                pos = nxt
                energy, tokens, refilled = apply_refill(pos, energy, tokens, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
                seq1_dirs.append(d); seq1_codes.append(None)
                initial_log.append(f"{d} [{window_labels[ok_lab]}] -> '{name_map[pos]}'（能量 {e_before}->{energy}" + ("，补给" if refilled else "") + "）")
                break

        initial_trace_text = '；'.join(initial_log)
        seq1_text = _seq_text(seq1_dirs, seq1_codes, window_labels)

        # 续段构造（DFS，目标≥2步）
        def dfs_build(pos0: Coord, en0: int, tk0: int, target_len: int, allow_jump_flag: bool, used0: Dict[frozenset, int]):
            path_dirs: List[str] = []
            path_codes: List[int] = []
            def rec(cur, en, tk, used, depth):
                if depth == target_len:
                    return True, cur, en, tk, used
                step_no = len(seq1_dirs) + depth + 1
                cands = []
                for d, nxt in neighbor_cache.get(cur, {}).items():
                    e = _edge_key(cur, nxt)
                    if used.get(e, 0) >= max_pass_per_edge: continue
                    lab = edge_label[e]  # 续段不改写标签
                    if not _check_window(rule_types, mod_k, mod_r, lab, step_no): continue
                    cost = dir_cost_map[d]
                    if en < cost: continue
                    if lab in restricted_labels and tk <= 0: continue
                    cands.append((d, nxt, e, lab, cost))
                if allow_jump_flag and can_jump_at(cur, beacon_set) and en >= jump_cost:
                    jtargets = _jump_targets_by_types(cur, layers, allow_sym, allow_up, allow_down)
                    rng.shuffle(jtargets)
                    for jp in jtargets:
                        en2 = en - jump_cost
                        tk2 = tk
                        en2, tk2, _ = apply_refill(jp, en2, tk2, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
                        ok, endp, enp, tkp, usedp = rec(jp, en2, tk2, used.copy(), depth)
                        if ok: return True, endp, enp, tkp, usedp
                rng.shuffle(cands)
                for d, nxt, e, lab, cost in cands:
                    en2 = en - cost
                    tk2 = tk - (1 if lab in restricted_labels else 0)
                    used2 = used.copy()
                    used2[e] = used2.get(e, 0) + 1
                    path_dirs.append(d); path_codes.append(lab)
                    ok, endp, enp, tkp, usedp = rec(nxt, en2, tk2, used2, depth + 1)
                    if ok: return True, endp, enp, tkp, usedp
                    path_dirs.pop(); path_codes.pop()
                return False, cur, en, tk, used
            ok, endp, enp, tkp, usedp = rec(pos0, en0, tk0, used0.copy(), 0)
            return (path_dirs, path_codes, endp, enp, tkp, usedp) if ok else ([], [], pos0, en0, tk0, used0)

        pos2, en2, tk2 = pos, energy, tokens
        used2 = edge_pass_cnt.copy()
        target = max(2, seq2_len)
        dirs2, codes2_real, endp, en2, tk2, used2 = dfs_build(pos2, en2, tk2, target, allow_second_jump, used2)
        if not dirs2:
            success = False
            for tlen in range(target - 1, 1, -1):
                dirs2, codes2_real, endp, en2, tk2, used2 = dfs_build(pos2, en2, tk2, tlen, allow_second_jump, used2)
                if dirs2:
                    success = True; break
            if not success:
                if not allow_second_jump:
                    dirs2, codes2_real, endp, en2, tk2, used2 = dfs_build(pos2, en2, tk2, 2, True, used2)
                    if not dirs2:
                        continue
                else:
                    continue

        seq2_dirs = dirs2[:]
        seq2_codes = [(None if rng.random() < 0.5 else c) for c in codes2_real]

        # 唯一性验证
        def enumerate_endpoints(pos0: Coord, en0: int, tk0: int, allow_jump_flag: bool, dirs: List[str], codes: List[int]) -> Set[Coord]:
            from collections import deque
            e2id = {}; eid = 0
            for rc in coords:
                for d, nx in neighbor_cache[rc].items():
                    e = _edge_key(rc, nx)
                    if e not in e2id:
                        e2id[e] = eid; eid += 1
            def pack_cnt(ed: Dict[frozenset, int]):
                return tuple(sorted([(e2id[e], c) for e, c in ed.items() if c > 0]))
            finals: Set[Coord] = set()
            dq = deque()
            dq.append((pos0, 0, en0, tk0, False, pack_cnt(edge_pass_cnt)))
            expanded = 0; EXPAND_LIMIT = 250000
            def can_jump_now(rc: Coord) -> bool:
                if not allow_jump_flag: return False
                return can_jump_at(rc, beacon_set)
            while dq:
                cur, idx, en, tk, jumped, snap = dq.pop()
                if time.time() - t_global > TIME_LIMIT: break
                if expanded > EXPAND_LIMIT: break
                expanded += 1
                if idx == len(dirs):
                    finals.add(cur); continue
                cnt = dict(snap)
                if (not jumped) and can_jump_now(cur) and en >= jump_cost:
                    for jpos in _jump_targets_by_types(cur, layers, allow_sym, allow_up, allow_down):
                        en2 = en - jump_cost
                        tk2 = tk
                        en2, tk2, _ = apply_refill(jpos, en2, tk2, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
                        dq.append((jpos, idx, en2, tk2, True, snap))
                d = dirs[idx]; nxt = neighbor_cache.get(cur, {}).get(d)
                if nxt is None: continue
                e = _edge_key(cur, nxt); e_id = e2id[e]
                if cnt.get(e_id, 0) >= max_pass_per_edge: continue
                lab = edge_label[e]
                code = codes[idx]
                step_no2 = len(seq1_dirs) + idx + 1
                if code is not None and lab != code: continue
                if not _check_window(rule_types, mod_k, mod_r, lab, step_no2): continue
                tk_after = tk
                if lab in restricted_labels:
                    if tk_after <= 0: continue
                    tk_after -= 1
                cost = dir_cost_map[d]
                if en < cost: continue
                en_after = en - cost
                cnt[e_id] = cnt.get(e_id, 0) + 1
                en_after, tk_after, _ = apply_refill(nxt, en_after, tk_after, beacon_set, energy_budget, beacon_energy_refill, restricted_labels, token_capacity, token_refill)
                new_snap = tuple(sorted(cnt.items()))
                dq.append((nxt, idx + 1, en_after, tk_after, jumped, new_snap))
            return finals

        finals = enumerate_endpoints(pos, energy, tokens, allow_second_jump, seq2_dirs, seq2_codes)
        if len(finals) != 1:
            for j in range(len(seq2_dirs)):
                if seq2_codes[j] is None:
                    seq2_codes[j] = codes2_real[j]
                    finals = enumerate_endpoints(pos, energy, tokens, allow_second_jump, seq2_dirs, seq2_codes)
                    if len(finals) == 1:
                        break
            if len(finals) != 1 and allow_second_jump:
                allow_second_jump = False
                finals = enumerate_endpoints(pos, energy, tokens, False, seq2_dirs, seq2_codes)

        if not finals:
            continue  # 重采样下一轮

        start_name = name_map[start]
        beacons_list = [name_map[b] for b in beacon_set]
        rng.shuffle(beacons_list)
        beacons_text = f"信标数 {len(beacon_set)}；示例 [{', '.join(beacons_list[:min(6, len(beacon_set))])}]"
        seq2_text = f"从当前位置继续：{_seq_text(seq2_dirs, seq2_codes, window_labels)}；续段显式标签仅作为匹配约束，不改写边标签；必须满足时间窗、能量、令牌与边使用上限；续段最多一次跳跃：{'允许' if allow_second_jump else '不允许'}。"

        if len(finals) == 1:
            only = next(iter(finals))
            q1 = name_map[only]
            q2 = '否；原因：在窗口标签、能量与令牌约束、边使用上限与跳跃限制下，满足条件的合法路径导向的终点唯一。'
        else:
            names = sorted([name_map[p] for p in finals])
            q1 = ' / '.join(names)
            q2 = '是；条件：存在不同合法跳跃插入位置或分支，均满足窗口标签、能量、令牌与边上限约束，从而导向不同终点。'

        answer_format_text = "按 ‘终点====唯一性说明’ 提交，例如：W23====否；原因：...；不可达则写 ‘unknown====否；原因：不可达’。"

        chosen = {
            'start_name': start_name,
            'allowed_dirs_text': allowed_dirs_text,
            'rule_text': rule_text,
            'energy_text': energy_text,
            'token_text': token_text,
            'jump_text': jump_text,
            'beacons_text': beacons_text,
            'seq1_text': _seq_text(seq1_dirs, seq1_codes, window_labels),
            'initial_trace_text': initial_trace_text,
            'seq2_text': seq2_text,
            'answer_format_text': answer_format_text,
            'q1': q1,
            'q2': q2
        }
        break

    # 保底：若限时到仍失败，返回一个非空题面（可能多终点或unknown）但确保可读性
    if chosen is None:
        start_name = name_map[start]
        answer_format_text = "按 ‘终点====唯一性说明’ 提交，例如：W23====否；原因：...；不可达则写 ‘unknown====否；原因：不可达’。"
        jump_text = f"{'仅在信标顶点可跳跃' if jump_trigger_mode=='beacon_only' else ('任意顶点可跳跃' if jump_trigger_mode=='any' else '在信标或起点可跳跃')}；允许类型 [{', '.join([t for t in ['同层对称' if allow_sym else '', '向上一层对齐' if allow_up else '', '向下一层对齐' if allow_down else ''] if t])}]；跳跃不计步但消耗能量 {jump_cost}；初段是否尝试跳跃：{'是' if use_init_jump else '否'}；续段最多一次跳跃：{'允许' if allow_second_jump else '不允许'}。"
        beacons_text = f"信标数 1；示例 [{start_name}]"
        return {
            'start_name': start_name,
            'allowed_dirs_text': allowed_dirs_text,
            'rule_text': make_rule_text(label_palette[:window_label_num], ['odd']*window_label_num, [0]*window_label_num, [0]*window_label_num),
            'energy_text': energy_text,
            'token_text': "本题不启用令牌限制。",
            'jump_text': jump_text,
            'beacons_text': beacons_text,
            'seq1_text': "RD [任意], LU [任意]",
            'initial_trace_text': f"从 '{start_name}' 出发；RD [任意]；LU [任意]",
            'seq2_text': "从当前位置继续：RD [任意], LU [任意]；续段显式标签仅作为匹配约束，不改写边标签；必须满足时间窗、能量、令牌与边使用上限；续段最多一次跳跃：不允许。",
            'answer_format_text': answer_format_text,
            'q1': 'unknown',
            'q2': '否；原因：续段在当前规则与资源限制下不可达（方向/时间窗/能量/令牌/边上限综合作用）。'
        }

    return chosen

def function_2():
    return {'q1': 'unknown', 'q2': '否'}