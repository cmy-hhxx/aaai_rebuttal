# zebra_puzzle_8.py
import random
from typing import List, Any, Sequence, Tuple, Dict


def shuffle_list(lst: List[Any]) -> List[Any]:
    cp = list(lst)
    random.shuffle(cp)
    return cp


def choose_random(lst: Sequence[Any]) -> Any:
    if not lst:
        return None
    return random.choice(list(lst))


def choose_k_distinct(lst: Sequence[Any], k: int) -> List[Any]:
    items = list(lst)
    if k <= 0:
        return []
    if k >= len(items):
        return list(shuffle_list(items))
    return random.sample(items, k)


def choose_pair_distinct(lst: Sequence[Any]) -> List[Any]:
    return choose_k_distinct(lst, 2)


def choose_triple_distinct(lst: Sequence[Any]) -> List[Any]:
    return choose_k_distinct(lst, 3)


def choose_right_of_pair_avoid(lst: Sequence[Any], avoid_first: Any = None) -> List[Any]:
    items = list(lst)
    if len(items) < 2:
        return list(items)
    if avoid_first in items:
        candidates_first = [x for x in items if x != avoid_first] or items[:]
        x = random.choice(candidates_first)
    else:
        x = random.choice(items)
    remaining = [z for z in items if z != x] or items[:]
    y = random.choice(remaining)
    if x == y:
        others = [z for z in items if z != x]
        y = random.choice(others) if others else x
    return [x, y]


def _canon_pair(a: Any, b: Any) -> Tuple[Any, Any]:
    try:
        return tuple(sorted([a, b]))
    except Exception:
        return (a, b) if str(a) <= str(b) else (b, a)


def choose_pair_distinct_avoid(lst: Sequence[Any], avoid_pair: Sequence[Any]) -> List[Any]:
    items = list(lst)
    if len(items) < 2:
        return list(items)
    avoid = None
    if isinstance(avoid_pair, Sequence) and len(avoid_pair) >= 2:
        avoid = _canon_pair(avoid_pair[0], avoid_pair[1])
    for _ in range(100):
        a, b = random.sample(items, 2)
        if avoid is None or _canon_pair(a, b) != avoid:
            return [a, b]
    a, b = random.sample(items, 2)
    return [a, b]


def choose_color_drink_pair_avoid(colors: Sequence[Any], drinks: Sequence[Any], avoid_pair: Sequence[Any]) -> List[Any]:
    c_list = list(colors)
    d_list = list(drinks)
    if not c_list or not d_list:
        return [c_list[0] if c_list else None, d_list[0] if d_list else None]
    avoid_color = avoid_pair[0] if isinstance(avoid_pair, Sequence) and len(avoid_pair) > 0 else None
    avoid_drink = avoid_pair[1] if isinstance(avoid_pair, Sequence) and len(avoid_pair) > 1 else None
    for _ in range(100):
        c = random.choice(c_list)
        d = random.choice(d_list)
        if not (c == avoid_color and d == avoid_drink):
            return [c, d]
    c = random.choice(c_list)
    d = random.choice([x for x in d_list if x != avoid_drink] or d_list)
    return [c, d]


def choose_country_instrument_pair_avoid(countries: Sequence[Any], instruments: Sequence[Any], avoid_country: Any) -> List[Any]:
    c_list = list(countries)
    i_list = list(instruments)
    if not c_list or not i_list:
        return [c_list[0] if c_list else None, i_list[0] if i_list else None]
    candidates = [c for c in c_list if c != avoid_country] or c_list
    country = random.choice(candidates)
    instrument = random.choice(i_list)
    return [country, instrument]


def _as_int(v):
    try:
        return v.as_long()
    except Exception:
        return int(v)


def _pos_by_idx(_sol, positions: List[int], stage, attr: str) -> Dict[int, int]:
    """Map attribute index (0..4) -> position (1..5)."""
    res = {}
    for p in positions:
        val = _sol.eval(stage[p].get(attr), model_completion=True)
        res[_as_int(val)] = p
    return res


