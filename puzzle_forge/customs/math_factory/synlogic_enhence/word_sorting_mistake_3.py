# word_sorting_mistake_0.py

import random
import re
from typing import List, Dict, Tuple, Union

# -------------------------
# Constants
# -------------------------
VOWELS = set('aeiou')
LETTERS = 'abcdefghijklmnopqrstuvwxyz'
ALLOWED_MODS = [83, 89, 97, 101]

# -------------------------
# Utilities
# -------------------------

def _alpha_pos(ch: str) -> int:
    ch = ch.lower()
    if 'a' <= ch <= 'z':
        return ord(ch) - ord('a') + 1
    raise ValueError(f"Non-alphabet character: {ch!r}")

def _gen_word(length: int) -> str:
    first = random.choice(LETTERS)
    rest = ''.join(random.choice(LETTERS) for _ in range(max(0, length - 1)))
    return (first + rest)

def _ensure_distinct_first_letters(words: List[str], min_distinct: int) -> List[str]:
    if min_distinct <= 1:
        return words
    current = set(w[0] for w in words)
    while len(current) < min_distinct:
        need = random.choice([c for c in LETTERS if c not in current])
        length = random.randint(5, 10)
        w = need + ''.join(random.choice(LETTERS) for _ in range(length - 1))
        if w not in words:
            words.append(w)
            current.add(need)
    return words

def _pick_weighted(weights: List[int]) -> int:
    total = sum(max(0, w) for w in weights)
    if total <= 0:
        return random.randint(0, len(weights) - 1)
    r = random.randint(1, total)
    s = 0
    for i, w in enumerate(weights):
        s += max(0, w)
        if r <= s:
            return i
    return len(weights) - 1

def _vowel_count(w: str) -> int:
    return sum(1 for ch in w if ch in VOWELS)

def _alpha_sum(w: str) -> int:
    return sum(_alpha_pos(ch) for ch in w if 'a' <= ch <= 'z')

def _compute_S1_S2(words: List[str]) -> Tuple[int, int]:
    s1 = sum(_alpha_pos(w[0]) for w in words)
    s2 = sum(len(w) for w in words)
    return s1, s2

def _to_int(x) -> int:
    """
    Robustly convert x to int if possible; raise ValueError if not possible.
    """
    if isinstance(x, int):
        return x
    if isinstance(x, bool):
        raise ValueError("Boolean is not an acceptable mod/value type.")
    try:
        return int(str(x).strip())
    except Exception as e:
        raise ValueError(f"Cannot convert {x!r} to int: {e}")

def compute_hash_value(words: List[str], mod: int) -> int:
    m = _to_int(mod)
    total = sum(_alpha_pos(w[0]) * len(w) for w in words)
    return total % max(1, m)

# 独立校验码 H2：与步骤中的 H（H1）无关
def compute_hash_value_v2(words: List[str], mod: int) -> int:
    """
    H2 = sum((首字母位次 + 末字母位次) * 长度) % mod
    """
    m = _to_int(mod)
    total = 0
    for w in words:
        first = _alpha_pos(w[0])
        last = _alpha_pos(w[-1])
        total += (first + last) * len(w)
    return total % max(1, m)

# -------------------------
# Generators for word list
# -------------------------

def generate_words(word_num: int, word_len_low: int, word_len_high: int,
                   ensure_distinct: bool, min_distinct_first_letters: int) -> List[str]:
    low = min(word_len_low, word_len_high)
    high = max(word_len_low, word_len_high)
    low = max(2, low)
    high = max(low, high)

    seen = set()
    words: List[str] = []
    attempts = 0
    target = max(3, word_num)
    while len(words) < target and attempts < target * 80:
        length = random.randint(low, high)
        w = _gen_word(length).lower()
        if w not in seen:
            seen.add(w)
            words.append(w)
        attempts += 1

    if ensure_distinct:
        words = _ensure_distinct_first_letters(words, max(2, min_distinct_first_letters))
        if len(words) > target:
            groups: Dict[str, List[str]] = {}
            for w in words:
                groups.setdefault(w[0], []).append(w)
            base: List[str] = []
            need = max(2, min_distinct_first_letters)
            for letter in sorted(groups.keys()):
                if len(base) >= need:
                    break
                base.append(groups[letter].pop(0))
            remaining = [w for wl in groups.values() for w in wl]
            random.shuffle(remaining)
            while len(base) < target and remaining:
                base.append(remaining.pop())
            words = base[:target]
    else:
        words = words[:target]
    return list(dict.fromkeys(words))

# -------------------------
# Random controls for steps & error
# -------------------------

def choose_step_num(min_steps: int, max_steps: int) -> int:
    lo = max(4, min(min_steps, max_steps))
    hi = max(lo, max(min_steps, max_steps))
    return random.randint(lo, hi)

