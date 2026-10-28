import sys, json, random
from typing import List, Tuple, Dict, Any

# Arrow-cover puzzle generator (self-contained).
# Key fix vs previous version: construction is now deterministic-feasible (no rejection-heavy sampling).
# We generate two always-valid families:
#   A) Pure horizontal (all arrows go right), row-wise segmentation with exact cover, no crossings.
#   B) Pure vertical (all arrows go down), column-wise segmentation with exact cover, no crossings.
# Because all arrows share orientation, crossings are impossible, and every blank is covered exactly once.
# Thus generation never fails and is fast/reproducible.

DIRS = {
    'R': (0, 1, '→'),
    'D': (1, 0, '↓'),
    'L': (0, -1, '←'),
    'U': (-1, 0, '↑'),
}

def inb(n: int, r: int, c: int) -> bool:
    return 0 <= r < n and 0 <= c < n

def fmt_output_matrix(mat: List[List[str]]) -> str:
    rows = [' '.join(row) for row in mat]
    return "[[" + ",".join(rows) + "]]"

def fmt_problem_text(grid: List[List[str]], lang: str = 'zh') -> str:
    n = len(grid)
    lines = []
    for i in range(n):
        lines.append(f"{i+1}: " + ' '.join(grid[i]))
    if lang == 'zh':
        intro = (
            "下面是一个自定义“箭头覆盖”谜题。\n"
            "规则（题目自包含）：\n"
            "1) 在 n×n 网格中，一些格子是数字格（数字直接写在格内），其余为空白格（用 X 表示）。\n"
            "2) 每个数字格必须发出且只发出一支箭头，方向只能是 ↑ ↓ ← →。\n"
            "3) 箭头从该数字格出发，沿所选方向连续覆盖若干个相邻空白格，直到到达边界或下一个数字格前停止。\n"
            "4) 该箭头覆盖的空白格数量必须恰好等于数字格上的数字。\n"
            "5) 箭头不能穿过数字格；且任意两支箭头不能在空白格处相交（水平段与垂直段在同一空白格相交视为相交）。\n"
            "6) 每个空白格至少被一支箭头覆盖。\n"
            "任务：把矩阵中的每个 X 替换为一个箭头符号（↑↓←→），数字保持不变。\n"
            "输出格式：从左到右、从上到下；每行元素用空格分隔，不同行用英文逗号分隔，并整体用双中括号包裹。\n"
        )
        return intro + "\n题目矩阵：\n" + "\n".join(lines)
    else:
        return "\n".join(lines)

def segment_lengths(total_blanks: int, rng: random.Random, max_len: int) -> List[int]:
    """
    Partition total_blanks into positive lengths <= max_len.
    Always possible for total_blanks>=1 if max_len>=1.
    """
    lengths = []
    remaining = total_blanks
    while remaining > 0:
        k = rng.randint(1, min(max_len, remaining))
        lengths.append(k)
        remaining -= k
    return lengths

def build_horizontal_instance(n: int, rng: random.Random, max_len: int = 5) -> Tuple[Dict[Tuple[int,int], int], Dict[Tuple[int,int], str]]:
    """
    For each row, we place alternating [Number cell][k blank cells] repeated.
    This yields exact cover of all blanks by right arrows; no crossings.
    """
    numbered: Dict[Tuple[int,int], int] = {}
    arrows: Dict[Tuple[int,int], str] = {}
    for r in range(n):
        c = 0
        while c < n:
            remaining_cells = n - c
            if remaining_cells == 1:
                # Make the last cell a numbered cell that points right with 0 blanks would be illegal.
                # So we ensure this never happens by adjusting: convert previous segment to absorb one more blank.
                # Practically: backtrack one step by forcing a 1-blank segment earlier.
                # To keep it simple and guaranteed, we restart this row deterministically by using a fixed pattern.
                # Fixed pattern for row: [num=1, blank] repeated, with last cell as num=1 and blank exists.
                # This requires n even; if odd, use a [num=2, blank blank] for first then [1,blank]...
                pass
            # Choose k blanks after number. Need 1 + k <= remaining_cells.
            # So k <= remaining_cells-1.
            if remaining_cells >= 2:
                kmax = min(max_len, remaining_cells - 1)
                k = rng.randint(1, kmax)
                numbered[(r, c)] = k
                arrows[(r, c)] = 'R'
                c = c + 1 + k
            else:
                break

        # Fix if ended with remaining_cells==1 situation (unfilled last cell).
        # We detect any unassigned cell in row and rebuild the row with a guaranteed pattern.
        assigned = set((rr, cc) for (rr, cc) in numbered.keys() if rr == r)
        if len(assigned) == 0:
            # shouldn't happen
            continue
        # Check if last column is blank but uncovered: in our construction every blank is covered by its left number.
        # The only issue is if c ended at n-1 (leaving final cell as number-only without blanks), which can't happen due to k>=1.
        # But we might have left exactly 1 cell not processed if we hit remaining_cells==1.
        # Let's verify coverage-by-row shape; if invalid, rebuild row with deterministic safe tiling.
        # Safe tiling:
        # - If n even: repeat (num=1, blank) => numbers at even indices 0,2,4,... n-2
        # - If n odd: start with (num=2, blank, blank), then (num=1, blank) repeating.
        # This always consumes exactly n cells.
        if not _row_valid_horizontal(n, r, numbered):
            # remove row entries then rebuild
            for key in [k for k in numbered.keys() if k[0] == r]:
                numbered.pop(key, None)
                arrows.pop(key, None)
            c = 0
            if n % 2 == 1:
                # place 2 then two blanks
                numbered[(r, 0)] = 2
                arrows[(r, 0)] = 'R'
                c = 3
            while c < n:
                # place 1 then one blank
                numbered[(r, c)] = 1
                arrows[(r, c)] = 'R'
                c += 2

    return numbered, arrows

def _row_valid_horizontal(n: int, r: int, numbered: Dict[Tuple[int,int], int]) -> bool:
    # simulate row to ensure every cell is either a number or covered blank and no uncovered leftover
    numpos = {c: numbered[(r,c)] for (rr,c) in numbered.keys() if rr == r}
    covered = [False]*n
    isnum = [False]*n
    for c, k in numpos.items():
        if c < 0 or c >= n: return False
        isnum[c] = True
        # must have k>=1 and fit without hitting another number by construction
        if k < 1: return False
        if c + k >= n: return False
        for cc in range(c+1, c+k+1):
            if isnum[cc]:  # two numbers inside segment
                return False
            covered[cc] = True
    # every non-number should be covered
    for c in range(n):
        if not isnum[c] and not covered[c]:
            return False
    return True

def build_vertical_instance(n: int, rng: random.Random, max_len: int = 5) -> Tuple[Dict[Tuple[int,int], int], Dict[Tuple[int,int], str]]:
    numbered: Dict[Tuple[int,int], int] = {}
    arrows: Dict[Tuple[int,int], str] = {}
    for c in range(n):
        r = 0
        while r < n:
            remaining_cells = n - r
            if remaining_cells >= 2:
                kmax = min(max_len, remaining_cells - 1)
                k = rng.randint(1, kmax)
                numbered[(r, c)] = k
                arrows[(r, c)] = 'D'
                r = r + 1 + k
            else:
                break
        if not _col_valid_vertical(n, c, numbered):
            # rebuild column with deterministic safe tiling
            for key in [k for k in numbered.keys() if k[1] == c]:
                numbered.pop(key, None)
                arrows.pop(key, None)
            r = 0
            if n % 2 == 1:
                numbered[(0, c)] = 2
                arrows[(0, c)] = 'D'
                r = 3
            while r < n:
                numbered[(r, c)] = 1
                arrows[(r, c)] = 'D'
                r += 2
    return numbered, arrows

def _col_valid_vertical(n: int, c: int, numbered: Dict[Tuple[int,int], int]) -> bool:
    numpos = {r: numbered[(r,c)] for (r,cc) in numbered.keys() if cc == c}
    covered = [False]*n
    isnum = [False]*n
    for r, k in numpos.items():
        isnum[r] = True
        if k < 1: return False
        if r + k >= n: return False
        for rr in range(r+1, r+k+1):
            if isnum[rr]:
                return False
            covered[rr] = True
    for r in range(n):
        if not isnum[r] and not covered[r]:
            return False
    return True

def compute_cover_map(n: int,
                      numbered: Dict[Tuple[int,int], int],
                      arrows: Dict[Tuple[int,int], str]) -> Dict[Tuple[int,int], str]:
    """
    Since our constructions ensure each blank is covered exactly once,
    return map blank_cell -> arrow_char covering it.
    """
    num_cells = set(numbered.keys())
    blank_to_char: Dict[Tuple[int,int], str] = {}

    for (r,c), val in numbered.items():
        dkey = arrows[(r,c)]
        dr, dc, ch = DIRS[dkey]
        rr, cc = r+dr, c+dc
        steps = 0
        while inb(n, rr, cc) and (rr, cc) not in num_cells:
            steps += 1
            if (rr, cc) in blank_to_char:
                # would mean multi-cover; shouldn't happen
                raise RuntimeError("构造校验失败：空白格被多支箭头覆盖")
            blank_to_char[(rr, cc)] = ch
            rr += dr
            cc += dc
        if steps != val:
            raise RuntimeError("构造校验失败：数字与覆盖长度不一致")

    # ensure all blanks covered
    for r in range(n):
        for c in range(n):
            if (r,c) in num_cells:
                continue
            if (r,c) not in blank_to_char:
                raise RuntimeError("构造校验失败：存在未覆盖空白格")
    return blank_to_char

def render_problem_grid(n: int, numbered: Dict[Tuple[int,int], int]) -> List[List[str]]:
    g = [['X' for _ in range(n)] for _ in range(n)]
    for (r,c), v in numbered.items():
        g[r][c] = str(v)
    return g

def render_answer_grid(n: int,
                       numbered: Dict[Tuple[int,int], int],
                       blank_to_char: Dict[Tuple[int,int], str]) -> List[List[str]]:
    g = [['' for _ in range(n)] for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if (r,c) in numbered:
                g[r][c] = str(numbered[(r,c)])
            else:
                g[r][c] = blank_to_char[(r,c)]
    return g

def generate_one(rng: random.Random, lang: str) -> Dict[str, Any]:
    # choose family and size
    fam = rng.choice(['H', 'V'])
    n = rng.randint(6, 10)
    max_len = rng.randint(3, 6)

    if fam == 'H':
        numbered, arrows = build_horizontal_instance(n, rng, max_len=max_len)
    else:
        numbered, arrows = build_vertical_instance(n, rng, max_len=max_len)

    blank_to_char = compute_cover_map(n, numbered, arrows)

    problem_grid = render_problem_grid(n, numbered)
    answer_grid = render_answer_grid(n, numbered, blank_to_char)

    problem_text = fmt_problem_text(problem_grid, lang=lang)
    answer = fmt_output_matrix(answer_grid)

    # explanation: show 2 numbered cells' arrow direction and covered coordinates
    items = list(numbered.items())
    rng.shuffle(items)
    samples = items[:2]
    ex_lines = []
    if lang == 'zh':
        ex_lines.append("本题的箭头满足：每个数字格发出一支箭头，覆盖的连续空白格数量恰等于该数字；且所有箭头同向（全水平或全竖直）因此不会发生相交。")
        for (r,c), v in samples:
            dkey = arrows[(r,c)]
            dr, dc, ch = DIRS[dkey]
            coords = []
            rr, cc = r+dr, c+dc
            while inb(n, rr, cc) and (rr, cc) not in numbered:
                coords.append((rr+1, cc+1))
                rr += dr
                cc += dc
            ex_lines.append(f"例如数字格({r+1},{c+1})= {v}，箭头为{ch}，覆盖坐标序列为 {coords}。")
    else:
        ex_lines.append("Verified arrow lengths and coverage.")
    explanation = "\n".join(ex_lines)

    return {"problem": problem_text, "answer": answer, "explanation": explanation}

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    lang = data.get("output_language", "zh")

    rng = random.Random(seed)
    out = []
    seen = set()

    # bounded retries to avoid duplicates; but generation space is large
    retries = 0
    while len(out) < count:
        if retries > 2000:
            raise RuntimeError("去重重试次数过多；请更换 seed 或减小 count。")
        item = generate_one(rng, lang)
        if item["problem"] in seen:
            retries += 1
            continue
        seen.add(item["problem"])
        out.append(item)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise