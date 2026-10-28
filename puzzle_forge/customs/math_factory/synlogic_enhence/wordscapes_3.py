# wordscapes_11.py
import random
import json
from typing import List, Tuple, Dict, Optional, Set

# ------------------------
# Word pools (lowercase; clean)
# ------------------------
WORDS_5 = [
    'amber','angle','apple','apron','arbor','baker','basil','beach','beads','beams','beech','berry','blaze','bleak',
    'board','brave','brick','bring','brink','brush','cable','canoe','caper','cedar','chess','chili','clamp','cliff',
    'coral','crane','cream','creek','crest','crown','dairy','daisy','darts','delta','dodge','dough','draft','drain',
    'eagle','earth','elbow','ember','fable','ferry','fiery','flame','flask','flora','forge','frost','giant','glade',
    'globe','grain','grape','graph','grave','grind','grove','harsh','honey','hover','humor','ivory','jelly','joust',
    'knock','laden','laser','lemon','linen','liver','mango','maple','marsh','melon','mince','mirth','mossy','mound',
    'naval','ocean','olive','onion','orbit','pearl','petal','piano','piper','plain','prism','quail','quick','radar',
    'raven','ridge','rider','river','robin','rover','salsa','sandy','scarf','scent','shade','shale','sheep','shelf',
    'shore','shrub','sleet','spice','spine','spore','stare','steam','stone','straw','sugar','swirl','table','tango',
    'taper','tease','tempo','tenor','terra','thorn','tiger','toast','trace','trail','tread','trend','trick','trout',
    'umbra','vapor','vines','vivid','wafer','waltz','wheat','whirl','wiser','world','wreck','yacht','yeast','zesty'
]

WORDS_6 = [
    'absorb','across','anchor','animal','answer','arabic','archer','beacon','beauty','beetle','belief','branch',
    'breath','bridge','bright','bronze','bubble','butter','cactus','candle','carpet','cashew','caster','cattle','cereal',
    'charge','cheese','cherry','circle','cobalt','cocoon','coffee','cooler','corpus','cotton','cougar','coyote',
    'damage','dancer','danger','desert','devour','dragon','drawer','drowsy','fabric','fairly',
    'falcon','fathom','fealty','feeder','feline','fervor','filter','flavor','flight','flower','forest','forget','fossil',
    'frozen','fusion','garden','garlic','gentle','ginger','glider','golden','gravel','hammer','harbor',
    'helium','honest','humane','island','jasper','junior','keeper','kernel','ladder','lament','legend','little','magnet',
    'marble','market','meadow','meteor','mingle','minnow','mirror','molten','monkey','nectar','nickel','noodle',
    'number','object','octave','office','oldest','orange','origin','palace','papaya','parade','pepper','photon','pickle',
    'pillow','planet','powder','pretty','rabbit','racket','random','ranger','rattle','ribbon','rocket','saddle',
    'salmon','school','sconce','sculpt','settle','shadow','shrimp','silver','simple','socket','sodium','softer','sorbet',
    'spider','spirit','sponge','spring','stable','stereo','stoney','stream','stripe','strong','sturdy','summer','sunset',
    'tangent','temple','throne','timber','tomato','tongue','tunnel','turret','turtle','uneven','vacuum','violet','walnut',
    'warmer','weaver','wheels','whisper','window','winter','wizard','yellow','zipper'
]
WORDS_6 = list(dict.fromkeys(WORDS_6))

VOWELS = set('aeiouy')
def is_vowel(ch: str) -> bool:
    return ch.isalpha() and ch.lower() in VOWELS
def is_consonant(ch: str) -> bool:
    return ch.isalpha() and ch.lower() not in VOWELS

# ------------------------
# Utility: mask and pretty
# ------------------------
def grid_to_string(mask: List[List[str]]) -> str:
    return '\n'.join(''.join(row) for row in mask)

def mask_to_string(mask: List[List[str]]) -> str:
    n = len(mask)
    header = '    ' + ' '.join(str(i) for i in range(1, n + 1))
    lines = [header]
    for r in range(n):
        lines.append(f'{r+1:>2}: ' + ''.join(mask[r]))
    return '\n'.join(lines)

def locks_to_text(locks: List[Tuple[int,int,str]]) -> str:
    if not locks:
        return '无'
    return '; '.join(f'({r},{c}):{ch}' for (r, c, ch) in locks)

