# pf_word_sorting_0.py
from functools import cmp_to_key

def build_custom_alphabet(moved_letters):
    """
    构造自定义字母表顺序：
    - moved_letters 依次放到最前（如 ['x','l','g'] 表示 x 最小，其次 l，其次 g）
    - 其余字母按 a~z 顺序接在后面
    返回：dict {char: rank}，rank越小表示越靠前。
    """
    moved = [c.lower() for c in moved_letters]
    base = [chr(ord('a') + i) for i in range(26)]
    rest = [c for c in base if c not in moved]
    alphabet = moved + rest
    return {c: i for i, c in enumerate(alphabet)}

def _cmp_words(a, b, rank):
    """
    比较两个单词 a,b 在给定 rank 下的字典序（升序）：
    - 逐字符比较
    - 若前缀相同，短者更小
    """
    a = a.lower()
    b = b.lower()
    n = min(len(a), len(b))
    for i in range(n):
        ra = rank.get(a[i], 10**9)
        rb = rank.get(b[i], 10**9)
        if ra != rb:
            return -1 if ra < rb else 1
    if len(a) == len(b):
        return 0
    return -1 if len(a) < len(b) else 1

def sort_words_by_custom_alphabet(words, moved_letters, reverse=True):
    """
    按“将 moved_letters 移到字母表开头”的自定义字母表进行排序。
    reverse=True 表示降序（题目要求）。
    返回：排序后的单词列表。
    """
    rank = build_custom_alphabet(moved_letters)
    key = cmp_to_key(lambda x, y: _cmp_words(x, y, rank))
    return sorted(list(words), key=key, reverse=bool(reverse))