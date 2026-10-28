# futoshiki_0.py
# 修正版要点：
# - 新增 pick_from(options) 自定义算子，供 YAML 通过 formula 随机选择字符串枚举，避免不被支持的 str 类型。
# - 保留并增强：逆向生成 + 复合约束 + 唯一性验证 + 线索最小化（贪心移除，每步短时片复核）。
# - 唯一性验证仅使用对玩家可见的约束与线索，保证题面与验证一致。

import random
import time
from typing import List, Dict, Tuple, Set, Optional

# ---------------------------
# 自定义算子：从列表中随机取一个元素
# ---------------------------

def pick_from(options):
    if not isinstance(options, (list, tuple)) or len(options) == 0:
        raise ValueError("pick_from expects a non-empty list/tuple.")
    return random.choice(list(options))

# ---------------------------
# 基础：拉丁方阵生成与校验
# ---------------------------

def _is_latin_square(grid: List[List[int]]) -> bool:
    if not grid or not isinstance(grid, list):
        return False
    n = len(grid)
    target = set(range(1, n + 1))
    for r in range(n):
        row = grid[r]
        if len(row) != n or set(row) != target:
            return False
    for c in range(n):
        col = [grid[r][c] for r in range(n)]
        if set(col) != target:
            return False
    return True

def function_1(n: int) -> List[List[int]]:
    if not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer >= 2")
    base = [[(i + j) % n + 1 for j in range(n)] for i in range(n)]
    row_perm = list(range(n)); random.shuffle(row_perm)
    col_perm = list(range(n)); random.shuffle(col_perm)
    temp = [[base[row_perm[i]][col_perm[j]] for j in range(n)] for i in range(n)]
    sym = list(range(1, n + 1)); random.shuffle(sym)
    mapping = {k: sym[k - 1] for k in range(1, n + 1)}
    grid = [[mapping[temp[i][j]] for j in range(n)] for i in range(n)]
    if not _is_latin_square(grid):
        raise RuntimeError("Generated grid failed Latin validation.")
    return grid

# ---------------------------
# 约束编码
# ---------------------------

class Constraints:
    def __init__(self, n: int):
        self.n = n
        self.ineq: List[Tuple[Tuple[int,int], Tuple[int,int], str]] = []
        self.diff: List[Tuple[Tuple[int,int], Tuple[int,int], str, int]] = []
        self.cages: List[Tuple[List[Tuple[int,int]], str, int]] = []
        self.parity: Dict[Tuple[int,int], str] = {}
        self.mod: List[Tuple[Tuple[int,int], int, int]] = []
        self.diag: List[Tuple[str, str, int]] = []          # (which in {'main','anti'}, 'sum', target)
        self.rowcol_agg: List[Tuple[str, int, str, int]] = []# ('row'/'col', idx, 'sum', target)
        self.path_sum: List[Tuple[List[Tuple[int,int]], int]] = []

    def families_present(self) -> List[str]:
        fam = []
        if self.ineq: fam.append("相邻不等式")
        if self.diff: fam.append("差值约束")
        if self.cages: fam.append("连锁区域(笼子)")
        if self.parity: fam.append("奇偶约束")
        if self.mod: fam.append("取模约束")
        if self.diag: fam.append("对角线和")
        if self.rowcol_agg: fam.append("行列聚合")
        if self.path_sum: fam.append("路径和")
        return fam

# ---------------------------
# 文本工具
# ---------------------------

def _coord1(r: int, c: int) -> str:
    return f"({r+1},{c+1})"

def _verbal_cell(r: int, c: int) -> str:
    return f"第{r+1}行第{c+1}列"

def _ineq_text(a, b, rel, style: str) -> str:
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        return f"{_coord1(*a)} {rel} {_coord1(*b)}"
    else:
        s = "大于" if rel == ">" else "小于"
        return f"{_verbal_cell(*a)}的数{s}{_verbal_cell(*b)}的数"

