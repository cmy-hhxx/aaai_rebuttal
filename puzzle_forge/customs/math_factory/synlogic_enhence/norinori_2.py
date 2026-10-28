# norinori_0.py
from typing import List, Tuple, Dict, Any
import random
import string

Cell = Tuple[int, int]
Edge = Tuple[Cell, Cell]

def make_cells(rows: int, cols: int) -> List[Cell]:
    return [(r, c) for r in range(1, rows + 1) for c in range(1, cols + 1)]

def gen_edges(rows: int, cols: int) -> List[Edge]:
    edges: List[Edge] = []
    # horizontal
    for r in range(1, rows + 1):
        for c in range(1, cols):
            edges.append(((r, c), (r, c + 1)))
    # vertical
    for r in range(1, rows):
        for c in range(1, cols + 1):
            edges.append(((r, c), (r + 1, c)))
    return edges

def flatten_2d(grid: List[List[Any]]) -> List[Any]:
    return [x for row in grid for x in row]

def uniq_regions(labels: List[str]) -> List[str]:
    s = sorted(set(labels))
    return [x for x in s if x not in ('X', 'O')]

def group_region_indices(labels: List[str], regions: List[str]) -> Dict[str, List[int]]:
    d: Dict[str, List[int]] = {r: [] for r in regions}
    for i, lab in enumerate(labels):
        if lab in d:
            d[lab].append(i)
    return d

def indices_by_label(labels: List[str], label: str) -> List[int]:
    return [i for i, lab in enumerate(labels) if lab == label]

def cell_to_index_map(cells: List[Cell]) -> Dict[Cell, int]:
    return {cell: i for i, cell in enumerate(cells)}

def build_cell_edge_indices(cells: List[Cell],
                            edges: List[Edge]
                           ) -> List[List[int]]:
    ct2i = cell_to_index_map(cells)
    res: List[List[int]] = [[] for _ in range(len(cells))]
    for ei, e in enumerate(edges):
        u, v = e
        res[ct2i[u]].append(ei)
        res[ct2i[v]].append(ei)
    return res

def list_len(l: List[Any]) -> int:
    return len(l)

def edges_to_str(edges: List[Edge]) -> List[str]:
    out: List[str] = []
    for (u, v) in edges:
        u_str = f'{u[0]}_{u[1]}'
        v_str = f'{v[0]}_{v[1]}'
        out.append(f'{u_str}-{v_str}')
    return out

def letter_sequence(n: int) -> List[str]:
    letters = []
    base = list(string.ascii_uppercase)
    if n <= 26:
        return base[:n]
    count = n
    letters.extend(base)
    count -= 26
    while count > 0:
        for a in base:
            for b in base:
                letters.append(a + b)
                count -= 1
                if count == 0:
                    break
            if count == 0:
                break
    return letters[:n]

def neighbors(cell: Cell, rows: int, cols: int) -> List[Cell]:
    r, c = cell
    res = []
    if r > 1: res.append((r - 1, c))
    if r < rows: res.append((r + 1, c))
    if c > 1: res.append((r, c - 1))
    if c < cols: res.append((r, c + 1))
    return res

def choose_region_sizes(total_cells: int, region_count: int,
                        size_min: int, size_max: int) -> List[int]:
    size_min = max(1, size_min)
    size_max = max(size_min, size_max)
    sizes = [size_min for _ in range(region_count)]
    remaining = total_cells - size_min * region_count
    if remaining < 0:
        sizes = [1 for _ in range(region_count)]
        remaining = total_cells - region_count
    while remaining > 0:
        i = random.randrange(region_count)
        if sizes[i] < size_max:
            sizes[i] += 1
            remaining -= 1
        else:
            candidates = [j for j in range(region_count) if sizes[j] < size_max]
            if not candidates:
                i = random.randrange(region_count)
                sizes[i] += 1
                remaining -= 1
            else:
                j = random.choice(candidates)
                sizes[j] += 1
                remaining -= 1
    return sizes

