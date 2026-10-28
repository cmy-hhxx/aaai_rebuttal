# buggy_tables_0.py
from typing import Any, Dict, List, Optional, Union
import random
import math
import datetime
import re

Number = Union[int, float]

# -------------------------
# Utilities
# -------------------------
def to_string(x: Any) -> str:
    return str(x)

def getk(d: Dict[str, Any], key: str) -> Any:
    return d.get(key)

def _to_number(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except Exception:
            return None
    return None

def _op_check_num(op: str, lhs: float, rhs: float) -> bool:
    if op == '>=':
        return lhs >= rhs
    if op == '<=':
        return lhs <= rhs
    if op == '>':
        return lhs > rhs
    if op == '<':
        return lhs < rhs
    if op == '==':
        return lhs == rhs
    if op == '!=':
        return lhs != rhs
    return False

def _rand_date() -> str:
    start = datetime.date(2024, 1, 1).toordinal()
    end = datetime.date(2026, 12, 31).toordinal()
    d = datetime.date.fromordinal(random.randint(start, end))
    return d.isoformat()

def _rand_time() -> str:
    h = random.randint(20, 23)
    m = random.randint(0, 59)
    return f'{h:02d}:{m:02d}'

def _rand_weekday() -> str:
    return random.choice(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])

def _maybe_none(p: float, value: Any) -> Any:
    return None if random.random() < p else value

def _numeric_pool() -> List[str]:
    return [
        'num_steps', 'study_minutes', 'exercise_minutes', 'sleep_minutes',
        'num_messages', 'num_emails', 'num_calls', 'calories_burned',
        'calories_consumed', 'num_meetings', 'coding_minutes',
        'num_tasks_completed', 'water_intake_ml',
        'phone_screen_time_minutes', 'music_listening_minutes',
        'walking_minutes', 'running_minutes', 'reading_minutes',
        'writing_minutes', 'meditation_minutes', 'breaks_taken',
        'focus_score', 'task_backlog', 'bug_count', 'feature_points',
        'build_minutes', 'review_minutes', 'merge_requests', 'deploy_count',
        'errors_count', 'uptime_minutes', 'support_tickets', 'commits',
        'loc_changed', 'tab_switches', 'context_switches',
        'meetings_minutes', 'coffee_cups', 'hydration_events',
        'stairs_climbed', 'heart_rate_avg', 'tickets_resolved',
        'pair_sessions', 'unit_tests', 'integration_tests',
        'pr_comments', 'refactor_minutes', 'context_retention',
        'daily_focus_minutes', 'deep_work_minutes'
    ]

def _nonnumeric_pool() -> List[str]:
    return [
        'date', 'weekday', 'bed_time', 'mood', 'project', 'device',
        'app_used', 'note'
    ]

def _gen_numeric_value(name: str) -> float:
    if 'minutes' in name:
        return float(random.randint(0, 600))
    if 'num_' in name or name.endswith('_count') or 'tickets' in name:
        return float(random.randint(0, 300))
    if 'calories' in name:
        return float(random.randint(800, 4000))
    if 'steps' in name:
        return float(random.randint(0, 25000))
    if 'ml' in name:
        return float(random.randint(0, 4000))
    if 'score' in name:
        return float(random.randint(0, 100))
    if 'loc' in name:
        return float(random.randint(0, 2000))
    if 'heart_rate' in name:
        return float(random.randint(50, 160))
    return float(random.randint(0, 3000))

def _choose_distinct(seq: List[str], k: int) -> List[str]:
    if k <= 0:
        return []
    return random.sample(seq, k)

def _format_op_text(op: str) -> str:
    mapping = {
        '>=': '≥',
        '<=': '≤',
        '>': '大于',
        '<': '小于',
        '==': '等于',
        '!=': '不等于'
    }
    return mapping.get(op, op)

def _time_to_min(t: str) -> Optional[int]:
    try:
        h, m = t.split(':')
        return int(h) * 60 + int(m)
    except Exception:
        return None