def _idx_by_pos(_sol, positions: List[int], stage, attr: str) -> List[int]:
    """List where idx_by_pos[p-1] = index of attr at position p."""
    lst = []
    for p in positions:
        val = _sol.eval(stage[p].get(attr), model_completion=True)
        lst.append(_as_int(val))
    return lst


def leftmost_color_from_solution(_sol, colors: List[str], positions: List[int], stage) -> str:
    val = _sol.eval(stage[positions[0]].get('color'), model_completion=True)
    idx = _as_int(val)
    return colors[idx]


def immediate_right_colors_from_solution(_sol, colors: List[str], positions: List[int], stage) -> List[str]:
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    n = len(positions)
    pairs = [[colors[color_idx_by_pos[i + 1]], colors[color_idx_by_pos[i]]] for i in range(n - 1)]
    return random.choice(pairs) if pairs else [colors[color_idx_by_pos[0]], colors[color_idx_by_pos[0]]]


def not_adjacent_colors_from_solution(_sol, colors: List[str], positions: List[int], stage) -> List[str]:
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    n = len(positions)
    choices = []
    for i in range(n):
        for j in range(i + 1, n):
            if abs((i + 1) - (j + 1)) != 1:
                choices.append([colors[color_idx_by_pos[i]], colors[color_idx_by_pos[j]]])
    if choices:
        return random.choice(choices)
    return random.sample(colors, 2)


def eq_color_drink_from_solution(_sol, colors: List[str], drinks: List[str], positions: List[int], stage) -> List[str]:
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    p = random.choice(positions)
    return [colors[color_idx_by_pos[p - 1]], drinks[drink_idx_by_pos[p - 1]]]


def eq_color_country_from_solution(_sol, colors: List[str], countries: List[str], positions: List[int], stage) -> List[str]:
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    p = random.choice(positions)
    return [colors[color_idx_by_pos[p - 1]], countries[country_idx_by_pos[p - 1]]]


def eq_country_drink_from_solution(_sol, countries: List[str], drinks: List[str], positions: List[int], stage) -> List[str]:
    """某国家主秀的吧台饮品等于某饮品。"""
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    p = random.choice(positions)
    return [countries[country_idx_by_pos[p - 1]], drinks[drink_idx_by_pos[p - 1]]]


def mid_drink_from_solution(_sol, drinks: List[str], positions: List[int], stage) -> str:
    n = len(positions)
    mid_pos = n // 2 + 1
    val = _sol.eval(stage[mid_pos].get('drink'), model_completion=True)
    return drinks[_as_int(val)]


def edge_genre_from_solution(_sol, genres: List[str], positions: List[int], stage) -> str:
    """强化方向性：只取最左端的风格，打破镜像对称。"""
    left_val = _sol.eval(stage[positions[0]].get('genre'), model_completion=True)
    return genres[_as_int(left_val)]


def between_country_colors_from_solution(_sol, countries: List[str], colors: List[str], positions: List[int], stage) -> List[str]:
    country_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'country')
    color_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'color')
    idxs = list(country_pos_by_idx.keys())
    random.shuffle(idxs)
    for ci in idxs:
        cp = country_pos_by_idx[ci]
        left_candidates = [c for c, p in color_pos_by_idx.items() if p < cp]
        right_candidates = [c for c, p in color_pos_by_idx.items() if p > cp]
        if left_candidates and right_candidates:
            lc = random.choice(left_candidates)
            rc = random.choice(right_candidates)
            return [countries[ci], colors[lc], colors[rc]]
    ci = idxs[0]
    all_colors = list(color_pos_by_idx.items())
    left_color_idx = min(all_colors, key=lambda x: x[1])[0]
    right_color_idx = max(all_colors, key=lambda x: x[1])[0]
    return [countries[ci], colors[left_color_idx], colors[right_color_idx]]


def adjacent_genre_drink_from_solution(_sol, genres: List[str], drinks: List[str], positions: List[int], stage) -> List[str]:
    genre_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'genre')
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    n = len(positions)
    pairs = []
    for i in range(n - 1):
        pairs.append([genres[genre_idx_by_pos[i]], drinks[drink_idx_by_pos[i + 1]]])
        pairs.append([genres[genre_idx_by_pos[i + 1]], drinks[drink_idx_by_pos[i]]])
    return random.choice(pairs) if pairs else [genres[genre_idx_by_pos[0]], drinks[drink_idx_by_pos[0]]]


