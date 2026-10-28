# time_sequence_5.py
from typing import List, Tuple, Union, Optional

def to_minutes(h: int, m: int) -> int:
    """
    Convert hour and minute to absolute minutes within a day [0, 1440).
    """
    return (h % 24) * 60 + (m % 60)

def to_hhmm(mins: int) -> str:
    """
    Format minutes-of-day to 'HH:MM' in 24-hour clock.
    """
    mins = mins % 1440
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"

def _normalize_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Normalize and merge overlapping intervals within [0, 1440).
    Intervals are [start, end) with end exclusive.
    """
    ivs = [(max(0, s), min(1440, e)) for s, e in intervals if s < e]
    if not ivs:
        return []
    ivs.sort()
    merged = [ivs[0]]
    for s, e in ivs[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged

def _intersect_intervals(a: List[Tuple[int, int]], b: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Intersect two lists of [start, end) intervals within [0, 1440).
    """
    ia = _normalize_intervals(a)
    ib = _normalize_intervals(b)
    i, j = 0, 0
    res: List[Tuple[int, int]] = []
    while i < len(ia) and j < len(ib):
        s1, e1 = ia[i]
        s2, e2 = ib[j]
        s = max(s1, s2)
        e = min(e1, e2)
        if s < e:
            res.append((s, e))
        if e1 < e2:
            i += 1
        else:
            j += 1
    return res

def _shift_to_baseline(local_min: int, local_utc_offset: int, baseline_utc_offset: int) -> int:
    """
    Convert local minutes-of-day to baseline minutes-of-day by UTC offsets.
    Result is wrapped into [0, 1440).
    """
    delta_h = baseline_utc_offset - local_utc_offset
    return (local_min + delta_h * 60) % 1440

def _convert_daily_window_to_baseline(
    local_windows: List[Tuple[int, int]],
    local_utc_offset: int,
    baseline_utc_offset: int
) -> List[Tuple[int, int]]:
    """
    Convert a list of daily windows [start, end) from local time to baseline time.
    Handles day wrap by splitting intervals if necessary.
    """
    res: List[Tuple[int, int]] = []
    for s, e in local_windows:
        s_b = _shift_to_baseline(s, local_utc_offset, baseline_utc_offset)
        e_b = _shift_to_baseline(e, local_utc_offset, baseline_utc_offset)
        if s_b < e_b:
            res.append((s_b, e_b))
        elif s_b > e_b:
            res.append((0, e_b))
            res.append((s_b, 1440))
        else:
            # s_b == e_b implies either full-day or empty; ignore zero-length here
            pass
    return _normalize_intervals(res)

def _subtract_interval_list(
    base: List[Tuple[int, int]],
    cut: List[Tuple[int, int]]
) -> List[Tuple[int, int]]:
    """
    Subtract cut intervals from base intervals, both lists are [start, end) within [0, 1440).
    Returns the remaining intervals.
    """
    base_norm = _normalize_intervals(base)
    cut_norm = _normalize_intervals(cut)
    if not base_norm or not cut_norm:
        return base_norm

    res: List[Tuple[int, int]] = base_norm
    for cs, ce in cut_norm:
        new_res: List[Tuple[int, int]] = []
        for bs, be in res:
            if ce <= bs or cs >= be:
                new_res.append((bs, be))
            else:
                if bs < cs:
                    new_res.append((bs, max(bs, cs)))
                if ce < be:
                    new_res.append((min(be, ce), be))
        res = _normalize_intervals(new_res)
        if not res:
            break
    return res

def _apply_buffer_to_windows(local_windows: List[Tuple[int, int]], buf_before: int, buf_after: int) -> List[Tuple[int, int]]:
    """
    Apply per-city buffers to each continuous availability block:
    shift start by +buf_before and end by -buf_after for every block.
    """
    adjusted = [(s + buf_before, e - buf_after) for s, e in local_windows]
    return _normalize_intervals(adjusted)

def _enumerate_aligned_starts(effective_windows: List[Tuple[int, int]], slot_minutes: int) -> List[int]:
    """
    Enumerate aligned start times within effective windows by slot_minutes.
    """
    per_day_starts: List[int] = []
    for s, e in effective_windows:
        if slot_minutes <= 0:
            continue
        t = (s // slot_minutes) * slot_minutes
        if t < s:
            t += slot_minutes
        while t < e:
            per_day_starts.append(t)
            t += slot_minutes
    return per_day_starts

def _daily_max_and_count(
    lon_windows_baseline: List[Tuple[int, int]],
    sg_windows_baseline: List[Tuple[int, int]],
    ny_windows_baseline: Optional[List[Tuple[int, int]]],
    slot_minutes: int,
    ny_flex_minutes: int
) -> Tuple[int, int]:
    """
    Compute per-day global maximum duration and how many aligned starts reach it.
    """
    if ny_windows_baseline is None:
        tmp = _intersect_intervals(lon_windows_baseline, sg_windows_baseline)
        effective_windows = tmp
    else:
        tmp = _intersect_intervals(lon_windows_baseline, sg_windows_baseline)
        effective_windows = _intersect_intervals(tmp, ny_windows_baseline)

    per_day_starts = _enumerate_aligned_starts(effective_windows, slot_minutes)
    if not per_day_starts:
        return 0, 0

    def window_end_for(t: int) -> int:
        for ws, we in effective_windows:
            if ws <= t and t < we:
                return we
        return t

    global_max = 0
    count_max = 0
    for t in per_day_starts:
        we = window_end_for(t)
        avail = max(0, we - t)
        dur = ny_flex_minutes if ny_flex_minutes < avail else avail
        if dur > global_max:
            global_max = dur
            count_max = 1
        elif dur == global_max:
            count_max += 1
    return global_max, count_max

def _compute_london_options_full(
    ny_utc_offset: int,
    lon_utc_offset: int,
    sg_utc_offset: int,
    ny_start_local_m: int,
    ny_end_local_m: int,
    lon_start_local_m: int,
    lon_end_local_m: int,
    lon_extend_end_m: int,
    sg_start_local_m: int,
    sg_lunch_start_m: int,
    sg_lunch_end_m: int,
    sg_end_local_m: int,
    weekdays: int,
    slot_minutes: int,
    ny_flex_minutes: int,
    ny_flex_anytime: bool,
    lon_extend_dir_start_enabled: bool,
    lon_extend_dir_end_enabled: bool,
    sg_lunch_enabled: bool,
    lon_black_days: int,
    lon_black_start_local_m: int,
    lon_black_end_local_m: int,
    ny_buf_before: int,
    ny_buf_after: int,
    lon_buf_before: int,
    lon_buf_after: int,
    sg_buf_before: int,
    sg_buf_after: int
) -> str:
    """
    Core computation with full parameter set.
    Returns: 'X 分钟, Y 个选项'
    """
    # London base window with extension policy
    lon_start_ext = lon_start_local_m - (lon_extend_end_m if lon_extend_dir_start_enabled else 0)
    lon_end_ext = lon_end_local_m + (lon_extend_end_m if lon_extend_dir_end_enabled else 0)
    lon_windows_local_base = [(max(0, lon_start_ext), min(1440, lon_end_ext))]

    # Apply London buffers
    lon_windows_local_base = _apply_buffer_to_windows(lon_windows_local_base, lon_buf_before, lon_buf_after)
    lon_windows_normal = _convert_daily_window_to_baseline(lon_windows_local_base, lon_utc_offset, lon_utc_offset)

    # London blackout day windows (subtract blackout interval, London is baseline so direct subtract)
    blackout_local = _normalize_intervals([(lon_black_start_local_m, lon_black_end_local_m)])
    lon_windows_blackout_local = _subtract_interval_list(lon_windows_local_base, blackout_local)
    lon_windows_blackout = _convert_daily_window_to_baseline(lon_windows_blackout_local, lon_utc_offset, lon_utc_offset)

    # Singapore windows with or without lunch, apply buffers to each block, then convert to baseline
    if sg_lunch_enabled:
        sg_windows_local = [
            (sg_start_local_m, sg_lunch_start_m),
            (sg_lunch_end_m, sg_end_local_m)
        ]
    else:
        sg_windows_local = [(sg_start_local_m, sg_end_local_m)]
    sg_windows_local = _apply_buffer_to_windows(sg_windows_local, sg_buf_before, sg_buf_after)
    sg_windows_baseline = _convert_daily_window_to_baseline(sg_windows_local, sg_utc_offset, lon_utc_offset)

    # New York windows depending on flexibility; if flexible, ignore NY window and buffers
    if ny_flex_anytime:
        ny_windows_baseline = None
    else:
        ny_windows_local = [(ny_start_local_m, ny_end_local_m)]
        ny_windows_local = _apply_buffer_to_windows(ny_windows_local, ny_buf_before, ny_buf_after)
        ny_windows_baseline = _convert_daily_window_to_baseline(ny_windows_local, ny_utc_offset, lon_utc_offset)

    # Per-day maxima for two day types
    max_norm, cnt_norm = _daily_max_and_count(
        lon_windows_normal, sg_windows_baseline, ny_windows_baseline, slot_minutes, ny_flex_minutes
    )
    max_blk, cnt_blk = _daily_max_and_count(
        lon_windows_blackout, sg_windows_baseline, ny_windows_baseline, slot_minutes, ny_flex_minutes
    )

    # Weekly aggregation by global maximum
    global_max = max(max_norm, max_blk)
    total_count = 0
    # Normal days contribute only if they share the global maximum
    normal_days = max(0, weekdays - max(0, lon_black_days))
    if max_norm == global_max and global_max > 0 and cnt_norm > 0 and normal_days > 0:
        total_count += cnt_norm * normal_days
    # Blackout days contribute only if they share the global maximum
    blk_days = max(0, lon_black_days)
    if max_blk == global_max and global_max > 0 and cnt_blk > 0 and blk_days > 0:
        total_count += cnt_blk * blk_days

    # Fallback: if no starts exist at all, return zero pair
    if global_max <= 0 or total_count <= 0:
        return '0 分钟, 0 个选项'

    return f'{global_max} 分钟, {total_count} 个选项'

def compute_london_options_text(*args: Union[int, bool]) -> str:
    """
    Compatibility wrapper:
    - If called with 28 args: use full model.
    - If called with 16 args (legacy): fill missing args with defaults/inferred values.
    """
    if len(args) == 28:
        return _compute_london_options_full(*args)  # type: ignore
    elif len(args) == 16:
        (
            ny_utc_offset,
            lon_utc_offset,
            sg_utc_offset,
            ny_start_local_m,
            ny_end_local_m,
            lon_start_local_m,
            lon_end_local_m,
            lon_extend_end_m,
            sg_start_local_m,
            sg_lunch_start_m,
            sg_lunch_end_m,
            sg_end_local_m,
            weekdays,
            slot_minutes,
            ny_flex_minutes,
            ny_flex_anytime
        ) = args

        # Infer or default missing policy parameters
        lon_extend_dir_start_enabled = False
        lon_extend_dir_end_enabled = False
        sg_lunch_enabled = True if (sg_lunch_end_m > sg_lunch_start_m) else False
        lon_black_days = 0
        lon_black_start_local_m = 0
        lon_black_end_local_m = 0
        ny_buf_before = 0
        ny_buf_after = 0
        lon_buf_before = 0
        lon_buf_after = 0
        sg_buf_before = 0
        sg_buf_after = 0

        return _compute_london_options_full(
            ny_utc_offset,
            lon_utc_offset,
            sg_utc_offset,
            ny_start_local_m,
            ny_end_local_m,
            lon_start_local_m,
            lon_end_local_m,
            lon_extend_end_m,
            sg_start_local_m,
            sg_lunch_start_m,
            sg_lunch_end_m,
            sg_end_local_m,
            weekdays,
            slot_minutes,
            ny_flex_minutes,
            ny_flex_anytime,
            lon_extend_dir_start_enabled,
            lon_extend_dir_end_enabled,
            sg_lunch_enabled,
            lon_black_days,
            lon_black_start_local_m,
            lon_black_end_local_m,
            ny_buf_before,
            ny_buf_after,
            lon_buf_before,
            lon_buf_after,
            sg_buf_before,
            sg_buf_after
        )
    else:
        # Unsupported signature length: be robust and return zero result
        return '0 分钟, 0 个选项'