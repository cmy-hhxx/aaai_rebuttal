from typing import List, Tuple, Dict
import random

# ==================== 基础时间与区间工具 ====================
def _parse_time(s: str) -> int:
    h, m = s.strip().split(':')
    return int(h) * 60 + int(m)

def _fmt_time(t: int) -> str:
    h = t // 60
    m = t % 60
    return f"{h:02d}:{m:02d}"

def _mk_interval_str(s: int, e: int) -> str:
    return f"{_fmt_time(s)}-{_fmt_time(e)}"

def _merge_intervals(intervals: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = []
    cs, ce = intervals[0]
    for s, e in intervals[1:]:
        if s <= ce:  # overlap or contiguous
            ce = max(ce, e)
        else:
            merged.append((cs, ce))
            cs, ce = s, e
    merged.append((cs, ce))
    return merged

def _complement_intervals(intervals: List[Tuple[int,int]], window: Tuple[int,int]) -> List[Tuple[int,int]]:
    ws, we = window
    busy = _merge_intervals([iv for iv in intervals if iv[1] > ws and iv[0] < we])
    free = []
    cur = ws
    for s, e in busy:
        s = max(ws, s)
        e = min(we, e)
        if cur < s:
            free.append((cur, s))
        cur = max(cur, e)
    if cur < we:
        free.append((cur, we))
    return free

def _intersect_two(a: List[Tuple[int,int]], b: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    i = j = 0
    res = []
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

def _intersect_many(lists: List[List[Tuple[int,int]]]) -> List[Tuple[int,int]]:
    if not lists:
        return []
    res = _merge_intervals(lists[0])
    for lst in lists[1:]:
        res = _intersect_two(res, _merge_intervals(lst))
        if not res:
            return []
    return _merge_intervals(res)

def _allowed_starts(work_start: int, work_end: int, grid: int = 30) -> List[int]:
    """
    返回允许的起始点列表：
    - 起始限制固定为整点/半点（grid强制重置为30）
    """
    grid = 30
    starts = []
    t = work_start
    mod = t % grid
    if mod != 0:
        t += (grid - mod)
    while t < work_end:
        starts.append(t)
        t += grid
    return starts

def _length_from_start(start: int, free_intervals: List[Tuple[int,int]]) -> int:
    for s, e in free_intervals:
        if s <= start < e:
            return e - start
    return 0

# ==================== 求解：计算答案 ====================
def compute_best_meeting(hewei: List[Dict], fengjie: List[Dict], gaolei: List[Dict],
                         work_start: str, work_end: str, grid_minutes: int = 30,
                         apply_clearance: bool = True) -> List[int]:
    """
    计算在“整点或半点开始”的最长可会议时长（分钟）及对应选项数。
    规则：
    - 工作时间窗口为 [work_start, work_end)
    - type='only_free'：仅列出空闲区间，其余时间视为不可安排
    - type='only_busy'：仅列出忙碌区间，其余时间视为空闲
    - 赫伟可清除其 busy 型日程中任意长度 ≤ 30 分钟的忙碌区间（apply_clearance=True）
    """
    ws = _parse_time(work_start)
    we = _parse_time(work_end)
    window = (ws, we)

    def person_free(person: List[Dict], name: str) -> Dict[str, List[Tuple[int,int]]]:
        free_map = {}
        for d in person:
            day = d['day']
            typ = d['type']
            raw_intervals = []
            for x in d['intervals']:
                a, b = x.split('-')
                raw_intervals.append((_parse_time(a), _parse_time(b)))
            if typ == 'only_free':
                adj = []
                for s, e in raw_intervals:
                    s = max(ws, s); e = min(we, e)
                    if s < e:
                        adj.append((s, e))
                free_map[day] = _merge_intervals(adj)
            else:  # only_busy
                busy = []
                for s, e in raw_intervals:
                    s = max(ws, s); e = min(we, e)
                    if s < e:
                        busy.append((s, e))
                # 赫伟清除 ≤30 分钟忙块
                if name == 'hewei' and apply_clearance:
                    busy = [iv for iv in busy if (iv[1] - iv[0]) > 30]
                free_map[day] = _complement_intervals(busy, window)
        return free_map

    h_free = person_free(hewei, 'hewei')
    f_free = person_free(fengjie, 'fengjie')
    g_free = person_free(gaolei, 'gaolei')

    max_len = 0
    count = 0

    for day in h_free.keys():
        if day not in f_free or day not in g_free:
            continue
        common = _intersect_many([h_free[day], f_free[day], g_free[day]])
        if not common:
            continue
        starts = _allowed_starts(ws, we, grid_minutes)
        for st in starts:
            L = _length_from_start(st, common)
            if L > max_len:
                max_len = L
                count = 1
            elif L == max_len and L > 0:
                count += 1

    if max_len <= 0:
        return [0, 0]
    return [max_len, count]

# ==================== 生成器：高质量+多样性+可复现 ====================
def _free_day_struct(day: str, intervals: List[Tuple[int,int]]) -> Dict:
    return {'day': day, 'type': 'only_free',
            'intervals': [_mk_interval_str(s, e) for s, e in _merge_intervals(intervals)]}

def _busy_day_struct(day: str, intervals: List[Tuple[int,int]]) -> Dict:
    return {'day': day, 'type': 'only_busy',
            'intervals': [_mk_interval_str(s, e) for s, e in _merge_intervals(intervals)]}

def _gen_small_intervals(ws: int, we: int, base_grid: int = 15) -> List[Tuple[int,int]]:
    """
    生成若干随机小窗口，用于扰动非目标日的空闲/忙碌分布。
    base_grid=15用于丰富形态（不会影响最终起始限制）。
    """
    res = []
    num_seg = random.randint(1, 3)
    for _ in range(num_seg):
        s = random.randrange(ws, we, base_grid)
        e = min(we, s + random.choice([10, 15, 20, 25, 30, 45]))
        if e > s:
            res.append((s, e))
    return _merge_intervals(res)

def _ensure_blocks_for_clearance(ws: int, start: int) -> List[Tuple[int,int]]:
    """
    在目标区间前插入 ≤30 分钟忙块（用于 requires_clearance 模式）：
    - 构造一个不超过30分钟的忙碌块，阻断起点，但可被赫伟清除。
    """
    size = random.choice([10, 15, 20, 25, 30])
    blk_start = max(ws, start - random.choice([10, 15, 20]))
    blk_end = min(blk_start + size, start + 1)
    if blk_end <= blk_start:
        blk_end = blk_start + min(30, size)
    return _merge_intervals([(blk_start, blk_end)])

def _build_week_for_mode(days: List[str], ws: int, we: int,
                         mode: str, min_len: int, max_len: int,
                         require_clearance: bool) -> Dict[str, List[Dict]]:
    allowed = _allowed_starts(ws, we, 30)
    candidates = [t for t in allowed if t + min_len <= we]
    if not candidates:
        candidates = allowed
    target_days = []

    hewei_week, fengjie_week, gaolei_week = [], [], []

    def add_day_common(day: str, start: int, length: int, clearance: bool):
        end = min(we, start + length)
        if mode == 'requires_clearance' and clearance:
            hewei_week.append(_busy_day_struct(day, _ensure_blocks_for_clearance(ws, start)))
            fengjie_week.append(_free_day_struct(day, [(start, end)]))
            gaolei_week.append(_free_day_struct(day, [(start, end)]))
        else:
            hewei_week.append(_free_day_struct(day, [(start, end)]))
            fengjie_week.append(_free_day_struct(day, [(start, end)]))
            gaolei_week.append(_free_day_struct(day, [(start, end)]))

    if mode == 'no_solution':
        for d in days:
            blocker = random.choice(['hewei', 'fengjie', 'gaolei'])
            if blocker == 'hewei':
                hewei_week.append(_busy_day_struct(d, [(ws, we)]))
                fengjie_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                   _busy_day_struct(d, _gen_small_intervals(ws, we))]))
                gaolei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                  _busy_day_struct(d, _gen_small_intervals(ws, we))]))
            elif blocker == 'fengjie':
                fengjie_week.append(_busy_day_struct(d, [(ws, we)]))
                hewei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                 _busy_day_struct(d, _gen_small_intervals(ws, we))]))
                gaolei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                  _busy_day_struct(d, _gen_small_intervals(ws, we))]))
            else:
                gaolei_week.append(_busy_day_struct(d, [(ws, we)]))
                hewei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                 _busy_day_struct(d, _gen_small_intervals(ws, we))]))
                fengjie_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                   _busy_day_struct(d, _gen_small_intervals(ws, we))]))
        return {'hewei': hewei_week, 'fengjie': fengjie_week, 'gaolei': gaolei_week}

    if mode in ['unique_max', 'requires_clearance']:
        target_day = random.choice(days)
        start = random.choice(candidates)
        length = random.randint(min_len, min(max_len, we - start))
        add_day_common(target_day, start, length, clearance=(mode == 'requires_clearance' and require_clearance))
        target_days = [target_day]
        for d in days:
            if d in target_days:
                continue
            pattern = random.choice(['block_all', 'short_noise', 'mixed'])
            if pattern == 'block_all':
                blocker = random.choice(['hewei', 'fengjie', 'gaolei'])
                if blocker == 'hewei':
                    hewei_week.append(_busy_day_struct(d, [(ws, we)]))
                    fengjie_week.append(_free_day_struct(d, _gen_small_intervals(ws, we)))
                    gaolei_week.append(_busy_day_struct(d, _gen_small_intervals(ws, we)))
                elif blocker == 'fengjie':
                    fengjie_week.append(_busy_day_struct(d, [(ws, we)]))
                    hewei_week.append(_free_day_struct(d, _gen_small_intervals(ws, we)))
                    gaolei_week.append(_busy_day_struct(d, _gen_small_intervals(ws, we)))
                else:
                    gaolei_week.append(_busy_day_struct(d, [(ws, we)]))
                    hewei_week.append(_free_day_struct(d, _gen_small_intervals(ws, we)))
                    fengjie_week.append(_busy_day_struct(d, _gen_small_intervals(ws, we)))
            elif pattern == 'short_noise':
                hewei_week.append(_free_day_struct(d, _gen_small_intervals(ws, we)))
                fengjie_week.append(_busy_day_struct(d, _gen_small_intervals(ws, we)))
                gaolei_week.append(_free_day_struct(d, _gen_small_intervals(ws, we)))
            else:
                hewei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                 _busy_day_struct(d, _gen_small_intervals(ws, we))]))
                fengjie_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                   _busy_day_struct(d, _gen_small_intervals(ws, we))]))
                gaolei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                                  _busy_day_struct(d, _gen_small_intervals(ws, we))]))
        return {'hewei': hewei_week, 'fengjie': fengjie_week, 'gaolei': gaolei_week}

    if mode == 'tie_max':
        tgt1, tgt2 = random.sample(days, 2)
        start1 = random.choice(candidates)
        length = random.randint(min_len, min(max_len, we - start1))
        candidates2 = [t for t in allowed if t + length <= we]
        if not candidates2:
            candidates2 = candidates
        start2 = random.choice(candidates2)
        add_day_common(tgt1, start1, length, clearance=False)
        add_day_common(tgt2, start2, length, clearance=False)
        target_days = [tgt1, tgt2]
        for d in days:
            if d in target_days:
                continue
            hewei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                             _busy_day_struct(d, _gen_small_intervals(ws, we))]))
            fengjie_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                               _busy_day_struct(d, _gen_small_intervals(ws, we))]))
            gaolei_week.append(random.choice([_free_day_struct(d, _gen_small_intervals(ws, we)),
                                              _busy_day_struct(d, _gen_small_intervals(ws, we))]))
        return {'hewei': hewei_week, 'fengjie': fengjie_week, 'gaolei': gaolei_week}

    return _build_week_for_mode(days, ws, we, 'unique_max', min_len, max_len, require_clearance)