def _diff_text(a, b, t, param, style: str) -> str:
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if t == "abs_eq":
        return f"|{_coord1(*a)} - {_coord1(*b)}| = {param}" if style == "symbolic" else f"{_verbal_cell(*a)}与{_verbal_cell(*b)}两格之差的绝对值等于{param}"
    elif t == "abs_ge":
        return f"|{_coord1(*a)} - {_coord1(*b)}| ≥ {param}" if style == "symbolic" else f"{_verbal_cell(*a)}与{_verbal_cell(*b)}两格之差的绝对值不小于{param}"
    else:
        return f"{_coord1(*a)} - {_coord1(*b)} = {param}" if style == "symbolic" else f"{_verbal_cell(*a)}的数比{_verbal_cell(*b)}的数大{param}"

def _cage_text(cells: List[Tuple[int,int]], op: str, target: int, style: str) -> str:
    coords_sym = ", ".join([_coord1(*xy) for xy in cells])
    coords_ver = "、".join([_verbal_cell(*xy) for xy in cells])
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        if op == "sum":
            return f"笼子[{coords_sym}] 用加法得到 {target}"
        elif op == "prod":
            return f"笼子[{coords_sym}] 用乘法得到 {target}"
        elif op == "diff":
            return f"笼子[{coords_sym}] 内较大数减较小数等于 {target}"
        else:
            return f"笼子[{coords_sym}] 内较大数除以较小数等于 {target}"
    else:
        if op == "sum":
            return f"同一笼子的格子（{coords_ver}）相加，结果为{target}"
        elif op == "prod":
            return f"同一笼子的格子（{coords_ver}）相乘，结果为{target}"
        elif op == "diff":
            return f"同一笼子的两格用较大的数减较小的数，结果为{target}"
        else:
            return f"同一笼子的两格用较大的数除以较小的数，结果为{target}"

def _parity_text(cell: Tuple[int,int], p: str, style: str) -> str:
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        return f"{_coord1(*cell)} % 2 = {0 if p=='even' else 1}"
    else:
        return f"{_verbal_cell(*cell)}应为{'偶数' if p=='even' else '奇数'}"

def _mod_text(cell: Tuple[int,int], m: int, r: int, style: str) -> str:
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        return f"{_coord1(*cell)} % {m} = {r}"
    else:
        return f"{_verbal_cell(*cell)}除以{m}的余数为{r}"

def _diag_text(which: str, op: str, target: int, style: str) -> str:
    name_sym = "主对角线" if which == "main" else "副对角线"
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        return f"{name_sym}的元素之和 = {target}"
    else:
        return f"{name_sym}（从左上到右下为主，从右上到左下为副）的所有数字相加为{target}"

def _rowcol_text(kind: str, idx: int, op: str, target: int, style: str) -> str:
    name = f"第{idx+1}{'行' if kind=='row' else '列'}"
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        return f"{name}的和 = {target}"
    else:
        return f"{name}中所有数字的和为{target}"

def _path_text(path: List[Tuple[int,int]], target: int, style: str) -> str:
    coords_sym = " -> ".join([_coord1(*xy) for xy in path])
    coords_ver = "、".join([_verbal_cell(*xy) for xy in path])
    if style == "mixed":
        style = random.choice(["symbolic", "verbal"])
    if style == "symbolic":
        return f"路径[{coords_sym}] 的数字之和 = {target}"
    else:
        return f"按顺序（{coords_ver}）相加，结果为{target}"

# ---------------------------
# 支撑生成
# ---------------------------

def _neighbors(n: int, i: int, j: int):
    for di, dj in [(1,0),(-1,0),(0,1),(0,-1)]:
        ni, nj = i+di, j+dj
        if 0 <= ni < n and 0 <= nj < n:
            yield (ni, nj)

def _all_adjacent_edges(n: int) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    edges = []
    for i in range(n):
        for j in range(n - 1):
            edges.append(((i, j), (i, j + 1)))
    for i in range(n - 1):
        for j in range(n):
            edges.append(((i, j), (i + 1, j)))
    return edges

