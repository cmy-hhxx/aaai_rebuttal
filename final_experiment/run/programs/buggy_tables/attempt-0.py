import sys, json, math, re, statistics
from typing import Any, Dict, List, Optional, Tuple
import random

# ----------------------------
# Utilities
# ----------------------------

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def fmt2(x: float) -> str:
    # Always show two decimals, avoid -0.00
    if abs(x) < 0.0005:
        x = 0.0
    return f"{x:.2f}"

def is_null_token(tok: str) -> bool:
    t = tok.strip()
    return t == "" or t.lower() in {"null", "none", "nan", "na", "n/a", "nil"}

_num_re = re.compile(r"""^[\+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][\+\-]?\d+)?$""")

def parse_number(tok: str) -> Optional[float]:
    t = tok.strip()
    if is_null_token(t):
        return None
    if _num_re.match(t):
        try:
            return float(t)
        except Exception:
            return None
    return None

_time_re = re.compile(r"^(\d{1,2}):(\d{2})$")

def parse_bed_time(tok: str) -> Optional[str]:
    t = tok.strip()
    if is_null_token(t):
        return None
    m = _time_re.match(t)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    if 0 <= hh <= 23 and 0 <= mm <= 59:
        return f"{hh:02d}:{mm:02d}"
    return None

_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def parse_date(tok: str) -> Optional[str]:
    t = tok.strip()
    if is_null_token(t):
        return None
    if _date_re.match(t):
        return t
    return None

def parse_weekday(tok: str) -> Optional[str]:
    t = tok.strip()
    if is_null_token(t):
        return None
    if t in WEEKDAYS:
        return t
    return None

def split_tokens_from_row_major_string(s: str) -> List[str]:
    # Extract inside [...] if present
    ss = s.strip()
    lb = ss.find('[')
    rb = ss.rfind(']')
    if lb != -1 and rb != -1 and rb > lb:
        ss = ss[lb+1:rb]
    # Split by commas. Seed-like data doesn't contain commas inside tokens.
    tokens = [t.strip() for t in ss.split(',')]
    # Remove possible enclosing quotes
    cleaned = []
    for t in tokens:
        tt = t.strip()
        if len(tt) >= 2 and ((tt[0] == tt[-1] == '"') or (tt[0] == tt[-1] == "'")):
            tt = tt[1:-1]
        cleaned.append(tt.strip())
    # Drop trailing empties caused by formatting
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned

def sample_variance(values: List[float]) -> Optional[float]:
    # Sample variance (n-1). Return None if cannot compute.
    vals = [v for v in values if v is not None and isinstance(v, (int, float)) and math.isfinite(v)]
    if len(vals) <= 1:
        return None
    try:
        return statistics.variance(vals)
    except Exception:
        return None

# ----------------------------
# Table synthesis
# ----------------------------

COLUMNS = [
    "date",
    "num_steps",
    "study_minutes",
    "exercise_minutes",
    "sleep_minutes",
    "bed_time",
    "num_messages",
    "num_emails",
    "num_calls",
    "calories_burned",
    "weekday",
    "calories_consumed",
    "num_meetings",
    "coding_minutes",
    "num_tasks_completed",
    "water_intake_ml",
    "phone_screen_time_minutes",
    "music_listening_minutes",
]

COL_INDEX = {name: i for i, name in enumerate(COLUMNS)}

def make_row(rng: random.Random, date_str: str) -> List[Any]:
    # Generate a plausible record, allowing some nulls
    def maybe_null(p: float, val):
        return None if rng.random() < p else val

    num_steps = maybe_null(0.05, float(rng.randint(0, 25000)))
    study = maybe_null(0.07, float(rng.randint(0, 360)))
    exercise = maybe_null(0.07, float(rng.randint(0, 120)))
    sleep = maybe_null(0.05, float(rng.randint(240, 600)))  # 4-10h in minutes
    hh = rng.randint(20, 23)
    mm = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    bed_time = maybe_null(0.05, f"{hh:02d}:{mm:02d}")
    msgs = maybe_null(0.06, float(rng.randint(0, 200)))
    emails = maybe_null(0.06, float(rng.randint(0, 60)))
    calls = maybe_null(0.06, float(rng.randint(0, 20)))
    cal_burn = maybe_null(0.05, float(rng.randint(1200, 3800)))
    weekday = maybe_null(0.0, rng.choice(WEEKDAYS))
    cal_cons = maybe_null(0.05, float(rng.randint(1200, 3200)))
    meetings = maybe_null(0.07, float(rng.randint(0, 10)))
    coding = maybe_null(0.07, float(rng.randint(0, 480)))
    tasks = maybe_null(0.06, float(rng.randint(0, 25)))
    water = maybe_null(0.06, float(rng.randint(0, 3500)))
    screen = maybe_null(0.06, float(rng.randint(0, 360)))
    music = maybe_null(0.06, float(rng.randint(0, 300)))

    return [
        date_str, num_steps, study, exercise, sleep, bed_time,
        msgs, emails, calls, cal_burn, weekday, cal_cons,
        meetings, coding, tasks, water, screen, music
    ]

