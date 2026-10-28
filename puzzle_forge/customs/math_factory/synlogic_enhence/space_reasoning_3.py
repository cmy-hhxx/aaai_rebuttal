# space_reasoning_5.py
import random
import time

# 六向轴坐标方向向量
DIR_VECTORS = {
    'E':  (1, 0),
    'NE': (1, -1),
    'NW': (0, -1),
    'W':  (-1, 0),
    'SW': (-1, 1),
    'SE': (0, 1),
}

# 方向中文名
DIR_CN = {
    'E': '东',
    'NE': '东北',
    'NW': '西北',
    'W': '西',
    'SW': '西南',
    'SE': '东南',
}

def hex_distance(q, r):
    s = -q - r
    return max(abs(q), abs(r), abs(s))

def within_ring(pos, max_ring):
    return hex_distance(pos[0], pos[1]) <= max_ring

def move_segment(pos, direction, steps):
    dq, dr = DIR_VECTORS[direction]
    return (pos[0] + dq * steps, pos[1] + dr * steps)

def move_sequence(start_pos, segments):
    q, r = start_pos
    for direction, steps in segments:
        q, r = move_segment((q, r), direction, steps)
    return (q, r)

def step_through_path(start_pos, segments):
    """按步推进路径，返回每一步到达的坐标序列（不含起点）。"""
    positions = []
    q, r = start_pos
    for d, s in segments:
        dq, dr = DIR_VECTORS[d]
        for _ in range(s):
            q += dq
            r += dr
            positions.append((q, r))
    return positions

def opposite_on_same_ring(pos):
    q, r = pos
    return (-q, -r)

def coord_to_text(coord):
    # 增强健壮性：允许 None，避免潜在渲染异常
    if coord is None:
        return '(未启用)'
    return f'({coord[0]},{coord[1]})'

def segments_to_text(segments):
    # 输入如 [('SE', 2), ('NE', 3)], 输出 '东南2步、东北3步'
    parts = []
    for d, s in segments:
        parts.append(f'{DIR_CN[d]}{s}步')
    return '、'.join(parts)

def rotation_cycle_text():
    """返回与代码一致的顺时针方向序列文本。"""
    # 顺时针序列严格使用 E -> SE -> SW -> W -> NW -> NE
    return '[东E, 东南SE, 西南SW, 西W, 西北NW, 东北NE]'

def _rand_int_from_range(closed_range):
    # closed_range 为形如 [min, max] 的 Python 列表
    lo, hi = int(closed_range[0]), int(closed_range[1])
    if lo > hi:
        lo, hi = hi, lo
    return random.randint(lo, hi)

def _random_segments(count, step_range, directions_list):
    segs = []
    for _ in range(count):
        d = random.choice(directions_list)
        s = _rand_int_from_range(step_range)
        segs.append((d, s))
    return segs

def gen_random_coord(max_ring):
    candidates = []
    for q in range(-max_ring, max_ring + 1):
        for r in range(-max_ring, max_ring + 1):
            if within_ring((q, r), max_ring):
                candidates.append((q, r))
    non_center = [c for c in candidates if c != (0, 0)]
    return random.choice(non_center if non_center else candidates)

def clockwise_direction(d):
    # 顺时针序列严格与 rotation_cycle_text 一致
    order = ['E', 'SE', 'SW', 'W', 'NW', 'NE']
    idx_map = {k: i for i, k in enumerate(order)}
    i = idx_map[d]
    return order[(i + 1) % len(order)]

def _compute_key_positions(start_coord, obs1, obs2, after_jump, max_ring):
    pos0 = start_coord
    pos1 = move_sequence(pos0, obs1)
    pos2 = move_sequence(pos1, obs2)
    pos3 = opposite_on_same_ring(pos2)
    pos4 = move_sequence(pos3, after_jump)
    return pos0, pos1, pos2, pos3, pos4

def _compute_final_pos(start_pos, final_query):
    return move_sequence(start_pos, final_query)

def _validate_distinct_positions(positions):
    return len(set(positions)) == len(positions)

def _pick_item_names(items_pool):
    pool = list(set(items_pool))
    if len(pool) < 5:
        extra = [f'化石_{i}' for i in range(5 - len(pool))]
        pool.extend(extra)
    random.shuffle(pool)
    return pool[:5]

def _final_answer_from_mapping(final_pos, max_ring, mapping):
    if not within_ring(final_pos, max_ring):
        return 'unknown'
    return mapping.get(final_pos, 'unknown')

def sum_steps(segments):
    """计算段式路径的总步数（每段的步数求和）"""
    return sum(s for d, s in segments)