def _sample_cages(n: int, cage_density: float) -> List[List[Tuple[int,int]]]:
    total = n * n
    target_cells = int(round(max(0.0, min(0.95, float(cage_density))) * total))
    if target_cells <= 0:
        return []
    cells = [(i, j) for i in range(n) for j in range(n)]
    random.shuffle(cells)
    used = set()
    cages: List[List[Tuple[int,int]]] = []
    consumed = 0
    k = 0
    while consumed < target_cells and k < len(cells):
        start = cells[k]; k += 1
        if start in used:
            continue
        cage = [start]
        used.add(start)
        consumed += 1
        max_size = random.choice([2, 3, 4])
        while len(cage) < max_size:
            frontier = []
            for (ci, cj) in cage:
                for nb in _neighbors(n, ci, cj):
                    if nb not in used:
                        frontier.append(nb)
            if not frontier:
                break
            pick = random.choice(frontier)
            cage.append(pick)
            used.add(pick)
            consumed += 1
            if consumed >= target_cells:
                break
        if len(cage) >= 2:
            cages.append(cage)
    return cages

def _sample_path(n: int, length: int) -> List[Tuple[int,int]]:
    all_cells = [(i, j) for i in range(n) for j in range(n)]
    start = random.choice(all_cells)
    path = [start]
    tried = 0
    while len(path) < length and tried < n*n*3:
        tried += 1
        last = path[-1]
        nbs = [nb for nb in _neighbors(n, *last) if nb not in path]
        if not nbs:
            start = random.choice(all_cells)
            path = [start]
            continue
        path.append(random.choice(nbs))
    if len(path) < length:
        random.shuffle(all_cells)
        used = set(path)
        for c in all_cells:
            if c not in used:
                path.append(c)
                used.add(c)
                if len(path) >= length:
                    break
    return path[:length]

# ---------------------------
# 从解派生约束
# ---------------------------

