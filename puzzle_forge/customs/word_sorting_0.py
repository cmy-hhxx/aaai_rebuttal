# word_sorting_0.py
import random
from typing import List, Dict

def _dedup_preserve_order(seq: List[str]) -> List[str]:
    """去重且保留顺序。"""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def build_custom_alphabet(special: List[str]) -> Dict[str, int]:
    """
    构造自定义字母顺序映射：
    - 将 special 中的字母（已按给定顺序）置于最前；
    - 其余字母保持 a-z 原序，排在后面；
    返回: {字符: 序位}，序位越小表示越靠前。
    """
    special = [ch for ch in _dedup_preserve_order(special) if 'a' <= ch <= 'z']
    base = [chr(i) for i in range(ord('a'), ord('z') + 1)]
    tail = [ch for ch in base if ch not in set(special)]
    ordered = special + tail
    return {ch: idx for idx, ch in enumerate(ordered)}

def sort_words(words: List[str], order_map: Dict[str, int], is_desc: bool) -> List[str]:
    """
    按照自定义字母顺序进行词典序比较。
    - words: 全部为 a-z 小写；
    - order_map: 字符 -> 序位；
    - is_desc: True 为降序，False 为升序。
    """
    def word_key(w: str):
        return [order_map[c] for c in w]  # 假设全部 a-z 小写，简化映射
    return sorted(words, key=word_key, reverse=is_desc)

def pick_words(n: int, seed: int) -> List[str]:
    """
    随机选取 n 个不重复英文小写单词，确保首字母具有区分度（至少两种不同首字母）。
    """
    random.seed(seed)
    word_bank = [
        'yangtze','dearly','helminthagogic','hover','cariniform','zinky','fistulatome','almond','bridge',
        'cascade','dynamo','ellipse','fragile','glisten','harbor','isolate','jungle','kernel','lattice','magnify',
        'nebula','opaque','prairie','quartz','raccoon','sapphire','tangent','umbra','vortex','walnut','xenial',
        'yonder','zephyr','glimmer','lullaby','garland','locator','glyph','lexicon','gadget','lagoon','goliath',
        'lignite','glisten','lagger','glycerin','lopsided','gambit','lobster','glaring','lancer','gramineous',
        'hovering','dearest','zincify','carinae','fasten','isogram','vagrant','tunable','nebular','praxis',
        'quibble','raffles','saffron','topaz','uranium','verdant','whistle','xylitol','yearning','zoology',
        'fuselage','laminar','granular','lexical','gyrate','locust','glorious','livid','gullible','laminate'
    ]
    # 去重、过滤非 a-z 与大写
    word_bank = [w for w in _dedup_preserve_order(word_bank) if w.isalpha() and w.islower()]
    if n > len(word_bank):
        n = len(word_bank)

    # 采样直到首字母至少有两种不同
    for _ in range(100):
        sample = random.sample(word_bank, n)
        initials = {w[0] for w in sample}
        if len(initials) >= 2:
            return sample
    # 若极端情况下仍未满足，强制修正：保证至少两种首字母
    sample = random.sample(word_bank, n)
    initials = {w[0] for w in sample}
    if len(initials) < 2:
        # 用不同首字母的词替换一个元素
        by_initial = {}
        for w in word_bank:
            by_initial.setdefault(w[0], []).append(w)
        # 找到一个与现有首字母不同的备选
        all_inits = list(by_initial.keys())
        for init in all_inits:
            if init not in initials:
                candidate = random.choice(by_initial[init])
                sample[0] = candidate
                break
    return sample

def pick_special_letters(k: int, words: List[str], seed: int) -> List[str]:
    """
    随机生成置前字母：
    - 至少两个来自 words 的首字母（若 words 首字母种类不足，则尽量满足）；
    - 其余从 a-z 中补足，不重复，保序。
    """
    random.seed(seed + 7)  # 与 pick_words 稍作区分
    alphabet = [chr(i) for i in range(ord('a'), ord('z') + 1)]
    initials = _dedup_preserve_order([w[0] for w in words])  # 保序的首字母集合
    # 从首字母中选至少两个
    chosen = []
    if len(initials) >= 2:
        chosen = random.sample(initials, 2)
    elif len(initials) == 1:
        chosen = initials[:]  # 仅一个首字母可用
    # 补足到 k
    pool = [ch for ch in alphabet if ch not in set(chosen)]
    need = max(0, k - len(chosen))
    if need > len(pool):
        need = len(pool)
    chosen += random.sample(pool, need)
    # 保留顺序与不重复
    return _dedup_preserve_order(chosen)[:k]

def make_prefix_chain(special: List[str]) -> str:
    """生成“x < l < g”样式的前缀顺序说明文本。"""
    special = _dedup_preserve_order([ch for ch in special if 'a' <= ch <= 'z'])
    return ' < '.join(special) if special else ''