def build_error_weights(step_count: int, w0: int, w1: int, w2: int, w3: int, w4: int, w5: int) -> List[int]:
    # Index 0 is "No Error", index i -> error at step i (1-based)
    pool = [max(0, w0)]
    step_weights = [w1, w2, w3, w4, w5]
    for i in range(step_count):
        pool.append(max(0, step_weights[i] if i < len(step_weights) else 1))
    return pool

def choose_error_step_n(weights: List[int], force_error: bool = False) -> int:
    """
    weights[0] -> 'No error'; weights[i] -> error at step i (1-based).
    Return index in 0..N (0 means no error).
    If force_error is True, always pick an index >= 1 according to normalized weights.
    """
    if not weights:
        return 0
    if force_error:
        # Normalize weights from 1..N; if all zeros, fallback to uniform among 1..N
        tail = [max(0, w) for w in weights[1:]]
        if sum(tail) <= 0:
            return random.randint(1, len(weights) - 1)
        total = sum(tail)
        r = random.randint(1, total)
        s = 0
        for i, w in enumerate(tail, start=1):
            s += w
            if r <= s:
                return i
        return len(weights) - 1
    return _pick_weighted(weights)

# -------------------------
# Helpers for deterministic sorting (with tiebreaker)
# -------------------------

def _rule_kind_and_func(rule_desc: str):
    """
    Return (kind, func) where kind in {'lex', 'num'}.
    """
    if rule_desc == '字典序':
        return 'lex', (lambda w: w)
    if rule_desc == '长度':
        return 'num', (lambda w: len(w))
    if rule_desc.startswith('元音数'):
        return 'num', (lambda w: _vowel_count(w))
    if rule_desc == '字母位次和':
        return 'num', (lambda w: _alpha_sum(w))
    if rule_desc == '首字母位次':
        return 'num', (lambda w: _alpha_pos(w[0]))
    return 'lex', (lambda w: w)

def _compute_sorted_with_rule(words: List[str], rule_desc: str, direction: str) -> List[str]:
    """
    Apply deterministic sorting with global tie-breaking rule:
    - For numeric primary keys: 
        asc:  key = (primary, word)
        desc: key = (-primary, word)
    - For lex primary:
        asc: sort by word ascending
        desc: reverse of ascending
    direction in {'升序','降序'}
    """
    kind, func = _rule_kind_and_func(rule_desc)
    wl = [w.lower() for w in words]
    if kind == 'lex':
        base = sorted(wl)
        return base if direction == '升序' else list(reversed(base))
    if direction == '升序':
        return sorted(wl, key=lambda w: (func(w), w))
    return sorted(wl, key=lambda w: (-func(w), w))

# -------------------------
# Step renderers (with optional error injection)
# 标签 ∈ {'映射','排序','分组','筛选','长度映射','摘要','交叉核对','摘要核对','校验码'}
# -------------------------

def _render_map_first_letter(i: int, words: List[str], inject_error: bool) -> str:
    items: List[Tuple[str, str, int]] = [(w, w[0], _alpha_pos(w[0])) for w in words]
    if inject_error:
        et = random.choice(['foreign_word', 'wrong_letter', 'wrong_index', 'missing_word', 'duplicate_word'])
        if et == 'foreign_word':
            fw = ''
            while not fw or fw in words:
                fw = _gen_word(random.randint(5, 10)).lower()
            items.append((fw, fw[0], _alpha_pos(fw[0])))
        elif et == 'wrong_letter' and items:
            j = random.randint(0, len(items) - 1)
            wrong_letter = random.choice([c for c in LETTERS if c != items[j][1]])
            items[j] = (items[j][0], wrong_letter, _alpha_pos(wrong_letter))
        elif et == 'wrong_index' and items:
            j = random.randint(0, len(items) - 1)
            wrong_idx = random.choice([n for n in range(1, 27) if n != _alpha_pos(items[j][1])])
            items[j] = (items[j][0], items[j][1], wrong_idx)
        elif et == 'missing_word' and items:
            j = random.randint(0, len(items) - 1)
            del items[j]
        elif et == 'duplicate_word' and items:
            j = random.randint(0, len(items) - 1)
            items.append(items[j])
    pairs = [f"'{w}': '{l}' ({idx})." for (w, l, idx) in items]
    header = f"思考 {i}|映射:我先查看每个单词的第一个字母并标注其字母位次(a=1,...,z=26)。标注如下: "
    return header + ' ' + ' '.join(pairs)

def _sort_key_and_desc():
    kind = random.choice(['lex', 'length', 'vowels', 'alpha_sum', 'first_pos'])
    if kind == 'lex':
        return (lambda w: w), '字典序'
    if kind == 'length':
        return (lambda w: len(w)), '长度'
    if kind == 'vowels':
        return (lambda w: _vowel_count(w)), '元音数(元音=a,e,i,o,u)'
    if kind == 'alpha_sum':
        return (lambda w: _alpha_sum(w)), '字母位次和'
    return (lambda w: _alpha_pos(w[0])), '首字母位次'

