# dyck_language_errors_0.py
# 改进要点：
# - 新增最小推理阈值：min_prefix_depth_at_error 与 min_matched_pairs_ratio，要求错误出现时前缀栈深度与匹配量不低于阈值；
# - 保留 mismatch_min_pos_ratio 与 illegal_min_pos_ratio 以避免错误过早出现的显见线索；
# - 可读性最大长度 readable_max_len 限制超长序列；max_depth_ratio 控制嵌套上限；
# - 后验一致性与有限重试保证题面质量与多样性；
# - 唯一解校验：线性复算 + 180s 时限保护，不对玩家暴露。

from typing import List, Tuple, Dict, Any
import random
import ast
import time
import math

ALL_PAIRS = [('(', ')'), ('[', ']'), ('{', '}'), ('<', '>')]
ILLEGAL_CAND = list('@#&*!?/\\+=-_~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')

def gen_policy(type_min: int, type_max: int, complexity_level: int,
               legal_prob_pct: int, unclosed_bias_pct: int, mismatch_bias_pct: int, illegal_bias_pct: int) -> Dict[str, Any]:
    """随机策略：索引、非法/末尾策略、类型子集、开括号偏置、前缀约束、深度上限、错误位置比例、可读性最大长度、最小推理阈值。"""
    k = random.randint(max(2, min(type_min, 4)), max(2, min(type_max, 4)))
    k = max(2, min(k, 4))
    pairs = random.sample(ALL_PAIRS, k)
    canonical = ['()', '[]', '{}', '<>']
    used = [op + cl for op, cl in pairs]
    types_used_sorted = [t for t in canonical if t in used]

    index_base = random.choice([0, 1])
    illegal_mode = random.choice(['error', 'skip'])
    end_unclosed_is_error = random.choice([True, False])

    if complexity_level == 1:
        open_bias = random.uniform(0.52, 0.60)
        prefix_type_min = 2
        max_run_same_type = random.randint(3, 5)
        max_depth_ratio = random.uniform(0.30, 0.42)
        min_prefix_depth_at_error = random.randint(2, 3)
        min_matched_pairs_ratio = random.uniform(0.12, 0.20)
    elif complexity_level == 2:
        open_bias = random.uniform(0.47, 0.63)
        prefix_type_min = 3
        max_run_same_type = random.randint(3, 6)
        max_depth_ratio = random.uniform(0.33, 0.48)
        min_prefix_depth_at_error = random.randint(3, 4)
        min_matched_pairs_ratio = random.uniform(0.15, 0.25)
    else:
        open_bias = random.uniform(0.45, 0.65)
        prefix_type_min = 3
        max_run_same_type = random.randint(4, 7)
        max_depth_ratio = random.uniform(0.35, 0.55)
        min_prefix_depth_at_error = random.randint(3, 5)
        min_matched_pairs_ratio = random.uniform(0.18, 0.30)

    illegal_min_pos_ratio = random.uniform(0.15, 0.35)
    mismatch_min_pos_ratio = random.uniform(0.15, 0.35)
    readable_max_len = random.randint(48, 72)

    return {
        'types_used': types_used_sorted,
        'pairs': pairs,
        'index_base': index_base,
        'illegal_mode': illegal_mode,
        'end_unclosed_is_error': end_unclosed_is_error,
        'legal_prob_pct': legal_prob_pct,
        'unclosed_bias_pct': unclosed_bias_pct,
        'mismatch_bias_pct': mismatch_bias_pct,
        'illegal_bias_pct': illegal_bias_pct,
        'open_bias': open_bias,
        'prefix_type_min': prefix_type_min,
        'max_run_same_type': max_run_same_type,
        'max_depth_ratio': max_depth_ratio,
        'illegal_min_pos_ratio': illegal_min_pos_ratio,
        'mismatch_min_pos_ratio': mismatch_min_pos_ratio,
        'readable_max_len': readable_max_len,
        'min_prefix_depth_at_error': min_prefix_depth_at_error,
        'min_matched_pairs_ratio': min_matched_pairs_ratio,
        'complexity_level': complexity_level,
    }

