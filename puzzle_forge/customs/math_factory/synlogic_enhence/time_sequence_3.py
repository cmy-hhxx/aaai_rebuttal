# time_sequence_7.py
import random
from typing import List, Tuple
from functools import lru_cache

def choose_step() -> int:
    """选择能整除60的安全步长"""
    return random.choice([5, 10, 15])

def choose_align_unit(step: int) -> int:
    """
    选择与步长相容的对齐单位，偏好常见的 15, 30, 60
    """
    candidates = [15, 30, 60]
    valid = [x for x in candidates if x % step == 0]
    if not valid:
        if 60 % step == 0:
            return 60
        return step
    return random.choice(valid)

def rand_inclusive(a: int, b: int) -> int:
    """返回闭区间[a, b]内的随机整数"""
    if a > b:
        a, b = b, a
    return random.randint(a, b)

def align_to_step(x: int, step: int) -> int:
    """将分钟数向下对齐至step的整数倍"""
    if step <= 0:
        return x
    return x - (x % step)

def pick_multiple(step: int, min_m: int, max_m: int) -> int:
    """在[min_m, max_m]中选取step的整数倍"""
    if min_m > max_m:
        min_m, max_m = max_m, min_m
    lo = (min_m + step - 1) // step
    hi = max(lo, max_m // step)
    k = rand_inclusive(lo, hi)
    return max(step, k * step)

def pick_len_bounds(step: int, min_slots: int, max_slots: int) -> List[int]:
    """
    选择区间长度上下界，单位为分钟，均为step的倍数，且low < high
    """
    if min_slots < 1:
        min_slots = 1
    if max_slots < min_slots + 1:
        max_slots = min_slots + 1
    low_slots = rand_inclusive(min_slots, max_slots - 1)
    high_slots = rand_inclusive(low_slots + 1, max_slots)
    return [low_slots * step, high_slots * step]

def _intervals_non_overlapping(intervals: List[Tuple[int, int]]) -> bool:
    s = sorted(intervals)
    for i in range(1, len(s)):
        if s[i][0] < s[i-1][1]:
            return False
    return True

def gen_intervals(day_start: int, day_end: int, count: int, min_len: int, max_len: int, step: int) -> List[List[int]]:
    """
    生成count个不重叠的区间[start, end)，落在[day_start, day_end)内，
    区间长度在[min_len, max_len]之间，且起止均为step对齐。
    返回 [[start, end], ...]，若生成失败则返回空列表。
    """
    if count <= 0:
        return []
    min_len = max(step, align_to_step(min_len, step))
    max_len = max(min_len, align_to_step(max_len, step))
    total_slots = (day_end - day_start) // step
    if total_slots <= 0:
        return []
    attempts = 0
    best: List[List[int]] = []
    while attempts < 3000:
        attempts += 1
        lengths = []
        for _ in range(count):
            L = random.randrange(min_len, max_len + step, step)
            lengths.append(L)
        random.shuffle(lengths)
        occupied: List[Tuple[int, int]] = []
        ok = True
        for L in lengths:
            slots_needed = max(1, L // step)
            placed = False
            for _ in range(200):
                start_slot = rand_inclusive(0, max(0, total_slots - slots_needed))
                start = day_start + start_slot * step
                end = start + L
                cand = (start, end)
                if all(not (cand[0] < e and cand[1] > s) for s, e in occupied):
                    occupied.append(cand)
                    placed = True
                    break
            if not placed:
                ok = False
                break
        if not ok:
            continue
        intervals = [[s, e] for s, e in sorted(occupied)]
        if len(intervals) == count and _intervals_non_overlapping([(x[0], x[1]) for x in intervals]):
            best = intervals
            break
    return best

def format_time(minute: int) -> str:
    h = minute // 60
    m = minute % 60
    return f"{h:02d}:{m:02d}"

def format_intervals(intervals: List[List[int]]) -> str:
    """将区间列表格式化为 HH:MM-HH:MM; ... 若无则输出 无"""
    if not intervals:
        return "无"
    parts = []
    for s, e in sorted(intervals):
        parts.append(f"{format_time(s)}-{format_time(e)}")
    return "; ".join(parts) if parts else "无"

def _intervals_to_slots(intervals: List[List[int]], day_start: int, day_end: int, step: int) -> List[bool]:
    n = max(0, (day_end - day_start) // step)
    arr = [False] * n
    for s, e in intervals:
        if s < day_start or e > day_end or s >= e:
            continue
        s0 = max(0, (s - day_start) // step)
        e0 = min(n, (e - day_start) // step)
        for i in range(s0, e0):
            arr[i] = True
    return arr

def _classify_slots(type_arrs: Tuple[List[bool], List[bool], List[bool]]) -> List[int]:
    """
    针对某一场景的三组可用槽数组(d, c, l)分类：
    2 = 三组均可用；
    1 = 导演忙（可通过取消翻转为可用，消耗K配额）；
    3 = 摄影忙（可用拼接跳过该连续段）；
    -1 = 其他不可用。
    """
    d, c, l = type_arrs
    n = len(d)
    out = [0]*n
    for i in range(n):
        if d[i] and c[i] and l[i]:
            out[i] = 2
        elif (not d[i]) and c[i] and l[i]:
            out[i] = 1
        elif d[i] and (not c[i]) and l[i]:
            out[i] = 3
        else:
            out[i] = -1
    return out

def _general_all_free(d_ext, d_int, c_ext, c_int, l_ext, l_int) -> List[bool]:
    """
    切换缓冲的通用判定：
    只要导演在外或内任一可用，摄影在外或内任一可用，灯光在外或内任一可用，则该槽在缓冲期可用
    """
    n = len(d_ext)
    gen = [False]*n
    for i in range(n):
        d_ok = d_ext[i] or d_int[i]
        c_ok = c_ext[i] or c_int[i]
        l_ok = l_ext[i] or l_int[i]
        gen[i] = d_ok and c_ok and l_ok
    return gen

def compute_longest(day_start: int, day_end: int, step: int,
                    switch_cost: int, cancel_limit: int, splice_cost: int,
                    d_ext_free: List[List[int]], d_int_free: List[List[int]],
                    c_ext_free: List[List[int]], c_int_free: List[List[int]],
                    l_ext_free: List[List[int]], l_int_free: List[List[int]],
                    align_unit: int, splice_times: int, max_switches: int) -> Tuple[int, int]:
    """
    返回(最长会议时长(分钟), 达到该最长时长的起始时间选项个数)

    规则摘要：
    - 起点需落在工作日范围内，且同时对齐到步长与 align_unit 网格；可在外景或内景开始
    - 最多 max_switches 次切换；每次插入 switch_cost 分钟缓冲，缓冲期间需通用可用，且计入会议时长
    - 导演可取消不超过 cancel_limit 分钟采访，按槽计数翻转导演忙槽为可用
    - 摄影总共可至多 splice_times 次拼接，每次可跳过连续不超过 splice_cost 分钟的摄影忙槽，跳过不计时长，且不能跨越他方忙碌
    """
    # 转为槽布尔数组
    d_ext = _intervals_to_slots(d_ext_free, day_start, day_end, step)
    d_int = _intervals_to_slots(d_int_free, day_start, day_end, step)
    c_ext = _intervals_to_slots(c_ext_free, day_start, day_end, step)
    c_int = _intervals_to_slots(c_int_free, day_start, day_end, step)
    l_ext = _intervals_to_slots(l_ext_free, day_start, day_end, step)
    l_int = _intervals_to_slots(l_int_free, day_start, day_end, step)

    n = (day_end - day_start) // step
    if n <= 0:
        return (0, 0)

    ext_cls = _classify_slots((d_ext, c_ext, l_ext))
    int_cls = _classify_slots((d_int, c_int, l_int))
    gen_all = _general_all_free(d_ext, d_int, c_ext, c_int, l_ext, l_int)

    K0 = max(0, cancel_limit // step)          # 可翻转导演忙的槽数（按步长格计数）
    travel_slots = max(0, switch_cost // step) # 切换缓冲槽数（计时长，按步长格计数）
    sp_slots = max(0, splice_cost // step)     # 单次可跳过的摄影忙槽数（按步长格计数）
    S = max(0, splice_times)                   # 拼接次数上限（总计）
    SW = max(0, max_switches)                  # 切换次数上限

    @lru_cache(None)
    def f(i: int, t: int, K: int, used_sp: int, used_sw: int) -> int:
        """
        DP：从槽 i 开始，场景 t（0外景/1内景），剩余导演翻转 K，
        已用拼接次数 used_sp（总计），已用切换次数 used_sw 的最大可行长度（以槽计）
        """
        if i >= n:
            return 0
        cls_arr = ext_cls if t == 0 else int_cls
        best = 0

        # 尝试在当前场景推进一槽
        c = cls_arr[i]
        if c == 2:
            best = max(best, 1 + f(i+1, t, K, used_sp, used_sw))
        elif c == 1:
            # 导演忙，可用取消翻转
            if K > 0:
                best = max(best, 1 + f(i+1, t, K-1, used_sp, used_sw))
        elif c == 3:
            # 摄影忙，若可拼接则跳过<=sp_slots的连续摄影忙段（不计时长）
            if used_sp < S and sp_slots > 0:
                j = i
                cnt = 0
                while j < n and cls_arr[j] == 3 and cnt < sp_slots:
                    j += 1
                    cnt += 1
                best = max(best, f(j, t, K, used_sp + 1, used_sw))
        # 其他情况不可在当前场景推进

        # 尝试切换场景（插入缓冲槽，计时长）
        if used_sw < SW and travel_slots > 0:
            ok = True
            for off in range(travel_slots):
                j = i + off
                if j >= n or not gen_all[j]:
                    ok = False
                    break
            if ok:
                t2 = 1 - t
                best = max(best, travel_slots + f(i + travel_slots, t2, K, used_sp, used_sw + 1))

        return best

    def is_aligned_slot(slot_index: int) -> bool:
        minute = day_start + slot_index * step
        # 步长对齐已天然满足；此处检查对齐单位
        return (minute % align_unit) == 0

    max_len_slots = 0
    starts_with_max = 0
    for s in range(n):
        if not is_aligned_slot(s):
            continue
        len_ext = f(s, 0, K0, 0, 0)
        len_int = f(s, 1, K0, 0, 0)
        local_best = max(len_ext, len_int)
        if local_best > max_len_slots:
            max_len_slots = local_best
            starts_with_max = 1 if local_best > 0 else 0
        elif local_best == max_len_slots and local_best > 0:
            starts_with_max += 1

    return (max_len_slots * step, starts_with_max)

def choose_align_unit_unique(step: int, day_start: int, day_end: int,
                             switch_cost: int, cancel_limit: int, splice_cost: int,
                             d_ext_free: List[List[int]], d_int_free: List[List[int]],
                             c_ext_free: List[List[int]], c_int_free: List[List[int]],
                             l_ext_free: List[List[int]], l_int_free: List[List[int]],
                             splice_times: int, max_switches: int) -> int:
    """
    选择能与步长相容且更可能产生唯一起点的对齐单位：
    依次尝试 60, 30, 15（仅保留能被step整除的选项），
    若某候选对齐下 (最长时长 > 0 且 起始计数 == 1)，立即返回该对齐单位；
    否则选择最长时长最大的候选（若并列，选择起始计数较小的）。
    """
    candidates = [60, 30, 15]
    valid = [x for x in candidates if x % step == 0]
    best_unit = None
    best_dur = -1
    best_count = None
    for u in valid:
        dur, cnt = compute_longest(day_start, day_end, step,
                                   switch_cost, cancel_limit, splice_cost,
                                   d_ext_free, d_int_free, c_ext_free, c_int_free, l_ext_free, l_int_free,
                                   u, splice_times, max_switches)
        if dur > 0 and cnt == 1:
            return u
        # 记录最优备选：时长优先，计数次优（越少越好）
        if dur > best_dur or (dur == best_dur and (best_count is None or (cnt > 0 and cnt < best_count))):
            best_unit = u
            best_dur = dur
            best_count = cnt
    # 若均无法唯一，返回最佳备选；若无有效候选，则退化为步长本身
    if best_unit is not None:
        return best_unit
    return step

def get_longest_duration(day_start: int, day_end: int, step: int,
                         switch_cost: int, cancel_limit: int, splice_cost: int,
                         d_ext_free: List[List[int]], d_int_free: List[List[int]],
                         c_ext_free: List[List[int]], c_int_free: List[List[int]],
                         l_ext_free: List[List[int]], l_int_free: List[List[int]],
                         align_unit: int, splice_times: int, max_switches: int) -> int:
    """仅返回最长会议时长（分钟）"""
    dur, _ = compute_longest(day_start, day_end, step,
                             switch_cost, cancel_limit, splice_cost,
                             d_ext_free, d_int_free, c_ext_free, c_int_free, l_ext_free, l_int_free,
                             align_unit, splice_times, max_switches)
    return dur

def choose_min_target(max_dur: int) -> int:
    """
    在不超过最长时长的范围内选取目标阈值，保证答案断言可通过。
    下界取 max(20, max_dur//2)，上界取 max_dur；若上界<下界则返回上界。
    """
    if max_dur <= 0:
        return 0
    low = max(20, max_dur // 2)
    high = max_dur
    if high < low:
        return high
    return rand_inclusive(low, high)