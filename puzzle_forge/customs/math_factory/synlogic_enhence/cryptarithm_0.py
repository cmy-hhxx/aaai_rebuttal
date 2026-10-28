# cryptarithm_1.py
# -*- coding: utf-8 -*-
"""
高阶泛化版：逆向生成 + 多元复合约束 + 高效唯一性验证（< 3分钟）。

核心函数
- function_1(...): 按参数随机生成满足两条算式与若干约束的实例；若 require_unique=True，则通过内置回溯验证唯一性，
  不唯一时尝试追加约束或重生成；返回 words, values, ops, mapping(仅出现字母), constraints_desc, ops_text, unique_label 等。
- function_2(mapping, order): 将映射格式化为'A=1, B=2, ...'字符串（仅包含出现的字母）。

安全与深度改进：
- 同余约束安全构造：先算 need，再从题面出现字母中找映射为 need 的 k，若无则放弃并用 SumDigits 约束兜底，避免 KeyError。
- 新增“九余数”约束（mod 9）：在完整校验时强制，题面中解释其含义，提升推理深度。
"""

import random
import time
from typing import Dict, List, Optional, Tuple, Set


def _digits_to_word(n: int, digit_to_letter: Dict[int, str]) -> str:
    """将整数n按digit_to_letter映射转换为字母词（不含前导零）。"""
    return ''.join(digit_to_letter[int(ch)] for ch in str(n))


def _rand_num(length_min: int, length_max: int) -> int:
    """生成指定长度范围的随机正整数，首位非零。"""
    length_min = max(1, length_min)
    length_max = max(length_min, length_max)
    L = random.randint(length_min, length_max)
    first = random.randint(1, 9)
    rest = [random.randint(0, 9) for _ in range(L - 1)]
    val = first
    for d in rest:
        val = val * 10 + d
    return val


def _squares_by_len(L: int) -> List[int]:
    """返回指定位数的完全平方数列表。"""
    if L <= 0:
        return []
    low, high = 10 ** (L - 1), 10 ** L - 1
    res = []
    i = int(low ** 0.5)
    if i * i < low:
        i += 1
    while i * i <= high:
        res.append(i * i)
        i += 1
    return res


def _digit_set_of_numbers(nums: List[int]) -> Set[int]:
    s: Set[int] = set()
    for x in nums:
        for ch in str(x):
            s.add(int(ch))
    return s


def _word_letters(word: str) -> Set[str]:
    return set(word)


def _sum_digits(n: int) -> int:
    return sum(int(ch) for ch in str(n))


def _build_constraints_text(extras: List[Dict], w_names: Dict[str, str]) -> str:
    """
    将额外约束列表转为自然语言文本。
    extras 元素示例：
    - {'type':'even','letter':'A'}
    - {'type':'prime','letter':'B'}
    - {'type':'cong','k':'K','m':'M','c':'C','op':'+'}
    - {'type':'sds','word':'w5','target': 23}
    - {'type':'mod9','eq':1,'sign':'+'}  # 表示等式1按 mod9 成立
    """
    texts = []
    for c in extras:
        if c['type'] == 'even':
            texts.append(f"{c['letter']}对应的数字为偶数")
        elif c['type'] == 'prime':
            texts.append(f"{c['letter']}对应的数字属于[2,3,5,7]")
        elif c['type'] == 'cong':
            op = c.get('op', '+')
            texts.append(f"同余约束：{c['k']}≡({c['m']} {op} {c['c']}) mod 10")
        elif c['type'] == 'sds':
            wn = w_names.get(c['word'], c['word'])
            texts.append(f"SumDigits({wn})={c['target']}")
        elif c['type'] == 'mod9':
            # eq: 1 或 2；sign: '+'/'-'
            if c.get('eq', 1) == 1:
                texts.append(f"九余数约束：SumDigitsMod9({w_names['w1']}) {c.get('sign','+')} SumDigitsMod9({w_names['w2']}) ≡ SumDigitsMod9({w_names['w3']}) (mod 9)")
            else:
                texts.append(f"九余数约束：SumDigitsMod9({w_names['w3']}) {c.get('sign','+')} SumDigitsMod9({w_names['w4']}) ≡ SumDigitsMod9({w_names['w5']}) (mod 9)")
    if not texts:
        return '无'
    return '；'.join(texts) + '。'