def rules_to_text(rules: List[Dict]) -> str:
    if not rules:
        return '无其他规则'
    lines = []
    for i, r in enumerate(rules, 1):
        lines.append(f"({i}) {r['text']}")
    return '; '.join(lines)

def words_to_brackets(words: List[str]) -> str:
    return '[' + ', '.join(words) + ']'

def grid_to_json(grid: List[List[str]]) -> str:
    return json.dumps(grid, ensure_ascii=False)

# ------------------------
# Core grid mechanics
# ------------------------
def build_positions(mask: List[List[str]], direction: str, length: int) -> List[Tuple[int,int]]:
    n = len(mask)
    starts = []
    if direction == 'across':
        for r in range(n):
            c = 0
            while c < n:
                if mask[r][c] == '0':
                    start = c
                    while c < n and mask[r][c] == '0':
                        c += 1
                    run_len = c - start
                    if run_len >= length:
                        for sc in range(start, start + run_len - length + 1):
                            starts.append((r, sc))
                else:
                    c += 1
    else:  # down
        for c in range(n):
            r = 0
            while r < n:
                if mask[r][c] == '0':
                    start = r
                    while r < n and mask[r][c] == '0':
                        r += 1
                    run_len = r - start
                    if run_len >= length:
                        for sr in range(start, start + run_len - length + 1):
                            starts.append((sr, c))
                else:
                    r += 1
    return starts

def coverable_cells(mask: List[List[str]], length: int) -> Set[Tuple[int,int]]:
    cells: Set[Tuple[int,int]] = set()
    for (r, c) in build_positions(mask, 'across', length):
        for i in range(length):
            cells.add((r, c + i))
    for (r, c) in build_positions(mask, 'down', length):
        for i in range(length):
            cells.add((r + i, c))
    return cells

def normalize_grid(grid: List[List[Optional[str]]]) -> List[List[str]]:
    out = []
    for row in grid:
        new_row = []
        for cell in row:
            if cell in ('x', 'X'):
                new_row.append('X')
            elif cell is None:
                new_row.append('X')
            elif cell == ' ':
                new_row.append(' ')
            else:
                new_row.append(cell.lower())
        out.append(new_row)
    return out

def canonical_grid_string(grid: List[List[Optional[str]]]) -> str:
    norm = normalize_grid(grid)
    return '|'.join(''.join(row) for row in norm)

def extract_placements(grid: List[List[Optional[str]]],
                       mask: List[List[str]],
                       length: int,
                       words: List[str],
                       direction: str) -> List[Tuple[Tuple[int,int], str]]:
    n = len(mask)
    starts = build_positions(mask, direction, length)
    placements = []
    for (r, c) in starts:
        chars = []
        ok = True
        for i in range(length):
            rr = r + (i if direction == 'down' else 0)
            cc = c + (i if direction == 'across' else 0)
            ch = grid[rr][cc]
            if ch is None or ch == ' ':
                ok = False
                break
            chars.append(ch.lower())
        if ok:
            s = ''.join(chars)
            if s in words:
                placements.append(((r, c), s))
    return placements

def a1z26_sum(chars: List[str]) -> int:
    total = 0
    for ch in chars:
        if ch is not None and ch != ' ' and ch.isalpha():
            total += (ord(ch.lower()) - 96)
    return total

def validate_grid_basic(grid: List[List[str]], mask: List[List[str]]) -> bool:
    if not grid or not mask or len(grid) != len(mask):
        return False
    n = len(mask)
    for r in range(n):
        if len(grid[r]) != len(mask[r]):
            return False
    for r in range(n):
        for c in range(n):
            gch = grid[r][c]
            mch = mask[r][c]
            if gch not in ('X', ' ') and not (len(gch) == 1 and gch.isalpha() and gch.islower()):
                return False
            if mch == 'X' and gch != 'X':
                return False
    return True