def _compose_constraints_from_solution(sol: List[List[int]],
                                       ineq_density: float,
                                       cage_density: float,
                                       rule_mode: str) -> Constraints:
    n = len(sol)
    cs = Constraints(n)
    edges = _all_adjacent_edges(n)
    total_edges = len(edges)
    ineq_num = max(1, int(round(min(max(ineq_density, 0.05), 0.95) * total_edges)))
    sampled_edges = random.sample(edges, ineq_num)
    for a, b in sampled_edges:
        va, vb = sol[a[0]][a[1]], sol[b[0]][b[1]]
        cs.ineq.append((a, b, ">" if va > vb else "<"))

    enable_diff = enable_cage = enable_parity = enable_mod = enable_diag = enable_rowcol = enable_path = False
    if rule_mode == 'auto':
        enable_diff = random.random() < 0.9
        enable_cage = random.random() < 0.8
        enable_parity = random.random() < 0.7
        enable_mod = random.random() < 0.5
        enable_diag = random.random() < 0.5
        enable_rowcol = random.random() < 0.6
        enable_path = random.random() < 0.6
    elif rule_mode == 'ineq_only':
        pass
    elif rule_mode == 'ineq_plus_diff':
        enable_diff = True
    elif rule_mode == 'ineq_plus_cages':
        enable_cage = True
    else:
        enable_diff = enable_cage = True
        enable_parity = random.random() < 0.7
        enable_mod = random.random() < 0.5
        enable_diag = random.random() < 0.5
        enable_rowcol = random.random() < 0.6
        enable_path = random.random() < 0.6

    if enable_diff:
        coords = [(i, j) for i in range(n) for j in range(n)]
        for _ in range(random.randint(n, 2*n)):
            a = random.choice(coords); b = random.choice(coords)
            if a == b: 
                continue
            va, vb = sol[a[0]][a[1]], sol[b[0]][b[1]]
            t = random.choice(["abs_eq", "abs_ge", "oriented"])
            if t == "abs_eq":
                cs.diff.append((a, b, t, abs(va - vb)))
            elif t == "abs_ge":
                cs.diff.append((a, b, t, random.randint(1, abs(va - vb))))
            else:
                if va >= vb:
                    cs.diff.append((a, b, t, va - vb))
                else:
                    cs.diff.append((b, a, t, vb - va))

    if enable_cage and cage_density > 0:
        cages = _sample_cages(n, cage_density)
        for cells in cages:
            vals = [sol[i][j] for (i, j) in cells]
            if len(cells) == 2:
                a, b = vals
                big, small = (a, b) if a >= b else (b, a)
                options = [("sum", a + b), ("prod", a * b), ("diff", big - small)]
                if small != 0 and big % small == 0:
                    options.append(("div", big // small))
                op, target = random.choice(options)
            else:
                s = sum(vals)
                p = 1
                for v in vals: p *= v
                op, target = random.choice([("sum", s), ("prod", p)])
            cs.cages.append((cells, op, target))

    if enable_parity:
        k = random.randint(n, 2*n)
        coords = [(i, j) for i in range(n) for j in range(n)]
        for cell in random.sample(coords, min(k, len(coords))):
            v = sol[cell[0]][cell[1]]
            cs.parity[cell] = "even" if v % 2 == 0 else "odd"

    if enable_mod:
        k = random.randint(n//2, n)
        coords = [(i, j) for i in range(n) for j in range(n)]
        for cell in random.sample(coords, min(k, len(coords))):
            v = sol[cell[0]][cell[1]]
            m = random.choice([2, 3]) if n <= 5 else random.choice([2, 3, 4])
            cs.mod.append((cell, m, v % m))

    if enable_diag:
        which = random.choice(["main", "anti"])
        target = sum(sol[i][i] for i in range(n)) if which == "main" else sum(sol[i][n-1-i] for i in range(n))
        cs.diag.append((which, "sum", target))

    if enable_rowcol:
        count = random.randint(1, max(1, n//2))
        rows = random.sample(range(n), count)
        for r in rows:
            target = sum(sol[r])
            cs.rowcol_agg.append(("row", r, "sum", target))
        cols = random.sample(range(n), count)
        for c in cols:
            target = sum(sol[i][c] for i in range(n))
            cs.rowcol_agg.append(("col", c, "sum", target))

    if enable_path:
        length = random.choice([n, n+1]) if n >= 5 else n
        path = _sample_path(n, length)
        target = sum(sol[i][j] for (i, j) in path)
        cs.path_sum.append((path, target))

    return cs

# ---------------------------
# 求解器：MRV + 前向检查 + 多族传播 + 唯一计数
# ---------------------------

class CPSolver:
    def __init__(self, n: int, cs: Constraints, hints: Dict[Tuple[int,int], int], time_limit: float = 10.0):
        self.n = n
        self.cs = cs
        self.dom: List[List[Set[int]]] = [[set(range(1, n+1)) for _ in range(n)] for _ in range(n)]
        self.sol_count = 0
        self.time_limit = time_limit
        self.start = time.time()
        # 初始线索/奇偶/模过滤
        for (i, j), v in hints.items():
            self.dom[i][j] = {v}
        for cell, p in cs.parity.items():
            i, j = cell
            self.dom[i][j] = {x for x in self.dom[i][j] if (x % 2 == 0) == (p == "even")}
        for (cell, m, r) in cs.mod:
            i, j = cell
            self.dom[i][j] = {x for x in self.dom[i][j] if x % m == r}

    def _timeout(self) -> bool:
        return (time.time() - self.start) > self.time_limit

    def _rowcol_propagate(self) -> bool:
        changed = False
        for i in range(self.n):
            fixed = {next(iter(self.dom[i][j])) for j in range(self.n) if len(self.dom[i][j]) == 1}
            for j in range(self.n):
                if len(self.dom[i][j]) > 1:
                    before = len(self.dom[i][j])
                    self.dom[i][j] -= fixed
                    if len(self.dom[i][j]) != before:
                        changed = True
        for j in range(self.n):
            fixed = {next(iter(self.dom[i][j])) for i in range(self.n) if len(self.dom[i][j]) == 1}
            for i in range(self.n):
                if len(self.dom[i][j]) > 1:
                    before = len(self.dom[i][j])
                    self.dom[i][j] -= fixed
                    if len(self.dom[i][j]) != before:
                        changed = True
        return changed

    def _ineq_propagate(self) -> bool:
        changed = False
        for (a, b, rel) in self.cs.ineq:
            ai, aj = a; bi, bj = b
            A = self.dom[ai][aj]; B = self.dom[bi][bj]
            if not A or not B: 
                continue
            if rel == ">":
                A2 = {x for x in A if x > min(B)} if B else set()
                B2 = {y for y in B if y < max(A)} if A else set()
            else:
                A2 = {x for x in A if x < max(B)} if B else set()
                B2 = {y for y in B if y > min(A)} if A else set()
            if A2 != A:
                self.dom[ai][aj] = A2; changed = True
            if B2 != B:
                self.dom[bi][bj] = B2; changed = True
        return changed

    def _diff_support(self) -> bool:
        changed = False
        for (a, b, t, param) in self.cs.diff:
            ai, aj = a; bi, bj = b
            A = self.dom[ai][aj]; B = self.dom[bi][bj]
            if not A or not B: 
                continue
            if t == "abs_eq":
                A2 = {x for x in A if any(abs(x - y) == param for y in B)}
                B2 = {y for y in B if any(abs(x - y) == param for x in A)}
            elif t == "abs_ge":
                A2 = {x for x in A if any(abs(x - y) >= param for y in B)}
                B2 = {y for y in B if any(abs(x - y) >= param for x in A)}
            else:
                A2 = {x for x in A if any(x - y == param for y in B)}
                B2 = {y for y in B if any(x - y == param for x in A)}
            if A2 != A:
                self.dom[ai][aj] = A2; changed = True
            if B2 != B:
                self.dom[bi][bj] = B2; changed = True
        return changed

    def _cage_support(self) -> bool:
        changed = False
        for (cells, op, target) in self.cs.cages:
            domains = [self.dom[i][j] for (i, j) in cells]
            if any(len(d) == 0 for d in domains):
                continue
            supports = [set() for _ in cells]
            def backtrack(k: int, acc_sum: int, acc_prod: int, chosen: List[int]):
                if k == len(cells):
                    if op == "sum" and acc_sum == target:
                        for idx, val in enumerate(chosen): supports[idx].add(val)
                    elif op == "prod" and acc_prod == target:
                        for idx, val in enumerate(chosen): supports[idx].add(val)
                    elif op == "diff" and len(chosen) == 2:
                        a, b = chosen
                        if abs(a - b) == target:
                            supports[0].add(a); supports[1].add(b)
                    elif op == "div" and len(chosen) == 2:
                        a, b = chosen
                        big, small = (a, b) if a >= b else (b, a)
                        if small != 0 and big % small == 0 and big // small == target:
                            supports[0].add(a); supports[1].add(b)
                    return
                for v in domains[k]:
                    if op == "sum" and acc_sum + v > target:
                        continue
                    if op == "prod" and acc_prod * v > target:
                        continue
                    backtrack(k+1, acc_sum + v, acc_prod * v, chosen + [v])
            backtrack(0, 0, 1, [])
            for idx, (i, j) in enumerate(cells):
                before = self.dom[i][j].copy()
                self.dom[i][j] = self.dom[i][j].intersection(supports[idx]) if supports[idx] else set()
                if self.dom[i][j] != before:
                    changed = True
        return changed

    def _sum_bound_propagate_on_cells(self, cells: List[Tuple[int,int]], target: int) -> bool:
        changed = False
        if not cells:
            return changed
        mins = []
        maxs = []
        for (i, j) in cells:
            if not self.dom[i][j]:
                return changed
            mins.append(min(self.dom[i][j]))
            maxs.append(max(self.dom[i][j]))
        total_min = sum(mins)
        total_max = sum(maxs)
        for idx, (i, j) in enumerate(cells):
            lo = target - (total_max - maxs[idx])
            hi = target - (total_min - mins[idx])
            allowed = {v for v in self.dom[i][j] if lo <= v <= hi}
            if allowed != self.dom[i][j]:
                self.dom[i][j] = allowed
                changed = True
        return changed

    def _path_sum_propagate(self) -> bool:
        changed = False
        for (path, target) in self.cs.path_sum:
            changed |= self._sum_bound_propagate_on_cells(path, target)
        return changed

    def _diag_sum_propagate(self) -> bool:
        changed = False
        for (which, op, target) in self.cs.diag:
            if op != "sum": 
                continue
            if which == "main":
                cells = [(i, i) for i in range(self.n)]
            else:
                cells = [(i, self.n-1-i) for i in range(self.n)]
            changed |= self._sum_bound_propagate_on_cells(cells, target)
        return changed

    def _rowcol_sum_propagate(self) -> bool:
        changed = False
        for (kind, idx, op, target) in self.cs.rowcol_agg:
            if op != "sum":
                continue
            if kind == "row":
                cells = [(idx, j) for j in range(self.n)]
            else:
                cells = [(i, idx) for i in range(self.n)]
            changed |= self._sum_bound_propagate_on_cells(cells, target)
        return changed

    def _propagate_all(self):
        while True:
            if self._timeout():
                break
            changed = False
            changed |= self._rowcol_propagate()
            changed |= self._ineq_propagate()
            changed |= self._diff_support()
            changed |= self._cage_support()
            changed |= self._path_sum_propagate()
            changed |= self._diag_sum_propagate()
            changed |= self._rowcol_sum_propagate()
            if not changed:
                break

    def _consistent_assignment_check(self, grid: List[List[int]]) -> bool:
        n = self.n
        for i in range(n):
            if len(set(grid[i])) != n: return False
        for j in range(n):
            col = [grid[i][j] for i in range(n)]
            if len(set(col)) != n: return False
        for (a, b, rel) in self.cs.ineq:
            va = grid[a[0]][a[1]]; vb = grid[b[0]][b[1]]
            if rel == ">" and not (va > vb): return False
            if rel == "<" and not (va < vb): return False
        for (a, b, t, param) in self.cs.diff:
            va = grid[a[0]][a[1]]; vb = grid[b[0]][b[1]]
            if t == "abs_eq" and abs(va - vb) != param: return False
            if t == "abs_ge" and abs(va - vb) < param: return False
            if t == "oriented" and (va - vb) != param: return False
        for (cells, op, target) in self.cs.cages:
            vals = [grid[i][j] for (i, j) in cells]
            if op == "sum":
                if sum(vals) != target: return False
            elif op == "prod":
                prod = 1
                for v in vals: prod *= v
                if prod != target: return False
            elif op == "diff":
                if len(vals) != 2: return False
                if abs(vals[0] - vals[1]) != target: return False
            else:
                if len(vals) != 2: return False
                a, b = vals
                big, small = (a, b) if a >= b else (b, a)
                if small == 0 or big % small != 0 or big // small != target: return False
        for (cell, p) in self.cs.parity.items():
            v = grid[cell[0]][cell[1]]
            if (v % 2 == 0) != (p == "even"): return False
        for (cell, m, r) in self.cs.mod:
            v = grid[cell[0]][cell[1]]
            if v % m != r: return False
        for (which, op, target) in self.cs.diag:
            if op != "sum": return False
            s = sum(grid[i][i] for i in range(n)) if which == "main" else sum(grid[i][n-1-i] for i in range(n))
            if s != target: return False
        for (kind, idx, op, target) in self.cs.rowcol_agg:
            if op != "sum": return False
            vals = grid[idx] if kind == "row" else [grid[i][idx] for i in range(n)]
            if sum(vals) != target: return False
        for (path, target) in self.cs.path_sum:
            if sum(grid[i][j] for (i, j) in path) != target: return False
        return True

    def _select_mrv(self) -> Optional[Tuple[int,int]]:
        best = None
        best_size = 10**9
        for i in range(self.n):
            for j in range(self.n):
                s = len(self.dom[i][j])
                if s > 1 and s < best_size:
                    best_size = s
                    best = (i, j)
        return best

    def _clone_domains(self):
        return [ [ self.dom[i][j].copy() for j in range(self.n) ] for i in range(self.n) ]

    def _solve(self) -> None:
        if self._timeout() or self.sol_count >= 2:
            return
        self._propagate_all()
        for i in range(self.n):
            for j in range(self.n):
                if not self.dom[i][j]:
                    return
        if all(len(self.dom[i][j]) == 1 for i in range(self.n) for j in range(self.n)):
            grid = [[next(iter(self.dom[i][j])) for j in range(self.n)] for i in range(self.n)]
            if self._consistent_assignment_check(grid):
                self.sol_count += 1
            return
        pos = self._select_mrv()
        if pos is None:
            return
        i, j = pos
        for v in sorted(list(self.dom[i][j])):
            if self._timeout() or self.sol_count >= 2:
                return
            saved = self._clone_domains()
            self.dom[i][j] = {v}
            self._solve()
            self.dom = saved

    def has_unique_solution(self) -> bool:
        self._solve()
        return self.sol_count == 1

# ---------------------------
# 线索构造与最小化
# ---------------------------

def _build_hints(sol: List[List[int]], hint_rate: float, min_hints: int) -> Dict[Tuple[int,int], int]:
    n = len(sol)
    hints: Dict[Tuple[int,int], int] = {}
    for i in range(n):
        for j in range(n):
            if random.random() < hint_rate:
                hints[(i, j)] = sol[i][j]
    cells = [(i, j) for i in range(n) for j in range(n)]
    random.shuffle(cells)
    k = 0
    while len(hints) < min_hints and k < len(cells):
        c = cells[k]; k += 1
        hints[c] = sol[c[0]][c[1]]
    return hints

def _hint_grid_text(n: int, hints: Dict[Tuple[int,int], int]) -> str:
    rows = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(str(hints[(i, j)]) if (i, j) in hints else "X")
        rows.append(" ".join(row))
    return "\\n".join(rows)

def _check_unique(n: int, cs: Constraints, hints: Dict[Tuple[int,int], int], limit: float) -> bool:
    solver = CPSolver(n, cs, hints, time_limit=limit)
    return solver.has_unique_solution()

def _greedy_minimize_hints(n: int, cs: Constraints, hints: Dict[Tuple[int,int], int], time_left: float) -> Dict[Tuple[int,int], int]:
    if time_left <= 0:
        return hints
    keys = list(hints.keys())
    random.shuffle(keys)
    start = time.time()
    per_check = 0.9
    for k in keys:
        if time.time() - start > time_left:
            break
        v = hints.pop(k)
        ok = _check_unique(n, cs, hints, limit=min(per_check, max(0.2, time_left - (time.time() - start))))
        if not ok:
            hints[k] = v
    return hints

# ---------------------------
# 题面生成 + 唯一性验证 + 自适应增强 + 线索最小化
# ---------------------------

def function_2(sol_grid: List[List[int]],
               ineq_density: float,
               hint_rate: float,
               rule_mode: str,
               cage_density: float,
               language_style: str) -> Dict[str, object]:
    assert _is_latin_square(sol_grid)
    n = len(sol_grid)
    explain_map = {
        "相邻不等式": "相邻不等式：只作用于水平或垂直相邻的两格，符号(>)表示左/上格更大，(<)表示右/下格更大。",
        "差值约束": "差值约束：两格差的绝对值等于/至少为某数，或某一格比另一格大k。若未写绝对值，则文本已指明方向。",
        "连锁区域(笼子)": "连锁区域(笼子)：同一笼子的若干格用指定运算(+、*、较大-较小、较大÷较小)得到目标数；‘-’与‘/’按较大与较小的数进行计算。",
        "奇偶约束": "奇偶约束：指明某格必须为奇数或偶数。",
        "取模约束": "取模约束：指明某格对某个模数取余的结果。",
        "对角线和": "对角线和：主对角线为左上到右下；副对角线为右上到左下。对角线上所有数字的和给定。",
        "行列聚合": "行列聚合：指定某行或某列的和（用于约束该行/列的整体取值）。",
        "路径和": "路径和：沿给定顺序的连通格子相加，结果固定。"
    }

    global_deadline = time.time() + 45.0
    base_ineq_density = min(max(ineq_density, 0.25), 0.8)
    base_cage_density = min(max(cage_density, 0.0), 0.5)
    base_hint_rate = min(max(hint_rate, 0.1), 0.6)
    style = language_style if language_style in ['symbolic','verbal','mixed'] else 'mixed'
    mode = rule_mode if rule_mode in ['auto','ineq_only','ineq_plus_diff','ineq_plus_cages','mixed'] else 'auto'

    attempt = 0
    while time.time() < global_deadline:
        attempt += 1
        ineq_d = min(0.9, base_ineq_density + 0.03 * attempt)
        cage_d = min(0.6, base_cage_density + 0.03 * attempt) if mode in ['auto','ineq_plus_cages','mixed'] else base_cage_density
        hint_r = min(0.7, base_hint_rate + 0.02 * attempt)

        cs = _compose_constraints_from_solution(sol_grid, ineq_d, cage_d, mode)
        min_hints = max(2, n)
        hints = _build_hints(sol_grid, hint_r, min_hints)

        per_try_limit = min(15.0, 6.0 + 0.6 * attempt)
        uniq = _check_unique(n, cs, hints, limit=per_try_limit)
        if not uniq:
            base_cage_density = min(0.6, base_cage_density + 0.02)
            base_ineq_density = min(0.9, base_ineq_density + 0.02)
            base_hint_rate = min(0.7, base_hint_rate + 0.01)
            continue

        time_left = max(0.0, global_deadline - time.time())
        hints = _greedy_minimize_hints(n, cs, hints, time_left=time_left)

        rules_text: List[str] = []
        families = cs.families_present()
        explain_list: List[str] = []
        for (a, b, rel) in cs.ineq:
            rules_text.append(_ineq_text(a, b, rel, style))
        for (a, b, t, param) in cs.diff:
            rules_text.append(_diff_text(a, b, t, param, style))
        for (cells, op, target) in cs.cages:
            rules_text.append(_cage_text(cells, op, target, style))
        for (cell, p) in cs.parity.items():
            rules_text.append(_parity_text(cell, p, style))
        for (cell, m, r) in cs.mod:
            rules_text.append(_mod_text(cell, m, r, style))
        for (which, op, target) in cs.diag:
            rules_text.append(_diag_text(which, op, target, style))
        for (kind, idx, op, target) in cs.rowcol_agg:
            rules_text.append(_rowcol_text(kind, idx, op, target, style))
        for (path, target) in cs.path_sum:
            rules_text.append(_path_text(path, target, style))

        for fam in families:
            if fam in explain_map:
                explain_list.append(explain_map[fam])

        rule_brief = "、".join(families) if families else "相邻不等式"
        hint_text = _hint_grid_text(n, hints)
        return {
            "rules_text": rules_text,
            "hint_grid_text": hint_text,
            "rule_brief": rule_brief,
            "rule_explain_text": explain_list
        }

    raise RuntimeError("Failed to generate a uniquely solvable puzzle within time budget.")