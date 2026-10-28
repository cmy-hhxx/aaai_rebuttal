# time_sequence_0.py
from typing import List, Tuple, Dict, Any, Optional
import random

# -----------------------------
# Basic time helpers
# -----------------------------
def _to_minutes(hm: str) -> int:
    h, m = hm.strip().split(':')
    return int(h) * 60 + int(m)

def _to_hm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f'{h:02d}:{m:02d}'

def _parse_interval(s: str) -> Tuple[int, int]:
    parts = s.split('-')
    if len(parts) != 2:
        raise ValueError(f'Bad interval: {s}')
    start = _to_minutes(parts[0].strip())
    end = _to_minutes(parts[1].strip())
    if end < start:
        raise ValueError(f'End before start: {s}')
    return start, end

def _interval_str(s: int, e: int) -> str:
    return f'{_to_hm(s)} - {_to_hm(e)}'

def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ms, me = merged[-1]
        if s <= me:
            merged[-1] = (ms, max(me, e))
        else:
            merged.append((s, e))
    return merged

def _clip_to_work(intervals: List[Tuple[int, int]], ws: int, we: int) -> List[Tuple[int, int]]:
    res = []
    for s, e in intervals:
        s2 = max(s, ws)
        e2 = min(e, we)
        if s2 < e2:
            res.append((s2, e2))
    return _merge_intervals(res)

def _complement_busy_to_free(busy: List[Tuple[int, int]], ws: int, we: int) -> List[Tuple[int, int]]:
    busy = _clip_to_work(_merge_intervals(busy), ws, we)
    free = []
    cur = ws
    for s, e in busy:
        if cur < s:
            free.append((cur, s))
        cur = max(cur, e)
    if cur < we:
        free.append((cur, we))
    return free

