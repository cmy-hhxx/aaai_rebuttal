# buggy_tables_2.py
# 高阶泛化版：随机规则 + 规则校准 + 稳定性分数 + 加权/普通方差 + 唯一解验证
from typing import List, Dict, Any, Optional, Tuple
import random
import math
from datetime import date, timedelta

DEFAULT_COLUMNS = [
    'date','campaign_id','impressions','clicks','spend_usd','conversions',
    'avg_session_duration_sec','bounce_rate_pct','device_type','country',
    'page_load_ms','emails_sent','emails_opened','sms_sent','sms_responses',
    'ad_position','promo_code_used','inventory_level','competitor_price_usd',
    'cpc_usd','roas','return_visits','channel_group','season'
]

# ------------------ 安全工具 ------------------
def _safe_float(x) -> Optional[float]:
    try:
        if x is None or isinstance(x, bool):
            return None
        return float(x)
    except Exception:
        return None

def _safe_int(x) -> Optional[int]:
    try:
        if x is None or isinstance(x, bool):
            return None
        return int(float(x))
    except Exception:
        return None

def _percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    n = len(sorted_vals)
    if n == 0:
        return None
    if n == 1:
        return sorted_vals[0]
    pos = (n - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac

def _iqr_bounds(values: List[float], whisker: float = 1.5) -> Optional[Tuple[float, float]]:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if len(vals) == 0:
        return None
    vals.sort()
    q1 = _percentile(vals, 0.25)
    q3 = _percentile(vals, 0.75)
    if q1 is None or q3 is None:
        return None
    iqr = q3 - q1
    return (q1 - whisker * iqr, q3 + whisker * iqr)

def _sample_variance(nums: List[float]) -> Optional[float]:
    arr = [x for x in nums if x is not None and not math.isnan(x)]
    n = len(arr)
    if n < 2:
        return None
    mean = sum(arr) / n
    var = sum((x - mean) ** 2 for x in arr) / (n - 1)
    return var

def _weighted_sample_variance(values: List[float], weights: List[float]) -> Optional[float]:
    vw = [(v, w) for v, w in zip(values, weights) if v is not None and not math.isnan(v) and w is not None and not math.isnan(w)]
    if len(vw) < 2:
        return None
    vals = [v for v, _ in vw]
    wts = [max(0.0, float(w)) for _, w in vw]
    W = sum(wts)
    if W <= 0:
        return None
    wts = [w / W for w in wts]
    mu = sum(v * w for v, w in zip(vals, wts))
    num = sum(w * (v - mu) ** 2 for v, w in zip(vals, wts))
    denom = 1.0 - sum(w ** 2 for w in wts)
    if denom <= 0:
        return None
    return num / denom

def _zscore(values: List[Optional[float]]) -> List[Optional[float]]:
    xs = [v for v in values if v is not None and not math.isnan(v)]
    if len(xs) == 0:
        return [None] * len(values)
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / len(xs)
    sd = math.sqrt(var) if var > 0 else 0.0
    out = []
    for v in values:
        if v is None or sd == 0.0:
            out.append(None)
        else:
            out.append((v - mu) / sd)
    return out

def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0

# ------------------ 随机规则生成 ------------------
def function_make_rules(rng_seed: int, gen_params: Dict[str, Any]) -> Dict[str, Any]:
    rng = random.Random(rng_seed ^ 0xDEADBEEF)
    country_pool = ['US', 'GB', 'DE', 'IN', 'BR', 'CN', 'CA', 'AU', 'FR', 'JP']

    # 国家规则
    country_rule_type = rng.choices(['exclude_one', 'include_set', 'none'], weights=[0.5, 0.35, 0.15], k=1)[0]
    if country_rule_type == 'exclude_one':
        target = rng.choice(country_pool)
        country_rule = {'type': 'exclude_one', 'value': target}
        country_text = f'- 国家：排除 {target}'
    elif country_rule_type == 'include_set':
        k = rng.randint(2, 4)
        subset = rng.sample(country_pool, k)
        country_rule = {'type': 'include_set', 'value': subset}
        country_text = f"- 国家：仅保留集合 {subset}"
    else:
        country_rule = {'type': 'none'}
        country_text = '- 国家：无'

    # 设备规则
    device_rule_type = rng.choices(['non_empty', 'allowed_set', 'equals', 'none'], weights=[0.45, 0.25, 0.2, 0.1], k=1)[0]
    if device_rule_type == 'non_empty':
        device_rule = {'type': 'non_empty'}
        device_text = '- 设备：device_type 非空'
    elif device_rule_type == 'allowed_set':
        subset = rng.sample(['mobile', 'desktop', 'tablet'], rng.randint(1, 3))
        device_rule = {'type': 'allowed_set', 'value': subset}
        device_text = f"- 设备：仅保留 {subset}"
    elif device_rule_type == 'equals':
        val = rng.choice(['mobile', 'desktop', 'tablet'])
        device_rule = {'type': 'equals', 'value': val}
        device_text = f"- 设备：device_type 等于 {val}"
    else:
        device_rule = {'type': 'none'}
        device_text = '- 设备：无'

    # 消息活跃规则
    emax = max(5, int(gen_params.get('emails_sent_max', 1200)))
    smax = max(5, int(gen_params.get('sms_sent_max', 600)))
    msg_rule_type = rng.choice(['or_nonzero', 'email_gt', 'sms_gt', 'and_nonzero', 'sum_gt'])
    t_email = rng.randint(1, max(2, emax // 3))
    t_sms = rng.randint(1, max(2, smax // 3))
    t_sum = rng.randint(2, max(3, (emax + smax) // 4))
    if msg_rule_type == 'or_nonzero':
        msg_rule = {'type': 'or_nonzero'}
        msg_text = '- 活跃：emails_sent 非零 或 sms_sent 非零'
    elif msg_rule_type == 'email_gt':
        msg_rule = {'type': 'email_gt', 't': t_email}
        msg_text = f"- 活跃：emails_sent > {t_email}"
    elif msg_rule_type == 'sms_gt':
        msg_rule = {'type': 'sms_gt', 't': t_sms}
        msg_text = f"- 活跃：sms_sent > {t_sms}"
    elif msg_rule_type == 'and_nonzero':
        msg_rule = {'type': 'and_nonzero'}
        msg_text = '- 活跃：emails_sent 与 sms_sent 均非零'
    else:
        msg_rule = {'type': 'sum_gt', 't': t_sum}
        msg_text = f"- 活跃：emails_sent + sms_sent > {t_sum}"

    # 库存规则
    inv_max = max(5, int(gen_params.get('inventory_max', 600)))
    t_inv = rng.randint(1, max(2, inv_max // 2))
    inv_op = rng.choice(['gt', 'ge'])
    inv_rule = {'type': inv_op, 't': t_inv}
    op_text = '>' if inv_op == 'gt' else '>='
    inventory_text = f"- 库存：inventory_level {op_text} {t_inv}"

    # 竞品价格规则（可选）
    comp_rel_type = rng.choice(['none', 'ge_threshold', 'le_threshold'])
    comp_rule = {'type': 'none'}
    comp_text = '- 竞品价格：无'
    if comp_rel_type != 'none':
        low = float(gen_params.get('competitor_price_min', 8.0))
        high = float(gen_params.get('competitor_price_max', 150.0))
        t_comp = round(rng.uniform(low, high), 2)
        comp_rule = {'type': comp_rel_type, 't': t_comp}
        comp_text = f"- 竞品价格：competitor_price_usd {'>=' if comp_rel_type=='ge_threshold' else '<='} {t_comp}"

    # 原子规则聚合器
    agg_type = rng.choice(['all', 'at_least_k'])
    atoms = ['country', 'device', 'message', 'inventory', 'competitor_price']
    if agg_type == 'at_least_k':
        k = rng.randint(2, len(atoms))
        agg = {'type': 'at_least_k', 'k': k}
        agg_text = f"- 聚合器：至少满足 {k} 条原子规则"
    else:
        agg = {'type': 'all'}
        agg_text = '- 聚合器：全部规则需要同时满足'

    # IQR 去极值
    iqr_candidates = ['page_load_ms', 'bounce_rate_pct', 'avg_session_duration_sec']
    iqr_num = rng.choice([0, 1, 2, 3])
    iqr_rules, iqr_texts = [], []
    for _ in range(iqr_num):
        field = rng.choice(iqr_candidates)
        whisker = round(rng.uniform(1.0, 2.0), 1)
        sides = rng.choice(['both', 'upper', 'lower'])
        iqr_rules.append({'field': field, 'whisker': whisker, 'sides': sides})
        side_word = {'both': '上下界', 'upper': '仅上界', 'lower': '仅下界'}[sides]
        iqr_texts.append(f"- IQR：字段 {field}，胡须系数 {whisker}，{side_word}剔除")

    # 稳定性分数
    alpha_page = round(random.uniform(0.4, 1.4), 2)
    alpha_bounce = round(random.uniform(-1.4, -0.4), 2)
    alpha_session = round(random.uniform(0.2, 1.2), 2)
    alpha_comp = round(random.uniform(-0.8, -0.2), 2)
    thresh_mode = random.choice(['quantile', 'absolute'])
    if thresh_mode == 'quantile':
        q = round(random.uniform(0.6, 0.85), 2)
        stability = {'alphas': [alpha_page, alpha_bounce, alpha_session, alpha_comp], 'mode': 'quantile', 'q': q}
        stab_text = f"- 稳定性分数：Sigmoid(复合z-score)，仅保留分位点 {q} 及以上"
    else:
        t_abs = round(random.uniform(0.5, 0.8), 2)
        stability = {'alphas': [alpha_page, alpha_bounce, alpha_session, alpha_comp], 'mode': 'absolute', 't': t_abs}
        stab_text = f"- 稳定性分数：Sigmoid(复合z-score)，仅保留分数 >= {t_abs}"

    # 方差模式
    var_mode = random.choice(['plain', 'weighted'])
    var_text = '- 方差模式：普通样本方差' if var_mode=='plain' else '- 方差模式：加权样本方差（无偏估计）'

    # 比率定义
    ratio_candidates = [
        {'name': 'conversions/impressions', 'num': 'conversions', 'den': 'impressions', 'den_min_range': (50, 220), 'den_ops': ['>=', '>'], 'num_nonneg': True},
        {'name': 'clicks/impressions',      'num': 'clicks',      'den': 'impressions', 'den_min_range': (50, 220), 'den_ops': ['>=', '>'], 'num_nonneg': True},
        {'name': 'spend_usd/clicks',        'num': 'spend_usd',   'den': 'clicks',      'den_min_range': (1, 250),  'den_ops': ['>', '>='], 'num_nonneg': True},
        {'name': 'spend_usd/conversions',   'num': 'spend_usd',   'den': 'conversions', 'den_min_range': (1, 250),  'den_ops': ['>', '>='], 'num_nonneg': True},
    ]
    def _mk_ratio(r: Dict[str, Any], rr: random.Random) -> Dict[str, Any]:
        den_t = rr.randint(r['den_min_range'][0], r['den_min_range'][1])
        den_op = rr.choice(r['den_ops'])
        return {'name': r['name'], 'num': r['num'], 'den': r['den'], 'den_op': den_op, 'den_t': den_t, 'num_nonneg': r['num_nonneg']}
    r1 = random.choice(ratio_candidates)
    r2 = random.choice([x for x in ratio_candidates if x['name'] != r1['name']])
    ratioA = _mk_ratio(r1, rng)
    ratioB = _mk_ratio(r2, rng)

    rules_lines = [country_text, device_text, msg_text, inventory_text, comp_text, agg_text] + (iqr_texts if iqr_texts else ['- IQR：无']) + [stab_text, var_text]
    rules_text = '\\n'.join(rules_lines)
    metrics_text = f"- 比率A：{ratioA['name']}，分母约束 {ratioA['den']} {ratioA['den_op']} {ratioA['den_t']}，分子需非负；\\n- 比率B：{ratioB['name']}，分母约束 {ratioB['den']} {ratioB['den_op']} {ratioB['den_t']}，分子需非负。"

    return {
        'country_rule': country_rule,
        'device_rule': device_rule,
        'msg_rule': msg_rule,
        'inventory_rule': inv_rule,
        'competitor_rule': comp_rule,
        'agg': agg,
        'iqr_rules': iqr_rules,
        'stability': stability,
        'var_mode': var_mode,
        'ratioA': ratioA,
        'ratioB': ratioB,
        'rules_text': rules_text,
        'metrics_text': metrics_text
    }

# ------------------ 数据生成 ------------------
def function_1(columns: List[str], row_count: int, params: Dict[str, Any]) -> Dict[str, Any]:
    rng = random.Random(params.get('rng_seed', 42))
    if not isinstance(columns, list) or len(columns) != 24:
        columns = DEFAULT_COLUMNS[:]
    row_count = max(20, min(36, int(row_count)))

    rows: List[List[Any]] = []
    rows.append(columns[:])

    start_day = date(2025, 6, 1)
    country_pool = ['US', 'GB', 'DE', 'IN', 'BR', 'CN', 'CA', 'AU', 'FR', 'JP']
    device_pool = ['mobile', 'desktop', 'tablet', '']  # '' 代表空
    ad_pos_pool = ['top', 'side', 'feed', 'search']
    channel_pool = ['Paid Search', 'Email', 'Social', 'SMS', 'Direct', 'Referral']

    dev_weights = [0.45, 0.45, 0.08, float(params.get('device_empty_prob', 0.02))]
    s = sum(dev_weights)
    dev_weights = [w / s for w in dev_weights]
    base_weight = (1.0 - float(params.get('include_CN_prob', 0.18))) / (len(country_pool) - 1)
    country_weights = [base_weight] * len(country_pool)
    country_weights[country_pool.index('CN')] = float(params.get('include_CN_prob', 0.18))

    for i in range(1, row_count):
        d = start_day + timedelta(days=i-1)
        d_str = d.isoformat()
        camp_id = f'CAMP{100 + i:03d}'

        impressions = rng.randint(int(params.get('impressions_min', 80)), int(params.get('impressions_max', 3000)))
        ctr = rng.uniform(float(params.get('ctr_min', 0.005)), float(params.get('ctr_max', 0.12)))
        clicks = int(max(0, round(impressions * ctr)))
        conv_rate_on_click = rng.uniform(float(params.get('conv_min_pct', 0.00)), float(params.get('conv_max_pct', 0.25)))
        conversions = int(max(0, round(clicks * conv_rate_on_click)))
        avg_cpc_sim = rng.uniform(float(params.get('cpc_min', 0.2)), float(params.get('cpc_max', 2.5)))
        spend_usd = round(avg_cpc_sim * clicks, 2)

        avg_sess = round(rng.uniform(20, 900), 1)
        if rng.random() < float(params.get('outlier_prob_bounce', 0.10)):
            bounce = round(rng.uniform(max(15, float(params.get('bounce_normal_max', 80))), float(params.get('bounce_outlier_max', 120))), 2)
        else:
            bounce = round(rng.uniform(15, float(params.get('bounce_normal_max', 80))), 2)

        device = rng.choices(device_pool, weights=dev_weights, k=1)[0]
        country = rng.choices(country_pool, weights=country_weights, k=1)[0]

        if rng.random() < float(params.get('outlier_prob_page', 0.12)):
            page_load = round(rng.uniform(max(600, float(params.get('page_load_normal_max', 4500))), float(params.get('page_load_outlier_max', 15000))), 1)
        else:
            page_load = round(rng.uniform(600, float(params.get('page_load_normal_max', 4500))), 1)

        emails_sent = rng.randint(0, int(params.get('emails_sent_max', 1200)))
        emails_opened = rng.randint(0, emails_sent) if emails_sent > 0 else 0
        sms_sent = rng.randint(0, int(params.get('sms_sent_max', 600)))
        sms_responses = rng.randint(0, sms_sent) if sms_sent > 0 else 0

        ad_position = rng.choice(ad_pos_pool)
        promo_code_used = rng.randint(0, 1)
        inventory_level = rng.randint(0, int(params.get('inventory_max', 600)))
        competitor_price_usd = round(rng.uniform(float(params.get('competitor_price_min', 8.0)), float(params.get('competitor_price_max', 150.0))), 2)

        if clicks > 0:
            cpc_usd = round(spend_usd / clicks, 4)
        else:
            cpc_usd = round(rng.uniform(float(params.get('cpc_min', 0.2)), float(params.get('cpc_max', 2.5))), 4)

        roas = round(rng.uniform(0.0, float(params.get('roas_max', 9.0))), 3)
        return_visits = rng.randint(0, int(params.get('return_visits_max', 250)))
        channel_group = rng.choice(channel_pool)

        m = d.month
        season = 'Spring' if m in (3,4,5) else ('Summer' if m in (6,7,8) else ('Autumn' if m in (9,10,11) else 'Winter'))

        row = [
            d_str, camp_id, impressions, clicks, spend_usd, conversions,
            avg_sess, bounce, device, country, page_load, emails_sent,
            emails_opened, sms_sent, sms_responses, ad_position, promo_code_used,
            inventory_level, competitor_price_usd, cpc_usd, roas, return_visits,
            channel_group, season
        ]
        rows.append(row)

    col_data: List[List[Any]] = []
    for j in range(len(columns)):
        col = [rows[i][j] for i in range(row_count)]
        tail_n = j + 1
        rng_tail = random.Random(int(params.get('rng_seed', 42)) + j * 9973)
        for _ in range(tail_n):
            col.append(_random_tail_for_column(columns[j], rng_tail))
        col_data.append(col)

    return {'col_data': col_data, 'display_rows': rows}

def _random_tail_for_column(col_name: str, rng: random.Random) -> Any:
    if col_name in ('date', 'campaign_id', 'device_type', 'country', 'ad_position', 'channel_group', 'season'):
        return rng.choice(['NA', 'X', 'tmp', 'misc', 'unknown', ''])
    elif col_name in ('promo_code_used',):
        return rng.randint(0, 1)
    elif col_name in ('impressions','clicks','conversions','emails_sent','emails_opened',
                      'sms_sent','sms_responses','inventory_level','return_visits'):
        return rng.randint(0, 3000)
    elif col_name in ('spend_usd','competitor_price_usd','cpc_usd','roas'):
        return round(rng.uniform(0.0, 200.0), 4)
    elif col_name in ('avg_session_duration_sec','page_load_ms'):
        return round(rng.uniform(0.0, 16000.0), 2)
    elif col_name in ('bounce_rate_pct',):
        return round(rng.uniform(0.0, 160.0), 3)
    else:
        return None

# ------------------ 内部通用过滤与计算 ------------------
def _apply_atomic_filters(records: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    def keep_country(val: Any) -> bool:
        rule = rules.get('country_rule', {'type': 'none'})
        t = rule.get('type', 'none')
        if not isinstance(val, str):
            return False if t != 'none' else True
        if t == 'exclude_one':
            return val != rule.get('value')
        elif t == 'include_set':
            allowed = rule.get('value', [])
            return val in allowed
        else:
            return True

    def keep_device(val: Any) -> bool:
        rule = rules.get('device_rule', {'type': 'non_empty'})
        t = rule.get('type', 'non_empty')
        if not isinstance(val, str):
            return False if t != 'none' else True
        if t == 'non_empty':
            return val != ''
        elif t == 'allowed_set':
            allowed = rule.get('value', [])
            return val in allowed
        elif t == 'equals':
            return val == rule.get('value')
        else:
            return True

    def keep_message(e: Optional[int], s: Optional[int]) -> bool:
        rule = rules.get('msg_rule', {'type': 'or_nonzero'})
        t = rule.get('type', 'or_nonzero')
        if t == 'or_nonzero':
            return (e is not None and e != 0) or (s is not None and s != 0)
        elif t == 'email_gt':
            T = rule.get('t', 0)
            return e is not None and e > T
        elif t == 'sms_gt':
            T = rule.get('t', 0)
            return s is not None and s > T
        elif t == 'and_nonzero':
            return (e is not None and e != 0) and (s is not None and s != 0)
        elif t == 'sum_gt':
            T = rule.get('t', 0)
            if e is None or s is None:
                return False
            return (e + s) > T
        else:
            return False

    def keep_inventory(inv: Optional[int]) -> bool:
        rule = rules.get('inventory_rule', {'type': 'gt', 't': 0})
        t = rule.get('type', 'gt')
        T = rule.get('t', 0)
        if inv is None:
            return False
        if t == 'gt':
            return inv > T
        elif t == 'ge':
            return inv >= T
        return False

    def keep_competitor(price: Optional[float]) -> bool:
        rule = rules.get('competitor_rule', {'type': 'none'})
        t = rule.get('type', 'none')
        if t == 'none':
            return True
        if price is None:
            return False
        T = rule.get('t', 0.0)
        if t == 'ge_threshold':
            return price >= T
        elif t == 'le_threshold':
            return price <= T
        return True

    atoms = []
    for rec in records:
        e = _safe_int(rec.get('emails_sent'))
        s = _safe_int(rec.get('sms_sent'))
        inv = _safe_int(rec.get('inventory_level'))
        price = _safe_float(rec.get('competitor_price_usd'))
        res = [
            keep_country(rec.get('country')),
            keep_device(rec.get('device_type')),
            keep_message(e, s),
            keep_inventory(inv),
            keep_competitor(price)
        ]
        atoms.append((rec, res))

    agg = rules.get('agg', {'type': 'all'})
    filtered = []
    for rec, res in atoms:
        if agg.get('type') == 'at_least_k':
            k = int(agg.get('k', 3))
            if sum(1 for x in res if x) >= k:
                filtered.append(rec)
        else:
            if all(res):
                filtered.append(rec)
    return filtered

def _apply_iqr(recs: List[Dict[str, Any]], iqr_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def apply_one(recs: List[Dict[str, Any]], field: str, whisker: float, sides: str) -> List[Dict[str, Any]]:
        vals = [_safe_float(r.get(field)) for r in recs]
        vals = [v for v in vals if v is not None]
        if len(vals) == 0:
            return recs
        bounds = _iqr_bounds(vals, whisker)
        if bounds is None:
            return recs
        low, high = bounds
        kept = []
        for r in recs:
            v = _safe_float(r.get(field))
            if v is None:
                kept.append(r)
                continue
            ok = True
            if sides in ('both', 'lower'):
                if v < low:
                    ok = False
            if sides in ('both', 'upper'):
                if v > high:
                    ok = False
            if ok:
                kept.append(r)
        return kept

    out = recs[:]
    for rule in iqr_rules:
        out = apply_one(out, rule.get('field'), float(rule.get('whisker', 1.5)), rule.get('sides', 'both'))
        if len(out) == 0:
            return []
    return out

def _compute_stability_and_mask(recs: List[Dict[str, Any]], st: Dict[str, Any]) -> Tuple[List[float], List[bool]]:
    a1, a2, a3, a4 = [float(x) for x in st.get('alphas', [1, -1, 1, -0.5])]
    page = [_safe_float(r.get('page_load_ms')) for r in recs]
    bounce = [_safe_float(r.get('bounce_rate_pct')) for r in recs]
    sess = [_safe_float(r.get('avg_session_duration_sec')) for r in recs]
    comp = [_safe_float(r.get('competitor_price_usd')) for r in recs]
    z_page = _zscore(page)
    z_bounce = _zscore(bounce)
    z_sess = _zscore(sess)
    z_comp = _zscore(comp)
    scores = []
    for zp, zb, zs, zc in zip(z_page, z_bounce, z_sess, z_comp):
        if None in (zp, zb, zs, zc):
            scores.append(0.0)
        else:
            scores.append(_sigmoid(a1*zp + a2*zb + a3*zs + a4*zc))
    if st.get('mode') == 'absolute':
        T = float(st.get('t', 0.6))
        mask = [sc >= T for sc in scores]
    else:
        q = float(st.get('q', 0.7))
        sorted_sc = sorted(scores)
        if len(sorted_sc) == 0:
            return scores, [False]*len(scores)
        pos = (len(sorted_sc)-1)*q
        lo = int(math.floor(pos)); hi = int(math.ceil(pos))
        th = sorted_sc[lo] if lo == hi else (sorted_sc[lo] + (sorted_sc[hi]-sorted_sc[lo])*(pos-lo))
        mask = [sc >= th for sc in scores]
    return scores, mask

def _build_ratio_values(recs: List[Dict[str, Any]], ratio_def: Dict[str, Any]) -> List[float]:
    num_col = ratio_def['num']; den_col = ratio_def['den']
    den_op = ratio_def.get('den_op', '>='); den_t = float(ratio_def.get('den_t', 0))
    num_nonneg = bool(ratio_def.get('num_nonneg', True))
    out = []
    for r in recs:
        num = _safe_float(r.get(num_col)); den = _safe_float(r.get(den_col))
        if num is None or den is None or den == 0:
            continue
        if num_nonneg and num < 0:
            continue
        if den_op == '>' and not (den > den_t):
            continue
        if den_op == '>=' and not (den >= den_t):
            continue
        out.append(num / den)
    return out

# ------------------ 规则校准 ------------------
def function_calibrate_rules(columns: List[str], col_data: List[List[Any]], row_count: int, rules_config_raw: Dict[str, Any]) -> Dict[str, Any]:
    # 构造记录（忽略尾部噪声，跳过表头）
    idx = {name: i for i, name in enumerate(columns)}
    cols_trimmed = [col[:row_count] for col in col_data]
    records = [{name: cols_trimmed[idx[name]][r] for name in columns} for r in range(1, row_count)]

    # 复制原规则并统一先筛后算
    cfg = {k: v for k, v in rules_config_raw.items()}
    cfg['order_mode'] = 'filter_then_ratio'

    # 原子规则 + IQR
    filtered = _apply_atomic_filters(records, cfg)
    filtered = _apply_iqr(filtered, cfg.get('iqr_rules', []))

    # 稳定性筛选（若样本过少则放宽）
    st = cfg.get('stability', {'alphas':[1,-1,1,-0.5], 'mode':'quantile', 'q':0.7})
    scores, mask = _compute_stability_and_mask(filtered, st)
    filtered_stable = [r for r, keep in zip(filtered, mask) if keep]

    if len(filtered_stable) < 6 and len(filtered) >= 6:
        if st.get('mode') == 'absolute':
            t_abs = max(0.4, float(st.get('t', 0.6)) - 0.1)
            cfg['stability'] = {'alphas': st.get('alphas', [1,-1,1,-0.5]), 'mode':'absolute', 't': round(t_abs, 2)}
        else:
            q = max(0.5, float(st.get('q', 0.7)) - 0.1)
            cfg['stability'] = {'alphas': st.get('alphas', [1,-1,1,-0.5]), 'mode':'quantile', 'q': round(q, 2)}
        st = cfg['stability']
        scores, mask = _compute_stability_and_mask(filtered, st)
        filtered_stable = [r for r, keep in zip(filtered, mask) if keep]

    # 比率阈值校准：保证各自至少2个样本
    def adjust_ratio(ratio_def: Dict[str, Any], q_target: float) -> Dict[str, Any]:
        den_vals = [_safe_float(r.get(ratio_def['den'])) for r in filtered_stable]
        den_vals = [v for v in den_vals if v is not None and v > 0]
        if len(den_vals) == 0:
            return ratio_def
        den_vals_sorted = sorted(den_vals)
        pos = (len(den_vals_sorted)-1) * q_target
        lo = int(math.floor(pos)); hi = int(math.ceil(pos))
        th = den_vals_sorted[lo] if lo == hi else (den_vals_sorted[lo] + (den_vals_sorted[hi]-den_vals_sorted[lo])*(pos-lo))
        r2 = dict(ratio_def)
        r2['den_t'] = max(1.0, round(th, 2))
        r2['den_op'] = '>='
        return r2

    ratioA = adjust_ratio(cfg.get('ratioA'), 0.6)
    ratioB = adjust_ratio(cfg.get('ratioB'), 0.6)
    A_vals = _build_ratio_values(filtered_stable, ratioA)
    B_vals = _build_ratio_values(filtered_stable, ratioB)
    if len(A_vals) < 2 or len(B_vals) < 2:
        ratioA = adjust_ratio(ratioA, 0.5)
        ratioB = adjust_ratio(ratioB, 0.5)

    cfg['ratioA'] = ratioA
    cfg['ratioB'] = ratioB

    # 文本重建
    def rules_text_from_cfg(cfg: Dict[str, Any]) -> str:
        c = cfg.get('country_rule', {'type':'none'})
        if c.get('type') == 'exclude_one':
            country_text = f"- 国家：排除 {c.get('value')}"
        elif c.get('type') == 'include_set':
            country_text = f"- 国家：仅保留集合 {c.get('value')}"
        else:
            country_text = "- 国家：无"
        d = cfg.get('device_rule', {'type':'none'})
        if d.get('type') == 'non_empty':
            device_text = "- 设备：device_type 非空"
        elif d.get('type') == 'allowed_set':
            device_text = f"- 设备：仅保留 {d.get('value')}"
        elif d.get('type') == 'equals':
            device_text = f"- 设备：device_type 等于 {d.get('value')}"
        else:
            device_text = "- 设备：无"
        m = cfg.get('msg_rule', {'type':'or_nonzero'})
        if m.get('type') == 'or_nonzero':
            msg_text = "- 活跃：emails_sent 非零 或 sms_sent 非零"
        elif m.get('type') == 'email_gt':
            msg_text = f"- 活跃：emails_sent > {m.get('t')}"
        elif m.get('type') == 'sms_gt':
            msg_text = f"- 活跃：sms_sent > {m.get('t')}"
        elif m.get('type') == 'and_nonzero':
            msg_text = "- 活跃：emails_sent 与 sms_sent 均非零"
        else:
            msg_text = f"- 活跃：emails_sent + sms_sent > {m.get('t')}"
        i = cfg.get('inventory_rule', {'type':'gt','t':0})
        inventory_text = f"- 库存：inventory_level {'>' if i.get('type')=='gt' else '>='} {i.get('t')}"
        cp = cfg.get('competitor_rule', {'type':'none'})
        if cp.get('type') == 'none':
            comp_text = "- 竞品价格：无"
        else:
            comp_text = f"- 竞品价格：competitor_price_usd {'>=' if cp.get('type')=='ge_threshold' else '<='} {cp.get('t')}"
        agg = cfg.get('agg', {'type':'all'})
        agg_text = f"- 聚合器：至少满足 {agg.get('k')} 条原子规则" if agg.get('type')=='at_least_k' else "- 聚合器：全部规则需要同时满足"
        iqr_rules = cfg.get('iqr_rules', [])
        iqr_texts = []
        for rule in iqr_rules:
            side_word = {'both': '上下界', 'upper': '仅上界', 'lower': '仅下界'}[rule.get('sides','both')]
            iqr_texts.append(f"- IQR：字段 {rule.get('field')}，胡须系数 {rule.get('whisker')}，{side_word}剔除")
        if not iqr_texts:
            iqr_texts = ['- IQR：无']
        st = cfg.get('stability', {'mode':'quantile','q':0.7})
        if st.get('mode')=='absolute':
            stab_text = f"- 稳定性分数：Sigmoid(复合z-score)，仅保留分数 >= {st.get('t')}"
        else:
            stab_text = f"- 稳定性分数：Sigmoid(复合z-score)，仅保留分位点 {st.get('q')} 及以上"
        vm = cfg.get('var_mode','plain')
        var_text = '- 方差模式：普通样本方差' if vm=='plain' else '- 方差模式：加权样本方差（无偏估计）'
        return '\\n'.join([country_text, device_text, msg_text, inventory_text, comp_text, agg_text] + iqr_texts + [stab_text, var_text])

    def metrics_text_from_cfg(cfg: Dict[str, Any]) -> str:
        rA = cfg.get('ratioA'); rB = cfg.get('ratioB')
        ta = f"- 比率A：{rA['name']}，分母约束 {rA['den']} {rA['den_op']} {rA['den_t']}，分子需非负；"
        tb = f"- 比率B：{rB['name']}，分母约束 {rB['den']} {rB['den_op']} {rB['den_t']}，分子需非负。"
        return ta + "\\n" + tb

    cfg['rules_text'] = rules_text_from_cfg(cfg)
    cfg['metrics_text'] = metrics_text_from_cfg(cfg)
    return cfg

# ------------------ 按规则计算答案 ------------------
def function_2(columns: List[str], col_data: List[List[Any]], row_count: int, rules_config: Dict[str, Any]) -> str:
    idx = {name: i for i, name in enumerate(columns)}
    cols_trimmed = [col[:row_count] for col in col_data]
    records = [{name: cols_trimmed[idx[name]][r] for name in columns} for r in range(1, row_count)]

    filtered = _apply_atomic_filters(records, rules_config)
    if len(filtered) == 0:
        return '0.00'
    filtered = _apply_iqr(filtered, rules_config.get('iqr_rules', []))
    if len(filtered) == 0:
        return '0.00'

    scores, mask = _compute_stability_and_mask(filtered, rules_config.get('stability', {'mode':'quantile','q':0.7}))
    filtered_stable = [r for r, keep in zip(filtered, mask) if keep]
    weights = [sc for sc, keep in zip(scores, mask) if keep]
    if len(filtered_stable) < 2:
        return '0.00'

    ratioA = rules_config.get('ratioA'); ratioB = rules_config.get('ratioB')
    A_vals = _build_ratio_values(filtered_stable, ratioA)
    B_vals = _build_ratio_values(filtered_stable, ratioB)
    if len(A_vals) < 2 or len(B_vals) < 2:
        return '0.00'

    if rules_config.get('var_mode','plain') == 'weighted' and len(weights) == len(filtered_stable):
        varA = _weighted_sample_variance(A_vals, weights[:len(A_vals)]) or _sample_variance(A_vals)
        varB = _weighted_sample_variance(B_vals, weights[:len(B_vals)]) or _sample_variance(B_vals)
    else:
        varA = _sample_variance(A_vals)
        varB = _sample_variance(B_vals)
    if varA is None or varB is None:
        return '0.00'
    diff = abs(varA - varB)
    return f'{diff:.2f}'

# ------------------ 唯一解验证 ------------------
def function_verify_unique(columns: List[str], col_data: List[List[Any]], row_count: int, rules_config: Dict[str, Any], ans_str: str) -> bool:
    try:
        recomputed = function_2(columns, col_data, row_count, rules_config)
        # 额外验证：两个比率各自至少2个样本
        idx = {name: i for i, name in enumerate(columns)}
        cols_trimmed = [col[:row_count] for col in col_data]
        records = [{name: cols_trimmed[idx[name]][r] for name in columns} for r in range(1, row_count)]
        filtered = _apply_atomic_filters(records, rules_config)
        filtered = _apply_iqr(filtered, rules_config.get('iqr_rules', []))
        scores, mask = _compute_stability_and_mask(filtered, rules_config.get('stability', {'mode':'quantile','q':0.7}))
        filtered_stable = [r for r, keep in zip(filtered, mask) if keep]
        if len(filtered_stable) < 2:
            return False
        A_vals = _build_ratio_values(filtered_stable, rules_config.get('ratioA'))
        B_vals = _build_ratio_values(filtered_stable, rules_config.get('ratioB'))
        if len(A_vals) < 2 or len(B_vals) < 2:
            return False
        return str(recomputed) == str(ans_str)
    except Exception:
        return False