def try_place_count_unique_grids(
    words_across: List[str],
    words_down: List[str],
    mask: List[List[str]],
    locks: Dict[Tuple[int,int], str],
    rules: Optional[List[Dict]] = None,
    max_unique: int = 2,
    deterministic: bool = False
) -> Tuple[Set[str], Dict[str, List[List[Optional[str]]]]]:
    n = len(mask)
    L = len(words_across[0]) if words_across else len(words_down[0])
    base = [[' ' if mask[r][c] == '0' else None for c in range(n)] for r in range(n)]
    lock0 = {(r-1, c-1): ch for (r, c), ch in locks.items()} if isinstance(locks, dict) else {}

    for (rr, cc), ch in lock0.items():
        if not (0 <= rr < n and 0 <= cc < n and mask[rr][cc] == '0'):
            return set(), {}
        if base[rr][cc] != ' ' and base[rr][cc].lower() != ch.lower():
            return set(), {}
        base[rr][cc] = ch.lower()

    across_starts = build_positions(mask, 'across', L)
    down_starts = build_positions(mask, 'down', L)

    unique_set: Set[str] = set()
    rep: Dict[str, List[List[Optional[str]]]] = {}

    def can_write(word: str, r: int, c: int, direction: str, g, occ_same_dir: Set[Tuple[int,int]]) -> bool:
        for i, ch in enumerate(word):
            rr = r + (i if direction == 'down' else 0)
            cc = c + (i if direction == 'across' else 0)
            if rr < 0 or rr >= n or cc < 0 or cc >= n or mask[rr][cc] != '0':
                return False
            if (rr, cc) in lock0 and lock0[(rr, cc)].lower() != ch.lower():
                return False
            if g[rr][cc] != ' ' and g[rr][cc].lower() != ch.lower():
                return False
            if (rr, cc) in occ_same_dir:
                return False
        return True

    def write_word(word: str, r: int, c: int, direction: str, g, occ_same_dir: Set[Tuple[int,int]]):
        for i, ch in enumerate(word):
            rr = r + (i if direction == 'down' else 0)
            cc = c + (i if direction == 'across' else 0)
            g[rr][cc] = ch.lower()
            occ_same_dir.add((rr, cc))

    def check_rules_and_coverage(grid: List[List[Optional[str]]]) -> bool:
        if rules:
            a_pl = extract_placements(grid, mask, L, words_across, 'across')
            d_pl = extract_placements(grid, mask, L, words_down, 'down')
            left_across = min(a_pl, key=lambda rcw: (rcw[0][1], rcw[0][0])) if a_pl else None
            top_down = min(d_pl, key=lambda rcw: (rcw[0][0], rcw[0][1])) if d_pl else None
            across_rows = {rc[0] for rc, _ in a_pl}
            down_cols = {rc[1] for rc, _ in d_pl}

            row_letters: List[List[str]] = [[] for _ in range(n)]
            col_letters: List[List[str]] = [[] for _ in range(n)]
            for rr in range(n):
                for cc in range(n):
                    ch = grid[rr][cc]
                    if ch is not None and ch != ' ':
                        row_letters[rr].append(ch)
                        col_letters[cc].append(ch)

            for r in rules:
                t = r['type']
                p = r['params']
                if t == 'vc_cell':
                    rr, cc, kind = p['r'] - 1, p['c'] - 1, p['kind']
                    ch = grid[rr][cc]
                    if ch is None or ch == ' ':
                        return False
                    if kind == 'vowel' and not is_vowel(ch):
                        return False
                    if kind == 'consonant' and not is_consonant(ch):
                        return False
                elif t == 'row_vowel_count':
                    rr, cnt = p['r'] - 1, p['count']
                    csum = sum(1 for ch in row_letters[rr] if is_vowel(ch))
                    if csum != cnt:
                        return False
                elif t == 'col_consonant_count':
                    cc, cnt = p['c'] - 1, p['count']
                    csum = sum(1 for ch in col_letters[cc] if is_consonant(ch))
                    if csum != cnt:
                        return False
                elif t == 'row_sum_parity':
                    rr = p['r'] - 1
                    parity = p['parity']
                    sm = a1z26_sum(row_letters[rr])
                    if (sm % 2 == 0 and parity != 'even') or (sm % 2 == 1 and parity != 'odd'):
                        return False
                elif t == 'global_letter_exact':
                    ch0 = p['ch'].lower()
                    cnt0 = p['count']
                    cnt = 0
                    for rr in range(n):
                        for cc in range(n):
                            ch = grid[rr][cc]
                            if ch is not None and ch != ' ' and ch.lower() == ch0:
                                cnt += 1
                    if cnt != cnt0:
                        return False
                elif t == 'distinct_rows_across':
                    if len(across_rows) != len(a_pl):
                        return False
                elif t == 'distinct_cols_down':
                    if len(down_cols) != len(d_pl):
                        return False
                elif t == 'compare_letters':
                    if not left_across or not top_down:
                        return False
                    a_word = left_across[1]
                    d_word = top_down[1]
                    a_ch = a_word[0]
                    d_ch = d_word[-1]
                    if p['relation'] == 'earlier' and not (a_ch < d_ch):
                        return False
                    if p['relation'] == 'later' and not (a_ch > d_ch):
                        return False
                elif t == 'anchor_compare':
                    if not left_across or not top_down:
                        return False
                    a_word = left_across[1]
                    d_word = top_down[1]
                    a_pos = p['a_pos']
                    d_pos = p['d_pos']
                    a_ch = a_word[0] if a_pos == 'first' else a_word[-1]
                    d_ch = d_word[0] if d_pos == 'first' else d_word[-1]
                    if p['relation'] == 'same':
                        if a_ch != d_ch:
                            return False
                    else:
                        if a_ch == d_ch:
                            return False
                else:
                    return False

        a_pl = extract_placements(grid, mask, L, words_across, 'across')
        d_pl = extract_placements(grid, mask, L, words_down, 'down')
        covered: Set[Tuple[int,int]] = set()
        for (r0, c0), _ in a_pl:
            for i in range(L):
                covered.add((r0, c0 + i))
        for (r0, c0), _ in d_pl:
            for i in range(L):
                covered.add((r0 + i, c0))
        for rr in range(n):
            for cc in range(n):
                ch = grid[rr][cc]
                if ch is not None and ch != ' ':
                    if (rr, cc) not in covered:
                        return False
        return True

    a_starts = across_starts[:]
    d_starts = down_starts[:]
    if not deterministic:
        random.shuffle(a_starts)
        random.shuffle(d_starts)

    def place_across(idx: int, g, occ_across: Set[Tuple[int,int]]):
        if len(unique_set) >= max_unique:
            return
        if idx == len(words_across):
            place_down(0, g, set())
            return
        w = words_across[idx]
        for (r, c) in a_starts:
            if can_write(w, r, c, 'across', g, occ_across):
                g2 = [row[:] for row in g]
                occ2 = set(occ_across)
                write_word(w, r, c, 'across', g2, occ2)
                place_across(idx + 1, g2, occ2)
                if len(unique_set) >= max_unique:
                    return

    def place_down(idx: int, g, occ_down: Set[Tuple[int,int]]):
        if len(unique_set) >= max_unique:
            return
        if idx == len(words_down):
            if check_rules_and_coverage(g):
                key = canonical_grid_string(g)
                if key not in unique_set:
                    unique_set.add(key)
                    rep[key] = [row[:] for row in g]
            return
        w = words_down[idx]
        for (r, c) in d_starts:
            if can_write(w, r, c, 'down', g, occ_down):
                g2 = [row[:] for row in g]
                occ2 = set(occ_down)
                write_word(w, r, c, 'down', g2, occ2)
                place_down(idx + 1, g2, occ2)
                if len(unique_set) >= max_unique:
                    return

    place_across(0, base, set())
    return unique_set, rep

