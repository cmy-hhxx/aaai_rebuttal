# -*- coding: utf-8 -*-
"""
buggy_tables_0.py

改进版（高质量题面与可核验数据）：
- 提供完整扁平数据（表头 + 记录 + 尾部噪声），并提供示例演示重建逻辑；
- 明确空值、解析、筛选顺序、方差口径与四舍五入规则（使用 Decimal HALF_UP）；
- 采用逆向生成：先确保筛选集合可计算（>=2），再注入尾部噪声（列 j 追加 j×scale 值）。
"""

import random
from typing import List, Any, Optional, Dict
from decimal import Decimal, ROUND_HALF_UP

# 必需列
REQUIRED_COLS = [
    "sleep_minutes",
    "num_calls",
    "num_tasks_completed",
    "num_emails",
]

# 可选列池
OPTIONAL_POOL = [
    "date", "num_steps", "study_minutes", "exercise_minutes", "bed_time",
    "num_messages", "calories_burned", "weekday", "calories_consumed",
    "num_meetings", "coding_minutes", "water_intake_ml",
    "phone_screen_time_minutes", "music_listening_minutes",
    "metric_x", "metric_y", "metric_z", "score_p", "score_q",
    "col_a", "col_b", "col_c", "col_d", "col_e", "col_f"
]

# 空值标记集合（明确不包含“,”；仅当单元格内容恰为这些独立标记时才视为空）
NULL_TOKENS = {"", "NA", "NaN", None, "null", "NULL", "tbd", "x"}

# 自然语言模板
DESC_TEMPLATES = [
    "一个行主序扁平表（含表头）存在缺陷：列 j（0 基）会在列底部追加 j×scale 个随机值。请在满足给定约束的记录集合上，忽略空值，计算 sleep_minutes 与 num_calls 的总体方差差的绝对值；若任一不可计算则输出 0.00。",
    "考虑行主序存储（含表头）的数据，由于缺陷，列 j 的末尾插入了 j×scale 噪声。请按约束筛选记录，忽略空值，计算两列总体方差差的绝对值；不可计算返回 0.00。",
    "给定扁平化列表（行主序，带表头与尾部噪声），满足约束的记录上，忽略空值，计算 sleep_minutes 与 num_calls 的总体方差差绝对值；若任一不可计算，答案为 0.00。"
]
QUERY_TEMPLATES = [
    "请输出结果（四舍五入到 2 位并固定两位展示）。",
    "请给出计算结果（两位小数显示）。",
    "结果请以两位小数给出。"
]
OP_TEXT = {
    "gt": "大于",
    "ge": "大于等于",
    "lt": "小于",
    "le": "小于等于",
    "eq": "等于",
    "neq": "不等于",
}


def gen_headers(col_num: int) -> List[str]:
    """生成列名（包含必需列并随机补充与打乱）。"""
    if col_num < len(REQUIRED_COLS):
        col_num = len(REQUIRED_COLS)
    headers = REQUIRED_COLS.copy()
    optional = OPTIONAL_POOL.copy()
    random.shuffle(optional)
    headers.extend(optional[: col_num - len(headers)])
    random.shuffle(headers)
    return headers


def headers_mapping(headers: List[str]) -> str:
    """列名索引映射文本。"""
    return ", ".join([f"{i}:{name}" for i, name in enumerate(headers)])


def noise_rule_text(tail_scale: int, headers: List[str]) -> str:
    """
    噪声注入与重建规则说明：
    - 注入：对每列 j 在列底部追加 j×tail_scale 个随机值（顺序：列 0 → 列 1 → … → 列 n-1）
    - 重建：n=len(headers), L=扁平列表长度, sum_noise=tail_scale*n*(n-1)/2，
            base_rows=(L - n - sum_noise) // n，仅使用表头后的前 base_rows 行；表头不参与计算。
    """
    n = len(headers)
    return (
        f"缺陷注入：每列 j（0 基）追加 j×{tail_scale} 个随机值，顺序为列 0→列 1→…→列 {n-1}。"
        f" 重建：设 n={n}，L 为扁平列表总长度，sum_noise={tail_scale}×n×(n-1)/2，"
        f"base_rows=(L - n - sum_noise) // n，仅使用表头后的前 base_rows 行，丢弃列尾噪声；表头不参与计算。"
    )


