# dyck_language_errors_0.py
# ================================================================
# Bracket Puzzle Toolkit (v4) – choose_task 固定为 pos_type
# ================================================================
from typing import List, Dict, Any
import random, time

ALL_BRACKETS = ['()', '[]', '{}', '<>']

# ---------- 基础映射与解析（同 v3） ----------
def _build_maps(bracket_types: List[str]):
    open_to_close = {p[0]: p[1] for p in bracket_types}
    close_to_open = {p[1]: p[0] for p in bracket_types}
    opening = set(open_to_close.keys())
    closing = set(close_to_open.keys())
    return open_to_close, close_to_open, opening, closing

def _first_error_position(seq: str, maps) -> int:
    open_to_close, close_to_open, opening, closing = maps
    stack: List[str] = []
    for idx, ch in enumerate(seq, 1):
        if ch in opening:
            stack.append(ch)
        elif ch in closing:
            if not stack or stack[-1] != close_to_open[ch]:
                return idx
            stack.pop()
        else:
            return idx
    return len(seq) + 1 if stack else -1

def _error_type(seq: str, maps) -> int:
    open_to_close, close_to_open, opening, closing = maps
    stack: List[str] = []
    for ch in seq:
        if ch in opening:
            stack.append(ch)
        elif ch in closing:
            if not stack:
                return 2
            if stack[-1] != close_to_open[ch]:
                return 1
            stack.pop()
    return 3 if stack else 0

def _nested_depth(seq: str, maps) -> int:
    _, _, opening, closing = maps
    depth = max_depth = 0
    for ch in seq:
        if ch in opening:
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch in closing:
            depth -= 1
    return max_depth

# ---------- 序列生成与错误注入（同 v3） ----------
def _generate_balanced(n: int, maps) -> str:
    open_to_close, _, opening, _ = maps
    seq, stack = [], []
    remaining = n
    while remaining:
        if not stack or (random.random() < 0.55 and remaining > len(stack)):
            ch_open = random.choice(list(opening))
            seq.append(ch_open)
            stack.append(ch_open)
        else:
            ch_open = stack.pop()
            seq.append(open_to_close[ch_open])
        remaining -= 1
    return ''.join(seq)

def _introduce_error(seq: str, maps) -> str:
    _, close_to_open, opening, closing = maps
    method = random.choice(['mismatch', 'extra_closing', 'missing_closing'])
    s = list(seq)
    if method == 'mismatch':
        rights = [i for i, ch in enumerate(s) if ch in closing]
        if not rights:
            return _introduce_error(seq, maps)
        idx = random.choice(rights)
        s[idx] = random.choice(list(closing - {s[idx]}))
    elif method == 'extra_closing':
        s.insert(random.randint(0, len(s)), random.choice(list(closing)))
    else:
        rights = [i for i, ch in enumerate(s) if ch in closing]
        if not rights:
            return _introduce_error(seq, maps)
        del s[random.choice(rights)]
    return ''.join(s)

def generate_bracket_problem(min_len: int,
                             max_len: int,
                             p_valid: float,
                             types: List[str],
                             depth_limit: int) -> Dict[str, Any]:
    maps = _build_maps(types)
    start = time.time()
    while True:
        if time.time() - start > 150:
            raise RuntimeError("Generation timeout")
        n = random.randint(min_len, max_len)
        n += n % 2
        base = _generate_balanced(n, maps)
        depth = _nested_depth(base, maps)
        if random.random() < p_valid:
            return {
                'seq': base,
                'first_error_pos': -1,
                'error_type': 0,
                'is_valid': True,
                'nested_score': depth
            }
        seq_err = _introduce_error(base, maps)
        pos = _first_error_position(seq_err, maps)
        if depth >= depth_limit and pos > len(seq_err)//2:
            continue
        return {
            'seq': seq_err,
            'first_error_pos': pos,
            'error_type': _error_type(seq_err, maps),
            'is_valid': False,
            'nested_score': depth
        }

# ---------- 任务固定 ----------
def sample_bracket_types(k: int) -> List[str]:
    return random.sample(ALL_BRACKETS, k)

def choose_task() -> str:
    return 'pos_type'   # 固定任务

def generate_answer(task: str, pos: int, valid: bool, etype: int):
    return f"{pos},{etype}"

def generate_question_desc(task: str) -> str:
    return '请同时给出首个错误位置及错误类型, 用逗号隔开(示例: 17,2)。错误类型: 0-合法, 1-括号不匹配, 2-多余右括号, 3-缺失右括号'

# ---------- 验证 ----------
def _is_unique_answer(seq: str, task: str, ans) -> bool:
    maps = _build_maps(ALL_BRACKETS)
    pos = _first_error_position(seq, maps)
    etype = _error_type(seq, maps)
    try:
        a_pos, a_type = map(int, str(ans).split(','))
    except ValueError:
        return False
    return a_pos == pos and a_type == etype

def is_unique_answer(seq: str, task: str, ans) -> bool:
    return _is_unique_answer(seq, task, ans)

def validate_answer(seq: str, task: str, ans) -> bool:
    return _is_unique_answer(seq, task, ans)

def gen_policy(*args, **kwargs) -> Dict[str, Any]:
    return {}

# ---------------- 自检 ----------------
if __name__ == "__main__":
    for _ in range(200):
        tlist = sample_bracket_types(random.randint(2, 4))
        pb = generate_bracket_problem(20, 80, 0.25, tlist, depth_limit=6)
        std = generate_answer('pos_type', pb['first_error_pos'], pb['is_valid'], pb['error_type'])
        assert validate_answer(pb['seq'], 'pos_type', std)
    print("Self-test passed (200 samples).")