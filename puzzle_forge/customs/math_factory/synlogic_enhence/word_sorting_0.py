# word_sorting_0.py
# -*- coding: utf-8 -*-
"""
高阶随机化词排序造题支持库（修复：唯一性校验 key 统一转为可哈希元组）

规则类型（可复合、顺序生效）：
- head_letters：将一组字母置前（保持给定顺序）
- tail_letters：将一组字母置后（保持给定顺序）
- group_bias：将一个组（'vowel' 或 'consonant'）整体移到开头或末尾（保持相对顺序）
- weights：为若干字母设置非负整数权重，单词分数为所有字母权重之和
- digraph_map：二字母组合（如 th、sh、ch、qu、ng）视作单一“伪字母”，并定义它们的相对顺序；用于生成独立的序列比较维度
- dynamic_anchor：从单词集合中选取出现频次最高的若干“锚字母”，将其整体移到开头或末尾；引入对实例数据的依赖（隐式辅助变量）

复合比较模式（示例）：
- 'feature_digraph_score_lex'
- 'score_lex_feature_digraph'
- 'lex_score_digraph_feature'
- 'digraph_feature_lex_score'
- 'lex_only' / 'score_then_lex' / 'lex_then_score' / 'feature_then_lex'

其它：
- order_type：'asc' 或 'desc'
- length_tiebreak：'longer_is_greater' 或 'shorter_is_greater'
- 唯一解验证：对复合 key 检查全局唯一性，O(n log n)，远小于 3 分钟。
"""

from typing import Dict, Iterable, List, Any, Tuple, Set
import random
import string
from collections import Counter

__all__ = [
    "op_gen_rules",
    "op_gen_words",
    "op_choose_tiebreak",
    "op_choose_order",
    "op_choose_comparator_mode",
    "op_sort_composite",
    "op_build_rule_text",
    "op_verify_by_rules",
    "op_verify_unique",
    "CustomCond",
]

# -------------------- 常量与工具 --------------------
VOWELS: Set[str] = set("aeiou")
ALPHABET: List[str] = list(string.ascii_lowercase)
DEFAULT_DIGRAPHS: List[str] = ["th", "sh", "ch", "ph", "gh", "ng", "qu", "wh"]


def _move_to_front(seq: List[str], letters_in_order: List[str]) -> List[str]:
    sset = set(letters_in_order)
    front = [c for c in letters_in_order if c in seq]
    rest = [c for c in seq if c not in sset]
    return front + rest


def _move_to_back(seq: List[str], letters_in_order: List[str]) -> List[str]:
    sset = set(letters_in_order)
    front = [c for c in seq if c not in sset]
    back = [c for c in letters_in_order if c in seq]
    return front + back


def _move_group(seq: List[str], group: str, direction: str) -> List[str]:
    if group == "vowel":
        is_group = lambda c: c in VOWELS
    else:
        is_group = lambda c: c not in VOWELS
    group_part = [c for c in seq if is_group(c)]
    rest_part = [c for c in seq if not is_group(c)]
    return (group_part + rest_part) if direction == "front" else (rest_part + group_part)


def _build_rank_map(rules: List[Dict[str, Any]]) -> Dict[str, int]:
    order = ALPHABET[:]
    for r in rules:
        t = r.get("type")
        if t == "head_letters":
            letters = [c for c in r.get("letters", []) if c in ALPHABET]
            order = _move_to_front(order, letters)
        elif t == "tail_letters":
            letters = [c for c in r.get("letters", []) if c in ALPHABET]
            order = _move_to_back(order, letters)
        elif t == "group_bias":
            group = r.get("group", "vowel")
            direction = r.get("direction", "front")
            order = _move_group(order, group, direction)
        elif t == "dynamic_anchor":
            anchors = [c for c in r.get("anchors", []) if c in ALPHABET]
            direction = r.get("direction", "front")
            order = _move_to_front(order, anchors) if direction == "front" else _move_to_back(order, anchors)
    return {c: idx for idx, c in enumerate(order)}


def _build_score_map(rules: List[Dict[str, Any]]) -> Dict[str, int]:
    score: Dict[str, int] = {}
    for r in rules:
        if r.get("type") == "weights":
            weights = r.get("weights", {})
            for k, v in weights.items():
                if k in ALPHABET and isinstance(v, int) and v >= 0:
                    score[k] = score.get(k, 0) + v
    return score


