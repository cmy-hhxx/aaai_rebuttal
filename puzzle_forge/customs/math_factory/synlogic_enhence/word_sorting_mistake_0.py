# word_sorting_mistake_0.py
# -*- coding: utf-8 -*-
"""
高阶复合逻辑的生成与校验（正向生成，含唯一解验证）：

函数摘要：
- function_generate_words(n, min_len, max_len): 生成唯一小写伪词。
- function_build_rules(num_steps_min, num_steps_max, allow_step1, inject_error):
    生成规则配置：
      {
        'num_steps': int,
        'types': [str],  # 步骤类型序列（含 'final_chain'）
        'params': {      # 各步骤参数字典，如 {'by_sum_mod': base, 'bucket_mode': 'vowel_consonant'}
            'by_sum_mod_base': int,
            'bucket_mode': str
        },
        'eff_error': {'type': <str>, 'index': <int>}  # 若不注入错误：{'type':'none','index':0}
      }
- function_build_steps(words, rules_config, eff_error): 基于类型与参数生成文本，并按需注入错误。
- function_2(steps): 步骤列表单行化与引号转义（用于题面desc）。
- function_1(words, steps): 主解析器，依序校验并返回首个错误步骤编号（1基），无误返回0。
- function_unique_check(words, steps, ans): 唯一解验证（多视角一致性，O(n log n)）。

支持步骤类型：
- 'list_letters'：列出 "word": "letter" (pos) 三元组。
- 'group_by_first'：按首字母分组，组内词按字典序。
- 'group_by_second'：在同首字母组内按第二字母排序说明。
- 'group_by_last'：按末字母分组，组内词按字典序。
- 'bucket_by_category'：按类别分桶（vowel_consonant / range_halves / prime_index）。
- 'by_sum_mod'：按 sum(letter_pos) % base 分桶（非降序）。
- 'final_chain'：最终完整字典序链。
"""

import random
import re
from typing import List, Tuple, Dict, Any


# --------------------------
# 基础工具
# --------------------------

def _rand_consonant() -> str:
    cons = 'bcdfghjklmnpqrstvwxyz'
    return random.choice(cons)


def _rand_vowel() -> str:
    vowels = 'aeiou'
    return random.choice(vowels)


def function_generate_words(n: int, min_len: int, max_len: int) -> List[str]:
    """生成 n 个唯一的小写词，仅含 a-z，长度在[min_len, max_len]。"""
    words = set()
    attempts = 0
    while len(words) < n and attempts < n * 300:
        attempts += 1
        L = random.randint(min_len, max_len)
        w_chars = []
        start_consonant = random.choice([True, False])
        for i in range(L):
            if (i % 2 == 0) == start_consonant:
                w_chars.append(_rand_consonant())
            else:
                w_chars.append(_rand_vowel())
        # 轻度扰动
        for _ in range(random.randint(0, 2)):
            idx = random.randint(0, L - 1)
            w_chars[idx] = random.choice('abcdefghijklmnopqrstuvwxyz')
        w = ''.join(w_chars)
        words.add(w)
    while len(words) < n:
        L = random.randint(min_len, max_len)
        w = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(L))
        words.add(w)
    return list(words)


def _letter_pos(ch: str) -> int:
    """字母位置（a=1..z=26）。"""
    return ord(ch) - 96


def _is_vowel(ch: str) -> bool:
    return ch in 'aeiou'


def _is_prime(x: int) -> bool:
    if x < 2:
        return False
    if x % 2 == 0:
        return x == 2
    i = 3
    while i * i <= x:
        if x % i == 0:
            return False
        i += 2
    return True


# --------------------------
# 规则生成
# --------------------------