def gen_schedules_advanced(work_start: str, work_end: str, days: List[str],
                           difficulty_profile: Dict, seed: int) -> Dict[str, List[Dict]]:
    """
    高质量日程生成器：
    - 支持 seed 可复现
    - 按 target_mode 构造形态，并使用 compute_best_meeting 回检；不达标重采样（max_resample）
    - 覆盖 unique_max / tie_max / no_solution / requires_clearance 等多种题型
    """
    random.seed(seed)
    ws = _parse_time(work_start)
    we = _parse_time(work_end)

    mode = difficulty_profile.get('target_mode', 'unique_max')
    min_len = int(difficulty_profile.get('min_len', 60))
    max_len = int(difficulty_profile.get('max_len', 120))
    max_resample = int(difficulty_profile.get('max_resample', 200))
    require_clearance = bool(difficulty_profile.get('require_clearance', True))

    for _ in range(max_resample):
        schedules = _build_week_for_mode(days, ws, we, mode, min_len, max_len, require_clearance)
        hewei = schedules['hewei']
        fengjie = schedules['fengjie']
        gaolei = schedules['gaolei']
        res_with = compute_best_meeting(hewei, fengjie, gaolei, work_start, work_end, 30, True)
        res_without = compute_best_meeting(hewei, fengjie, gaolei, work_start, work_end, 30, False)

        if mode == 'unique_max':
            if res_with[0] > 0 and res_with[1] == 1:
                return schedules
        elif mode == 'tie_max':
            if res_with[0] > 0 and res_with[1] >= 2:
                return schedules
        elif mode == 'no_solution':
            if res_with == [0, 0]:
                return schedules
        elif mode == 'requires_clearance':
            if res_with[0] > 0 and (res_without == [0, 0] or res_without[0] < res_with[0]):
                return schedules

    return _build_week_for_mode(days, ws, we, 'no_solution', min_len, max_len, require_clearance)

