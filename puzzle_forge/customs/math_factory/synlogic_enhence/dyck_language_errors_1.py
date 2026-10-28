# dyck_language_errors_4.py
# -*- coding: utf-8 -*-
"""
多层带权括号随机规则造题与首错定位评估器（增强版，向下兼容旧接口）

自定义算子：
- pick_one(options)
- choose_target_type(min_err_pos)
- build_rules(n_pairs, overflow_w, overflow_g, T_w_min, T_w_max, T_g_min, T_g_max, w_max, gw_max, check_order, seed=None)
- rules_to_text(pairs, w_open, g_open, overflow_w, overflow_g, T_w, T_g, check_order, active_in_g)
- function_1(seq: str, rule_pack_or_T)
- function_2(rule_pack: dict, min_len, max_len, target_type, min_err_pos, seed=None)
- validate_unique(seq, rule_pack_or_T, ans, time_limit=180.0)
"""

from typing import List, Dict, Optional, Tuple, Union, Any
import random
import time

ALL_PAIRS: List[str] = ['()', '[]', '{}', '<>']
NAME_MAP: Dict[str, str] = {'()': '小括号', '[]': '方括号', '{}': '大括号', '<>': '尖括号'}

# ------------------ 基础工具 ------------------

def pick_one(options: List[Any]) -> Any:
    if not isinstance(options, list) or not options:
        return None
    return random.choice(options)

def choose_target_type(min_err_pos: int) -> str:
    if min_err_pos <= 1:
        return pick_one(['valid', 'overflow_w', 'overflow_g', 'mismatch', 'early_close', 'unclosed'])
    return pick_one(['valid', 'overflow_w', 'overflow_g', 'mismatch', 'unclosed'])

# ------------------ 规则构建与描述 ------------------

def build_rules(n_pairs: int,
                overflow_w: str,
                overflow_g: str,
                T_w_min: int,
                T_w_max: int,
                T_g_min: int,
                T_g_max: int,
                w_max: int,
                gw_max: int,
                check_order: str,
                seed: Optional[int] = None) -> Dict:
    rng = random.Random(seed)
    pairs = rng.sample(ALL_PAIRS, k=n_pairs)

    w_open: Dict[str, int] = {}
    g_open: Dict[str, int] = {}
    for p in pairs:
        op = p[0]
        w_open[op] = rng.randint(1, max(1, w_max))
        g_open[op] = rng.randint(1, max(1, gw_max))

    # 参与G的类型集合：至少1种
    openers = [p[0] for p in pairs]
    g_active_num = rng.randint(1, len(openers))
    active_set = set(rng.sample(openers, k=g_active_num))
    active_in_g: Dict[str, bool] = {op: (op in active_set) for op in openers}

    # 阈值下界（ge模式需 +1）
    min_w = min(w_open.values())
    min_g_active = min([g_open[op] for op in openers if active_in_g[op]]) if any(active_in_g.values()) else 0
    T_w_low = max(T_w_min, min_w + (1 if overflow_w == 'ge' else 0))
    T_g_low = max(T_g_min, min_g_active + (1 if overflow_g == 'ge' else 0))
    T_w_high = max(T_w_low, T_w_max)
    T_g_high = max(T_g_low, T_g_max)
    T_w = rng.randint(T_w_low, T_w_high)
    T_g = rng.randint(T_g_low, T_g_high) if any(active_in_g.values()) else 10**9

    return {
        'pairs': pairs[:],
        'w_open': w_open,
        'g_open': g_open,
        'overflow_w': overflow_w,
        'overflow_g': overflow_g,
        'T_w': T_w,
        'T_g': T_g,
        'check_order': check_order,
        'active_in_g': active_in_g
    }

