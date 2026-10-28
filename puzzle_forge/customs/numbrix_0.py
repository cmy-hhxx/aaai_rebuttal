import random

def gen_serpentine_with_transform(n, seed=None):
    """
    生成 n×n 的蛇形（哈密顿路径）解网格，然后随机旋转/翻转以增加多样性。
    返回：grid（二维列表），grid[r][c] = 1..n^2
    """
    if seed is not None:
        random.seed(seed)
    # 基础蛇形填充
    grid = [[0]*n for _ in range(n)]
    val = 1
    for r in range(n):
        if r % 2 == 0:
            # 左->右
            for c in range(n):
                grid[r][c] = val
                val += 1
        else:
            # 右->左
            for c in range(n-1, -1, -1):
                grid[r][c] = val
                val += 1

    # 随机选择一个对称变换：旋转0/90/180/270，再随机水平或垂直翻转
    def rot90(g):
        return [list(row) for row in zip(*g[::-1])]
    def rot180(g):
        return rot90(rot90(g))
    def rot270(g):
        return rot90(rot180(g))
    def flip_h(g):
        return [row[::-1] for row in g]
    def flip_v(g):
        return g[::-1]

    transforms = [
        lambda x: x,
        rot90,
        rot180,
        rot270
    ]
    g = random.choice(transforms)(grid)
    if random.choice([True, False]):
        g = flip_h(g)
    if random.choice([True, False]):
        g = flip_v(g)
    return g


def gen_clues_from_grid(grid, min_per_row=2, add_mid=True, seed=None):
    """
    从已知解网格中选取线索，返回dict:
        {'vals': [...], 'rows': [...], 'cols': [...]}
    策略：
      - 必含 1 和 n^2 两个端点（强锚点）
      - 每行至少选择两端（col=0 与 col=n-1）作为线索（若重复会去重）
      - 随机挑选若干行在中列再放1个线索（提高唯一性）
      - 线索总数约为 2n~3n，留足空格
    """
    if seed is not None:
        random.seed(seed)
    n = len(grid)
    vals, rows, cols = [], [], []
    def add(r, c):
        v = grid[r][c]
        # 去重
        for i in range(len(vals)):
            if rows[i] == r and cols[i] == c:
                return
        vals.append(v); rows.append(r); cols.append(c)

    # 强锚点：1 和 n^2
    # 找1和n^2位置
    pos = {}
    for r in range(n):
        for c in range(n):
            pos[grid[r][c]] = (r, c)
    add(*pos[1])
    add(*pos[n*n])

    # 每行两端
    for r in range(n):
        add(r, 0)
        add(r, n-1)

    # 适当增加中间锚点（每行随机加1个）
    candidate_cols = list(range(1, n-1))
    if add_mid and candidate_cols:
        for r in range(n):
            if random.random() < 0.6:  # 约60%的行添加一个中列线索
                c = random.choice(candidate_cols)
                add(r, c)

    # 确保线索覆盖足够多（至少 2n，且不超过 n^2-2 保持题目有空）
    # 若不足，随机补一些中间格
    targets = max(2*n, len(vals))
    cells = [(r, c) for r in range(n) for c in range(n)]
    random.shuffle(cells)
    for (r, c) in cells:
        if len(vals) >= targets:
            break
        add(r, c)

    # 不要过多线索（最多保留3n左右，以免题面无空格）
    if len(vals) > 3*n:
        # 固定保留端点1与n^2，再从其余线索中随机裁剪
        must_keep = set([pos[1], pos[n*n]])
        other = [(rows[i], cols[i]) for i in range(len(vals)) if (rows[i], cols[i]) not in must_keep]
        random.shuffle(other)
        keep = list(must_keep) + other[:3*n - 2]
        # 重组
        nv, nr, nc = [], [], []
        s = set((r, c) for (r, c) in keep)
        for r in range(n):
            for c in range(n):
                if (r, c) in s:
                    nv.append(grid[r][c]); nr.append(r); nc.append(c)
        vals, rows, cols = nv, nr, nc

    return {'vals': vals, 'rows': rows, 'cols': cols}


def build_clue_grid(n, vals, rows, cols):
    """
    构造只含线索的 n×n 网格；无线索处放 None
    """
    g = [[None]*n for _ in range(n)]
    for v, r, c in zip(vals, rows, cols):
        g[r][c] = v
    return g


def render_grid_text(grid):
    """
    将仅包含线索的二维网格渲染为ASCII文本，空位用'X'表示。
    单元宽度自适应（右对齐）。
    """
    n = len(grid)
    # 单元宽度按最大数字长度
    maxv = n*n
    w = max(2, len(str(maxv)))
    sep = '+' + '+'.join(['-'*(w+2) for _ in range(n)]) + '+\n'

    def cell_text(v):
        if v is None:
            s = 'X'
        else:
            s = str(v)
        return ' ' + s.rjust(w) + ' '

    out = []
    out.append(sep)
    for r in range(n):
        row = '|' + '|'.join([cell_text(grid[r][c]) for c in range(n)]) + '|\n'
        out.append(row)
        out.append(sep)
    return ''.join(out)