def function_build_rules(num_steps_min: int, num_steps_max: int, allow_step1: bool, inject_error: bool) -> Dict[str, Any]:
    """
    生成步骤类型序列与参数，并规划一个错误（或不注入）。
    """
    num_steps = random.randint(num_steps_min, num_steps_max)
    # 类型池（不含 final_chain）
    mid_pool = ['group_by_first', 'group_by_second', 'group_by_last', 'bucket_by_category', 'by_sum_mod']
    types: List[str] = []

    # 第一步
    if allow_step1:
        types.append(random.choice(['list_letters', 'group_by_first']))
    else:
        types.append(random.choice(['group_by_first', 'group_by_second']))

    # 中间步
    mid_len = max(0, num_steps - 2)
    for _ in range(mid_len):
        types.append(random.choice(mid_pool))

    # 终步
    types.append('final_chain')

    # 参数：by_sum_mod 的 base 与 bucket 模式
    params: Dict[str, Any] = {
        'by_sum_mod_base': random.randint(3, 7),
        'bucket_mode': random.choice(['vowel_consonant', 'range_halves', 'prime_index'])
    }

    # 错误注入位置与类型
    eff_error = {'type': 'none', 'index': 0}
    if inject_error:
        candidates: List[Tuple[str, int]] = []
        # step1 错误（仅当首步为 list_letters）
        if types[0] == 'list_letters':
            candidates.append(('step1_word_miss', 1))
            candidates.append(('step1_letter_wrong', 1))
        # 中间步错误（可用于多种分组/分桶）
        for i, t in enumerate(types, start=1):
            if t in ('group_by_first', 'group_by_second', 'group_by_last', 'bucket_by_category', 'by_sum_mod') and i != len(types):
                candidates.append(('mid_group_wrong', i))
        # 终步错误
        candidates.append(('final_wrong_order', len(types)))
        candidates.append(('final_missing_word', len(types)))
        if candidates:
            et, idx = random.choice(candidates)
            eff_error = {'type': et, 'index': idx}

    return {'num_steps': num_steps, 'types': types, 'params': params, 'eff_error': eff_error}


# --------------------------
# 步骤构造（含错误注入）
# --------------------------

def _mutate_word(w: str) -> str:
    """替换首字母为不同字母以制造“类似但不在列表”的词。"""
    if not w:
        return w
    choices = [c for c in 'abcdefghijklmnopqrstuvwxyz' if c != w[0]]
    return random.choice(choices) + w[1:]


def _build_step_list_letters(words: List[str], inject: str) -> str:
    pairs: List[Tuple[str, str, int]] = []
    for w in words:
        ch = w[0]
        pairs.append((w, ch, _letter_pos(ch)))
    if inject == 'step1_word_miss':
        idx = random.randrange(len(pairs))
        w0, ch0, _ = pairs[idx]
        w_mut = _mutate_word(w0)
        ch_mut = w_mut[0]
        pairs[idx] = (w_mut, ch_mut, _letter_pos(ch_mut))
    elif inject == 'step1_letter_wrong':
        idx = random.randrange(len(pairs))
        w0, ch0, _ = pairs[idx]
        wrong_letters = [c for c in 'abcdefghijklmnopqrstuvwxyz' if c != ch0]
        ch_wrong = random.choice(wrong_letters)
        pairs[idx] = (w0, ch_wrong, _letter_pos(ch_wrong))
    prefix = '思考 1: 我先列出每个单词的第一个字母。第一个字母: '
    chunks = [f'"{w}": "{ch}" ({pos}).' for (w, ch, pos) in pairs]
    return prefix + ' '.join(chunks)


def _group_chain_from_key(words: List[str], key_func, misorder: bool = False) -> str:
    """按 key_func 分组→排序→串联，misorder 为真时打乱相邻组顺序制造错误。"""
    groups: Dict[Any, List[str]] = {}
    for w in words:
        groups.setdefault(key_func(w), []).append(w)
    ordered_keys = sorted(groups.keys())
    if misorder and len(ordered_keys) >= 2:
        i = random.randrange(len(ordered_keys) - 1)
        ordered_keys[i], ordered_keys[i + 1] = ordered_keys[i + 1], ordered_keys[i]
    parts = []
    for k in ordered_keys:
        g = sorted(groups[k])  # 组内字典序
        if len(g) > 1:
            parts.append('[' + ' ? '.join([f'"{x}"' for x in g]) + ']')
        else:
            parts.append(f'"{g[0]}"')
    return ' < '.join(parts)


def _build_step_group_by_first(words: List[str], idx: int, inject_here: bool) -> str:
    prefix = f'思考 {idx}: 按第一个字母分组进行链式说明。我们现在有: '
    chain = _group_chain_from_key(words, key_func=lambda w: w[0], misorder=inject_here)
    return prefix + chain + '。'


def _build_step_group_by_last(words: List[str], idx: int, inject_here: bool) -> str:
    prefix = f'思考 {idx}: 按最后一个字母分组进行链式说明。我们现在有: '
    chain = _group_chain_from_key(words, key_func=lambda w: w[-1], misorder=inject_here)
    return prefix + chain + '。'