# ==================== 题面描述格式化 ====================
def format_schedule(person: List[Dict], name: str) -> str:
    """
    将结构化日程转为中文描述：
    - only_free：'以下时间空闲：...'
    - only_busy：'以下时间无法安排会议：...'
    句尾不添加多余标点；若无区间则给出“(无具体时段)”提示。
    """
    lines = [f"{name} 当地时间本周的日程安排如下："]
    for d in person:
        day = d['day']
        typ = d['type']
        ivs = d['intervals']
        if typ == 'only_free':
            prefix = f"{day}：以下时间空闲："
        else:
            prefix = f"{day}：以下时间无法安排会议："
        if ivs:
            lines.append(prefix + "、".join(ivs))
        else:
            lines.append(prefix + "(无具体时段)")
    return "\n".join(lines)

# ==================== 自测 ====================
if __name__ == "__main__":
    work_start = '09:00'
    work_end = '17:00'
    days = ['星期一','星期二','星期三','星期四','星期五']
    for mode in ['unique_max', 'tie_max', 'no_solution', 'requires_clearance']:
        dp = {
            'target_mode': mode,
            'grid': 30,
            'min_len': 60,
            'max_len': 120,
            'require_clearance': True,
            'max_resample': 100
        }
        schedules = gen_schedules_advanced(work_start, work_end, days, dp, seed=12345)
        hewei = schedules['hewei']
        fengjie = schedules['fengjie']
        gaolei = schedules['gaolei']
        print("==== Mode:", mode, "====")
        print(format_schedule(hewei, '赫伟'))
        print(format_schedule(fengjie, '丰杰'))
        print(format_schedule(gaolei, '郜磊'))
        print("With clearance:", compute_best_meeting(hewei, fengjie, gaolei, work_start, work_end, 30, True))
        print("Without clearance:", compute_best_meeting(hewei, fengjie, gaolei, work_start, work_end, 30, False))