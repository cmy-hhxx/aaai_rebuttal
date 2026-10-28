# wordscapes_0.py

import json
import random
from typing import List, Tuple, Dict

def _grid_size(grid: List[List[str]]) -> Tuple[int, int]:
    return len(grid), len(grid[0]) if grid else 0

def _init_output(grid: List[List[str]]) -> List[List[str]]:
    # 将'0'预处理为' '（空格），'X'置为None等待填字
    out = []
    for row in grid:
        out.append([(' ' if c == '0' else None) for c in row])
    return out

def _find_across_slots(grid: List[List[str]]) -> List[Tuple[int, int, int]]:
    """
    找到所有横向连续的X片段，按行从上到下、每行从左到右的顺序返回
    结果格式：[(row, start_col, length), ...]
    """
    R, C = _grid_size(grid)
    slots = []
    for r in range(R):
        c = 0
        while c < C:
            if grid[r][c] == 'X':
                start = c
                while c < C and grid[r][c] == 'X':
                    c += 1
                length = c - start
                slots.append((r, start, length))
            else:
                c += 1
    return slots

def _find_down_slots(grid: List[List[str]]) -> List[Tuple[int, int, int]]:
    """
    找到所有纵向连续的X片段，按列从左到右、每列从上到下的顺序返回
    结果格式：[(start_row, col, length), ...]
    """
    R, C = _grid_size(grid)
    slots = []
    for c in range(C):
        r = 0
        while r < R:
            if grid[r][c] == 'X':
                start = r
                while r < R and grid[r][c] == 'X':
                    r += 1
                length = r - start
                slots.append((start, c, length))
            else:
                r += 1
    return slots

def _rand_word(length: int) -> str:
    # 随机生成由小写字母组成的指定长度单词
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(length))

def _place_across(filled: List[List[str]], r: int, start_c: int, word: str) -> None:
    # 严格长度匹配
    for i, ch in enumerate(word):
        if filled[r][start_c + i] is None or filled[r][start_c + i] == ch:
            filled[r][start_c + i] = ch
        else:
            raise ValueError("Across conflict at ({},{})".format(r, start_c + i))

def _collect_across_words_from_grid(grid: List[List[str]], filled: List[List[str]]) -> List[str]:
    """
    从成品网格中按横向顺序抽取所有横词，长度>=1（允许单字格）。
    """
    R, C = _grid_size(grid)
    res = []
    for r in range(R):
        c = 0
        while c < C:
            if grid[r][c] == 'X':
                word = []
                while c < C and grid[r][c] == 'X':
                    ch = filled[r][c]
                    if not ch or ch == ' ':
                        # 不应出现未填或空格
                        return []
                    word.append(ch)
                    c += 1
                res.append(''.join(word))
            else:
                c += 1
    return res

def _collect_down_words_from_grid(grid: List[List[str]], filled: List[List[str]]) -> List[str]:
    """
    从成品网格中按纵向顺序抽取所有纵词，长度>=1（允许单字格）。
    """
    R, C = _grid_size(grid)
    res = []
    for c in range(C):
        r = 0
        while r < R:
            if grid[r][c] == 'X':
                word = []
                while r < R and grid[r][c] == 'X':
                    ch = filled[r][c]
                    if not ch or ch == ' ':
                        return []
                    word.append(ch)
                    r += 1
                res.append(''.join(word))
            else:
                r += 1
    return res

def _format_answer(filled: List[List[str]]) -> str:
    """将二维数组转为题面要求的 JSON 字符串（字母带引号，空格为' '）。"""
    return json.dumps(filled, ensure_ascii=False, indent=2)

def _random_grid(rows_range=(3, 5), cols_range=(3, 5), max_tries=200) -> List[List[str]]:
    """
    随机生成一个包含'X'和'0'的网格，确保至少存在一个横词槽和一个纵词槽。
    """
    for _ in range(max_tries):
        R = random.randint(rows_range[0], rows_range[1])
        C = random.randint(cols_range[0], cols_range[1])
        grid = []
        for _r in range(R):
            row = []
            for _c in range(C):
                # 以0.55概率生成X，0.45概率生成0，使得X数量适中
                row.append('X' if random.random() < 0.55 else '0')
            grid.append(row)
        across_slots = _find_across_slots(grid)
        down_slots = _find_down_slots(grid)
        # 至少有一个横槽和一个纵槽，且每个槽长度>=1（自然满足）
        if len(across_slots) > 0 and len(down_slots) > 0:
            return grid
    # 若未找到，退回一个固定可用样例
    return [['0','X','X'],
            ['X','0','X'],
            ['X','X','0']]

def function_1() -> Dict[str, object]:
    """
    随机生成完整的填字谜题：
    - grid: 包含'X'和'0'
    - across: 横向单词列表（顺序与横槽遍历一致）
    - down  : 纵向单词列表（顺序与纵槽遍历一致）
    - filled: 填字完成后的二维字符数组（'0'位置为' '）
    """
    # 随机生成网格
    grid = _random_grid()

    # 找横槽
    across_slots = _find_across_slots(grid)
    # 为每个横槽随机生成匹配长度的单词
    across_words = [_rand_word(L) for (_, _, L) in across_slots]

    # 初始化输出网格并按横槽顺序填入横词
    filled = _init_output(grid)
    for (slot_idx, (r, sc, L)) in enumerate(across_slots):
        _place_across(filled, r, sc, across_words[slot_idx])

    # 收集纵词（由已填好的横词在纵向槽上截取得到）
    down_words = _collect_down_words_from_grid(grid, filled)

    # 最终将None替换为安全字符（理论上不存在，因为所有X都被横词填满）
    R, C = _grid_size(grid)
    for r in range(R):
        for c in range(C):
            if filled[r][c] is None:
                # 冗余保护：若出现未填位置，置为'a'
                filled[r][c] = 'a'

    return {
        'grid': grid,
        'across': across_words,
        'down': down_words,
        'filled': filled
    }

def function_2(grid: List[List[str]], across_words: List[str], down_words: List[str],
               filled: List[List[str]], strict: bool = False):
    """
    双用途函数：
    - strict=False：返回格式化字符串（最终答案输出）。
    - strict=True ：执行严格校验（返回True/False）。
      校验规则：
        1) 所有'0'位置均为' '；
        2) 按横向顺序读取到的单词列表应与 across_words 完全一致（一一对应）；
        3) 按纵向顺序读取到的单词列表应与 down_words 完全一致（一一对应）；
        4) 交叉处字母一致（由填字过程保证）。
      满足以上即视为唯一答案（横词顺序锁定所有X格的字母）。
    """
    if not strict:
        return _format_answer(filled)

    # 1) '0' 位置为 ' '
    R, C = _grid_size(grid)
    for r in range(R):
        for c in range(C):
            if grid[r][c] == '0' and filled[r][c] != ' ':
                return False

    # 2) 横向顺序校验
    across_found = _collect_across_words_from_grid(grid, filled)
    if across_found != across_words:
        return False

    # 3) 纵向顺序校验
    down_found = _collect_down_words_from_grid(grid, filled)
    if down_found != down_words:
        return False

    return True