def build_policy_text(policy: Dict[str, Any]) -> str:
    idx_txt = f"索引起始为 {policy['index_base']}；"
    ill_txt = "遇到非括号字符视为错误；" if policy['illegal_mode'] == 'error' else "遇到非括号字符跳过不计为错误；"
    end_txt = "末尾未闭合视为错误；" if policy['end_unclosed_is_error'] else "末尾未闭合不视为错误；"
    types_txt = "本题使用的括号类型为 [" + ', '.join(policy['types_used']) + "]；"
    glossary = "错误类型术语：empty_close 空栈遇闭；mismatch 栈顶与闭括号不匹配；illegal 非法字符；unclosed 末尾未闭合；none 完全合法。"
    return f"{idx_txt}{ill_txt}{end_txt}{types_txt}{glossary}"

def build_query_text(policy: Dict[str, Any], format_spec: str) -> str:
    return f"请按格式 [{format_spec}] 输出答案。"

def parse_literal(s: str) -> str:
    try:
        return ast.literal_eval(s)
    except Exception:
        return s

def build_types_desc(inst: Dict[str, Any]) -> str:
    try:
        canonical = ['()', '[]', '{}', '<>']
        used = inst.get('types_used', [])
        ordered = [t for t in canonical if t in used]
        return ', '.join(ordered)
    except Exception:
        return ''

def build_format_spec() -> str:
    return 'pos====prefix_depth====matched_pairs====max_depth====error_type'

# ------------------------------
# 结构生成与约束（深度上限控制）
# ------------------------------
def _gen_block(pairs: List[Tuple[str, str]], target_depth: int, open_bias: float,
               max_run_same_type: int, depth_cap: int) -> str:
    opens = [op for op, _ in pairs]
    close_of = {op: cl for op, cl in pairs}
    seq: List[str] = []
    stack: List[str] = []
    run_same = 0
    last_op = None
    for _ in range(target_depth):
        op_choices = opens[:]
        if last_op is not None and run_same >= max_run_same_type:
            op_choices = [x for x in op_choices if x != last_op]
        op = random.choice(op_choices)
        seq.append(op)
        stack.append(op)
        run_same = run_same + 1 if op == last_op else 1
        last_op = op
        if len(stack) >= depth_cap:
            break
    extra_steps = random.randint(target_depth, target_depth * 2)
    for _ in range(extra_steps):
        if len(stack) >= depth_cap:
            top = stack.pop()
            seq.append(close_of[top])
            run_same = 0
            last_op = None
            continue
        can_open = random.random() < open_bias
        if can_open:
            op_choices = opens[:]
            if last_op is not None and run_same >= max_run_same_type:
                op_choices = [x for x in op_choices if x != last_op]
            op = random.choice(op_choices)
            seq.append(op)
            stack.append(op)
            run_same = run_same + 1 if op == last_op else 1
            last_op = op
        else:
            if stack:
                top = stack.pop()
                seq.append(close_of[top])
                run_same = 0
                last_op = None
    while stack:
        top = stack.pop()
        seq.append(close_of[top])
    return ''.join(seq)