def random_date(rng: random.Random) -> str:
    # 2024-12-01 .. 2026-12-28
    year = rng.choice([2024, 2025, 2026])
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"

def render_value(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, str):
        return v
    # numeric
    # sometimes integer-ish floats; render with one decimal sometimes to mimic seed
    if abs(v - round(v)) < 1e-9:
        # show as x.0
        return f"{int(round(v))}.0"
    return f"{v:.2f}"

def build_row_major_with_defect(rng: random.Random, rows: List[List[Any]]) -> Tuple[str, List[str], int]:
    """
    Returns:
      - a single row-major list rendered as string with defect applied
      - tokens list
      - nrows (including header)
    Defect: for each column j (0-index), append j extra random values at bottom of that column,
    i.e., after normal data, column streams have extra tail. In row-major flattening, we simulate
    by taking per-column lists with tails, then interleaving row-major until exhaustion.
    """
    header = COLUMNS[:]
    n_data = len(rows)
    # Build per-column arrays: header + data + tail
    per_col = []
    for j, col in enumerate(COLUMNS):
        col_vals = [header[j]]
        for r in range(n_data):
            col_vals.append(rows[r][j])
        # tail random values (j of them)
        tail = []
        for _ in range(j):
            # random value type depends on column
            if col == "date":
                tail.append(random_date(rng))
            elif col == "bed_time":
                hh = rng.randint(0, 23); mm = rng.randint(0, 59)
                tail.append(f"{hh:02d}:{mm:02d}")
            elif col == "weekday":
                tail.append(rng.choice(WEEKDAYS))
            else:
                # numeric random float-ish
                base = rng.random() * 4000
                if col in {"num_calls", "num_emails", "num_messages", "num_meetings", "num_tasks_completed"}:
                    base = rng.randint(0, 200) + rng.random()
                tail.append(float(base))
        col_vals.extend(tail)
        per_col.append(col_vals)

    # Now interleave as if stored row-major but underlying got corrupted by appending per-column tails.
    # Construct rows by pulling next value from each column if available; stop when no column has more.
    max_len = max(len(c) for c in per_col)
    tokens = []
    for i in range(max_len):
        for j in range(len(COLUMNS)):
            if i < len(per_col[j]):
                tokens.append(render_value(per_col[j][i]))
            else:
                # missing -> nothing appended (ragged)
                pass

    rendered = "[" + ", ".join(tokens) + "]"
    return rendered, tokens, max_len  # max_len approximates max "row count" across columns

# ----------------------------
# Parsing from row-major corrupted stream
# ----------------------------

def parse_table_from_tokens(tokens: List[str], ncols: int) -> List[List[Any]]:
    """
    Parse only complete rows from the front (row-major). Remaining tokens are garbage.
    We attempt to interpret each cell based on header name.
    """
    if len(tokens) < ncols:
        return []
    header = tokens[:ncols]
    # Ensure header matches expected; if not, still proceed using expected header mapping.
    # Rows start after header.
    data_tokens = tokens[ncols:]
    n_full_rows = len(data_tokens) // ncols
    rows = []
    for r in range(n_full_rows):
        row_tok = data_tokens[r*ncols:(r+1)*ncols]
        row = [None]*ncols
        for j, col in enumerate(COLUMNS):
            t = row_tok[j]
            if col == "date":
                row[j] = parse_date(t)
            elif col == "bed_time":
                row[j] = parse_bed_time(t)
            elif col == "weekday":
                row[j] = parse_weekday(t)
            else:
                row[j] = parse_number(t)
        rows.append(row)
    return rows

def compute_answer_from_rows(rows: List[List[Any]]) -> Tuple[str, str]:
    """
    variance(sleep_minutes) and variance(num_calls) over all valid numeric values.
    Then consider records with (num_tasks_completed > 3) and (num_emails != 3),
    ignoring nulls; unverifiable => condition false.
    For those records, compute abs(var_sleep - var_calls). (Same variances for all records,
    but keep semantics.) If either variance cannot be computed => 0.00
    """
    sleep_vals = [r[COL_INDEX["sleep_minutes"]] for r in rows]
    calls_vals = [r[COL_INDEX["num_calls"]] for r in rows]
    var_sleep = sample_variance([v for v in sleep_vals if isinstance(v, (int, float, float)) and v is not None])
    var_calls = sample_variance([v for v in calls_vals if isinstance(v, (int, float, float)) and v is not None])

    if var_sleep is None or var_calls is None:
        return "0.00", "由于 sleep_minutes 或 num_calls 的方差无法计算（有效值不足 2 个），按规则答案为 0.00。"

    # Filter rows by conditions
    selected = []
    for r in rows:
        tasks = r[COL_INDEX["num_tasks_completed"]]
        emails = r[COL_INDEX["num_emails"]]
        ok = True
        # tasks > 3
        if not (isinstance(tasks, (int, float)) and tasks is not None):
            ok = False
        else:
            ok = ok and (tasks > 3)
        # emails != 3
        if not (isinstance(emails, (int, float)) and emails is not None):
            ok = False
        else:
            ok = ok and (emails != 3)
        if ok:
            selected.append(r)

    diff = abs(var_sleep - var_calls)
    expl = []
    expl.append(f"从可解析的完整行中提取 sleep_minutes 与 num_calls 的数值（忽略空值）计算样本方差：")
    expl.append(f"var(sleep_minutes) = {fmt2(var_sleep)}，var(num_calls) = {fmt2(var_calls)}。")
    expl.append("再筛选满足 num_tasks_completed > 3 且 num_emails != 3 的记录（任一条件无法验证则视为不满足）。")
    expl.append(f"筛选到 {len(selected)} 条记录；所求为两方差的绝对差：|{fmt2(var_sleep)} - {fmt2(var_calls)}| = {fmt2(diff)}。")
    return fmt2(diff), "\n".join(expl)

