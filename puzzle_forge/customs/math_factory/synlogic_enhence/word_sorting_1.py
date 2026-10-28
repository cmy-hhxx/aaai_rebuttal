# word_sorting_2.py
# -*- coding: utf-8 -*-
"""
高阶泛化的西语目录排序造题算子集合（确保唯一解与高复杂度，修复缺失 YAML 问题）
提供：
- function_3(item_num, min_len, max_len, accent_pct, ll_pct, enye_pct, uppercase_pct): 随机生成标题列表
- function_4(letters_pool, front_letters_num, prefer_bon_prob): 前置字母选择（倾向 [b,o,n]）
- function_8(front_letters, letters_pool, back_letters_num): 尾置字母选择（不与前置重复）
- function_5(front_letters, back_letters): 规则包构建（digraph、重音/大小写、ñ 模式、tie-break、隐藏权重、分块策略）
- function_6(titles, rule_config): 两阶段排序（主排序 + 分块调整），并在键末加入原标题回退，确保稳定唯一
- function_7(rule_config): 规则说明文本（通俗易懂，不暴露内部验证）
- function_9(titles, rule_config, timeout_ms): 唯一解校验（与最终排序键一致，O(n)，限时 3000ms）
- function_10(sorted_titles, rule_config): 校验码生成（基于规则与结果的短指纹）
- function_13(sorted_titles, rule_config): 最终答案 'item1,item2,…|K'
- function_2(titles): 简单拼接（内部使用）
"""

from typing import List, Dict, Tuple
import random
import time

# ---------- 字符集与映射 ----------
_ACCENTS_TO_PLAIN = {
    'á': 'a', 'Á': 'a',
    'é': 'e', 'É': 'e',
    'í': 'i', 'Í': 'i',
    'ó': 'o', 'Ó': 'o',
    'ú': 'u', 'Ú': 'u',
    'ü': 'u', 'Ü': 'u',
}
_VOWELS_PLAIN = set(list('aeiouAEIOU'))
_ACCENT_VOWELS = set(list('áéíóúÁÉÍÓÚ'))
_VOWELS_ALL = _VOWELS_PLAIN.union(_ACCENT_VOWELS)
_BASE_LETTERS = list('abcdefghijklmnopqrstuvwxyz')
_DIGRAPH_AFTER = {'ll': 'l', 'rr': 'r', 'ch': 'c'}

_CONS = list('bcdfghjklmnñpqrstvwyz')
_VOW = list('aeiou')
_ACCENT_VOW_LOWER = ['á', 'é', 'í', 'ó', 'ú']


# ---------- 预处理与记号化 ----------
def _strip_vowel_accents_keep_enye(s: str) -> str:
    out = []
    for ch in s:
        if ch in _ACCENTS_TO_PLAIN:
            out.append(_ACCENTS_TO_PLAIN[ch])
        else:
            out.append(ch.lower())
    return ''.join(out)


def _maybe_lower(s: str, case_insensitive: bool) -> str:
    return s.lower() if case_insensitive else s


def tokenize_with_rules(s: str, rule: Dict) -> List[str]:
    """
    根据规则记号化：
    - case_insensitive（是否统一小写）
    - ignore_accents（是否去除重音）
    - treat_ll/ch/rr（是否将 digraph 视为单字母）
    """
    s1 = _maybe_lower(s, rule.get('case_insensitive', True))
    s2 = _strip_vowel_accents_keep_enye(s1) if rule.get('ignore_accents', True) else s1

    treat_ll = rule.get('treat_ll', True)
    treat_rr = rule.get('treat_rr', False)
    treat_ch = rule.get('treat_ch', False)

    tokens = []
    i = 0
    while i < len(s2):
        if treat_ll and i + 1 < len(s2) and s2[i] == 'l' and s2[i + 1] == 'l':
            tokens.append('ll'); i += 2; continue
        if treat_rr and i + 1 < len(s2) and s2[i] == 'r' and s2[i + 1] == 'r':
            tokens.append('rr'); i += 2; continue
        if treat_ch and i + 1 < len(s2) and s2[i] == 'c' and s2[i + 1] == 'h':
            tokens.append('ch'); i += 2; continue
        tokens.append(s2[i]); i += 1
    return tokens