def _normalize_rule_desc(desc: str) -> str:
    if desc.startswith('元音数'):
        return '元音数'
    return desc

def _render_sort(i: int, words: List[str], inject_error: bool) -> str:
    _, rule_desc_raw = _sort_key_and_desc()
    rule_desc = _normalize_rule_desc(rule_desc_raw)
    direction = random.choice(['asc', 'desc'])
    declared_label = '升序' if direction == 'asc' else '降序'
    target = _compute_sorted_with_rule(words, rule_desc, '升序' if direction == 'asc' else '降序')
    shown = target[:]
    if inject_error:
        et = random.choice(['wrong_direction', 'local_swap', 'wrong_key'])
        if et == 'wrong_direction':
            shown = list(reversed(target))
        elif et == 'local_swap' and len(shown) >= 2:
            j = random.randint(0, len(shown) - 2)
            shown[j], shown[j + 1] = shown[j + 1], shown[j]
        elif et == 'wrong_key':
            tries = 0
            alt_rule_desc = rule_desc
            while tries < 6:
                _, rd = _sort_key_and_desc()
                rd = _normalize_rule_desc(rd)
                if rd != rule_desc:
                    alt_rule_desc = rd
                    break
                tries += 1
            shown = _compute_sorted_with_rule(words, alt_rule_desc, '升序' if direction == 'asc' else '降序')
    header = f"思考 {i}|排序:我按照下述规则对这些单词进行排序。规则: {rule_desc_raw}; 平局规则: 键值相同则按字典序升序; 方向: {declared_label}。排序结果: "
    return header + ', '.join(shown)

def _render_group(i: int, words: List[str], inject_error: bool) -> str:
    counts: Dict[str, int] = {}
    for w in words:
        counts[w[0]] = counts.get(w[0], 0) + 1
    mapping = dict(counts)
    if inject_error and mapping:
        et = random.choice(['wrong_count', 'missing_group', 'extra_group'])
        if et == 'wrong_count':
            pick = random.choice(list(mapping.keys()))
            val = mapping[pick]
            mapping[pick] = val + 1 if random.choice([True, False]) else max(0, val - 1)
        elif et == 'missing_group':
            pick = random.choice(list(mapping.keys()))
            del mapping[pick]
        elif et == 'extra_group':
            extra = random.choice([c for c in LETTERS if c not in mapping])
            mapping[extra] = random.randint(1, 3)
    display = '; '.join([f"{k}:{mapping[k]}" for k in sorted(mapping.keys())])
    header = f"思考 {i}|分组:我统计每个首字母的出现次数(按字母顺序展示)。结果: "
    return header + display

def _render_filter(i: int, words: List[str], inject_error: bool) -> str:
    kind = random.choice(['len_ge', 'len_le', 'first_in_set', 'vowels_ge'])
    shown: List[str] = []
    rule_str = ''
    if kind == 'len_ge':
        k = random.randint(3, max(4, max(len(w) for w in words)))
        shown = [w for w in words if len(w) >= k]
        rule_str = f"长度>={k}"
    elif kind == 'len_le':
        k = random.randint(3, max(4, max(len(w) for w in words)))
        shown = [w for w in words if len(w) <= k]
        rule_str = f"长度<={k}"
    elif kind == 'first_in_set':
        letters_pool = sorted({w[0] for w in words})
        choose_k = min(len(letters_pool), random.randint(2, 4))
        chosen = sorted(random.sample(letters_pool, choose_k))
        shown = [w for w in words if w[0] in chosen]
        rule_str = f"首字母∈[{', '.join(chosen)}]"
    else:
        k = random.randint(1, 4)
        shown = [w for w in words if _vowel_count(w) >= k]
        rule_str = f"元音数>={k}(元音=a,e,i,o,u)"
    result_list = shown[:]
    if inject_error:
        et = random.choice(['threshold_shift', 'missing_item', 'extra_item'])
        if et == 'threshold_shift' and ('>=' in rule_str or '<=' in rule_str):
            if kind == 'len_ge':
                result_list = [w for w in words if len(w) >= (int(rule_str.split('>=')[-1]) + random.choice([-1, 1]))]
            elif kind == 'len_le':
                result_list = [w for w in words if len(w) <= (int(rule_str.split('<=')[-1]) + random.choice([-1, 1]))]
            elif kind == 'vowels_ge':
                m = re.search(r'元音数>=(\d+)', rule_str)
                if m:
                    k2 = int(m.group(1)) + random.choice([-1, 1])
                    k2 = max(0, k2)
                    result_list = [w for w in words if _vowel_count(w) >= k2]
        elif et == 'missing_item' and result_list:
            j = random.randint(0, len(result_list) - 1)
            del result_list[j]
        elif et == 'extra_item':
            pool = [w for w in words if w not in shown]
            if pool:
                result_list = result_list + [random.choice(pool)]
    header = f"思考 {i}|筛选:我根据如下筛选规则选出单词。筛选规则: {rule_str}; 筛选结果: "
    return header + ', '.join(result_list)