def adjacent_country_instrument_from_solution(_sol, countries: List[str], instruments: List[str], positions: List[int], stage) -> List[str]:
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    inst_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'instrument')
    n = len(positions)
    pairs = []
    for i in range(n - 1):
        pairs.append([countries[country_idx_by_pos[i]], instruments[inst_idx_by_pos[i + 1]]])
        pairs.append([countries[country_idx_by_pos[i + 1]], instruments[inst_idx_by_pos[i]]])
    return random.choice(pairs) if pairs else [countries[country_idx_by_pos[0]], instruments[inst_idx_by_pos[0]]]


def far_left_color_genre_from_solution(_sol, colors: List[str], genres: List[str], positions: List[int], stage) -> List[str]:
    color_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'color')
    genre_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'genre')
    choices = []
    for ci, cp in color_pos_by_idx.items():
        for gi, gp in genre_pos_by_idx.items():
            if cp + 2 <= gp:
                choices.append([colors[ci], genres[gi]])
    if choices:
        return random.choice(choices)
    return [colors[0], genres[0]]


def adjacent_genre_country_from_solution(_sol, genres: List[str], countries: List[str], positions: List[int], stage) -> List[str]:
    genre_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'genre')
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    n = len(positions)
    pairs = []
    for i in range(n - 1):
        pairs.append([genres[genre_idx_by_pos[i]], countries[country_idx_by_pos[i + 1]]])
        pairs.append([genres[genre_idx_by_pos[i + 1]], countries[country_idx_by_pos[i]]])
    return random.choice(pairs) if pairs else [genres[genre_idx_by_pos[0]], countries[country_idx_by_pos[0]]]


def color_forbid_and_two_instruments_from_solution(_sol, colors: List[str], instruments: List[str], positions: List[int], stage) -> List[Any]:
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    inst_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'instrument')
    p = random.choice(positions)
    color_name = colors[color_idx_by_pos[p - 1]]
    inst_at_color = instruments[inst_idx_by_pos[p - 1]]
    others = [x for x in instruments if x != inst_at_color]
    if len(others) >= 2:
        forb = random.sample(others, 2)
    else:
        forb = others + [inst_at_color] if others else random.sample(instruments, 2)
    return [color_name, forb]


def parity_country_drink_from_solution(_sol, countries: List[str], drinks: List[str], positions: List[int], stage) -> List[str]:
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    odds = [i + 1 for i in range(len(positions)) if (i + 1) % 2 == 1]
    evens = [i + 1 for i in range(len(positions)) if (i + 1) % 2 == 0]
    cpos = random.choice(odds)
    dpos = random.choice(evens)
    return [countries[country_idx_by_pos[cpos - 1]], drinks[drink_idx_by_pos[dpos - 1]]]


def edge_drink_instrument_from_solution(_sol, drinks: List[str], instruments: List[str], positions: List[int], stage) -> List[str]:
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    inst_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'instrument')
    # 强化方向性：取“最右端的饮品”和“最左端的乐器”（用于固定两端位置）
    d_right = drinks[drink_idx_by_pos[-1]]
    i_left = instruments[inst_idx_by_pos[0]]
    return [d_right, i_left]


def immediate_left_drink_genre_from_solution(_sol, drinks: List[str], genres: List[str], positions: List[int], stage) -> List[str]:
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    genre_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'genre')
    n = len(positions)
    pairs = [[drinks[drink_idx_by_pos[j - 2]], genres[genre_idx_by_pos[j - 1]]] for j in range(2, n + 1)]
    return random.choice(pairs) if pairs else [drinks[drink_idx_by_pos[0]], genres[genre_idx_by_pos[0]]]


def eq_country_instrument_1_from_solution(_sol, countries: List[str], instruments: List[str], positions: List[int], stage) -> List[str]:
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    inst_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'instrument')
    p = random.choice(positions)
    return [countries[country_idx_by_pos[p - 1]], instruments[inst_idx_by_pos[p - 1]]]


def eq_country_instrument_2_from_solution(_sol, countries: List[str], instruments: List[str], positions: List[int], stage, eq_country_instrument_1: List[str]) -> List[str]:
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    inst_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'instrument')
    different_positions = [p for p in positions if countries[country_idx_by_pos[p - 1]] != eq_country_instrument_1[0]]
    p = random.choice(different_positions) if different_positions else random.choice(positions)
    return [countries[country_idx_by_pos[p - 1]], instruments[inst_idx_by_pos[p - 1]]]


def gap_drink_instrument_from_solution(_sol, drinks: List[str], instruments: List[str], positions: List[int], stage) -> List[str]:
    drink_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'drink')
    inst_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'instrument')
    pairs = []
    for di, dp in drink_pos_by_idx.items():
        for ii, ip in inst_pos_by_idx.items():
            if abs(dp - ip) == 2:
                pairs.append([drinks[di], instruments[ii]])
    return random.choice(pairs) if pairs else [drinks[0], instruments[0]]


def not_edge_country_from_solution(_sol, countries: List[str], positions: List[int], stage) -> str:
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    n = len(positions)
    middle_positions = [p for p in positions if p not in (1, n)]
    p = random.choice(middle_positions) if middle_positions else random.choice(positions)
    return countries[country_idx_by_pos[p - 1]]


def not_color_drink_from_solution(_sol, colors: List[str], drinks: List[str], positions: List[int], stage) -> List[str]:
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    drink_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'drink')
    pairs = []
    n = len(positions)
    for i in range(n):
        for j in range(n):
            if i != j:
                pairs.append([colors[color_idx_by_pos[i]], drinks[drink_idx_by_pos[j]]])
    return random.choice(pairs) if pairs else [colors[color_idx_by_pos[0]], drinks[drink_idx_by_pos[0]]]


def immediate_left_countries_from_solution(_sol, countries: List[str], positions: List[int], stage) -> List[str]:
    country_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'country')
    n = len(positions)
    pairs = [[countries[country_idx_by_pos[i]], countries[country_idx_by_pos[i + 1]]] for i in range(n - 1)]
    return random.choice(pairs) if pairs else [countries[country_idx_by_pos[0]], countries[country_idx_by_pos[0]]]


def genre_target_instrument_right_color_from_solution(_sol, genres: List[str], instruments: List[str], colors: List[str], positions: List[int], stage) -> List[Any]:
    genre_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'genre')
    inst_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'instrument')
    color_idx_by_pos = _idx_by_pos(_sol, positions, stage, 'color')
    n = len(positions)
    valid_ps = [p for p in positions if p > 1]
    if not valid_ps:
        p = 2
    else:
        p = random.choice(valid_ps)
    gname = genres[genre_idx_by_pos[p - 1]]
    iname = instruments[inst_idx_by_pos[p - 1]]
    left_positions = [q for q in positions if q < p]
    q = random.choice(left_positions) if left_positions else p - 1
    ry = colors[color_idx_by_pos[q - 1]]
    rx = colors[color_idx_by_pos[p - 1]]
    return [gname, iname, [rx, ry]]


def get_color_by_drink(solutions, colors, positions, stage, drink_index):
    try:
        import z3  # noqa: F401
    except Exception:
        return colors[0] if colors else ''
    if not solutions:
        return colors[0] if colors else ''
    m = solutions[0]
    for p in positions:
        drink_val = m.eval(stage[p].get('drink'), model_completion=True)
        drink_val = _as_int(drink_val)
        if drink_val == drink_index:
            col_val = m.eval(stage[p].get('color'), model_completion=True)
            col_val = _as_int(col_val)
            if isinstance(col_val, int) and 0 <= col_val < len(colors):
                return colors[col_val]
            return colors[0] if colors else ''
    return colors[0] if colors else ''


def get_color_by_genre(solutions, colors, positions, stage, genre_index):
    try:
        import z3  # noqa: F401
    except Exception:
        return colors[0] if colors else ''
    if not solutions:
        return colors[0] if colors else ''
    m = solutions[0]
    for p in positions:
        genre_val = m.eval(stage[p].get('genre'), model_completion=True)
        genre_val = _as_int(genre_val)
        if genre_val == genre_index:
            col_val = m.eval(stage[p].get('color'), model_completion=True)
            col_val = _as_int(col_val)
            if isinstance(col_val, int) and 0 <= col_val < len(colors):
                return colors[col_val]
            return colors[0] if colors else ''
    return colors[0] if colors else ''


def generate_include_flags_for_solution(
    _sol,
    positions: List[int],
    stage,
    min_true: int,
    max_true: int
) -> List[bool]:
    """
    强化线索启用策略：
    - 优先启用所有锚定线索；
    - 对结构性可选线索（左侧至少两位与恰隔一个舞台），在存在时也启用；
    - 启用数目标为尽可能大（通常为23或24），稳固唯一解。
    """
    total = 24
    flags = [False] * total

    # 可用性检查：线索7与16可能不存在
    color_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'color')
    genre_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'genre')
    exists_far_left = any(cp + 2 <= gp for cp in color_pos_by_idx.values() for gp in genre_pos_by_idx.values())

    drink_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'drink')
    inst_pos_by_idx = _pos_by_idx(_sol, positions, stage, 'instrument')
    exists_gap = any(abs(dp - ip) == 2 for dp in drink_pos_by_idx.values() for ip in inst_pos_by_idx.values())

    # 锚定线索（0基索引）
    anchors = {
        0,   # 1 目标风格使用某乐器且在某颜色右侧，并绑定其舞台颜色
        1,   # 2 风格与饮品相邻
        2,   # 3 最左端风格（强化方向性）
        3,   # 4 中间饮品
        4,   # 5 国家在两颜色之间
        5,   # 6 国家与乐器相邻
        7,   # 8 风格与国家相邻
        8,   # 9 指定颜色的乐器不为两者
        9,   # 10 国家与饮品奇偶不同
        10,  # 11 两颜色不相邻
        11,  # 12 强化：右端饮品与左端乐器分别在最右与最左端
        12,  # 13 颜色右侧紧邻
        13,  # 14 饮品左侧紧邻风格
        14,  # 15 某国家的乐器等于某乐器
        16,  # 17 指定颜色的饮品等于某饮品
        17,  # 18 指定颜色的国家等于某国家
        18,  # 19 另一国家的乐器等于某乐器
        19,  # 20 两国家左侧紧邻
        20,  # 21 指定国家不在边上
        21,  # 22 某颜色不卖某饮品
        22,  # 23 左端颜色
        23   # 24 某国家主秀的吧台饮品等于某饮品
    }
    for idx in anchors:
        flags[idx] = True

    # 结构性可选（0基）
    optional = set()
    if exists_far_left:
        optional.add(6)   # 7 颜色在风格左侧至少两位
    if exists_gap:
        optional.add(15)  # 16 饮品与乐器恰隔一个舞台

    # 启用可选（如存在）
    for i in optional:
        flags[i] = True

    return flags


def build_clue_texts(
    include_flags: List[bool],
    genres: List[str],
    instruments: List[str],
    drinks: List[str],
    countries: List[str],
    colors: List[str],
    genre_target: str,
    instrument_for_genre_target: str,
    right_of_pair_colors: List[str],
    adjacent_genre_drink: List[str],
    edge_genre: str,
    mid_drink: str,
    between_country_colors: List[str],
    adjacent_country_instrument: List[str],
    adjacent_genre_country: List[str],
    color_forbid: str,
    forbid_instruments: List[str],
    parity_country_drink: List[str],
    not_adjacent_colors: List[str],
    edge_drink_instrument: List[str],
    immediate_right_colors: List[str],
    immediate_left_drink_genre: List[str],
    eq_country_instrument_1: List[str],
    eq_color_drink: List[str],
    eq_color_country: List[str],
    eq_country_instrument_2: List[str],
    not_edge_country: str,
    not_color_drink: List[str],
    leftmost_color: str,
    far_left_color_genre: List[str],
    gap_drink_instrument: List[str],
    immediate_left_countries: List[str],
    eq_country_drink: List[str]
) -> str:
    mapping = list(range(1, 25))  # 1..24
    lines = []
    idx = 0
    for pos, flag in enumerate(include_flags):
        if not flag:
            continue
        clue_no = mapping[pos]
        if clue_no == 1:
            # 强化文案：加入颜色绑定
            text = f"{genre_target} 舞台使用 {instrument_for_genre_target} 并且位于颜色为 {right_of_pair_colors[1]} 的舞台右侧某处 且该舞台颜色为 {right_of_pair_colors[0]}"
        elif clue_no == 2:
            text = f"{adjacent_genre_drink[0]} 舞台与卖 {adjacent_genre_drink[1]} 的舞台相邻"
        elif clue_no == 3:
            text = f"{edge_genre} 舞台位于最左端"
        elif clue_no == 4:
            text = f"卖 {mid_drink} 的舞台位于中间位置"
        elif clue_no == 5:
            text = f"{between_country_colors[0]} 主秀位于颜色为 {between_country_colors[1]} 与 {between_country_colors[2]} 的两舞台之间某处"
        elif clue_no == 6:
            text = f"{adjacent_country_instrument[0]} 主秀与 {adjacent_country_instrument[1]} 舞台相邻"
        elif clue_no == 7:
            text = f"颜色为 {far_left_color_genre[0]} 的舞台在 {far_left_color_genre[1]} 舞台左侧至少两位"
        elif clue_no == 8:
            text = f"{adjacent_genre_country[0]} 舞台与 {adjacent_genre_country[1]} 主秀相邻"
        elif clue_no == 9:
            text = f"颜色为 {color_forbid} 的舞台重点乐器既不是 {forbid_instruments[0]} 也不是 {forbid_instruments[1]}"
        elif clue_no == 10:
            text = f"{parity_country_drink[0]} 主秀与卖 {parity_country_drink[1]} 的舞台具有不同奇偶位"
        elif clue_no == 11:
            text = f"颜色为 {not_adjacent_colors[0]} 与 {not_adjacent_colors[1]} 的舞台不相邻"
        elif clue_no == 12:
            # 强化文案：明确两端位置
            text = f"卖 {edge_drink_instrument[0]} 的舞台位于最右端 用 {edge_drink_instrument[1]} 的舞台位于最左端"
        elif clue_no == 13:
            text = f"颜色为 {immediate_right_colors[0]} 的舞台在颜色为 {immediate_right_colors[1]} 的舞台右侧紧邻"
        elif clue_no == 14:
            text = f"卖 {immediate_left_drink_genre[0]} 的舞台在 {immediate_left_drink_genre[1]} 舞台左侧紧邻"
        elif clue_no == 15:
            text = f"{eq_country_instrument_1[0]} 主秀的重点乐器是 {eq_country_instrument_1[1]}"
        elif clue_no == 16:
            text = f"卖 {gap_drink_instrument[0]} 的舞台与用 {gap_drink_instrument[1]} 的舞台之间恰隔一个舞台"
        elif clue_no == 17:
            text = f"颜色为 {eq_color_drink[0]} 的舞台的吧台饮品是 {eq_color_drink[1]}"
        elif clue_no == 18:
            text = f"颜色为 {eq_color_country[0]} 的舞台的主秀国家是 {eq_color_country[1]}"
        elif clue_no == 19:
            text = f"{eq_country_instrument_2[0]} 主秀的重点乐器是 {eq_country_instrument_2[1]}"
        elif clue_no == 20:
            text = f"{immediate_left_countries[0]} 主秀所在舞台在 {immediate_left_countries[1]} 主秀所在舞台左侧紧邻"
        elif clue_no == 21:
            text = f"{not_edge_country} 主秀不在最左端或最右端"
        elif clue_no == 22:
            text = f"颜色为 {not_color_drink[0]} 的舞台不出售 {not_color_drink[1]}"
        elif clue_no == 23:
            text = f"颜色为 {leftmost_color} 的舞台位于最左端"
        elif clue_no == 24:
            text = f"{eq_country_drink[0]} 主秀的吧台饮品是 {eq_country_drink[1]}"
        else:
            text = ""
        if text:
            idx += 1
            lines.append(f"{idx} {text}")
    return "\n".join(lines)