def sample_words(length: int, k: int) -> List[str]:
    pool = WORDS_5 if length == 5 else WORDS_6
    pool = [w for w in pool if len(w) == length]
    if not pool:
        pool = [w for w in WORDS_5 if len(w) == length]
    if k > len(pool):
        k = len(pool)
    return random.sample(pool, k)

def make_mask(n: int, rows: List[int], cols: List[int]) -> List[List[str]]:
    mask = [['X'] * n for _ in range(n)]
    for r in rows:
        for c in range(n):
            mask[r][c] = '0'
    for c in cols:
        for r in range(n):
            mask[r][c] = '0'
    return mask

def derive_rules_from_grid(grid: List[List[Optional[str]]],
                           mask: List[List[str]],
                           L: int,
                           across_words: List[str],
                           down_words: List[str],
                           n_rules_vc: int,
                           n_rules_row: int,
                           n_rules_col: int,
                           n_rules_parity: int,
                           use_distinct_rows_across: bool,
                           use_distinct_cols_down: bool,
                           use_compare_letters: bool,
                           use_anchor_equal: bool,
                           use_global_letter_exact: bool) -> List[Dict]:
    n = len(mask)
    rules: List[Dict] = []
    a_pl = extract_placements(grid, mask, L, across_words, 'across')
    d_pl = extract_placements(grid, mask, L, down_words, 'down')

    inter_cells = []
    for (ar, ac), aw in a_pl:
        for i in range(L):
            rr = ar
            cc = ac + i
            for (dr, dc), dw in d_pl:
                for j in range(L):
                    rr2 = dr + j
                    cc2 = dc
                    if rr2 == rr and cc2 == cc:
                        ch = grid[rr][cc]
                        if ch is not None and ch != ' ':
                            inter_cells.append((rr, cc, ch))

    random.shuffle(inter_cells)
    vc_targets = inter_cells[:]
    if len(vc_targets) < n_rules_vc:
        filled_cells = []
        for r in range(n):
            for c in range(n):
                ch = grid[r][c]
                if ch is not None and ch != ' ':
                    filled_cells.append((r, c, ch))
        random.shuffle(filled_cells)
        for fc in filled_cells:
            if fc not in vc_targets:
                vc_targets.append(fc)
    for i in range(min(n_rules_vc, len(vc_targets))):
        rr, cc, ch = vc_targets[i]
        kind = 'vowel' if is_vowel(ch) else 'consonant'
        rules.append({
            'type': 'vc_cell',
            'params': {'r': rr + 1, 'c': cc + 1, 'kind': kind},
            'text': f'坐标({rr+1},{cc+1})处的字母为{"元音" if kind=="vowel" else "辅音"}'
        })

    candidates_rows = list(range(n))
    random.shuffle(candidates_rows)
    added = 0
    for rr in candidates_rows:
        cnt = 0
        filled_any = False
        for cc in range(n):
            ch = grid[rr][cc]
            if ch is not None and ch != ' ':
                filled_any = True
                if is_vowel(ch):
                    cnt += 1
        if filled_any and 1 <= cnt <= L and added < n_rules_row:
            rules.append({
                'type': 'row_vowel_count',
                'params': {'r': rr + 1, 'count': cnt},
                'text': f'第{rr+1}行中已填字母的元音数量恰好为{cnt}（仅统计字母格，忽略空格与X）'
            })
            added += 1
        if added >= n_rules_row:
            break

    candidates_cols = list(range(n))
    random.shuffle(candidates_cols)
    added_col = 0
    for cc in candidates_cols:
        cnt = 0
        filled_any = False
        for rr in range(n):
            ch = grid[rr][cc]
            if ch is not None and ch != ' ':
                filled_any = True
                if is_consonant(ch):
                    cnt += 1
        if filled_any and 1 <= cnt <= L and added_col < n_rules_col:
            rules.append({
                'type': 'col_consonant_count',
                'params': {'c': cc + 1, 'count': cnt},
                'text': f'第{cc+1}列中已填字母的辅音数量恰好为{cnt}（仅统计字母格，忽略空格与X）'
            })
            added_col += 1
        if added_col >= n_rules_col:
            break

    candidates_rows2 = list(range(n))
    random.shuffle(candidates_rows2)
    added_parity = 0
    for rr in candidates_rows2:
        chars = []
        for cc in range(n):
            ch = grid[rr][cc]
            if ch is not None and ch != ' ':
                chars.append(ch)
        if not chars:
            continue
        sm = a1z26_sum(chars)
        parity = 'even' if sm % 2 == 0 else 'odd'
        rules.append({
            'type': 'row_sum_parity',
            'params': {'r': rr + 1, 'parity': parity},
            'text': f'按a1z26映射求和后，第{rr+1}行已填字母的总和为{"偶数" if parity=="even" else "奇数"}（a=1,...,z=26；仅统计字母格）'
        })
        added_parity += 1
        if added_parity >= n_rules_parity:
            break

    if use_distinct_rows_across and a_pl and len(a_pl) >= 2:
        rows = {rc[0] for rc, _ in a_pl}
        if len(rows) == len(a_pl):
            rules.append({
                'type': 'distinct_rows_across',
                'params': {},
                'text': '所有Across单词的起始行互不相同'
            })

    if use_distinct_cols_down and d_pl and len(d_pl) >= 2:
        cols = {rc[1] for rc, _ in d_pl}
        if len(cols) == len(d_pl):
            rules.append({
                'type': 'distinct_cols_down',
                'params': {},
                'text': '所有Down单词的起始列互不相同'
            })

    if use_compare_letters and a_pl and d_pl:
        left_across = min(a_pl, key=lambda rcw: (rcw[0][1], rcw[0][0]))
        top_down = min(d_pl, key=lambda rcw: (rcw[0][0], rcw[0][1]))
        a_ch = left_across[1][0]
        d_ch = top_down[1][-1]
        relation = 'earlier' if a_ch < d_ch else 'later'
        text = (
            '最左侧Across单词（按起始列最小，若并列取起始行最小）的首字母字母序'
            f'{"早于" if relation=="earlier" else "晚于"}'
            '最上方Down单词（按起始行最小，若并列取起始列最小）的末字母'
        )
        rules.append({
            'type': 'compare_letters',
            'params': {'relation': relation},
            'text': text
        })

    if use_anchor_equal and a_pl and d_pl:
        left_across = min(a_pl, key=lambda rcw: (rcw[0][1], rcw[0][0]))
        top_down = min(d_pl, key=lambda rcw: (rcw[0][0], rcw[0][1]))
        a_word = left_across[1]
        d_word = top_down[1]
        a_pos = random.choice(['first', 'last'])
        d_pos = random.choice(['first', 'last'])
        a_ch = a_word[0] if a_pos == 'first' else a_word[-1]
        d_ch = d_word[0] if d_pos == 'first' else d_word[-1]
        relation = 'same' if a_ch == d_ch else 'different'
        text = (
            '最左侧Across单词（按起始列最小，若并列取起始行最小）的'
            f'{"首" if a_pos=="first" else "尾"}字母'
            f'与最上方Down单词（按起始行最小，若并列取起始列最小）的'
            f'{"首" if d_pos=="first" else "尾"}字母'
            f'{"相同" if relation=="same" else "不同"}'
        )
        rules.append({
            'type': 'anchor_compare',
            'params': {'a_pos': a_pos, 'd_pos': d_pos, 'relation': relation},
            'text': text
        })

    if use_global_letter_exact:
        filled = []
        for r in range(n):
            for c in range(n):
                ch = grid[r][c]
                if ch is not None and ch != ' ':
                    filled.append(ch.lower())
        if filled:
            counts: Dict[str, int] = {}
            for ch in filled:
                counts[ch] = counts.get(ch, 0) + 1
            items = [(ch, k) for ch, k in counts.items() if 1 <= k <= 5]
            if not items:
                items = list(counts.items())
            ch0, k0 = random.choice(items)
            rules.append({
                'type': 'global_letter_exact',
                'params': {'ch': ch0, 'count': k0},
                'text': f'整个网格中，字母“{ch0}”一共出现{k0}次'
            })

    return rules