def _has_same_first_letter(words: List[str]) -> bool:
    cnt: Dict[str, int] = {}
    for w in words:
        cnt[w[0]] = cnt.get(w[0], 0) + 1
    return any(v >= 2 for v in cnt.values())


def _build_step_group_by_second(words: List[str], idx: int, inject_here: bool) -> str:
    prefix = f'思考 {idx}: 在同首字母的词组内按第二个字母排序说明。我们现在有: '
    # 分组
    buckets: Dict[str, List[str]] = {}
    for w in words:
        buckets.setdefault(w[0], []).append(w)
    chain_parts = []
    letters = sorted(buckets.keys())
    for lt in letters:
        g = buckets[lt]
        if len(g) <= 1:
            chain_parts.append(f'"{g[0]}"')
            continue
        arr = sorted(g, key=lambda w: w[1])
        if inject_here and random.random() < 0.6 and len(arr) >= 2:
            j = random.randrange(len(arr) - 1)
            arr[j], arr[j + 1] = arr[j + 1], arr[j]
        if len(arr) > 1:
            chain_parts.append('[' + ' ? '.join([f'"{x}"' for x in arr]) + ']')
        else:
            chain_parts.append(f'"{arr[0]}"')
    return prefix + ' < '.join(chain_parts) + '。'


def _bucket_key(mode: str, base: int):
    if mode == 'vowel_consonant':
        # 元音优先（用0/1编码便于排序）
        return lambda w: 0 if _is_vowel(w[0]) else 1
    if mode == 'range_halves':
        return lambda w: 0 if 'a' <= w[0] <= 'm' else 1
    if mode == 'prime_index':
        return lambda w: 0 if _is_prime(_letter_pos(w[0])) else 1
    if mode == 'by_sum_mod':
        return lambda w: sum(_letter_pos(c) for c in w) % base
    # 默认退化
    return lambda w: 0


def _bucket_mode_name(mode: str, base: int) -> str:
    if mode == 'vowel_consonant':
        return '类别(元音开头优先于辅音开头)'
    if mode == 'range_halves':
        return '类别([a..m]为前半区优先于[n..z]后半区)'
    if mode == 'prime_index':
        return '类别(首字母序号为素数优先于非素数)'
    if mode == 'by_sum_mod':
        return f'字母值和模{base}的非降序'
    return '类别'


def _build_step_bucket(words: List[str], idx: int, mode: str, base: int, inject_here: bool) -> str:
    key_func = _bucket_key(mode, base)
    name = _bucket_mode_name(mode, base)
    prefix = f'思考 {idx}: 按{name}进行分桶说明。我们现在有: '
    chain = _group_chain_from_key(words, key_func=key_func, misorder=inject_here)
    return prefix + chain + '。'


def function_build_steps(words: List[str], rules_config: Dict[str, Any], eff_error: Dict[str, Any]) -> List[str]:
    words = [w.lower() for w in words]
    types: List[str] = rules_config.get('types', [])
    params: Dict[str, Any] = rules_config.get('params', {})
    steps: List[str] = []
    err_index = eff_error.get('index', 0)
    err_type = eff_error.get('type', 'none')

    for i, t in enumerate(types, start=1):
        if t == 'list_letters':
            inject = err_type if (err_index == i and err_type in ('step1_word_miss', 'step1_letter_wrong')) else 'none'
            steps.append(_build_step_list_letters(words, inject))
        elif t == 'group_by_first':
            inject_here = (err_index == i and err_type == 'mid_group_wrong')
            steps.append(_build_step_group_by_first(words, i, inject_here))
        elif t == 'group_by_second':
            inject_here = (err_index == i and err_type == 'mid_group_wrong')
            steps.append(_build_step_group_by_second(words, i, inject_here))
        elif t == 'group_by_last':
            inject_here = (err_index == i and err_type == 'mid_group_wrong')
            steps.append(_build_step_group_by_last(words, i, inject_here))
        elif t == 'bucket_by_category':
            inject_here = (err_index == i and err_type == 'mid_group_wrong')
            mode = params.get('bucket_mode', 'vowel_consonant')
            steps.append(_build_step_bucket(words, i, mode, base=0, inject_here=inject_here))
        elif t == 'by_sum_mod':
            inject_here = (err_index == i and err_type == 'mid_group_wrong')
            base = params.get('by_sum_mod_base', 5)
            steps.append(_build_step_bucket(words, i, 'by_sum_mod', base=base, inject_here=inject_here))
        elif t == 'final_chain':
            final_list = sorted(words)
            if err_index == i and err_type == 'final_wrong_order' and len(final_list) >= 2:
                k = random.randrange(len(final_list) - 1)
                final_list[k], final_list[k + 1] = final_list[k + 1], final_list[k]
            elif err_index == i and err_type == 'final_missing_word' and len(final_list) >= 2:
                m = random.randrange(len(final_list))
                del final_list[m]
            chain3 = '<'.join([f'"{w}"' for w in final_list])
            steps.append(f'思考 {i}: 我已经排序了所有单词。答案是{chain3}。')
        else:
            steps.append(f'思考 {i}: 说明性步骤。')

    return steps


# --------------------------
# 步骤解析与校验（主解析器）
# --------------------------

def _parse_list_letters_triples(text: str) -> List[Tuple[str, str, int]]:
    triples = re.findall(r'"([a-z]+)"\s*:\s*"([a-z])"\s*\(\s*(\d+)\s*\)', text)
    out = []
    for w, ch, pos in triples:
        try:
            out.append((w, ch, int(pos)))
        except Exception:
            out.append((w, ch, -1))
    return out


def _extract_groups(text: str) -> List[List[str]]:
    """从链式文本中提取各组的词序列。"""
    parts = [p.strip() for p in re.split(r'<', text)]
    groups: List[List[str]] = []
    for p in parts:
        ws = re.findall(r'"([a-z]+)"', p)
        if ws:
            groups.append(ws)
    return groups


def _check_list_letters(words: List[str], text: str) -> bool:
    pairs = _parse_list_letters_triples(text)
    listed_words = [w for (w, _, _) in pairs]
    if set(listed_words) != set(words):
        return False
    for (w, ch, pos) in pairs:
        if ch != w[0]:
            return False
        if pos != _letter_pos(ch):
            return False
    return True


def _check_group_by_first(words: List[str], text: str) -> bool:
    groups = _extract_groups(text)
    if not groups:
        return True
    prev = ''
    seen = []
    for g in groups:
        if len({w[0] for w in g}) != 1:
            return False
        cur = g[0][0]
        if prev and cur < prev:
            return False
        prev = cur
        seen.extend(g)
    return set(seen).issubset(set(words))


def _check_group_by_last(words: List[str], text: str) -> bool:
    groups = _extract_groups(text)
    if not groups:
        return True
    prev = ''
    seen = []
    for g in groups:
        last_letters = {w[-1] for w in g}
        if len(last_letters) != 1:
            return False
        cur = list(last_letters)[0]
        if prev and cur < prev:
            return False
        prev = cur
        seen.extend(g)
    return set(seen).issubset(set(words))


def _check_group_by_second(words: List[str], text: str) -> bool:
    groups = _extract_groups(text)
    if not groups:
        return True
    for g in groups:
        if len(g) <= 1:
            if not set(g).issubset(set(words)):
                return False
            continue
        if len({w[0] for w in g}) != 1:
            return False
        # 非降序
        seconds = [w[1] for w in g]
        if any(seconds[i] > seconds[i + 1] for i in range(len(seconds) - 1)):
            return False
        if not set(g).issubset(set(words)):
            return False
    return True


def _check_bucket(words: List[str], text: str, mode: str, base: int) -> bool:
    groups = _extract_groups(text)
    if not groups:
        return True
    key = _bucket_key(mode, base)
    # 检查组顺序非降（按 key 的代表值）
    prev = None
    for g in groups:
        if not set(g).issubset(set(words)):
            return False
        # 组内 key 一致（允许字典序列）
        k_vals = {key(w) for w in g}
        if len(k_vals) != 1:
            return False
        k = list(k_vals)[0]
        if prev is not None and k < prev:
            return False
        prev = k
    return True