def _in_night(t: Any) -> bool:
    if not isinstance(t, str):
        return False
    mm = _time_to_min(t)
    if mm is None:
        return False
    return 1320 <= mm <= 1439  # 22:00–23:59

def _group_values(name: str) -> List[str]:
    if name == 'weekday':
        return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    if name == 'project':
        return ['Alpha', 'Beta', 'Gamma', 'Delta']
    if name == 'device':
        return ['iOS', 'Android', 'Web']
    if name == 'app_used':
        return ['Mail', 'Docs', 'Chat', 'IDE', 'Browser']
    return ['A', 'B', 'C', 'D']

# -------------------------
# Text builders
# -------------------------
def build_filter_text(inst: Dict[str, Any]) -> str:
    """
    Return human-friendly description of filter (AND/OR/K-of-N) and night gate if enabled.
    """
    conds = inst['conds']
    mode = inst['comb_mode']
    k_of = inst.get('k_of', None)
    night_only = inst.get('night_only', False)

    if mode == 'AND':
        head = '以下全部条件'
    elif mode == 'OR':
        head = '以下任一条件'
    else:
        head = f'以下 {len(conds)} 条条件中至少 {k_of} 条'

    parts: List[str] = []
    for i, c in enumerate(conds, 1):
        if c['op'] == 'range':
            lo = c['lo']
            hi = c['hi']
            parts.append(f'{i}) {lo} ≤ {c["col"]} ≤ {hi}')
        else:
            op_text = _format_op_text(c['op'])
            parts.append(f'{i}) {c["col"]} {op_text} {c["val"]}')
    if night_only:
        parts.append('额外限制：仅在 22:00–23:59 的记录视为有效')
    return f'{head}：\\n' + '；'.join(parts)

def build_metric_text(inst: Dict[str, Any]) -> str:
    t = inst['metric_type']
    if t == 'var':
        return '样本方差'
    if t == 'std':
        return '样本标准差'
    return '算术平均值'

def build_control_metric_text(inst: Dict[str, Any]) -> str:
    t = inst['control_metric_type']
    if t == 'var':
        return '控制度量：样本方差'
    if t == 'std':
        return '控制度量：样本标准差'
    return '控制度量：算术平均值'

def build_group_rule_text(inst: Dict[str, Any]) -> str:
    gcol = inst['group_col']
    ccol = inst['control_col']
    t = inst['control_metric_type']
    metric_name = '样本方差' if t == 'var' else ('样本标准差' if t == 'std' else '算术平均值')
    need = 2 if t in ('var', 'std') else 1
    return (
        f'在满足筛选的记录中，按列 {gcol} 分组；'
        f'仅对在列 {ccol} 上样本数≥{need}的分组计算{metric_name}并参与比较；'
        f'选择该控制度量最大的分组作为目标分组；如出现并列最大，则选择分组名称字典序最小者'
    )

# -------------------------
# Stats helpers
# -------------------------
def _sample_variance(values: List[float]) -> Optional[float]:
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    ssd = sum((v - mean) ** 2 for v in values)
    return ssd / (n - 1)

def _sample_std(values: List[float]) -> Optional[float]:
    var = _sample_variance(values)
    if var is None:
        return None
    return math.sqrt(var)

def _mean(values: List[float]) -> Optional[float]:
    if len(values) < 1:
        return None
    return sum(values) / float(len(values))

def _metric_compute(kind: str, values: List[float]) -> Optional[float]:
    if kind == 'var':
        return _sample_variance(values)
    if kind == 'std':
        return _sample_std(values)
    return _mean(values)

def _metric_min_samples(kind: str) -> int:
    return 2 if kind in ('var', 'std') else 1

