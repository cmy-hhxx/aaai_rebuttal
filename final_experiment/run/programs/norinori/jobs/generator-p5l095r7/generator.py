import sys, json, random
from typing import List, Tuple, Dict, Any, Optional
from z3 import Solver, Bool, Sum, If, Or, And, Not, sat

Coord = Tuple[int, int]
Domino = Tuple[Coord, Coord]

# ----------------------- Utilities -----------------------

def rc_in_bounds(r: int, c: int, R: int, C: int) -> bool:
    return 1 <= r <= R and 1 <= c <= C

def neighbors_ortho(r: int, c: int, R: int, C: int):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        rr, cc = r+dr, c+dc
        if rc_in_bounds(rr, cc, R, C):
            yield (rr, cc)

def canonical_domino(a: Coord, b: Coord) -> Domino:
    return (a, b) if a <= b else (b, a)

def all_adjacent_pairs(R: int, C: int) -> List[Domino]:
    pairs = []
    for r in range(1, R+1):
        for c in range(1, C+1):
            if c+1 <= C:
                pairs.append(canonical_domino((r,c),(r,c+1)))
            if r+1 <= R:
                pairs.append(canonical_domino((r,c),(r+1,c)))
    return pairs

def json_dumps_cn(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def grid_to_text(grid: List[List[str]]) -> str:
    return "\n".join(" ".join(row) for row in grid)

# ----------------------- Instance (given a full grid labeling) -----------------------

class NorinoriInstance:
    """
    网格用字符矩阵：
    - 'X'：不属于任何区域，但必须被覆盖
    - 其他（如'A'..'G'）：区域标签
    """
    def __init__(self, grid: List[List[str]], labels: List[str], X: set, lang: str = "zh"):
        self.grid = grid
        self.R = len(grid)
        self.C = len(grid[0]) if self.R else 0
        self.labels = labels
        self.X = set(X)

        # 区域格列表
        self.region_cells: Dict[str, List[Coord]] = {lab: [] for lab in labels}
        for r in range(1, self.R+1):
            for c in range(1, self.C+1):
                ch = grid[r-1][c-1]
                if ch == 'X':
                    continue
                if ch not in self.region_cells:
                    # 防御：允许labels遗漏时自动补
                    self.region_cells[ch] = []
                    self.labels.append(ch)
                self.region_cells[ch].append((r,c))

        # 所有可选多米诺（相邻格对）
        self.dominoes = all_adjacent_pairs(self.R, self.C)

        # 每个格涉及哪些多米诺
        self.cell_to_dom: Dict[Coord, List[int]] = {}
        for i, (a,b) in enumerate(self.dominoes):
            self.cell_to_dom.setdefault(a, []).append(i)
            self.cell_to_dom.setdefault(b, []).append(i)

        # 冲突：两多米诺若覆盖格之间存在正交相邻（或重叠）则不可同时选
        self.conflicts: List[Tuple[int,int]] = []
        dom_cells = [set(d) for d in self.dominoes]
        for i in range(len(self.dominoes)):
            for j in range(i+1, len(self.dominoes)):
                if dom_cells[i] & dom_cells[j]:
                    self.conflicts.append((i,j))
                    continue
                bad = False
                for ca in dom_cells[i]:
                    for cb in dom_cells[j]:
                        if abs(ca[0]-cb[0]) + abs(ca[1]-cb[1]) == 1:
                            bad = True
                            break
                    if bad:
                        break
                if bad:
                    self.conflicts.append((i,j))

    def solve(self, require_unique: bool = True, max_solutions: int = 2):
        s = Solver()
        use = [Bool(f"d_{i}") for i in range(len(self.dominoes))]

        # 每格至多覆盖一次
        for r in range(1, self.R+1):
            for c in range(1, self.C+1):
                idxs = self.cell_to_dom.get((r,c), [])
                s.add(Sum([If(use[i], 1, 0) for i in idxs]) <= 1)

        # X 必须被覆盖（由于<=1，等价于==1）
        for cell in self.X:
            idxs = self.cell_to_dom.get(cell, [])
            s.add(Sum([If(use[i], 1, 0) for i in idxs]) == 1)

        # 每个区域恰好2格被覆盖
        for lab, cells in self.region_cells.items():
            cover_terms = []
            for cell in cells:
                idxs = self.cell_to_dom.get(cell, [])
                cover_terms.append(Sum([If(use[i], 1, 0) for i in idxs]))
            s.add(Sum(cover_terms) == 2)

        # 多米诺不共享边（且不重叠）
        for i,j in self.conflicts:
            s.add(Not(And(use[i], use[j])))

        solutions: List[List[Domino]] = []
        chosen_lists: List[List[int]] = []

        while len(solutions) < max_solutions and s.check() == sat:
            m = s.model()
            chosen = [i for i in range(len(use)) if bool(m.evaluate(use[i], model_completion=True))]
            doms = [self.dominoes[i] for i in chosen]
            solutions.append(doms)
            chosen_lists.append(chosen)
            # block current solution
            s.add(Or([use[i] != m.evaluate(use[i], model_completion=True) for i in range(len(use))]))

        if require_unique and len(solutions) != 1:
            return None
        return solutions, chosen_lists

    def render_problem_zh(self) -> str:
        return (
            f"你的挑战是通过在 {self.R}×{self.C} 的网格上放置多米诺来解决这个 Norinori 谜题，使每个区域恰好有两个格子被覆盖。\n"
            f"# Norinori 谜题\n\n"
            f"## 规则：\n"
            f"- 在网格中放置多米诺（1×2 或 2×1 的矩形块）。\n"
            f"- 每个区域（用字母标识）必须恰好有两个格子被多米诺覆盖。\n"
            f"- 多米诺可以跨越区域边界。\n"
            f"- 多米诺不能共享边（即不能正交相邻），但可以对角线相接。\n"
            f"- 每个格子最多只能被一个多米诺覆盖。\n"
            f"- 标记为 'X' 的格子不属于任何区域，但是必须成为某个多米诺的一部分。\n\n"
            f"## 网格：\n"
            f"{grid_to_text(self.grid)}\n\n"
            f"请解决这个谜题，找出所有多米诺的位置。将每个多米诺表示为一对坐标，例如 [(1,2), (1,3)]。\n"
            f"注意：坐标从1开始计数（左上角的格子位置是 (1,1)）。\n\n"
            f"你的答案应该采用以下格式：[[ (r1,c1), (r1,c2) ], [ (r2,c1), (r2,c2) ], ...]，其中每对坐标表示一个多米诺。\n"
        )

# ----------------------- Explanation -----------------------

def format_domino_list(doms: List[Domino]) -> List[List[List[int]]]:
    out = []
    for a,b in doms:
        a,b = canonical_domino(a,b)
        out.append([[a[0], a[1]], [b[0], b[1]]])
    # 为稳定输出排序
    out.sort()
    return out

def explanation_zh(inst: NorinoriInstance, doms: List[Domino]) -> str:
    covered = set()
    for a,b in doms:
        covered.add(a); covered.add(b)

    lines = ["核对："]
    # 区域覆盖统计
    for lab in sorted(inst.region_cells.keys()):
        cells = [cell for cell in inst.region_cells[lab] if cell in covered]
        lines.append(f"- 区域 {lab} 覆盖了 {len(cells)} 格：{cells}")
    # X 覆盖
    if inst.X:
        lines.append(f"- X 格均被覆盖：{all((x in covered) for x in inst.X)}，X 列表：{sorted(inst.X)}")
    else:
        lines.append("- 本题没有 X 格。")

    # 不相邻检查（任意两多米诺覆盖格不能正交相邻）
    dom_cells = [set(d) for d in doms]
    ok = True
    witness = None
    for i in range(len(doms)):
        for j in range(i+1, len(doms)):
            for ca in dom_cells[i]:
                for cb in dom_cells[j]:
                    if abs(ca[0]-cb[0]) + abs(ca[1]-cb[1]) == 1:
                        ok = False
                        witness = (doms[i], doms[j], ca, cb)
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            break
    if ok:
        lines.append("- 任意两块多米诺之间都不发生正交相邻（满足规则）。")
    else:
        lines.append(f"- 发现正交相邻冲突（不应发生）：{witness}")

    return "\n".join(lines)

# ----------------------- Constructive generator (always solvable, then check uniqueness) -----------------------

def build_instance_from_domino_solution(rng: random.Random, R: int = 5, C: int = 5):
    """
    先随机选一组满足“不相邻且不重叠”的多米诺作为“目标解”，
    再用这些多米诺诱导区域划分：每个区域包含恰好2个被覆盖格 + 若干未覆盖格。
    这样天然满足“每区域恰好2格被覆盖”，且可通过控制区域来提高唯一性概率。
    """
    all_cells = [(r,c) for r in range(1,R+1) for c in range(1,C+1)]
    all_dom = all_adjacent_pairs(R, C)

    # 随机选择若干对作为 X 多米诺（让题型更像种子：可能有0..2个X）
    x_count = rng.randint(0, 2)
    X = set(rng.sample(all_cells, x_count))

    # 选择一组多米诺，要求：
    # - 覆盖所有X
    # - 彼此不重叠
    # - 彼此不正交相邻
    # 目标多米诺数：由区域数决定。区域数取 3..7 => 多米诺数同为区域数（每区2格=一个多米诺的2格，但可跨区；
    # 这里构造时先让每区的2格来自某个“被覆盖格对”，不必是同一多米诺的两格。为了更可控，这里让“被覆盖格集合”
    # 恰好是所选多米诺覆盖集合。
    num_regions = rng.randint(3, 7)
    target_domino_count = num_regions  # 使得覆盖格数=2*num_regions，剩余格作为“空白”

    # 预计算：多米诺之间是否冲突（重叠或正交相邻）
    dom_cells = [set(d) for d in all_dom]
    conflict = [[False]*len(all_dom) for _ in range(len(all_dom))]
    for i in range(len(all_dom)):
        for j in range(i+1, len(all_dom)):
            bad = False
            if dom_cells[i] & dom_cells[j]:
                bad = True
            else:
                for ca in dom_cells[i]:
                    for cb in dom_cells[j]:
                        if abs(ca[0]-cb[0]) + abs(ca[1]-cb[1]) == 1:
                            bad = True
                            break
                    if bad:
                        break
            conflict[i][j] = conflict[j][i] = bad

    # 先找必须覆盖X的多米诺候选集合
    x_cover_options: Dict[Coord, List[int]] = {}
    for x in X:
        x_cover_options[x] = []
        for i, d in enumerate(all_dom):
            if x in d:
                x_cover_options[x].append(i)
        if not x_cover_options[x]:
            raise RuntimeError("X格居然无法被任何多米诺覆盖（不可能）。")

    # 回溯选择多米诺（小规模，5x5足够快）
    chosen: List[int] = []
    used_cells: set = set()

    def can_add(i: int) -> bool:
        a,b = all_dom[i]
        if a in used_cells or b in used_cells:
            return False
        for j in chosen:
            if conflict[i][j]:
                return False
        return True

    # 先满足X
    x_list = list(X)

    def backtrack_x(k: int) -> bool:
        if k == len(x_list):
            return True
        x = x_list[k]
        opts = x_cover_options[x][:]
        rng.shuffle(opts)
        for i in opts:
            if not can_add(i):
                continue
            # add
            chosen.append(i)
            a,b = all_dom[i]
            used_cells.add(a); used_cells.add(b)
            if backtrack_x(k+1):
                return True
            # undo
            chosen.pop()
            used_cells.remove(a); used_cells.remove(b)
        return False

    if not backtrack_x(0):
        raise RuntimeError("无法为X选择不冲突的覆盖多米诺。")

    # 再填充到 target_domino_count
    remaining = [i for i in range(len(all_dom)) if i not in chosen]
    rng.shuffle(remaining)
    for i in remaining:
        if len(chosen) >= target_domino_count:
            break
        if can_add(i):
            chosen.append(i)
            a,b = all_dom[i]
            used_cells.add(a); used_cells.add(b)

    if len(chosen) < target_domino_count:
        # 构造失败，交给外层重采样
        raise RuntimeError("未能选出足够数量的不相邻多米诺。")

    chosen_doms = [all_dom[i] for i in chosen]
    covered_cells = set()
    for a,b in chosen_doms:
        covered_cells.add(a); covered_cells.add(b)

    # 构造区域：每个区域先包含恰好2个“被覆盖格”（从covered_cells中分组），再加入若干未覆盖格
    covered_list = list(covered_cells)
    rng.shuffle(covered_list)
    # 由于 chosen_doms 不重叠 => covered_cells 数=2*target_domino_count
    assert len(covered_list) == 2*target_domino_count

    region_seeds = []
    for i in range(num_regions):
        region_seeds.append([covered_list[2*i], covered_list[2*i+1]])

    # 未覆盖格
    uncovered = [cell for cell in all_cells if cell not in covered_cells and cell not in X]
    # 注意：X已经在covered_cells中必然成立（否则构造失败），所以这里排除X只是防御
    rng.shuffle(uncovered)

    # 分配未覆盖格到各区域，保证每区至少2格（已满足），并让区域大小有变化
    region_cells: List[List[Coord]] = [seed[:] for seed in region_seeds]
    for cell in uncovered:
        # 偏向扩展为连通：若某区域有正交邻居则优先
        candidate_regions = []
        for idx, rcells in enumerate(region_cells):
            for rr,cc in rcells:
                if abs(rr-cell[0]) + abs(cc-cell[1]) == 1:
                    candidate_regions.append(idx)
                    break
        if candidate_regions:
            idx = rng.choice(candidate_regions)
        else:
            idx = rng.randrange(num_regions)
        region_cells[idx].append(cell)

    # 生成网格字符
    labels = [chr(ord('A')+i) for i in range(num_regions)]
    grid = [['' for _ in range(C)] for _ in range(R)]
    Xset = set(X)

    # 先填区域
    reg_of = {}
    for i, cells in enumerate(region_cells):
        for cell in cells:
            reg_of[cell] = labels[i]
    # 填grid
    for r in range(1,R+1):
        for c in range(1,C+1):
            if (r,c) in Xset:
                grid[r-1][c-1] = 'X'
            else:
                grid[r-1][c-1] = reg_of[(r,c)]

    return grid, labels, Xset, chosen_doms

# ----------------------- Generator -----------------------

def generate_one(rng: random.Random, lang: str = "zh") -> Dict[str, Any]:
    # 通过“先构造解，再构造区域”大幅提高可解率与唯一解概率；仍以Z3检验唯一性。
    for _ in range(400):
        try:
            grid, labels, X, _chosen_doms = build_instance_from_domino_solution(rng, 5, 5)
        except Exception:
            continue

        inst = NorinoriInstance(grid, labels, X, lang=lang)
        sol = inst.solve(require_unique=True, max_solutions=2)
        if sol is None:
            continue
        doms = sol[0][0]

        # 基本合法性复核（避免渲染/模型不一致）
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
        if any(x not in seen for x in X):
            continue
        for lab, cells in inst.region_cells.items():
            if sum(1 for cell in cells if cell in seen) != 2:
                ok = False
                break
        if not ok:
            continue

        problem = inst.render_problem_zh() if lang == "zh" else inst.render_problem_zh()
        answer = format_domino_list(doms)
        expl = explanation_zh(inst, doms) if lang == "zh" else explanation_zh(inst, doms)
        return {"problem": problem, "answer": answer, "explanation": expl}

    # 如果唯一解太难，放宽到“返回一个解且声明非唯一”会违背题意，所以直接报错
    raise RuntimeError("在重采样上限内未能生成具有唯一解的实例。请更换seed重试。")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)
    lang = "zh"

    results = []
    seen_fps = set()

    attempts = 0
    max_attempts = max(1000, count * 800)
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng, lang=lang)
        except RuntimeError as e:
            # 如果阶段性很难，继续尝试直到上限
            print(str(e), file=sys.stderr)
            continue
        fp = item["problem"]  # 以题面文本去重
        if fp in seen_fps:
            continue
        seen_fps.add(fp)
        results.append(item)

    if len(results) != count:
        print(f"只生成了 {len(results)}/{count} 道题（达到采样上限）。", file=sys.stderr)

    sys.stdout.write(json_dumps_cn(results))

if __name__ == "__main__":
    main()