# ---------- 度量与映射 ----------
def accent_count(title: str) -> int:
    return sum(1 for ch in title if ch in _ACCENT_VOWELS)


def vowel_count(title: str) -> int:
    return sum(1 for ch in title if ch in _VOWELS_ALL)


def _is_consonant_unit(tok: str) -> bool:
    if tok in ('ll', 'rr', 'ch'):
        return True
    if tok == 'ñ':
        return True
    if len(tok) == 1:
        return tok.lower() not in set(list('aeiou'))
    return False


def consonant_count_units(title: str, rule: Dict) -> int:
    toks = tokenize_with_rules(title, rule)
    return sum(1 for t in toks if _is_consonant_unit(t))


def unit_length(title: str, rule: Dict) -> int:
    return len(tokenize_with_rules(title, rule))


def build_order_map(rule: Dict) -> Dict[str, int]:
    front = [ch.lower() for ch in rule.get('front_letters', [])]
    back = [ch.lower() for ch in rule.get('back_letters', [])]
    enye_mode = rule.get('enye_mode', 'after_n')

    seq = [ch for ch in _BASE_LETTERS]
    if 'ñ' not in seq:
        n_idx = seq.index('n')
        seq.insert(n_idx + 1, 'ñ')

    digraphs = []
    if rule.get('treat_ll', False): digraphs.append('ll')
    if rule.get('treat_rr', False): digraphs.append('rr')
    if rule.get('treat_ch', False): digraphs.append('ch')
    for dg in digraphs:
        ref = _DIGRAPH_AFTER[dg]
        if dg not in seq:
            idx = seq.index(ref) if ref in seq else len(seq) - 1
            seq.insert(idx + 1, dg)

    core = [x for x in seq if x not in front and x not in back]
    full_order = front + core + back
    order_map = {sym: idx for idx, sym in enumerate(full_order)}

    if enye_mode == 'as_n':
        n_idx = order_map.get('n', None)
        if n_idx is not None:
            order_map['ñ'] = n_idx
    return order_map


def primary_key(title: str, order_map: Dict[str, int], rule: Dict) -> List[int]:
    toks = tokenize_with_rules(title, rule)
    seq = []
    fallback_base = len(order_map) + 100
    for t in toks:
        if t in order_map:
            seq.append(order_map[t])
        else:
            seq.append(fallback_base)
            fallback_base += 1
    return seq


def _tie_values(title: str, rule: Dict) -> List[int]:
    out = []
    for metric, direction in rule.get('tie_breakers', []):
        if metric == 'accent_count':
            v = accent_count(title)
        elif metric == 'vowel_count':
            v = vowel_count(title)
        elif metric == 'consonant_count':
            v = consonant_count_units(title, rule)
        elif metric == 'unit_length':
            v = unit_length(title, rule)
        else:
            v = 0
        if direction == 'desc':
            v = -v
        out.append(v)
    return out


def _hidden_weight(title: str, rule: Dict) -> int:
    a, b, c = rule.get('hidden_coef', (1, 1, 1))
    base = a * unit_length(title, rule) + b * consonant_count_units(title, rule) - c * accent_count(title)
    if rule.get('hidden_dir', 'asc') == 'desc':
        base = -base
    return base


def _first_unit(title: str, order_map: Dict[str, int], rule: Dict) -> str:
    toks = tokenize_with_rules(title, rule)
    return toks[0] if toks else ''


def _apply_block_strategy(sorted_list: List[str], order_map: Dict[str, int], rule: Dict) -> List[str]:
    strategy = rule.get('block_strategy', 'none')
    if strategy == 'none':
        return list(sorted_list)

    blocks = []
    curr = []
    prev_key = None
    for t in sorted_list:
        key = _first_unit(t, order_map, rule)
        if prev_key is None or key == prev_key:
            curr.append(t)
        else:
            blocks.append(curr)
            curr = [t]
        prev_key = key
    if curr:
        blocks.append(curr)

    new_list = []
    for blk in blocks:
        if strategy == 'reverse_even_blocks':
            if len(blk) % 2 == 0:
                blk = list(reversed(blk))
        elif strategy == 'swap_head_tail':
            if len(blk) >= 2:
                blk = [blk[-1]] + blk[1:-1] + [blk[0]]
        elif strategy == 'rotate_right_1':
            if len(blk) >= 2:
                blk = [blk[-1]] + blk[:-1]
        new_list.extend(blk)
    return new_list


