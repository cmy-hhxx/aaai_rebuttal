# dyck_language_errors_0.py
# 提供括号序列错误位置分析与随机生成的工具函数
import random

def function_1(seq: str, bracket_pairs):
    """
    计算括号序列的第一个错误位置（1为起始索引）。
    规则：
      - 遇到开括号：入栈
      - 遇到闭括号：需匹配栈顶对应类型，否则该位置即为错误
      - 遍历结束后栈非空：错误位置为 len(seq) + 1
      - 序列完全合法：返回 -1
    """
    opens = {op for op, _ in bracket_pairs}
    close_map = {cl: op for op, cl in bracket_pairs}

    stack = []
    for i, ch in enumerate(seq, start=1):
        if ch in opens:
            stack.append(ch)
        elif ch in close_map:
            if not stack:
                return i  # 栈空却遇到闭括号
            if stack[-1] != close_map[ch]:
                return i  # 类型不匹配
            stack.pop()
        else:
            return i  # 非法字符

    # 末尾仍有未闭合括号
    if stack:
        return len(seq) + 1
    return -1


def function_2(seq: str, bracket_pairs, expected: int) -> bool:
    """
    校验 function_1 的结果是否等于期望值。
    用于 YAML 中的答案断言。
    """
    return function_1(seq, bracket_pairs) == expected


def _build_valid_sequence(N: int, bracket_pairs):
    """
    构造一个长度为N的合法括号序列（N需为偶数），尽量包含四种括号类型。
    返回字符串（合法序列）。
    """
    assert N % 2 == 0 and N >= 2
    opens = [op for op, _ in bracket_pairs]
    closes = {op: cl for op, cl in bracket_pairs}

    seq = []
    stack = []

    pairs_target = N // 2
    # 先强制引入4种类型（若可行）
    forced = min(4, pairs_target)
    for i in range(forced):
        op = opens[i % len(opens)]
        seq.append(op)
        stack.append(op)

    open_cnt = forced
    close_cnt = 0

    while len(seq) < N:
        # 若还有可开括号，随机决定开或关
        can_open = open_cnt < pairs_target
        can_close = len(stack) > 0
        # 保证最终能关闭：如果剩余位置不足以关闭现有栈，则优先关闭
        remaining = N - len(seq)
        must_close = can_close and remaining <= len(stack)

        if must_close or (can_close and random.random() < 0.4 and remaining > len(stack)):
            # 关闭栈顶
            top = stack.pop()
            seq.append(closes[top])
            close_cnt += 1
        elif can_open:
            op = random.choice(opens)
            seq.append(op)
            stack.append(op)
            open_cnt += 1
        else:
            # 只能关闭
            top = stack.pop()
            seq.append(closes[top])
            close_cnt += 1

    # 保险：关闭所有未闭合（理论上此时stack应已空）
    while stack and len(seq) < N:
        top = stack.pop()
        seq.append(closes[top])

    return "".join(seq)


def gen_seq(length: int, bracket_pairs, make_valid: bool):
    """
    随机生成括号序列与其唯一答案（正向：先随机产生输入，再计算答案）。
    - 当 make_valid 为 True 且长度为偶数：生成合法序列，答案为-1。
    - 当 make_valid 为 True 且长度为奇数：无法合法，只能生成“末尾未闭合”的序列，答案为 length+1。
    - 当 make_valid 为 False：随机生成一个首错位置在中间的非法序列（如类型不匹配或栈空遇闭括号），答案为该首错位置。
    返回 (sequence_str, answer_int)
    """
    opens = [op for op, _ in bracket_pairs]
    closes = {op: cl for op, cl in bracket_pairs}
    close_to_open = {cl: op for op, cl in bracket_pairs}

    if make_valid and length % 2 == 0:
        seq = _build_valid_sequence(length, bracket_pairs)
        return seq, -1

    if make_valid and length % 2 == 1:
        # 末尾未闭合：构造一个长度为 length-1 的合法前缀，再追加1个开括号
        prefix_len = length - 1
        prefix = _build_valid_sequence(prefix_len if prefix_len % 2 == 0 else prefix_len - 1, bracket_pairs)
        # 保障长度恰好为 length
        seq = prefix
        if len(seq) < length:
            seq += random.choice(opens)
        return seq, length + 1

    # 非法序列：在某个位置注入首错
    # 先构造一个合法前缀（至少长度1），再在pos位置制造错误
    # 合法前缀长度随机取 [0, length-1]（为保证明显错误，建议前缀非负）
    prefix_len = random.randint(0, max(0, length - 2))
    if prefix_len % 2 == 1:
        prefix_len = max(0, prefix_len - 1)  # 合法前缀长度取偶数以便构造平衡序列

    prefix = _build_valid_sequence(prefix_len if prefix_len >= 2 else (2 if length >= 2 else 0), bracket_pairs) if prefix_len > 0 else ""
    stack = []
    for ch in prefix:
        if ch in opens:
            stack.append(ch)
        else:
            # ch must be a closer
            if stack and stack[-1] == close_to_open[ch]:
                stack.pop()
            else:
                # 若前缀内部已不合法，则重新生成前缀（极少发生）
                prefix = _build_valid_sequence(2, bracket_pairs) if length >= 2 else ""
                stack = []
                for c in prefix:
                    if c in opens:
                        stack.append(c)
                    else:
                        stack.pop()

    # 选定错误位置
    pos = len(prefix) + 1  # 1-based
    seq_list = list(prefix)

    # 制造错误：如果栈为空，直接放置任意闭括号；否则放置与栈顶不匹配的闭括号
    if not stack:
        bad_close = random.choice([cl for _, cl in bracket_pairs])
        seq_list.append(bad_close)
    else:
        top = stack[-1]
        bad_close_choices = [cl for op, cl in bracket_pairs if op != top]
        bad_close = random.choice(bad_close_choices)
        seq_list.append(bad_close)

    # 填充剩余位置（不影响首错位置的唯一性）
    remaining = length - len(seq_list)
    for _ in range(remaining):
        # 随机填充括号即可
        if random.random() < 0.5:
            seq_list.append(random.choice(opens))
        else:
            seq_list.append(random.choice([cl for _, cl in bracket_pairs]))

    seq = "".join(seq_list)
    return seq, pos