def _ensure_prefix_type_diversity(seq: str, pairs: List[Tuple[str, str]], required_types: int) -> str:
    opens = [op for op, _ in pairs]
    types_present = set()
    for ch in seq[:max(10, len(seq)//3)]:
        if ch in opens:
            types_present.add(ch)
    while len(types_present) < required_types and len(seq) < 10000:
        for op, cl in pairs:
            seq = op + cl + seq
            types_present.add(op)
            if len(types_present) >= required_types:
                break
    return seq

def _gen_legal_complex(pairs: List[Tuple[str, str]], depth_min: int, depth_max: int,
                       open_bias: float, prefix_type_min: int, max_run_same_type: int,
                       min_len: int, max_len: int, max_depth_ratio: float) -> str:
    total_target_len = random.randint(min_len, max_len)
    depth_cap = max(2, int(math.floor(max_depth_ratio * total_target_len)))
    blocks: List[str] = []
    while sum(len(b) for b in blocks) < total_target_len:
        d = random.randint(depth_min, depth_max)
        b = _gen_block(pairs, d, open_bias, max_run_same_type, depth_cap)
        blocks.append(b)
    seq = ''.join(blocks)
    if len(seq) > max_len:
        seq = seq[:max_len]
        close_of = {op: cl for op, cl in pairs}
        match = {cl: op for op, cl in pairs}
        stack: List[str] = []
        fixed: List[str] = []
        for ch in seq:
            if ch in close_of:
                stack.append(ch)
                fixed.append(ch)
            elif ch in match:
                if stack and stack[-1] == match[ch]:
                    stack.pop()
                    fixed.append(ch)
                else:
                    if stack:
                        top = stack.pop()
                        fixed.append(close_of[top])
        while stack:
            fixed.append(close_of[stack.pop()])
        seq = ''.join(fixed)
    seq = _ensure_prefix_type_diversity(seq, pairs, prefix_type_min)
    close_of = {op: cl for op, cl in pairs}
    match = {cl: op for op, cl in pairs}
    stack: List[str] = []
    fixed: List[str] = []
    for ch in seq:
        if ch in close_of:
            stack.append(ch)
            fixed.append(ch)
        elif ch in match:
            if stack and stack[-1] == match[ch]:
                stack.pop()
                fixed.append(ch)
            else:
                if stack:
                    top = stack.pop()
                    fixed.append(close_of[top])
    while stack:
        fixed.append(close_of[stack.pop()])
    seq = ''.join(fixed)
    return seq

# ------------------------------
# 错误注入与一致性保障
# ------------------------------
def _inject_unclosed(base_seq: str, pairs: List[Tuple[str, str]], extra_opens: int) -> str:
    opens = [op for op, _ in pairs]
    tail = ''.join(random.choice(opens) for _ in range(extra_opens))
    return base_seq + tail

def _inject_mismatch_with_minpos(base_seq: str, pairs: List[Tuple[str, str]], min_pos: int) -> str:
    closes = [cl for _, cl in pairs]
    seq = list(base_seq)
    close_positions = [i for i, ch in enumerate(seq) if ch in closes]
    filtered = [i for i in close_positions if i >= min_pos] or close_positions
    if not filtered:
        seq.insert(0, random.choice(closes))
        return ''.join(seq)
    pos = random.choice(filtered)
    original = seq[pos]
    cand = [c for c in closes if c != original]
    if not cand:
        seq.insert(0, random.choice(closes))
        return ''.join(seq)
    seq[pos] = random.choice(cand)
    return ''.join(seq)

def _inject_illegal_at(seq: str, pos: int) -> str:
    seq_list = list(seq)
    ch = random.choice(ILLEGAL_CAND)
    seq_list.insert(pos, ch)
    return ''.join(seq_list)

# ------------------------------
# 主实例生成器（后验一致性与阈值对齐）
# ------------------------------
def gen_instance(min_len: int, max_len: int, depth_min: int, depth_max: int, policy: Dict[str, Any],
                 seed: int = None) -> Dict[str, Any]:
    if seed is not None:
        random.seed(seed)
    pairs = policy['pairs']
    types_used = policy['types_used']
    retries = 0
    effective_max_len = min(max_len, policy.get('readable_max_len', max_len))

    def thresholds_ok(metrics: Dict[str, Any], base_len: int) -> bool:
        min_depth = int(policy['min_prefix_depth_at_error'])
        min_pairs = int(math.floor(policy['min_matched_pairs_ratio'] * base_len / 2.0))
        return (metrics['prefix_depth'] >= min_depth) and (metrics['matched_pairs'] >= min_pairs)

    while True:
        retries += 1
        base = _gen_legal_complex(
            pairs,
            depth_min, depth_max,
            policy['open_bias'],
            policy['prefix_type_min'],
            policy['max_run_same_type'],
            min_len, effective_max_len,
            policy['max_depth_ratio']
        )
        make_legal = random.randint(0, 99) < max(0, min(100, policy['legal_prob_pct']))

        if not make_legal:
            u = max(1, policy['unclosed_bias_pct'])
            m_ = max(1, policy['mismatch_bias_pct'])
            i = max(1, policy['illegal_bias_pct'])
            total = u + m_ + i
            r = random.randint(1, total)
            mode = 'unclosed' if r <= u else ('mismatch' if r <= u + m_ else 'illegal')

            if mode == 'unclosed':
                if policy['end_unclosed_is_error']:
                    max_extra = max(1, effective_max_len - len(base))
                    extra = random.randint(1, max_extra)
                    seq = _inject_unclosed(base, pairs, extra)
                else:
                    min_pos_mis = max(0, int(math.floor(policy['mismatch_min_pos_ratio'] * len(base))))
                    seq = _inject_mismatch_with_minpos(base, pairs, min_pos_mis)
            elif mode == 'mismatch':
                min_pos_mis = max(0, int(math.floor(policy['mismatch_min_pos_ratio'] * len(base))))
                seq = _inject_mismatch_with_minpos(base, pairs, min_pos_mis)
            else:
                if policy['illegal_mode'] == 'skip':
                    min_pos_mis = max(0, int(math.floor(policy['mismatch_min_pos_ratio'] * len(base))))
                    seq = _inject_mismatch_with_minpos(base, pairs, min_pos_mis)
                else:
                    min_pos_il = max(1, int(math.floor(policy['illegal_min_pos_ratio'] * len(base))))
                    insert_pos = random.randint(min_pos_il, len(base)) if len(base) > min_pos_il else min_pos_il
                    seq = _inject_illegal_at(base, insert_pos)
                    if len(seq) > effective_max_len:
                        keep_len = effective_max_len
                        base_cut = base[:keep_len-1] if keep_len > 0 else base
                        insert_pos2 = min(insert_pos, keep_len-1 if keep_len > 0 else 0)
                        seq = _inject_illegal_at(base_cut, insert_pos2)
        else:
            seq = base

        if not (min_len <= len(seq) <= effective_max_len):
            if retries > 200:
                fallback_pairs = random.sample(ALL_PAIRS, 2)
                seq_fb = _gen_legal_complex(fallback_pairs, 2, 4, 0.55, 2, 4, max(12, min_len), min(effective_max_len, min_len + 24), 0.4)
                types_sorted = []
                for t in ['()', '[]', '{}', '<>']:
                    if t in [op + cl for op, cl in fallback_pairs]:
                        types_sorted.append(t)
                return {'seq_lit': repr(seq_fb), 'types_used': types_sorted, 'length': len(seq_fb)}
            continue

        m = compute_metrics(seq, policy)
        if make_legal:
            if m['error_type'] == 'none':
                return {'seq_lit': repr(seq), 'types_used': types_used, 'length': len(seq)}
            else:
                if retries > 200:
                    return {'seq_lit': repr(base), 'types_used': types_used, 'length': len(base)}
                continue
        else:
            # illegal 首错与阈值对齐
            if policy['illegal_mode'] == 'error' and m['error_type'] != 'illegal':
                min_pos_il = max(1, int(math.floor(policy['illegal_min_pos_ratio'] * len(base))))
                improved = False
                for delta in range(0, 6):
                    pos_try = min_pos_il + delta
                    if pos_try > len(base):
                        break
                    seq_try = _inject_illegal_at(base, pos_try)
                    if len(seq_try) > effective_max_len:
                        base_cut = base[:effective_max_len-1]
                        pos_try2 = min(pos_try, effective_max_len-1)
                        seq_try = _inject_illegal_at(base_cut, pos_try2)
                    m_try = compute_metrics(seq_try, policy)
                    if m_try['error_type'] == 'illegal' and thresholds_ok(m_try, len(base)):
                        seq, m, improved = seq_try, m_try, True
                        break
                # 未改善则接受当前错误类型

            # mismatch 对齐与阈值
            if m['error_type'] in {'empty_close', 'mismatch'}:
                if m['error_type'] == 'empty_close' or not thresholds_ok(m, len(base)):
                    for _ in range(5):
                        min_pos_mis = max(0, int(math.floor(policy['mismatch_min_pos_ratio'] * len(base))))
                        seq_try = _inject_mismatch_with_minpos(base, pairs, min_pos_mis)
                        m_try = compute_metrics(seq_try, policy)
                        if m_try['error_type'] == 'mismatch' and thresholds_ok(m_try, len(base)):
                            seq, m = seq_try, m_try
                            break

            # unclosed 阈值不达标则重生
            if m['error_type'] == 'unclosed' and not thresholds_ok(m, len(base)):
                continue

            return {'seq_lit': repr(seq), 'types_used': types_used, 'length': len(seq)}

# ------------------------------
# 复合指标计算与答案
# ------------------------------
def compute_metrics(seq: str, policy: Dict[str, Any]) -> Dict[str, Any]:
    index_base = int(policy['index_base'])
    illegal_mode = policy['illegal_mode']
    opens = set(op for op, _ in policy['pairs'])
    match = {cl: op for op, cl in policy['pairs']}
    stack: List[str] = []
    max_depth = 0
    matched_pairs = 0
    for pos0, ch in enumerate(seq):
        idx = pos0 + index_base
        if ch in opens:
            stack.append(ch)
            if len(stack) > max_depth:
                max_depth = len(stack)
        elif ch in match:
            if not stack:
                return {'pos': idx, 'error_type': 'empty_close', 'prefix_depth': 0, 'max_depth': max_depth, 'matched_pairs': matched_pairs}
            if stack[-1] != match[ch]:
                return {'pos': idx, 'error_type': 'mismatch', 'prefix_depth': len(stack), 'max_depth': max_depth, 'matched_pairs': matched_pairs}
            stack.pop()
            matched_pairs += 1
        else:
            if illegal_mode == 'error':
                return {'pos': idx, 'error_type': 'illegal', 'prefix_depth': len(stack), 'max_depth': max_depth, 'matched_pairs': matched_pairs}
            else:
                continue
    if stack and policy['end_unclosed_is_error']:
        return {'pos': len(seq) + index_base, 'error_type': 'unclosed', 'prefix_depth': len(stack), 'max_depth': max_depth, 'matched_pairs': matched_pairs}
    return {'pos': -1, 'error_type': 'none', 'prefix_depth': 0, 'max_depth': max_depth, 'matched_pairs': matched_pairs}

def compose_answer(seq: str, policy: Dict[str, Any]) -> str:
    m = compute_metrics(seq, policy)
    return f"{m['pos']}===={m['prefix_depth']}===={m['matched_pairs']}===={m['max_depth']}===={m['error_type']}"

# ------------------------------
# 唯一解校验（线性时间 + 时限）
# ------------------------------
def _parse_answer_str(ans_str: str) -> Dict[str, Any]:
    parts = ans_str.split('====')
    if len(parts) != 5:
        raise ValueError('答案格式不正确，应包含5段并用====分隔')
    pos_s, pd_s, mp_s, md_s, et_s = parts
    pos = int(pos_s)
    prefix_depth = int(pd_s)
    matched_pairs = int(mp_s)
    max_depth = int(md_s)
    error_type = et_s.strip()
    if error_type not in {'none', 'unclosed', 'mismatch', 'illegal', 'empty_close'}:
        raise ValueError('错误类型不在可选集合中')
    return {'pos': pos, 'prefix_depth': prefix_depth, 'matched_pairs': matched_pairs, 'max_depth': max_depth, 'error_type': error_type}

def validate_answer(seq: str, ans_str: str, policy: Dict[str, Any], time_limit_sec: int = 180) -> bool:
    start = time.time()
    try:
        ans = _parse_answer_str(ans_str)
    except Exception:
        return False
    if time.time() - start > time_limit_sec:
        return False
    m = compute_metrics(seq, policy)
    if time.time() - start > time_limit_sec:
        return False
    return (ans['pos'] == m['pos'] and
            ans['prefix_depth'] == m['prefix_depth'] and
            ans['matched_pairs'] == m['matched_pairs'] and
            ans['max_depth'] == m['max_depth'] and
            ans['error_type'] == m['error_type'])

# ------------------------------
# 示例样例（供外部合成器）
# ------------------------------
def sample_pairs() -> List[Tuple[str, str]]:
    random.seed(2026)
    samples: List[Tuple[str, str]] = []
    for _ in range(6):
        policy = gen_policy(2, 4, random.randint(1, 3), 50, 40, 40, 20)
        inst = gen_instance(12, 48, 2, 5, policy)
        seq_lit = inst['seq_lit']
        seq = parse_literal(seq_lit)
        ans = compose_answer(seq, policy)
        samples.append((seq_lit, ans))
    return samples