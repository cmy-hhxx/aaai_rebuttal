# word_sorting_mistake_5.py  —— 完整实现
import random
import unicodedata
from typing import List, Tuple, Dict

# ---------------- 基础工具 ----------------
WORD_POOL = [
    'fiancée', 'fiance', 'Ångström', 'ångström', 'Über', 'über',
    'café', 'cafe', 'résumé', 'Résumé', 'élève', 'naïve', 'naive',
    'coöperate', 'São', 'niño', 'jalapeño', 'français', 'Garçon',
    'Żubrówka', 'München', 'İstanbul', 'Łódź', 'Śląsk', 'Γειά',
    'Αθήνα', 'София', 'Łukasz', 'Žižka', 'Český', 'İzmir',
    'Łomża', 'Łęczyca', 'Zoë', 'Håkon', 'Crème', 'à la carte'
]

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)

def code_points(s: str) -> List[int]:
    return [ord(ch) for ch in nfc(s)]

def unicode_key(pair: Tuple[str, int]):
    word, freq = pair
    return (code_points(word), -freq)   # 频高→负更小，靠前

# ---------- operator: gen_word_data ----------
def gen_word_data(num: int) -> List[Tuple[str, int]]:
    return [(w, random.randint(5, 120)) for w in random.sample(WORD_POOL, num)]

# ---------- 模板函数 ----------
def _t_first_char(word_data):
    chars, seen = [], set()
    for w, _ in word_data:
        c = nfc(w)[0]
        if c not in seen:
            seen.add(c)
            chars.append((c, ord(c)))
    chars.sort(key=lambda x: x[1])
    true = '首字符升序为：' + ', '.join(f'{c}({cp:04X})' for c, cp in chars)
    if len(chars) >= 2:
        wrong = chars[:]
        i = random.randrange(len(chars)-1)
        wrong[i], wrong[i+1] = wrong[i+1], wrong[i]
        false = '首字符升序为：' + ', '.join(f'{c}({cp:04X})' for c, cp in wrong)
    else:
        false = true
    return true, false

def _t_min_word(word_data):
    minw = min(word_data, key=unicode_key)[0]
    true = f'排序后最靠前的单词是 “{minw}”'
    alt = random.choice([w for w, _ in word_data if w != minw])
    false = f'排序后最靠前的单词是 “{alt}”'
    return true, false

def _t_max_word(word_data):
    maxw = max(word_data, key=unicode_key)[0]
    true = f'排序后最后的单词是 “{maxw}”'
    alt = random.choice([w for w, _ in word_data if w != maxw])
    false = f'排序后最后的单词是 “{alt}”'
    return true, false

def _t_upper_lower(word_data):
    words = [w for w, _ in word_data]
    upper = random.choice(words)
    lower = upper.lower() if upper.lower() in words and upper.lower() != upper else random.choice([w for w in words if w != upper])
    uc, lc = ord(nfc(upper)[0]), ord(nfc(lower)[0])
    rel = '<' if uc < lc else '>'
    true = f'字符比较：{upper[0]}({uc:04X}) {rel} {lower[0]}({lc:04X})'
    false = f'字符比较：{upper[0]}({uc:04X}) {"<" if rel==">" else ">"} {lower[0]}({lc:04X})'
    return true, false

def _t_same_initial(word_data):
    groups: Dict[str, List[str]] = {}
    for w, _ in word_data:
        groups.setdefault(w[0], []).append(w)
    if any(len(g) >= 2 for g in groups.values()):
        g = random.choice([g for g in groups.values() if len(g) >= 2])
        w1, w2 = random.sample(g, 2)
    else:
        w1, w2 = random.sample([w for w, _ in word_data], 2)
    earlier = w1 if unicode_key(next(p for p in word_data if p[0]==w1)) < \
                    unicode_key(next(p for p in word_data if p[0]==w2)) else w2
    true = f'同首字母比较：在 “{w1}” 与 “{w2}” 中先出现的是 “{earlier}”'
    false = f'同首字母比较：在 “{w1}” 与 “{w2}” 中先出现的是 “{w2 if earlier==w1 else w1}”'
    return true, false