# -------------------------
# Generation and solving
# -------------------------
def mk_instance() -> Dict[str, Any]:
    n_rows = random.randint(7, 11)   # includes header
    n_cols = random.randint(14, 22)

    num_pool = _numeric_pool()
    non_pool = _nonnumeric_pool()

    targets = _choose_distinct(num_pool, 2)

    cond_count = random.randint(2, 4)
    cond_cols = _choose_distinct([c for c in num_pool if c not in targets] + targets, cond_count)

    conds: List[Dict[str, Any]] = []
    for col in cond_cols:
        if random.random() < 0.45:
            lo = float(random.randint(5, 60))
            hi = lo + float(random.randint(5, 80))
            if lo > hi:
                lo, hi = hi, lo
            conds.append({'col': col, 'op': 'range', 'lo': lo, 'hi': hi})
        else:
            # 禁用 '!='，保留更具约束性的运算符
            op = random.choice(['>=', '<=', '>', '<', '=='])
            base = _gen_numeric_value(col)
            if op == '==':
                val = float(random.randint(1, 80))
            else:
                if 'score' in col:
                    val = float(random.randint(10, 90))
                else:
                    span = max(20, int(base // 2) if base > 0 else 100)
                    val = float(max(0, int(base) - random.randint(0, span)))
            conds.append({'col': col, 'op': op, 'val': val})

    mode = random.choices(['AND', 'OR', 'KOF'], weights=[0.45, 0.30, 0.25])[0]
    k_of = None
    if mode == 'KOF':
        k_of = random.randint(1, len(conds))

    metric_type = random.choice(['var', 'std', 'mean'])

    group_candidates = ['weekday', 'project', 'device', 'app_used']
    group_col = random.choice(group_candidates)
    control_col_candidates = [c for c in num_pool if c not in targets + [cc['col'] for cc in conds]]
    if not control_col_candidates:
        control_col_candidates = [c for c in num_pool if c not in targets]
    control_col = random.choice(control_col_candidates)
    control_metric_type = random.choice(['var', 'std', 'mean'])

    night_only = random.random() < 0.5

    header: List[str] = []
    must_have = ['date', 'weekday', 'bed_time']
    header.extend(must_have)

    for nm in [group_col, control_col] + targets + [c['col'] for c in conds]:
        if nm not in header:
            header.append(nm)

    combined_pool = [x for x in num_pool + non_pool if x not in header]
    need = n_cols - len(header)
    if need > 0:
        header.extend(random.sample(combined_pool, need))
    header = header[:n_cols]

    data_rows = n_rows - 1
    missing_p = random.uniform(0.05, 0.18)

    min_good = 3
    k_good = random.randint(min_good, max(min_good, min(6, data_rows)))
    good_idx = set(random.sample(list(range(data_rows)), k_good))

    col_index: Dict[str, int] = {name: i for i, name in enumerate(header)}
    idx_t1 = col_index[targets[0]]
    idx_t2 = col_index[targets[1]]
    idx_group = col_index[group_col]
    idx_control = col_index[control_col]
    idx_bedtime = col_index['bed_time']

    gvals = _group_values(group_col)
    gA, gB = random.sample(gvals, 2)

    rows: List[List[Any]] = []
    rows.append(header[:])

    for i in range(data_rows):
        row: List[Any] = [None] * n_cols
        for j, name in enumerate(header):
            if name in _nonnumeric_pool():
                if name == 'date':
                    row[j] = _maybe_none(missing_p, _rand_date())
                elif name == 'weekday':
                    row[j] = _maybe_none(missing_p, _rand_weekday())
                elif name == 'bed_time':
                    base_t = _rand_time()
                    row[j] = _maybe_none(missing_p, base_t)
                else:
                    row[j] = _maybe_none(missing_p, random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'iOS', 'Android', 'Web', 'Mail', 'Docs', 'Chat', 'IDE', 'Browser']))
            else:
                row[j] = _maybe_none(missing_p, _gen_numeric_value(name))

        if i in good_idx:
            row[idx_t1] = _gen_numeric_value(targets[0])
            row[idx_t2] = _gen_numeric_value(targets[1])
            row[idx_control] = _gen_numeric_value(control_col)

            if night_only:
                h = random.randint(22, 23)
                m = random.randint(0, 59)
                row[idx_bedtime] = f'{h:02d}:{m:02d}'

            row[idx_group] = random.choice([gA, gB])

            if mode == 'AND':
                satisfy_set = list(range(len(conds)))
            elif mode == 'OR':
                rcount = random.randint(1, len(conds))
                satisfy_set = random.sample(list(range(len(conds))), rcount)
            else:
                rcount = random.randint(k_of, len(conds))
                satisfy_set = random.sample(list(range(len(conds))), rcount)

            for idxc in satisfy_set:
                c = conds[idxc]
                cj = col_index[c['col']]
                if c['op'] == 'range':
                    lo = float(c['lo'])
                    hi = float(c['hi'])
                    val = random.uniform(lo, hi)
                    row[cj] = val
                else:
                    op = c['op']
                    v = float(c['val'])
                    if op == '==':
                        row[cj] = v
                    elif op == '!=':
                        row[cj] = v + random.uniform(1, 5)
                    elif op == '>=':
                        row[cj] = max(v, v + random.uniform(0, 50))
                    elif op == '<=':
                        row[cj] = max(0.0, v - random.uniform(0, 50))
                    elif op == '>':
                        row[cj] = v + random.uniform(1, 50)
                    elif op == '<':
                        row[cj] = max(0.0, v - random.uniform(1, 50))
        else:
            if random.random() < 0.8:
                row[idx_group] = random.choice(gvals)
            if night_only and random.random() < 0.6:
                h = random.randint(20, 21)
                m = random.randint(0, 59)
                row[idx_bedtime] = f'{h:02d}:{m:02d}'

            if mode == 'AND':
                fail_idx = random.choice(range(len(conds)))
                c = conds[fail_idx]
                cj = col_index[c['col']]
                if c['op'] == 'range':
                    lo = float(c['lo'])
                    hi = float(c['hi'])
                    if random.random() < 0.5:
                        row[cj] = lo - random.uniform(1, 30)
                    else:
                        row[cj] = hi + random.uniform(1, 30)
                else:
                    op = c['op']
                    v = float(c.get('val', 0.0))
                    if op == '==':
                        row[cj] = v + random.uniform(1, 5)
                    elif op == '!=':
                        row[cj] = v
                    elif op == '>=':
                        row[cj] = max(0.0, v - random.uniform(5, 80))
                    elif op == '<=':
                        row[cj] = v + random.uniform(5, 80)
                    elif op == '>':
                        row[cj] = max(0.0, v - random.uniform(5, 80))
                    elif op == '<':
                        row[cj] = v + random.uniform(5, 80)
            elif mode == 'OR':
                for c in conds:
                    cj = col_index[c['col']]
                    if c['op'] == 'range':
                        lo = float(c['lo'])
                        hi = float(c['hi'])
                        if random.random() < 0.5:
                            row[cj] = lo - random.uniform(1, 30)
                        else:
                            row[cj] = hi + random.uniform(1, 30)
                    else:
                        op = c['op']
                        v = float(c.get('val', 0.0))
                        if op == '==':
                            row[cj] = v + random.uniform(1, 5)
                        elif op == '!=':
                            row[cj] = v
                        elif op == '>=':
                            row[cj] = max(0.0, v - random.uniform(5, 80))
                        elif op == '<=':
                            row[cj] = v + random.uniform(5, 80)
                        elif op == '>':
                            row[cj] = max(0.0, v - random.uniform(5, 80))
                        elif op == '<':
                            row[cj] = v + random.uniform(5, 80)
            else:
                desired = random.randint(0, max(0, k_of - 1))
                indices = list(range(len(conds)))
                pass_idx = random.sample(indices, desired) if desired > 0 else []
                for idxc in indices:
                    c = conds[idxc]
                    cj = col_index[c['col']]
                    if idxc in pass_idx:
                        if c['op'] == 'range':
                            lo = float(c['lo'])
                            hi = float(c['hi'])
                            row[cj] = random.uniform(lo, hi)
                        else:
                            op = c['op']
                            v = float(c.get('val', 0.0))
                            if op == '==':
                                row[cj] = v
                            elif op == '!=':
                                row[cj] = v + random.uniform(1, 5)
                            elif op == '>=':
                                row[cj] = v + random.uniform(0, 40)
                            elif op == '<=':
                                row[cj] = max(0.0, v - random.uniform(0, 40))
                            elif op == '>':
                                row[cj] = v + random.uniform(1, 40)
                            elif op == '<':
                                row[cj] = max(0.0, v - random.uniform(1, 40))
                    else:
                        if c['op'] == 'range':
                            lo = float(c['lo'])
                            hi = float(c['hi'])
                            if random.random() < 0.5:
                                row[cj] = lo - random.uniform(1, 30)
                            else:
                                row[cj] = hi + random.uniform(1, 30)
                        else:
                            op = c['op']
                            v = float(c.get('val', 0.0))
                            if op == '==':
                                row[cj] = v + random.uniform(1, 5)
                            elif op == '!=':
                                row[cj] = v
                            elif op == '>=':
                                row[cj] = max(0.0, v - random.uniform(5, 80))
                            elif op == '<=':
                                row[cj] = v + random.uniform(5, 80)
                            elif op == '>':
                                row[cj] = max(0.0, v - random.uniform(5, 80))
                            elif op == '<':
                                row[cj] = v + random.uniform(5, 80)

        rows.append(row)

    flat: List[Any] = []
    for r in rows:
        flat.extend(r)

    for j in range(n_cols):
        extra_count = j if random.random() < 0.5 else 0
        for _ in range(extra_count):
            if random.random() < 0.7:
                flat.append(_gen_numeric_value(header[j]) if header[j] not in _nonnumeric_pool() else random.randint(0, 999))
            else:
                flat.append(random.choice(['NA', _rand_time(), _rand_weekday()]))

    inst: Dict[str, Any] = {
        'n_rows': n_rows,
        'n_cols': n_cols,
        'flat_data': flat,
        'header': header,
        'targets': targets,
        'conds': conds,
        'comb_mode': mode,
        'k_of': k_of,
        'metric_type': metric_type,
        'group_col': group_col,
        'control_col': control_col,
        'control_metric_type': control_metric_type,
        'night_only': night_only
    }
    return inst