def _intersect_two(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    ia = ib = 0
    res = []
    while ia < len(a) and ib < len(b):
        s1, e1 = a[ia]
        s2, e2 = b[ib]
        s = max(s1, s2)
        e = min(e1, e2)
        if s < e:
            res.append((s, e))
        if e1 < e2:
            ia += 1
        else:
            ib += 1
    return res

def _intervals_from_strings(strings: List[str]) -> List[Tuple[int, int]]:
    return [_parse_interval(s) for s in strings]

def _drop_small_busy(busy: List[Tuple[int, int]], threshold: int) -> List[Tuple[int, int]]:
    # Remove busy intervals with length <= threshold minutes
    return [(s, e) for s, e in busy if (e - s) > threshold]

def _evict_one_smallest_busy(busy: List[Tuple[int, int]], limit: int) -> List[Tuple[int, int]]:
    # Drop at most one smallest busy interval whose length <= limit
    cand = [(e - s, i) for i, (s, e) in enumerate(busy) if (e - s) <= limit]
    if not cand:
        return busy
    cand.sort()
    _, idx = cand[0]
    return [it for j, it in enumerate(busy) if j != idx]

def _subtract_block(intervals: List[Tuple[int, int]], block: Tuple[int, int]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    bs, be = block
    res: List[Tuple[int, int]] = []
    for s, e in intervals:
        # no overlap
        if e <= bs or s >= be:
            res.append((s, e))
            continue
        # overlap: cut
        if s < bs:
            res.append((s, bs))
        if e > be:
            res.append((be, e))
    return _merge_intervals([(s, e) for s, e in res if s < e])

def _day_free_from_schedule(day_item: Dict[str, Any], ws: int, we: int, drop_small_threshold: int = None) -> List[Tuple[int, int]]:
    mode = day_item['type']
    intervals = _intervals_from_strings(day_item['intervals'])
    if mode == 'free':
        return _clip_to_work(_merge_intervals(intervals), ws, we)
    elif mode == 'busy':
        if drop_small_threshold is not None:
            intervals = _drop_small_busy(intervals, drop_small_threshold)
        return _complement_busy_to_free(intervals, ws, we)
    else:
        raise ValueError(f'Unknown mode: {mode}')

def _person_free_with_mode(day_item: Dict[str, Any],
                           ws: int,
                           we: int,
                           name: str,
                           clearer_name: str,
                           clearance_mode: str,
                           single_threshold: int,
                           per_day_clear_limit: Optional[int]) -> List[Tuple[int, int]]:
    mode = day_item['type']
    intervals = _intervals_from_strings(day_item['intervals'])
    if mode == 'free':
        return _clip_to_work(_merge_intervals(intervals), ws, we)
    # busy
    if clearance_mode == 'single_clearer_threshold':
        drop_thr = single_threshold if name == clearer_name else None
        if drop_thr is not None:
            intervals = _drop_small_busy(intervals, drop_thr)
    elif clearance_mode == 'everyone_one_small':
        if per_day_clear_limit is not None:
            intervals = _evict_one_smallest_busy(intervals, per_day_clear_limit)
    # fallback: no clearance changes
    return _complement_busy_to_free(intervals, ws, we)

def _is_covered(free_list: List[Tuple[int, int]], s: int, e: int) -> bool:
    # check if [s,e) is fully covered by union of free intervals
    if s >= e:
        return True
    for fs, fe in free_list:
        if s >= fs and e <= fe:
            return True
    return False

def _shrink_free_for_buffer(free_list: List[Tuple[int, int]], before: int, after: int) -> List[Tuple[int, int]]:
    # shrink free intervals by before at start and after at end
    res = []
    for s, e in free_list:
        s2 = s + before
        e2 = e - after
        if s2 < e2:
            res.append((s2, e2))
    return _merge_intervals(res)

# -----------------------------
# Custom operators for YAML: generation
# -----------------------------
def gen_days() -> List[str]:
    return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

def gen_work_bounds() -> Dict[str, str]:
    start_hour = random.choice([8, 9, 10])
    end_hour = random.choice([16, 17, 18, 19])
    if end_hour <= start_hour + 6:
        end_hour = start_hour + 7
    return {'start': f'{start_hour:02d}:00', 'end': f'{end_hour:02d}:00'}

def gen_people(n: int) -> List[str]:
    return [f'A{i+1}' for i in range(n)]

def pick_step() -> int:
    return random.choice([15, 30, 60])

def pick_min_duration(work_bounds: Dict[str, str], step_minutes: int) -> int:
    ws = _to_minutes(work_bounds['start'])
    we = _to_minutes(work_bounds['end'])
    span = we - ws
    upper = max(step_minutes, min(180, span // 2))
    val = random.randint(step_minutes // 5, upper // 5) * 5
    return max(step_minutes, val)

def pick_clearance_threshold() -> int:
    return random.choice([20, 25, 30, 35, 40])

def pick_clearer_index(p_num: int) -> int:
    return random.randint(0, p_num - 1)

def join_names(names: List[str]) -> str:
    return ', '.join(names)

def join_days(days: List[str]) -> str:
    return ', '.join(days)

def pick_buffers() -> Dict[str, int]:
    # symmetric buffers to make reasoning clean but nontrivial
    val = random.choice([5, 10, 15])
    return {'before': val, 'after': val}

def _random_no_start_zones(ws: int, we: int) -> List[str]:
    zones = []
    if random.random() < 0.5:
        count = random.choice([1, 2])
        for _ in range(count):
            s = random.randint(ws, max(ws, we - 45))
            e = min(we, s + random.choice([10, 15, 20]))
            zones.append(_interval_str(s, e))
    return zones

def _build_feasible_schedules(names: List[str],
                              days: List[str],
                              work_start: str,
                              work_end: str,
                              policy_pack: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    极端情况下的保底构造：所有允许工作日人人全天空闲（'free' 模式），
    其他规则如午休、结束前限制、起始禁区、指定不可用段等通过全局裁剪生效。
    """
    schedules: Dict[str, Dict[str, Dict[str, Any]]] = {}
    allowed_days = policy_pack.get('allowed_days', days)
    for name in names:
        person_sched: Dict[str, Dict[str, Any]] = {}
        for d in days:
            if d in allowed_days:
                person_sched[d] = {'type': 'free', 'intervals': [f'{work_start} - {work_end}']}
            else:
                person_sched[d] = {'type': 'busy', 'intervals': []}
        schedules[name] = person_sched
    return schedules

def _earliest_enumerated_start(ws: int, anchor: str, step_len: int, s_effective: int) -> int:
    # s_effective 已包含缓冲要求：即起点必须 >= ws + buffer_before
    if anchor == 'workstart':
        def next_grid_from(x):
            delta = (x - ws) % step_len
            return x if delta == 0 else x + (step_len - delta)
        return next_grid_from(s_effective)
    else:
        return ((s_effective + step_len - 1) // step_len) * step_len

def gen_policy_pack_v2(days: List[str],
                       work_start: str,
                       work_end: str,
                       step_minutes: int,
                       names: List[str],
                       min_duration: int) -> Dict[str, Any]:
    """
    生成策略包v2，并基于min_duration与缓冲进行可行性保障：
      - must_end_by 在可能开启时，确保不早于“最早可枚举起点 + min_duration”
      - 若整体策略仍不可行，按序放松：取消must_end_by -> 取消午间禁开 -> 缓冲降到5 -> 清空起始禁区 ->
        对齐统一为workstart、步长缩放为1、allowed_days扩展为全部工作日
      - 最终硬兜底：若依然不可行，统一取消 must_end_by 与午间禁开、清空起始禁区、缓冲置0、对齐workstart、步长1、允许全部工作日；
        如仍不可行，移除 veto_block
    """
    ws = _to_minutes(work_start)
    we = _to_minutes(work_end)

    # allowed days: ensure >= 2 days
    if len(days) <= 2 or random.random() < 0.6:
        allowed_days = list(days)
    else:
        k = random.randint(max(2, len(days) - 2), len(days) - 1)
        allowed_days = sorted(random.sample(days, k))

    # base grid anchor
    grid_anchor = random.choice(['absolute', 'workstart'])

    # per-day anchor overrides
    day_anchor_map: Dict[str, str] = {}
    for d in days:
        if random.random() < 0.35:
            day_anchor_map[d] = 'workstart' if grid_anchor == 'absolute' else 'absolute'
        else:
            day_anchor_map[d] = grid_anchor

    # per-day step scaling
    step_scale_map: Dict[str, int] = {}
    for d in days:
        step_scale_map[d] = random.choice([1, 1, 2, 2, 3])

    # buffers first (用于 must_end_by 可行性计算)
    buf = pick_buffers()
    buffer_before = buf['before']
    buffer_after = buf['after']

    # clearance mode
    if random.random() < 0.6:
        clearance_mode = 'single_clearer_threshold'
        per_day_clear_limit = None
    else:
        clearance_mode = 'everyone_one_small'
        per_day_clear_limit = random.choice([10, 15, 20])

    # lunch block
    lunch_block = None
    if random.random() < 0.5:
        lunch_block = random.choice(['12:00 - 13:00', '12:30 - 13:00'])

    # must end by: ensure viability vs earliest enumerated start + min_duration
    must_end_by = None
    if random.random() < 0.5:
        earliest_needed_end_list: List[int] = []
        for d in allowed_days:
            step_len = step_minutes * step_scale_map.get(d, 1)
            anchor = day_anchor_map.get(d, grid_anchor)
            s_effective = max(ws, ws + buffer_before)
            t0 = _earliest_enumerated_start(ws, anchor, step_len, s_effective)
            earliest_needed_end_list.append(t0 + min_duration)
        if earliest_needed_end_list:
            min_required_end = min(earliest_needed_end_list)
            low = min_required_end + 10
            high = we
            if low < high:
                latest = random.randint(low // 5, high // 5) * 5
                latest = max(latest, ws + step_minutes * 2)
                must_end_by = _to_hm(latest) if latest <= we else None

    # veto person and block
    veto_person = random.choice(names)
    vb_candidates = [('09:30', '10:00'), ('10:30', '11:00'), ('15:00', '15:30'), ('16:00', '16:30')]
    vb = random.choice(vb_candidates)
    veto_block = f'{vb[0]} - {vb[1]}'

    # start forbidden zones (global)
    no_start_zones = _random_no_start_zones(ws, we)

    policy_pack: Dict[str, Any] = {
        'grid_anchor': grid_anchor,
        'day_anchor_map': day_anchor_map,
        'step_scale_map': step_scale_map,
        'allowed_days': allowed_days,
        'clearance_mode': clearance_mode,
        'per_day_clear_limit': per_day_clear_limit,
        'lunch_block': lunch_block,
        'must_end_by': must_end_by,
        'buffer_before': buffer_before,
        'buffer_after': buffer_after,
        'veto_person': veto_person,
        'veto_block': veto_block,
        'no_start_zones': no_start_zones
    }

    # 可行性预检查并按序放松
    schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
    r_probe = compute_max_and_count_v3(
        schedules=schedules_probe,
        names=names,
        days=days,
        work_start=work_start,
        work_end=work_end,
        step_minutes=step_minutes,
        min_duration=min_duration,
        policy_pack=policy_pack,
        clearer_index=0,  # 探测用，不影响全空闲
        clearance_threshold=30
    )
    if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
        # 1) 取消must_end_by
        if policy_pack.get('must_end_by') is not None:
            policy_pack['must_end_by'] = None
        schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
        r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)

    if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
        # 2) 取消午间禁开
        policy_pack['lunch_block'] = None
        schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
        r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)

    if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
        # 3) 缓冲降到5
        policy_pack['buffer_before'] = 5
        policy_pack['buffer_after'] = 5
        schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
        r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)

    if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
        # 4) 清空起始禁区
        policy_pack['no_start_zones'] = []
        schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
        r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)

    if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
        # 5) 对齐统一为workstart、步长缩放为1、allowed_days扩展到全部
        policy_pack['grid_anchor'] = 'workstart'
        policy_pack['day_anchor_map'] = {d: 'workstart' for d in days}
        policy_pack['step_scale_map'] = {d: 1 for d in days}
        policy_pack['allowed_days'] = list(days)
        schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
        r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)

    # 硬兜底
    if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
        policy_pack['must_end_by'] = None
        policy_pack['lunch_block'] = None
        policy_pack['no_start_zones'] = []
        policy_pack['buffer_before'] = 0
        policy_pack['buffer_after'] = 0
        policy_pack['grid_anchor'] = 'workstart'
        policy_pack['day_anchor_map'] = {d: 'workstart' for d in days}
        policy_pack['step_scale_map'] = {d: 1 for d in days}
        policy_pack['allowed_days'] = list(days)
        schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
        r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)
        if not (r_probe[0] >= min_duration and r_probe[1] >= 1):
            policy_pack['veto_block'] = None
            schedules_probe = _build_feasible_schedules(names, days, work_start, work_end, policy_pack)
            r_probe = compute_max_and_count_v3(schedules_probe, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, 0, 30)

    return policy_pack

def render_rules(policy_pack: Dict[str, Any],
                 step_minutes: int,
                 min_duration: int,
                 clearer_name: str,
                 clearance_threshold: int,
                 work_start: str,
                 work_end: str) -> str:
    # Kept for backward compatibility (not used by YAML)
    return ''

def render_rules_v2(policy_pack: Dict[str, Any],
                    step_minutes: int,
                    min_duration: int,
                    clearer_name: str,
                    clearance_threshold: int,
                    work_start: str,
                    work_end: str) -> str:
    lines: List[str] = []
    # 时间窗口
    if policy_pack.get('must_end_by'):
        lines.append(f'会议时间窗口为本地时间{work_start}至{work_end}，且需在{policy_pack["must_end_by"]}之前结束。')
    else:
        lines.append(f'会议时间窗口为本地时间{work_start}至{work_end}。')
    # 对齐与步长 逐日说明
    dam = policy_pack.get('day_anchor_map', {})
    ssm = policy_pack.get('step_scale_map', {})
    anchor_groups: Dict[Tuple[str, int], List[str]] = {}
    for d, anc in dam.items():
        scale = ssm.get(d, 1)
        anchor_groups.setdefault((anc, scale), []).append(d)
    for (anc, scale), dlist in anchor_groups.items():
        step_len = step_minutes * scale
        if anc == 'workstart':
            lines.append(f'{", ".join(dlist)}使用与工作起始时间对齐的起点规则，步长为{step_len}分钟。')
        else:
            lines.append(f'{", ".join(dlist)}使用与绝对时间对齐的起点规则，步长为{step_len}分钟。')
    # 最短时长
    lines.append(f'会议至少持续{min_duration}分钟。')
    # 可开会日
    adays = policy_pack.get('allowed_days', [])
    if adays:
        lines.append(f'仅可在如下工作日安排会议：{", ".join(adays)}。')
    # 清除/忽略规则
    if policy_pack.get('clearance_mode') == 'single_clearer_threshold':
        lines.append(f'仅{clearer_name}可清除其忙碌片段中长度不超过{clearance_threshold}分钟的片段，其他人不得清除任何忙碌片段。')
    else:
        lim = policy_pack.get('per_day_clear_limit', 15)
        lines.append(f'每人每天可忽略至多1段不超过{lim}分钟的忙碌片段（仅限一段，更长片段不可忽略）。')
    # 午间禁开
    if policy_pack.get('lunch_block'):
        lines.append(f'在{policy_pack["lunch_block"]}期间不得安排会议，该时间段不可被清除或忽略。')
    # 缓冲时间
    bb = policy_pack.get('buffer_before', 0)
    ba = policy_pack.get('buffer_after', 0)
    if bb or ba:
        lines.append(f'每位与会者需在会议开始前预留{bb}分钟缓冲、结束后预留{ba}分钟缓冲（缓冲时间同样视为占用时间）。')
    # 起始禁区
    nz = policy_pack.get('no_start_zones', [])
    if nz:
        lines.append(f'会议开始时间不得落在如下起始禁区内：{", ".join(nz)}。')
    # 指定人员固定不可用时段
    if policy_pack.get('veto_person') and policy_pack.get('veto_block'):
        lines.append(f'{policy_pack["veto_person"]}在每日的{policy_pack["veto_block"]}期间固定无法参加，该时段不可被清除或忽略。')
    return '\n'.join(lines)

def _random_busy_outside(ws: int, we: int, avoid: Tuple[int, int], count_range=(1, 3)) -> List[Tuple[int, int]]:
    cnt = random.randint(count_range[0], count_range[1])
    res: List[Tuple[int, int]] = []
    for _ in range(cnt):
        side = random.choice(['before', 'after'])
        if side == 'before':
            latest_start = min(we - 10, avoid[0] - 10)
            earliest_start = ws
            if latest_start < earliest_start:
                continue
            s = random.randint(earliest_start, latest_start)
            e_lower = s + 10
            e_upper = min(we, avoid[0] - 1)
            if e_upper < e_lower:
                continue
            e = random.randint(e_lower, e_upper)
            if e > ws and s < avoid[0] and s < e:
                res.append((max(ws, s), min(avoid[0], e)))
        else:
            earliest_start = max(avoid[1] + 5, ws)
            latest_start = we - 10
            if latest_start < earliest_start:
                continue
            s = random.randint(earliest_start, latest_start)
            e_lower = s + 10
            e_upper = we
            if e_upper < e_lower:
                continue
            e = random.randint(e_lower, e_upper)
            if s < we and e > avoid[1] and s < e:
                res.append((max(avoid[1], s), min(we, e)))
    return _clip_to_work(_merge_intervals(res), ws, we)

def _random_free_with_core(ws: int, we: int, core: Tuple[int, int], extra_range=(0, 2)) -> List[Tuple[int, int]]:
    res = [core]
    extra = random.randint(extra_range[0], extra_range[1])
    for _ in range(extra):
        s = random.randint(ws, we - 30) if we - ws >= 30 else ws
        e_min = min(we, s + 10)
        e_max = we
        if e_max > e_min:
            e = random.randint(e_min, e_max)
            res.append((s, e))
    return _clip_to_work(_merge_intervals(res), ws, we)

# -----------------------------
# 保底构造：确保可行性的确定性日程
# -----------------------------
def gen_schedules(names: List[str],
                  days: List[str],
                  work_start: str,
                  work_end: str,
                  step_minutes: int,
                  min_duration: int,
                  clearer_index: int,
                  clearance_threshold: int,
                  target_count: int,
                  policy_pack: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    反向生成日程并结合策略进行可行性与唯一性验证：
      - 产生若干天具备较大交集的核心窗口
      - 注入可清除的小忙碌段与随机忙碌/空闲
      - 生成后用双路径评估 若不可行或评估不一致则重试
      - 若多次失败使用保底构造（allowed_days 全空闲）并确保在原策略下可行
    返回: schedules[person][day] = {'type': 'free'|'busy', 'intervals': ['HH:MM - HH:MM', ...]}
    """
    attempts = 300
    ws = _to_minutes(work_start)
    we = _to_minutes(work_end)
    names_local = list(names)
    clearer_name = names[clearer_index]

    for _try in range(attempts):
        span = we - ws
        Lmin = max(min_duration + step_minutes, min_duration + 5)
        Lmax_upper = min(span - step_minutes, 240)
        if Lmax_upper < Lmin:
            Lmax_upper = Lmin
        Lmax = random.randint(Lmin // 5, Lmax_upper // 5) * 5

        tdays = random.sample(days, min(target_count, len(days)))
        core_by_day: Dict[str, Tuple[int, int]] = {}
        base_anchor = policy_pack.get('grid_anchor', 'absolute')

        for d in tdays:
            if base_anchor == 'workstart':
                low = ws
                high = max(ws, we - Lmax)
                if high < low:
                    high = low
                def next_grid_from(x):
                    delta = (x - ws) % step_minutes
                    return x if delta == 0 else x + (step_minutes - delta)
                t0 = next_grid_from(low)
                if t0 > high:
                    t0 = low
                t = random.randint(t0 // step_minutes, max(t0 // step_minutes, high // step_minutes)) * step_minutes
            else:
                low = ws
                high = max(ws, we - Lmax)
                if high < low:
                    high = low
                t = random.randint(low // step_minutes, high // step_minutes) * step_minutes
            core_by_day[d] = (t, min(we, t + Lmax))

        other_days = [d for d in days if d not in core_by_day]
        small_by_day: Dict[str, Tuple[int, int]] = {}
        for d in other_days:
            if random.random() < 0.5:
                Lsmall_upper = max(min_duration, Lmax - step_minutes)
                Lsmall_lower = min_duration
                if Lsmall_upper < Lsmall_lower:
                    Lsmall_upper = Lsmall_lower
                Ls = random.randint(Lsmall_lower // 5, Lsmall_upper // 5) * 5
                grid_first_abs = ws
                grid_last_abs = max(ws, we - Ls)
                if grid_last_abs < grid_first_abs:
                    grid_last_abs = grid_first_abs
                t = random.randint(grid_first_abs // step_minutes, grid_last_abs // step_minutes) * step_minutes
                small_by_day[d] = (t, min(we, t + Ls))

        schedules: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for name in names_local:
            person_sched: Dict[str, Dict[str, Any]] = {}
            for d in days:
                if d in core_by_day:
                    core = core_by_day[d]
                    if name == clearer_name and random.random() < 0.8:
                        blocks = []
                        nb = random.randint(1, 2)
                        for _ in range(nb):
                            length = random.randint(10, clearance_threshold)
                            start_latest = max(core[0], core[1] - length)
                            if start_latest < core[0]:
                                start_latest = core[0]
                            s = random.randint(core[0], start_latest)
                            e = s + length
                            blocks.append((s, e))
                        blocks += _random_busy_outside(ws, we, core, count_range=(1, 3))
                        blocks = _clip_to_work(_merge_intervals(blocks), ws, we)
                        intervals = [_interval_str(s, e) for s, e in blocks]
                        person_sched[d] = {'type': 'busy', 'intervals': intervals}
                    else:
                        if random.random() < 0.6:
                            free_ints = _random_free_with_core(ws, we, core, extra_range=(0, 2))
                            intervals = [_interval_str(s, e) for s, e in free_ints]
                            person_sched[d] = {'type': 'free', 'intervals': intervals}
                        else:
                            busy_ints = _random_busy_outside(ws, we, core, count_range=(1, 3))
                            intervals = [_interval_str(s, e) for s, e in busy_ints]
                            person_sched[d] = {'type': 'busy', 'intervals': intervals}
                else:
                    if d in small_by_day:
                        sc = small_by_day[d]
                        if random.random() < 0.5:
                            free_ints = _random_free_with_core(ws, we, sc, extra_range=(0, 1))
                            intervals = [_interval_str(s, e) for s, e in free_ints]
                            person_sched[d] = {'type': 'free', 'intervals': intervals}
                        else:
                            busy_ints = _random_busy_outside(ws, we, sc, count_range=(1, 2))
                            intervals = [_interval_str(s, e) for s, e in busy_ints]
                            person_sched[d] = {'type': 'busy', 'intervals': intervals}
                    else:
                        if random.random() < 0.5:
                            bcnt = random.randint(2, 4)
                            blocks = []
                            for _ in range(bcnt):
                                if we - ws < 20:
                                    continue
                                s = random.randint(ws, max(ws, we - 20))
                                e_min = min(we, s + 10)
                                e_max = we
                                if e_max <= e_min:
                                    continue
                                e = random.randint(e_min, e_max)
                                blocks.append((s, e))
                            blocks = _clip_to_work(_merge_intervals(blocks), ws, we)
                            intervals = [_interval_str(s, e) for s, e in blocks]
                            person_sched[d] = {'type': 'busy', 'intervals': intervals}
                        else:
                            fcnt = random.randint(1, 2)
                            frees = []
                            for _ in range(fcnt):
                                if we - ws < 15:
                                    continue
                                s = random.randint(ws, max(ws, we - 15))
                                e_min = min(we, s + 5)
                                e_max = min(we, s + 20)
                                if e_max <= e_min:
                                    continue
                                e = random.randint(e_min, e_max)
                                frees.append((s, e))
                            frees = _clip_to_work(_merge_intervals(frees), ws, we)
                            intervals = [_interval_str(s, e) for s, e in frees]
                            person_sched[d] = {'type': 'free', 'intervals': intervals}
            schedules[name] = person_sched

        # 可行性与一致性验证（原策略）
        res1 = compute_max_and_count_v3(
            schedules=schedules,
            names=names_local,
            days=days,
            work_start=work_start,
            work_end=work_end,
            step_minutes=step_minutes,
            min_duration=min_duration,
            policy_pack=policy_pack,
            clearer_index=clearer_index,
            clearance_threshold=clearance_threshold
        )
        if res1[0] < min_duration or res1[1] < 1:
            continue
        res2 = compute_max_and_count_v3_alt(
            schedules=schedules,
            names=names_local,
            days=days,
            work_start=work_start,
            work_end=work_end,
            step_minutes=step_minutes,
            min_duration=min_duration,
            policy_pack=policy_pack,
            clearer_index=clearer_index,
            clearance_threshold=clearance_threshold
        )
        if res1 == res2:
            return schedules
        # else retry

    # 保底构造：确保返回满足断言的 schedules（在原策略下验证）
    fallback = _build_feasible_schedules(names_local, days, work_start, work_end, policy_pack)
    resA = compute_max_and_count_v3(
        schedules=fallback,
        names=names_local,
        days=days,
        work_start=work_start,
        work_end=work_end,
        step_minutes=step_minutes,
        min_duration=min_duration,
        policy_pack=policy_pack,
        clearer_index=clearer_index,
        clearance_threshold=clearance_threshold
    )
    resB = compute_max_and_count_v3_alt(
        schedules=fallback,
        names=names_local,
        days=days,
        work_start=work_start,
        work_end=work_end,
        step_minutes=step_minutes,
        min_duration=min_duration,
        policy_pack=policy_pack,
        clearer_index=clearer_index,
        clearance_threshold=clearance_threshold
    )
    if resA[0] >= min_duration and resA[1] >= 1 and resA == resB:
        return fallback

    # 理论上不会触发
    return fallback

def render_schedule(schedules: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    lines: List[str] = []
    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    for person in sorted(schedules.keys()):
        for d in day_order:
            if d not in schedules[person]:
                continue
            item = schedules[person][d]
            typ = '空闲' if item['type'] == 'free' else '忙碌'
            intervals = item['intervals']
            inter_text = ', '.join(intervals) if intervals else '无区间'
            lines.append(f'{person} 在 {d} 为 {typ}，区间：{inter_text}')
    return '\n'.join(lines)

# -----------------------------
# Custom operators for YAML: answer computation and verification
# -----------------------------
def _apply_global_cuts(intervals: List[Tuple[int, int]],
                       lunch_tuple: Optional[Tuple[int, int]],
                       end_cap: Optional[int]) -> List[Tuple[int, int]]:
    inter = intervals
    if lunch_tuple:
        tmp: List[Tuple[int, int]] = []
        for s, e in inter:
            tmp.extend(_subtract_block([(s, e)], lunch_tuple))
        inter = _merge_intervals(tmp)
    if end_cap is not None:
        inter = [(s, min(e, end_cap)) for s, e in inter if s < min(e, end_cap)]
        inter = _merge_intervals(inter)
    return inter

def _enumerate_starts(s: int, e: int, ws: int, anchor: str, step_len: int) -> List[int]:
    if anchor == 'workstart':
        def next_grid_from(x):
            delta = (x - ws) % step_len
            return x if delta == 0 else x + (step_len - delta)
        t = next_grid_from(s)
    else:
        t = ((s + step_len - 1) // step_len) * step_len
    res = []
    while t < e:
        if t >= ws:
            res.append(t)
        t += step_len
    return res

def compute_max_and_count_v3(schedules: Dict[str, Dict[str, Dict[str, Any]]],
                             names: List[str],
                             days: List[str],
                             work_start: str,
                             work_end: str,
                             step_minutes: int,
                             min_duration: int,
                             policy_pack: Dict[str, Any],
                             clearer_index: int,
                             clearance_threshold: int) -> List[int]:
    ws = _to_minutes(work_start)
    we = _to_minutes(work_end)
    allowed_days = policy_pack.get('allowed_days', days)
    lunch_block = policy_pack.get('lunch_block')
    lunch_tuple: Optional[Tuple[int, int]] = _parse_interval(lunch_block) if lunch_block else None
    must_end_by = policy_pack.get('must_end_by')
    end_cap = _to_minutes(must_end_by) if must_end_by else None

    clearance_mode = policy_pack.get('clearance_mode', 'single_clearer_threshold')
    per_day_clear_limit = policy_pack.get('per_day_clear_limit', None)
    clearer_name = names[clearer_index]

    day_anchor_map = policy_pack.get('day_anchor_map', {})
    step_scale_map = policy_pack.get('step_scale_map', {})
    base_anchor = policy_pack.get('grid_anchor', 'absolute')

    buffer_before = policy_pack.get('buffer_before', 0)
    buffer_after = policy_pack.get('buffer_after', 0)

    veto_person = policy_pack.get('veto_person', None)
    veto_block_str = policy_pack.get('veto_block', None)
    veto_tuple = _parse_interval(veto_block_str) if veto_block_str else None

    no_start_zones = [ _parse_interval(z) for z in policy_pack.get('no_start_zones', []) ]

    max_dur = 0
    count = 0

    for day in days:
        if day not in allowed_days:
            continue

        # gather each person's free intervals with clearance
        all_free: List[List[Tuple[int, int]]] = []
        for name in names:
            item = schedules[name][day]
            free_list = _person_free_with_mode(
                day_item=item,
                ws=ws,
                we=we,
                name=name,
                clearer_name=clearer_name,
                clearance_mode=clearance_mode,
                single_threshold=clearance_threshold,
                per_day_clear_limit=per_day_clear_limit
            )
            # veto cut for veto person
            if veto_tuple and name == veto_person:
                free_list = _subtract_block(free_list, veto_tuple)
            free_list = _apply_global_cuts(free_list, lunch_tuple, end_cap)
            all_free.append(free_list)

        # intersection
        if not all_free:
            continue
        inter = all_free[0]
        for idx in range(1, len(all_free)):
            inter = _intersect_two(inter, all_free[idx])
            inter = _merge_intervals(inter)
            if not inter:
                break
        if not inter:
            continue

        step_len = step_minutes * int(step_scale_map.get(day, 1))
        anchor = day_anchor_map.get(day, base_anchor)

        for s, e in inter:
            # 起点必须同时满足缓冲前覆盖，因此将枚举起点下界提升到 ws + buffer_before
            s_effective = max(s, ws + buffer_before)
            starts = _enumerate_starts(s_effective, e, ws, anchor, step_len)
            for t in starts:
                # no-start zones filter
                invalid = False
                for z in no_start_zones:
                    if z[0] <= t < z[1]:
                        invalid = True
                        break
                if invalid:
                    continue
                dur = e - t
                if dur < min_duration:
                    continue
                # buffer coverage check per person
                ok = True
                for i, name in enumerate(names):
                    free_list = all_free[i]
                    if not _is_covered(free_list, t - buffer_before, t):
                        ok = False
                        break
                    if not _is_covered(free_list, t, t + dur):
                        ok = False
                        break
                    if not _is_covered(free_list, t + dur, t + dur + buffer_after):
                        ok = False
                        break
                if not ok:
                    continue
                # update
                if dur > max_dur:
                    max_dur = dur
                    count = 1
                elif dur == max_dur:
                    count += 1

    if max_dur == 0:
        return [0, 0]
    return [max_dur, count]

def compute_max_and_count_v3_alt(schedules: Dict[str, Dict[str, Dict[str, Any]]],
                                 names: List[str],
                                 days: List[str],
                                 work_start: str,
                                 work_end: str,
                                 step_minutes: int,
                                 min_duration: int,
                                 policy_pack: Dict[str, Any],
                                 clearer_index: int,
                                 clearance_threshold: int) -> List[int]:
    ws = _to_minutes(work_start)
    we = _to_minutes(work_end)
    allowed_days = policy_pack.get('allowed_days', days)
    lunch_block = policy_pack.get('lunch_block')
    lunch_tuple: Optional[Tuple[int, int]] = _parse_interval(lunch_block) if lunch_block else None
    must_end_by = policy_pack.get('must_end_by')
    end_cap = _to_minutes(must_end_by) if must_end_by else None

    clearance_mode = policy_pack.get('clearance_mode', 'single_clearer_threshold')
    per_day_clear_limit = policy_pack.get('per_day_clear_limit', None)
    clearer_name = names[clearer_index]

    day_anchor_map = policy_pack.get('day_anchor_map', {})
    step_scale_map = policy_pack.get('step_scale_map', {})
    base_anchor = policy_pack.get('grid_anchor', 'absolute')

    buffer_before = policy_pack.get('buffer_before', 0)
    buffer_after = policy_pack.get('buffer_after', 0)

    veto_person = policy_pack.get('veto_person', None)
    veto_block_str = policy_pack.get('veto_block', None)
    veto_tuple = _parse_interval(veto_block_str) if veto_block_str else None

    no_start_zones = [ _parse_interval(z) for z in policy_pack.get('no_start_zones', []) ]

    max_dur = 0
    count = 0

    for day in days:
        if day not in allowed_days:
            continue

        # gather and shrink frees
        all_free_shrunk: List[List[Tuple[int, int]]] = []
        for name in names:
            item = schedules[name][day]
            free_list = _person_free_with_mode(
                day_item=item,
                ws=ws,
                we=we,
                name=name,
                clearer_name=clearer_name,
                clearance_mode=clearance_mode,
                single_threshold=clearance_threshold,
                per_day_clear_limit=per_day_clear_limit
            )
            # veto cut
            if veto_tuple and name == veto_person:
                free_list = _subtract_block(free_list, veto_tuple)
            # global cuts
            free_list = _apply_global_cuts(free_list, lunch_tuple, end_cap)
            # shrink for buffers
            free_list = _shrink_free_for_buffer(free_list, buffer_before, buffer_after)
            all_free_shrunk.append(free_list)

        if not all_free_shrunk:
            continue
        inter = all_free_shrunk[0]
        for idx in range(1, len(all_free_shrunk)):
            inter = _intersect_two(inter, all_free_shrunk[idx])
            inter = _merge_intervals(inter)
            if not inter:
                break
        if not inter:
            continue

        step_len = step_minutes * int(step_scale_map.get(day, 1))
        anchor = day_anchor_map.get(day, base_anchor)

        for s, e in inter:
            starts = _enumerate_starts(s, e, ws, anchor, step_len)
            for t in starts:
                # no-start zones filter
                invalid = False
                for z in no_start_zones:
                    if z[0] <= t < z[1]:
                        invalid = True
                        break
                if invalid:
                    continue
                dur = e - t
                if dur >= min_duration:
                    if dur > max_dur:
                        max_dur = dur
                        count = 1
                    elif dur == max_dur:
                        count += 1

    if max_dur == 0:
        return [0, 0]
    return [max_dur, count]

def verify_unique_solution(schedules: Dict[str, Dict[str, Dict[str, Any]]],
                           names: List[str],
                           days: List[str],
                           work_start: str,
                           work_end: str,
                           step_minutes: int,
                           min_duration: int,
                           policy_pack: Dict[str, Any],
                           clearer_index: int,
                           clearance_threshold: int) -> bool:
    r1 = compute_max_and_count_v3(
        schedules, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, clearer_index, clearance_threshold
    )
    r2 = compute_max_and_count_v3_alt(
        schedules, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, clearer_index, clearance_threshold
    )
    return r1 == r2

# Backward function kept (not used by YAML)
def compute_max_and_count_v2(schedules: Dict[str, Dict[str, Dict[str, Any]]],
                             names: List[str],
                             days: List[str],
                             work_start: str,
                             work_end: str,
                             step_minutes: int,
                             min_duration: int,
                             policy_pack: Dict[str, Any],
                             clearer_index: int,
                             clearance_threshold: int) -> List[int]:
    # Delegate to v3 for compatibility
    return compute_max_and_count_v3(schedules, names, days, work_start, work_end, step_minutes, min_duration, policy_pack, clearer_index, clearance_threshold)