def _merge_unique_rules(base: List[Dict], extra: List[Dict], need: int) -> List[Dict]:
    seen = {(r['type'], json.dumps(r['params'], sort_keys=True)) for r in base}
    out = list(base)
    for r in extra:
        key = (r['type'], json.dumps(r['params'], sort_keys=True))
        if key not in seen:
            out.append(r)
            seen.add(key)
            if len(out) >= len(base) + need:
                break
    return out

def _ensure_min_rules(grid, mask, L, across_words, down_words, rules, min_rules: int = 4) -> List[Dict]:
    if len(rules) >= min_rules:
        return rules
    add_rules = derive_rules_from_grid(
        grid, mask, L, across_words, down_words,
        n_rules_vc=2, n_rules_row=1, n_rules_col=1, n_rules_parity=1,
        use_distinct_rows_across=True, use_distinct_cols_down=True,
        use_compare_letters=True, use_anchor_equal=True, use_global_letter_exact=True
    )
    need = min_rules - len(rules)
    merged = _merge_unique_rules(rules, add_rules, need)
    return merged

def _diff_lock_candidates(g1: List[List[Optional[str]]],
                          g2: List[List[Optional[str]]],
                          mask: List[List[str]],
                          L: int) -> List[Tuple[int,int,str]]:
    n = len(mask)
    slots = coverable_cells(mask, L)
    diffs = []
    for r in range(n):
        for c in range(n):
            ch1 = g1[r][c]
            ch2 = g2[r][c]
            if ch1 != ch2:
                pick = None
                if ch1 is not None and ch1 != ' ':
                    pick = ch1
                elif ch2 is not None and ch2 != ' ':
                    pick = ch2
                if pick is not None and (r, c) in slots:
                    diffs.append((r, c, pick))
    return diffs