def rules_to_text(pairs: List[str], w_open: Dict[str, int], g_open: Dict[str, int],
                  overflow_w: str, overflow_g: str, T_w: int, T_g: int,
                  check_order: str, active_in_g: Dict[str, bool]) -> str:
    parts = []
    for p in pairs:
        nm = NAME_MAP[p]
        op = p[0]
        parts.append(f'{nm}的主权重={w_open[op]}, 组权重={g_open[op]}')
    rule_str = '; '.join(parts)
    ovw = 'W + 新主权重 > T_w' if overflow_w == 'gt' else 'W + 新主权重 >= T_w'
    ovg = 'G + 新组权重 > T_g' if overflow_g == 'gt' else 'G + 新组权重 >= T_g'
    order_text = '开括号时先检查W再检查G' if check_order == 'WG' else '开括号时先检查G再检查W'
    # 列出参与G的类型
    def pair_name_from_op(op: str) -> str:
        pair = op + (')' if op == '(' else ']' if op == '[' else '}' if op == '{' else '>')
        return NAME_MAP[pair]
    active_list = ', '.join([pair_name_from_op(op) for op, flag in active_in_g.items() if flag]) or '无'
    return f'使用的括号与权重如下: {rule_str}; 主载荷溢出判定: {ovw}; 组载荷溢出判定: {ovg}; {order_text}; 参与组载荷计算的括号类型: {active_list}; 闭括号需与栈顶匹配; 结束仍未闭合则错误位置为长度+1。'

# ------------------ 表派生与评估 ------------------

def _derive_tables(rule_pack_or_T: Union[Dict, int]) -> Tuple[Dict[str, str], Dict[str, str], List[str], List[str], Dict[str, int], Dict[str, int], int, int, str, str, str, Dict[str, bool]]:
    if isinstance(rule_pack_or_T, dict):
        pairs: List[str] = rule_pack_or_T['pairs']
        w_open: Dict[str, int] = rule_pack_or_T['w_open']
        g_open: Dict[str, int] = rule_pack_or_T['g_open']
        T_w: int = rule_pack_or_T['T_w']
        T_g: int = rule_pack_or_T['T_g']
        overflow_w: str = rule_pack_or_T['overflow_w']
        overflow_g: str = rule_pack_or_T['overflow_g']
        check_order: str = rule_pack_or_T['check_order']
        active_in_g: Dict[str, bool] = rule_pack_or_T['active_in_g']
    else:
        # 旧接口：仅主载荷W，G关闭
        T_int: int = int(rule_pack_or_T)
        pairs = ALL_PAIRS[:]
        w_open = {'(' : 1, '[' : 2, '{' : 3, '<' : 2}
        g_open = {'(' : 0, '[' : 0, '{' : 0, '<' : 0}
        T_w = T_int
        T_g = 10**9
        overflow_w = 'gt'
        overflow_g = 'gt'
        check_order = 'WG'
        active_in_g = {op: False for op in w_open}
    OPEN_TO_CLOSE: Dict[str, str] = {p[0]: p[1] for p in pairs}
    CLOSE_TO_OPEN: Dict[str, str] = {p[1]: p[0] for p in pairs}
    OPENERS: List[str] = list(OPEN_TO_CLOSE.keys())
    CLOSERS: List[str] = list(CLOSE_TO_OPEN.keys())
    return OPEN_TO_CLOSE, CLOSE_TO_OPEN, OPENERS, CLOSERS, w_open, g_open, T_w, T_g, overflow_w, overflow_g, check_order, active_in_g

def function_1(seq: str, rule_pack_or_T: Union[Dict, int]) -> int:
    OPEN_TO_CLOSE, CLOSE_TO_OPEN, OPENERS, CLOSERS, W_OPEN, G_OPEN, T_w, T_g, overflow_w, overflow_g, check_order, active_in_g = _derive_tables(rule_pack_or_T)
    def will_over_w(cur: int, w: int) -> bool:
        return (cur + w > T_w) if overflow_w == 'gt' else (cur + w >= T_w)
    def will_over_g(cur: int, g: int) -> bool:
        return (cur + g > T_g) if overflow_g == 'gt' else (cur + g >= T_g)
    stack: List[str] = []
    W = 0
    G = 0
    for i, ch in enumerate(seq, start=1):
        if ch in OPENERS:
            w = W_OPEN[ch]
            g = G_OPEN[ch] if active_in_g.get(ch, False) else 0
            if check_order == 'WG':
                if will_over_w(W, w): return i
                if will_over_g(G, g): return i
            else:
                if will_over_g(G, g): return i
                if will_over_w(W, w): return i
            stack.append(ch)
            W += w
            G += g
        elif ch in CLOSERS:
            if not stack: return i
            top = stack[-1]
            if OPEN_TO_CLOSE[top] != ch: return i
            stack.pop()
            W -= W_OPEN[top]
            G -= (G_OPEN[top] if active_in_g.get(top, False) else 0)
        else:
            return i
    if stack:
        return len(seq) + 1
    return -1