# ----------------------------
# Problem generator families
# ----------------------------

def make_problem_instance(rng: random.Random, family: int) -> Dict[str, Any]:
    # Choose size and slight variations while keeping core skill: parse corrupted row-major table + variance + filtering
    n_data_rows = rng.randint(5, 9)  # data rows count; header adds 1
    # Build clean rows
    dates = set()
    rows = []
    while len(rows) < n_data_rows:
        d = random_date(rng)
        if d in dates:
            continue
        dates.add(d)
        rows.append(make_row(rng, d))

    rendered, tokens, max_len = build_row_major_with_defect(rng, rows)
    parsed_rows = parse_table_from_tokens(tokens, len(COLUMNS))

    # Ensure there are at least 2 valid values for both columns most of the time; else allow (answer 0.00) sometimes
    ans, expl = compute_answer_from_rows(parsed_rows)

    # Family variations: different wording / rounding instruction / mention sample variance
    if family == 0:
        prompt = (
            f"我有一个表格，按行主序存成一个列表，共 {n_data_rows+1} 行（含表头）与 {len(COLUMNS)} 列。\n"
            f"列表内容为：\n{rendered}。\n"
            "但保存机制有缺陷：对于每一列 j（0 索引），在该列底部额外追加了 j 个随机值，导致末尾出现噪声。\n"
            "请你只依据能解析出的完整行数据（多出来的尾部噪声应忽略），计算列 sleep_minutes 与列 num_calls 的样本方差（variance）。\n"
            "然后在满足 num_tasks_completed > 3 且 num_emails != 3 的记录上，计算两方差的绝对差。\n"
            "忽略空值；任一筛选条件无法验证则视为不满足。结果四舍五入到 2 位小数，并始终显示两位小数。\n"
            "如果任一方差由于有效值为 0 或 1 个而无法计算，则最终答案输出 \"0.00\"。"
        )
    elif family == 1:
        prompt = (
            f"下面是一个按行主序展开的表格列表（{len(COLUMNS)} 列，表头在第一行）。\n"
            f"{rendered}\n"
            "已知写入时发生列尾追加错误：第 j 列（从 0 开始）在末尾被额外追加了 j 个随机单元格。\n"
            "任务：\n"
            "1) 用所有可用的 sleep_minutes 数值计算其样本方差；用所有可用的 num_calls 数值计算其样本方差（均忽略空值）。\n"
            "2) 仅对满足 num_tasks_completed > 3 且 num_emails ≠ 3 的行（无法判断则不选）计算 |var_sleep - var_calls|。\n"
            "输出保留 2 位小数（四舍五入，且必须显示两位）。若任一方差不可计算则输出 0.00。"
        )
    else:
        prompt = (
            f"给定一个行为主序的扁平列表，表示一个 {len(COLUMNS)} 列的日志表（第一行是列名）。数据如下：\n"
            f"{rendered}\n"
            "由于存储缺陷：对每列 j(0 起)，在列底部附加了 j 个随机值，因此列表末尾混入额外噪声。\n"
            "请忽略这部分噪声（只使用能组成完整行的部分），并：\n"
            "计算 sleep_minutes 与 num_calls 的样本方差；再对满足 num_tasks_completed > 3 且 num_emails != 3 的记录求两方差的绝对差。\n"
            "空值忽略；条件无法核实视为不满足。若任何一个方差因样本量不足无法计算，答案为 0.00。结果保留两位小数。"
        )

    return {"problem": prompt, "answer": ans, "explanation": expl}

def generate_unique(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    items = []
    seen = set()
    attempts = 0
    while len(items) < count and attempts < count * 50:
        attempts += 1
        family = rng.randint(0, 2)
        inst = make_problem_instance(rng, family)
        key = inst["problem"]
        if key in seen:
            continue
        seen.add(key)
        items.append(inst)
    if len(items) < count:
        raise RuntimeError(f"生成失败：仅生成 {len(items)} / {count} 道不重复题目。")
    return items

# ----------------------------
# Main
# ----------------------------

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"输入不是合法 JSON：{e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    out = generate_unique(rng, count)
    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()