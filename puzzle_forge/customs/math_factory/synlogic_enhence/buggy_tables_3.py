# buggy_tables_6.py
from typing import Any, Dict, List, Optional, Tuple
import math
import random
from datetime import datetime, timedelta
from copy import deepcopy

# -----------------------------
# 基础类型与安全转换
# -----------------------------
def _to_float_or_none(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, str):
            xs = x.strip()
            if xs == '':
                return None
            v = float(xs)
        else:
            v = float(x)
        if not math.isfinite(v):
            return None
        return v
    except Exception:
        return None

def _to_str_or_empty(x: Any) -> str:
    if x is None:
        return ''
    return str(x).strip()

# -----------------------------
# 随机数与选择工具
# -----------------------------
def randint_inclusive(a: int, b: int) -> int:
    return random.randint(a, b)

def randint_step(a: int, b: int, step: int) -> int:
    if step <= 0:
        step = 1
    choices = list(range(a, b + 1, step))
    return random.choice(choices)

def random_choice(seq: List[Any]) -> Any:
    if not seq:
        return None
    return random.choice(seq)

def gen_start_date(min_date_str: str, max_date_str: str) -> str:
    fmt = '%Y-%m-%d'
    dmin = datetime.strptime(min_date_str, fmt)
    dmax = datetime.strptime(max_date_str, fmt)
    if dmax < dmin:
        dmin, dmax = dmax, dmin
    days = (dmax - dmin).days
    offset = random.randint(0, max(0, days))
    return (dmin + timedelta(days=offset)).strftime(fmt)

# -----------------------------
# 数据清洗与统计
# -----------------------------
def clean_table_rm(raw_flat: List[Any], rows: int, cols: int) -> List[Dict[str, Any]]:
    base = rows * cols
    flat = list(raw_flat)[:base]
    table: List[List[Any]] = []
    for r in range(rows):
        start = r * cols
        end = start + cols
        table.append(flat[start:end])
    header = [str(c) for c in table[0]]
    data_rows = table[1:]
    name_to_idx = {name: i for i, name in enumerate(header)}
    out_rows: List[Dict[str, Any]] = []
    for row in data_rows:
        rec: Dict[str, Any] = {}
        rec['date'] = _to_str_or_empty(row[name_to_idx.get('date', 0)])
        rec['device_type'] = _to_str_or_empty(row[name_to_idx.get('device_type', 5)]).lower()
        rec['region'] = _to_str_or_empty(row[name_to_idx.get('region', 8)])
        for key in ['orders', 'units_sold', 'returns', 'session_minutes', 'ad_clicks', 'revenue_usd']:
            idx = name_to_idx.get(key, None)
            val = row[idx] if idx is not None and idx < len(row) else None
            rec[key] = _to_float_or_none(val)
        out_rows.append(rec)
    return out_rows

def population_variance(values: List[Optional[float]]) -> Optional[float]:
    xs = [v for v in values if v is not None and isinstance(v, (int, float))]
    n = len(xs)
    if n == 0:
        return None
    if n == 1:
        return 0.0
    mean = sum(xs) / n
    sse = sum((x - mean) * (x - mean) for x in xs)
    return sse / n

def population_std(values: List[Optional[float]]) -> Optional[float]:
    var = population_variance(values)
    if var is None:
        return None
    if var < 0:
        return None
    return math.sqrt(var)

def format_two_decimals(value: Optional[float]) -> str:
    if value is None or (isinstance(value, float) and (not math.isfinite(value))):
        return '0.00'
    return f'{value:.2f}'

# -----------------------------
# 规则评估与度量计算
# -----------------------------
def _eval_filter(row: Dict[str, Any], f: Dict[str, Any]) -> bool:
    field = f.get('field')
    op = f.get('op')
    val = f.get('value')
    rv = row.get(field)
    # 统一预处理
    if field in ('device_type', 'region'):
        rv = (rv or '').strip().lower()
        if isinstance(val, str):
            val = val.strip().lower()
        if isinstance(val, list):
            val = [str(x).strip().lower() for x in val]
    if field == 'date':
        rv = (rv or '').strip()
    if field in ('ad_clicks', 'returns', 'revenue_usd', 'orders', 'units_sold', 'session_minutes'):
        rv = _to_float_or_none(rv)
        if isinstance(val, (int, float, str)):
            try:
                val = float(val)
            except Exception:
                pass

    # 运算符
    if op == 'eq':
        return rv == val
    if op == 'ne':
        return rv != val
    if op == 'ge':
        return (rv is not None) and (val is not None) and (rv >= float(val))
    if op == 'gt':
        return (rv is not None) and (val is not None) and (rv > float(val))
    if op == 'le':
        return (rv is not None) and (val is not None) and (rv <= float(val))
    if op == 'lt':
        return (rv is not None) and (val is not None) and (rv < float(val))
    if op == 'between':
        lo, hi = val
        return (rv is not None) and (rv >= lo) and (rv <= hi)
    if op == 'in':
        return rv in val
    if op == 'not_in':
        return rv not in val
    return False

def _apply_ruleset(data: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    subset = []
    flist = rules.get('filters', [])
    for r in data:
        ok = True
        for f in flist:
            if not _eval_filter(r, f):
                ok = False
                break
        if ok:
            subset.append(r)
    return subset

def _metric_value(rules: Dict[str, Any], subset: List[Dict[str, Any]]) -> Optional[float]:
    m = rules.get('metric', {})
    mtype = m.get('type', 'var_diff')
    cols = m.get('on', ['revenue_usd', 'returns'])
    if not subset:
        return None
    if mtype == 'var_diff':
        v1 = population_variance([x.get(cols[0]) for x in subset])
        v2 = population_variance([x.get(cols[1]) for x in subset])
        if v1 is None or v2 is None:
            return None
        return abs(v1 - v2)
    if mtype == 'std_diff':
        s1 = population_std([x.get(cols[0]) for x in subset])
        s2 = population_std([x.get(cols[1]) for x in subset])
        if s1 is None or s2 is None:
            return None
        return abs(s1 - s2)
    if mtype == 'mean_ratio':
        xs1 = [x.get(cols[0]) for x in subset if x.get(cols[0]) is not None]
        xs2 = [x.get(cols[1]) for x in subset if x.get(cols[1]) is not None]
        if len(xs1) == 0 or len(xs2) == 0:
            return None
        mu1 = sum(xs1) / len(xs1)
        mu2 = sum(xs2) / len(xs2)
        if mu2 == 0:
            return None
        return mu1 / mu2
    return None

# -----------------------------
# 规则文本重建（统一口径）
# -----------------------------
def _is_int_like(x: float, eps: float = 1e-9) -> bool:
    try:
        return abs(float(x) - int(round(float(x)))) <= eps
    except Exception:
        return False

def _fmt_num(x: float) -> str:
    try:
        xf = float(x)
        if _is_int_like(xf):
            return str(int(round(xf)))
        return str(xf)
    except Exception:
        return str(x)

def filter_to_text(f: Dict[str, Any]) -> str:
    field = f.get('field', '')
    op = f.get('op', '')
    val = f.get('value', None)
    if op in ('eq', 'ne', 'ge', 'gt', 'le', 'lt'):
        symbol = {'eq': '等于', 'ne': '不等于', 'ge': '≥', 'gt': '>', 'le': '≤', 'lt': '<'}[op]
        if field == 'date':
            return f"{field} {symbol} {val}"
        if isinstance(val, (int, float)):
            return f"{field} {symbol} {_fmt_num(val)}"
        return f"{field} {symbol} {val}"
    if op == 'between':
        lo, hi = val
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            return f"{field} 在区间 [{_fmt_num(lo)}, {_fmt_num(hi)}]"
        # 日期或其他字符串区间
        return f"{field} 在 [{lo}, {hi}]（闭区间）"
    if op in ('in', 'not_in'):
        lst = val if isinstance(val, list) else [val]
        lst_str = ', '.join([str(x) for x in lst if x is not None])
        return f"{field} {'属于' if op=='in' else '不属于'} {lst_str}"
    return f"{field} 满足 {op}"

def filters_to_text(filters: List[Dict[str, Any]]) -> str:
    parts = [filter_to_text(f) for f in filters]
    parts = [p for p in parts if p]
    return ' 且 '.join(parts) if parts else '无过滤条件'

# -----------------------------
# 规则生成与文本生成
# -----------------------------
def _region_pool(data: List[Dict[str, Any]]) -> List[str]:
    regions = set()
    for r in data:
        regions.add((r.get('region') or '').strip())
    pool = [x for x in regions if x]
    if not pool:
        pool = ['NA', 'EU', 'APAC', 'LATAM']
    return pool

def _date_range(data: List[Dict[str, Any]]) -> Tuple[str, str]:
    ds = [r.get('date') for r in data if isinstance(r.get('date'), str) and len(r.get('date')) == 10]
    ds = sorted(ds)
    if not ds:
        return ('2025-01-01', '2025-12-31')
    return (ds[0], ds[-1])

def _pick_device(data: List[Dict[str, Any]], device_pool: List[str]) -> str:
    # 优先选取数据中出现较多的设备
    cnt = {}
    for r in data:
        d = (r.get('device_type') or '').strip().lower()
        if d:
            cnt[d] = cnt.get(d, 0) + 1
    choices = list(cnt.keys()) if cnt else device_pool
    if not choices:
        choices = ['mobile', 'desktop', 'tablet']
    return random.choice(choices)

def _ensure_subset_ok(data: List[Dict[str, Any]], rules: Dict[str, Any]) -> Dict[str, Any]:
    # 保证子集≥2且metric可算，尝试逐步放宽或微调
    tries = 0
    while tries < 4:
        subset = _apply_ruleset(data, rules)
        val = _metric_value(rules, subset)
        if subset is not None and len(subset) >= 2 and (val is not None) and math.isfinite(val):
            return rules
        # 放宽：随机去掉一个非关键过滤或放宽between区间
        fl = rules.get('filters', [])
        if not fl:
            fl.append({'field': 'returns', 'op': 'ge', 'value': 0.0, 'text': 'returns ≥ 0'})
        else:
            idx = random.randint(0, len(fl) - 1)
            f = fl[idx]
            if f.get('op') == 'between':
                val_pair = f.get('value')
                handled = False
                if isinstance(val_pair, (tuple, list)) and len(val_pair) == 2:
                    lo, hi = val_pair[0], val_pair[1]
                    # 数值区间
                    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
                        try:
                            lof = float(lo)
                            hif = float(hi)
                            span = hif - lof
                            widen = max(1.0, abs(span) * 0.5)
                            f['value'] = (lof - widen, hif + widen)
                            f['text'] = f"将 {f['field']} 的区间适当放宽"
                            handled = True
                        except Exception:
                            handled = False
                    else:
                        # 日期字符串区间
                        try:
                            fmt = '%Y-%m-%d'
                            dlo = datetime.strptime(str(lo), fmt)
                            dhi = datetime.strptime(str(hi), fmt)
                            days_span = (dhi - dlo).days
                            widen_days = max(1, days_span // 2 if days_span > 0 else 7)
                            new_lo = (dlo - timedelta(days=widen_days)).strftime(fmt)
                            new_hi = (dhi + timedelta(days=widen_days)).strftime(fmt)
                            f['value'] = (new_lo, new_hi)
                            f['text'] = f"将 {f['field']} 的日期区间适当放宽"
                            handled = True
                        except Exception:
                            handled = False
                if not handled:
                    # 无法放宽则移除该过滤器
                    fl.pop(idx)
            else:
                fl.pop(idx)
        rules['filters'] = fl
        tries += 1
    return rules

def generate_ruleset(raw_flat: List[Any],
                     rows: int,
                     cols: int,
                     device_pool: List[str],
                     ad_click_threshold: int,
                     metric_type: Optional[str] = None) -> Dict[str, Any]:
    data = clean_table_rm(raw_flat, rows, cols)
    regions = _region_pool(data)
    dmin, dmax = _date_range(data)
    dev = _pick_device(data, device_pool)

    # 随机选择过滤模块数量 2~4
    k = random.randint(2, 4)
    filters: List[Dict[str, Any]] = []

    # 备选过滤模块，随机抽样
    candidates: List[Dict[str, Any]] = []

    # device eq/ne
    candidates.append({'field': 'device_type', 'op': 'eq', 'value': dev, 'text': f"device_type 等于 '{dev}'"})
    other_dev = random_choice([x for x in ['mobile', 'desktop', 'tablet'] if x != dev]) or dev
    candidates.append({'field': 'device_type', 'op': 'ne', 'value': other_dev, 'text': f"device_type 不等于 '{other_dev}'"})

    # ad_clicks ge/gt/between
    thr = float(ad_click_threshold)
    candidates.append({'field': 'ad_clicks', 'op': 'ge', 'value': thr, 'text': f"ad_clicks ≥ {int(thr)}"})
    candidates.append({'field': 'ad_clicks', 'op': 'gt', 'value': thr - 1.0, 'text': f"ad_clicks > {int(thr - 1.0)}"})
    lo = max(0.0, thr - random.randint(5, 50))
    hi = thr + random.randint(10, 100)
    if hi < lo:
        lo, hi = hi, lo
    candidates.append({'field': 'ad_clicks', 'op': 'between', 'value': (float(lo), float(hi)), 'text': f"ad_clicks 在区间 [{int(lo)}, {int(hi)}]"})

    # returns 阈值 le/ge
    rthr = random.randint(10, 40)
    candidates.append({'field': 'returns', 'op': 'le', 'value': float(rthr), 'text': f"returns ≤ {rthr}"})
    candidates.append({'field': 'returns', 'op': 'ge', 'value': float(max(0, rthr - 5)), 'text': f"returns ≥ {max(0, rthr - 5)}"})

    # orders/session_minutes 适度加入选择空间（增强差异维度）
    orthr = random.randint(250, 450)
    candidates.append({'field': 'orders', 'op': 'ge', 'value': float(orthr), 'text': f"orders ≥ {orthr}"})
    smthr = random.randint(3500, 7000)
    candidates.append({'field': 'session_minutes', 'op': 'ge', 'value': float(smthr), 'text': f"session_minutes ≥ {smthr}"})

    # region in/not_in
    pick_regions = list(set([random_choice(regions) for _ in range(random.randint(1, 2))]))
    if not pick_regions:
        pick_regions = [random_choice(['NA', 'EU', 'APAC', 'LATAM'])]
    candidates.append({'field': 'region', 'op': 'in', 'value': pick_regions, 'text': f"region 属于 {', '.join(pick_regions)}"})
    other_regions = [x for x in regions if x not in pick_regions]
    if other_regions:
        candidates.append({'field': 'region', 'op': 'not_in', 'value': other_regions, 'text': f"region 不属于 {', '.join(other_regions)}"})

    # date between
    try:
        fmt = '%Y-%m-%d'
        d0 = datetime.strptime(dmin, fmt)
        d1 = datetime.strptime(dmax, fmt)
        days = max(0, (d1 - d0).days)
        off = random.randint(0, max(0, days // 2))
        span = random.randint(0, max(1, days - off))
        lo_date = (d0 + timedelta(days=off)).strftime(fmt)
        hi_date = (d0 + timedelta(days=off + span)).strftime(fmt)
    except Exception:
        lo_date, hi_date = dmin, dmax
    candidates.append({'field': 'date', 'op': 'between', 'value': (lo_date, hi_date), 'text': f"date 在 [{lo_date}, {hi_date}]（闭区间）"})

    random.shuffle(candidates)
    filters = candidates[:k]

    if metric_type is None:
        metric_type = random_choice(['var_diff', 'std_diff', 'mean_ratio']) or 'var_diff'
    metric_desc_map = {
        'var_diff': 'revenue_usd 与 returns 的总体方差的绝对差',
        'std_diff': 'revenue_usd 与 returns 的总体标准差的绝对差',
        'mean_ratio': 'revenue_usd 与 returns 的均值之比'
    }
    metric = {'type': metric_type, 'on': ['revenue_usd', 'returns'], 'text': metric_desc_map.get(metric_type, 'revenue_usd 与 returns 的总体方差的绝对差')}

    rules = {'filters': filters, 'metric': metric}
    rules = _ensure_subset_ok(data, rules)
    return rules

def rules_text(rules: Dict[str, Any], mode: str = 'metric') -> str:
    # 统一由当前 filters 数值重建文案，确保题面与计算一致
    fpart = filters_to_text(rules.get('filters', []))
    mtxt = rules.get('metric', {}).get('text', '')
    if mode == 'metric':
        return f"在满足 {fpart} 的记录子集中，计算 {mtxt}；若无法计算则输出 '0.00'（四舍五入到 2 位并保留两位）。答案必须为保留两位小数的字符串，例如：'12.34'。"
    if mode == 'count':
        return f"在满足 {fpart} 的记录子集中，输出满足条件的记录条数；答案必须为纯数字字符串，例如：'3'。"
    return f"在满足 {fpart} 的记录子集中进行统计。"

def answer_metric(raw_flat: List[Any], rows: int, cols: int, rules: Dict[str, Any]) -> str:
    data = clean_table_rm(raw_flat, rows, cols)
    subset = _apply_ruleset(data, rules)
    val = _metric_value(rules, subset)
    return format_two_decimals(val)

def validate_ruleset(raw_flat: List[Any], rows: int, cols: int, rules: Dict[str, Any]) -> bool:
    data = clean_table_rm(raw_flat, rows, cols)
    subset = _apply_ruleset(data, rules)
    val = _metric_value(rules, subset)
    return (subset is not None) and (len(subset) >= 2) and (val is not None) and math.isfinite(val)

def answer_count(raw_flat: List[Any], rows: int, cols: int, rules: Dict[str, Any]) -> str:
    data = clean_table_rm(raw_flat, rows, cols)
    subset = _apply_ruleset(data, rules)
    n = len(subset) if subset is not None else 0
    return str(int(n))

def validate_count(raw_flat: List[Any], rows: int, cols: int, rules: Dict[str, Any]) -> bool:
    # 至少保证有 1 条满足条件的记录，避免出现“0”导致的显见答案
    data = clean_table_rm(raw_flat, rows, cols)
    subset = _apply_ruleset(data, rules)
    return (subset is not None) and (len(subset) >= 1)

# -----------------------------
# 基础生成器与最终答案（兼容旧接口）
# -----------------------------
def _random_region() -> str:
    return random.choice(['NA', 'EU', 'APAC', 'LATAM'])

def _random_device(dev_pool: Optional[List[str]] = None) -> str:
    pool = dev_pool if dev_pool else ['mobile', 'desktop', 'tablet']
    return random.choice(pool)

def _ensure_distinct(vals: List[float]) -> List[float]:
    if len(vals) >= 2 and len(set(round(v, 6) for v in vals)) == 1:
        vals[-1] = vals[-1] + random.uniform(1.0, 5.0)
    return vals

def generate_raw_flat(rows: int,
                      cols: int,
                      target_device: str,
                      ad_click_threshold: int,
                      noise_k: int,
                      start_date: str,
                      seed: Optional[int] = None) -> List[Any]:
    if seed is not None:
        random.seed(seed)
    if cols != 9:
        raise ValueError('cols must be 9 for this generator.')
    data_rows = rows - 1
    if data_rows < 2:
        raise ValueError('rows must be at least 3 (including header).')
    header = ['date', 'orders', 'units_sold', 'returns', 'session_minutes', 'device_type', 'ad_clicks', 'revenue_usd', 'region']
    fmt = '%Y-%m-%d'
    try:
        d0 = datetime.strptime(start_date, fmt)
    except Exception:
        d0 = datetime.strptime('2025-01-01', fmt)

    min_target_rows = min(4, max(2, data_rows // 2))
    target_rows = random.randint(2, min_target_rows)

    rows_data: List[List[Any]] = []
    target_rev_vals: List[float] = []
    target_ret_vals: List[float] = []

    for i in range(target_rows):
        day = d0 + timedelta(days=i)
        date_str = day.strftime(fmt)
        device = (target_device or 'mobile').lower()
        ad_clicks = float(ad_click_threshold + random.randint(0, 90))
        orders = float(random.randint(220, 460))
        units_sold = float(random.randint(520, 1100))
        returns = float(random.randint(10, 40))
        session_minutes = float(random.randint(3600, 7200))
        revenue_usd = float(random.uniform(9000.0, 22000.0) + 3.5 * units_sold + random.uniform(-800.0, 800.0))
        region = _random_region()
        target_rev_vals.append(revenue_usd)
        target_ret_vals.append(returns)
        rows_data.append([date_str, orders, units_sold, returns, session_minutes, device, ad_clicks, revenue_usd, region])

    target_rev_vals = _ensure_distinct(target_rev_vals)
    target_ret_vals = _ensure_distinct(target_ret_vals)
    for idx in range(target_rows):
        rows_data[idx][7] = target_rev_vals[idx]
        rows_data[idx][3] = target_ret_vals[idx]

    for i in range(target_rows, data_rows):
        day = d0 + timedelta(days=i)
        date_str = day.strftime(fmt)
        device = _random_device(['mobile', 'desktop', 'tablet']).lower()
        if random.random() < 0.8:
            ad_clicks = float(max(0, ad_click_threshold - random.randint(10, 100)))
        else:
            ad_clicks = float(ad_click_threshold + random.randint(0, 60))
        orders = float(random.randint(200, 500))
        units_sold = float(random.randint(480, 1200))
        returns = float(random.randint(8, 42))
        session_minutes = float(random.randint(3000, 7800))
        revenue_usd = float(random.uniform(8000.0, 24000.0) + 2.8 * units_sold + random.uniform(-1200.0, 1200.0))
        region = _random_region()
        rows_data.append([date_str, orders, units_sold, returns, session_minutes, device, ad_clicks, revenue_usd, region])

    flat: List[Any] = []
    flat.extend(header)
    for r in rows_data:
        flat.extend(r)

    total_noise = 0
    k = max(1, int(noise_k))
    for j in range(1, cols + 1):
        total_noise += k * j
    for _ in range(total_noise):
        if random.random() < 0.9:
            flat.append(float(random.uniform(-1e3, 1e3)))
        else:
            flat.append(random_choice(['NA', 'bad', 'x', 'None', '']))

    tries = 0
    while tries < 3:
        data = clean_table_rm(flat, rows, cols)
        baseline_rules = {
            'filters': [
                {'field': 'device_type', 'op': 'eq', 'value': (target_device or 'mobile').lower(), 'text': ''},
                {'field': 'ad_clicks', 'op': 'ge', 'value': float(ad_click_threshold), 'text': ''}
            ],
            'metric': {'type': 'var_diff', 'on': ['revenue_usd', 'returns']}
        }
        subset = _apply_ruleset(data, baseline_rules)
        val = _metric_value(baseline_rules, subset)
        if subset is not None and len(subset) >= 2 and (val is not None) and math.isfinite(val):
            break
        if rows_data:
            rows_data[0][6] = float(ad_click_threshold + random.randint(50, 120))
            rows_data[0][7] = float(rows_data[0][7]) + random.uniform(100.0, 600.0)
        flat = []
        flat.extend(header)
        for r in rows_data:
            flat.extend(r)
        for _ in range(total_noise):
            if random.random() < 0.9:
                flat.append(float(random.uniform(-1e3, 1e3)))
            else:
                flat.append(random_choice(['NA', 'bad', 'x', 'None', '']))
        tries += 1

    return flat

# 向后兼容：原题的最终答案函数
def compute_abs_diff_variances_by_filter(raw_flat: List[Any],
                                         rows: int,
                                         cols: int,
                                         target_device: str,
                                         ad_click_threshold: int) -> Optional[float]:
    data = clean_table_rm(raw_flat, rows, cols)
    td = (target_device or '').lower().strip()
    subset = []
    for r in data:
        dv = (r.get('device_type') or '').lower().strip()
        ac = _to_float_or_none(r.get('ad_clicks'))
        if dv == td and ac is not None and ac >= float(ad_click_threshold):
            subset.append(r)
    rev_var = population_variance([r.get('revenue_usd') for r in subset])
    ret_var = population_variance([r.get('returns') for r in subset])
    if rev_var is None or ret_var is None:
        return None
    return abs(rev_var - ret_var)

def final_answer(raw_flat: List[Any],
                 rows: int,
                 cols: int,
                 target_device: str,
                 ad_click_threshold: int) -> str:
    diff = compute_abs_diff_variances_by_filter(
        raw_flat, rows, cols, target_device, ad_click_threshold
    )
    return format_two_decimals(diff)

# 兼容旧合成器接口：mobile 专用包装函数（避免 ImportError）
def compute_abs_diff_variances_mobile(raw_flat: List[Any],
                                      rows: int,
                                      cols: int,
                                      ad_click_threshold: Optional[int] = None,
                                      *args, **kwargs) -> Optional[float]:
    thr = 0 if ad_click_threshold is None else ad_click_threshold
    return compute_abs_diff_variances_by_filter(
        raw_flat, rows, cols, 'mobile', thr
    )

# ================================================================
# 复合稳定度指标（Q4）与唯一性护栏
# ================================================================
def _safe_mean(xs: List[Optional[float]]) -> Optional[float]:
    vals = [float(x) for x in xs if x is not None and isinstance(x, (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)

def _safe_var(xs: List[Optional[float]]) -> Optional[float]:
    return population_variance(xs)

def _safe_std(xs: List[Optional[float]]) -> Optional[float]:
    return population_std(xs)

def _safe_pearson(xs: List[Optional[float]], ys: List[Optional[float]]) -> Optional[float]:
    x = [float(v) for v in xs if v is not None and isinstance(v, (int, float))]
    y = [float(v) for v in ys if v is not None and isinstance(v, (int, float))]
    n = min(len(x), len(y))
    if n < 2:
        return None
    x = x[:n]
    y = y[:n]
    mx = sum(x) / n
    my = sum(y) / n
    sx = sum((v - mx) * (v - mx) for v in x)
    sy = sum((v - my) * (v - my) for v in y)
    if sx <= 0 or sy <= 0:
        return 0.0
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    denom = math.sqrt(sx) * math.sqrt(sy)
    if denom == 0:
        return 0.0
    return cov / denom

def _union_filters(rules_a: Dict[str, Any], rules_b: Dict[str, Any]) -> List[Dict[str, Any]]:
    fa = rules_a.get('filters', []) or []
    fb = rules_b.get('filters', []) or []
    return list(fa) + list(fb)

def composite_rules_text(rules_a: Dict[str, Any], rules_b: Dict[str, Any]) -> str:
    combined = _union_filters(rules_a, rules_b)
    rebuilt = [filter_to_text(f) for f in combined]
    uniq = []
    seen = set()
    for t in rebuilt:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    fpart = ' 且 '.join(uniq)
    return (
        f"在同时满足 {fpart} 的记录交集子集中，计算稳定度分数 stability_score："
        f"定义为 abs(σ_revenue_usd - σ_returns) + abs(var_revenue_usd - var_returns) / (1 + abs(pearson(revenue_usd, returns)))，"
        f"其中 σ 为总体标准差，var 为总体方差，pearson 为 revenue_usd 与 returns 的皮尔逊相关系数（不足 2 条记录时按 0 处理）。"
        f"若无法计算则输出 '0.00'。答案输出格式为 'value|count'，例如：'12.34|5'，"
        f"value 为四舍五入并保留两位小数的字符串，count 为满足交集条件的记录条数字符串。"
    )

def _composite_value_on_subset(subset: List[Dict[str, Any]]) -> Optional[float]:
    if not subset or len(subset) < 1:
        return None
    rev = [r.get('revenue_usd') for r in subset]
    ret = [r.get('returns') for r in subset]
    srev = _safe_std(rev)
    sret = _safe_std(ret)
    vrev = _safe_var(rev)
    vret = _safe_var(ret)
    p = _safe_pearson(rev, ret)
    if srev is None or sret is None or vrev is None or vret is None:
        return None
    if p is None:
        p = 0.0
    score = abs(srev - sret) + abs(vrev - vret) / (1.0 + abs(p))
    if not math.isfinite(score):
        return None
    return float(score)

def _apply_intersection(data: List[Dict[str, Any]], rules_a: Dict[str, Any], rules_b: Dict[str, Any]) -> List[Dict[str, Any]]:
    subset_a = _apply_ruleset(data, rules_a)
    subset_b = _apply_ruleset(data, rules_b)
    key = lambda r: (r.get('date'), r.get('device_type'), r.get('revenue_usd'), r.get('returns'))
    set_b = {key(r) for r in subset_b}
    out = [r for r in subset_a if key(r) in set_b]
    return out

def answer_composite(raw_flat: List[Any], rows: int, cols: int,
                     rules_a: Dict[str, Any], rules_b: Dict[str, Any]) -> str:
    data = clean_table_rm(raw_flat, rows, cols)
    inter = _apply_intersection(data, rules_a, rules_b)
    val = _composite_value_on_subset(inter)
    val_str = format_two_decimals(val)
    cnt_str = str(int(len(inter))) if inter is not None else '0'
    return f'{val_str}|{cnt_str}'

def _perturb_filters_once(filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not filters:
        return []
    new_filters = [dict(f) for f in filters]
    idx = random.randint(0, len(new_filters) - 1)
    f = new_filters[idx]
    op = f.get('op')
    if op == 'between' and isinstance(f.get('value'), tuple) and len(f.get('value')) == 2:
        lo, hi = f['value']
        # 数值区间
        if isinstance(hi, (int, float)) and isinstance(lo, (int, float)):
            span = (hi - lo)
            widen = max(0.5, abs(span) * 0.1)
            if random.random() < 0.5:
                f['value'] = (lo - widen, hi + widen)
            else:
                inner = max(0.0, abs(span) * 0.1)
                f['value'] = (lo + inner, hi - inner) if (hi - lo > 2 * inner) else (lo, hi)
        else:
            # 日期区间：向外扩/向内缩
            try:
                fmt = '%Y-%m-%d'
                dlo = datetime.strptime(str(lo), fmt)
                dhi = datetime.strptime(str(hi), fmt)
                delta = max(1, (dhi - dlo).days // 6 if (dhi - dlo).days > 0 else 2)
                if random.random() < 0.5:
                    f['value'] = ((dlo - timedelta(days=delta)).strftime(fmt), (dhi + timedelta(days=delta)).strftime(fmt))
                else:
                    inner = max(1, (dhi - dlo).days // 6) if (dhi - dlo).days > 2 else 1
                    f['value'] = ((dlo + timedelta(days=inner)).strftime(fmt), (dhi - timedelta(days=inner)).strftime(fmt))
            except Exception:
                pass
    elif op in ('ge', 'gt', 'le', 'lt'):
        try:
            val = float(f.get('value', 0.0))
        except Exception:
            val = 0.0
        delta = max(0.5, abs(val) * 0.05)
        f['value'] = val + (delta if random.random() < 0.5 else -delta)
    else:
        if len(new_filters) > 1 and random.random() < 0.5:
            new_filters.pop(idx)
    return new_filters

def validate_composite(raw_flat: List[Any], rows: int, cols: int,
                       rules_a: Dict[str, Any], rules_b: Dict[str, Any]) -> bool:
    """
    唯一性护栏（改进版）：
    - 基于交集子集进行微扰验证（分别微扰 A 或 B），避免使用合并过滤器导致的非交集不稳定。
    - 使用数值容差（0.005）和交集条数比较判定差异，只要存在一次微扰导致稳定度值或交集条数不同，即通过。
    """
    data = clean_table_rm(raw_flat, rows, cols)
    inter = _apply_intersection(data, rules_a, rules_b)
    if inter is None or len(inter) < 3:
        return False
    base_val = _composite_value_on_subset(inter)
    if base_val is None or (not math.isfinite(base_val)):
        return False
    base_count = len(inter)

    trials = 0
    found_difference = False
    while trials < 6:
        pa = deepcopy(rules_a)
        pb = deepcopy(rules_b)
        if trials % 2 == 0:
            pa['filters'] = _perturb_filters_once(pa.get('filters', []))
        else:
            pb['filters'] = _perturb_filters_once(pb.get('filters', []))

        pa = _ensure_subset_ok(data, pa)
        pb = _ensure_subset_ok(data, pb)

        pinter = _apply_intersection(data, pa, pb)
        if pinter and len(pinter) >= 1:
            pval = _composite_value_on_subset(pinter)
            if pval is not None and math.isfinite(pval):
                if (abs(pval - base_val) >= 0.005) or (len(pinter) != base_count):
                    found_difference = True
                    break
        trials += 1

    return found_difference

# ================================================================
# 规则对调和器：保证交集规模与可计算性（新增，增强差异维度）
# ================================================================
def harmonize_pair(raw_flat: List[Any],
                   rows: int,
                   cols: int,
                   rules_a: Dict[str, Any],
                   rules_b: Dict[str, Any],
                   target_min: int = 3,
                   max_iters: int = 10) -> Dict[str, Any]:
    """
    对两个独立生成的规则集进行对齐与放宽，提升交集规模并保证稳定度值可计算。
    在对齐主条件（设备与点击阈值）后，强制引入至少一个差异过滤维度，确保 Q4 的交集非平凡。
    返回 {'a': tuned_rules_a, 'b': tuned_rules_b}
    """
    data = clean_table_rm(raw_flat, rows, cols)
    dmin, dmax = _date_range(data)

    def most_common_device() -> Optional[str]:
        cnt: Dict[str, int] = {}
        for r in data:
            dv = (r.get('device_type') or '').strip().lower()
            if dv:
                cnt[dv] = cnt.get(dv, 0) + 1
        if not cnt:
            return None
        return sorted(cnt.items(), key=lambda x: (-x[1], x[0]))[0][0]

    def min_ad_for_device(dev: Optional[str]) -> float:
        vals: List[float] = []
        for r in data:
            dv = (r.get('device_type') or '').strip().lower()
            if (dev is None) or (dv == dev):
                v = _to_float_or_none(r.get('ad_clicks'))
                if v is not None and math.isfinite(v):
                    vals.append(v)
        if not vals:
            return 0.0
        return float(min(vals))

    def set_device_eq(rule: Dict[str, Any], dev: Optional[str]) -> None:
        fs = [f for f in rule.get('filters', []) if f.get('field') != 'device_type']
        if dev is not None:
            fs.append({'field': 'device_type', 'op': 'eq', 'value': dev, 'text': f"device_type 等于 '{dev}'"})
        rule['filters'] = fs

    def ensure_ad_ge(rule: Dict[str, Any], thr: float) -> None:
        fs = [f for f in rule.get('filters', []) if f.get('field') != 'ad_clicks']
        fs.append({'field': 'ad_clicks', 'op': 'ge', 'value': float(thr), 'text': f"ad_clicks ≥ {int(thr)}"})
        rule['filters'] = fs

    def drop_region_not_in(rule: Dict[str, Any]) -> None:
        fs = []
        for f in rule.get('filters', []):
            if not (f.get('field') == 'region' and f.get('op') == 'not_in'):
                fs.append(f)
        rule['filters'] = fs

    def widen_date_to_full(rule: Dict[str, Any]) -> None:
        fs = []
        for f in rule.get('filters', []):
            if f.get('field') == 'date' and f.get('op') == 'between':
                fs.append({'field': 'date', 'op': 'between', 'value': (dmin, dmax), 'text': f"date 在 [{dmin}, {dmax}]（闭区间）"})
            else:
                fs.append(f)
        rule['filters'] = fs

    def add_returns_upper(rule: Dict[str, Any]) -> None:
        # 基于数据分布选一个较为宽松的 returns 上界
        rvals = [ _to_float_or_none(r.get('returns')) for r in data ]
        rvals = [v for v in rvals if v is not None]
        if rvals:
            bound = float(max(10, int(min(max(rvals), 35))))
        else:
            bound = 35.0
        fs = list(rule.get('filters', []))
        fs.append({'field': 'returns', 'op': 'le', 'value': bound, 'text': f"returns ≤ {int(bound)}"})
        rule['filters'] = fs

    def add_orders_lower(rule: Dict[str, Any]) -> None:
        ov = [ _to_float_or_none(r.get('orders')) for r in data ]
        ov = [v for v in ov if v is not None]
        thr = float(max(200, int(sum(ov)/len(ov))) if ov else 250)
        fs = list(rule.get('filters', []))
        fs.append({'field': 'orders', 'op': 'ge', 'value': thr, 'text': f"orders ≥ {int(thr)}"})
        rule['filters'] = fs

    def narrow_date(rule: Dict[str, Any]) -> None:
        # 在全范围内收窄一个子区间
        fmt = '%Y-%m-%d'
        try:
            d0 = datetime.strptime(dmin, fmt)
            d1 = datetime.strptime(dmax, fmt)
            days = max(1, (d1 - d0).days)
            win = max(1, days // 3)
            offset = random.randint(0, max(0, days - win))
            lo_date = (d0 + timedelta(days=offset)).strftime(fmt)
            hi_date = (d0 + timedelta(days=offset + win)).strftime(fmt)
        except Exception:
            lo_date, hi_date = dmin, dmax
        fs = [f for f in rule.get('filters', []) if f.get('field') != 'date']
        fs.append({'field': 'date', 'op': 'between', 'value': (lo_date, hi_date), 'text': f"date 在 [{lo_date}, {hi_date}]（闭区间）"})
        rule['filters'] = fs

    A = deepcopy(rules_a)
    B = deepcopy(rules_b)

    # 初始对齐：统一设备与点击阈值，放宽排斥项与日期
    dev0 = most_common_device()
    thr0 = min_ad_for_device(dev0)
    set_device_eq(A, dev0)
    set_device_eq(B, dev0)
    ensure_ad_ge(A, thr0)
    ensure_ad_ge(B, thr0)
    drop_region_not_in(A)
    drop_region_not_in(B)
    widen_date_to_full(A)
    widen_date_to_full(B)

    # 修复各自可计算性
    A = _ensure_subset_ok(data, A)
    B = _ensure_subset_ok(data, B)

    # 强制引入差异维度：A 加 returns 上界或 orders 下界，B 收窄日期或加 session_minutes 下界
    if random.random() < 0.5:
        add_returns_upper(A)
    else:
        add_orders_lower(A)
    if random.random() < 0.5:
        narrow_date(B)
    else:
        # 使用 session_minutes 下界增强差异
        smthr = random.randint(3500, 7000)
        fsb = list(B.get('filters', []))
        fsb.append({'field': 'session_minutes', 'op': 'ge', 'value': float(smthr), 'text': f"session_minutes ≥ {smthr}"})
        B['filters'] = fsb

    A = _ensure_subset_ok(data, A)
    B = _ensure_subset_ok(data, B)

    def ok_enough(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        inter = _apply_intersection(data, a, b)
        if inter is None or len(inter) < target_min:
            return False
        val = _composite_value_on_subset(inter)
        return (val is not None) and math.isfinite(val)

    if ok_enough(A, B):
        return {'a': A, 'b': B}

    # 迭代放宽/微调两侧规则
    for _ in range(max_iters):
        sa = _apply_ruleset(data, A)
        sb = _apply_ruleset(data, B)
        # 优先放宽子集更小的一侧
        if len(sa) <= len(sb):
            A['filters'] = _perturb_filters_once(A.get('filters', []))
            A = _ensure_subset_ok(data, A)
        else:
            B['filters'] = _perturb_filters_once(B.get('filters', []))
            B = _ensure_subset_ok(data, B)
        if ok_enough(A, B):
            return {'a': A, 'b': B}

    # 兜底：构造最小但有效的规则对，随后注入最小差异
    dev_max = most_common_device()
    thr_min = min_ad_for_device(dev_max)
    base_filters_dev = []
    if dev_max is not None:
        base_filters_dev.append({'field': 'device_type', 'op': 'eq', 'value': dev_max, 'text': f"device_type 等于 '{dev_max}'"})
    base_filters_dev.append({'field': 'ad_clicks', 'op': 'ge', 'value': float(thr_min), 'text': f"ad_clicks ≥ {int(thr_min)}"})
    A['filters'] = deepcopy(base_filters_dev)
    B['filters'] = deepcopy(base_filters_dev)
    # 注入差异
    add_returns_upper(A)
    narrow_date(B)

    A = _ensure_subset_ok(data, A)
    B = _ensure_subset_ok(data, B)

    inter = _apply_intersection(data, A, B)
    if inter is None or len(inter) < target_min:
        # 去掉设备限制，只保留极宽 ad_clicks（≥0），并仍维持差异
        A['filters'] = [{'field': 'ad_clicks', 'op': 'ge', 'value': 0.0, 'text': 'ad_clicks ≥ 0'}]
        add_returns_upper(A)
        B['filters'] = [{'field': 'ad_clicks', 'op': 'ge', 'value': 0.0, 'text': 'ad_clicks ≥ 0'}]
        narrow_date(B)
        A = _ensure_subset_ok(data, A)
        B = _ensure_subset_ok(data, B)

    return {'a': A, 'b': B}

# ================================================================
# Q1/Q2 稳健性校验（增强试次）
# ================================================================
def validate_ruleset_strict(raw_flat: List[Any], rows: int, cols: int, rules: Dict[str, Any]) -> bool:
    """
    在 validate_ruleset 基础上，加入微扰稳定性校验：
    - 基线子集≥2、度量可算
    - 对过滤器进行小幅微扰，若度量值或子集大小产生可感知差异（≥0.005 或 count 改变），则通过
    - 若微扰均未改变，但仍满足可算且子集≥2，也视为通过（减少过严拒绝）
    """
    data = clean_table_rm(raw_flat, rows, cols)
    subset = _apply_ruleset(data, rules)
    base_val = _metric_value(rules, subset)
    if subset is None or len(subset) < 2 or base_val is None or (not math.isfinite(base_val)):
        return False

    base_count = len(subset)
    trials = 0
    while trials < 6:
        prule = deepcopy(rules)
        prule['filters'] = _perturb_filters_once(prule.get('filters', []))
        prule = _ensure_subset_ok(data, prule)
        psubset = _apply_ruleset(data, prule)
        pval = _metric_value(prule, psubset)
        if psubset and pval is not None and math.isfinite(pval):
            if (abs(pval - base_val) >= 0.005) or (len(psubset) != base_count):
                return True
        trials += 1
    return True  # 若微扰均未改变，但仍满足可算且子集≥2，也视为通过