def _render_length_map(i: int, words: List[str], inject_error: bool) -> str:
    items: List[Tuple[str, int]] = [(w, len(w)) for w in words]
    if inject_error:
        et = random.choice(['wrong_length', 'missing_word', 'foreign_word'])
        if et == 'wrong_length' and items:
            j = random.randint(0, len(items) - 1)
            wrong_len = max(1, items[j][1] + random.choice([-1, 1]))
            items[j] = (items[j][0], wrong_len)
        elif et == 'missing_word' and items:
            j = random.randint(0, len(items) - 1)
            del items[j]
        elif et == 'foreign_word':
            fw = ''
            while not fw or fw in words:
                fw = _gen_word(random.randint(5, 10)).lower()
            items.append((fw, len(fw)))
    pairs = [f"'{w}': {l}." for (w, l) in items]
    header = f"思考 {i}|长度映射:我计算每个单词的长度。结果: "
    return header + ' '.join(pairs)

def _render_summary(i: int, words: List[str], inject_error: bool) -> str:
    s1, s2 = _compute_S1_S2(words)
    show_s1, show_s2 = s1, s2
    if inject_error:
        if random.choice([True, False]):
            show_s1 += random.choice([-1, 1, 2])
        else:
            show_s2 += random.choice([-2, -1, 1, 2])
    header = f"思考 {i}|摘要:我计算两个摘要值以便后续核查。定义: S1=所有首字母位次之和; S2=所有长度之和。摘要: S1={show_s1}, S2={show_s2}。"
    return header

def _render_summary_check(i: int, words: List[str], steps_so_far: List[str], inject_error: bool) -> str:
    """
    摘要核对：再次声明期望 S1/S2 并给出结论 True/False。
    校验逻辑：若文本中的期望值与真实 S1/S2 相符，则结论必须 True，否则 False。
    错误注入：flip_conclusion / wrong_s1 / wrong_s2 / wrong_both。
    """
    s1, s2 = _compute_S1_S2(words)
    exp_s1, exp_s2 = s1, s2
    conclusion = True
    if inject_error:
        et = random.choice(['flip_conclusion', 'wrong_s1', 'wrong_s2', 'wrong_both'])
        if et == 'flip_conclusion':
            conclusion = False
        elif et == 'wrong_s1':
            exp_s1 = s1 + random.choice([-2, -1, 1, 2])
        elif et == 'wrong_s2':
            exp_s2 = s2 + random.choice([-2, -1, 1, 2])
        else:
            exp_s1 = s1 + random.choice([-2, -1, 1, 2])
            exp_s2 = s2 + random.choice([-2, -1, 1, 2])
            conclusion = True
    header = f"思考 {i}|摘要核对:我再次核对摘要值。期望 S1={exp_s1}, 期望 S2={exp_s2}。结论: {conclusion}"
    return header

def _render_hash(i: int, words: List[str], mod: int, inject_error: bool) -> str:
    """
    步骤中的校验码（H）：定义 H = sum(首字母位次×长度) 对 mod 取模。
    注：问题2的独立校验码 H2 与此步骤无关。
    """
    h = compute_hash_value(words, mod)
    shown_mod = _to_int(mod)
    shown_h = h
    if inject_error:
        et = random.choice(['wrong_mod', 'wrong_value'])
        if et == 'wrong_mod':
            choices = [m for m in ALLOWED_MODS if m != shown_mod]
            shown_mod = random.choice(choices) if choices else shown_mod
            shown_h = compute_hash_value(words, shown_mod)
        else:
            shown_h = (h + random.choice([-2, -1, 1, 2, 3])) % max(1, shown_mod)
    header = f"思考 {i}|校验码:定义 H=sum(首字母位次×长度) 对 {shown_mod} 取模; 计算结果: {shown_h}。"
    return header

def _detect_step_tag(step: str) -> str:
    m = re.match(r'\s*思考\s*\d+\|([^\:\：]+)\s*[:：]', step)
    return m.group(1) if m else ''

# -------------------------
# Parsers/Validators per step type
# -------------------------

def _parse_step1_pairs_single_quote(step: str) -> List[Tuple[str, str, int]]:
    pattern = r"'([^']+)':\s*'([A-Za-z])'\s*\((\d+)\)"
    return [(w, letter, int(idx)) for w, letter, idx in re.findall(pattern, step)]

def _validate_map_first_letter(words: List[str], step: str) -> bool:
    words_norm = [w.strip().lower() for w in words]
    word_set = set(words_norm)
    pairs = _parse_step1_pairs_single_quote(step)
    if not pairs:
        return False
    listed = []
    for w, letter, idx in pairs:
        wl = w.strip().lower()
        listed.append(wl)
        if wl not in word_set:
            return False
        if not wl or letter.lower() != wl[0]:
            return False
        if idx != _alpha_pos(letter):
            return False
    if set(listed) != word_set:
        return False
    if len(listed) != len(words_norm):
        return False
    return True

def _parse_sort(step: str) -> Tuple[str, str, List[str]]:
    m1 = re.search(r'规则:\s*([^;；]+)', step)
    rule_desc = m1.group(1).strip() if m1 else ''
    m2 = re.search(r'方向:\s*(升序|降序)', step)
    declared = m2.group(1) if m2 else ''
    m3 = re.search(r'排序结果:\s*([a-zA-Z,\s]+)', step)
    shown_str = m3.group(1).strip() if m3 else ''
    shown_list = [w.strip().lower() for w in shown_str.split(',') if w.strip()]
    norm_rule = _normalize_rule_desc(rule_desc)
    return norm_rule, declared, shown_list

def _validate_sort(words: List[str], step: str) -> bool:
    rule_desc, declared, shown = _parse_sort(step)
    if declared not in ('升序', '降序') or not rule_desc:
        return False
    expected = _compute_sorted_with_rule(words, rule_desc, declared)
    if sorted(shown) != sorted([w.lower() for w in words]):
        return False
    return shown == expected

def _parse_group(step: str) -> Dict[str, int]:
    return {ltr.lower(): int(cnt) for ltr, cnt in re.findall(r'([A-Za-z]):\s*(\d+)', step)}

def _validate_group(words: List[str], step: str) -> bool:
    actual: Dict[str, int] = {}
    for w in words:
        actual[w[0]] = actual.get(w[0], 0) + 1
    parsed = _parse_group(step)
    if not parsed:
        return False
    if set(parsed.keys()) != set(actual.keys()):
        return False
    for k in actual:
        if parsed.get(k, -1) != actual[k]:
            return False
    return True

def _parse_filter(step: str) -> Tuple[str, List[str]]:
    m1 = re.search(r'筛选规则:\s*([^\;；]+)', step)
    rule = m1.group(1).strip() if m1 else ''
    m2 = re.search(r'筛选结果:\s*([a-zA-Z,\s]*)', step)
    shown_str = (m2.group(1).strip() if m2 else '')
    shown_list = [w.strip().lower() for w in shown_str.split(',') if w.strip()]
    return rule, shown_list

def _validate_filter(words: List[str], step: str) -> bool:
    rule, shown = _parse_filter(step)
    if not rule:
        return False
    expected: List[str] = []
    if rule.startswith('长度>='):
        k = int(rule.split('>=')[-1])
        expected = [w for w in words if len(w) >= k]
    elif rule.startswith('长度<='):
        k = int(rule.split('<=')[-1])
        expected = [w for w in words if len(w) <= k]
    elif rule.startswith('首字母∈'):
        m = re.search(r'\[([a-zA-Z,\s]+)\]', rule)
        if not m:
            return False
        letters = [x.strip().lower() for x in m.group(1).split(',') if x.strip()]
        expected = [w for w in words if w[0] in set(letters)]
    elif rule.startswith('元音数>='):
        m = re.search(r'元音数>=(\d+)', rule)
        if not m:
            return False
        k = int(m.group(1))
        expected = [w for w in words if _vowel_count(w) >= k]
    else:
        return False
    return sorted(shown) == sorted(expected)

def _parse_length_map(step: str) -> List[Tuple[str, int]]:
    pattern = r"'([^']+)':\s*(\d+)\."
    return [(w, int(n)) for w, n in re.findall(pattern, step)]

def _validate_length_map(words: List[str], step: str) -> bool:
    items = _parse_length_map(step)
    if not items:
        return False
    words_norm = [w.strip().lower() for w in words]
    word_set = set(words_norm)
    listed = []
    for w, n in items:
        wl = w.strip().lower()
        listed.append(wl)
        if wl not in word_set:
            return False
        if n != len(wl):
            return False
    if set(listed) != word_set:
        return False
    if len(listed) != len(words_norm):
        return False
    return True

def _parse_summary(step: str) -> Tuple[int, int]:
    m1 = re.search(r'S1\s*=\s*(\d+)', step)
    m2 = re.search(r'S2\s*=\s*(\d+)', step)
    s1 = int(m1.group(1)) if m1 else -1
    s2 = int(m2.group(1)) if m2 else -1
    return s1, s2

def _validate_summary(words: List[str], step: str) -> bool:
    s1_show, s2_show = _parse_summary(step)
    if s1_show < 0 or s2_show < 0:
        return False
    s1, s2 = _compute_S1_S2(words)
    return (s1_show == s1) and (s2_show == s2)