def _choose_rules():
    """
    随机选择规则组合：
    - 至少2条步级规则（portal_pos3 / exit_unknown / beacon_turn）
    - 至少1条终局规则（reflect_last_even / cross_origin_reflect）
    - 总数3~5条
    - range_limit 作为附加限制，避免成为显见解（L 设置在较宽范围，最终生成时亦保证总步数不超过 L）
    """
    step_rules = ['portal_pos3', 'exit_unknown', 'beacon_turn']
    end_rules = ['reflect_last_even', 'cross_origin_reflect']

    step_cnt = random.choice([2, 3])
    end_cnt = random.choice([1, 2])
    chosen = set(random.sample(step_rules, step_cnt) + random.sample(end_rules, end_cnt))

    # 在 3~5 条之间补齐
    target_k = random.choice([3, 4, 5])
    all_rules = step_rules + end_rules + ['range_limit']
    while len(chosen) < target_k:
        cand = random.choice(all_rules)
        chosen.add(cand)

    cfg = {k: (k in chosen) for k in (step_rules + end_rules + ['range_limit'])}
    # L 取较宽松区间，减少显见解概率；真正的防显见由生成阶段“sum_steps <= L”保障
    cfg['range_limit_L'] = random.randint(10, 18)

    # 灯塔规则若启用需提供坐标，生成阶段补充
    return cfg

def rules_to_text(instance_rules):
    """将规则配置转换为中文文本，与求解引擎执行顺序一致，仅描述已激活规则。"""
    texts = []
    L = int(instance_rules.get('range_limit_L', 10))
    if instance_rules.get('portal_pos3'):
        texts.append('对径停止：最终移动过程中若到达对径节点则立即停止并在该节点观察')
    if instance_rules.get('exit_unknown'):
        texts.append('越界unknown：最终移动过程中若任一步越出最大环半径则答案为unknown')
    if instance_rules.get('beacon_turn'):
        btxt = f'灯塔坐标为{coord_to_text(instance_rules.get("beacon_coord"))}'
        cycle_txt = rotation_cycle_text()
        texts.append(f'灯塔转向：最终移动过程中若任一步到达灯塔坐标，则仅将下一步方向顺时针旋转60度（顺时针序列为{cycle_txt}）；{btxt}')
    if instance_rules.get('reflect_last_even'):
        texts.append('末段偶数反射：若最终移动最后一段步数为偶数，则将最终观察点取其关于原点的对径坐标')
    if instance_rules.get('cross_origin_reflect'):
        texts.append('穿越原点反射：若最终移动过程中任一步到达原点(0,0)，则在完成所有移动后将最终观察点取其关于原点的对径坐标')
    if instance_rules.get('range_limit'):
        texts.append(f'范围限制：若最终移动的总步数之和超过{L}则直接答案为unknown')

    if not texts:
        texts.append('按基线规则：仅五个关键坐标存在化石，其余位置为unknown')

    flow = []
    if instance_rules.get('range_limit'):
        flow.append(f'规则判定顺序说明：预检门槛先于所有步级判定（总步数超过{L}则直接unknown）')
    # 步级与终局的固定顺序说明
    flow.append('规则判定顺序说明：步级规则的触发次序为 对径停止 > 越界unknown > 灯塔转向')
    flow.append('规则判定顺序说明：终局规则的触发次序为 末段偶数反射 > 穿越原点反射')
    flow.append('最终映射：仅五个关键坐标存在化石，其余位置为unknown；若最终观察点不在最大环内则为unknown')

    return '；'.join(texts + ['执行说明：' + '；'.join(flow)])

def compute_answer_with_order(instance, step_rule_order):
    """按给定的步级规则次序执行（用于唯一性检查），其它环节顺序固定并与文本一致。"""
    max_ring = instance['max_ring']
    start_coord = instance['start_coord']
    obs1 = instance['obs1']
    obs2 = instance['obs2']
    after_jump = instance['after_jump']
    final_query = instance['final_query']
    rules = instance.get('rules', {})

    pos0, pos1, pos2, pos3, pos4 = _compute_key_positions(start_coord, obs1, obs2, after_jump, max_ring)
    mapping = {
        pos0: instance['item_names'][0],
        pos1: instance['item_names'][1],
        pos2: instance['item_names'][2],
        pos3: instance['item_names'][3],
        pos4: instance['item_names'][4],
    }

    # 预检：范围限制（先验门槛）
    if rules.get('range_limit', False):
        total_steps = sum_steps(final_query)
        if total_steps > int(rules.get('range_limit_L', 10)):
            return 'unknown'

    # 步级仿真
    pos = pos4
    rotate_next = False
    crossed_origin = False

    atom_steps = []
    for d, s in final_query:
        for _ in range(s):
            atom_steps.append(d)

    for d in atom_steps:
        if rotate_next:
            d = clockwise_direction(d)
            rotate_next = False

        dq, dr = DIR_VECTORS[d]
        pos = (pos[0] + dq, pos[1] + dr)

        for rule in step_rule_order:
            if rule == 'portal_pos3' and rules.get('portal_pos3', False):
                if pos == pos3:
                    return mapping.get(pos3, 'unknown')
            elif rule == 'exit_unknown' and rules.get('exit_unknown', False):
                if not within_ring(pos, max_ring):
                    return 'unknown'
            elif rule == 'beacon_turn' and rules.get('beacon_turn', False):
                beacon = rules.get('beacon_coord', None)
                if beacon is not None and pos == beacon:
                    rotate_next = True

        if rules.get('cross_origin_reflect', False):
            if pos == (0, 0):
                crossed_origin = True

    # 终局规则
    final_pos = pos
    if rules.get('reflect_last_even', False):
        if len(final_query) > 0:
            last_steps = final_query[-1][1]
            if (last_steps % 2) == 0:
                final_pos = opposite_on_same_ring(final_pos)

    if rules.get('cross_origin_reflect', False):
        if crossed_origin:
            final_pos = opposite_on_same_ring(final_pos)

    return _final_answer_from_mapping(final_pos, max_ring, mapping)

def compute_answer_with_rules(instance):
    """固定执行顺序，作为最终答案计算：预检范围限制 -> 步级顺序(对径停止>越界unknown>灯塔转向) -> 终局顺序(末段偶数反射>穿越原点反射) -> 映射。"""
    step_order = ['portal_pos3', 'exit_unknown', 'beacon_turn']
    return compute_answer_with_order(instance, step_order)

def instance_answer(instance):
    return compute_answer_with_rules(instance)

def verify_instance_unique(instance, max_seconds=170.0):
    """唯一解验证：对所有步级规则次序排列，答案必须一致；限时保证。"""
    start_time = time.time()
    rules = instance.get('rules', {})
    step_rules = []
    if rules.get('portal_pos3', False):
        step_rules.append('portal_pos3')
    if rules.get('exit_unknown', False):
        step_rules.append('exit_unknown')
    if rules.get('beacon_turn', False):
        step_rules.append('beacon_turn')

    if len(step_rules) <= 1:
        return True

    def perms(lst):
        if len(lst) <= 1:
            return [lst[:]]
        res = []
        for i in range(len(lst)):
            first = lst[i]
            rest = lst[:i] + lst[i+1:]
            for p in perms(rest):
                res.append([first] + p)
        return res

    reference = None
    for order in perms(step_rules):
        if time.time() - start_time > max_seconds:
            return False
        ans = compute_answer_with_order(instance, order)
        if reference is None:
            reference = ans
        else:
            if ans != reference:
                return False
    return True

def _choose_beacon_coord(candidates):
    random.shuffle(candidates)
    return candidates[0] if candidates else None

