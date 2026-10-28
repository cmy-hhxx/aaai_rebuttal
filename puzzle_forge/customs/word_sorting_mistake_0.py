import random
import re
import string

# ==========================================
# 1. 基础词库配置
# ==========================================

REAL_COMPLEX_WORDS = [
    "Absquatulate", "Anachronism", "Boulevard", "Cacophony", "Chrysanthemum",
    "Defenestration", "Ephemeral", "Flabbergasted", "Gobbledygook", "Hippopotamus",
    "Iconoclast", "Juxtaposition", "Kaleidoscope", "Lackadaisical", "Magnanimous",
    "Nonsequitur", "Obfuscation", "Pandemonium", "Quizzical", "Rambunctious",
    "Schadenfreude", "Tintinnabulation", "Ubiquitous", "Ventriloquist", "Wunderkind",
    "Xenophobia", "Ylang-ylang", "Zeitgeist", "Algorithm", "Bioluminescence",
    "Cryptography", "Dodecahedron", "Etymology", "Photosynthesis", "Quantum",
    "Thermodynamics", "Vertebrate", "Xylophone", "Yachtsmanship", "Zoology",
    "Ambidextrous", "Circumlocution", "Idiosyncrasy", "Onomatopoeia", "Superfluous",
    "Acquiesce", "Bourgeoisie", "Connoisseur", "Demagogue", "Epiphany"
]

PREFIXES = [
    "ad", "anti", "astro", "auto", "bi", "bio", "circum", "con", "contra", "cyber",
    "de", "dis", "dys", "endo", "epi", "exo", "extra", "fore", "geo", "hemi",
    "hetero", "homo", "hyper", "hypo", "in", "infra", "inter", "intra", "iso",
    "kilo", "macro", "mal", "meta", "micro", "mid", "mis", "mono", "multi",
    "neo", "non", "omni", "out", "over", "pan", "para", "per", "peri", "poly",
    "post", "pre", "pro", "proto", "pseudo", "quadri", "re", "retro",
    "semi", "sub", "super", "supra", "syn", "tele", "trans", "tri", "ultra", "un", "uni"
]

ROOTS = [
    "anthrop", "arch", "aud", "bell", "brev", "capit", "cede", "cent", "chron",
    "cide", "clam", "clud", "cogn", "cord", "corp", "cred", "cur", "cycl",
    "dem", "dict", "doc", "duc", "dur", "equ", "fac", "fer", "fid", "fin",
    "flect", "flu", "form", "fort", "fract", "fus", "gen", "grad", "gram",
    "graph", "grav", "greg", "gress", "hab", "hydr", "ject", "jud", "junct",
    "jur", "lab", "later", "leg", "lig", "loc", "log", "luc", "lum", "lun",
    "magn", "mal", "man", "mand", "mar", "mater", "mech", "mem", "ment",
    "meter", "migr", "min", "mit", "mob", "mon", "morph", "mort", "mot",
    "mut", "narr", "nat", "nav", "neg", "nom", "not", "noun", "nov", "numer",
    "onym", "oper", "opt", "ord", "orig", "orth", "pale", "pan", "pater",
    "path", "ped", "pel", "pend", "pens", "phil", "phon", "photo", "phys",
    "plex", "plic", "plur", "pod", "poli", "pon", "pop", "port", "pos",
    "pot", "prim", "princ", "priv", "prob", "psych", "punct", "put", "pyr",
    "quad", "quer", "quest", "quir", "quis", "rad", "ram", "rect", "reg",
    "rid", "rog", "rupt", "sanct", "scend", "sci", "scop", "scrib", "script",
    "sect", "sed", "sens", "sent", "sequ", "serv", "sign", "simil", "sist",
    "soci", "sol", "solv", "son", "soph", "spec", "spect", "spir", "spond",
    "stat", "strict", "struct", "sum", "tact", "tang", "tech", "temp", "ten",
    "tend", "tens", "term", "terr", "test", "text", "the", "therm", "tort",
    "tract", "trib", "trud", "urb", "vac", "vad", "val", "var", "ven", "ver",
    "vers", "vert", "vest", "via", "vic", "vid", "vict", "vin", "vis", "viv",
    "voc", "vol", "volv", "vor", "xen", "xyl", "zo", "zym"
]