def _unique_solver(
    words: List[str],
    values: List[int],
    ops: List[str],
    extras: List[Dict],
    time_limit_sec: int
) -> Tuple[str, int]:
    """
    回溯求解，验证唯一性。
    输入：
      - words: [w1, w2, w3, w4, w5]
      - values: 对应数值 [v1..v5]
      - ops: ['+'|'-', '+'|'-'] 表示原始两条式子中的运算符
      - extras: 额外约束列表
    输出：
      - unique_label: 'unique' 或 'multiple'
      - sol_count: 求得的解数量（最多返回2）
    """
    deadline = time.time() + max(1, min(180, time_limit_sec))

    # 转加法三元组
    def to_addition(op, a, b, c):
        return (a, b, c) if op == '+' else (b, c, a)

    eq1 = to_addition(ops[0], words[0], words[1], words[2])
    eq2 = to_addition(ops[1], words[2], words[3], words[4])

    # 字母集合与前导非零集合
    letters: Set[str] = set().union(*map(_word_letters, words))
    leading_letters = {w[0] for w in words}

    # 固定映射（来自 w4 与 values[3] 的逐位绑定）
    fixed: Dict[str, int] = {}
    digits_w4 = list(map(int, str(values[3])))
    if len(digits_w4) != len(words[3]):
        return ('multiple', 2)
    for L, d in zip(words[3], digits_w4):
        if L in fixed and fixed[L] != d:
            return ('multiple', 2)
        fixed[L] = d

    # 解析额外约束
    even_letters: Set[str] = set()
    prime_letters: Set[str] = set()
    cong_constraints: List[Tuple[str, str, str, str]] = []  # (k,m,c,op)
    sds_constraints: List[Tuple[str, int]] = []  # (word_name,target)
    mod9_constraints: List[Tuple[int, str]] = []  # (eq_index, sign)
    for c in extras:
        if c['type'] == 'even':
            even_letters.add(c['letter'])
        elif c['type'] == 'prime':
            prime_letters.add(c['letter'])
        elif c['type'] == 'cong':
            cong_constraints.append((c['k'], c['m'], c['c'], c.get('op', '+')))
        elif c['type'] == 'sds':
            sds_constraints.append((c['word'], c['target']))
        elif c['type'] == 'mod9':
            mod9_constraints.append((c.get('eq', 1), c.get('sign', '+')))

    # SumDigits 的字母频次
    word_letters_list = {f"w{i+1}": list(words[i]) for i in range(5)}
    word_coeff: Dict[str, Dict[str, int]] = {}
    for name, ls in word_letters_list.items():
        cnt: Dict[str, int] = {}
        for L in ls:
            cnt[L] = cnt.get(L, 0) + 1
        word_coeff[name] = cnt

    # 域初始化
    all_digits = set(range(10))
    prime_set = {2, 3, 5, 7}
    domains: Dict[str, Set[int]] = {}
    for L in letters:
        if L in fixed:
            domains[L] = {fixed[L]}
        else:
            dom = set(all_digits)
            if L in leading_letters:
                dom.discard(0)
            if L in even_letters:
                dom = {d for d in dom if d % 2 == 0}
            if L in prime_letters:
                dom = {d for d in dom if d in prime_set}
            domains[L] = dom
        if not domains[L]:
            return ('multiple', 2)

    # 固定冲突检查
    if len({d for d in fixed.values()}) != len(fixed):
        return ('multiple', 2)

    # 同余局部剪枝
    def check_congruence_partial(current: Dict[str, int]) -> bool:
        inv_used = set(current.values())
        for (k, m, c, op) in cong_constraints:
            mv = current.get(m, None)
            cv = current.get(c, None)
            kv = current.get(k, None)
            if mv is not None and cv is not None:
                need = (mv + cv) % 10 if op == '+' else (mv - cv) % 10
                if kv is not None:
                    if kv != need:
                        return False
                else:
                    if need in inv_used:
                        return False
        return True

    # 数位和上下界剪枝
    def check_sds_bounds(current: Dict[str, int]) -> bool:
        used = set(current.values())
        for (wname, target) in sds_constraints:
            coeff = word_coeff[wname]
            sum_assigned = 0
            min_extra = 0
            max_extra = 0
            for L, c in coeff.items():
                if L in current:
                    sum_assigned += c * current[L]
                else:
                    dom = domains[L] - used
                    if not dom:
                        return False
                    min_extra += c * min(dom)
                    max_extra += c * max(dom)
            if not (sum_assigned + min_extra <= target <= sum_assigned + max_extra):
                return False
        return True

    # 完整验证
    def check_full(current: Dict[str, int]) -> bool:
        def word_to_num(w: str) -> int:
            return int(''.join(str(current[L]) for L in w))
        for w in words:
            if current[w[0]] == 0:
                return False
        for (wname, target) in sds_constraints:
            widx = int(wname[1]) - 1
            if _sum_digits(word_to_num(words[widx])) != target:
                return False
        # mod 9 约束
        for (eq_idx, sign) in mod9_constraints:
            if eq_idx == 1:
                a, b, c = words[0], words[1], words[2]
            else:
                a, b, c = words[2], words[3], words[4]
            da = _sum_digits(word_to_num(a)) % 9
            db = _sum_digits(word_to_num(b)) % 9
            dc = _sum_digits(word_to_num(c)) % 9
            if sign == '+':
                if (da + db) % 9 != dc % 9:
                    return False
            else:
                if (da - db) % 9 != dc % 9:
                    return False
        # 等式：转加法为 A + B = C
        def ok_eq(triple) -> bool:
            a, b, c = triple
            return word_to_num(a) + word_to_num(b) == word_to_num(c)
        return ok_eq((words[0], words[1], words[2]) if ops[0] == '+' else (words[1], words[2], words[0])) and \
               ok_eq((words[2], words[3], words[4]) if ops[1] == '+' else (words[4], words[3], words[2]))

    # MRV 选取
    def select_unassigned(current: Dict[str, int]) -> Optional[str]:
        best_L, best_size = None, 10**9
        used = set(current.values())
        for L in letters:
            if L in current:
                continue
            dom = domains[L] - used
            if L in leading_letters:
                dom = {d for d in dom if d != 0}
            s = len(dom)
            if s < best_size:
                best_L, best_size = L, s
        return best_L

    # 初始化赋值（固定字母先赋）
    assigned: Dict[str, int] = {}
    for L, d in fixed.items():
        assigned[L] = d

    sol_count = 0
    deadline = time.time() + max(1, min(180, time_limit_sec))

    def dfs(current: Dict[str, int]) -> None:
        nonlocal sol_count
        if time.time() > deadline or sol_count >= 2:
            return
        if len(current) == len(letters):
            if check_full(current):
                sol_count += 1
            return
        L = select_unassigned(current)
        if L is None:
            return
        used = set(current.values())
        dom = domains[L] - used
        if L in leading_letters:
            dom = {d for d in dom if d != 0}
        for d in sorted(dom):
            current[L] = d
            if check_congruence_partial(current) and check_sds_bounds(current):
                dfs(current)
            del current[L]
            if sol_count >= 2 or time.time() > deadline:
                return

    dfs(dict(assigned))
    label = 'unique' if sol_count == 1 else ('multiple' if sol_count >= 2 else 'multiple')
    return (label, sol_count)