def gen_hex_instance(
    ring_range,
    seg_cnt_obs1_range,
    seg_cnt_obs2_range,
    seg_cnt_final_range,
    step_obs_range,
    step_final_range,
    after_jump_steps_range,
    directions_list,
    items_pool,
    unknown_prob=0.35,
    ensure_distinct=True
):
    """
    生成单个六向坐标题实例（正向生成 + 规则随机化 + 唯一性验证）：
    - 采样 max_ring, start_coord
    - 采样 obs1, obs2, 对径跳转（after_jump）与 final_query
    - 随机启用 3~5 条规则并生成说明（至少2条步级 + 至少1条终局）
    - 保证五处化石位置在环内且两两不同（如 ensure_distinct=True）
    - unknown 的生成尽量由越界、对径中止、反射与落点非关键造成，而非范围限制
    - 唯一性验证：对所有步级规则次序进行答案一致性检查
    """
    MAX_ATTEMPTS = 6000

    directions_list = [d for d in directions_list if d in DIR_VECTORS]
    if not directions_list:
        directions_list = ['E', 'NE', 'NW', 'W', 'SW', 'SE']

    for _ in range(MAX_ATTEMPTS):
        max_ring = _rand_int_from_range(ring_range)
        start_coord = gen_random_coord(max_ring)

        c1 = _rand_int_from_range(seg_cnt_obs1_range)
        c2 = _rand_int_from_range(seg_cnt_obs2_range)

        inner_attempt = 0
        while True:
            inner_attempt += 1
            if inner_attempt > 600:
                break
            obs1 = _random_segments(c1, step_obs_range, directions_list)
            pos1 = move_sequence(start_coord, obs1)
            if within_ring(pos1, max_ring) and ((not ensure_distinct) or (pos1 != start_coord and pos1 != (0, 0))):
                break
        else:
            continue

        inner_attempt = 0
        while True:
            inner_attempt += 1
            if inner_attempt > 600:
                break
            obs2 = _random_segments(c2, step_obs_range, directions_list)
            pos2 = move_sequence(pos1, obs2)
            if within_ring(pos2, max_ring) and ((not ensure_distinct) or (pos2 not in {start_coord, pos1} and pos2 != (0, 0))):
                break
        else:
            continue

        pos3 = opposite_on_same_ring(pos2)

        inner_attempt = 0
        while True:
            inner_attempt += 1
            if inner_attempt > 600:
                break
            after_jump = [(random.choice(directions_list), _rand_int_from_range(after_jump_steps_range))]
            pos4 = move_sequence(pos3, after_jump)
            if within_ring(pos4, max_ring) and ((not ensure_distinct) or (pos4 not in {start_coord, pos1, pos2, pos3} and pos4 != (0, 0))):
                break
        else:
            continue

        if ensure_distinct:
            if not _validate_distinct_positions([start_coord, pos1, pos2, pos3, pos4]):
                continue

        item_names = _pick_item_names(items_pool)

        # 选择规则，补充灯塔坐标
        rules = _choose_rules()
        if rules.get('beacon_turn', False):
            candidates = [pos1, pos2, pos3]
            rules['beacon_coord'] = _choose_beacon_coord(candidates)
        else:
            rules['beacon_coord'] = None

        c_final = _rand_int_from_range(seg_cnt_final_range)
        want_unknown = random.random() < float(unknown_prob)

        # 采样最终路径，若启用范围限制则总步数必须 <= L，避免显见解
        inner_attempt = 0
        chosen_final = None
        L = int(rules.get('range_limit_L', 10))
        while True:
            inner_attempt += 1
            if inner_attempt > 2200:
                if chosen_final is None:
                    chosen_final = _random_segments(c_final, step_final_range, directions_list)
                break
            candidate = _random_segments(c_final, step_final_range, directions_list)
            if rules.get('range_limit', False):
                if sum_steps(candidate) > L:
                    continue  # 避免范围限制造成显见unknown

            tmp_instance = {
                'max_ring': max_ring,
                'start_coord': start_coord,
                'obs1': obs1,
                'obs2': obs2,
                'after_jump': after_jump,
                'final_query': candidate,
                'item_names': item_names,
                'rules': rules,
            }
            ans = compute_answer_with_rules(tmp_instance)
            if want_unknown and ans == 'unknown':
                chosen_final = candidate
                break
            if (not want_unknown) and ans != 'unknown':
                chosen_final = candidate
                break

        if chosen_final is None:
            continue

        final_query = chosen_final

        instance = {
            'max_ring': max_ring,
            'start_coord': start_coord,
            'obs1': obs1,
            'obs2': obs2,
            'after_jump': after_jump,
            'final_query': final_query,
            'item_names': item_names,
            'rules': rules,
        }

        pos0, p1, p2, p3, p4 = _compute_key_positions(start_coord, obs1, obs2, after_jump, max_ring)
        if ensure_distinct and not _validate_distinct_positions([pos0, p1, p2, p3, p4]):
            continue
        if not all(within_ring(p, max_ring) for p in [pos0, p1, p2, p3, p4]):
            continue

        if not verify_instance_unique(instance, max_seconds=170.0):
            continue

        instance['answer'] = compute_answer_with_rules(instance)
        return instance

    # fallback（不暴露给题干任何内部信息）
    fallback_ring = 6
    fallback_start = (1, -1)
    fallback_obs1 = [('E', 2), ('NE', 1)]
    fallback_obs2 = [('W', 1), ('SE', 1)]
    fallback_after = [('SW', 2)]
    fallback_final = [('NE', 3), ('W', 1), ('SE', 1)]
    items = _pick_item_names(['菊石','树化石','鱼化石','螺类化石','恐龙牙齿化石'])
    rules = {
        'portal_pos3': True,
        'exit_unknown': True,
        'range_limit': True,
        'reflect_last_even': True,  # 提升终局规则参与度
        'beacon_turn': True,
        'cross_origin_reflect': False,
        'range_limit_L': 14,
        'beacon_coord': (0, 0),
    }
    inst = {
        'max_ring': fallback_ring,
        'start_coord': fallback_start,
        'obs1': fallback_obs1,
        'obs2': fallback_obs2,
        'after_jump': fallback_after,
        'final_query': fallback_final,
        'item_names': items,
        'rules': rules,
    }
    try:
        if verify_instance_unique(inst, max_seconds=5.0):
            inst['answer'] = compute_answer_with_rules(inst)
        else:
            inst['answer'] = compute_answer_with_rules(inst)
    except Exception:
        inst['answer'] = compute_answer_with_rules(inst)
    return inst