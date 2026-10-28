import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# We generate "Arrow puzzle" instances:
# - n*n grid with some numbered cells (black squares) and blanks ("X")
# - Each numbered cell has exactly one arrow direction (U/D/L/R).
# - Its arrow extends in that direction over consecutive blank cells until before next numbered cell or boundary.
# - The number on the numbered cell equals how many blank cells its arrow covers.
# - Arrows cannot pass through or cross other arrows. With axis-aligned rays, "cross" can only happen
#   when a horizontal arrow segment intersects a vertical arrow segment at a blank cell.
# - Each blank cell must be covered by at least one arrow.
# Output: replace each X by one of {↓ ↑ → ←} indicating which arrow(s) cover that blank cell.
# Since a blank can be covered by multiple arrows, we define a deterministic tie-break to keep output single-symbol:
#   choose the direction of the covering arrow whose source numbered cell is closest (Manhattan distance along the ray).
#   If still tied, choose by fixed order: ↑, ↓, ←, →.
# This makes the output well-defined while respecting rule 6 ("at least one arrow").
#
# We construct puzzles by:
# 1) Choosing n.
# 2) Placing numbered cells such that every blank cell is covered exactly once by the induced arrows
#    (stronger than "at least one") and no crossings occur by construction.
# 3) Then the arrow directions are implicit from construction; numbers are computed lengths.
# 4) We verify all rules and uniqueness of the drawn matrix (it is unique given our construction).
#
# Note: The puzzle statement asks to "replace X regions with arrows". In seed, numbered cells keep numbers,
# and X become arrows. We follow that.

DIRS = {
    'U': (-1, 0, '↑'),
    'D': (1, 0, '↓'),
    'L': (0, -1, '←'),
    'R': (0, 1, '→'),
}
TIE_ORDER = ['↑', '↓', '←', '→']
TIE_RANK = {ch: i for i, ch in enumerate(TIE_ORDER)}

def inb(n, r, c):
    return 0 <= r < n and 0 <= c < n

def render_problem_grid(n: int, numbered: Dict[Tuple[int,int], int]) -> List[List[str]]:
    g = [['X' for _ in range(n)] for _ in range(n)]
    for (r,c), val in numbered.items():
        g[r][c] = str(val)
    return g

def fmt_output_matrix(mat: List[List[str]]) -> str:
    # Each row: space-separated; rows separated by comma. Wrapped in [[...]].
    rows = [' '.join(row) for row in mat]
    return "[[" + ",".join(rows) + "]]"

def fmt_problem_text(grid: List[List[str]], lang='zh') -> str:
    n = len(grid)
    lines = []
    for i in range(n):
        lines.append(f"{i+1}: " + ' '.join(grid[i]))
    if lang == 'zh':
        intro = (
            "下面是一个自定义“箭头覆盖”谜题。\n"
            "规则（题目已自包含）：\n"
            "1) 在 n×n 网格中，一些格子是数字格（黑格），其余为空白格（用 X 表示）。\n"
            "2) 每个数字格必须发出且只发出一支箭头，方向只能是 ↑ ↓ ← →。\n"
            "3) 箭头从该数字格出发，沿所选方向连续覆盖若干个相邻空白格，直到到达边界或下一个数字格前停止。\n"
            "4) 该箭头覆盖的空白格数量必须恰好等于数字格上的数字。\n"
            "5) 任意两支箭头不能穿过数字格；且箭头之间不能在空白格发生相交（水平段与垂直段在同一空白格相交视为相交）。\n"
            "6) 每个空白格至少被一支箭头覆盖。\n"
            "任务：把矩阵中的每个 X 替换为一个箭头符号（↑↓←→），数字保持不变，并按“从左到右、从上到下”输出矩阵。\n"
            "输出格式：每行元素用空格分隔，不同行用英文逗号分隔，并整体用双中括号包裹，例如 [[a b c, d e f]]。\n"
        )
        return intro + "\n题目矩阵：\n" + "\n".join(lines)
    else:
        return "\n".join(lines)