def function_1(words: List[str], steps: List[str]) -> int:
    """主解析器：返回首个错误步骤编号（1基）。"""
    words = [w.lower() for w in words]
    sorted_words = sorted(words)

    for idx, s in enumerate(steps, start=1):
        if '第一个字母' in s and '答案是' not in s:
            if not _check_list_letters(words, s):
                return idx
        elif '按第一个字母' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if not _check_group_by_first(words, chain):
                return idx
        elif '按最后一个字母' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if not _check_group_by_last(words, chain):
                return idx
        elif '按第二个字母' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if not _check_group_by_second(words, chain):
                return idx
        elif '按类别' in s and '我们现在有:' in s:
            chain = s.split('我们现在有:', 1)[-1]
            # 推断模式
            if '元音开头' in s:
                if not _check_bucket(words, chain, 'vowel_consonant', 0):
                    return idx
            elif '[a..m]' in s or '前半区' in s:
                if not _check_bucket(words, chain, 'range_halves', 0):
                    return idx
            elif '素数' in s:
                if not _check_bucket(words, chain, 'prime_index', 0):
                    return idx
            else:
                # 未识别则视为正确（不作为错误干扰）
                pass
        elif '字母值和模' in s:
            chain = s.split('我们现在有:', 1)[-1]
            m = re.search(r'字母值和模(\d+)', s)
            base = int(m.group(1)) if m else 5
            if not _check_bucket(words, chain, 'by_sum_mod', base):
                return idx
        elif '答案是' in s:
            finals = re.findall(r'"([a-z]+)"', s)
            if set(finals) != set(words):
                return idx
            if finals != sorted_words:
                return idx
        else:
            # 非关键描述，默认通过
            pass
    return 0


# --------------------------
# 唯一解验证（多视角一致性）
# --------------------------

def _normalize_steps(steps: List[str]) -> List[str]:
    """清洗多余空白与全角句号差异等，不改变语义。"""
    out = []
    for s in steps:
        t = s.replace('。', '.')
        t = re.sub(r'\s+', ' ', t).strip()
        out.append(t)
    return out


def _alt_detection(words: List[str], steps: List[str]) -> int:
    """
    备用解析：不同的识别优先级，确认首错位置一致。
    优先顺序：final_chain -> list_letters -> bucket/by_sum_mod -> group_by_first/last/second。
    """
    words = [w.lower() for w in words]
    sorted_words = sorted(words)

    # 先找final错误
    for idx, s in enumerate(steps, start=1):
        if '答案是' in s:
            finals = re.findall(r'"([a-z]+)"', s)
            if set(finals) != set(words) or finals != sorted_words:
                return idx

    # 再检查 list_letters
    for idx, s in enumerate(steps, start=1):
        if '第一个字母' in s and '答案是' not in s:
            if not _check_list_letters(words, s):
                return idx

    # 再检查分桶
    for idx, s in enumerate(steps, start=1):
        if '字母值和模' in s:
            chain = s.split('我们现在有:', 1)[-1]
            m = re.search(r'字母值和模(\d+)', s)
            base = int(m.group(1)) if m else 5
            if not _check_bucket(words, chain, 'by_sum_mod', base):
                return idx
        elif '按类别' in s and '我们现在有:' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if '元音开头' in s:
                if not _check_bucket(words, chain, 'vowel_consonant', 0):
                    return idx
            elif '[a..m]' in s or '前半区' in s:
                if not _check_bucket(words, chain, 'range_halves', 0):
                    return idx
            elif '素数' in s:
                if not _check_bucket(words, chain, 'prime_index', 0):
                    return idx

    # 最后检查 group_by_* 字母位次
    for idx, s in enumerate(steps, start=1):
        if '按第一个字母' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if not _check_group_by_first(words, chain):
                return idx
        if '按最后一个字母' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if not _check_group_by_last(words, chain):
                return idx
        if '按第二个字母' in s:
            chain = s.split('我们现在有:', 1)[-1]
            if not _check_group_by_second(words, chain):
                return idx

    return 0


def function_unique_check(words: List[str], steps: List[str], ans: int) -> bool:
    """
    唯一解验证：
    - 原始解析结果 == ans
    - 规范化后解析结果 == ans
    - 备用解析路径结果 == ans
    """
    a1 = function_1(words, steps)
    if a1 != ans:
        return False
    steps2 = _normalize_steps(steps)
    a2 = function_1(words, steps2)
    if a2 != ans:
        return False
    a3 = _alt_detection(words, steps)
    if a3 != ans:
        return False
    return True


# --------------------------
# 题面desc用：单行化替换引号
# --------------------------

def function_2(steps: List[str]) -> str:
    """将步骤列表拼为单行并把双引号替换为反引号。"""
    return " ".join(s.replace('"', '`') for s in steps)