def _parse_summary_check(step: str) -> Tuple[int, int, bool]:
    m1 = re.search(r'期望\s*S1\s*=\s*(\d+)', step)
    m2 = re.search(r'期望\s*S2\s*=\s*(\d+)', step)
    m3 = re.search(r'结论:\s*(True|False)', step)
    exp_s1 = int(m1.group(1)) if m1 else -1
    exp_s2 = int(m2.group(1)) if m2 else -1
    conc = (m3.group(1) == 'True') if m3 else False
    return exp_s1, exp_s2, conc

def _validate_summary_check(words: List[str], step: str) -> bool:
    exp_s1, exp_s2, conc = _parse_summary_check(step)
    if exp_s1 < 0 or exp_s2 < 0:
        return False
    s1, s2 = _compute_S1_S2(words)
    claims_ok = (exp_s1 == s1 and exp_s2 == s2)
    return conc == claims_ok

def _parse_hash(step: str) -> Tuple[int, int]:
    m_mod = re.search(r'对\s*(\d+)\s*取模', step)
    m_val = re.search(r'计算结果:\s*(\d+)', step)
    mod = int(m_mod.group(1)) if m_mod else 0
    val = int(m_val.group(1)) if m_val else -1
    return mod, val

def _validate_hash(words: List[str], step: str, hash_mod: int) -> bool:
    mod_shown, val_show = _parse_hash(step)
    if mod_shown <= 0 or val_show < 0:
        return False
    mod_expect = _to_int(hash_mod)
    if mod_shown != mod_expect:
        return False
    val_real = compute_hash_value(words, mod_expect)
    return val_show == val_real

def _validate_cross_check(words: List[str], step: str, steps_all: List[str]) -> bool:
    m_first = re.search(r'第一个应为\s+([a-zA-Z]+)', step)
    m_last = re.search(r'最后一个应为\s+([a-zA-Z]+)', step)
    m_conc = re.search(r'结论:\s*(True|False)', step)
    if not (m_first and m_last and m_conc):
        return False
    claim_first = m_first.group(1).strip().lower()
    claim_last = m_last.group(1).strip().lower()
    conc = (m_conc.group(1) == 'True')
    sort_idx = -1
    for j in range(len(steps_all) - 1, -1, -1):
        if _detect_step_tag(steps_all[j]) == '排序':
            sort_idx = j
            break
    if sort_idx == -1:
        return False
    rule_desc, declared, _ = _parse_sort(steps_all[sort_idx])
    expected = _compute_sorted_with_rule(words, rule_desc, declared)
    exp_first = expected[0]
    exp_last = expected[-1]
    claims_ok = (claim_first == exp_first and claim_last == exp_last)
    return conc == claims_ok

# -------------------------
# Cross-check renderer
# -------------------------

def _render_cross_check(i: int, words: List[str], steps_so_far: List[str], inject_error: bool) -> str:
    sort_idx = -1
    for j in range(len(steps_so_far) - 1, -1, -1):
        if _detect_step_tag(steps_so_far[j]) == '排序':
            sort_idx = j
            break
    if sort_idx >= 0:
        rule_desc, declared, _ = _parse_sort(steps_so_far[sort_idx])
        expected = _compute_sorted_with_rule(words, rule_desc, declared)
        claim_first = expected[0]
        claim_last = expected[-1]
        conclusion = True
        if inject_error:
            et = random.choice(['flip_conclusion', 'wrong_first', 'wrong_last', 'both_wrong'])
            if et == 'flip_conclusion':
                conclusion = False
            elif et == 'wrong_first':
                candidates = [w for w in expected if w != claim_first]
                if candidates:
                    claim_first = random.choice(candidates)
            elif et == 'wrong_last':
                candidates = [w for w in expected if w != claim_last]
                if candidates:
                    claim_last = random.choice(candidates)
            else:
                candidates_first = [w for w in expected if w != claim_first]
                if candidates_first:
                    claim_first = random.choice(candidates_first)
                candidates_last = [w for w in expected if w not in {claim_first, claim_last}]
                if candidates_last:
                    claim_last = random.choice(candidates_last)
                conclusion = True
        header = f"思考 {i}|交叉核对:为核查此前排序的端点，我进行简单核对。第一个应为 {claim_first}, 最后一个应为 {claim_last}。结论: {conclusion}"
        return header
    claim_first = min(words) if words else ''
    claim_last = max(words) if words else ''
    conclusion = not inject_error
    header = f"思考 {i}|交叉核对:为核查排序，我对端点进行检查。第一个应为 {claim_first}, 最后一个应为 {claim_last}。结论: {conclusion}"
    return header

# -------------------------
# Step type selection with constraints
# -------------------------