def compute_coverage(n: int,
                     numbered: Dict[Tuple[int,int], int],
                     arrows: Dict[Tuple[int,int], str]) -> Tuple[Dict[Tuple[int,int], List[Tuple[Tuple[int,int], str, int]]], bool, str]:
    """
    returns:
      cover_map: blank cell -> list of (source_cell, arrow_char, distance_from_source_along_ray starting at 1)
      ok, msg
    """
    cover_map: Dict[Tuple[int,int], List[Tuple[Tuple[int,int], str, int]]] = {}
    # build set for quick check
    num_cells = set(numbered.keys())

    # collect segments for intersection check
    # represent each covered blank cell per arrow; crossings happen when a blank is covered by both a horizontal and vertical arrow
    for src, dkey in arrows.items():
        if src not in numbered:
            return {}, False, "存在非数字格发箭头"
        dr, dc, ch = DIRS[dkey]
        r, c = src
        steps = 0
        rr, cc = r + dr, c + dc
        while inb(n, rr, cc) and (rr, cc) not in num_cells:
            steps += 1
            cover_map.setdefault((rr, cc), []).append((src, ch, steps))
            rr += dr
            cc += dc
        # check number matches
        if numbered[src] != steps:
            return {}, False, f"数字格{src}的数字与覆盖长度不符"
    # each blank must be covered >=1
    for r in range(n):
        for c in range(n):
            if (r,c) in num_cells:
                continue
            if (r,c) not in cover_map:
                return {}, False, f"存在未被覆盖的空白格 {(r,c)}"

    # intersection check: if a blank cell has both horizontal and vertical coverings, it's a crossing (not allowed)
    for cell, lst in cover_map.items():
        has_h = any(ch in ['←','→'] for _, ch, _ in lst)
        has_v = any(ch in ['↑','↓'] for _, ch, _ in lst)
        if has_h and has_v:
            return {}, False, f"存在箭头相交于空白格 {cell}"
    return cover_map, True, "OK"