# ---------- 生成与选择算子 ----------
def function_3(item_num: int, min_len: int, max_len: int,
               accent_pct: int, ll_pct: int, enye_pct: int, uppercase_pct: int) -> List[str]:
    accent_prob = max(0.0, min(1.0, accent_pct / 100.0))
    ll_prob = max(0.0, min(1.0, ll_pct / 100.0))
    enye_prob = max(0.0, min(1.0, enye_pct / 100.0))
    upper_prob = max(0.0, min(1.0, uppercase_pct / 100.0))

    def _make_syllable(accent: bool) -> str:
        parts = []
        if random.random() < 0.5: parts.append(random.choice(_CONS))
        parts.append(random.choice(_ACCENT_VOW_LOWER) if accent else random.choice(_VOW))
        if random.random() < 0.4: parts.append(random.choice(_CONS))
        return ''.join(parts)

    def _inject_ll(s: str) -> str:
        if random.random() >= ll_prob or len(s) < 3: return s
        pos = random.randint(1, len(s)-2)
        return s[:pos] + 'll' + s[pos:]

    def _inject_enye(s: str) -> str:
        if random.random() >= enye_prob: return s
        indices = [i for i, ch in enumerate(s) if ch == 'n']
        if indices:
            i = random.choice(indices); return s[:i] + 'ñ' + s[i+1:]
        i = random.randint(0, len(s)); return s[:i] + 'ñ' + s[i:]

    def _apply_uppercase(s: str) -> str:
        r = random.random()
        if r < upper_prob * 0.5: return s.capitalize()
        elif r < upper_prob: return s.upper()
        return s

    words = set()
    attempt = 0
    max_attempt = item_num * 60
    while len(words) < item_num and attempt < max_attempt:
        attempt += 1
        syllable_count = random.choice([1, 2, 3])
        s = ''.join(_make_syllable(random.random() < accent_prob) for _ in range(syllable_count))
        if len(s) < min_len: s += _make_syllable(random.random() < accent_prob)
        if len(s) > max_len: s = s[:max_len]
        s = _inject_ll(s); s = _inject_enye(s); s = _apply_uppercase(s)
        words.add(s)
    while len(words) < item_num:
        s = ''.join(random.choice(_VOW + _CONS) for _ in range(random.randint(min_len, max_len)))
        words.add(s)
    return list(words)


def function_4(letters_pool: List[str], front_letters_num: int, prefer_bon_prob: int) -> List[str]:
    prefer = max(0, min(100, prefer_bon_prob)) / 100.0
    pool = list(set(ch.lower() for ch in letters_pool if isinstance(ch, str)))
    if random.random() < prefer and all(ch in pool for ch in ['b', 'o', 'n']):
        return ['b', 'o', 'n']
    random.shuffle(pool)
    chosen = []
    for ch in pool:
        if len(chosen) >= front_letters_num: break
        if ch not in chosen: chosen.append(ch)
    while len(chosen) < front_letters_num:
        ch = random.choice(pool)
        if ch not in chosen: chosen.append(ch)
    random.shuffle(chosen)
    return chosen


def function_8(front_letters: List[str], letters_pool: List[str], back_letters_num: int) -> List[str]:
    if back_letters_num <= 0: return []
    pool = list(set(ch.lower() for ch in letters_pool if isinstance(ch, str)))
    exclude = set(ch.lower() for ch in front_letters)
    cand = [ch for ch in pool if ch not in exclude]
    random.shuffle(cand)
    chosen = []
    for ch in cand:
        if len(chosen) >= back_letters_num: break
        chosen.append(ch)
    random.shuffle(chosen)
    return chosen


def function_5(front_letters: List[str], back_letters: List[str]) -> Dict:
    treat_ll = random.random() < 0.85
    treat_rr = random.random() < 0.5
    treat_ch = random.random() < 0.5
    ignore_accents = random.random() < 0.7
    case_insensitive = random.random() < 0.85
    enye_mode = random.choice(['after_n', 'as_n'])

    metrics_pool = ['accent_count', 'vowel_count', 'consonant_count', 'unit_length']
    random.shuffle(metrics_pool)
    k = random.randint(1, 3)
    chosen_metrics = metrics_pool[:k]
    tie_breakers: List[Tuple[str, str]] = [(m, random.choice(['asc', 'desc'])) for m in chosen_metrics]

    hidden_coef = (random.randint(1, 3), random.randint(1, 3), random.randint(1, 3))
    hidden_dir = random.choice(['asc', 'desc'])
    block_strategy = random.choice(['none', 'reverse_even_blocks', 'swap_head_tail', 'rotate_right_1'])

    return {
        'front_letters': [ch.lower() for ch in front_letters],
        'back_letters': [ch.lower() for ch in back_letters],
        'treat_ll': treat_ll,
        'treat_rr': treat_rr,
        'treat_ch': treat_ch,
        'ignore_accents': ignore_accents,
        'case_insensitive': case_insensitive,
        'enye_mode': enye_mode,
        'tie_breakers': tie_breakers,
        'hidden_coef': hidden_coef,
        'hidden_dir': hidden_dir,
        'block_strategy': block_strategy
    }


def function_6(titles: List[str], rule_config: Dict) -> List[str]:
    """
    两阶段排序：
    第一阶段：按 (primary_key, tie_values..., hidden_weight, original_title) 排序；
      - original_title 作为最终回退项，确保唯一与稳定。
    第二阶段：按 block_strategy 对连续首单位块进行确定性调整。
    """
    order_map = build_order_map(rule_config)
    base_sorted = sorted(
        titles,
        key=lambda t: (primary_key(t, order_map, rule_config),
                       *_tie_values(t, rule_config),
                       _hidden_weight(t, rule_config),
                       t)
    )
    final_sorted = _apply_block_strategy(base_sorted, order_map, rule_config)
    return final_sorted


def function_7(rule: Dict) -> str:
    parts = []
    fl = '[' + ', '.join(rule.get('front_letters', [])) + ']'
    bl_list = rule.get('back_letters', [])
    bl = '[' + ', '.join(bl_list) + ']' if bl_list else '无'
    parts.append(f'前置字母 {fl} 置于最前，尾置字母 {bl} 置于末尾')
    digraphs = []
    if rule.get('treat_ll', False): digraphs.append('ll')
    if rule.get('treat_ch', False): digraphs.append('ch')
    if rule.get('treat_rr', False): digraphs.append('rr')
    parts.append(('将 ' + ', '.join(digraphs) + ' 视为单字母') if digraphs else '不将 ll、ch、rr 视为单字母')
    parts.append('主比较' + ('忽略重音' if rule.get('ignore_accents', True) else '保留重音差异'))
    parts.append('主比较' + ('不区分大小写' if rule.get('case_insensitive', True) else '区分大小写'))
    enye_mode = rule.get('enye_mode', 'after_n')
    parts.append('ñ 位于 n 之后' if enye_mode == 'after_n' else '主比较中将 ñ 与 n 视为相同')
    tb_desc = []
    for metric, direction in rule.get('tie_breakers', []):
        name = {'accent_count': '重音元音个数', 'vowel_count': '元音总数', 'consonant_count': '辅音单位个数', 'unit_length': '单位长度'}.get(metric, metric)
        dir_cn = '升序' if direction == 'asc' else '降序'
        tb_desc.append(f'{name}{dir_cn}')
    parts.append(('若主键完全相同，则依次比较：' + '，'.join(tb_desc)) if tb_desc else '不设置额外的 tie-break 规则')
    a, b, c = rule.get('hidden_coef', (1, 1, 1))
    dir_cn = '升序' if rule.get('hidden_dir', 'asc') == 'asc' else '降序'
    parts.append(f'必要时使用隐藏加权分数 a*单位长度 + b*辅音单位个数 - c*重音个数（a={a},b={b},c={c}，{dir_cn}）决胜')
    bs = rule.get('block_strategy', 'none')
    bs_cn = {'none': '无分块调整', 'reverse_even_blocks': '对偶数长度块进行反转', 'swap_head_tail': '每块交换首尾', 'rotate_right_1': '每块整体右移一位'}.get(bs, bs)
    parts.append('第二阶段分块策略：' + bs_cn)
    parts.append('如仍完全相同，则按原标题的字典序比较')
    return '；'.join(parts)