SUFFIXES = [
    "ability", "able", "ac", "acean", "aceous", "ade", "age", "aholic",
    "al", "algia", "an", "ance", "ant", "ar", "ard", "arian", "arium", "ary",
    "ate", "ation", "ative", "cide", "cracy", "crat", "cule", "cy", "cycle",
    "dom", "dox", "ed", "ee", "eer", "emia", "en", "ence", "ency", "ent", "er",
    "ern", "escence", "ese", "esque", "ess", "est", "etic", "ette", "ful",
    "fy", "gam", "gamy", "gon", "gonic", "hood", "ial", "ian", "iasis", "iatry",
    "ible", "ic", "ice", "icle", "ics", "id", "ide", "ile", "ine", "ing", "ion",
    "ior", "ious", "ique", "ise", "ish", "ism", "ist", "ite",
    "itis", "ity", "ium", "ive", "ize", "less", "let", "like", "ling", "log",
    "logy", "ly", "ment", "ness", "oid", "ology", "oma", "onym", "opia", "opsy",
    "or", "ory", "osis", "ous", "path", "pathy", "phile", "phobia", "phone",
    "phyte", "plegia", "plegic", "pnea", "scopy", "scope", "ship", "sion",
    "some", "sophy", "tion", "tome", "tomy", "tude", "ty", "ular", "uous",
    "ure", "ward", "ware", "wise", "zure"
]

# ==========================================
# 2. 内部辅助函数
# ==========================================

def _clean_format(w: str):
    """
    格式化：仅保留字母，移除连字符等，并首字母大写
    """
    clean_w = ''.join([c for c in w if c.isalpha()])
    return clean_w.capitalize()

def _introduce_typo(w: str):
    """
    仅允许字母替换的干扰
    """
    if len(w) < 4: return w
    chars = list(w)
    idx = random.randint(1, len(w) - 2)
    char = chars[idx].lower()
    
    # 纯字母混淆表
    typo_map = {
        'a': ['e', 'o'], 'b': ['d', 'p'], 'c': ['k', 's'], 
        'e': ['a', 'i'], 'g': ['q'], 'i': ['l', 'e'], 
        'l': ['i'], 'o': ['a', 'e'], 's': ['z', 'c'], 
        't': ['f'], 'z': ['s'], 'm': ['n'], 'n': ['m'],
        'p': ['b', 'q'], 'q': ['g', 'p']
    }
    
    if char in typo_map:
        rep = random.choice(typo_map[char])
    else:
        rep = random.choice(string.ascii_lowercase)
        
    if chars[idx].isupper():
        rep = rep.upper()
    
    chars[idx] = rep
    return ''.join(chars)

def _generate_procedural_word():
    r = random.random()
    if r < 0.2:
        raw = random.choice(ROOTS) + random.choice(ROOTS) + random.choice(SUFFIXES)
    elif r < 0.5:
        raw = random.choice(PREFIXES) + random.choice(ROOTS) + random.choice(SUFFIXES)
    elif r < 0.8:
        raw = random.choice(ROOTS) + random.choice(SUFFIXES)
    else:
        raw = random.choice(PREFIXES) + random.choice(PREFIXES) + random.choice(ROOTS)
    
    return _clean_format(raw)

def lex_key(s: str):
    return s.lower()

# ==========================================
# 3. YAML 调用的核心接口函数
# ==========================================

def make_words(n: int, seed: int):
    """
    对应 YAML: formula: make_words(word_num, seed)
    """
    random.seed(seed)
    words = set()
    attempts = 0
    
    while len(words) < n and attempts < n * 100:
        attempts += 1
        if random.random() < 0.3:
            base = _clean_format(random.choice(REAL_COMPLEX_WORDS))
        else:
            base = _generate_procedural_word()
            
        if random.random() < 0.15:
            base = _introduce_typo(base)
            
        if base.isalpha():
            words.add(base)
            
    return list(words)