def draw_matrix(n: int,
                numbered: Dict[Tuple[int,int], int],
                arrows: Dict[Tuple[int,int], str],
                cover_map: Dict[Tuple[int,int], List[Tuple[Tuple[int,int], str, int]]]) -> List[List[str]]:
    # Fill digits and arrows on blanks using deterministic tie-break.
    mat = [['' for _ in range(n)] for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if (r,c) in numbered:
                mat[r][c] = str(numbered[(r,c)])
            else:
                lst = cover_map[(r,c)]
                # choose minimal distance; tie by arrow symbol order
                best = None
                for src, ch, dist in lst:
                    key = (dist, TIE_RANK.get(ch, 99))
                    if best is None or key < best[0]:
                        best = (key, ch)
                mat[r][c] = best[1]
    return mat

# --- Construction families ---

def family_stripes(rng: random.Random) -> Tuple[int, Dict[Tuple[int,int], int], Dict[Tuple[int,int], str]]:
    """
    Construct without crossings by using only horizontal arrows or only vertical arrows,
    and ensure each blank covered exactly once.
    Pattern: place a numbered cell at the start of each stripe segment.
    """
    n = rng.randint(6, 9)
    mode = rng.choice(['H', 'V'])
    numbered: Dict[Tuple[int,int], int] = {}
    arrows: Dict[Tuple[int,int], str] = {}

    if mode == 'H':
        # for each row, partition columns into segments; each segment starts with number cell, arrows go right
        for r in range(n):
            c = 0
            while c < n:
                # choose segment length for blanks after number: k in [1, min(4, remaining-1)] but allow 0 occasionally
                remaining = n - c
                if remaining == 1:
                    # last cell must be a blank covered by someone earlier; avoid: instead place number with 0 not allowed.
                    # So ensure we never leave remaining==1 here by choosing earlier segments appropriately.
                    # fallback: turn this cell into part of previous segment by regenerating row.
                    # We'll restart whole construction if happens.
                    raise ValueError("row segmentation failed")
                maxk = min(4, remaining - 1)
                k = rng.randint(1, maxk)
                numbered[(r, c)] = k
                arrows[(r, c)] = 'R'
                c = c + 1 + k
                # The k blanks are positions c0+1..c0+k; next segment begins at c0+1+k
        # Any cell not listed as numbered is blank.
    else:
        # vertical stripes: for each column, segments start with number, arrows go down
        for c in range(n):
            r = 0
            while r < n:
                remaining = n - r
                if remaining == 1:
                    raise ValueError("col segmentation failed")
                maxk = min(4, remaining - 1)
                k = rng.randint(1, maxk)
                numbered[(r, c)] = k
                arrows[(r, c)] = 'D'
                r = r + 1 + k

    return n, numbered, arrows

def family_boxes(rng: random.Random) -> Tuple[int, Dict[Tuple[int,int], int], Dict[Tuple[int,int], str]]:
    """
    Create non-crossing by using a mix but separating regions:
    Top half uses horizontal right arrows; bottom half uses vertical down arrows,
    with a full numbered separator row to prevent crossings.
    """
    n = rng.randint(7, 10)
    sep = rng.randint(2, n-3)  # separator row index
    numbered: Dict[Tuple[int,int], int] = {}
    arrows: Dict[Tuple[int,int], str] = {}

    # Separator row: make every cell a numbered cell with arrow length 0 not allowed -> instead,
    # make it a chain of length 1 right arrows, leaving blanks next cell; but then crossings? still horizontal.
    # Easier: make separator row all numbered with length 1 alternating and ensure within bounds by restarting if odd.
    if n % 2 == 1:
        # allow odd, still possible with varying lengths; use segmentation.
        pass

    # Top region rows [0..sep-1]: horizontal segments
    for r in range(sep):
        c = 0
        while c < n:
            remaining = n - c
            if remaining == 1:
                raise ValueError("top segmentation failed")
            maxk = min(3, remaining - 1)
            k = rng.randint(1, maxk)
            numbered[(r, c)] = k
            arrows[(r, c)] = 'R'
            c = c + 1 + k

    # Separator row sep: make it all numbered cells with arrow going left length = its column index (covers blanks?) can't.
    # Instead make it vertical up arrows into top? would cross. So: make it horizontal too and ensure it covers its own blanks,
    # leaving no blanks on that row: use pattern [Num,blank] repeated; last cell if odd handled by 2-length.
    r = sep
    c = 0
    while c < n:
        remaining = n - c
        if remaining == 1:
            # set previous number to cover one more blank not possible; so avoid by using k=2 earlier
            raise ValueError("sep row failed")
        if remaining == 2:
            k = 1
        else:
            k = rng.choice([1, 2])
        numbered[(r, c)] = k
        arrows[(r, c)] = 'R'
        c = c + 1 + k

    # Bottom region rows [sep+1..n-1]: vertical segments in each column, starting from sep+1
    for c in range(n):
        r = sep + 1
        while r < n:
            remaining = n - r
            if remaining == 1:
                raise ValueError("bottom segmentation failed")
            maxk = min(3, remaining - 1)
            k = rng.randint(1, maxk)
            numbered[(r, c)] = k
            arrows[(r, c)] = 'D'
            r = r + 1 + k

    return n, numbered, arrows

def generate_one(rng: random.Random, lang: str) -> Dict[str, Any]:
    families = [family_stripes, family_boxes]
    for attempt in range(200):
        fam = rng.choice(families)
        try:
            n, numbered, arrows = fam(rng)
        except Exception:
            continue

        cover_map, ok, msg = compute_coverage(n, numbered, arrows)
        if not ok:
            continue

        # Additional check: no blank covered by >1 arrow (optional) to make "drawn matrix" unambiguous.
        # If not, we still can output due to tie-break, but keep stronger property for cleaner puzzles.
        if any(len(v) != 1 for v in cover_map.values()):
            continue

        mat = draw_matrix(n, numbered, arrows, cover_map)

        # Cross-verify numbers by recomputation independent of compute_coverage:
        for (r,c), val in numbered.items():
            dkey = arrows[(r,c)]
            dr, dc, _ = DIRS[dkey]
            rr, cc = r+dr, c+dc
            steps = 0
            while inb(n, rr, cc) and (rr, cc) not in numbered:
                steps += 1
                rr += dr
                cc += dc
            if steps != val:
                raise RuntimeError("独立校验失败：数字长度不一致")

        problem_grid = render_problem_grid(n, numbered)
        problem_text = fmt_problem_text(problem_grid, lang=lang)
        answer = fmt_output_matrix(mat)

        # Explanation: give a short verifiable summary + one example cell/path.
        # Pick 2 numbered cells to illustrate.
        nums = list(numbered.items())
        rng.shuffle(nums)
        sample = nums[:2]
        ex_lines = []
        if lang == 'zh':
            ex_lines.append("校验要点：每个数字格向其箭头方向连续覆盖恰好等于数字的空白格；且本题构造保证空白格被且仅被一支箭头覆盖，因此不会出现相交。")
            for (r,c), val in sample:
                dkey = arrows[(r,c)]
                dr, dc, ch = DIRS[dkey]
                path = []
                rr, cc = r+dr, c+dc
                while inb(n, rr, cc) and (rr, cc) not in numbered:
                    path.append((rr+1, cc+1))
                    rr += dr
                    cc += dc
                ex_lines.append(f"例如第({r+1},{c+1})格数字为{val}，箭头为{ch}，覆盖的空白格坐标依次为：{path}（共{len(path)}格）。")
        else:
            ex_lines.append("Checked lengths and non-crossing coverage.")
        explanation = "\n".join(ex_lines)

        return {"problem": problem_text, "answer": answer, "explanation": explanation}

    raise RuntimeError("在采样上限内未能生成满足约束的题目，请更换 seed 或降低要求。")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    lang = data.get("output_language", "zh")

    rng = random.Random(seed)
    out = []
    seen = set()
    failures = 0

    while len(out) < count:
        if failures > 5000:
            raise RuntimeError("生成失败次数过多，无法完成目标数量。")
        item = generate_one(rng, lang)
        key = item["problem"]
        if key in seen:
            failures += 1
            continue
        seen.add(key)
        out.append(item)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise