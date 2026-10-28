import sys, json, random
from typing import List, Tuple, Dict, Any, Optional
from z3 import Solver, Bool, Sum, If, Or, And, Not, sat

Coord = Tuple[int, int]
Domino = Tuple[Coord, Coord]

# ----------------------- Utilities -----------------------

def rc_in_bounds(r, c, R, C):
    return 1 <= r <= R and 1 <= c <= C

def neighbors_ortho(r, c, R, C):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        rr, cc = r+dr, c+dc
        if rc_in_bounds(rr, cc, R, C):
            yield (rr, cc)

def canonical_domino(a: Coord, b: Coord) -> Domino:
    return (a, b) if a <= b else (b, a)

def all_adjacent_pairs(R, C) -> List[Domino]:
    pairs = []
    for r in range(1, R+1):
        for c in range(1, C+1):
            if c+1 <= C:
                pairs.append(canonical_domino((r,c),(r,c+1)))
            if r+1 <= R:
                pairs.append(canonical_domino((r,c),(r+1,c)))
    return pairs

def json_dumps_cn(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

# ----------------------- Region generation -----------------------

def gen_regions_partition(rng: random.Random, R: int, C: int, num_regions: int, x_count: int):
    """
    生成一个包含若干区域(字母标识) + 若干 X(不属于任何区域) 的 5x5 网格。
    保证每个区域大小 >= 2，且总区域格子数 = R*C - x_count。
    """
    assert 0 <= x_count < R*C
    N = R*C
    cells = [(r,c) for r in range(1,R+1) for c in range(1,C+1)]

    # 选 X
    X = set(rng.sample(cells, x_count))
    region_cells = [cell for cell in cells if cell not in X]
    M = len(region_cells)

    # 每个区域至少2格
    if num_regions * 2 > M:
        raise ValueError("区域数量过多，无法保证每个区域至少2格。")

    # 生成一个随机连通分区：先选种子，再生长
    # 用 BFS/随机扩展把所有非X格子分配给 num_regions 个区域，尽量连通
    # 若失败则重试由外层负责
    seeds = rng.sample(region_cells, num_regions)
    reg_of: Dict[Coord, int] = {}
    fronts: List[List[Coord]] = [[] for _ in range(num_regions)]
    for i, s in enumerate(seeds):
        reg_of[s] = i
        fronts[i].append(s)

    unassigned = set(region_cells)
    for s in seeds:
        unassigned.remove(s)

    # 先让每个区域至少2格：优先给每个种子扩一个邻居（若可）
    for i in range(num_regions):
        if not unassigned:
            break
        s = seeds[i]
        cand = [nb for nb in neighbors_ortho(*s, R, C) if nb in unassigned]
        rng.shuffle(cand)
        if cand:
            nb = cand[0]
            reg_of[nb] = i
            fronts[i].append(nb)
            unassigned.remove(nb)

    # 其余随机扩展
    safety = 0
    while unassigned and safety < 2000:
        safety += 1
        # 选一个仍可扩展的区域
        reg_indices = list(range(num_regions))
        rng.shuffle(reg_indices)
        progressed = False
        for i in reg_indices:
            # 收集边界可扩展格
            boundary = []
            for cell in fronts[i]:
                for nb in neighbors_ortho(*cell, R, C):
                    if nb in unassigned:
                        boundary.append(nb)
            if not boundary:
                continue
            nb = rng.choice(boundary)
            reg_of[nb] = i
            fronts[i].append(nb)
            unassigned.remove(nb)
            progressed = True
            break
        if not progressed:
            # 如果无法扩展（由于断裂），随机把一个未分配格子强行塞给最近区域（允许不连通但尽量少）
            u = rng.choice(list(unassigned))
            # 找与 u 正交相邻的已分配区域
            adj_regs = []
            for nb in neighbors_ortho(*u, R, C):
                if nb in reg_of:
                    adj_regs.append(reg_of[nb])
            if adj_regs:
                i = rng.choice(adj_regs)
            else:
                i = rng.randrange(num_regions)
            reg_of[u] = i
            fronts[i].append(u)
            unassigned.remove(u)

    if unassigned:
        raise ValueError("分区生成失败：仍有未分配格。")

    # 统计每区大小，确保 >=2
    sizes = [0]*num_regions
    for cell, i in reg_of.items():
        sizes[i] += 1
    if any(sz < 2 for sz in sizes):
        raise ValueError("分区生成失败：存在小于2格的区域。")

    # 构建网格字符：区域用字母 A,B,C... ；X用 'X'
    labels = [chr(ord('A')+i) for i in range(num_regions)]
    grid = [['' for _ in range(C)] for _ in range(R)]
    for r in range(1,R+1):
        for c in range(1,C+1):
            if (r,c) in X:
                grid[r-1][c-1] = 'X'
            else:
                grid[r-1][c-1] = labels[reg_of[(r,c)]]
    return grid, labels, X

def grid_to_text(grid: List[List[str]]) -> str:
    return "\n".join(" ".join(row) for row in grid)

# ----------------------- Norinori solver model -----------------------

class NorinoriInstance:
    def __init__(self, grid: List[List[str]], labels: List[str], X: set, lang: str = "zh"):
        self.grid = grid
        self.R = len(grid)
        self.C = len(grid[0]) if self.R else 0
        self.labels = labels
        self.X = set(X)
        # 收集区域格
        self.region_cells: Dict[str, List[Coord]] = {lab: [] for lab in labels}
        for r in range(1, self.R+1):
            for c in range(1, self.C+1):
                ch = grid[r-1][c-1]
                if ch == 'X':
                    continue
                self.region_cells[ch].append((r,c))

        # 所有可选多米诺
        self.dominoes = all_adjacent_pairs(self.R, self.C)
        self.d_index = {d:i for i,d in enumerate(self.dominoes)}

        # 每个格子涉及哪些多米诺
        self.cell_to_dom: Dict[Coord, List[int]] = {}
        for i, (a,b) in enumerate(self.dominoes):
            for cell in (a,b):
                self.cell_to_dom.setdefault(cell, []).append(i)

        # 相邻约束：选中的多米诺不能共享边（正交相邻）
        # 建立冲突对列表
        self.conflicts: List[Tuple[int,int]] = []
        # 预先计算每个多米诺覆盖的格集合
        dom_cells = [set(d) for d in self.dominoes]
        # 若两个多米诺有共享格则也不可（覆盖唯一性会处理，但冲突可加快）
        # 更重要：若它们覆盖的任意两个格正交相邻（且不是同一多米诺内部那一对）
        # 则冲突。
        cell_list = [(r,c) for r in range(1,self.R+1) for c in range(1,self.C+1)]
        ortho_adj = set()
        for r,c in cell_list:
            for nb in neighbors_ortho(r,c,self.R,self.C):
                a = (r,c); b = nb
                if a <= b:
                    ortho_adj.add((a,b))
                else:
                    ortho_adj.add((b,a))

        for i in range(len(self.dominoes)):
            for j in range(i+1, len(self.dominoes)):
                # 若共享格：冲突（虽然由唯一覆盖也能避免）
                if dom_cells[i] & dom_cells[j]:
                    self.conflicts.append((i,j))
                    continue
                # 检查正交相邻
                bad = False
                for ca in dom_cells[i]:
                    for cb in dom_cells[j]:
                        pair = (ca, cb) if ca <= cb else (cb, ca)
                        if pair in ortho_adj:
                            bad = True
                            break
                    if bad:
                        break
                if bad:
                    self.conflicts.append((i,j))

    def solve(self, require_unique: bool = True, rng: Optional[random.Random]=None, max_solutions: int = 2):
        """
        求解该 Norinori 约束：
        - 每个区域恰好 2 个格子被覆盖
        - X 格必须被覆盖
        - 每格至多被覆盖一次（由多米诺选取表示）
        - 多米诺之间不共享边（正交相邻），允许对角
        - 多米诺可以跨区域
        返回：(solutions, model_domino_indices)
        solutions: list of list of Domino (坐标对)
        """
        s = Solver()
        use = [Bool(f"d_{i}") for i in range(len(self.dominoes))]

        # 每个格子至多被一个多米诺覆盖
        for r in range(1, self.R+1):
            for c in range(1, self.C+1):
                idxs = self.cell_to_dom.get((r,c), [])
                if not idxs:
                    # 5x5不会发生
                    continue
                s.add(Sum([If(use[i], 1, 0) for i in idxs]) <= 1)

        # X格必须被覆盖：恰好1（因为至多1），所以 >=1
        for cell in self.X:
            idxs = self.cell_to_dom.get(cell, [])
            s.add(Sum([If(use[i], 1, 0) for i in idxs]) == 1)

        # 区域覆盖数=2
        for lab, cells in self.region_cells.items():
            cover_terms = []
            for cell in cells:
                idxs = self.cell_to_dom.get(cell, [])
                cover_terms.append(Sum([If(use[i], 1, 0) for i in idxs]))
            s.add(Sum(cover_terms) == 2)

        # 多米诺之间不共享边（正交相邻）
        for i,j in self.conflicts:
            s.add(Not(And(use[i], use[j])))

        # 可选：轻微对称破除/随机引导（不影响正确性）
        # 不强制。

        solutions = []
        dom_index_solutions = []

        # 通过枚举解来检查唯一性/取一个解
        while len(solutions) < max_solutions and s.check() == sat:
            m = s.model()
            chosen = [i for i in range(len(use)) if m.evaluate(use[i], model_completion=True)]
            doms = [self.dominoes[i] for i in chosen]
            # 校验：所有 chosen 的确两格相邻
            for a,b in doms:
                if abs(a[0]-b[0]) + abs(a[1]-b[1]) != 1:
                    raise AssertionError("非相邻格组成的多米诺。")
            solutions.append(doms)
            dom_index_solutions.append(chosen)
            # block this solution
            s.add(Or([use[i] != m.evaluate(use[i], model_completion=True) for i in range(len(use))]))

        if require_unique and len(solutions) != 1:
            return None
        return solutions, dom_index_solutions

    def render_problem_zh(self) -> str:
        rules = (
            f"你的挑战是通过在 {self.R}×{self.C} 的网格上放置多米诺来解决一个 Norinori 谜题。\n"
            f"请在网格中放置若干个多米诺（1×2 或 2×1）。\n\n"
            f"规则：\n"
            f"- 每个区域（用字母标识）必须恰好有 2 个格子被多米诺覆盖。\n"
            f"- 标记为 'X' 的格子不属于任何区域，但每个 X 格都必须被某个多米诺覆盖。\n"
            f"- 多米诺可以跨越区域边界。\n"
            f"- 任意两块多米诺不能共享边（即它们覆盖的格子之间不能正交相邻）；但允许对角线相接。\n"
            f"- 每个格子最多只能被一个多米诺覆盖。\n\n"
            f"网格（从上到下为第1..{self.R}行，从左到右为第1..{self.C}列）：\n"
            f"{grid_to_text(self.grid)}\n\n"
            f"问题：给出所有多米诺的位置。将每个多米诺表示为一对坐标，例如 [(1,2),(1,3)]。\n"
            f"答案格式：[[((r1,c1),(r1,c2)), ...]] 这样的列表（每个元素是一块多米诺的两端坐标；坐标从1开始）。"
        )
        # 说明：为了兼容 seed 的格式，输出中用 [(r,c),(r,c)] 的形式；这里描述更宽松。
        return rules

# ----------------------- Explanation -----------------------

def format_domino_list(doms: List[Domino]) -> List[List[List[int]]]:
    # 输出为 [[(r,c),(r,c)], ...] 但JSON中用列表表示元组
    out = []
    for (a,b) in doms:
        out.append([[a[0], a[1]], [b[0], b[1]]])
    return out

def explanation_zh(instance: NorinoriInstance, doms: List[Domino]) -> str:
    # 生成可复核的简短校验说明：列出每个区域被覆盖的格、X格覆盖、以及“不相邻”检查方式
    covered = set()
    for a,b in doms:
        covered.add(a); covered.add(b)

    # 区域计数
    reg_cov = {}
    for lab, cells in instance.region_cells.items():
        reg_cov[lab] = [cell for cell in cells if cell in covered]

    # X 覆盖
    x_cov = {cell: (cell in covered) for cell in sorted(instance.X)}

    # 不相邻：检查任意两多米诺覆盖格之间是否正交相邻
    dom_cells = [set(d) for d in doms]
    ok_adj = True
    for i in range(len(doms)):
        for j in range(i+1, len(doms)):
            bad = False
            for ca in dom_cells[i]:
                for cb in dom_cells[j]:
                    if abs(ca[0]-cb[0]) + abs(ca[1]-cb[1]) == 1:
                        bad = True
                        break
                if bad:
                    break
            if bad:
                ok_adj = False
                break
        if not ok_adj:
            break

    lines = []
    lines.append("校验要点：")
    # 1) 每区恰好2格
    for lab in sorted(reg_cov.keys()):
        cells = reg_cov[lab]
        lines.append(f"- 区域 {lab} 被覆盖的格子数 = {len(cells)}，分别是 {cells}")
    # 2) X 必须覆盖
    if instance.X:
        lines.append(f"- X 格覆盖情况：{x_cov}")
    else:
        lines.append("- 本题没有 X 格。")
    # 3) 多米诺不相邻
    lines.append(f"- 任意两块多米诺之间正交不相邻：{'满足' if ok_adj else '不满足'}。")
    lines.append("将上面的覆盖统计与规则逐条对照即可复核。")
    return "\n".join(lines)

# ----------------------- Generator -----------------------

def generate_one(rng: random.Random, lang: str = "zh") -> Dict[str, Any]:
    R = 5
    C = 5

    # 多样性：区域数、X数量变化
    # 区域数太少会空间太大，太多则每区太小；取 3..7
    num_regions = rng.randint(3, 7)
    x_count = rng.randint(0, 4)

    # 重采样上限
    for _ in range(120):
        try:
            grid, labels, X = gen_regions_partition(rng, R, C, num_regions, x_count)
        except Exception:
            continue

        inst = NorinoriInstance(grid, labels, X, lang=lang)

        sol = inst.solve(require_unique=True, max_solutions=2)
        if sol is None:
            continue
        solutions, _ = sol
        doms = solutions[0]

        # 基本渲染检查：所有区域都在 grid 中出现，且X位置一致
        # 检查domino合法且不重叠
        seen = set()
        ok = True
        for a,b in doms:
            if abs(a[0]-b[0]) + abs(a[1]-b[1]) != 1:
                ok = False; break
            if a in seen or b in seen:
                ok = False; break
            seen.add(a); seen.add(b)
        if not ok:
            continue
        # X必须覆盖
        if any(x not in seen for x in X):
            continue
        # 每区恰2覆盖
        for lab, cells in inst.region_cells.items():
            cnt = sum(1 for cell in cells if cell in seen)
            if cnt != 2:
                ok = False; break
        if not ok:
            continue

        problem = inst.render_problem_zh() if lang == "zh" else inst.render_problem_zh()
        answer = format_domino_list([canonical_domino(a,b) for (a,b) in doms])
        expl = explanation_zh(inst, doms) if lang == "zh" else explanation_zh(inst, doms)

        return {"problem": problem, "answer": answer, "explanation": expl}

    raise RuntimeError("在重采样上限内未能生成具有唯一解的实例。")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # 语言：题面要求由外部传入，但本程序仅从 stdin 读取 seed/count。
    # 若需固定中文，直接用中文。
    lang = "zh"

    results = []
    seen_fingerprints = set()

    # 去重：基于网格文本的fingerprint（足以防止大量重复）
    attempts = 0
    while len(results) < count and attempts < count * 300:
        attempts += 1
        item = generate_one(rng, lang=lang)
        # fingerprint: problem中的网格部分
        fp = item["problem"]
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)
        results.append(item)

    if len(results) != count:
        print(f"只生成了 {len(results)}/{count} 道题（达到采样上限）。", file=sys.stderr)

    sys.stdout.write(json_dumps_cn(results))

if __name__ == "__main__":
    main()