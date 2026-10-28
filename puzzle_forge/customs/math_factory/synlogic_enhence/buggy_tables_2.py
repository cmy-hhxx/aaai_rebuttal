# buggy_tables_5.py
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import random
from typing import List, Any, Tuple, Optional, Dict, Set


# ----------------------------
# Small utility generators
# ----------------------------
def sample_list(lst: List[Any], k: int) -> List[Any]:
    if k <= 0:
        return []
    if k >= len(lst):
        return lst[:]
    return random.sample(lst, k)


def choose_two_distinct(lst: List[str]) -> Tuple[str, str]:
    if len(lst) < 2:
        raise ValueError("Need at least two candidates")
    a, b = random.sample(lst, 2)
    return a, b


def gen_start_ts() -> str:
    day = random.randint(1, 25)
    hour = random.randint(5, 8)
    minute = random.choice([0, 5, 10, 15, 20, 30, 45])
    dt = datetime(2026, 1, day, hour, minute)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_zone_names(n: int) -> List[str]:
    # Generate zone names as ['A','B','C',...]
    n = max(1, min(n, 26))
    return [chr(65 + i) for i in range(n)]


def select_sigma() -> float:
    return random.choice([2.5, 3.0, 3.5])


def select_dedup_policy() -> str:
    return random.choice(['keep_max_ts', 'keep_min_ts'])


def select_subset_template() -> str:
    return random.choice([
        'zone_and_pump',
        'zone_and_weekday',
        'pump_and_fan',
        'weekday_only',
        'zone_only'
    ])


def select_clipping_method() -> str:
    return random.choice(['sigma', 'iqr'])


def select_iqr_k() -> float:
    return random.choice([1.5, 2.0])


def select_variance_mode() -> str:
    return random.choice(['population', 'sample'])


def select_normalize_mode() -> str:
    return random.choice(['none', 'zone_center', 'weekday_center'])


def select_gate_mode() -> str:
    return random.choice(['both', 'independent'])


def select_rolling_median_w() -> int:
    return random.choice([1, 3])


def _round_two_str(val: float) -> str:
    d = Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{d:.2f}"


def _round_half_up_float(val: float, places: int = 2) -> float:
    d = Decimal(str(val)).quantize(Decimal('0.' + '0' * places), rounding=ROUND_HALF_UP)
    return float(d)


def _parse_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if s == '' or s.lower() in {'null', 'none', 'nan'}:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def _parse_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    return str(val).strip()


def _parse_ts(ts: Any) -> Optional[datetime]:
    s = _parse_str(ts)
    if s is None or s == '':
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        try:
            if s.endswith('Z'):
                return datetime.fromisoformat(s[:-1])
            return datetime.fromisoformat(s)
        except Exception:
            return None


# ----------------------------
# Stats helpers
# ----------------------------
def _population_mean_std(vals: List[Optional[float]]) -> Tuple[Optional[float], Optional[float]]:
    data = [v for v in vals if v is not None]
    n = len(data)
    if n == 0:
        return None, None
    mean = sum(data) / n
    var = sum((x - mean) ** 2 for x in data) / n
    std = var ** 0.5
    return mean, std


def _variance(vals: List[Optional[float]], mode: str) -> Optional[float]:
    data = [v for v in vals if v is not None]
    n = len(data)
    if n < 2:
        return None
    mean = sum(data) / n
    if mode == 'sample':
        if n - 1 <= 0:
            return None
        var = sum((x - mean) ** 2 for x in data) / (n - 1)
    else:
        var = sum((x - mean) ** 2 for x in data) / n
    return var


def _quantile(data: List[float], q: float) -> Optional[float]:
    arr = sorted(data)
    n = len(arr)
    if n == 0:
        return None
    pos = (n - 1) * q
    lower = int(pos)
    upper = lower + 1
    if upper >= n:
        return arr[lower]
    frac = pos - lower
    return arr[lower] * (1 - frac) + arr[upper] * frac


def _iqr_bounds(vals: List[Optional[float]], k: float) -> Optional[Tuple[float, float]]:
    data = [v for v in vals if v is not None]
    if len(data) == 0:
        return None
    q1 = _quantile(data, 0.25)
    q3 = _quantile(data, 0.75)
    if q1 is None or q3 is None:
        return None
    iqr = q3 - q1
    low = q1 - k * iqr
    high = q3 + k * iqr
    return low, high


def _median(data: List[float]) -> Optional[float]:
    if not data:
        return None
    arr = sorted(data)
    n = len(arr)
    mid = n // 2
    if n % 2 == 1:
        return arr[mid]
    return (arr[mid - 1] + arr[mid]) / 2.0


def _rolling_median(vals: List[Optional[float]], w: int) -> List[Optional[float]]:
    if w <= 1:
        return vals[:]
    n = len(vals)
    out: List[Optional[float]] = []
    half = w // 2
    for i in range(n):
        window = []
        for j in range(max(0, i - half), min(n, i + half + 1)):
            v = vals[j]
            if v is not None:
                window.append(v)
        if not window:
            out.append(None)
        else:
            m = _median(window)
            out.append(m)
    return out


# ----------------------------
# Render helpers
# ----------------------------
def render_columns(header: List[str], columns: List[List[Any]]) -> str:
    parts = []
    for j, name in enumerate(header):
        vals = columns[j]
        rendered_vals = []
        for v in vals:
            if isinstance(v, float):
                rendered_vals.append(_round_two_str(v))
            elif isinstance(v, int):
                rendered_vals.append(str(v))
            elif isinstance(v, str):
                rendered_vals.append(v)
            elif v is None:
                rendered_vals.append("null")
            else:
                rendered_vals.append(str(v))
        parts.append(f"{name}: [{', '.join(rendered_vals)}]")
    return "; ".join(parts)


def render_header_with_index(header: List[str]) -> str:
    return ", ".join([f"{i}:{name}" for i, name in enumerate(header)])


def render_dedup_desc(policy: str) -> str:
    base = "按 timestamp 去重：若同一 timestamp 出现多条记录，"
    if policy == 'keep_min_ts':
        keep = "保留最早的一条（相同时间下保留先出现的记录）"
    else:
        keep = "保留最晚的一条（相同时间下保留后出现的记录）"
    order = "；去重完成后按时间升序排列（不可解析时间视为最小）"
    return base + keep + order


def render_subset_desc(template: str, allowed_zones: List[str], pump_threshold: float, fan_threshold: float, allowed_weekdays: List[str]) -> str:
    z = ", ".join(allowed_zones)
    w = ", ".join(allowed_weekdays)
    if template == 'zone_and_pump':
        return f"满足 zone_id ∈ {{{z}}} 且 pump_minutes>{pump_threshold}"
    elif template == 'zone_and_weekday':
        return f"满足 zone_id ∈ {{{z}}} 且 weekday ∈ {{{w}}}"
    elif template == 'pump_and_fan':
        return f"满足 pump_minutes>{pump_threshold} 且 fan_speed_rpm>{fan_threshold}"
    elif template == 'weekday_only':
        return f"满足 weekday ∈ {{{w}}}"
    else:
        return f"满足 zone_id ∈ {{{z}}}"


def render_clipping_desc(method: str, sigma_k: float, iqr_k: float) -> str:
    if method == 'iqr':
        return f"各自进行 IQR 去极值（以 Q1 与 Q3 为界，容忍系数 {iqr_k}）"
    return f"各自进行 {sigma_k}σ 去极值（相对各自的均值与标准差，忽略空值）"


def render_variance_desc(mode: str) -> str:
    if mode == 'sample':
        return "样本方差（除以 n-1）"
    return "总体方差（除以 n）"


def render_normalize_desc(mode: str, allowed_zones: List[str]) -> str:
    if mode == 'zone_center':
        z = ", ".join(allowed_zones)
        return f"在 zone_id ∈ {{{z}}} 的记录中，对每个指标按各自分区的中位数做中心化（值减去该分区中位数）"
    elif mode == 'weekday_center':
        return "按 weekday 对每个指标做中位数中心化（值减去该 weekday 的中位数）"
    else:
        return "不做中心化"


def render_gate_desc(gating: str) -> str:
    if gating == 'both':
        return "仅保留同时通过去极值筛选的行（两指标都不为缺失）"
    else:
        return "各指标独立统计（不强制两者同时有效）"


def render_rolling_desc(w: int) -> str:
    if w <= 1:
        return "滚动中位数平滑（窗口 1，等效不平滑；采用居中窗口，边界处使用可用样本）"
    return f"滚动中位数平滑（窗口 {w}，采用居中窗口，边界处使用可用样本）"


def render_pipeline_notes() -> str:
    return ("处理顺序为：严格剔除占位（按列索引 j 从底部删除 j 个元素，不基于值内容识别）→按最短列重组为行→按 timestamp 去重并升序排序→"
            "所有数值统一按题面展示的两位小数进行计算（ROUND_HALF_UP）→"
            "中心化→滚动中位数→去极值→基于原始字段进行子集筛选→按 gating 计算方差→取绝对差；"
            "中心化与去极值均在去重后的全体行上按列独立计算并忽略缺失值；"
            "分位数采用线性插值：对升序数据，pos=(n-1)*q，按相邻两点线性插值；中位数为奇数样本取中位，偶数样本取两中位的平均；"
            "σ剪裁按 abs(v-mean) ≤ k*std（std 为总体标准差）；IQR 剪裁区间为 [Q1-k*IQR, Q3+k*IQR]；"
            "gating=independent 时分别对两指标的非缺失样本独立计算方差，不强制同一行同时有效；"
            "不可解析时间在排序时视为最小；最终答案四舍五入（ROUND_HALF_UP）保留两位小数并以数字字符串输出（示例：12.30）。")


# ----------------------------
# Data generator (extended, smaller scale)
# ----------------------------
def _adjust_ts_to_weekday(ts: str, allowed_weekdays: List[str]) -> str:
    dt = _parse_ts(ts)
    if dt is None or not allowed_weekdays:
        return ts
    weekdays_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    target_set = set(allowed_weekdays)
    for add_days in range(0, 14):
        candidate = dt + timedelta(days=add_days)
        if weekdays_map[candidate.weekday()] in target_set:
            return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")
    return ts


def _ensure_at_least_one_duplicate_after_forcing(timestamps: List[str], avoid_indices: Set[int]) -> None:
    if len(timestamps) < 2:
        return
    seen: Dict[str, int] = {}
    for s in timestamps:
        seen[s] = seen.get(s, 0) + 1
        if seen[s] >= 2:
            return
    candidates = [p for p in range(1, len(timestamps)) if (p not in avoid_indices and (p - 1) not in avoid_indices)]
    if not candidates:
        pos = 1
    else:
        pos = random.choice(candidates)
    timestamps[pos] = timestamps[pos - 1]


def generate_sensor_columns_ext(
    header: List[str],
    base_rows: int,
    start_ts: str,
    step_minutes: int,
    zone_names: List[str],
    duplicate_count: int,
    allowed_zones: List[str],
    pump_threshold: float,
    subset_template: str,
    allowed_weekdays: List[str],
    fan_threshold: float
) -> List[List[Any]]:
    col_count = len(header)
    ranges: Dict[str, Tuple[float, float]] = {
        'temp_c': (random.uniform(20.0, 26.0), random.uniform(0.3, 1.5)),
        'humidity_pct': (random.uniform(45.0, 65.0), random.uniform(1.0, 4.0)),
        'co2_ppm': (random.uniform(350.0, 600.0), random.uniform(10.0, 40.0)),
        'light_lux': (random.uniform(12000.0, 20000.0), random.uniform(300.0, 1200.0)),
        'pump_minutes': (random.uniform(5.0, 18.0), random.uniform(1.0, 4.0)),
        'fan_speed_rpm': (random.uniform(1200.0, 1700.0), random.uniform(30.0, 90.0)),
        'soil_moisture_pct': (random.uniform(28.0, 40.0), random.uniform(0.8, 2.5)),
    }

    start_dt = _parse_ts(start_ts) or datetime(2026, 1, 3, 6, 15)
    timestamps = []
    for i in range(base_rows):
        dt = start_dt + timedelta(minutes=i * step_minutes)
        timestamps.append(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    dup_candidates = list(range(1, base_rows))
    if dup_candidates and duplicate_count >= 1:
        positions = sample_list(dup_candidates, min(duplicate_count, len(dup_candidates)))
        for pos in positions:
            timestamps[pos] = timestamps[pos - 1]

    zones = [random.choice(zone_names) for _ in range(base_rows)]

    pump_mean, pump_std = ranges['pump_minutes']
    pumps: List[Optional[float]] = []
    for _ in range(base_rows):
        val = random.gauss(pump_mean, pump_std)
        if random.random() < 0.05:
            pumps.append(None)
        else:
            pumps.append(max(0.0, float(val)))

    force_needed = 2
    indices = sample_list(list(range(base_rows)), force_needed)

    for idx in indices:
        if subset_template in ('zone_and_pump', 'zone_only', 'zone_and_weekday'):
            zones[idx] = random.choice(allowed_zones) if allowed_zones else zones[idx]
        if subset_template in ('zone_and_pump', 'pump_and_fan'):
            pumps[idx] = float(pump_threshold + random.uniform(1.0, 6.0))
        if subset_template in ('zone_and_weekday', 'weekday_only'):
            timestamps[idx] = _adjust_ts_to_weekday(timestamps[idx], allowed_weekdays)

        dt = _parse_ts(timestamps[idx])
        if dt:
            timestamps[idx] = (dt + timedelta(minutes=random.choice([-step_minutes, 0, step_minutes]))).strftime("%Y-%m-%dT%H:%M:%SZ")

    _ensure_at_least_one_duplicate_after_forcing(timestamps, set(indices))

    weekdays_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekdays = []
    for ts in timestamps:
        dt = _parse_ts(ts)
        weekdays.append(weekdays_map[dt.weekday()] if dt else random.choice(weekdays_map))

    numeric_cols: Dict[str, List[Optional[float]]] = {}
    for name, (mean, std) in ranges.items():
        if name == 'pump_minutes':
            continue
        arr: List[Optional[float]] = []
        for _ in range(base_rows):
            v = random.gauss(mean, std)
            arr.append(None if random.random() < 0.03 else float(v))
        numeric_cols[name] = arr

    if subset_template == 'pump_and_fan':
        fan_arr = numeric_cols.get('fan_speed_rpm', [])
        for idx in indices:
            if idx < len(fan_arr):
                fan_arr[idx] = float(fan_threshold + random.uniform(5.0, 40.0))

    columns: List[List[Any]] = []
    for j, name in enumerate(header):
        if name == 'timestamp':
            base = timestamps[:]
        elif name == 'zone_id':
            base = zones[:]
        elif name == 'pump_minutes':
            base = pumps[:]
        elif name == 'weekday':
            base = weekdays[:]
        elif name in numeric_cols:
            base = numeric_cols[name][:]
        else:
            mean = random.uniform(10.0, 100.0)
            std = random.uniform(1.0, 10.0)
            base = [float(random.gauss(mean, std)) for _ in range(base_rows)]

        defects = []
        for _ in range(j):
            if name == 'timestamp':
                if random.random() < 0.5:
                    defects.append("null")
                else:
                    dt = start_dt + timedelta(minutes=random.randint(-60, 60))
                    defects.append(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
            elif name == 'zone_id':
                defects.append(random.choice(zone_names))
            elif name == 'weekday':
                defects.append(random.choice(weekdays_map))
            else:
                if random.random() < 0.4:
                    defects.append(None)
                else:
                    defects.append(float(random.gauss(0.0, 1.0)))
        columns.append(base + defects)

    return columns


# ----------------------------
# Core solver (extended)
# ----------------------------
def _clean_columns_by_defect_from_cols(columns: List[List[Any]]) -> List[List[Any]]:
    if not columns:
        return []
    cleaned_per_col: List[List[Any]] = []
    for j, col in enumerate(columns):
        if j <= 0:
            cleaned_per_col.append(col[:])
        else:
            cleaned_per_col.append(col[:-j] if j <= len(col) else [])
    if not cleaned_per_col:
        return []
    min_len = min(len(c) for c in cleaned_per_col) if cleaned_per_col else 0
    return [c[:min_len] for c in cleaned_per_col]


def _reconstruct_rows_from_cols(cleaned_cols: List[List[Any]]) -> List[List[Any]]:
    if not cleaned_cols:
        return []
    n_rows = min(len(c) for c in cleaned_cols)
    col_count = len(cleaned_cols)
    return [[cleaned_cols[j][i] for j in range(col_count)] for i in range(n_rows)]


def _dedup_by_timestamp_policy(rows: List[List[Any]], header: List[str], policy: str) -> List[List[Any]]:
    if not rows or not header:
        return rows
    try:
        ts_idx = header.index('timestamp')
    except ValueError:
        return rows

    grouped: Dict[str, Tuple[List[Any], int]] = {}
    for i, r in enumerate(rows):
        ts_str = _parse_str(r[ts_idx]) or ''
        ts_obj = _parse_ts(ts_str)
        if ts_str not in grouped:
            grouped[ts_str] = (r, i)
            continue

        prev_row, prev_i = grouped[ts_str]
        prev_ts_obj = _parse_ts(_parse_str(prev_row[ts_idx]))
        if ts_obj is not None and prev_ts_obj is not None:
            if policy == 'keep_min_ts':
                if ts_obj < prev_ts_obj:
                    grouped[ts_str] = (r, i)
            else:
                if ts_obj > prev_ts_obj or ts_obj == prev_ts_obj:
                    grouped[ts_str] = (r, i)
        else:
            if policy == 'keep_min_ts':
                pass
            else:
                grouped[ts_str] = (r, i)

    def _sort_key(tup: Tuple[List[Any], int]):
        row, _ = tup
        ts_str = _parse_str(row[ts_idx]) or ''
        ts_obj = _parse_ts(ts_str)
        return ts_obj if ts_obj is not None else datetime.min

    kept = sorted(grouped.values(), key=_sort_key)
    return [row for (row, _) in kept]


def _compute_group_medians(rows: List[List[Any]], idx_metric: int, idx_group: int) -> Dict[str, float]:
    med: Dict[str, float] = {}
    buckets: Dict[str, List[float]] = {}
    for r in rows:
        g = _parse_str(r[idx_group]) or ''
        v = _parse_float(r[idx_metric])
        if v is not None:
            buckets.setdefault(g, []).append(v)
    for g, arr in buckets.items():
        m = _median(arr)
        if m is not None:
            med[g] = m
    return med


def _round_numeric_rows_inplace(rows: List[List[Any]], header: List[str], decimals: int = 2) -> None:
    numeric_exclude = {'timestamp', 'zone_id', 'weekday'}
    for j, name in enumerate(header):
        if name in numeric_exclude:
            continue
        for r in rows:
            v = _parse_float(r[j])
            if v is None:
                r[j] = None
            else:
                r[j] = _round_half_up_float(v, decimals)


def compute_variance_diff_cols_ext(
    header: List[str],
    columns: List[List[Any]],
    metric_x: str,
    metric_y: str,
    subset_template: str,
    allowed_zones: List[str],
    pump_threshold: float,
    fan_threshold: float,
    allowed_weekdays: List[str],
    dedup_policy: str,
    clipping_method: str,
    sigma_k: float,
    iqr_k: float,
    variance_mode: str,
    normalize_mode: str,
    gating_mode: str,
    rolling_median_w: int
) -> str:
    if not header or not columns or len(header) != len(columns):
        return "0.00"

    cleaned_cols = _clean_columns_by_defect_from_cols(columns)
    rows = _reconstruct_rows_from_cols(cleaned_cols)
    rows = _dedup_by_timestamp_policy(rows, header, dedup_policy)

    # Round all numeric cells to 2 decimals (as displayed) before any computation
    _round_numeric_rows_inplace(rows, header, decimals=2)

    try:
        idx_x = header.index(metric_x)
        idx_y = header.index(metric_y)
        idx_zone = header.index('zone_id')
        idx_pump = header.index('pump_minutes')
        idx_weekday = header.index('weekday')
        idx_fan = header.index('fan_speed_rpm')
    except ValueError:
        return "0.00"

    x_vals_raw = [_parse_float(r[idx_x]) for r in rows]
    y_vals_raw = [_parse_float(r[idx_y]) for r in rows]

    if normalize_mode == 'zone_center':
        zone_mx = _compute_group_medians(rows, idx_x, idx_zone)
        zone_my = _compute_group_medians(rows, idx_y, idx_zone)
        allowed_set = set(allowed_zones)
        x_vals_norm = []
        y_vals_norm = []
        for i, r in enumerate(rows):
            z = _parse_str(r[idx_zone]) or ''
            vx = x_vals_raw[i]
            vy = y_vals_raw[i]
            if z in allowed_set:
                mx = zone_mx.get(z, None)
                my = zone_my.get(z, None)
                x_vals_norm.append(None if (vx is None or mx is None) else vx - mx)
                y_vals_norm.append(None if (vy is None or my is None) else vy - my)
            else:
                x_vals_norm.append(vx)
                y_vals_norm.append(vy)
    elif normalize_mode == 'weekday_center':
        wd_mx = _compute_group_medians(rows, idx_x, idx_weekday)
        wd_my = _compute_group_medians(rows, idx_y, idx_weekday)
        x_vals_norm = []
        y_vals_norm = []
        for i, r in enumerate(rows):
            w = _parse_str(r[idx_weekday]) or ''
            vx = x_vals_raw[i]
            vy = y_vals_raw[i]
            mx = wd_mx.get(w, None)
            my = wd_my.get(w, None)
            x_vals_norm.append(None if (vx is None or mx is None) else vx - mx)
            y_vals_norm.append(None if (vy is None or my is None) else vy - my)
    else:
        x_vals_norm = x_vals_raw[:]
        y_vals_norm = y_vals_raw[:]

    x_vals_smooth = _rolling_median(x_vals_norm, rolling_median_w)
    y_vals_smooth = _rolling_median(y_vals_norm, rolling_median_w)

    def _clip_sigma(vals: List[Optional[float]], k: float) -> List[Optional[float]]:
        mean, std = _population_mean_std(vals)
        if mean is None or std is None:
            return [None for _ in vals]
        clipped = []
        for v in vals:
            if v is None:
                clipped.append(None)
            elif std == 0.0:
                clipped.append(v if abs(v - mean) <= 0.0 else None)
            else:
                clipped.append(v if abs(v - mean) <= float(k) * std else None)
        return clipped

    def _clip_iqr(vals: List[Optional[float]], k: float) -> List[Optional[float]]:
        bounds = _iqr_bounds(vals, k)
        if bounds is None:
            return [None for _ in vals]
        low, high = bounds
        clipped = []
        for v in vals:
            if v is None:
                clipped.append(None)
            else:
                clipped.append(v if (v >= low and v <= high) else None)
        return clipped

    if clipping_method == 'iqr':
        x_clipped = _clip_iqr(x_vals_smooth, iqr_k)
        y_clipped = _clip_iqr(y_vals_smooth, iqr_k)
    else:
        x_clipped = _clip_sigma(x_vals_smooth, sigma_k)
        y_clipped = _clip_sigma(y_vals_smooth, sigma_k)

    subset_indices: List[int] = []
    allowed_zone_set = set(allowed_zones)
    allowed_weekday_set = set(allowed_weekdays)

    for i, r in enumerate(rows):
        zone = _parse_str(r[idx_zone]) or ''
        pump = _parse_float(r[idx_pump])
        wd = _parse_str(r[idx_weekday]) or ''
        fan = _parse_float(r[idx_fan])

        if subset_template == 'zone_and_pump':
            cond = (zone in allowed_zone_set) and (pump is not None and pump > float(pump_threshold))
        elif subset_template == 'zone_and_weekday':
            cond = (zone in allowed_zone_set) and (wd in allowed_weekday_set)
        elif subset_template == 'pump_and_fan':
            cond = (pump is not None and pump > float(pump_threshold)) and (fan is not None and fan > float(fan_threshold))
        elif subset_template == 'weekday_only':
            cond = (wd in allowed_weekday_set)
        else:
            cond = (zone in allowed_zone_set)

        if cond:
            subset_indices.append(i)

    if not subset_indices:
        return "0.00"

    if gating_mode == 'both':
        filt_idx = [i for i in subset_indices if (x_clipped[i] is not None and y_clipped[i] is not None)]
        if len(filt_idx) < 2:
            return "0.00"
        x_subset = [x_clipped[i] for i in filt_idx]
        y_subset = [y_clipped[i] for i in filt_idx]
    else:
        x_subset = [x_clipped[i] for i in subset_indices]
        y_subset = [y_clipped[i] for i in subset_indices]

    var_x = _variance(x_subset, variance_mode)
    var_y = _variance(y_subset, variance_mode)

    if var_x is None or var_y is None:
        return "0.00"

    diff = abs(var_x - var_y)
    return _round_two_str(diff)


def _has_timestamp_duplicates(columns: List[List[Any]], header: List[str]) -> bool:
    try:
        ts_idx = header.index('timestamp')
    except ValueError:
        return False
    seen: Dict[str, int] = {}
    for v in columns[ts_idx]:
        s = _parse_str(v) or ''
        seen[s] = seen.get(s, 0) + 1
        if seen[s] >= 2 and s != '':
            return True
    return False


def validate_uniqueness_ext(
    header: List[str],
    columns: List[List[Any]],
    metric_x: str,
    metric_y: str,
    subset_template: str,
    allowed_zones: List[str],
    pump_threshold: float,
    fan_threshold: float,
    allowed_weekdays: List[str],
    dedup_policy: str,
    clipping_method: str,
    sigma_k: float,
    iqr_k: float,
    variance_mode: str,
    normalize_mode: str,
    gating_mode: str,
    rolling_median_w: int
) -> bool:
    if not header or not columns:
        return False

    if not _has_timestamp_duplicates(columns, header):
        return False

    ans = compute_variance_diff_cols_ext(
        header, columns, metric_x, metric_y, subset_template, allowed_zones, pump_threshold,
        fan_threshold, allowed_weekdays, dedup_policy, clipping_method, sigma_k, iqr_k,
        variance_mode, normalize_mode, gating_mode, rolling_median_w
    )
    try:
        val = float(ans)
    except Exception:
        return False

    if val < 0.01:
        return False

    cleaned_cols = _clean_columns_by_defect_from_cols(columns)
    rows = _reconstruct_rows_from_cols(cleaned_cols)
    rows = _dedup_by_timestamp_policy(rows, header, dedup_policy)

    # Ensure the same rounding principle as in compute
    _round_numeric_rows_inplace(rows, header, decimals=2)

    try:
        idx_x = header.index(metric_x)
        idx_y = header.index(metric_y)
        idx_zone = header.index('zone_id')
        idx_pump = header.index('pump_minutes')
        idx_weekday = header.index('weekday')
        idx_fan = header.index('fan_speed_rpm')
    except ValueError:
        return False

    x_vals_raw = [_parse_float(r[idx_x]) for r in rows]
    y_vals_raw = [_parse_float(r[idx_y]) for r in rows]

    if normalize_mode == 'zone_center':
        zone_mx = _compute_group_medians(rows, idx_x, idx_zone)
        zone_my = _compute_group_medians(rows, idx_y, idx_zone)
        allowed_set = set(allowed_zones)
        x_vals_norm = []
        y_vals_norm = []
        for i, r in enumerate(rows):
            z = _parse_str(r[idx_zone]) or ''
            vx = x_vals_raw[i]
            vy = y_vals_raw[i]
            if z in allowed_set:
                mx = zone_mx.get(z, None)
                my = zone_my.get(z, None)
                x_vals_norm.append(None if (vx is None or mx is None) else vx - mx)
                y_vals_norm.append(None if (vy is None or my is None) else vy - my)
            else:
                x_vals_norm.append(vx)
                y_vals_norm.append(vy)
    elif normalize_mode == 'weekday_center':
        wd_mx = _compute_group_medians(rows, idx_x, idx_weekday)
        wd_my = _compute_group_medians(rows, idx_y, idx_weekday)
        x_vals_norm = []
        y_vals_norm = []
        for i, r in enumerate(rows):
            w = _parse_str(r[idx_weekday]) or ''
            vx = x_vals_raw[i]
            vy = y_vals_raw[i]
            mx = wd_mx.get(w, None)
            my = wd_my.get(w, None)
            x_vals_norm.append(None if (vx is None or mx is None) else vx - mx)
            y_vals_norm.append(None if (vy is None or my is None) else vy - my)
    else:
        x_vals_norm = x_vals_raw[:]
        y_vals_norm = y_vals_raw[:]

    x_vals_smooth = _rolling_median(x_vals_norm, rolling_median_w)
    y_vals_smooth = _rolling_median(y_vals_norm, rolling_median_w)

    if clipping_method == 'iqr':
        x_clipped = _clip_iqr_for_validate(x_vals_smooth, iqr_k)
        y_clipped = _clip_iqr_for_validate(y_vals_smooth, iqr_k)
    else:
        x_clipped = _clip_sigma_for_validate(x_vals_smooth, sigma_k)
        y_clipped = _clip_sigma_for_validate(y_vals_smooth, sigma_k)

    subset_indices: List[int] = []
    allowed_zone_set = set(allowed_zones)
    allowed_weekday_set = set(allowed_weekdays)
    for i, r in enumerate(rows):
        zone = _parse_str(r[idx_zone]) or ''
        pump = _parse_float(r[idx_pump])
        wd = _parse_str(r[idx_weekday]) or ''
        fan = _parse_float(r[idx_fan])
        if subset_template == 'zone_and_pump':
            cond = (zone in allowed_zone_set) and (pump is not None and pump > float(pump_threshold))
        elif subset_template == 'zone_and_weekday':
            cond = (zone in allowed_zone_set) and (wd in allowed_weekday_set)
        elif subset_template == 'pump_and_fan':
            cond = (pump is not None and pump > float(pump_threshold)) and (fan is not None and fan > float(fan_threshold))
        elif subset_template == 'weekday_only':
            cond = (wd in allowed_weekday_set)
        else:
            cond = (zone in allowed_zone_set)
        if cond:
            subset_indices.append(i)
    if not subset_indices:
        return False

    if gating_mode == 'both':
        filt_idx = [i for i in subset_indices if (x_clipped[i] is not None and y_clipped[i] is not None)]
        return len(filt_idx) >= 2
    else:
        return (sum(1 for i in subset_indices if x_clipped[i] is not None) >= 2 and
                sum(1 for i in subset_indices if y_clipped[i] is not None) >= 2)


def _clip_sigma_for_validate(vals: List[Optional[float]], k: float) -> List[Optional[float]]:
    mean, std = _population_mean_std(vals)
    if mean is None or std is None:
        return [None for _ in vals]
    clipped = []
    for v in vals:
        if v is None:
            clipped.append(None)
        elif std == 0.0:
            clipped.append(v if abs(v - mean) <= 0.0 else None)
        else:
            clipped.append(v if abs(v - mean) <= float(k) * std else None)
    return clipped


def _clip_iqr_for_validate(vals: List[Optional[float]], k: float) -> List[Optional[float]]:
    bounds = _iqr_bounds(vals, k)
    if bounds is None:
        return [None for _ in vals]
    low, high = bounds
    clipped = []
    for v in vals:
        if v is None:
            clipped.append(None)
        else:
            clipped.append(v if (v >= low and v <= high) else None)
    return clipped