# ------------------ 前缀与生成器 ------------------

def _padding_valid_pairs(rule_pack: Dict, length_needed: int, rng: random.Random) -> str:
    if length_needed <= 0:
        return ''
    OPEN_TO_CLOSE, _, OPENERS, _, W_OPEN, G_OPEN, _, _, overflow_w, overflow_g, check_order, active_in_g = _derive_tables(rule_pack)
    # 最轻（按W优先，再按G参与）对
    op = min(OPENERS, key=lambda x: (W_OPEN[x], (G_OPEN[x] if active_in_g.get(x, False) else 0)))
    cl = OPEN_TO_CLOSE[op]
    unit = op + cl
    base = unit * ((length_needed + 1) // 2)
    return base[:length_needed]

def _build_valid_pair_sequence(rule_pack: Dict, length_target: int, rng: random.Random) -> str:
    OPEN_TO_CLOSE, _, OPENERS, _, W_OPEN, G_OPEN, T_w, T_g, overflow_w, overflow_g, check_order, active_in_g = _derive_tables(rule_pack)
    def will_over_w(cur: int, w: int) -> bool:
        return (cur + w > T_w) if overflow_w == 'gt' else (cur + w >= T_w)
    def will_over_g(cur: int, g: int) -> bool:
        return (cur + g > T_g) if overflow_g == 'gt' else (cur + g >= T_g)
    seq: List[str] = []
    stack: List[str] = []
    W = 0
    G = 0
    max_steps = max(50 * (length_target + 1), 200)
    while len(seq) < length_target and max_steps > 0:
        max_steps -= 1
        candidates = []
        for op in OPENERS:
            w = W_OPEN[op]; g = (G_OPEN[op] if active_in_g.get(op, False) else 0)
            ok_w = not will_over_w(W, w)
            ok_g = not will_over_g(G, g)
            ok = (ok_w and ok_g) if check_order == 'WG' else (ok_g and ok_w)
            if ok:
                candidates.append(op)
        do_open = False
        if not stack:
            do_open = len(candidates) > 0
        else:
            do_open = (len(candidates) > 0 and rng.random() < 0.6)
        if do_open:
            ch = rng.choice(candidates)
            seq.append(ch); stack.append(ch)
            W += W_OPEN[ch]; G += (G_OPEN[ch] if active_in_g.get(ch, False) else 0)
        else:
            if not stack: break
            top = stack.pop()
            seq.append(OPEN_TO_CLOSE[top])
            W -= W_OPEN[top]; G -= (G_OPEN[top] if active_in_g.get(top, False) else 0)
    while stack:
        top = stack.pop()
        seq.append(OPEN_TO_CLOSE[top])
        W -= W_OPEN[top]; G -= (G_OPEN[top] if active_in_g.get(top, False) else 0)
    return ''.join(seq)

def _build_safe_prefix(rule_pack: Dict, target_len: int, rng: random.Random,
                       min_distinct_types: int = 2, min_active_g_pairs: int = 1) -> str:
    """
    构造长度为target_len的合法前缀（尽量偶数），包含至少min_distinct_types种不同括号，
    且至少min_active_g_pairs个参与G的括号对。采用成对填充，保证前缀本身无错。
    """
    if target_len <= 0:
        return ''
    # 使用对数（成对添加）
    num_pairs = (target_len // 2)
    OPEN_TO_CLOSE, _, OPENERS, _, W_OPEN, G_OPEN, T_w, T_g, overflow_w, overflow_g, check_order, active_in_g = _derive_tables(rule_pack)

    # 可用的对类型
    def opener_ok(op: str) -> bool:
        w = W_OPEN[op]; g = (G_OPEN[op] if active_in_g.get(op, False) else 0)
        # 在栈为空时开一个（随后立即闭合），检查顺序即在W=0,G=0时不触发
        if check_order == 'WG':
            return (w <= T_w if overflow_w == 'gt' else w < T_w) and (g <= T_g if overflow_g == 'gt' else g < T_g)
        else:
            return (g <= T_g if overflow_g == 'gt' else g < T_g) and (w <= T_w if overflow_w == 'gt' else w < T_w)

    candidates = [op for op in OPENERS if opener_ok(op)]
    if not candidates:
        # 兜底：不用G限制（极罕见），退化为最轻小括号对
        candidates = OPENERS[:]

    # 先放置满足G参与的对，再补足不同类型
    active_ops = [op for op in candidates if active_in_g.get(op, False)]
    seq_ops: List[str] = []

    # 添加参与G的对
    for _ in range(min(min_active_g_pairs, num_pairs)):
        if active_ops:
            seq_ops.append(random.choice(active_ops))
        else:
            break
    # 保证不同类型至少min_distinct_types
    used = set(seq_ops)
    need_types = max(0, min_distinct_types - len(used))
    rest_ops = [op for op in candidates if op not in used]
    for _ in range(need_types):
        if rest_ops:
            pick = rest_ops.pop(0)
            seq_ops.append(pick)
            used.add(pick)
        else:
            break
    # 填满其余位置
    while len(seq_ops) < num_pairs:
        seq_ops.append(random.choice(candidates))

    # 拼接为“对”
    seq_list: List[str] = []
    for op in seq_ops:
        seq_list.append(op)
        seq_list.append(OPEN_TO_CLOSE[op])
    seq = ''.join(seq_list)
    # 若需要奇数长度，额外补一个开括号（保持合法前缀时不会立刻报错）
    if len(seq) < target_len:
        add_op = random.choice(candidates)
        seq += add_op
    return seq[:target_len]

# ------------------ 生成主函数 ------------------

def function_2(rule_pack: Dict, min_len: int, max_len: int, target_type: str, min_err_pos: int, seed: Optional[int] = None) -> str:
    rng = random.Random(seed)
    OPEN_TO_CLOSE, CLOSE_TO_OPEN, OPENERS, CLOSERS, W_OPEN, G_OPEN, T_w, T_g, overflow_w, overflow_g, check_order, active_in_g = _derive_tables(rule_pack)
    def will_over_w(cur: int, w: int) -> bool:
        return (cur + w > T_w) if overflow_w == 'gt' else (cur + w >= T_w)
    def will_over_g(cur: int, g: int) -> bool:
        return (cur + g > T_g) if overflow_g == 'gt' else (cur + g >= T_g)

    attempts = 500
    while attempts > 0:
        attempts -= 1

        if target_type == 'valid':
            base_len = rng.randint(min_len, min(max_len, min_len + 24))
            seq = _build_valid_pair_sequence(rule_pack, base_len, rng)
            if len(seq) < min_len:
                seq += _padding_valid_pairs(rule_pack, min_len - len(seq), rng)
            if len(seq) <= max_len and function_1(seq, rule_pack) == -1:
                return seq
            continue

        # 统一安全前缀：长度取不小于min_err_pos-1的最近偶数，避免显见线索，且包含G信息与多类型
        safe_len = max(0, min_err_pos - 1)
        if safe_len % 2 == 1:
            safe_len += 1
        # 预留至少1个位置用于制造错误
        if safe_len > max_len - 1:
            safe_len = max(0, max_len - 3 if (max_len - 3) >= 0 else 0)
            if safe_len % 2 == 1:
                safe_len -= 1
        safe_prefix = _build_safe_prefix(rule_pack, safe_len, rng, min_distinct_types=2, min_active_g_pairs=1)

        if target_type == 'overflow_w':
            # 构造W溢出，避免优先触发G
            if overflow_w == 'gt':
                # 尝试W_pre=T_w
                prefix_ops = _reachable_open_prefix(rule_pack, target_W=T_w, rng=rng)
                if prefix_ops is None:
                    # 退而求其次 W_pre<=T_w
                    found = False
                    for W_pre in range(T_w, -1, -1):
                        prefix_ops = _reachable_open_prefix(rule_pack, target_W=W_pre, rng=rng)
                        if prefix_ops is None:
                            continue
                        gap = T_w - W_pre
                        overflow_candidates = [op for op in OPENERS if W_OPEN[op] > gap]
                        if not overflow_candidates:
                            continue
                        err_op = rng.choice(overflow_candidates)
                        G_pre = sum((G_OPEN[ch] if active_in_g.get(ch, False) else 0) for ch in prefix_ops)
                        g_err = (G_OPEN[err_op] if active_in_g.get(err_op, False) else 0)
                        # 避免G先溢出
                        if check_order == 'WG':
                            if will_over_g(G_pre, g_err): 
                                continue
                        else:
                            if will_over_g(G_pre, g_err): 
                                continue
                        seq = safe_prefix + ''.join(prefix_ops) + err_op
                        if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == len(seq):
                            return seq
                        found = True
                    if not found:
                        continue
                else:
                    err_op = rng.choice(OPENERS)
                    G_pre = sum((G_OPEN[ch] if active_in_g.get(ch, False) else 0) for ch in prefix_ops)
                    g_err = (G_OPEN[err_op] if active_in_g.get(err_op, False) else 0)
                    if check_order == 'WG':
                        if will_over_g(G_pre, g_err): 
                            continue
                    else:
                        if will_over_g(G_pre, g_err): 
                            continue
                    seq = safe_prefix + ''.join(prefix_ops) + err_op
                    if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == len(seq):
                        return seq
                    continue
            else:  # ge
                w_set = sorted(set(W_OPEN[op] for op in OPENERS))
                rng.shuffle(w_set)
                built = False
                for w_err in w_set:
                    W_pre = T_w - w_err
                    if W_pre < 0:
                        continue
                    prefix_ops = _reachable_open_prefix(rule_pack, target_W=W_pre, rng=rng)
                    if prefix_ops is None:
                        continue
                    candidates = [op for op in OPENERS if W_OPEN[op] == w_err]
                    if not candidates:
                        continue
                    err_op = rng.choice(candidates)
                    G_pre = sum((G_OPEN[ch] if active_in_g.get(ch, False) else 0) for ch in prefix_ops)
                    g_err = (G_OPEN[err_op] if active_in_g.get(err_op, False) else 0)
                    if check_order == 'WG':
                        if will_over_g(G_pre, g_err): 
                            continue
                    else:
                        if will_over_g(G_pre, g_err): 
                            continue
                    seq = safe_prefix + ''.join(prefix_ops) + err_op
                    if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == len(seq):
                        return seq
                    built = True
                if not built:
                    continue

        elif target_type == 'overflow_g':
            # 直接构造让G溢出（err_op需参与G），同时避免W先溢出
            built = False
            active_ops = [op for op in OPENERS if active_in_g.get(op, False)]
            if not active_ops:
                # 若无参与G类型则无法构造G溢出，跳过本轮
                continue
            for err_op in active_ops:
                g_err = G_OPEN[err_op]
                if overflow_g == 'gt':
                    G_pre = T_g
                else:
                    G_pre = T_g - g_err
                    if G_pre < 0:
                        continue
                # 使用随机贪心提升G至G_pre
                Greach: List[str] = []
                Gsum = 0
                tries = 200
                while Gsum < G_pre and tries > 0:
                    tries -= 1
                    cands = [op for op in active_ops if Gsum + G_OPEN[op] <= G_pre]
                    if not cands:
                        break
                    ch = rng.choice(cands)
                    Greach.append(ch)
                    Gsum += G_OPEN[ch]
                if Gsum != G_pre:
                    continue
                W_pre = sum(W_OPEN[ch] for ch in Greach)
                w_err = W_OPEN[err_op]
                # 避免W先溢出（考虑检查顺序）
                if check_order == 'WG':
                    if will_over_w(W_pre, w_err): 
                        continue
                else:
                    if will_over_w(W_pre, w_err): 
                        continue
                seq = safe_prefix + ''.join(ch + OPEN_TO_CLOSE[ch] for ch in Greach).replace(')(', '')  # Greach由开括号集合构建，这里简化：只拼接开括号后在末尾直接出错
                # 上面简化：将Greach视作开括号列表并在末尾放置err_op即可；为确保无提前错误，直接拼接开括号（不开合）可能堆W/G，保守处理：构造为仅开括号串
                seq = safe_prefix + ''.join(Greach) + err_op
                if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == len(seq):
                    return seq
                built = True
            if not built:
                continue

        elif target_type == 'mismatch':
            # 安全前缀 + 若干开括号 + 错误闭括号
            seq_list: List[str] = list(safe_prefix)
            W = 0; G = 0; stack: List[str] = []
            while len(seq_list) + 1 < max_len:
                candidates = [op for op in OPENERS
                              if not will_over_w(W, W_OPEN[op])
                              and not will_over_g(G, (G_OPEN[op] if active_in_g.get(op, False) else 0))]
                if not candidates:
                    break
                ch = rng.choice(candidates)
                seq_list.append(ch); stack.append(ch)
                W += W_OPEN[ch]
                G += (G_OPEN[ch] if active_in_g.get(ch, False) else 0)
                if len(seq_list) >= min_len - 1 and rng.random() < 0.6:
                    break
            if not stack:
                op_min = min(OPENERS, key=lambda x: (W_OPEN[x], (G_OPEN[x] if active_in_g.get(x, False) else 0)))
                if not will_over_w(W, W_OPEN[op_min]) and not will_over_g(G, (G_OPEN[op_min] if active_in_g.get(op_min, False) else 0)) and len(seq_list) + 1 <= max_len:
                    seq_list.append(op_min); stack.append(op_min)
                    W += W_OPEN[op_min]
                    G += (G_OPEN[op_min] if active_in_g.get(op_min, False) else 0)
                else:
                    continue
            top = stack[-1]
            wrong_closers = [c for c in CLOSERS if c != OPEN_TO_CLOSE[top]]
            if not wrong_closers:
                continue
            wrong = rng.choice(wrong_closers)
            if len(seq_list) + 1 < min_len:
                need = (min_len - 1) - len(seq_list)
                seq_list.extend(list(_padding_valid_pairs(rule_pack, need, rng)))
            if len(seq_list) + 1 > max_len:
                continue
            seq_list.append(wrong)
            seq = ''.join(seq_list)
            if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == len(seq):
                return seq
            continue

        elif target_type == 'unclosed':
            # 安全前缀 + 开括号若干，不闭合
            seq_list = list(safe_prefix)
            W = 0; G = 0; stack: List[str] = []
            added = 0
            while len(seq_list) < max_len:
                candidates = [op for op in OPENERS
                              if not will_over_w(W, W_OPEN[op])
                              and not will_over_g(G, (G_OPEN[op] if active_in_g.get(op, False) else 0))]
                if not candidates:
                    break
                ch = rng.choice(candidates)
                seq_list.append(ch); stack.append(ch)
                W += W_OPEN[ch]
                G += (G_OPEN[ch] if active_in_g.get(ch, False) else 0)
                added += 1
                if added >= 2 and rng.random() < 0.6:
                    break
            if len(seq_list) < min_len:
                need = min_len - len(seq_list)
                pad2 = _padding_valid_pairs(rule_pack, need, rng)
                tmp = seq_list + list(pad2)
                if len(tmp) < max_len:
                    candidates = [op for op in OPENERS
                                  if not will_over_w(W, W_OPEN[op])
                                  and not will_over_g(G, (G_OPEN[op] if active_in_g.get(op, False) else 0))]
                    if candidates:
                        ch = rng.choice(candidates)
                        tmp.append(ch)
                        seq_list = tmp
                    else:
                        continue
                else:
                    continue
            seq = ''.join(seq_list)
            if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == len(seq) + 1:
                return seq
            continue

        elif target_type == 'early_close':
            # 仅在min_err_pos==1时可能出现；此处保留
            first = rng.choice(CLOSERS)
            rest_len_min = max(0, min_len - 1)
            rest_len_max = max(0, max_len - 1)
            if rest_len_min > rest_len_max:
                continue
            tail_len = rng.randint(rest_len_min, rest_len_max)
            tail = _padding_valid_pairs(rule_pack, tail_len, rng)
            seq = first + tail
            if min_len <= len(seq) <= max_len and function_1(seq, rule_pack) == 1:
                return seq
            continue

        else:
            base_len = rng.randint(min_len, min(max_len, min_len + 24))
            seq = _build_valid_pair_sequence(rule_pack, base_len, rng)
            if len(seq) < min_len:
                seq += _padding_valid_pairs(rule_pack, min_len - len(seq), rng)
            if len(seq) <= max_len and function_1(seq, rule_pack) == -1:
                return seq

    # 兜底：生成合法串
    seq = _build_valid_pair_sequence(rule_pack, min_len, random.Random(seed))
    if len(seq) < min_len:
        seq += _padding_valid_pairs(rule_pack, min_len - len(seq), random.Random(seed))
    return seq[:max_len]

# ------------------ 唯一性校验 ------------------

def validate_unique(seq: str, rule_pack_or_T: Union[Dict, int], ans: int, time_limit: float = 180.0) -> bool:
    start = time.time()
    if function_1(seq, rule_pack_or_T) != ans:
        return False
    trials = 1000
    for _ in range(trials):
        if time.time() - start > time_limit:
            break
        if function_1(seq, rule_pack_or_T) != ans:
            return False
    return True