# arrow_maze_3.py
# ================================================================
# Mirror Maze Generator with Unique-Solution & Clue Selector
# ================================================================
import random
import time
import itertools
from typing import List, Tuple, Dict, Set

# ------------------- clue helper -------------------------------
def select_clues(q_type: int, raw_types: List[int]) -> List[int]:
    """
    过滤与题型冲突的线索并控制线索数量
    type 0: diag_cnt, 1: vert_cnt, 2: parity, 3: min/max
    """
    forbid = {2: [0], 1: [3]}.get(q_type, [])
    filtered = [t for t in raw_types if t not in forbid]
    max_keep = 2 if q_type == 0 else len(filtered)
    return filtered[:max_keep]

# ---------------- Direction & Reflection -----------------------
DIRS = {
    'U': (-1, 0),  'D': (1, 0),
    'L': (0, -1),  'R': (0, 1),
    'UL': (-1, -1),'UR': (-1, 1),
    'DL': (1, -1), 'DR': (1, 1)
}
REFLECT = {
    '/':  {'U':'R','R':'U','D':'L','L':'D','UL':'DR','DR':'UL','UR':'DL','DL':'UR'},
    '\\': {'U':'L','L':'U','D':'R','R':'D','UL':'UR','UR':'UL','DL':'DR','DR':'DL'}
}
DIR_LIST = list(DIRS.keys())
DIAG_DIRS, VERT_DIRS = {'UL','UR','DL','DR'}, {'U','D'}

# ---------------- Basic helpers --------------------------------
def rand_bool() -> bool:
    return random.random() < 0.5

def step(r: int, c: int, d: str) -> Tuple[int, int]:
    dr, dc = DIRS[d]
    return r + dr, c + dc

def in_board(r: int, c: int, n: int) -> bool:
    return 0 <= r < n and 0 <= c < n

def ray_length(board: List[List[str]], r: int, c: int, d: str,
               max_len: int, num_cells: Set[Tuple[int, int]]) -> int:
    seen = set()
    length = 0
    direction = d
    n = len(board)
    for _ in range(max_len + 1):
        sig = (r, c, direction)
        if sig in seen:
            return -1
        seen.add(sig)
        length += 1
        nr, nc = step(r, c, direction)
        if not in_board(nr, nc, n):
            return length
        if (nr, nc) in num_cells:
            return length
        cell = board[nr][nc]
        if cell in REFLECT:
            direction = REFLECT[cell][direction]
        r, c = nr, nc
    return -1

# ---------------- Uniqueness check -----------------------------
def count_solutions(board, num_pos, numbers, extra, max_len, limit=2):
    num_set = set(num_pos)
    tgt_diag = extra.get('diag_cnt')
    tgt_vert = extra.get('vert_cnt')
    tgt_par  = extra.get('parity')
    tgt_min  = extra.get('min_len')
    tgt_max  = extra.get('max_len')
    cnt = 0
    for dirs in itertools.product(DIR_LIST, repeat=len(num_pos)):
        diag = vert = 0
        lens = []
        for (r, c), need, d in zip(num_pos, numbers, dirs):
            l = ray_length(board, r, c, d, max_len, num_set - {(r, c)})
            if l != need:
                break
            lens.append(l)
            if d in DIAG_DIRS:
                diag += 1
            if d in VERT_DIRS:
                vert += 1
        else:
            if tgt_diag is not None and diag != tgt_diag:
                continue
            if tgt_vert is not None and vert != tgt_vert:
                continue
            if tgt_par is not None and sum(numbers) % 2 != tgt_par:
                continue
            if tgt_min is not None and min(lens) != tgt_min:
                continue
            if tgt_max is not None and max(lens) != tgt_max:
                continue
            cnt += 1
            if cnt >= limit:
                return cnt
    return cnt

# ---------------- Main generator -------------------------------
def generate_maze(n: int, num_cnt: int, mirror_density: float, max_len: int,
                  mirror_mode: str, unique_numbers: bool,
                  q_type: int, clue_types: List[int]) -> Dict:

    mirror_choices = {
        'slash': ['/'],
        'backslash': ['\\'],
        'both': ['/', '\\']
    }[mirror_mode]

    deadline = time.time() + 170
    while time.time() < deadline:
        board = [['X'] * n for _ in range(n)]

        # place mirrors
        for r in range(n):
            for c in range(n):
                if random.random() < mirror_density:
                    board[r][c] = random.choice(mirror_choices)

        blanks = [(r, c) for r in range(n) for c in range(n) if board[r][c] == 'X']
        if len(blanks) < num_cnt:
            continue
        random.shuffle(blanks)
        num_pos = sorted(blanks[:num_cnt])   # keep deterministic order
        num_set = set(num_pos)

        answers, numbers = [], []
        for r, c in num_pos:
            legal = []
            dirs = DIR_LIST[:]
            random.shuffle(dirs)
            for d in dirs:
                l = ray_length(board, r, c, d, max_len, num_set - {(r, c)})
                if 1 <= l <= max_len:
                    legal.append((d, l))
            if not legal:
                break
            d_sel, l_sel = random.choice(legal)
            answers.append(d_sel)
            numbers.append(l_sel)
            board[r][c] = str(l_sel)
        else:
            if unique_numbers and len(set(numbers)) != len(numbers):
                continue

            diag_cnt = sum(1 for d in answers if d in DIAG_DIRS)
            vert_cnt = sum(1 for d in answers if d in VERT_DIRS)
            parity = sum(numbers) % 2
            min_len, max_len_hint = min(numbers), max(numbers)

            extra_req, clues = {}, []
            for t in clue_types:
                if q_type == 2 and t == 0:
                    continue
                if q_type == 1 and t == 3:
                    continue
                if t == 0:
                    extra_req['diag_cnt'] = diag_cnt
                    clues.append(f'对角箭头数为{diag_cnt}')
                elif t == 1:
                    extra_req['vert_cnt'] = vert_cnt
                    clues.append(f'竖直箭头数为{vert_cnt}')
                elif t == 2:
                    extra_req['parity'] = parity
                    clues.append(f'所有数字之和为{"奇" if parity else "偶"}数')
                elif t == 3:
                    extra_req['min_len'] = min_len
                    extra_req['max_len'] = max_len_hint
                    clues.append(f'最短射线{min_len}格, 最长{max_len_hint}格')

            if count_solutions(board, num_pos, numbers, extra_req, max_len) == 1:
                return {
                    'grid': board,
                    'num_positions': num_pos,
                    'numbers': numbers,
                    'answers': answers,
                    'min_idx': numbers.index(min_len),
                    'diag_cnt': diag_cnt,
                    'clues': clues
                }
    raise RuntimeError("Generation timed out; unique puzzle not found")