def _t_freq_tie(word_data):
    cf: Dict[str, List[Tuple[str,int]]] = {}
    for w, f in word_data:
        cf.setdefault(nfc(w).casefold(), []).append((w, f))
    dup = [v for v in cf.values() if len(v) >= 2]
    if not dup:
        return ('若出现完全相同单词，则按词频高者在前',
                '若出现完全相同单词，则按词频低者在前')
    (w1, f1), (w2, f2) = random.choice(dup)[:2]
    better, worse = (w1, w2) if f1 > f2 else (w2, w1)
    true = f'若拼写完全一致，则 {better}({max(f1,f2)}) 在前，{worse}({min(f1,f2)}) 在后'
    false = f'若拼写完全一致，则 {worse}({min(f1,f2)}) 在前，{better}({max(f1,f2)}) 在后'
    return true, false

def _t_char_position(word_data):
    words = [w for w, _ in word_data]
    w1, w2 = random.sample(words, 2)
    pos = random.randrange(min(len(w1), len(w2)))
    c1, c2 = nfc(w1)[pos], nfc(w2)[pos]
    cp1, cp2 = ord(c1), ord(c2)
    rel = '<' if cp1 < cp2 else '>'
    true = f'第 {pos+1} 个字符比较：{c1}({cp1:04X}) {rel} {c2}({cp2:04X})'
    false = f'第 {pos+1} 个字符比较：{c1}({cp1:04X}) {"<" if rel==">" else ">"} {c2}({cp2:04X})'
    return true, false

def _t_length_secondary(word_data):
    w1, w2 = random.sample([w for w, _ in word_data], 2)
    shorter, longer = (w1, w2) if len(w1) < len(w2) else (w2, w1)
    true = f'若前面字符都相同，则更短的单词 “{shorter}” 更靠前'
    false = f'若前面字符都相同，则更长的单词 “{longer}” 更靠前'
    return true, false

def _t_reverse_order(word_data):
    rev_first = max(word_data, key=unicode_key)[0]
    alt = random.choice([w for w, _ in word_data if w != rev_first])
    true = f'在完全倒序排序中，最前面的是 “{rev_first}”'
    false = f'在完全倒序排序中，最前面的是 “{alt}”'
    return true, false

TEMPLATES = [
    _t_first_char, _t_min_word, _t_max_word, _t_upper_lower, _t_same_initial,
    _t_freq_tie, _t_char_position, _t_length_secondary, _t_reverse_order
]

# ---------- 唯一解验证 ----------
def _verify_unique(flags: List[bool], correct_total: int, answer: str):
    n, count = len(flags), 0
    for mask in range(1 << n):
        if bin(mask).count('1') != correct_total:
            continue
        wrong_index = next((i for i in range(n) if not (mask & (1 << i))), None)
        ans = 'No' if wrong_index is None else str(wrong_index + 1)
        if ans == answer:
            count += 1
            if count > 1:
                break
    assert count == 1, "Puzzle not uniquely solvable!"

# ---------- operator: gen_complex_steps ----------
def gen_complex_steps(word_data: List[Tuple[str, int]], step_num: int):
    tpl_selected = random.sample(TEMPLATES, step_num)
    true_texts, false_texts = zip(*(tpl(word_data) for tpl in tpl_selected))

    # 生成错误数量：80% 至少 1 个错误，20% 全对
    if random.random() < 0.8:
        err_cnt = random.choice([1, 2])
        err_cnt = min(err_cnt, step_num - 1)
    else:
        err_cnt = 0

    wrong_idx_set = set(random.sample(range(step_num), err_cnt))
    flags = [i not in wrong_idx_set for i in range(step_num)]

    answer = 'No' if err_cnt == 0 else str(min(wrong_idx_set) + 1)
    correct_total = flags.count(True)

    steps_render = [
        f'步骤 {i+1}. ' + (true_texts[i] if flags[i] else false_texts[i])
        for i in range(step_num)
    ]

    _verify_unique(flags, correct_total, answer)

    return {'steps': steps_render, 'answer': answer, 'correct_total': correct_total}