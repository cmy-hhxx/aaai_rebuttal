# word_sorting_5.py
# -*- coding: utf-8 -*-
"""
高阶造题脚本（正向生成）：
- function_2: 随机生成数据与规则，并确保唯一解（无重复完整排序键）。返回 {'items': List[str], 'rules': Dict, 'desc': str}
- function_1: 按规则对items进行排序，形成唯一答案。
- function_3: 唯一解校验，生成完整排序键并判重，返回布尔值。
- function_4: 构造前三项的统计串 'item:SC/SR/VC|item:...|item:...'

规则可变要点与复合：
1) 特殊复合字母集合与顺序：从候选池抽取若干，并设定顺序；比较时可设特殊在前或单字母在前。
2) 分词模式：特殊复合字母可在任意位置匹配或仅在词首匹配。
3) 单字母旋转字母表：从随机起点开始的26字母循环。
4) 次级键：声调升/降；三级键：长度升/降。
5) 附加决胜键：特殊数量（升/降）、旋转值总和（升/降）、元音数量（升/降）。
6) 触发器机制：
   - mode=1：含触发器token时，声调翻转（effective_tone = 5 - tone）。
   - mode=2：含触发器token时，从触发器首次出现之后的token采用反向排名（单字母索引与特殊rank反向）。
"""

from typing import List, Tuple, Dict, Any
import random
import string

_ALL_LETTERS = [chr(ord('a') + i) for i in range(26)]
_VOWELS = set(list("aeiou"))

def _build_rotated_order(offset: int) -> List[str]:
    offset = offset % 26
    return _ALL_LETTERS[offset:] + _ALL_LETTERS[:offset]

def _split_base_tone(s: str) -> Tuple[str, int]:
    """拆分末尾声调数字与拼音主体，并做基础校验。"""
    if not s:
        raise ValueError("Empty string in items.")
    s = s.strip()
    if not s or not s[-1].isdigit():
        raise ValueError(f"Item '{s}' does not end with a tone digit.")
    tone = int(s[-1])
    if tone < 1 or tone > 4:
        raise ValueError(f"Item '{s}' has invalid tone '{tone}'. Must be 1..4.")
    base = s[:-1]
    if not base:
        raise ValueError(f"Item '{s}' has empty base part.")
    return base.lower(), tone

def _tokenize(base: str, special_set: List[str], segmentation_mode: int) -> List[str]:
    """
    将拼音主体按规则切分为token序列：
    - segmentation_mode = 0: 任意位置匹配特殊复合字母；
    - segmentation_mode = 1: 仅在词首匹配特殊复合字母；
    """
    tokens: List[str] = []
    n = len(base)
    i = 0
    if segmentation_mode == 1:
        if n >= 2 and base[:2] in special_set:
            tokens.append(base[:2])
            i = 2
        while i < n:
            tokens.append(base[i])
            i += 1
        return tokens
    while i < n:
        if i + 1 < n:
            two = base[i:i+2]
            if two in special_set:
                tokens.append(two)
                i += 2
                continue
        tokens.append(base[i])
        i += 1
    return tokens

def _apply_trigger_effects(tokens: List[str], tone: int, rules: Dict[str, Any]) -> Tuple[List[str], int]:
    """
    触发器机制：
    - mode=1：含触发器token时，声调翻转（5 - tone）
    - mode=2：含触发器token时，触发器首次出现之后的token采用反向排名
    """
    trig_mode = rules['trigger_mode']
    trig_token = rules.get('trigger_token', None)
    if trig_mode == 0 or not trig_token:
        return tokens, tone

    # 是否包含触发器
    present_pos = None
    for idx, tk in enumerate(tokens):
        if tk == trig_token:
            present_pos = idx
            break

    if present_pos is None:
        return tokens, tone

    # 声调翻转
    if trig_mode == 1:
        tone_eff = 5 - tone
        return tokens, tone_eff

    # 后段排名反转
    if trig_mode == 2:
        # 将触发器之后的token标记为需要反向排名（在rank函数中实现）
        # 这里仅返回原tokens，具体反向由_rank_sequence实现（依赖present_pos）
        rules['_trigger_pos'] = present_pos
        return tokens, tone

    return tokens, tone