def function_1(
    letter_pool_size: int = 10,
    gen_attempts: int = 4,
    w1_len_min: int = 4,
    w1_len_max: int = 6,
    w2_len_min: int = 4,
    w2_len_max: int = 6,
    square_len_min: int = 2,
    square_len_max: int = 3,
    extra_constraints_min: int = 2,
    extra_constraints_max: int = 4,
    used_digits_max: int = 7,
    time_limit_sec: int = 120,
    require_unique: bool = True
) -> Dict:
    """
    生成并验证实例，必要时追加约束以寻求唯一性。返回结构：
    {
      'status': 'SAT',
      'words': [w1..w5],
      'values': [v1..v5],
      'ops': ['+|-', '+|-'],
      'mapping': {letter: digit},           # 仅包含题面出现的字母
      'constraints_desc': <str>,
      'ops_text': <str>,
      'unique_label': 'unique|multiple'
    }
    """
    time_limit_sec = max(1, min(180, time_limit_sec))
    deadline = time.time() + time_limit_sec

    all_letters = [chr(ord('A') + i) for i in range(26)]
    digits_all = list(range(10))

    def try_build_instance() -> Optional[Dict]:
        letters = random.sample(all_letters, 10)
        random.shuffle(digits_all)
        letter_to_digit = {letters[i]: digits_all[i] for i in range(10)}
        digit_to_letter = {d: L for L, d in letter_to_digit.items()}

        op1 = random.choice(['+', '-'])
        op2 = random.choice(['+', '-'])

        sq_len = random.randint(square_len_min, square_len_max)
        sq_list = _squares_by_len(sq_len)
        if not sq_list:
            return None

        for _ in range(40):
            v1 = _rand_num(w1_len_min, w1_len_max)
            v2 = _rand_num(w2_len_min, w2_len_max)

            if op1 == '+':
                v3 = v1 + v2
            else:
                if v1 <= v2:
                    v1, v2 = v2, v1
                    if v1 == v2:
                        v1 += 1
                v3 = v1 - v2

            v4 = random.choice(sq_list)

            if op2 == '+':
                v5 = v3 + v4
            else:
                if v3 <= v4:
                    smaller = [s for s in sq_list if s < v3]
                    if not smaller:
                        continue
                    v4 = random.choice(smaller)
                v5 = v3 - v4

            used_digits = _digit_set_of_numbers([v1, v2, v3, v4, v5])
            if len(used_digits) > used_digits_max:
                continue

            w1 = _digits_to_word(v1, digit_to_letter)
            w2 = _digits_to_word(v2, digit_to_letter)
            w3 = _digits_to_word(v3, digit_to_letter)
            w4 = _digits_to_word(v4, digit_to_letter)
            w5 = _digits_to_word(v5, digit_to_letter)

            if any(letter_to_digit[w[0]] == 0 for w in [w1, w2, w3, w4, w5]):
                continue

            return {
                'words': [w1, w2, w3, w4, w5],
                'values': [v1, v2, v3, v4, v5],
                'ops': [op1, op2],
                'letter_to_digit': letter_to_digit
            }
        return None

    def sample_extras(words: List[str], mapping: Dict[str, int], values: List[int], kmin: int, kmax: int) -> List[Dict]:
        """
        安全生成额外约束：
        - 必加：一条 SumDigits（w3 或 w5）。
        - 尝试加入一条同余约束（安全：仅当存在映射到 need 的字母且不与 m,c 重合）。
        - 以一定概率加入一条 mod9 约束（九余数），提升深度。
        - 再随机补足偶数/素数/SumDigits 等约束至目标数量。
        """
        Ls = sorted(set().union(*map(_word_letters, words)))
        extras: List[Dict] = []
        k_target = random.randint(kmin, kmax)

        # 必加：SumDigits
        idx = random.choice([2, 4])  # w3 或 w5
        extras.append({'type': 'sds', 'word': f"w{idx+1}", 'target': _sum_digits(values[idx])})

        # 安全同余
        added_cong = False
        for _ in range(20):
            if len(Ls) < 3:
                break
            m, c = random.sample(Ls, 2)
            op = random.choice(['+', '-'])
            need = (mapping[m] + mapping[c]) % 10 if op == '+' else (mapping[m] - mapping[c]) % 10
            cand_k = [x for x in Ls if mapping[x] == need and x not in {m, c}]
            if cand_k:
                k = random.choice(cand_k)
                extras.append({'type': 'cong', 'k': k, 'm': m, 'c': c, 'op': op})
                added_cong = True
                break
        # mod9：以50%概率加入一条（任选等式1或2，符号沿用原op）
        if random.random() < 0.5:
            eq_idx = random.choice([1, 2])
            sign = '+' if (eq_idx == 1 and ops[0] == '+') or (eq_idx == 2 and ops[1] == '+') else '-'
            extras.append({'type': 'mod9', 'eq': eq_idx, 'sign': sign})

        # 若未能加入同余，兜底再加一条 SumDigits 提升信息量
        if not added_cong:
            idx2 = random.choice([0, 1, 2, 4])  # w1/w2/w3/w5
            extras.append({'type': 'sds', 'word': f"w{idx2+1}", 'target': _sum_digits(values[idx2])})

        # 补足其余随机项
        pool = ['even', 'prime', 'sds']
        random.shuffle(pool)
        for t in pool:
            if len(extras) >= k_target:
                break
            if t == 'even':
                cand = [L for L in Ls if mapping[L] % 2 == 0 and all(not (e.get('type') == 'even' and e.get('letter') == L) for e in extras)]
                if cand:
                    extras.append({'type': 'even', 'letter': random.choice(cand)})
            elif t == 'prime':
                cand = [L for L in Ls if mapping[L] in {2, 3, 5, 7} and all(not (e.get('type') == 'prime' and e.get('letter') == L) for e in extras)]
                if cand:
                    extras.append({'type': 'prime', 'letter': random.choice(cand)})
            elif t == 'sds':
                idx3 = random.choice([0, 1, 2, 4])
                extras.append({'type': 'sds', 'word': f"w{idx3+1}", 'target': _sum_digits(values[idx3])})
        return extras

    # 主循环
    base = None
    while time.time() < deadline:
        base = try_build_instance()
        if not base:
            continue
        words = base['words']
        values = base['values']
        ops = base['ops']
        letter_to_digit = base['letter_to_digit']

        used_letters = sorted(set().union(*map(_word_letters, words)))
        mapping_used = {L: letter_to_digit[L] for L in used_letters}

        extras = sample_extras(words, mapping_used, values, extra_constraints_min, extra_constraints_max)

        # 唯一性验证
        label, _ = _unique_solver(words, values, ops, extras, time_limit_sec=int(deadline - time.time()))
        if label == 'unique' or not require_unique:
            w_names = {'w1': words[0], 'w2': words[1], 'w3': words[2], 'w4': words[3], 'w5': words[4]}
            ctext = _build_constraints_text(extras, w_names)
            # 多风格运算描述
            style = random.choice([0, 1, 2])
            if style == 0:
                ops_text = f"运算关系：{words[0]} {ops[0]} {words[1]} = {words[2]}，以及 {words[2]} {ops[1]} {words[3]} = {words[4]}。"
            elif style == 1:
                ops_text = f"等式如下：{words[0]} {ops[0]} {words[1]} 等于 {words[2]}；同时 {words[2]} {ops[1]} {words[3]} 等于 {words[4]}。"
            else:
                ops_text = f"{words[0]} 与 {words[1]} 经 '{ops[0]}' 运算得到 {words[2]}；{words[2]} 与 {words[3]} 经 '{ops[1]}' 运算得到 {words[4]}。"
            return {
                'status': 'SAT',
                'words': words,
                'values': values,
                'ops': ops,
                'mapping': mapping_used,
                'constraints_desc': ctext,
                'ops_text': ops_text,
                'unique_label': label
            }

        # 若不唯一，追加一条 SumDigits(w5) 或 SumDigits(w3) 再试
        added = False
        if all(not (c.get('type') == 'sds' and c.get('word') == 'w5') for c in extras):
            extras.append({'type': 'sds', 'word': 'w5', 'target': _sum_digits(values[4])})
            added = True
        elif all(not (c.get('type') == 'sds' and c.get('word') == 'w3') for c in extras):
            extras.append({'type': 'sds', 'word': 'w3', 'target': _sum_digits(values[2])})
            added = True

        if added and time.time() < deadline:
            label2, _ = _unique_solver(words, values, ops, extras, time_limit_sec=int(deadline - time.time()))
            if label2 == 'unique' or not require_unique:
                w_names = {'w1': words[0], 'w2': words[1], 'w3': words[2], 'w4': words[3], 'w5': words[4]}
                ctext = _build_constraints_text(extras, w_names)
                style = random.choice([0, 1, 2])
                if style == 0:
                    ops_text = f"运算关系：{words[0]} {ops[0]} {words[1]} = {words[2]}，以及 {words[2]} {ops[1]} {words[3]} = {words[4]}。"
                elif style == 1:
                    ops_text = f"等式如下：{words[0]} {ops[0]} {words[1]} 等于 {words[2]}；同时 {words[2]} {ops[1]} {words[3]} 等于 {words[4]}。"
                else:
                    ops_text = f"{words[0]} 与 {words[1]} 经 '{ops[0]}' 运算得到 {words[2]}；{words[2]} 与 {words[3]} 经 '{ops[1]}' 运算得到 {words[4]}。"
                return {
                    'status': 'SAT',
                    'words': words,
                    'values': values,
                    'ops': ops,
                    'mapping': mapping_used,
                    'constraints_desc': ctext,
                    'ops_text': ops_text,
                    'unique_label': label2
                }
        # 重生成
        continue

    # 超时兜底：返回最后一次有效（不保证唯一）
    if base:
        words = base['words']; values = base['values']; ops = base['ops']
        used_letters = sorted(set().union(*map(_word_letters, words)))
        mapping_used = {L: base['letter_to_digit'][L] for L in used_letters}
        extras = [{'type': 'sds', 'word': 'w5', 'target': _sum_digits(values[4])}]
        w_names = {'w1': words[0], 'w2': words[1], 'w3': words[2], 'w4': words[3], 'w5': words[4]}
        ctext = _build_constraints_text(extras, w_names)
        ops_text = f"运算关系：{words[0]} {ops[0]} {words[1]} = {words[2]}，以及 {words[2]} {ops[1]} {words[3]} = {words[4]}。"
        return {
            'status': 'SAT',
            'words': words,
            'values': values,
            'ops': ops,
            'mapping': mapping_used,
            'constraints_desc': ctext,
            'ops_text': ops_text,
            'unique_label': 'multiple'
        }
    raise RuntimeError("Failed to generate a valid instance within time limit.")


def function_2(mapping: Optional[Dict[str, int]], order: Optional[List[str]] = None) -> str:
    """
    将字母-数字映射格式化为字符串（仅包含题面出现的字母）。
    - 若mapping为空或None，返回空字符串。
    - 若指定order（字母顺序），按该顺序输出；否则按键名升序。
    """
    if not mapping:
        return ''
    keys = order if order is not None else sorted(mapping.keys())
    parts = []
    for k in keys:
        if k in mapping:
            parts.append(f"{k}={mapping[k]}")
    return ', '.join(parts)