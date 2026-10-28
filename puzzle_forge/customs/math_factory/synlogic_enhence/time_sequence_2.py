# time_sequence_0.py
from typing import Dict, List, Tuple, Optional
import random

# ----------------------------
# Time and interval utilities
# ----------------------------
def _to_minutes(t: str) -> int:
    h, m = t.strip().split(':')
    return int(h) * 60 + int(m)

def _to_hhmm(x: int) -> str:
    h = x // 60
    m = x % 60
    return f'{h:02d}:{m:02d}'

def _ceil_to_grid(x: int, gran: int = 30) -> int:
    r = x % gran
    return x if r == 0 else x + (gran - r)

def _floor_to_grid(x: int, gran: int = 30) -> int:
    r = x % gran
    return x - r

def _round_to_grid(x: int, gran: int = 30) -> int:
    # Round to nearest multiple of gran; ties go to floor (靠前)
    r = x % gran
    down = x - r
    up = down if r == 0 else down + gran
    return down if r * 2 <= gran else up

def _clip_interval(iv: Tuple[int, int], ws: int, we: int) -> Optional[Tuple[int, int]]:
    s, e = iv
    s = max(s, ws)
    e = min(e, we)
    if s >= e:
        return None
    return (s, e)

def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged

def _complement(ws: int, we: int, busy: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if ws >= we:
        return []
    busy = _merge_intervals(busy)
    free: List[Tuple[int, int]] = []
    cur = ws
    for s, e in busy:
        if e <= ws or s >= we:
            continue
        s = max(s, ws)
        e = min(e, we)
        if s > cur:
            free.append((cur, s))
        cur = max(cur, e)
    if cur < we:
        free.append((cur, we))
    return free

def _normalize_day(day_obj: Dict[str, List[Tuple[str, str]]], ws: int, we: int) -> List[Tuple[int, int]]:
    free_raw = day_obj.get('free', []) or []
    busy_raw = day_obj.get('busy', []) or []

    free_int: List[Tuple[int, int]] = []
    for s, e in free_raw:
        iv = _clip_interval((_to_minutes(s), _to_minutes(e)), ws, we)
        if iv:
            free_int.append(iv)
    busy_int: List[Tuple[int, int]] = []
    for s, e in busy_raw:
        iv = _clip_interval((_to_minutes(s), _to_minutes(e)), ws, we)
        if iv:
            busy_int.append(iv)

    if free_int:
        return _merge_intervals(free_int)
    else:
        return _complement(ws, we, busy_int)

def _intersect_two(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    i, j = 0, 0
    res: List[Tuple[int, int]] = []
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if s < e:
            res.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return res

def _intersect_many(lists_of_intervals: List[List[Tuple[int, int]]]) -> List[Tuple[int, int]]:
    if not lists_of_intervals:
        return []
    res = lists_of_intervals[0]
    for nxt in lists_of_intervals[1:]:
        res = _intersect_two(res, nxt)
        if not res:
            break
    return res

# ---------------------------------
# Optional coverage segments
# ---------------------------------
def _build_coverage_segments(free_lists: List[List[Tuple[int, int]]]) -> List[Tuple[int, int, int]]:
    """
    Build piecewise-constant coverage segments from many persons' free intervals.
    Returns list of (seg_start, seg_end, count).
    """
    events: List[Tuple[int, int]] = []
    for ints in free_lists:
        for s, e in ints:
            events.append((s, +1))
            events.append((e, -1))
    if not events:
        return []
    events.sort(key=lambda x: (x[0], -x[1]))  # add before remove at same time
    segs: List[Tuple[int, int, int]] = []
    cnt = 0
    prev: Optional[int] = None
    for t, d in events:
        if prev is not None and prev < t:
            segs.append((prev, t, cnt))
        cnt += d
        prev = t
    return segs

def _duration_with_optional(start: int, req_end: int,
                            opt_segs: List[Tuple[int, int, int]],
                            need_k: int) -> int:
    """
    From 'start' up to req_end, find max continuous duration such that optional coverage >= need_k.
    opt_segs is list of (s,e,cnt). If need_k <= 0, returns req_end - start.
    """
    if start >= req_end:
        return 0
    if need_k <= 0:
        return max(0, req_end - start)

    # find segment containing start
    idx = -1
    for i, (s, e, c) in enumerate(opt_segs):
        if s <= start < e:
            idx = i
            break
    if idx == -1:
        return 0

    dur_end = start
    s, e, c = opt_segs[idx]
    if c < need_k:
        return 0
    dur_end = min(e, req_end)
    i = idx + 1
    while dur_end == e and dur_end < req_end and i < len(opt_segs):
        s2, e2, c2 = opt_segs[i]
        if s2 != e:  # gap
            break
        if c2 < need_k:
            break
        dur_end = min(e2, req_end)
        e = e2
        i += 1
    return max(0, dur_end - start)

# ---------------------------------
# Random schedule generation utils
# ---------------------------------
def _rand_non_overlapping_intervals(ws: int, we: int, k: int, min_len: int, max_len: int, step: int = 5) -> List[Tuple[int, int]]:
    # Generate up to k non-overlapping intervals inside [ws, we]
    if ws >= we or k <= 0:
        return []
    intervals: List[Tuple[int, int]] = []
    tries = 0
    max_tries = 300
    while len(intervals) < k and tries < max_tries:
        tries += 1
        start = random.randrange(ws, we, step)
        length = random.randint(min_len, max_len)
        end = start + length
        if end > we:
            continue
        ok = True
        for s, e in intervals:
            if not (end <= s or start >= e):
                ok = False
                break
        if ok:
            intervals.append((start, end))
    return _merge_intervals(intervals)

def _make_person_schedule(days: List[str],
                          work_windows: Dict[str, Tuple[str, str]],
                          p_free_desc: float,
                          k_range: Tuple[int, int],
                          min_len: int, max_len: int) -> Dict[str, Dict[str, List[Tuple[str, str]]]]:
    sched: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
    k_low, k_high = k_range
    for d in days:
        ws = _to_minutes(work_windows[d][0])
        we = _to_minutes(work_windows[d][1])
        if we - ws < 15:
            sched[d] = {'busy': []}
            continue
        use_free = (random.random() < p_free_desc)
        k = random.randint(k_low, k_high)
        max_seg_len = min(max_len, max(10, we - ws))
        min_seg_len = min(min_len, max_seg_len)
        ints = _rand_non_overlapping_intervals(ws, we, k, min_seg_len, max_seg_len, step=5)
        ints_str = [(_to_hhmm(s), _to_hhmm(e)) for s, e in ints]
        if use_free:
            sched[d] = {'free': ints_str}
        else:
            sched[d] = {'busy': ints_str}
    return sched

def _gen_names(n: int) -> List[str]:
    pool = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    if n <= len(pool):
        return pool[:n]
    extra = [f'员{i+1}' for i in range(n - len(pool))]
    return pool + extra

# ---------------------------------
# Core computation and validation
# ---------------------------------
def compute_max_meeting(schedules: Dict[str, Dict[str, Dict[str, List[Tuple[str, str]]]]],
                        days: List[str],
                        work_windows: Dict[str, Tuple[str, str]],
                        granularity: int = 30,
                        candidate_policy: str = 'ceil_left',
                        required_names: Optional[List[str]] = None,
                        min_total: Optional[int] = None) -> List[int]:
    """
    Compute [max_duration_minutes, option_count, day_index].
    day_index is 1-based and corresponds to the order of 'days'.
    """
    people = list(schedules.keys())
    if required_names is None:
        required_names = people[:]  # degenerate: all required
    req_set = set(required_names)
    optional_names = [p for p in people if p not in req_set]
    need_k = 0 if min_total is None else max(0, min_total - len(required_names))

    global_max = 0
    day_best: Dict[str, Tuple[int, int]] = {}

    for d in days:
        ws = _to_minutes(work_windows[d][0])
        we = _to_minutes(work_windows[d][1])
        if ws >= we:
            day_best[d] = (0, 0)
            continue

        # collect free intervals for required participants
        req_free_lists: List[List[Tuple[int, int]]] = []
        for p in required_names:
            day_obj = schedules.get(p, {}).get(d, {})
            free_ints = _normalize_day(day_obj, ws, we)
            req_free_lists.append(free_ints)
        common_req = _intersect_many(req_free_lists)
        if not common_req:
            day_best[d] = (0, 0)
            continue

        # optional coverage segments
        opt_free_lists: List[List[Tuple[int, int]]] = []
        for p in optional_names:
            day_obj = schedules.get(p, {}).get(d, {})
            free_ints = _normalize_day(day_obj, ws, we)
            opt_free_lists.append(free_ints)
        opt_segs = _build_coverage_segments(opt_free_lists)

        best_dur_d = 0
        cand_d: List[int] = []

        for s, e in common_req:
            if candidate_policy == 'ceil_left':
                start = _ceil_to_grid(s, granularity)
                if start < e:
                    dur = _duration_with_optional(start, e, opt_segs, need_k)
                    if dur > best_dur_d:
                        best_dur_d = dur
                        cand_d = [start]
                    elif dur == best_dur_d and dur > 0:
                        cand_d.append(start)

            elif candidate_policy == 'all_grid':
                t = _ceil_to_grid(s, granularity)
                while t < e:
                    dur = _duration_with_optional(t, e, opt_segs, need_k)
                    if dur > best_dur_d:
                        best_dur_d = dur
                        cand_d = [t]
                    elif dur == best_dur_d and dur > 0:
                        cand_d.append(t)
                    t += granularity

            else:  # 'midpoint'
                mid = (s + e) // 2
                start = _round_to_grid(mid, granularity)
                if start < s:
                    start = _ceil_to_grid(s, granularity)
                if start >= e:
                    start = _floor_to_grid(e - 1, granularity)
                if start < e:
                    dur = _duration_with_optional(start, e, opt_segs, need_k)
                    if dur > best_dur_d:
                        best_dur_d = dur
                        cand_d = [start]
                    elif dur == best_dur_d and dur > 0:
                        cand_d.append(start)

        day_best[d] = (best_dur_d, len(cand_d))
        if best_dur_d > global_max:
            global_max = best_dur_d
        elif best_dur_d == global_max and best_dur_d > 0:
            pass  # just tracking global_max

    # determine unique day with global max
    days_with_max = [d for d in days if day_best.get(d, (0, 0))[0] == global_max and global_max > 0]
    if len(days_with_max) == 1:
        the_day = days_with_max[0]
        count = day_best[the_day][1]
        return [global_max, count, days.index(the_day) + 1]
    else:
        # deterministic fallback: earliest by order (validator rejects non-unique)
        if global_max <= 0:
            return [0, 0, 1 if days else 1]
        the_day = None
        for d in days:
            if day_best.get(d, (0, 0))[0] == global_max:
                the_day = d
                break
        if the_day is None:
            the_day = days[0] if days else 'Mon'
        return [global_max, day_best.get(the_day, (0, 0))[1], days.index(the_day) + 1]

def _compute_day_stats(schedules: Dict[str, Dict[str, Dict[str, List[Tuple[str, str]]]]],
                       day: str,
                       work_windows: Dict[str, Tuple[str, str]],
                       granularity: int,
                       candidate_policy: str,
                       required_names: List[str],
                       min_total: int) -> Tuple[int, int]:
    res = compute_max_meeting(schedules, [day], work_windows, granularity, candidate_policy, required_names, min_total)
    return (res[0], res[1])

def validate_instance(schedules: Dict[str, Dict[str, Dict[str, List[Tuple[str, str]]]]],
                      days: List[str],
                      work_windows: Dict[str, Tuple[str, str]],
                      granularity: int = 30,
                      candidate_policy: str = 'ceil_left',
                      required_names: Optional[List[str]] = None,
                      min_total: Optional[int] = None) -> bool:
    if required_names is None or min_total is None:
        return False
    ans = compute_max_meeting(schedules, days, work_windows, granularity, candidate_policy, required_names, min_total)
    if (not isinstance(ans, list)) or len(ans) != 3:
        return False
    max_dur, cnt, day_idx = ans
    if not isinstance(max_dur, int) or not isinstance(cnt, int) or not isinstance(day_idx, int):
        return False
    if max_dur <= 0 or cnt < 1:
        return False
    if day_idx < 1 or day_idx > len(days):
        return False

    # Uniqueness: exactly one day achieves the global max
    day_stats = {d: _compute_day_stats(schedules, d, work_windows, granularity, candidate_policy, required_names, min_total) for d in days}
    max_over_days = max(v[0] for v in day_stats.values()) if day_stats else 0
    days_with_max = [d for d, v in day_stats.items() if v[0] == max_over_days and max_over_days > 0]
    if len(days_with_max) != 1:
        return False
    the_day = days_with_max[0]
    # Consistency
    if day_idx != days.index(the_day) + 1:
        return False
    if cnt != day_stats[the_day][1]:
        return False
    return True

# ---------------------------------
# Instance making and text formatting
# ---------------------------------
def make_instance(participants_num: int,
                  days: List[str],
                  work_windows: Dict[str, Tuple[str, str]],
                  granularity: int,
                  candidate_policy: str,
                  required_num: int,
                  min_total: int) -> Dict[str, object]:
    """
    Randomly generate names, roles, and schedules for participants,
    guarantee at least one feasible candidate start under the chosen policy,
    and ensure the unique day achieving global maximum (validated).
    """
    names = _gen_names(participants_num)
    req_names = random.sample(names, required_num)
    opt_names = [nm for nm in names if nm not in req_names]

    tries = 0
    max_tries = 160

    while tries < max_tries:
        tries += 1
        schedules: Dict[str, Dict[str, Dict[str, List[Tuple[str, str]]]]] = {}

        p_free_desc = random.uniform(0.35, 0.7)
        k_low, k_high = 1, 3
        min_len = random.randint(20, 50)  # minutes
        max_len = random.randint(60, 140)
        if min_len > max_len:
            min_len, max_len = max_len, min_len

        for nm in names:
            schedules[nm] = _make_person_schedule(days, work_windows, p_free_desc, (k_low, k_high), min_len, max_len)

        if validate_instance(schedules, days, work_windows, granularity, candidate_policy, req_names, min_total):
            return {'names': names, 'schedules': schedules, 'required': req_names, 'optional': opt_names}

    # Fallback construction with deterministic unique best day
    fallback_day = random.choice(days)
    ws_fb = _to_minutes(work_windows[fallback_day][0])
    we_fb = _to_minutes(work_windows[fallback_day][1])
    base_choices = [max(granularity + 20, 70), max(granularity + 40, 100), max(granularity + 60, 130)]
    base_len = min(random.choice(base_choices), max(30, we_fb - ws_fb))
    s_fb = max(ws_fb, ((ws_fb + we_fb) // 2) - base_len // 2)
    s_fb = _floor_to_grid(s_fb, 5)
    e_fb = min(we_fb, s_fb + base_len)
    if e_fb - s_fb < max(20, granularity):
        e_fb = min(we_fb, s_fb + max(20, granularity) + 30)

    schedules: Dict[str, Dict[str, Dict[str, List[Tuple[str, str]]]]] = {}
    need_k = max(0, min_total - len(req_names))
    strong_opt = []
    if need_k > 0:
        if len(opt_names) >= need_k:
            strong_opt = random.sample(opt_names, need_k)
        else:
            strong_opt = opt_names[:]

    for nm in names:
        person = {}
        for d in days:
            ws_d = _to_minutes(work_windows[d][0])
            we_d = _to_minutes(work_windows[d][1])

            if d == fallback_day:
                if nm in req_names:
                    person[d] = {'free': [(_to_hhmm(s_fb), _to_hhmm(e_fb))]}
                else:
                    if nm in strong_opt:
                        person[d] = {'free': [(_to_hhmm(s_fb), _to_hhmm(e_fb))]}
                    else:
                        if we_d - ws_d < 20:
                            person[d] = {'busy': []}
                        else:
                            mid = (s_fb + e_fb) // 2
                            seg_len = max(10, (e_fb - s_fb) // 2)
                            a = max(ws_d, mid - seg_len // 2)
                            b = min(we_d, a + seg_len)
                            person[d] = {'free': [(_to_hhmm(a), _to_hhmm(b))]}
            else:
                if we_d - ws_d < 30:
                    person[d] = {'busy': []}
                else:
                    if nm in req_names:
                        start = random.randrange(ws_d, max(ws_d + 5, we_d - 30), 5)
                        end = min(we_d, start + random.randint(15, max(20, (e_fb - s_fb) - 30)))
                        person[d] = {'free': [(_to_hhmm(start), _to_hhmm(end))]}
                    else:
                        start = random.randrange(ws_d, max(ws_d + 5, we_d - 25), 5)
                        end = min(we_d, start + random.randint(10, 40))
                        person[d] = {'busy': [(_to_hhmm(start), _to_hhmm(end))]}
        schedules[nm] = person

    return {'names': names, 'schedules': schedules, 'required': req_names, 'optional': [x for x in names if x not in req_names]}

def format_schedules_text(names: List[str],
                          schedules: Dict[str, Dict[str, Dict[str, List[Tuple[str, str]]]]],
                          days: List[str],
                          work_windows: Dict[str, Tuple[str, str]],
                          granularity: int,
                          candidate_policy: str,
                          required_names: List[str],
                          min_total: int) -> str:
    """
    Produce a human-readable multiline text without quotes.
    """
    lines: List[str] = []
    day_cn = {'Mon': '周一', 'Tue': '周二', 'Wed': '周三', 'Thu': '周四', 'Fri': '周五'}
    lines.append('工作时间窗口如下')
    for d in days:
        s, e = work_windows[d]
        lines.append(f"{day_cn.get(d, d)} {s} 到 {e}")
    # roles statement
    req_disp = ''.join(required_names)
    opt_disp = ''.join([nm for nm in names if nm not in required_names])
    lines.append(f"必到参与者 {req_disp}")
    if opt_disp:
        lines.append(f"可选参与者 {opt_disp}")
    need_k = max(0, min_total - len(required_names))
    lines.append(f"最少参会人数阈值 {min_total} 人 会议需包含全部必到者 且总人数不少于该阈值")
    if need_k > 0:
        lines.append(f"人数阈值换算 除全部必到者外 至少还需 {need_k} 名可选参与者同时空闲")
    else:
        lines.append("人数阈值换算 无需可选参与者到场即可满足人数要求")
    if candidate_policy == 'ceil_left':
        policy_text = '候选起点规则 每个共同空闲区间仅统计一个候选起点 为将该区间左端点按粒度向上取整 若不小于右端点则该区间无候选'
    elif candidate_policy == 'all_grid':
        policy_text = '候选起点规则 每个共同空闲区间内统计所有与粒度对齐且落在区间内的起点 对每个起点自该时刻起连续向右延伸 直至到达该共同空闲区间右端或可选覆盖人数不足的首个时刻 取较早者为终点 以此得到该起点的可达时长'
    else:
        policy_text = '候选起点规则 每个共同空闲区间仅统计一个候选起点 为该区间中点按粒度四舍五入到最近时间 若该时间不落入区间内则向内侧调整到最近可行起点 中点与两侧等距时取靠前时间'
    lines.append(f'起始时间粒度 {granularity} 分钟')
    lines.append(policy_text)
    lines.append('记法说明 同一天若仅给出空闲时段 则未列出的时间视为忙碌 若仅给出忙碌时段 则该日工作时间窗口内除列出的忙碌外均为空闲 若无记录则视为该日窗口内全程可用')
    lines.append('共同空闲区间以全部必到者在该日工作时间窗口内的空闲交集为准')
    lines.append('持续时间判定 自候选起点起连续向右 直至到达共同空闲区间右端或可选覆盖人数不足的首个时刻 取较早者为终点 期间需包含全部必到者 且满足人数阈值')
    lines.append('中点取整遇到两侧等距时取靠前时间')
    lines.append('所有时间单位均为分钟 时段采用左闭右开约定')

    for nm in names:
        lines.append(f'参与者{nm}')
        person = schedules.get(nm, {})
        for d in days:
            dobj = person.get(d, {})
            if 'free' in dobj and dobj['free']:
                segs = ';'.join([f'{s}-{e}' for s, e in dobj['free']])
                lines.append(f"{day_cn.get(d, d)} 空闲时段 {segs}")
            elif 'busy' in dobj and dobj['busy']:
                segs = ';'.join([f'{s}-{e}' for s, e in dobj['busy']])
                lines.append(f"{day_cn.get(d, d)} 忙碌时段 {segs}")
            else:
                lines.append(f"{day_cn.get(d, d)} 无记录 视为整天可用")
    lines.append('工作日编号按1开始 对应如下')
    for i, d in enumerate(days):
        lines.append(f"{i+1} {d} {day_cn.get(d, d)}")
    return '\n'.join(lines)

# ---------------------------------
# Helpers to randomize work windows
# ---------------------------------
def rand_work_windows(days: List[str]) -> Dict[str, Tuple[str, str]]:
    windows: Dict[str, Tuple[str, str]] = {}
    for d in days:
        sh = random.randint(8, 10)          # start hour
        ln = random.randint(7, 9)           # length in hours
        eh = sh + ln
        s = f'{sh:02d}:00'
        e = f'{eh:02d}:00'
        windows[d] = (s, e)
    return windows