def _build_digraph_rank_and_list(rules: List[Dict[str, Any]]) -> Tuple[Dict[str, int], List[str], str]:
    for r in rules:
        if r.get("type") == "digraph_map":
            digraphs = [dg for dg in r.get("digraphs", []) if isinstance(dg, str) and 2 <= len(dg) <= 3]
            seen = set()
            ordered = []
            for dg in digraphs:
                if dg not in seen:
                    seen.add(dg)
                    ordered.append(dg)
            direction = r.get("direction", "front")
            rank_map = {f"DG_{i}": i for i in range(len(ordered))}
            return rank_map, ordered, direction
    return {}, [], ""


def _collapse_digraphs(word: str, digraphs: List[str]) -> List[str]:
    if not digraphs:
        return list(word.lower())
    i = 0
    out: List[str] = []
    lower = word.lower()
    while i < len(lower):
        matched = False
        for dg_len in sorted({len(dg) for dg in digraphs}, reverse=True):
            if i + dg_len <= len(lower):
                segment = lower[i : i + dg_len]
                try:
                    idx = digraphs.index(segment)
                except ValueError:
                    idx = -1
                if idx != -1:
                    out.append(f"DG_{idx}")
                    i += dg_len
                    matched = True
                    break
        if not matched:
            out.append(lower[i])
            i += 1
    return out


def _word_rank_seq(word: str, rank_map: Dict[str, int]) -> List[int]:
    seq: List[int] = []
    for ch in word.lower():
        if ch in rank_map:
            seq.append(rank_map[ch])
        else:
            seq.append(26 + ord(ch))
    return seq


def _word_digraph_seq(word: str, digraph_rank_map: Dict[str, int], digraphs: List[str], direction: str) -> List[int]:
    if not digraphs:
        return []
    toks = _collapse_digraphs(word, digraphs)
    seq: List[int] = []
    base = -1 if direction == "front" else 1000
    for tk in toks:
        if tk.startswith("DG_"):
            seq.append(digraph_rank_map.get(tk, 500))
        else:
            seq.append(base)
    return seq


def _word_score(word: str, score_map: Dict[str, int]) -> int:
    if not score_map:
        return 0
    s = 0
    for ch in word.lower():
        s += score_map.get(ch, 0)
    return s


def _word_features(word: str, rank_map: Dict[str, int]) -> Tuple[int, int, int, int]:
    lower = word.lower()
    vowel_cnt = sum(1 for ch in lower if ch in VOWELS)
    consonant_cnt = sum(1 for ch in lower if ch in ALPHABET and ch not in VOWELS)
    unique_cnt = len(set(ch for ch in lower if ch in ALPHABET))
    first_rank = rank_map.get(lower[0], 999) if lower else 999
    return vowel_cnt, consonant_cnt, unique_cnt, first_rank


# -------------------- 随机生成部分 --------------------
def op_gen_words(words_num: int, min_len: int, max_len: int) -> List[str]:
    result: List[str] = []
    seen = set()
    attempts = 0
    max_attempts = words_num * 60
    while len(result) < words_num and attempts < max_attempts:
        length = random.randint(min_len, max_len)
        w = "".join(random.choice(string.ascii_lowercase) for _ in range(length))
        attempts += 1
        if w not in seen:
            seen.add(w)
            result.append(w)
    while len(result) < words_num:
        length = random.randint(min_len, max_len)
        w = "".join(random.choice(string.ascii_lowercase) for _ in range(length))
        if w not in seen:
            seen.add(w)
            result.append(w)
    return result


def _random_letter_set(k: int) -> List[str]:
    k = max(1, min(k, 26))
    letters = ALPHABET[:]
    random.shuffle(letters)
    return letters[:k]


def _build_dynamic_anchor(words: List[str], max_k: int = 5) -> List[str]:
    cnt = Counter(ch for w in words for ch in w.lower() if ch in ALPHABET)
    if not cnt:
        return []
    k = random.randint(1, min(max_k, len(cnt)))
    ordered = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
    anchors = [kv[0] for kv in ordered[:k]]
    return anchors