def _choose_step_types(step_count: int, ensure_sort: bool, ensure_hash: bool) -> List[str]:
    """
    强制包含：映射、长度映射、排序、摘要、校验码，且
    - 交叉核对紧随排序
    - 摘要核对紧随摘要
    """
    types_pool = ['映射', '排序', '分组', '筛选', '长度映射', '摘要', '交叉核对', '摘要核对', '校验码']
    result: List[str] = [random.choice(types_pool) for _ in range(step_count)]

    # 保证核心类型存在
    core = ['映射', '长度映射', '排序', '摘要']
    for need in core:
        if need not in result:
            result[random.randint(0, step_count - 1)] = need

    # 保证校验码存在且仅一次
    hash_positions = [i for i, t in enumerate(result) if t == '校验码']
    if ensure_hash:
        if len(hash_positions) == 0:
            result[random.randint(0, step_count - 1)] = '校验码'
        elif len(hash_positions) > 1:
            keep = hash_positions[0]
            for pos in hash_positions[1:]:
                result[pos] = random.choice(['分组', '筛选', '摘要'])

    # 保证交叉核对靠近排序
    if step_count >= 5:
        sort_positions = [i for i, t in enumerate(result) if t == '排序']
        if sort_positions:
            base_pos = sort_positions[0]
            place_pos = base_pos + 1 if base_pos + 1 < step_count else base_pos
            result[place_pos] = '交叉核对'
        else:
            result[0] = '排序'
            if step_count > 1:
                result[1] = '交叉核对'

    # 保证摘要核对靠近摘要
    sum_positions = [i for i, t in enumerate(result) if t == '摘要']
    if sum_positions:
        s_pos = sum_positions[0]
        s2 = s_pos + 1 if s_pos + 1 < step_count else s_pos
        result[s2] = '摘要核对'
    else:
        # 若摘要被替换掉，至少强制插入
        result[0] = '摘要'
        if step_count > 1:
            result[1] = '摘要核对'

    return result

# -------------------------
# Step generator with uniqueness enforcement
# -------------------------

def render_steps_verified(words: List[str], step_count: int, error_index: int, hash_mod: int) -> List[str]:
    max_tries = 60
    for _ in range(max_tries):
        steps: List[str] = []
        types = _choose_step_types(step_count, ensure_sort=True, ensure_hash=True)
        inject_pos = error_index
        for idx in range(step_count):
            tag = types[idx]
            inject = (inject_pos == (idx + 1))
            if tag == '映射':
                steps.append(_render_map_first_letter(idx + 1, words, inject))
            elif tag == '排序':
                steps.append(_render_sort(idx + 1, words, inject))
            elif tag == '分组':
                steps.append(_render_group(idx + 1, words, inject))
            elif tag == '筛选':
                steps.append(_render_filter(idx + 1, words, inject))
            elif tag == '长度映射':
                steps.append(_render_length_map(idx + 1, words, inject))
            elif tag == '摘要':
                steps.append(_render_summary(idx + 1, words, inject))
            elif tag == '摘要核对':
                steps.append(_render_summary_check(idx + 1, words, steps, inject))
            elif tag == '交叉核对':
                steps.append(_render_cross_check(idx + 1, words, steps, inject))
            else:
                steps.append(_render_hash(idx + 1, words, hash_mod, inject))
        first = find_first_mistake_dynamic(words, steps, _to_int(hash_mod))
        invalid_count = 0
        for s in steps:
            tag = _detect_step_tag(s)
            ok = False
            if tag == '映射':
                ok = _validate_map_first_letter(words, s)
            elif tag == '排序':
                ok = _validate_sort(words, s)
            elif tag == '分组':
                ok = _validate_group(words, s)
            elif tag == '筛选':
                ok = _validate_filter(words, s)
            elif tag == '长度映射':
                ok = _validate_length_map(words, s)
            elif tag == '摘要':
                ok = _validate_summary(words, s)
            elif tag == '摘要核对':
                ok = _validate_summary_check(words, s)
            elif tag == '交叉核对':
                ok = _validate_cross_check(words, s, steps)
            elif tag == '校验码':
                ok = _validate_hash(words, s, hash_mod)
            else:
                ok = False
            if not ok:
                invalid_count += 1
        if error_index == 0 and invalid_count == 0:
            return steps
        if error_index > 0 and invalid_count == 1 and first == error_index:
            return steps
    # Fallback：无错误版本
    steps = []
    types = _choose_step_types(step_count, ensure_sort=True, ensure_hash=True)
    for idx in range(step_count):
        tag = types[idx]
        if tag == '映射':
            steps.append(_render_map_first_letter(idx + 1, words, False))
        elif tag == '排序':
            steps.append(_render_sort(idx + 1, words, False))
        elif tag == '分组':
            steps.append(_render_group(idx + 1, words, False))
        elif tag == '筛选':
            steps.append(_render_filter(idx + 1, words, False))
        elif tag == '长度映射':
            steps.append(_render_length_map(idx + 1, words, False))
        elif tag == '摘要':
            steps.append(_render_summary(idx + 1, words, False))
        elif tag == '摘要核对':
            steps.append(_render_summary_check(idx + 1, words, steps, False))
        elif tag == '交叉核对':
            steps.append(_render_cross_check(idx + 1, words, steps, False))
        else:
            steps.append(_render_hash(idx + 1, words, _to_int(hash_mod), False))
    return steps

