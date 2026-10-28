# dyck_language_0.py
# 提供三个函数：
# - generate_random_prefix(min_len, max_len): 随机生成合法括号前缀，支持 () [] {} <>，无非法关闭，且默认确保未完全闭合
# - complete_sequence(seq): 对给定前缀进行唯一补全，只在末尾追加所需右括号，得到合法Dyck串
# - validate_sequence(seq): 校验完整串是否合法且正确闭合

import random

OPEN_TO_CLOSE = {
    '(': ')',
    '[': ']',
    '{': '}',
    '<': '>',
}
CLOSE_TO_OPEN = {v: k for k, v in OPEN_TO_CLOSE.items()}
OPEN_SET = set(OPEN_TO_CLOSE.keys())
CLOSE_SET = set(CLOSE_TO_OPEN.keys())


def _is_valid_prefix(seq: str) -> bool:
    """校验前缀是否无非法关闭（允许未闭合）。"""
    stack = []
    for ch in seq:
        if ch in OPEN_SET:
            stack.append(ch)
        elif ch in CLOSE_SET:
            if not stack or stack[-1] != CLOSE_TO_OPEN[ch]:
                return False
            stack.pop()
        else:
            return False
    return True


def complete_sequence(seq: str) -> str:
    """对给定括号前缀进行唯一补全，仅在末尾追加必需右括号，得到合法Dyck串。"""
    if not _is_valid_prefix(seq):
        raise ValueError("Invalid prefix: contains mismatched closing or invalid characters.")

    stack = []
    for ch in seq:
        if ch in OPEN_SET:
            stack.append(ch)
        else:
            if not stack or stack[-1] != CLOSE_TO_OPEN[ch]:
                raise ValueError("Invalid sequence: mismatched closing bracket in prefix.")
            stack.pop()

    completion = []
    while stack:
        completion.append(OPEN_TO_CLOSE[stack.pop()])

    return seq + ''.join(completion)


def validate_sequence(seq: str) -> bool:
    """严格校验整个序列是否为合法且正确闭合的Dyck语言串。"""
    stack = []
    for ch in seq:
        if ch in OPEN_SET:
            stack.append(ch)
        elif ch in CLOSE_SET:
            if not stack or stack[-1] != CLOSE_TO_OPEN[ch]:
                return False
            stack.pop()
        else:
            return False
    return len(stack) == 0


def generate_random_prefix(min_len: int, max_len: int) -> str:
    """
    随机生成合法括号前缀（支持四类括号），确保无非法关闭，且默认未完全闭合：
    - 长度在[min_len, max_len]之间
    - 仅使用 () [] {} <> 四类括号
    - 无非法关闭（即任何关闭都匹配栈顶）
    - 至少保留一个未闭合的打开括号，保证答案非空且唯一
    """
    if min_len < 1 or max_len < min_len:
        raise ValueError("Invalid length parameters.")

    L = random.randint(min_len, max_len)
    prefix = []
    stack = []

    # 行为概率：更多打开，适度关闭，避免频繁空栈
    p_open = 0.6

    for i in range(L):
        # 最后一步强制打开，以确保未完全闭合（答案非空）
        if i == L - 1:
            ch_open = random.choice(list(OPEN_SET))
            prefix.append(ch_open)
            stack.append(ch_open)
            continue

        if not stack:
            # 栈空时只能打开
            ch_open = random.choice(list(OPEN_SET))
            prefix.append(ch_open)
            stack.append(ch_open)
        else:
            if random.random() < p_open:
                ch_open = random.choice(list(OPEN_SET))
                prefix.append(ch_open)
                stack.append(ch_open)
            else:
                # 合法关闭：必须关闭栈顶
                top = stack[-1]
                ch_close = OPEN_TO_CLOSE[top]
                prefix.append(ch_close)
                stack.pop()

    # 双保险：若仍意外闭合，追加一个打开括号
    if not stack:
        ch_open = random.choice(list(OPEN_SET))
        prefix.append(ch_open)
        stack.append(ch_open)

    result = ''.join(prefix)
    # 最终保证为合法前缀
    assert _is_valid_prefix(result), "Generated prefix is not valid."
    return result


# 自检
if __name__ == "__main__":
    for _ in range(5):
        pre = generate_random_prefix(5, 15)
        ans = complete_sequence(pre)
        ok = validate_sequence(ans)
        print("prefix:", pre)
        print("completed:", ans, "valid:", ok)
        print("-" * 40)