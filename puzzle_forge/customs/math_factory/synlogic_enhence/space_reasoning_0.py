# space_reasoning_1.py
# 说明：
# - 生成阶段：完整候选域（长度4、步长固定1、方向6）枚举终点计数，挑选计数为1的终点并选取一条包含事件（优先至少一次传送与至少一次外圈沿边通过；次优至少一个事件；再次优纯唯一）的序列。将证书写入场景。
# - 验证阶段：优先使用证书（cert_end_label、cert_count、cert_len）快速判定；若证书缺失则回退枚举验证，域与生成一致，时间控制在3分钟内。

from typing import List, Dict, Tuple, Any
import random
import time

# 轴坐标方向映射
DIRS = {
    'E':  (1, 0),
    'SE': (0, 1),
    'SW': (-1, 1),
    'W':  (-1, 0),
    'NW': (0, -1),
    'NE': (1, -1),
}

def _hex_add(a: Tuple[int,int], b: Tuple[int,int]) -> Tuple[int,int]:
    return (a[0] + b[0], a[1] + b[1])

def _hex_dist(qr: Tuple[int,int]) -> int:
    q, r = qr
    return max(abs(q), abs(r), abs(q + r))

def _gen_all_nodes(R: int) -> List[Tuple[int,int]]:
    return [(q, r) for q in range(-R, R+1) for r in range(-R, R+1) if _hex_dist((q, r)) <= R]

def _outer_corners(R: int) -> List[Tuple[int,int]]:
    return [(R, 0), (0, R), (-R, R), (-R, 0), (0, -R), (R, -R)]

def _build_outer_ring(R: int) -> List[Tuple[int,int]]:
    start = (R, 0)
    seq = ['SE', 'SW', 'W', 'NW', 'NE', 'E']  # CW方向
    path = [start]
    curr = start
    for d in seq:
        dq, dr = DIRS[d]
        for _ in range(R):
            curr = (curr[0] + dq, curr[1] + dr)
            path.append(curr)
    if path[-1] == start:
        path = path[:-1]
    return path

def _ring_cw_map(ring: List[Tuple[int,int]]) -> Dict[Tuple[int,int], Tuple[int,int]]:
    cw = {}
    n = len(ring)
    for i in range(n):
        cw[ring[i]] = ring[(i+1) % n]
    return cw

def _gen_label(i: int, node: Tuple[int,int]) -> str:
    base = [
        '声纳','推进','通讯','材料','照明','能源','控制','采样','传感','定位','摄像',
        '电池','数据','气体','耐压','管路','导航','模块','滤波','水压','化学',
        '组织','取样','生物','机械','光学','磁场','热学','动力','校准','稳压','封装'
    ]
    q, r = node
    return f"{random.choice(base)}设备{i}@({q},{r})"

def _assign_labels(nodes: List[Tuple[int,int]]) -> Dict[Tuple[int,int], str]:
    return {n: _gen_label(i+1, n) for i, n in enumerate(nodes)}

def _assign_categories(nodes: List[Tuple[int,int]], energy_ratio: float, safety_ratio: float) -> Dict[Tuple[int,int], str]:
    total = len(nodes)
    ec = max(1, int(total * energy_ratio))
    sc = max(1, int(total * safety_ratio))
    pool = nodes[:]
    random.shuffle(pool)
    energy_set = set(pool[:ec])
    safety_set = set(pool[ec:ec+sc])
    cats = {}
    for n in nodes:
        if n in energy_set:
            cats[n] = '能量'
        elif n in safety_set:
            cats[n] = '安全'
        else:
            cats[n] = 'neutral'
    return cats

def _assign_tags(nodes: List[Tuple[int,int]]) -> Dict[Tuple[int,int], str]:
    total = len(nodes)
    key_count = max(1, int(total * random.uniform(0.05, 0.12)))
    gate_count = max(1, int(total * random.uniform(0.03, 0.08)))
    hazard_count = max(1, int(total * random.uniform(0.05, 0.10)))
    beacon_count = max(1, int(total * random.uniform(0.03, 0.08)))
    pool = nodes[:]
    random.shuffle(pool)
    keys = set(pool[:key_count])
    gates = set()
    i = key_count
    while len(gates) < gate_count and i < len(pool):
        if pool[i] not in keys:
            gates.add(pool[i])
        i += 1
    hazards = set()
    j = i
    while len(hazards) < hazard_count and j < len(pool):
        if pool[j] not in keys and pool[j] not in gates:
            hazards.add(pool[j])
        j += 1
    beacons = set()
    k = j
    while len(beacons) < beacon_count and k < len(pool):
        if pool[k] not in keys and pool[k] not in gates and pool[k] not in hazards:
            beacons.add(pool[k])
        k += 1
    tags = {}
    for n in nodes:
        if n in keys:
            tags[n] = 'key'
        elif n in gates:
            tags[n] = 'gate'
        elif n in hazards:
            tags[n] = 'hazard'
        elif n in beacons:
            tags[n] = 'beacon'
        else:
            tags[n] = 'none'
    return tags

def _modifier_rules_restricted() -> Dict[str, Dict[str, Any]]:
    # 限幅版：能量乘2；安全整除2；neutral不变（至少1）
    return {
        '能量': {'type': 'mul', 'value': 2},
        '安全': {'type': 'div_floor', 'value': 2},
        'neutral': {'type': 'clamp_min1', 'value': 1}
    }