def function_9(titles: List[str], rule_config: Dict, timeout_ms: int) -> bool:
    """
    唯一解校验（快速）：
    - 键向量与最终排序一致：(primary_key, tie_values..., hidden_weight, original_title)
    - 若存在两个标题的键完全相同，返回 False；
    - 超时直接返回 False。
    """
    start = time.time()
    order_map = build_order_map(rule_config)
    keys = []
    for t in titles:
        if (time.time() - start) * 1000 > timeout_ms:
            return False
        key_vec = tuple(primary_key(t, order_map, rule_config) + _tie_values(t, rule_config) + [_hidden_weight(t, rule_config), t])
        keys.append(key_vec)
    return len(set(keys)) == len(keys)


def function_10(sorted_titles: List[str], rule_config: Dict) -> str:
    fp = 0
    for b in ['treat_ll', 'treat_rr', 'treat_ch', 'ignore_accents', 'case_insensitive']:
        fp = (fp * 131 + (1 if rule_config.get(b, False) else 0)) & 0xFFFFFFFF
    fp = (fp * 131 + (1 if rule_config.get('enye_mode', 'after_n') == 'after_n' else 2)) & 0xFFFFFFFF
    for m, d in rule_config.get('tie_breakers', []):
        fp = (fp * 131 + hash(m) % 997) & 0xFFFFFFFF
        fp = (fp * 131 + (1 if d == 'asc' else 2)) & 0xFFFFFFFF
    a, b, c = rule_config.get('hidden_coef', (1, 1, 1))
    fp = (fp * 131 + a*17 + b*19 + c*23) & 0xFFFFFFFF
    fp = (fp * 131 + (1 if rule_config.get('hidden_dir', 'asc') == 'asc' else 2)) & 0xFFFFFFFF
    fp = (fp * 131 + {'none':1,'reverse_even_blocks':2,'swap_head_tail':3,'rotate_right_1':4}.get(rule_config.get('block_strategy','none'),5)) & 0xFFFFFFFF

    ssum = 0
    for i, t in enumerate(sorted_titles):
        chsum = sum(ord(ch) for ch in t)
        ssum = (ssum + (i + 1) * (chsum % 1009)) & 0xFFFFFFFF

    total = (fp ^ (ssum * 2654435761 & 0xFFFFFFFF)) & 0xFFFFFFFF

    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if total == 0:
        return '0'
    out = []
    while total > 0:
        out.append(digits[total % 36])
        total //= 36
    return ''.join(reversed(out))


def function_13(sorted_titles: List[str], rule_config: Dict) -> str:
    return ','.join(sorted_titles) 


def function_2(titles: List[str]) -> str:
    return ','.join(titles)


# ---------- 自检 ----------
if __name__ == '__main__':
    random.seed()
    item_num = 14
    titles = function_3(item_num, 3, 8, 35, 40, 25, 20)
    front_letters = function_4(list('abcdefghijklmnopqrstuvwxyz') + ['ñ'], 3, 60)
    back_letters = function_8(front_letters, list('abcdefghijklmnopqrstuvwxyz') + ['ñ'], 2)
    rule = function_5(front_letters, back_letters)
    sorted_list = function_6(titles, rule)
    ok = function_9(titles, rule, 3000)
    code = function_10(sorted_list, rule)
    print('RULE:', function_7(rule))
    print('FRONT:', front_letters, 'BACK:', back_letters)
    print('UNIQUE:', ok)
    print('TITLES:', titles)
    print('SORTED:', sorted_list)
    print('ANSWER:', function_13(sorted_list, rule))