def _reconstruct_rows(inst: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    flat = inst['flat_data']
    n_rows = inst['n_rows']
    n_cols = inst['n_cols']
    total_needed = n_rows * n_cols
    if len(flat) < total_needed:
        return None
    rows: List[List[Any]] = []
    offset = 0
    for _ in range(n_rows):
        rows.append(flat[offset:offset + n_cols])
        offset += n_cols
    if not rows or len(rows[0]) != n_cols:
        return None
    header = rows[0]
    try:
        col_index = {str(h): i for i, h in enumerate(header)}
    except Exception:
        return None
    return {'rows': rows, 'header': header, 'col_index': col_index}

def _row_satisfies(inst: Dict[str, Any], row: List[Any], col_index: Dict[str, int]) -> bool:
    conds = inst['conds']
    mode = inst['comb_mode']
    k_of = inst.get('k_of', None)

    truth_list: List[bool] = []
    for c in conds:
        j = col_index.get(c['col'], None)
        if j is None:
            truth_list.append(False)
            continue
        v = _to_number(row[j])
        if v is None:
            truth_list.append(False)
            continue
        if c['op'] == 'range':
            ok = (v >= float(c['lo'])) and (v <= float(c['hi']))
            truth_list.append(ok)
        else:
            ok = _op_check_num(c['op'], v, float(c.get('val', 0.0)))
            truth_list.append(ok)

    if mode == 'AND':
        return all(truth_list)
    if mode == 'OR':
        return any(truth_list)
    return sum(1 for b in truth_list if b) >= int(k_of)

def compute_metric(inst: Dict[str, Any]) -> str:
    rec = _reconstruct_rows(inst)
    if rec is None:
        return '0.00'
    rows = rec['rows']
    col_index = rec['col_index']
    t1, t2 = inst['targets'][0], inst['targets'][1]
    if t1 not in col_index or t2 not in col_index:
        return '0.00'
    j1 = col_index[t1]
    j2 = col_index[t2]

    gcol = inst['group_col']
    ccol = inst['control_col']
    if gcol not in col_index or ccol not in col_index or 'bed_time' not in col_index:
        return '0.00'
    jg = col_index[gcol]
    jc = col_index[ccol]
    jt = col_index['bed_time']

    group_controls: Dict[str, List[float]] = {}
    group_t1: Dict[str, List[float]] = {}
    group_t2: Dict[str, List[float]] = {}

    for r in rows[1:]:
        if len(r) != inst['n_cols']:
            continue
        if not _row_satisfies(inst, r, col_index):
            continue
        if inst.get('night_only', False) and not _in_night(r[jt]):
            continue
        gval = r[jg]
        if gval is None:
            continue
        if isinstance(gval, str) and gval.strip() == '':
            continue
        gkey = str(gval)
        cv = _to_number(r[jc])
        if cv is not None:
            group_controls.setdefault(gkey, []).append(cv)
        v1 = _to_number(r[j1])
        v2 = _to_number(r[j2])
        if v1 is not None:
            group_t1.setdefault(gkey, []).append(v1)
        if v2 is not None:
            group_t2.setdefault(gkey, []).append(v2)

    ctrl_kind = inst['control_metric_type']
    ctrl_need = _metric_min_samples(ctrl_kind)
    ctrl_values: Dict[str, float] = {}
    for g, vals in group_controls.items():
        if len(vals) >= ctrl_need:
            mv = _metric_compute(ctrl_kind, vals)
            if mv is not None:
                ctrl_values[g] = mv

    if not ctrl_values:
        return '0.00'

    best_val = max(ctrl_values.values())
    tied = [g for g, v in ctrl_values.items() if v == best_val]
    chosen_group = sorted(tied)[0]

    metric_kind = inst['metric_type']
    need = _metric_min_samples(metric_kind)
    vals1 = group_t1.get(chosen_group, [])
    vals2 = group_t2.get(chosen_group, [])
    if len(vals1) < need or len(vals2) < need:
        return '0.00'
    m1 = _metric_compute(metric_kind, vals1)
    m2 = _metric_compute(metric_kind, vals2)
    if m1 is None or m2 is None:
        return '0.00'
    diff = abs(m1 - m2)
    return f'{diff:.2f}'

def validate_instance(inst: Dict[str, Any]) -> bool:
    rec = _reconstruct_rows(inst)
    if rec is None:
        return False
    rows = rec['rows']
    col_index = rec['col_index']

    needed = inst['targets'] + [c['col'] for c in inst['conds']] + [inst['group_col'], inst['control_col'], 'bed_time']
    for nm in needed:
        if nm not in col_index:
            return False

    t1, t2 = inst['targets'][0], inst['targets'][1]
    j1 = col_index[t1]
    j2 = col_index[t2]
    jg = col_index[inst['group_col']]
    jc = col_index[inst['control_col']]
    jt = col_index['bed_time']

    group_controls: Dict[str, List[float]] = {}
    group_t1: Dict[str, List[float]] = {}
    group_t2: Dict[str, List[float]] = {}

    for r in rows[1:]:
        if len(r) != inst['n_cols']:
            continue
        if not _row_satisfies(inst, r, col_index):
            continue
        if inst.get('night_only', False) and not _in_night(r[jt]):
            continue
        gval = r[jg]
        if gval is None:
            continue
        if isinstance(gval, str) and gval.strip() == '':
            continue
        gkey = str(gval)
        cv = _to_number(r[jc])
        if cv is not None:
            group_controls.setdefault(gkey, []).append(cv)
        v1 = _to_number(r[j1])
        v2 = _to_number(r[j2])
        if v1 is not None:
            group_t1.setdefault(gkey, []).append(v1)
        if v2 is not None:
            group_t2.setdefault(gkey, []).append(v2)

    ctrl_kind = inst['control_metric_type']
    ctrl_need = _metric_min_samples(ctrl_kind)
    ctrl_values: Dict[str, float] = {}
    for g, vals in group_controls.items():
        if len(vals) >= ctrl_need:
            mv = _metric_compute(ctrl_kind, vals)
            if mv is not None:
                ctrl_values[g] = mv

    if not ctrl_values:
        return False

    best_val = max(ctrl_values.values())
    tied = [g for g, v in ctrl_values.items() if v == best_val]
    chosen_group = sorted(tied)[0]

    metric_kind = inst['metric_type']
    need = _metric_min_samples(metric_kind)
    vals1 = group_t1.get(chosen_group, [])
    vals2 = group_t2.get(chosen_group, [])
    if len(vals1) < need or len(vals2) < need:
        return False

    m1 = _metric_compute(metric_kind, vals1)
    m2 = _metric_compute(metric_kind, vals2)
    return m1 is not None and m2 is not None

def unique_answer_ok(inst: Dict[str, Any]) -> bool:
    """
    确认答案在题面规则下具有唯一性（以最终两位小数口径为准）：
    - 找到控制度量最大值的所有并列分组；
    - 对满足目标统计量样本门槛的并列分组，计算两列目标度量差值，四舍五入到两位小数（字符串格式）；
    - 若这些两位小数字符串不一致，则返回 False。
    """
    rec = _reconstruct_rows(inst)
    if rec is None:
        return False
    rows = rec['rows']
    col_index = rec['col_index']
    if 'bed_time' not in col_index:
        return False

    t1, t2 = inst['targets'][0], inst['targets'][1]
    gcol, ccol = inst['group_col'], inst['control_col']
    if any(k not in col_index for k in [t1, t2, gcol, ccol]):
        return False

    j1 = col_index[t1]
    j2 = col_index[t2]
    jg = col_index[gcol]
    jc = col_index[ccol]
    jt = col_index['bed_time']

    group_controls: Dict[str, List[float]] = {}
    group_t1: Dict[str, List[float]] = {}
    group_t2: Dict[str, List[float]] = {}

    for r in rows[1:]:
        if len(r) != inst['n_cols']:
            continue
        if not _row_satisfies(inst, r, col_index):
            continue
        if inst.get('night_only', False) and not _in_night(r[jt]):
            continue
        gval = r[jg]
        if gval is None:
            continue
        if isinstance(gval, str) and gval.strip() == '':
            continue
        gkey = str(gval)
        cv = _to_number(r[jc])
        if cv is not None:
            group_controls.setdefault(gkey, []).append(cv)
        v1 = _to_number(r[j1])
        v2 = _to_number(r[j2])
        if v1 is not None:
            group_t1.setdefault(gkey, []).append(v1)
        if v2 is not None:
            group_t2.setdefault(gkey, []).append(v2)

    ctrl_kind = inst['control_metric_type']
    ctrl_need = _metric_min_samples(ctrl_kind)
    ctrl_values: Dict[str, float] = {}
    for g, vals in group_controls.items():
        if len(vals) >= ctrl_need:
            mv = _metric_compute(ctrl_kind, vals)
            if mv is not None:
                ctrl_values[g] = mv
    if not ctrl_values:
        return False

    best_val = max(ctrl_values.values())
    tied = [g for g, v in ctrl_values.items() if v == best_val]
    metric_kind = inst['metric_type']
    need = _metric_min_samples(metric_kind)

    # 当前答案（两位小数口径）
    ans_str = compute_metric(inst)
    if not isinstance(ans_str, str):
        return False

    rounded_diffs: List[str] = []
    for g in tied:
        vals1 = group_t1.get(g, [])
        vals2 = group_t2.get(g, [])
        if len(vals1) < need or len(vals2) < need:
            continue
        m1 = _metric_compute(metric_kind, vals1)
        m2 = _metric_compute(metric_kind, vals2)
        if m1 is None or m2 is None:
            continue
        s = f'{abs(m1 - m2):.2f}'
        rounded_diffs.append(s)

    if not rounded_diffs:
        # 并列分组均不达标或无可比较差值，答案由题面字典序破局规则唯一确定
        return True

    # 所有可比较的并列分组差值（两位小数）需一致，否则唯一性不足
    return all(s == ans_str for s in rounded_diffs)

def answer_format_ok(ans: Any) -> bool:
    """
    Enforce that the final answer is a string with exactly two decimal digits, e.g., '0.00'.
    """
    if not isinstance(ans, str):
        return False
    return re.fullmatch(r'\d+\.\d{2}', ans) is not None