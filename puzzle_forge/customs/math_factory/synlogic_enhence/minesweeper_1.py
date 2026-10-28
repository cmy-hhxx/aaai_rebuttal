# minesweeper_3.py
# 辅助算子：骑士邻域生成 + 唯一采样 + 不重复配对采样
from typing import Dict, List, Tuple, Any
import random

def function_1(rows: int, cols: int, obstacles: List[Tuple[int, int]]) -> Dict[Tuple[int, int], List[Tuple[int, int]]]:
    """
    计算每个坐标的骑士步邻居(排除越界与障碍)。
    - 国际象棋马的走法为(+/-1, +/-2)与(+/-2, +/-1)组合共8个偏移。
    - 邻域定义为在网格内的马步坐标，且障碍O不计入邻域。
    返回: dict[(r, c)] -> List[(nr, nc)]
    """
    obstacle_set = set(obstacles)
    k_offsets = [(1, 2), (2, 1), (1, -2), (2, -1), (-1, 2), (-2, 1), (-1, -2), (-2, -1)]
    neigh: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    for r in range(rows):
        for c in range(cols):
            cand: List[Tuple[int, int]] = []
            for dr, dc in k_offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in obstacle_set:
                    cand.append((nr, nc))
            neigh[(r, c)] = cand
    return neigh

def function_pick_unique(seq: List[Any], k: int) -> List[Any]:
    """
    从序列中唯一采样k个不同元素：
    - k <= 0: 返回空列表；
    - k >= len(seq): 返回打乱后的全部元素；
    - 其他: 使用random.sample进行无放回采样。
    """
    if k <= 0:
        return []
    n = len(seq)
    if n == 0:
        return []
    if k >= n:
        out = list(seq)
        random.shuffle(out)
        return out
    return random.sample(seq, k)

def function_pick_pairs(seq: List[Tuple[int, int]], pair_k: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    从候选坐标集合中选取pair_k对不重复配对（同一坐标不参与多对），返回[(a,b), ...]。
    策略：
    - 随机打乱候选序列；
    - 依次取相邻成对；若剩余不足2则停止；
    - pair_k超界时按最大可配对数截断。
    """
    if pair_k <= 0 or not seq:
        return []
    pool = list(seq)
    random.shuffle(pool)
    max_pairs = len(pool) // 2
    take = min(pair_k, max_pairs)
    pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    idx = 0
    for _ in range(take):
        a = pool[idx]
        b = pool[idx + 1]
        pairs.append((a, b))
        idx += 2
    return pairs