def make_thoughts(words, error_type: str, err_step: int, seed: int):
    """
    对应 YAML: formula: make_thoughts(words, error_type, err_step, seed)
    """
    random.seed(seed)
    arr = list(words)
    thoughts = []
    sorted_list = [arr[0]] 
    
    # 纯字母非法词
    illegal_word = "ERROR" + "".join(random.choices(string.ascii_uppercase, k=3))

    for k in range(1, len(arr)):
        to_insert = arr[k]
        before = list(sorted_list)
        
        # 寻找正确插入位置
        pos = 0
        while pos < len(sorted_list) and lex_key(sorted_list[pos]) <= lex_key(to_insert):
            pos += 1
        
        planned_pos = pos
        result = sorted_list[:pos] + [to_insert] + sorted_list[pos:]

        # 错误注入
        if err_step == k and error_type != 'none':
            if error_type == 'not_in_list':
                result = sorted_list[:pos] + [illegal_word] + sorted_list[pos:]
            elif error_type == 'misorder':
                new_pos = pos - 1 if pos > 0 else pos + 1
                planned_pos = new_pos
                result = sorted_list[:new_pos] + [to_insert] + sorted_list[new_pos:]
            elif error_type == 'omission':
                result = list(sorted_list)
            elif error_type == 'duplicate':
                result = sorted_list[:pos] + [to_insert, to_insert] + sorted_list[pos:]
            elif error_type == 'case_misunderstanding':
                # ASCII 排序错误模拟
                pos_wrong = 0
                while pos_wrong < len(sorted_list) and sorted_list[pos_wrong] <= to_insert:
                    pos_wrong += 1
                planned_pos = pos_wrong
                result = sorted_list[:pos_wrong] + [to_insert] + sorted_list[pos_wrong:]

        sorted_list = list(result)
        
        # 生成思考文本
        line = f"思考 {k}: 已排序=[{','.join(before)}]; 待插入={to_insert}; 计划位置={planned_pos}; 结果=[{','.join(result)}]"
        thoughts.append(line)

    return thoughts


def parse_step(line: str):
    """
    解析思考步骤的辅助函数
    """
    m_k = re.search(r"思考\s+(\d+)\s*:", line)
    k = int(m_k.group(1)) if m_k else -1
    
    m_before = re.search(r"已排序=\[(.*?)\];", line)
    before_list = m_before.group(1).split(",") if m_before and m_before.group(1) else []
    
    m_ins = re.search(r"待插入=([^;]+);", line)
    to_insert = m_ins.group(1).strip() if m_ins else ""
    
    m_pos = re.search(r"计划位置=(\d+);", line)
    planned_pos = int(m_pos.group(1)) if m_pos else -1
    
    m_res = re.search(r"结果=\[(.*?)\]$", line)
    result_list = m_res.group(1).split(",") if m_res and m_res.group(1) else []
    
    return k, before_list, to_insert, planned_pos, result_list


def check_first_error(words, thoughts):
    """
    对应 YAML: formula: check_first_error(words, thoughts)
    """
    word_set = set(w for w in words)
    sorted_ref = [words[0]]

    for line in thoughts:
        k, before, to_insert, planned_pos, result = parse_step(line)
        
        # 清洗空字符串
        before = [x for x in before if x]
        result = [x for x in result if x]

        # 检查 1: 初始状态是否匹配
        if before != sorted_ref: 
            return k if k != -1 else "No"
        
        # 检查 2: 结果中是否包含非法词
        for x in result:
            if x not in word_set and "ERROR" not in x: # 允许注入的非法词通过后续逻辑判定
                return k if k != -1 else "No"
        
        # 计算正确的下一步
        if 0 <= k < len(words):
            expected = words[k]
        else:
            expected = to_insert # Fallback
            
        pos = 0
        while pos < len(sorted_ref) and lex_key(sorted_ref[pos]) <= lex_key(expected):
            pos += 1
        correct = sorted_ref[:pos] + [expected] + sorted_ref[pos:]
        
        # 检查 3: 比较结果
        if len(result) != len(correct): return k 
        if sorted(result, key=lex_key) != sorted(correct, key=lex_key): return k 
        if result != correct: return k 
        
        # 更新参考状态
        sorted_ref = list(result)
        
    return "No"