def generate_fill(across: List[str],
                  down: List[str],
                  grid_mask: List[List[str]],
                  locks_list: List[Tuple[int,int,str]],
                  rules: Optional[List[Dict]] = None) -> List[List[str]]:
    locks = {(r, c): ch for (r, c, ch) in locks_list}
    uniq, rep = try_place_count_unique_grids(
        across, down, grid_mask, locks, rules, max_unique=2, deterministic=True
    )
    if len(uniq) != 1:
        raise ValueError('No unique solution under the provided configuration.')
    grid = next(iter(rep.values()))
    return normalize_grid(grid)

def validate_solution(grid: List[List[str]],
                      mask: List[List[str]],
                      across: List[str],
                      down: List[str],
                      locks_list: List[Tuple[int,int,str]],
                      rules: Optional[List[Dict]],
                      L: int) -> bool:
    if not validate_grid_basic(grid, mask):
        return False
    locks = {(r, c): ch for (r, c, ch) in locks_list}
    uniq, rep = try_place_count_unique_grids(
        across, down, mask, locks, rules, max_unique=2, deterministic=True
    )
    if len(uniq) != 1:
        return False
    target = next(iter(rep.values()))
    return canonical_grid_string(grid) == canonical_grid_string(target)

def generate_instance(
    grid_size: int,
    word_len: int,
    n_across: int,
    n_down: int,
    across_rows_count: int,
    down_cols_count: int,
    locks_budget: int,
    attempt_limit: int,
    vc_rule_count: int,
    row_rule_count: int,
    col_rule_count: int,
    parity_rule_count: int,
    distinct_rows_flag: int = 0,
    distinct_cols_flag: int = 0,
    compare_rule_flag: int = 0,
    anchor_equal_flag: int = 0,
    global_letter_rule_flag: int = 0
) -> Dict:
    n = max(5, min(12, grid_size))
    L = word_len if word_len in (5, 6) else 5
    A = max(2, min(3, n_across))
    D = max(2, min(3, n_down))
    rr = max(1, min(4, across_rows_count))
    cc = max(1, min(4, down_cols_count))
    maxlocks = max(0, min(6, locks_budget))
    tries = max(50, min(2000, attempt_limit))

    vc_rule_count = max(2, min(4, vc_rule_count))
    row_rule_count = max(0, min(3, row_rule_count))
    col_rule_count = max(0, min(3, col_rule_count))
    parity_rule_count = max(1, min(3, parity_rule_count))

    use_distinct_rows = bool(distinct_rows_flag)
    use_distinct_cols = bool(distinct_cols_flag)
    use_compare = bool(compare_rule_flag)
    use_anchor = bool(anchor_equal_flag)
    use_global_exact = bool(global_letter_rule_flag)

    for _ in range(tries):
        rows = sorted(random.sample(list(range(n)), min(rr, n)))
        cols = sorted(random.sample(list(range(n)), min(cc, n)))
        mask = make_mask(n, rows, cols)
        if n < L:
            continue
        across_words = sample_words(L, A)
        down_words = sample_words(L, D)
        locks: List[Tuple[int,int,str]] = []

        base_rules: List[Dict] = []
        for _aug in range(maxlocks + 1):
            uniq, rep = try_place_count_unique_grids(
                across_words, down_words, mask,
                {(r, c): ch for (r, c, ch) in locks},
                base_rules,
                max_unique=2,
                deterministic=True
            )
            if len(uniq) == 1:
                grid = next(iter(rep.values()))
                rules = derive_rules_from_grid(
                    grid, mask, L, across_words, down_words,
                    n_rules_vc=vc_rule_count,
                    n_rules_row=row_rule_count,
                    n_rules_col=col_rule_count,
                    n_rules_parity=parity_rule_count,
                    use_distinct_rows_across=use_distinct_rows,
                    use_distinct_cols_down=use_distinct_cols,
                    use_compare_letters=use_compare,
                    use_anchor_equal=use_anchor,
                    use_global_letter_exact=use_global_exact
                )
                rules = _ensure_min_rules(grid, mask, L, across_words, down_words, rules, min_rules=4)
                uniq2, rep2 = try_place_count_unique_grids(
                    across_words, down_words, mask,
                    {(r, c): ch for (r, c, ch) in locks},
                    rules,
                    max_unique=2,
                    deterministic=True
                )
                if len(uniq2) == 1:
                    return {
                        'grid_size': n,
                        'word_len': L,
                        'across_words': across_words,
                        'down_words': down_words,
                        'grid_mask': mask,
                        'locks': locks,
                        'rules': rules
                    }
                if _aug < maxlocks and len(uniq2) == 2:
                    keys = list(uniq2)
                    g1 = rep2[keys[0]]
                    g2 = rep2[keys[1]]
                    diffs = _diff_lock_candidates(g1, g2, mask, L)
                    if diffs:
                        r, c, ch = random.choice(diffs)
                        lock_t = (r + 1, c + 1, ch)
                        if lock_t not in locks:
                            locks.append(lock_t)
                    continue

            if len(uniq) == 0:
                break
            if _aug < maxlocks and len(uniq) == 2:
                keys = list(uniq)
                g1 = rep[keys[0]]
                g2 = rep[keys[1]]
                diffs = _diff_lock_candidates(g1, g2, mask, L)
                if not diffs:
                    break
                r, c, ch = random.choice(diffs)
                lock_t = (r + 1, c + 1, ch)
                if lock_t not in locks:
                    locks.append(lock_t)

    n = max(n, 7)
    mask = make_mask(n, list(range(0, n, 2)), list(range(1, n, 3)))
    L = 5
    across_words = sample_words(L, max(2, n_across))
    down_words = sample_words(L, max(2, n_down))
    locks: List[Tuple[int,int,str]] = []
    rules: List[Dict] = []

    for _aug in range(10):
        uniq, rep = try_place_count_unique_grids(across_words, down_words, mask,
                                                 {(r, c): ch for (r, c, ch) in locks},
                                                 rules, max_unique=2, deterministic=True)
        if len(uniq) == 1:
            grid = next(iter(rep.values()))
            rules = derive_rules_from_grid(
                grid, mask, L, across_words, down_words,
                n_rules_vc=2,
                n_rules_row=1,
                n_rules_col=1,
                n_rules_parity=1,
                use_distinct_rows_across=True,
                use_distinct_cols_down=False,
                use_compare_letters=True,
                use_anchor_equal=False,
                use_global_letter_exact=False
            )
            rules = _ensure_min_rules(grid, mask, L, across_words, down_words, rules, min_rules=4)
            uniq2, rep2 = try_place_count_unique_grids(across_words, down_words, mask,
                                                       {(r, c): ch for (r, c, ch) in locks},
                                                       rules, max_unique=2, deterministic=True)
            if len(uniq2) == 1:
                return {
                    'grid_size': n,
                    'word_len': L,
                    'across_words': across_words,
                    'down_words': down_words,
                    'grid_mask': mask,
                    'locks': locks,
                    'rules': rules
                }
            keys = list(uniq2)
            if len(keys) >= 2:
                g1 = rep2[keys[0]]
                g2 = rep2[keys[1]]
                diffs = _diff_lock_candidates(g1, g2, mask, L)
            else:
                diffs = []
        else:
            keys = list(uniq)
            if len(keys) < 2:
                across_words = sample_words(L, max(2, n_across))
                down_words = sample_words(L, max(2, n_down))
                continue
            g1 = rep[keys[0]]
            g2 = rep[keys[1]]
            diffs = _diff_lock_candidates(g1, g2, mask, L)

        if diffs:
            r, c, ch = random.choice(diffs)
            lock_t = (r + 1, c + 1, ch)
            if lock_t not in locks:
                locks.append(lock_t)
        else:
            across_words = sample_words(L, max(2, n_across))
            down_words = sample_words(L, max(2, n_down))

    return {
        'grid_size': n,
        'word_len': L,
        'across_words': across_words,
        'down_words': down_words,
        'grid_mask': mask,
        'locks': locks,
        'rules': rules
    }