def generate_labels_with_marks(rows: int, cols: int,
                               region_min: int, region_max: int,
                               reg_size_min: int, reg_size_max: int,
                               x_target: int, o_target: int) -> List[List[str]]:
    total = rows * cols
    region_min = max(1, region_min)
    region_max = max(region_min, region_max)
    # Clamp marks
    x_target = max(0, min(x_target, total - region_min))
    o_target = max(0, min(o_target, 2))
    # Decide region count
    region_count = random.randint(region_min, region_max)
    region_total = total - max(x_target, 0)
    if region_total < region_count:
        region_count = region_total
    if region_count <= 0:
        grid = [['X' for _ in range(cols)] for _ in range(rows)]
        all_cells = [(r, c) for r in range(rows) for c in range(cols)]
        random.shuffle(all_cells)
        for i in range(min(o_target, len(all_cells))):
            r, c = all_cells[i]
            grid[r][c] = 'O'
        # 奇偶修正：确保 X 的数量为偶数
        x_count = sum(1 for r in range(rows) for c in range(cols) if grid[r][c] == 'X')
        if x_count % 2 == 1:
            for r in range(rows):
                done = False
                for c in range(cols):
                    if grid[r][c] == 'X':
                        grid[r][c] = 'O'
                        done = True
                        break
                if done:
                    break
        return grid
    # Sizes per region
    sizes = choose_region_sizes(region_total, region_count, reg_size_min, reg_size_max)
    labels = letter_sequence(region_count)
    grid = [['' for _ in range(cols)] for _ in range(rows)]
    unassigned = {(r, c) for r in range(1, rows + 1) for c in range(1, cols + 1)}
    # seeds
    seeds: List[Cell] = []
    for _ in range(region_count):
        seed = random.choice(list(unassigned))
        seeds.append(seed)
        unassigned.remove(seed)
    # grow regions
    for reg_idx in range(region_count):
        target = sizes[reg_idx]
        lab = labels[reg_idx]
        frontier = [seeds[reg_idx]]
        assigned = 0
        r0, c0 = seeds[reg_idx]
        grid[r0 - 1][c0 - 1] = lab
        assigned += 1
        while assigned < target:
            if not frontier:
                if not unassigned:
                    break
                new_seed = random.choice(list(unassigned))
                frontier.append(new_seed)
            cur = random.choice(frontier)
            neighs = neighbors(cur, rows, cols)
            random.shuffle(neighs)
            placed = False
            for nb in neighs:
                if nb in unassigned:
                    r, c = nb
                    grid[r - 1][c - 1] = lab
                    unassigned.remove(nb)
                    frontier.append(nb)
                    assigned += 1
                    placed = True
                    break
            if not placed and unassigned:
                nb = random.choice(list(unassigned))
                r, c = nb
                grid[r - 1][c - 1] = lab
                unassigned.remove(nb)
                frontier.append(nb)
                assigned += 1
            if random.random() < 0.3 and cur in frontier:
                frontier.remove(cur)
    # fill blank as X until we meet x_target (note: may exceed x_target depending on blanks)
    current_x = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '':
                grid[r][c] = 'X'
                current_x += 1
    remaining_to_convert_x = max(0, x_target - current_x)
    if remaining_to_convert_x > 0:
        non_x_cells = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] != 'X']
        random.shuffle(non_x_cells)
        for i in range(min(remaining_to_convert_x, len(non_x_cells))):
            r, c = non_x_cells[i]
            grid[r][c] = 'X'
    # place O marks (small number, random)
    non_o_cells = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] != 'O']
    random.shuffle(non_o_cells)
    o_to_place = o_target
    for i in range(min(o_to_place, len(non_o_cells))):
        r, c = non_o_cells[i]
        grid[r][c] = 'O'
    # 奇偶修正：若 X 数为奇数，将一个 X 改为字母区以保证 #X 为偶数
    x_count = sum(1 for rr in range(rows) for cc in range(cols) if grid[rr][cc] == 'X')
    if x_count % 2 == 1:
        done = False
        for rr in range(1, rows + 1):
            if done:
                break
            for cc in range(1, cols + 1):
                if grid[rr - 1][cc - 1] == 'X':
                    for nb in neighbors((rr, cc), rows, cols):
                        r2, c2 = nb
                        lab = grid[r2 - 1][c2 - 1]
                        if lab not in ('X', 'O', ''):
                            grid[rr - 1][cc - 1] = lab
                            done = True
                            break
                    if done:
                        break
        if not done:
            first_lab = None
            for rr in range(rows):
                for cc in range(cols):
                    if grid[rr][cc] not in ('X', 'O', ''):
                        first_lab = grid[rr][cc]
                        break
                if first_lab:
                    break
            if first_lab is None:
                for rr in range(rows):
                    notdone = False
                    for cc in range(cols):
                        if grid[rr][cc] == 'X':
                            grid[rr][cc] = 'O'
                            notdone = True
                            break
                    if notdone:
                        break
            else:
                for rr in range(rows):
                    ended = False
                    for cc in range(cols):
                        if grid[rr][cc] == 'X':
                            grid[rr][cc] = first_lab
                            ended = True
                            break
                    if ended:
                        break
    return grid