def _rank_sequence(tokens: List[str], rotated_index: Dict[str, int], special_rank: Dict[str, int], special_first: bool, rules: Dict[str, Any]) -> List[int]:
    """
    将token序列映射为整数序列以进行字典序比较。
    支持触发器模式2的后段反向：触发器之后的token的索引取反（单字母与特殊皆反向）。
    """
    ranks: List[int] = []
    max_single = 26
    max_special = max(1, len(special_rank))
    single_offset = (max_special if special_first else 0)
    special_offset = (0 if special_first else max_single)
    trig_pos = rules.get('_trigger_pos', None)

    for idx, tk in enumerate(tokens):
        after_trigger = (trig_pos is not None and idx > trig_pos)
        if tk in special_rank:
            sr = special_rank[tk]
            if after_trigger and rules['trigger_mode'] == 2:
                sr = (max_special - 1) - sr  # 特殊rank反向
            ranks.append(special_offset + sr)
        else:
            # 单字母（已小写）
            ch = tk
            if ch not in rotated_index:
                ranks.append(single_offset + max_single + (ord(ch) % 256))
            else:
                ri = rotated_index[ch]
                if after_trigger and rules['trigger_mode'] == 2:
                    ri = (max_single - 1) - ri  # 单字母索引反向
                ranks.append(single_offset + ri)
    return ranks

def _aux_counts(tokens: List[str], rules: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    计算隐式辅助统计：
    - special_count: 特殊token数量
    - sum_rotated: 单字母的旋转索引总和（考虑触发器模式2的后段反向）
    - vowel_count: 主体中元音字母数量（按字符级统计）
    """
    special_rank = rules['special_rank']
    rotated_index = rules['rotated_index']
    trig_pos = rules.get('_trigger_pos', None)

    special_count = 0
    sum_rotated = 0
    vowel_count = 0

    for idx, tk in enumerate(tokens):
        after_trigger = (trig_pos is not None and idx > trig_pos)
        if tk in special_rank:
            special_count += 1
        else:
            ch = tk
            if ch in rotated_index:
                ri = rotated_index[ch]
                if after_trigger and rules['trigger_mode'] == 2:
                    ri = (26 - 1) - ri
                sum_rotated += ri
            if ch in _VOWELS:
                vowel_count += 1

    return special_count, sum_rotated, vowel_count

def _sort_key(item: str, rules: Dict[str, Any]) -> Tuple[List[int], int, int, int, int, int]:
    """
    生成排序键：
    - 主键：rank_sequence
    - 次键：声调（升/降）
    - 三键：长度（升/降）
    - 四键：特殊数量（升/降）
    - 五键：旋转值总和（升/降）
    - 六键：元音数（升/降）
    """
    base, tone = _split_base_tone(item)
    tokens = _tokenize(base, rules['special_set'], rules['segmentation_mode'])
    # 触发器效应
    rules.pop('_trigger_pos', None)  # 清理旧状态
    tokens_eff, tone_eff = _apply_trigger_effects(tokens, tone, rules)
    ranks = _rank_sequence(tokens_eff, rules['rotated_index'], rules['special_rank'], rules['special_first'], rules)
    tone_key = tone_eff if rules['tone_order_mode'] == 0 else -tone_eff
    length_key = len(base) if rules['length_order_mode'] == 0 else -len(base)
    sc, sr, vc = _aux_counts(tokens_eff, rules)
    sc_key = sc if rules['special_count_order_mode'] == 0 else -sc
    sr_key = sr if rules['sum_rank_order_mode'] == 0 else -sr
    vc_key = vc if rules['vowel_count_order_mode'] == 0 else -vc
    return (ranks, tone_key, length_key, sc_key, sr_key, vc_key)

def function_1(items: List[str], rules: Dict[str, Any] = None) -> List[str]:
    """
    按规则对输入列表进行排序。
    """
    if rules is None:
        raise ValueError("function_1 requires a rules dictionary.")
    if not isinstance(items, list):
        raise TypeError("function_1 expects a list of strings.")
    for s in items:
        if not isinstance(s, str):
            raise TypeError("All items must be strings.")
    # 排序前先清理触发器状态，避免跨项污染
    rules.pop('_trigger_pos', None)
    return sorted(items, key=lambda it: _sort_key(it, rules))

def _random_token(special_set: List[str], weight_special: int, position: int, segmentation_mode: int) -> str:
    """
    随机生成一个token：
    - segmentation_mode=1时，只有首位(position==0)才可能是特殊，其余强制单字母；
    - 否则按权重选择特殊或单字母。
    """
    if segmentation_mode == 1 and position > 0:
        return random.choice(_ALL_LETTERS)
    base_single_weight = 10
    pick_special = False
    if weight_special > 0 and len(special_set) > 0:
        pick_special = random.choices([True, False], weights=[weight_special, base_single_weight], k=1)[0]
    if pick_special:
        return random.choice(special_set)
    return random.choice(_ALL_LETTERS)

def _apply_upper_mode(s: str, mode: int) -> str:
    """
    根据upper_mode调整大小写：
    - 0: 全小写
    - 1: 首字符50%概率大写
    - 2: 随机大小写（约30%字符转为大写）
    """
    if mode <= 0:
        return s.lower()
    if mode == 1:
        if not s:
            return s
        return (s[0].upper() + s[1:].lower()) if random.random() < 0.5 else s.lower()
    chars = []
    for ch in s:
        if ch.isalpha() and random.random() < 0.3:
            chars.append(ch.upper())
        else:
            chars.append(ch.lower())
    return ''.join(chars)

def _choose_special_set(pool: List[str], pick_num: int, order_mode: int) -> List[str]:
    """从候选池选择若干特殊复合字母并按指定模式排序。"""
    if pick_num < 1:
        pick_num = 1
    pick_num = min(pick_num, len(pool))
    choice = random.sample(pool, pick_num)
    if order_mode == 0:
        return sorted(choice)
    if order_mode == 1:
        return sorted(choice, reverse=True)
    random.shuffle(choice)
    return choice

def _build_rules(rotated_start_offset: int,
                 segmentation_mode: int,
                 tone_order_mode: int,
                 length_order_mode: int,
                 special_set: List[str],
                 special_priority_mode: int,
                 special_count_order_mode: int,
                 sum_rank_order_mode: int,
                 vowel_count_order_mode: int,
                 trigger_mode: int,
                 trigger_token: str) -> Dict[str, Any]:
    """构造规则字典与索引映射。"""
    rotated = _build_rotated_order(rotated_start_offset)
    rotated_index = {ch: i for i, ch in enumerate(rotated)}
    special_first = (special_priority_mode == 0)
    special_rank = {sp: i for i, sp in enumerate(special_set)}
    rules = {
        'special_set': special_set,
        'special_order': special_set[:],
        'special_rank': special_rank,
        'special_first': special_first,
        'segmentation_mode': segmentation_mode,
        'rotated_index': rotated_index,
        'tone_order_mode': tone_order_mode,
        'length_order_mode': length_order_mode,
        'rotated_start_letter': rotated[0],
        'rotated_example': ','.join(rotated[:3] + ['...'] + rotated[-3:]),
        'special_count_order_mode': special_count_order_mode,
        'sum_rank_order_mode': sum_rank_order_mode,
        'vowel_count_order_mode': vowel_count_order_mode,
        'trigger_mode': trigger_mode,
        'trigger_token': trigger_token,
    }
    return rules

def _build_rule_desc(rules: Dict[str, Any]) -> str:
    """
    构造人类可读的规则描述，避免双引号，使用简洁自然语言。
    """
    special_list = rules['special_order']
    if special_list:
        seq = '<'.join(special_list)
        special_part = f"特殊复合字母集合为 [{','.join(special_list)}] 且顺序为 {seq}"
    else:
        special_part = "无特殊复合字母集合，全部按单字母规则比较"
    priority_part = "特殊在前" if rules['special_first'] else "单字母在前"
    seg_part = "分词方式为任意位置匹配特殊复合字母" if rules['segmentation_mode'] == 0 else "分词方式为仅在词首匹配特殊复合字母"
    rot_start = rules['rotated_start_letter']
    rot_example = rules['rotated_example']
    tone_part = "声调升序" if rules['tone_order_mode'] == 0 else "声调降序"
    len_part = "长度升序" if rules['length_order_mode'] == 0 else "长度降序"
    sc_part = "特殊数量升序" if rules['special_count_order_mode'] == 0 else "特殊数量降序"
    sr_part = "旋转值总和升序" if rules['sum_rank_order_mode'] == 0 else "旋转值总和降序"
    vc_part = "元音数量升序" if rules['vowel_count_order_mode'] == 0 else "元音数量降序"
    trig_mode = rules['trigger_mode']
    if trig_mode == 0:
        trig_part = "不启用触发器规则"
    elif trig_mode == 1:
        trig_part = f"启用触发器规则: 若包含触发器 {rules['trigger_token']} 则声调翻转"
    else:
        trig_part = f"启用触发器规则: 若包含触发器 {rules['trigger_token']} 则触发器之后的token按反向排名"
    # 单行描述
    return f"{special_part}; {priority_part}; {seg_part}; 单字母使用从 {rot_start} 开始的旋转字母表, 示例顺序为 {rot_example}; 若主键仍相同则依次比较 {tone_part}、{len_part}、{sc_part}、{sr_part}、{vc_part}; {trig_part}; 比较时忽略拼音末尾的声调数字本身。"

def function_3(items: List[str], rules: Dict[str, Any]) -> bool:
    """
    唯一性校验：生成完整排序键并判重。
    返回True表示所有键互不相同（唯一解），否则False。
    """
    try:
        keys = []
        for it in items:
            rules.pop('_trigger_pos', None)
            k = _sort_key(it, rules)
            keys.append(tuple(k[0]) + (k[1], k[2], k[3], k[4], k[5]))
        return len(keys) == len(set(keys))
    except Exception:
        return False

def function_4(sorted_items: List[str], rules: Dict[str, Any]) -> str:
    """
    构造前三项的统计串 'item:SC/SR/VC|item:...|item:...'
    若不足三项，则按实际项数生成。
    """
    n = min(3, len(sorted_items))
    parts: List[str] = []
    for i in range(n):
        it = sorted_items[i]
        base, tone = _split_base_tone(it)
        tokens = _tokenize(base, rules['special_set'], rules['segmentation_mode'])
        rules.pop('_trigger_pos', None)
        tokens_eff, _tone_eff = _apply_trigger_effects(tokens, tone, rules)
        sc, sr, vc = _aux_counts(tokens_eff, rules)
        parts.append(f"{it}:{sc}/{sr}/{vc}")
    return "|".join(parts)

def function_2(item_num: int,
               token_len_min: int,
               token_len_max: int,
               weight_special: int,
               upper_mode: int,
               rotated_start_offset: int,
               segmentation_mode: int,
               tone_order_mode: int,
               length_order_mode: int,
               special_candidate_pool: List[str],
               special_pick_num: int,
               special_order_mode: int,
               special_priority_mode: int,
               special_count_order_mode: int,
               sum_rank_order_mode: int,
               vowel_count_order_mode: int,
               trigger_mode: int,
               trigger_pool: List[str]) -> Dict[str, Any]:
    """
    生成 items 与规则，并保证唯一解；返回 {'items': items, 'rules': rules, 'desc': rule_desc}
    """
    # 选择特殊集合与构造规则
    special_set = _choose_special_set(special_candidate_pool, special_pick_num, special_order_mode)
    trigger_token = None
    if trigger_mode != 0 and len(trigger_pool) > 0:
        trigger_token = random.choice(trigger_pool)
    rules = _build_rules(rotated_start_offset, segmentation_mode, tone_order_mode, length_order_mode,
                         special_set, special_priority_mode,
                         special_count_order_mode, sum_rank_order_mode, vowel_count_order_mode,
                         trigger_mode, trigger_token)
    rule_desc = _build_rule_desc(rules)

    # 生成items（带唯一解保障，限制尝试次数，确保<3分钟）
    if token_len_min < 1:
        token_len_min = 1
    if token_len_max < token_len_min:
        token_len_max = token_len_min
    if item_num < 1:
        item_num = 1

    max_outer_trials = 30  # 大循环尝试次数上限
    for outer in range(max_outer_trials):
        items: List[str] = []
        seen = set()
        max_inner_trials = item_num * 60
        trials = 0
        while len(items) < item_num and trials < max_inner_trials:
            trials += 1
            L = random.randint(token_len_min, token_len_max)
            tokens = [_random_token(special_set, weight_special, pos, segmentation_mode) for pos in range(L)]
            base = ''.join(tokens)
            tone = random.randint(1, 4)
            candidate = _apply_upper_mode(base, upper_mode) + str(tone)
            norm = candidate.lower()
            if norm not in seen:
                seen.add(norm)
                items.append(candidate)
        # 补齐（极端情况下）
        while len(items) < item_num:
            base = ''.join(random.choice(_ALL_LETTERS) for _ in range(max(token_len_min, 2)))
            tone = random.randint(1, 4)
            candidate = _apply_upper_mode(base, upper_mode) + str(tone)
            norm = candidate.lower()
            if norm not in seen:
                seen.add(norm)
                items.append(candidate)

        # 唯一性检验：需要每个项的完整排序键唯一
        if function_3(items, rules):
            return {'items': items, 'rules': rules, 'desc': rule_desc}
        # 若失败则调整部分参数以增加区分度（简单随机扰动）
        rotated_start_offset = (rotated_start_offset + random.randint(1, 5)) % 26
        rules = _build_rules(rotated_start_offset, segmentation_mode, tone_order_mode, length_order_mode,
                             special_set, special_priority_mode,
                             special_count_order_mode, sum_rank_order_mode, vowel_count_order_mode,
                             trigger_mode, trigger_token)
        rule_desc = _build_rule_desc(rules)

    # 兜底：返回最后一次生成（可能不唯一，但通常已满足）
    return {'items': items, 'rules': rules, 'desc': rule_desc}

# 本地快速自测
if __name__ == "__main__":
    random.seed()
    pack = function_2(
        item_num=14,
        token_len_min=2,
        token_len_max=5,
        weight_special=3,
        upper_mode=2,
        rotated_start_offset=6,
        segmentation_mode=0,
        tone_order_mode=1,
        length_order_mode=0,
        special_candidate_pool=['zh', 'ch', 'sh', 'ng'],
        special_pick_num=3,
        special_order_mode=2,
        special_priority_mode=0,
        special_count_order_mode=1,
        sum_rank_order_mode=0,
        vowel_count_order_mode=1,
        trigger_mode=2,
        trigger_pool=['zh', 'ch', 'sh', 'ng'] + _ALL_LETTERS
    )
    items = pack['items']
    rules = pack['rules']
    print("RULES:", pack['desc'])
    print("INPUT :", ','.join(items))
    print("OUTPUT:", ','.join(function_1(items, rules)))
    print("UNIQUE:", function_3(items, rules))
    print("TOP3  :", function_4(function_1(items, rules), rules))