def op_gen_rules(rule_num: int, words: List[str]) -> List[Dict[str, Any]]:
    n = max(2, min(rule_num, 5))
    types_pool = ["head_letters", "tail_letters", "group_bias", "weights", "digraph_map", "dynamic_anchor"]
    random.shuffle(types_pool)
    rules: List[Dict[str, Any]] = []
    has_weights = False
    has_digraph = False
    has_anchor = False
    for t in types_pool:
        if len(rules) >= n:
            break
        if t == "head_letters":
            k = random.randint(1, 5)
            rules.append({"type": "head_letters", "letters": _random_letter_set(k)})
        elif t == "tail_letters":
            k = random.randint(1, 5)
            rules.append({"type": "tail_letters", "letters": _random_letter_set(k)})
        elif t == "group_bias":
            group = random.choice(["vowel", "consonant"])
            direction = random.choice(["front", "back"])
            rules.append({"type": "group_bias", "group": group, "direction": direction})
        elif t == "weights":
            if not has_weights:
                k = random.randint(2, 5)
                letters = _random_letter_set(k)
                weights = {c: random.randint(1, 5) for c in letters}
                rules.append({"type": "weights", "weights": weights})
                has_weights = True
        elif t == "digraph_map":
            if not has_digraph:
                k = random.randint(1, 4)
                dset = DEFAULT_DIGRAPHS[:]
                random.shuffle(dset)
                digraphs = dset[:k]
                direction = random.choice(["front", "back"])
                rules.append({"type": "digraph_map", "digraphs": digraphs, "direction": direction})
                has_digraph = True
        elif t == "dynamic_anchor":
            if not has_anchor:
                anchors = _build_dynamic_anchor(words, max_k=5)
                if anchors:
                    direction = random.choice(["front", "back"])
                    rules.append({"type": "dynamic_anchor", "anchors": anchors, "direction": direction})
                    has_anchor = True
    while len(rules) < n:
        k = random.randint(1, 5)
        rules.append({"type": "head_letters", "letters": _random_letter_set(k)})
    return rules


def op_choose_tiebreak() -> str:
    return random.choice(["longer_is_greater", "shorter_is_greater"])


def op_choose_order() -> str:
    return random.choice(["asc", "desc"])


def op_choose_comparator_mode(rules: List[Dict[str, Any]]) -> str:
    has_w = any(r.get("type") == "weights" for r in rules)
    has_dg = any(r.get("type") == "digraph_map" for r in rules)
    if has_w and has_dg:
        modes = [
            "feature_digraph_score_lex",
            "score_lex_feature_digraph",
            "lex_score_digraph_feature",
            "digraph_feature_lex_score",
        ]
    elif has_w and not has_dg:
        modes = ["score_then_lex", "lex_then_score", "feature_then_lex"]
    elif not has_w and has_dg:
        modes = ["digraph_feature_lex_score", "lex_then_score", "lex_only"]
    else:
        modes = ["lex_only", "feature_then_lex"]
    return random.choice(modes)


# -------------------- 排序与校验 --------------------
def op_sort_composite(
    words: Iterable[str],
    rules: List[Dict[str, Any]],
    order_type: str,
    length_tiebreak: str,
    comparator_mode: str,
) -> List[str]:
    rank_map = _build_rank_map(rules)
    score_map = _build_score_map(rules)
    digraph_rank_map, digraphs_list, dg_dir = _build_digraph_rank_and_list(rules)

    def make_key(w: str) -> Tuple[Any, ...]:
        feature_key = _word_features(w, rank_map)  # tuple
        digraph_seq = tuple(_word_digraph_seq(w, digraph_rank_map, digraphs_list, dg_dir)) if digraphs_list else ()
        score = _word_score(w, score_map)
        lex_seq = tuple(_word_rank_seq(w, rank_map))
        length_key = len(w) if length_tiebreak == "longer_is_greater" else -len(w)

        if comparator_mode == "feature_digraph_score_lex":
            key = (feature_key, digraph_seq, score, lex_seq, length_key, w)
        elif comparator_mode == "score_lex_feature_digraph":
            key = (score, lex_seq, feature_key, digraph_seq, length_key, w)
        elif comparator_mode == "lex_score_digraph_feature":
            key = (lex_seq, score, digraph_seq, feature_key, length_key, w)
        elif comparator_mode == "digraph_feature_lex_score":
            key = (digraph_seq, feature_key, lex_seq, score, length_key, w)
        elif comparator_mode == "score_then_lex":
            key = (score, lex_seq, length_key, w)
        elif comparator_mode == "lex_then_score":
            key = (lex_seq, score, length_key, w)
        elif comparator_mode == "feature_then_lex":
            key = (feature_key, lex_seq, length_key, w)
        else:  # lex_only
            key = (lex_seq, length_key, w)
        return key

    arr = sorted(list(words), key=make_key)
    if order_type == "desc":
        arr.reverse()
    return arr


def op_verify_by_rules(
    words: Iterable[str],
    sorted_words: Iterable[str],
    rules: List[Dict[str, Any]],
    order_type: str,
    length_tiebreak: str,
    comparator_mode: str,
) -> bool:
    recomputed = op_sort_composite(words, rules, order_type, length_tiebreak, comparator_mode)
    return list(recomputed) == list(sorted_words)


