# dyck_language_reasoning_errors_0.py
# function_2: 随机生成一个合法的Dyck括号序列与对应的“思考过程”文本，并在随机位置注入错误，保证答案唯一
# function_1: 根据Dyck规则计算真实栈演化，与题面记录对比，返回错误步骤编号的逗号分隔字符串；若无错误返回空字符串

import random

BRACKET_TYPES = [('(', ')'), ('{', '}'), ('[', ']'), ('<', '>')]


def _gen_balanced_dyck_sequence(pairs_num, types):
    """生成一个随机的平衡括号序列（Dyck序列），支持多种括号类型。"""
    seq_chars = []
    stack = []  # 存储待关闭的右括号，同时记录对应的左括号以便展示栈
    pushes = 0
    pops = 0
    while pushes < pairs_num or pops < pairs_num:
        # 决定是否push或pop
        if pushes < pairs_num and (not stack or random.random() < 0.6):
            # push一个随机类型的左括号
            op_l, op_r = random.choice(types)
            seq_chars.append(op_l)
            stack.append((op_l, op_r))
            pushes += 1
        else:
            # pop一个右括号（必须有栈）
            if stack:
                _, op_r = stack.pop()
                seq_chars.append(op_r)
                pops += 1
            else:
                # 若栈空但仍需pop，强制push
                op_l, op_r = random.choice(types)
                seq_chars.append(op_l)
                stack.append((op_l, op_r))
                pushes += 1
    return ''.join(seq_chars)


def _compute_correct_stack_repr(seq_chars):
    """根据Dyck语言规则，逐字符计算栈的正确文本表示。"""
    pair_map = {')': '(', ']': '[', '}': '{', '>': '<'}
    open_set = set(['(', '{', '[', '<'])
    stack = []
    result = []
    for ch in seq_chars:
        if ch in open_set:
            stack.append(ch)
        else:
            # 闭括号：栈顶应匹配
            if stack and stack[-1] == pair_map.get(ch, ''):
                stack.pop()
            else:
                # 若不匹配（理论上不会，因为我们生成的是合法Dyck序列），做健壮处理
                if stack:
                    stack.pop()
        result.append('空' if not stack else ''.join(stack))
    return result


def _mutate_stack_repr(correct_repr, types):
    """生成一个与correct_repr不同的错误栈文本。"""
    if correct_repr == '空':
        # 生成一个非空栈文本
        op_l_choices = [t[0] for t in types]
        length = random.randint(1, 3)
        return ''.join(random.choice(op_l_choices) for _ in range(length))
    else:
        # 对非空文本进行微小扰动：替换/增加/删除一个括号
        op_l_choices = [t[0] for t in types]
        s = list(correct_repr)
        choice = random.choice(['replace', 'append', 'drop'])
        if choice == 'replace':
            idx = random.randint(0, len(s) - 1)
            new_char = random.choice(op_l_choices)
            # 保证不同
            tries = 0
            while new_char == s[idx] and tries < 5:
                new_char = random.choice(op_l_choices)
                tries += 1
            s[idx] = new_char
        elif choice == 'append':
            s.append(random.choice(op_l_choices))
        else:  # drop
            # 若长度为1，替换成不同字符以保持与原不同
            if len(s) == 1:
                s[0] = random.choice([c for c in op_l_choices if c != s[0]])
            else:
                del s[random.randint(0, len(s) - 1)]
        mutated = ''.join(s)
        if mutated == correct_repr:
            # 兜底：追加一个不同字符
            mutated += random.choice(op_l_choices)
        return mutated


def function_2():
    """
    随机生成题目实例：
      - 随机选择括号类型子集与对数
      - 生成合法Dyck序列
      - 计算正确栈演化，并随机注入错误，保证答案唯一（至少1处错误）
      - 构造思考过程的文本行与各步数据
    返回一个dict，包含：seq, thought_lines, step_indices, step_chars, step_stacks
    """
    # 随机选择括号类型（2~4种）
    types_num = random.randint(2, 4)
    types = random.sample(BRACKET_TYPES, types_num)

    # 随机选择括号对数（6~20）
    pairs_num = random.randint(6, 20)

    # 生成合法Dyck序列
    seq = _gen_balanced_dyck_sequence(pairs_num, types)
    seq_chars = list(seq)

    # 计算正确的栈文本
    correct_stacks = _compute_correct_stack_repr(seq_chars)

    # 决定错误数量（至少1处，最多len(seq)//4）
    max_err = max(1, len(seq_chars) // 4)
    err_count = random.randint(1, max_err)

    # 随机选择错误位置（在处理字符的步骤内）
    err_positions = sorted(random.sample(range(len(seq_chars)), err_count))

    # 根据正确栈生成记录栈文本，并在错误位置注入错误
    recorded_stacks = correct_stacks[:]
    for pos in err_positions:
        recorded_stacks[pos] = _mutate_stack_repr(correct_stacks[pos], types)
        # 确保确实不同
        if recorded_stacks[pos] == correct_stacks[pos]:
            recorded_stacks[pos] = _mutate_stack_repr(correct_stacks[pos], types)

    # 思考过程行的构造
    thought_lines = []
    thought_lines.append('Thought 1: 我们应该逐个处理输入并跟踪栈的配置。')
    thought_lines.append('Thought 2: 栈: 空')

    # 步骤编号从3开始，对应每个字符处理
    step_indices = []
    step_chars = []
    step_stacks = []
    for i, ch in enumerate(seq_chars):
        idx = i + 3
        step_indices.append(idx)
        step_chars.append(ch)
        step_stacks.append(recorded_stacks[i])
        # 格式如：Thought 3: ( ; 栈: (
        thought_lines.append(f"Thought {idx}: {ch} ; 栈: {recorded_stacks[i]}")

    return {
        'seq': seq,
        'thought_lines': thought_lines,
        'step_indices': step_indices,
        'step_chars': step_chars,
        'step_stacks': step_stacks
    }


def function_1(seq, step_indices, step_chars, step_stacks):
    """
    计算答案：对比真实栈与题面记录栈，收集所有不一致的“思考过程N”编号。
    若无错误，返回空字符串""；有错误返回逗号分隔字符串，如 "11,15,18"。
    """
    # 真实栈演化
    correct_stacks = _compute_correct_stack_repr(step_chars)

    errors = []
    for i, (idx, recorded) in enumerate(zip(step_indices, step_stacks)):
        if recorded != correct_stacks[i]:
            errors.append(idx)

    # 保证唯一答案：根据随机注入错误的位置，errors天然唯一
    return ','.join(map(str, errors)) if errors else ""