def _apply_modifier(mod_rules: Dict[str, Dict[str, Any]], prev_cat: str, orig_len: int) -> Tuple[int, str]:
    rule = mod_rules.get(prev_cat, {'type': 'clamp_min1', 'value': 1})
    t = rule['type']
    v = int(rule['value'])
    eff = orig_len
    if t == 'mul':
        eff = orig_len * v
    elif t == 'div_floor':
        eff = max(1, orig_len // v)
    elif t == 'clamp_min1':
        eff = max(1, orig_len)
    note = f'修正为{eff}'
    return eff, note

def _teleport_policy_strict() -> Dict[str, Any]:
    return {
        'enabled': True,
        'consumes_step': random.random() < 0.5,
        'target': random.choice(['opposite', 'adjacent']),
        'only_outward': True,
        'enabled_by_beacon': True
    }

def _teleport_target(curr_corner: Tuple[int,int], corners: List[Tuple[int,int]]) -> Tuple[int,int]:
    idx = corners.index(curr_corner)
    next_idx = (idx + 1) % 6
    opp_idx = (idx + 3) % 6
    return corners[opp_idx], corners[next_idx]

def _random_hazard_policy() -> Dict[str, Any]:
    t = random.choice(['bounce', 'skip_next_micro', 'increase_next_step_by1'])
    return {'type': t}

def _format_rules_text(
    mod_rules: Dict[str, Dict[str, Any]],
    ring_gate_cost: int,
    consume_gate_key: bool,
    tp_policy: Dict[str, Any],
    hazard_policy: Dict[str, Any]
) -> str:
    def mod_desc(cat: str) -> str:
        t = mod_rules[cat]['type']
        v = int(mod_rules[cat]['value'])
        if t == 'mul':
            return f'{cat}设备会使下一步步长乘以{v}'
        if t == 'div_floor':
            return f'{cat}设备会使下一步步长除以{v}并向下取整，且至少为1'
        if t == 'clamp_min1':
            return f'{cat}设备不会改变下一步步长（至少为1）'
        return f'{cat}设备不会改变下一步步长'
    mods = f"{mod_desc('能量')}； {mod_desc('安全')}； {mod_desc('neutral')}。"
    ring_txt = '外圈边仅允许沿CW方向通过'
    gate_txt = f'在最外圈沿边通过时需要钥匙数不少于{ring_gate_cost}' + ('，并消耗相应数量的钥匙' if consume_gate_key else '，且不消耗钥匙')
    tgt = '对径角点' if tp_policy.get('target') == 'opposite' else '相邻角点'
    consume = '并消耗一个微步' if tp_policy.get('consumes_step', False) else '且不消耗微步'
    tp_txt = f'外圈角点具备传送功能：若下一步会越界且当前角点有信标激活，则传送到{tgt}{consume}'
    hz = hazard_policy.get('type')
    if hz == 'bounce':
        hz_txt = '危险点会让下一微步方向反向（只影响一次）'
    elif hz == 'skip_next_micro':
        hz_txt = '危险点会跳过下一微步（只影响一次）'
    else:
        hz_txt = '危险点会使下一步步长临时增加1个微步（只影响一次）'
    return f'{mods} 外圈边仅允许沿CW方向通过； {gate_txt}； {tp_txt}； {hz_txt}。'

def _simulate_sequence(
    R: int,
    start: Tuple[int,int],
    prev_cat: str,
    seq_dirs: List[str],
    seq_steps: List[int],
    labels_map: Dict[Tuple[int,int], str],
    cats_map: Dict[Tuple[int,int], str],
    tags_map: Dict[Tuple[int,int], str],
    cw_map: Dict[Tuple[int,int], Tuple[int,int]],
    corners: List[Tuple[int,int]],
    mod_rules: Dict[str, Dict[str, Any]],
    tp_policy: Dict[str, Any],
    hazard_policy: Dict[str, Any],
    ring_gate_cost: int,
    consume_gate_key: bool,
    init_keys: int = 0,
    init_beacon_on: bool = False
) -> Tuple[List[Tuple[int,int]], bool, List[int], List[str], List[str], int, bool, int, int]:
    """固定CW外圈方向仿真，返回：visited、ok、eff_steps、mod_notes、tag_notes、keys_count、beacon_on、tp_count、outer_count。"""
    curr = start
    eff_steps = []
    visited = []
    mod_notes = []
    tag_notes = []
    keys_count = init_keys
    beacon_on = init_beacon_on
    corner_set = set(corners)
    hazard_next_applied = False
    tp_count = 0
    outer_count = 0

    for i in range(len(seq_steps)):
        orig = int(seq_steps[i])
        eff, mnote = _apply_modifier(mod_rules, prev_cat, orig)
        eff_steps.append(eff)
        mod_notes.append(mnote)
        direction = seq_dirs[i]
        if direction not in DIRS:
            return visited, False, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count
        base_vec = DIRS[direction]
        remain = eff
        while remain > 0:
            vec = base_vec
            if tags_map.get(curr) == 'hazard' and not hazard_next_applied:
                htype = hazard_policy.get('type')
                if htype == 'bounce':
                    vec = (-base_vec[0], -base_vec[1])
                    hazard_next_applied = True
                elif htype == 'skip_next_micro':
                    remain -= 1
                    hazard_next_applied = True
                    continue
                elif htype == 'increase_next_step_by1':
                    remain += 1
                    hazard_next_applied = True
                else:
                    hazard_next_applied = True
            nxt = _hex_add(curr, vec)
            if _hex_dist(nxt) > R:
                if tp_policy.get('enabled', False) and (curr in corner_set):
                    if tp_policy.get('enabled_by_beacon', False) and not beacon_on:
                        return visited, False, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count
                    opp, adj = _teleport_target(curr, corners)
                    target_corner = opp if tp_policy.get('target') == 'opposite' else adj
                    curr = target_corner
                    tp_count += 1
                    if tp_policy.get('consumes_step', False):
                        remain -= 1
                        continue
                    else:
                        nxt = _hex_add(curr, vec)
                        if _hex_dist(nxt) > R:
                            return visited, False, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count
                else:
                    return visited, False, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count
            if _hex_dist(curr) == R and _hex_dist(nxt) == R:
                if cw_map.get(curr) != nxt:
                    return visited, False, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count
                outer_count += 1
                if keys_count < ring_gate_cost:
                    return visited, False, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count
                if consume_gate_key:
                    keys_count -= ring_gate_cost
            curr = nxt
            remain -= 1
            if tags_map.get(curr) == 'key':
                keys_count += 1
            if tags_map.get(curr) == 'beacon':
                beacon_on = True
        visited.append(curr)
        prev_cat = cats_map.get(curr, 'neutral')
        t = tags_map.get(curr, 'none')
        if t == 'key':
            tag_notes.append('获得钥匙')
        elif t == 'gate':
            tag_notes.append('到达门禁点')
        elif t == 'hazard':
            tag_notes.append('经过危险点')
        elif t == 'beacon':
            tag_notes.append('激活信标')
        else:
            tag_notes.append('')
        hazard_next_applied = False
    return visited, True, eff_steps, mod_notes, tag_notes, keys_count, beacon_on, tp_count, outer_count

def _format_record_text(
    dirs: List[str],
    steps: List[int],
    labels: List[str],
    cats: List[str],
    eff_steps: List[int],
    mod_notes: List[str],
    tag_notes: List[str]
) -> str:
    parts = []
    for i in range(len(dirs)):
        mod = f'（{mod_notes[i]}）' if mod_notes[i] else ''
        tag = f'[{tag_notes[i]}]' if tag_notes[i] else ''
        unit = f"{dirs[i]} {steps[i]}{mod} -> {labels[i]}({cats[i]}){tag}"
        parts.append(unit)
    return '； '.join(parts)

def _enumerate_count_same_end(
    R: int,
    start_after_record: Tuple[int,int],
    prev_cat_after_record: str,
    keys_after_record: int,
    beacon_after_record: bool,
    target_label: str,
    labels_map: Dict[Tuple[int,int], str],
    cats_map: Dict[Tuple[int,int], str],
    tags_map: Dict[Tuple[int,int], str],
    cw_map: Dict[Tuple[int,int], Tuple[int,int]],
    corners: List[Tuple[int,int]],
    mod_rules: Dict[str, Dict[str, Any]],
    tp_policy: Dict[str, Any],
    hazard_policy: Dict[str, Any],
    ring_gate_cost: int,
    consume_gate_key: bool,
    L: int
) -> int:
    # 穷举所有长度L的序列（6方向、步长固定1），计数达到 target_label 的数量
    dirs_keys = list(DIRS.keys())
    count = 0
    def dfs(idx: int, node: Tuple[int,int], prev_cat: str, keys: int, beacon: bool):
        nonlocal count
        if idx == L:
            if labels_map.get(node, '') == target_label:
                count += 1
            return
        for d in dirs_keys:
            visited, ok, _, _, _, keys2, beacon2, _, _ = _simulate_sequence(
                R, node, prev_cat, [d], [1], labels_map, cats_map, tags_map, cw_map, corners,
                mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, keys, beacon
            )
            if not ok or len(visited) == 0:
                continue
            nxt = visited[-1]
            nxt_cat = cats_map.get(nxt, 'neutral')
            dfs(idx + 1, nxt, nxt_cat, keys2, beacon2)
    dfs(0, start_after_record, prev_cat_after_record, keys_after_record, beacon_after_record)
    return count

def function_2(R: int) -> Dict[str, Any]:
    # 全局多次尝试，选择唯一终点的最终序列，并存入唯一性证书；不返回降级场景
    for _ in range(120):
        nodes = _gen_all_nodes(R)
        labels_map = _assign_labels(nodes)
        cats_map = _assign_categories(nodes, energy_ratio=random.uniform(0.05, 0.15), safety_ratio=random.uniform(0.10, 0.25))
        tags_map = _assign_tags(nodes)
        corners = _outer_corners(R)
        ring = _build_outer_ring(R)
        cw_map = _ring_cw_map(ring)
        mod_rules = _modifier_rules_restricted()
        tp_policy = _teleport_policy_strict()
        hazard_policy = _random_hazard_policy()
        ring_gate_cost = random.choice([2, 3])
        consume_gate_key = random.random() < 0.6
        rule_text = _format_rules_text(mod_rules, ring_gate_cost, consume_gate_key, tp_policy, hazard_policy)

        # 环境统计
        env_counts = {'key': 0, 'gate': 0, 'hazard': 0, 'beacon': 0}
        for n, tg in tags_map.items():
            if tg in env_counts:
                env_counts[tg] += 1
        env_text = f"钥匙点{env_counts['key']}个，门禁{env_counts['gate']}个，危险点{env_counts['hazard']}个，信标{env_counts['beacon']}个"

        # 起点选择
        eligible = [n for n in nodes if cats_map[n] in ['能量', '安全']]
        if not eligible:
            eligible = nodes[:]
        if random.random() < 0.4:
            eligible = list(set(eligible).union(set(corners)))
        start_node = random.choice(eligible)
        start_label = labels_map[start_node]
        start_cat = cats_map[start_node]

        # 生成行走记录
        rec_dirs, rec_steps, rec_labels, rec_cats = [], [], [], []
        eff_steps_seq, mod_notes_seq, tag_notes_seq = [], [], []
        curr = start_node
        prev_cat = start_cat
        keys_count = 0
        beacon_on = False

        target_len = random.randint(6, 10)
        trials = 0
        max_trials = 600
        while len(rec_dirs) < target_len and trials < max_trials:
            trials += 1
            d = random.choice(list(DIRS.keys()))
            s = random.randint(1, 3)
            visited, ok, effs, mnotes, tnotes, keys2, beacon2, _, _ = _simulate_sequence(
                R, curr, prev_cat, [d], [s], labels_map, cats_map, tags_map, cw_map, corners,
                mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, keys_count, beacon_on
            )
            if not ok:
                continue
            nxt = visited[-1]
            rec_dirs.append(d)
            rec_steps.append(s)
            eff_steps_seq.append(effs[-1])
            mod_notes_seq.append(mnotes[-1])
            tag_notes_seq.append(tnotes[-1])
            rec_labels.append(labels_map[nxt])
            rec_cats.append(cats_map[nxt])
            curr = nxt
            prev_cat = cats_map[nxt]
            keys_count = keys2
            beacon_on = beacon2

        if len(rec_dirs) == 0:
            continue

        # 记录后状态
        visited_record, ok_record, _, _, _, keys_after, beacon_after, _, _ = _simulate_sequence(
            R, start_node, start_cat, rec_dirs, rec_steps, labels_map, cats_map, tags_map, cw_map, corners,
            mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, 0, False
        )
        if not ok_record or len(visited_record) == 0:
            continue
        start_after = visited_record[-1]
        prev_cat_after = cats_map.get(start_after, 'neutral')

        # 穷举完整候选域（长度4、步长固定1）
        dirs_keys = list(DIRS.keys())
        end_counts: Dict[str, int] = {}
        end_seq_samples: Dict[str, List[Tuple[List[str], List[int], int, int]]] = {}

        for d0 in dirs_keys:
            v0, ok0, _, _, _, k0, b0, tp0, oc0 = _simulate_sequence(
                R, start_after, prev_cat_after, [d0], [1], labels_map, cats_map, tags_map, cw_map, corners,
                mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, keys_after, beacon_after
            )
            if not ok0 or len(v0) == 0:
                continue
            n0 = v0[-1]; pc0 = cats_map.get(n0, 'neutral')
            for d1 in dirs_keys:
                v1, ok1, _, _, _, k1, b1, tp1, oc1 = _simulate_sequence(
                    R, n0, pc0, [d1], [1], labels_map, cats_map, tags_map, cw_map, corners,
                    mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, k0, b0
                )
                if not ok1 or len(v1) == 0:
                    continue
                n1 = v1[-1]; pc1 = cats_map.get(n1, 'neutral')
                for d2 in dirs_keys:
                    v2, ok2, _, _, _, k2, b2, tp2, oc2 = _simulate_sequence(
                        R, n1, pc1, [d2], [1], labels_map, cats_map, tags_map, cw_map, corners,
                        mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, k1, b1
                    )
                    if not ok2 or len(v2) == 0:
                        continue
                    n2 = v2[-1]; pc2 = cats_map.get(n2, 'neutral')
                    for d3 in dirs_keys:
                        v3, ok3, _, _, _, k3, b3, tp3, oc3 = _simulate_sequence(
                            R, n2, pc2, [d3], [1], labels_map, cats_map, tags_map, cw_map, corners,
                            mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, k2, b2
                        )
                        if not ok3 or len(v3) == 0:
                            continue
                        end_node = v3[-1]
                        end_label = labels_map.get(end_node, '')
                        total_tp = tp0 + tp1 + tp2 + tp3
                        total_oc = oc0 + oc1 + oc2 + oc3
                        end_counts[end_label] = end_counts.get(end_label, 0) + 1
                        end_seq_samples.setdefault(end_label, []).append(
                            ([d0, d1, d2, d3], [1, 1, 1, 1], total_tp, total_oc)
                        )

        unique_end_labels = [el for el, cnt in end_counts.items() if cnt == 1]
        if not unique_end_labels:
            continue

        # 选择策略：优先“传送≥1且外圈沿边通过≥1”；其次“事件≥1”；最后“纯唯一”
        chosen_dirs = None
        chosen_steps = None
        chosen_end = None

        # 优先策略
        random.shuffle(unique_end_labels)
        for el in unique_end_labels:
            samples = end_seq_samples.get(el, [])
            random.shuffle(samples)
            # 第一优先：双事件
            cand = [s for s in samples if s[2] >= 1 and s[3] >= 1]
            if cand:
                dirs_final, steps_final, tp_sum, oc_sum = cand[0]
                chosen_dirs, chosen_steps, chosen_end = dirs_final, steps_final, el
                break
        # 次优策略：单事件
        if chosen_end is None:
            for el in unique_end_labels:
                samples = end_seq_samples.get(el, [])
                random.shuffle(samples)
                cand = [s for s in samples if (s[2] + s[3]) >= 1]
                if cand:
                    dirs_final, steps_final, tp_sum, oc_sum = cand[0]
                    chosen_dirs, chosen_steps, chosen_end = dirs_final, steps_final, el
                    break
        # 最后策略：纯唯一
        if chosen_end is None:
            el = unique_end_labels[0]
            dirs_final, steps_final, tp_sum, oc_sum = end_seq_samples[el][0]
            chosen_dirs, chosen_steps, chosen_end = dirs_final, steps_final, el

        # 构造文本与场景
        record_text = _format_record_text(rec_dirs, rec_steps, rec_labels, rec_cats, eff_steps_seq, mod_notes_seq, tag_notes_seq)
        final_text = '，'.join([f"{chosen_dirs[i]} {chosen_steps[i]}" for i in range(len(chosen_dirs))])
        state_text = f"当前钥匙数{keys_count}，信标{'已激活' if beacon_on else '未激活'}"

        scenario = {
            'R': R,
            'labels_map': labels_map,
            'cats_map': cats_map,
            'tags_map': tags_map,
            'start_node': start_node,
            'start_label': start_label,
            'start_category': start_cat,
            'record': {
                'dirs': rec_dirs,
                'steps': rec_steps,
                'labels': rec_labels,
                'categories': rec_cats,
                'text': record_text
            },
            'final': {
                'dirs': chosen_dirs,
                'steps': chosen_steps,
                'text': final_text
            },
            'cw_map': cw_map,
            'corners': corners,
            'mod_rules': mod_rules,
            'tp_policy': tp_policy,
            'hazard_policy': hazard_policy,
            'ring_gate_cost': ring_gate_cost,
            'consume_gate_key': consume_gate_key,
            'rule_text': rule_text,
            'env_text': env_text,
            'state_text': state_text,
            # 唯一性证书
            'cert_end_label': chosen_end,
            'cert_count': 1,
            'cert_len': 4
        }
        return scenario

    # 若仍失败（极低概率），继续重试由上层框架处理
    raise RuntimeError('Failed to generate a unique terminal sequence after exhaustive trials.')

def function_1(scenario: Dict[str, Any]) -> str:
    R = scenario['R']
    labels_map = scenario['labels_map']
    cats_map = scenario['cats_map']
    tags_map = scenario['tags_map']
    start = scenario['start_node']
    start_cat = scenario['start_category']
    rec_dirs = scenario['record']['dirs']
    rec_steps = scenario['record']['steps']
    rec_labels = scenario['record']['labels']
    rec_cats = scenario['record']['categories']
    final_dirs = scenario['final']['dirs']
    final_steps = scenario['final']['steps']
    cw_map = scenario['cw_map']
    corners = scenario['corners']
    mod_rules = scenario['mod_rules']
    tp_policy = scenario['tp_policy']
    hazard_policy = scenario['hazard_policy']
    ring_gate_cost = scenario['ring_gate_cost']
    consume_gate_key = scenario['consume_gate_key']

    visited, ok, _, _, _, keys_count, beacon_on, _, _ = _simulate_sequence(
        R, start, start_cat, rec_dirs, rec_steps, labels_map, cats_map, tags_map, cw_map, corners,
        mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key
    )
    if not ok or len(visited) != len(rec_labels):
        return 'unknown'
    for i, node in enumerate(visited):
        if labels_map.get(node) != rec_labels[i] or cats_map.get(node) != rec_cats[i]:
            return 'unknown'

    curr = visited[-1] if visited else start
    prev_cat = cats_map.get(curr, start_cat)
    visited2, ok2, _, _, _, _, _, _, _ = _simulate_sequence(
        R, curr, prev_cat, final_dirs, final_steps, labels_map, cats_map, tags_map, cw_map, corners,
        mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, keys_count, beacon_on
    )
    if not ok2 or len(visited2) == 0:
        return 'unknown'
    end_node = visited2[-1]
    return labels_map.get(end_node, 'unknown')

def function_3(scenario: Dict[str, Any], ans: str) -> bool:
    # 证书优先：若场景存有 cert_end_label 且计数=1 且长度=4，直接比对答案
    if not isinstance(ans, str) or len(ans) == 0:
        return False
    cert_label = scenario.get('cert_end_label', None)
    cert_count = scenario.get('cert_count', None)
    cert_len = scenario.get('cert_len', None)
    if cert_label is not None and cert_count == 1 and cert_len == 4:
        return ans == cert_label

    # 回退：枚举验证（与生成一致：长度4、步长固定1）
    start_time = time.time()
    time_limit = 180.0

    R = scenario['R']
    labels_map = scenario['labels_map']
    cats_map = scenario['cats_map']
    tags_map = scenario['tags_map']
    start = scenario['start_node']
    start_cat = scenario['start_category']
    rec_dirs = scenario['record']['dirs']
    rec_steps = scenario['record']['steps']
    cw_map = scenario['cw_map']
    corners = scenario['corners']
    mod_rules = scenario['mod_rules']
    tp_policy = scenario['tp_policy']
    hazard_policy = scenario['hazard_policy']
    ring_gate_cost = scenario['ring_gate_cost']
    consume_gate_key = scenario['consume_gate_key']

    visited, ok, _, _, _, keys_count, beacon_on, _, _ = _simulate_sequence(
        R, start, start_cat, rec_dirs, rec_steps, labels_map, cats_map, tags_map, cw_map, corners,
        mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key
    )
    if not ok:
        return False
    curr = visited[-1] if visited else start
    prev_cat = cats_map.get(curr, start_cat)

    final_dirs = scenario['final']['dirs']
    final_steps = scenario['final']['steps']
    if len(final_steps) != 4:
        return False
    visited2, ok2, _, _, _, keys_after, beacon_after, _, _ = _simulate_sequence(
        R, curr, prev_cat, final_dirs, final_steps, labels_map, cats_map, tags_map, cw_map, corners,
        mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, keys_count, beacon_on
    )
    if not ok2 or len(visited2) == 0:
        return False
    end_label = labels_map.get(visited2[-1], 'unknown')
    if end_label != ans:
        return False

    count = _enumerate_count_same_end(
        R, curr, prev_cat, keys_count, beacon_on, end_label, labels_map, cats_map, tags_map, cw_map, corners,
        mod_rules, tp_policy, hazard_policy, ring_gate_cost, consume_gate_key, L=4
    )
    if time.time() - start_time > time_limit:
        return False
    return count == 1