def op_verify_unique(
    words: Iterable[str],
    rules: List[Dict[str, Any]],
    order_type: str,
    length_tiebreak: str,
    comparator_mode: str,
) -> bool:
    """
    唯一解校验：检查复合 key 的全局唯一性（无两词共享同一核心 key）。
    核心 key 不含稳定维度 w，需全部转为可哈希的元组。
    """
    rank_map = _build_rank_map(rules)
    score_map = _build_score_map(rules)
    digraph_rank_map, digraphs_list, dg_dir = _build_digraph_rank_and_list(rules)

    def core_key(w: str) -> Tuple[Any, ...]:
        feature_key = _word_features(w, rank_map)
        digraph_seq = tuple(_word_digraph_seq(w, digraph_rank_map, digraphs_list, dg_dir)) if digraphs_list else ()
        score = _word_score(w, score_map)
        lex_seq = tuple(_word_rank_seq(w, rank_map))
        length_key = len(w) if length_tiebreak == "longer_is_greater" else -len(w)

        if comparator_mode == "feature_digraph_score_lex":
            return (feature_key, digraph_seq, score, lex_seq, length_key)
        elif comparator_mode == "score_lex_feature_digraph":
            return (score, lex_seq, feature_key, digraph_seq, length_key)
        elif comparator_mode == "lex_score_digraph_feature":
            return (lex_seq, score, digraph_seq, feature_key, length_key)
        elif comparator_mode == "digraph_feature_lex_score":
            return (digraph_seq, feature_key, lex_seq, score, length_key)
        elif comparator_mode == "score_then_lex":
            return (score, lex_seq, length_key)
        elif comparator_mode == "lex_then_score":
            return (lex_seq, score, length_key)
        elif comparator_mode == "feature_then_lex":
            return (feature_key, lex_seq, length_key)
        else:
            return (lex_seq, length_key)

    seen = set()
    for w in words:
        k = core_key(w)
        if k in seen:
            return False
        seen.add(k)
    return True


# -------------------- 规则说明生成 --------------------
def _fmt_letters_list(lst: List[str]) -> str:
    return "[ " + ", ".join(lst) + " ]"


def _fmt_weights(weights: Dict[str, int]) -> str:
    items = [f"{k}:{v}" for k, v in weights.items()]
    return "[ " + ", ".join(items) + " ]"


def op_build_rule_text(
    rules: List[Dict[str, Any]],
    order_type: str,
    length_tiebreak: str,
    comparator_mode: str,
) -> str:
    parts: List[str] = []
    parts.append("基础字母表为 a-z")
    parts.append(f"规则共 {len(rules)} 条")
    idx = 1
    for r in rules:
        t = r.get("type")
        if t == "head_letters":
            letters = [c for c in r.get("letters", []) if c in ALPHABET]
            parts.append(f"{idx}) 将以下字母置前并保持给定顺序: {_fmt_letters_list(letters)}")
        elif t == "tail_letters":
            letters = [c for c in r.get("letters", []) if c in ALPHABET]
            parts.append(f"{idx}) 将以下字母置后并保持给定顺序: {_fmt_letters_list(letters)}")
        elif t == "group_bias":
            group = r.get("group", "vowel")
            direction = r.get("direction", "front")
            grp_cn = "元音" if group == "vowel" else "辅音"
            dir_cn = "开头" if direction == "front" else "末尾"
            parts.append(f"{idx}) 将{grp_cn}整体移到{dir_cn}并保持相对顺序")
        elif t == "weights":
            weights = {k: v for k, v in r.get("weights", {}).items() if k in ALPHABET}
            parts.append(f"{idx}) 为字母设置权重用于分数计算: {_fmt_weights(weights)}")
        elif t == "digraph_map":
            digraphs = [dg for dg in r.get("digraphs", [])]
            dir_cn = "开头优先" if r.get("direction", "front") == "front" else "末尾优先"
            parts.append(f"{idx}) 将以下二字母组合视作单一单位并参与比较（{dir_cn}）: {_fmt_letters_list(digraphs)}")
        elif t == "dynamic_anchor":
            anchors = [c for c in r.get("anchors", []) if c in ALPHABET]
            dir_cn = "开头" if r.get("direction", "front") == "front" else "末尾"
            parts.append(f"{idx}) 按本题单词的出现频次选取锚字母并移到{dir_cn}: {_fmt_letters_list(anchors)}")
        idx += 1

    parts.append(f"比较模式为 {comparator_mode}")
    parts.append(f"排序方向为 {order_type}")
    parts.append(f"并列长度规则为 {length_tiebreak}")
    parts.append("答案格式为按顺序完整列出，使用逗号+空格分隔")

    return "; ".join(parts)


# -------------------- 兼容占位类 --------------------
class CustomCond:
    """占位条件类，以满足框架统一导入需求。默认恒真。"""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args: Any, **kwargs: Any) -> bool:
        return True