def filter_rule_text() -> str:
    """筛选流程说明。"""
    return (
        "先在所有约束列上过滤记录：若某约束列为空或不可解析，则视为不满足该约束。"
        "过滤完成后，在剩余记录中分别对目标两列（sleep_minutes 与 num_calls）忽略空值并计算总体方差；"
        "若任一方差因无值或仅一个值而不可计算，则返回 0.00。"
    )


def parse_rule_text() -> str:
    """数值解析与错误处理说明。"""
    return (
        "数值解析采用浮点转换（float）；若单元格内容恰为空值标记（如 '', 'NA', 'NaN', 'None', 'null', 'NULL', 'tbd', 'x'）"
        "或无法解析为数值，则视为缺失值（空），不参与方差。最终结果用十进制四舍五入到两位（HALF_UP），保证标准四舍五入。"
    )


def _is_numeric_column(col_name: str) -> bool:
    """简单判定：非日期/时间/星期视为数值列。"""
    return col_name not in ("date", "bed_time", "weekday")


def gen_constraints(n_constraints: int,
                    operator_pool: List[str],
                    headers: List[str],
                    num_low: int,
                    num_high: int) -> Dict[str, Any]:
    """生成约束配置与人类可读文本。"""
    for req in REQUIRED_COLS:
        if req not in headers:
            headers.insert(0, req)

    def sample_op() -> str:
        return random.choice(operator_pool) if operator_pool else "gt"

    def sample_val() -> float:
        lo = min(num_low, num_high)
        hi = max(num_low, num_high)
        return round(random.uniform(lo, hi), 2)

    configs: List[Dict[str, Any]] = []
    texts: List[str] = []

    base_cols = ["num_tasks_completed", "num_emails"]
    for bc in base_cols:
        op = sample_op()
        val = sample_val()
        configs.append({"col": bc, "op": op, "val": val})
        texts.append(f"{bc} {OP_TEXT.get(op, op)} {val}")

    numeric_headers = [h for h in headers if _is_numeric_column(h)]
    random.shuffle(numeric_headers)
    extra_candidates = [h for h in numeric_headers if h not in base_cols]

    need_extra = max(0, n_constraints - len(configs))
    for _ in range(need_extra):
        col = extra_candidates.pop(0) if extra_candidates else random.choice(numeric_headers)
        op = sample_op()
        val = sample_val()
        configs.append({"col": col, "op": op, "val": val})
        texts.append(f"{col} {OP_TEXT.get(op, op)} {val}")

    return {"configs": configs, "texts": texts}


def _to_float(x: Any) -> Optional[float]:
    """安全转换为 float；空值标记返回 None。"""
    if x in NULL_TOKENS:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except:
            return None
    return None


def _variance(values: List[float]) -> Optional[float]:
    """总体方差（n>=2），否则返回 None。"""
    n = len(values)
    if n < 2:
        return None
    mu = sum(values) / n
    ssd = sum((v - mu) ** 2 for v in values)
    return ssd / n


def _build_record(headers: List[str], num_low: int, num_high: int, inject_null_prob: float = 0.05) -> List[Any]:
    """随机生成一条记录。"""
    rec: List[Any] = []
    lo = min(num_low, num_high)
    hi = max(num_low, num_high)

    for name in headers:
        if name == "date":
            y = random.randint(2000, 2035)
            m = random.randint(1, 12)
            d = random.randint(1, 28)
            rec.append(f"{y:04d}-{m:02d}-{d:02d}")
        elif name == "bed_time":
            hh = random.randint(20, 23)
            mm = random.randint(0, 59)
            rec.append(f"{hh:02d}:{mm:02d}")
        elif name == "weekday":
            rec.append(random.choice(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]))
        else:
            # 数值列：可少量注入空值（非必需列）
            if random.random() < inject_null_prob and name not in REQUIRED_COLS:
                rec.append(random.choice(list(NULL_TOKENS)))
            else:
                rec.append(round(random.uniform(lo, hi), 2))
    return rec


def _make_satisfying_value(op: str, pivot: float, lo: float, hi: float) -> float:
    """生成满足 op 的数值。"""
    eps = 1e-6
    if op == "gt":
        return round(random.uniform(max(pivot + eps, lo), hi), 2)
    if op == "ge":
        return round(random.uniform(max(pivot, lo), hi), 2)
    if op == "lt":
        return round(random.uniform(lo, min(pivot - eps, hi)), 2)
    if op == "le":
        return round(random.uniform(lo, min(pivot, hi)), 2)
    if op == "eq":
        return round(min(max(pivot, lo), hi), 2)
    if op == "neq":
        cand = round(random.uniform(lo, hi), 2)
        if abs(cand - pivot) < 1e-9:
            cand = round(pivot + 1.0, 2) if pivot + 1.0 <= hi else round(pivot - 1.0, 2)
        return cand
    return round(random.uniform(max(pivot + eps, lo), hi), 2)


def gen_flattened_data(row_num: int,
                       col_num: int,
                       headers: List[str],
                       tail_scale: int,
                       min_filter_count: int,
                       num_low: int,
                       num_high: int,
                       constraints_config: List[Dict[str, Any]]) -> List[Any]:
    """
    生成完整扁平列表数据：
    - 先生成 >= min_filter_count 条满足所有约束的记录（目标两列保证可解析）；
    - 再补充随机记录直至 row_num-1 条；
    - 扁平化与尾部噪声注入（每列 j 追加 j×tail_scale）。
    """
    for req in REQUIRED_COLS:
        if req not in headers:
            headers.insert(0, req)

    n_cols = len(headers)
    col_num = max(col_num, n_cols)
    headers = headers[:col_num]
    n_cols = len(headers)
    idx_map = {h: i for i, h in enumerate(headers)}
    if not all(h in idx_map for h in REQUIRED_COLS):
        for req in REQUIRED_COLS:
            if req not in idx_map:
                headers.append(req)
        n_cols = len(headers)
        idx_map = {h: i for i, h in enumerate(headers)}

    idx_sleep = idx_map["sleep_minutes"]
    idx_calls = idx_map["num_calls"]
    lo = min(num_low, num_high)
    hi = max(num_low, num_high)

    # 满足约束的记录
    satisfying_rows: List[List[Any]] = []
    for _ in range(min_filter_count):
        rec = _build_record(headers, num_low, num_high, inject_null_prob=0.0)
        rec[idx_sleep] = round(random.uniform(lo, hi), 2)
        rec[idx_calls] = round(random.uniform(lo, hi), 2)
        for cfg in constraints_config:
            col = cfg.get("col")
            op = str(cfg.get("op"))
            pivot = float(cfg.get("val"))
            idx = idx_map.get(col)
            if idx is None:
                continue
            rec[idx] = _make_satisfying_value(op, pivot, lo, hi)
        satisfying_rows.append(rec)

    # 补充随机记录
    total_needed = max(row_num - 1, min_filter_count)
    other_rows: List[List[Any]] = []
    for _ in range(total_needed - len(satisfying_rows)):
        rec = _build_record(headers, num_low, num_high, inject_null_prob=0.08)
        rec[idx_sleep] = round(random.uniform(lo, hi), 2)
        rec[idx_calls] = round(random.uniform(lo, hi), 2)
        other_rows.append(rec)

    # 扁平化
    flattened: List[Any] = []
    flattened.extend(headers)
    for rec in (satisfying_rows + other_rows):
        flattened.extend(rec)

    # 尾部噪声：每列 j 追加 j×tail_scale 个值（大多数为数值、少量空值）
    for j in range(n_cols):
        tail_n = j * max(1, int(tail_scale))
        for _ in range(tail_n):
            if random.random() < 0.1:
                flattened.append(random.choice(list(NULL_TOKENS)))
            else:
                flattened.append(round(random.uniform(lo, hi), 2))
    return flattened


def _eval_constraint(val: Optional[float], op: str, pivot: float) -> bool:
    """对单一值评估比较约束。"""
    if val is None:
        return False
    if op == "gt":
        return val > pivot
    if op == "ge":
        return val >= pivot
    if op == "lt":
        return val < pivot
    if op == "le":
        return val <= pivot
    if op == "eq":
        return abs(val - pivot) < 1e-9
    if op == "neq":
        return abs(val - pivot) >= 1e-9
    return False


def compute_variance_diff(flattened_data: List[Any],
                          headers: List[str],
                          constraints_config: List[Dict[str, Any]],
                          tail_scale: int) -> float:
    """
    计算：在满足约束的记录集合上，sleep_minutes 与 num_calls 的总体方差差的绝对值。
    重建（对齐）步骤：
    - n = len(headers)，L = len(flattened_data)
    - sum_noise = tail_scale * n * (n-1) / 2
    - base_rows = (L - n - sum_noise) // n
    - 表头不参与，数据块为 flattened_data[n : n + base_rows*n]
    - 先按 constraints_config 过滤（缺失或不可解析视为不满足），再对目标两列忽略空值计算总体方差
    """
    if not isinstance(flattened_data, list) or not isinstance(headers, list):
        return 0.0
    n = len(headers)
    if n < 1 or len(flattened_data) < n:
        return 0.0

    L = len(flattened_data)
    sum_noise = tail_scale * n * (n - 1) // 2
    rem = L - n - sum_noise
    if rem < 0:
        return 0.0
    base_rows = rem // n
    if base_rows <= 0 or n + base_rows * n > L:
        return 0.0

    data_block = flattened_data[n: n + base_rows * n]

    idx_map = {h: i for i, h in enumerate(headers)}
    for req in REQUIRED_COLS:
        if req not in idx_map:
            return 0.0

    idx_sleep = idx_map["sleep_minutes"]
    idx_calls = idx_map["num_calls"]

    sleep_vals: List[float] = []
    calls_vals: List[float] = []

    for r in range(base_rows):
        row = data_block[r * n: (r + 1) * n]

        # 先按约束过滤
        ok = True
        for cfg in constraints_config:
            col = str(cfg.get("col"))
            op = str(cfg.get("op"))
            pivot = float(cfg.get("val"))
            cidx = idx_map.get(col)
            val = _to_float(row[cidx]) if cidx is not None else None
            if not _eval_constraint(val, op, pivot):
                ok = False
                break
        if not ok:
            continue

        # 再对目标两列忽略空值
        v_sleep = _to_float(row[idx_sleep])
        v_calls = _to_float(row[idx_calls])
        if v_sleep is None or v_calls is None:
            continue

        sleep_vals.append(v_sleep)
        calls_vals.append(v_calls)

    var_sleep = _variance(sleep_vals)
    var_calls = _variance(calls_vals)
    if var_sleep is None or var_calls is None:
        return 0.0
    return abs(var_sleep - var_calls)


def to_fixed_2(x: float) -> str:
    """两位小数四舍五入（十进制 HALF_UP，避免银行家舍入）。"""
    try:
        return str(Decimal(str(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        return "0.00"


def render_desc(headers: List[str], constraints_desc: str, tail_scale: int) -> str:
    """多模板题面描述。"""
    base = random.choice(DESC_TEMPLATES)
    return f"{base}（当前 scale={tail_scale}，列数={len(headers)}。）"


def render_query_desc() -> str:
    """多模板查询文本。"""
    return random.choice(QUERY_TEMPLATES)


def display_flattened(flattened_data: List[Any]) -> str:
    """将完整扁平列表转换为可读文本（用逗号分隔，保留引号/数值原貌）。"""
    return "[" + ", ".join(repr(v) for v in flattened_data) + "]"


def gen_toy_demo(tail_scale: int) -> Dict[str, Any]:
    """
    小型示例：演示“列 j 末尾插入 j×scale 噪声”的注入与重建。
    - 取 5 列（包含必需列），3 条数据记录；
    - 扁平化后按规则追加噪声，并给出 base_rows 推导。
    """
    headers = ["sleep_minutes", "num_calls", "num_tasks_completed", "num_emails", "col_a"]
    n = len(headers)
    # 三条简明记录
    rows = [
        [100.0, 10.0, 5.0, 4.0, 1.0],
        [120.0, 12.0, 6.0, 5.0, 2.0],
        [140.0, 14.0, 7.0, 6.0, 3.0],
    ]
    flat = []
    flat.extend(headers)
    for r in rows:
        flat.extend(r)
    # 追加噪声：每列 j 追加 j×tail_scale 个随机数（为示例清晰，使用固定序列值 j*100+k）
    sum_noise = 0
    for j in range(n):
        tail_n = j * max(1, int(tail_scale))
        sum_noise += tail_n
        for k in range(tail_n):
            flat.append(float(j * 100 + k + 1))
    L = len(flat)
    base_rows = (L - n - sum_noise) // n
    text = (
        f"示例：n={n} 列，原始数据行数=3。按规则在列 j 末追加 j×scale（scale={tail_scale}) 个噪声，总噪声个数 sum_noise={sum_noise}。"
        f" 扁平总长度 L={L}。重建 base_rows=(L - n - sum_noise)//n = {base_rows}（仅用表头后的前 {base_rows} 行）。"
    )
    return {"headers": headers, "flat": flat, "text": text}