# -------------------------
# Final answer helpers
# -------------------------

def find_first_mistake_dynamic(words: List[str], steps: List[str], hash_mod: int) -> Union[int, str]:
    mod_int = _to_int(hash_mod)
    for idx, step in enumerate(steps):
        tag = _detect_step_tag(step)
        ok = False
        if tag == '映射':
            ok = _validate_map_first_letter(words, step)
        elif tag == '排序':
            ok = _validate_sort(words, step)
        elif tag == '分组':
            ok = _validate_group(words, step)
        elif tag == '筛选':
            ok = _validate_filter(words, step)
        elif tag == '长度映射':
            ok = _validate_length_map(words, step)
        elif tag == '摘要':
            ok = _validate_summary(words, step)
        elif tag == '摘要核对':
            ok = _validate_summary_check(words, step)
        elif tag == '交叉核对':
            ok = _validate_cross_check(words, step, steps)
        elif tag == '校验码':
            ok = _validate_hash(words, step, mod_int)
        else:
            ok = False
        if not ok:
            return idx + 1
    return 'No'

def validate_unique_first_error(words: List[str], steps: List[str], hash_mod: int) -> bool:
    mod_int = _to_int(hash_mod)
    first = find_first_mistake_dynamic(words, steps, mod_int)
    invalid_positions: List[int] = []
    for idx, s in enumerate(steps):
        tag = _detect_step_tag(s)
        ok = False
        if tag == '映射':
            ok = _validate_map_first_letter(words, s)
        elif tag == '排序':
            ok = _validate_sort(words, s)
        elif tag == '分组':
            ok = _validate_group(words, s)
        elif tag == '筛选':
            ok = _validate_filter(words, s)
        elif tag == '长度映射':
            ok = _validate_length_map(words, s)
        elif tag == '摘要':
            ok = _validate_summary(words, s)
        elif tag == '摘要核对':
            ok = _validate_summary_check(words, s)
        elif tag == '交叉核对':
            ok = _validate_cross_check(words, s, steps)
        elif tag == '校验码':
            ok = _validate_hash(words, s, mod_int)
        else:
            ok = False
        if not ok:
            invalid_positions.append(idx + 1)
    if first == 'No':
        return len(invalid_positions) == 0
    return len(invalid_positions) == 1 and invalid_positions[0] == first

def format_final_answer(words: List[str], steps: List[str], hash_mod: int) -> str:
    """
    统一最终答案：Q1 通过管线验证得到；Q2 使用独立校验码 H2（与步骤无关）。
    """
    mod_int = _to_int(hash_mod)
    q1 = find_first_mistake_dynamic(words, steps, mod_int)
    q2 = compute_hash_value_v2(words, mod_int)
    return f"Q1={q1}====Q2={q2}"

# -------------------------
# Assertions for Q2 consistency
# -------------------------

def assert_q2_consistency(words: List[str], mod: int, val: int) -> bool:
    try:
        m = _to_int(mod)
        v = _to_int(val)
    except ValueError:
        return False
    if m not in ALLOWED_MODS:
        return False
    return v == compute_hash_value(words, m)

def assert_q2_consistency_v2(words: List[str], mod: int, val: int) -> bool:
    try:
        m = _to_int(mod)
        v = _to_int(val)
    except ValueError:
        return False
    if m not in ALLOWED_MODS:
        return False
    return v == compute_hash_value_v2(words, m)

# -------------------------
# Final bundle assertion
# -------------------------

def assert_final_bundle(words: List[str], steps: List[str], mod: int, final_str: str) -> bool:
    """
    校验最终提交字符串是否与各子答案一致，且格式严格为:
    Q1=<No或整数>====Q2=<整数>
    同时校验唯一错误步骤约束与哈希模数合法性。
    """
    try:
        m = _to_int(mod)
    except ValueError:
        return False
    if m not in ALLOWED_MODS:
        return False
    if not isinstance(final_str, str):
        return False
    pat = r'^\s*Q1=(No|\d+)\s*====\s*Q2=(\d+)\s*$'
    mobj = re.match(pat, final_str)
    if not mobj:
        return False
    q1_tok = mobj.group(1)
    q2_tok = mobj.group(2)
    q1_expected = find_first_mistake_dynamic(words, steps, m)
    q2_expected = compute_hash_value_v2(words, m)
    q1_expected_str = str(q1_expected)
    q2_expected_str = str(q2_expected)
    if q1_tok != q1_expected_str:
        return False
    if q2_tok != q2_expected_str:
        return False
    if not validate_unique_first_error(words, steps, m):
        return False
    return True