def select_blocked_edges(edges: List[Edge], blocked_edge_num: int) -> List[Edge]:
    n = len(edges)
    cap = max(0, n // 10)
    k = max(0, min(blocked_edge_num, cap))
    sampled = random.sample(edges, k) if k > 0 else []
    return sampled

def grid_to_line(labels_grid: List[List[str]]) -> str:
    rows_str = []
    for row in labels_grid:
        rows_str.append(' '.join(row))
    return '[' + '; '.join(rows_str) + ']'

def blocked_indices(edges: List[Edge], blocked_edges: List[Edge]) -> List[int]:
    idx_map: Dict[Tuple[Cell, Cell], int] = {}
    for i, e in enumerate(edges):
        u, v = e
        idx_map[(u, v)] = i
        idx_map[(v, u)] = i
    out: List[int] = []
    for e in blocked_edges:
        u, v = e
        if (u, v) in idx_map:
            out.append(idx_map[(u, v)])
        elif (v, u) in idx_map:
            out.append(idx_map[(v, u)])
    return sorted(set(out))

def edge_orientation_indices(edges: List[Edge]) -> Dict[str, List[int]]:
    h: List[int] = []
    v: List[int] = []
    for i, e in enumerate(edges):
        (r1, c1), (r2, c2) = e
        if r1 == r2:
            h.append(i)
        else:
            v.append(i)
    return {'H': h, 'V': v}

def _edge_index_map(edges: List[Edge]) -> Dict[Tuple[Cell, Cell], int]:
    m: Dict[Tuple[Cell, Cell], int] = {}
    for i, e in enumerate(edges):
        u, v = e
        m[(u, v)] = i
        m[(v, u)] = i
    return m

def square_edge_groups(rows: int, cols: int, edges: List[Edge]) -> List[List[int]]:
    m = _edge_index_map(edges)
    groups: List[List[int]] = []
    for r in range(1, rows):
        for c in range(1, cols):
            top = ((r, c), (r, c + 1))
            bottom = ((r + 1, c), (r + 1, c + 1))
            left = ((r, c), (r + 1, c))
            right = ((r, c + 1), (r + 1, c + 1))
            g = []
            for e in (top, bottom, left, right):
                if e in m:
                    g.append(m[e])
            if g:
                groups.append(g)
    return groups

def adj_desc_from_policy(policy: int) -> str:
    if policy == 0:
        return '不同多米诺不能在正交方向上相邻（共享边相接）；同一条边上的两个格子可作为一个多米诺。'
    else:
        return '在任意2×2方块内部，至多允许放置一个多米诺（即该方块内部不出现平行相邻的两个多米诺）。'

def orient_rule_desc(switch: int, hmin: int, vmin: int) -> str:
    if switch == 1:
        return f'另外，至少需要放置 {hmin} 个水平多米诺、以及 {vmin} 个竖直多米诺。'
    return ''

def marks_desc(has_o: bool) -> str:
    if has_o:
        return '标记为 O 的格子必须保持未覆盖。'
    return ''

# ---------- New helpers for expansion ----------

def perimeter_edge_indices(rows: int, cols: int, edges: List[Edge]) -> List[int]:
    m = _edge_index_map(edges)
    idxs: List[int] = []
    for r in range(1, rows + 1):
        for c in range(1, cols):
            if r == 1 or r == rows:
                e = ((r, c), (r, c + 1))
                if e in m: idxs.append(m[e])
    for r in range(1, rows):
        for c in range(1, cols + 1):
            if c == 1 or c == cols:
                e = ((r, c), (r + 1, c))
                if e in m: idxs.append(m[e])
    return sorted(set(idxs))

def region_internal_edges_map(labels_grid: List[List[str]], edges: List[Edge]) -> Dict[str, List[int]]:
    regs = sorted({lab for row in labels_grid for lab in row if lab not in ('X', 'O')})
    groups: Dict[str, List[int]] = {r: [] for r in regs}
    def lab_at(cell: Cell) -> str:
        r, c = cell
        return labels_grid[r - 1][c - 1]
    for i, e in enumerate(edges):
        u, v = e
        lu = lab_at(u)
        lv = lab_at(v)
        if lu == lv and lu not in ('X', 'O'):
            groups[lu].append(i)
    for k in groups:
        groups[k] = sorted(set(groups[k]))
    return groups

def bridge_edge_indices(labels_grid: List[List[str]], edges: List[Edge]) -> List[int]:
    def lab_at(cell: Cell) -> str:
        r, c = cell
        return labels_grid[r - 1][c - 1]
    idxs: List[int] = []
    for i, e in enumerate(edges):
        u, v = e
        lu = lab_at(u)
        lv = lab_at(v)
        if lu not in ('X', 'O') and lv not in ('X', 'O') and lu != lv:
            idxs.append(i)
    return sorted(set(idxs))

def row_cell_groups(rows: int, cols: int, cells: List[Cell]) -> List[List[int]]:
    ct2i = cell_to_index_map(cells)
    groups: List[List[int]] = [[] for _ in range(rows)]
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            idx = ct2i[(r, c)]
            groups[r - 1].append(idx)
    return groups

def choose_k_rows(rows: int, k: int) -> List[int]:
    k = max(1, min(k, rows))
    all_rows = list(range(1, rows + 1))
    random.shuffle(all_rows)
    return sorted(all_rows[:k])

def row_hints_desc(row_ids: List[int], row_values: List[int]) -> str:
    parts = []
    for i, rid in enumerate(row_ids):
        parts.append(f'第{rid}行被覆盖格数为 {row_values[i]}')
    return '；'.join(parts)

def hv_balance_desc(switch: int, limit: int) -> str:
    if switch == 1:
        return f'水平与竖直多米诺数量的差不超过 {limit}。'
    return ''

def bridge_rule_desc(mincnt: int) -> str:
    return f'至少需要 {mincnt} 条跨区多米诺（跨越不同字母区域的多米诺）。'

def intra_rule_desc(mincnt: int) -> str:
    return f'至少需要 {mincnt} 个字母区域的两格由同一多米诺连接。'

# ---------- New adaptive selectors to lower UNSAT probability ----------

def choose_adjacency_policy(rows: int, cols: int, x_count: int,
                            blocked_edge_num: int, bridge_min: int,
                            intra_quota_min: int) -> int:
    area = rows * cols
    pressure = 0
    pressure += 2 * bridge_min + 2 * intra_quota_min
    pressure += (x_count // max(1, area // 8))
    pressure += (blocked_edge_num // max(1, (area // 6)))
    if area <= 20 or pressure >= 2:
        return 1
    return random.choice([0, 1, 1])

def choose_orientation_switch(rows: int, cols: int,
                              hmin: int, vmin: int,
                              blocked_edge_num: int) -> int:
    total_edges = rows * (cols - 1) + (rows - 1) * cols
    if total_edges == 0:
        return 0
    if blocked_edge_num > total_edges // 6 or rows * cols <= 20:
        return 0
    return random.choice([0, 1, 0])

def choose_hv_balance_switch(rows: int, cols: int,
                             hmin: int, vmin: int) -> int:
    if rows * cols <= 20:
        return 0
    return random.choice([0, 1, 0])

# ---------- New helpers to clamp quotas ----------

def clamp_to_max(x: int, m: int) -> int:
    return x if x <= m else m

def list_diff(a: List[int], b: List[int]) -> List[int]:
    s = set(b)
    return [x for x in a if x not in s]

# ---------- Column-based hint helpers (new) ----------

def col_cell_groups(rows: int, cols: int, cells: List[Cell]) -> List[List[int]]:
    ct2i = cell_to_index_map(cells)
    groups: List[List[int]] = [[] for _ in range(cols)]
    for c in range(1, cols + 1):
        for r in range(1, rows + 1):
            idx = ct2i[(r, c)]
            groups[c - 1].append(idx)
    return groups

def choose_k_cols(cols: int, k: int) -> List[int]:
    k = max(1, min(k, cols))
    all_cols = list(range(1, cols + 1))
    random.shuffle(all_cols)
    return sorted(all_cols[:k])

def col_hints_desc(col_ids: List[int], col_values: List[int]) -> str:
    parts = []
    for i, cid in enumerate(col_ids):
        parts.append(f'第{cid}列被覆盖格数为 {col_values[i]}')
    return '；'.join(parts)

# ---------- New: exact-count descriptions for equality hints ----------

def bridge_eq_desc(k: int) -> str:
    return f'恰有 {k} 条跨区多米诺（跨越不同字母区域的多米诺）。'

def intra_eq_desc(k: int) -> str:
    return f'恰有 {k} 个字母区域的两格由同一多米诺连接。'

# ---------- New: text helpers for safer optional sections & format notes ----------

def fmt_optional_section(title: str, body: str) -> str:
    if not body:
        return ''
    return f'{title}{body}'

def edge_format_desc() -> str:
    return '边采用 r_c-r2_c2 表示两个相邻格子的坐标对'

def grid_format_desc() -> str:
    return '棋盘行使用分号分隔，每行格子用空格分隔；X 表示必须覆盖格子，O 表示禁止覆盖格子，其他字母表示字母区域。'

# ---------- New: legal placement description ----------
def domino_legal_desc() -> str:
    return '多米诺可以覆盖任意两个相邻且不是 O 的格子（包括字母-字母、字母-X、X-X）；其中“内部多米诺”指两端属于同一字母区域，“跨区多米诺”指两端属于不同字母区域（均为字母格）。X 不属于任何字母区域，仅作为必须覆盖的普通格子参与放置。'