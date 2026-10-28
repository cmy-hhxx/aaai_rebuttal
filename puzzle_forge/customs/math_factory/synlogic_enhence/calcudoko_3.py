# calcudoko_5.py
# 自定义算子合集：KenKen 与跨层约束高级构造（供 YAML 引用）
from z3 import And, Or, Sum, Not
import random

def all_distinct(vals):
    """构造两两不等的合取约束。"""
    conj = []
    n = len(vals)
    for i in range(n):
        for j in range(i + 1, n):
            conj.append(vals[i] != vals[j])
    return And(conj) if conj else And(True)

def is_even(x):
    """在 1..n 值域语境下的偶数判定。"""
    return Or(x == 2, x == 4, x == 6)

def is_odd(x):
    """在 1..n 值域语境下的奇数判定。"""
    return Or(x == 1, x == 3, x == 5, x == 7)

def odd_sum_condition(x, y):
    """x 与 y 一奇一偶（和为奇数）。"""
    return Or(And(is_even(x), is_odd(y)), And(is_odd(x), is_even(y)))

def even_sum_condition(x, y):
    """x 与 y 同奇同偶（和为偶数）。"""
    return Or(And(is_even(x), is_even(y)), And(is_odd(x), is_odd(y)))

def parity_condition(x, y, parity_type):
    """根据 parity_type ('odd' 或 'even') 选择对应的 Z3 约束。"""
    if parity_type == 'odd':
        return odd_sum_condition(x, y)
    else:
        return even_sum_condition(x, y)

def make_row_pairs(n):
    """
    生成按行配对的笼子。
    - 若 n 为偶数，每行分为若干对 [(r,0),(r,1)], [(r,2),(r,3)], ...
    - 若 n 为奇数，最后三个列组成三格笼子 [(r,n-3),(r,n-2),(r,n-1)]
    返回形如 [ [[r,c],[r,c]], ... ] 或三格 [[r,c],[r,c],[r,c]] 的列表。
    """
    cages = []
    for r in range(n):
        c = 0
        while c + 1 < n:
            if c + 3 == n:  # 剩余 3 格，合成三格笼
                cages.append([[r, c], [r, c+1], [r, c+2]])
                c += 3
            else:
                cages.append([[r, c], [r, c+1]])
                c += 2
        if c == n - 1:  # 兜底（一般不触发）
            cages.append([[r, n-2], [r, n-1]])
    return cages

def make_col_pairs(n):
    """
    生成按列配对的笼子。
    - 若 n 为偶数，每列分为若干对 [(0,c),(1,c)], [(2,c),(3,c)], ...
    - 若 n 为奇数，最后三个行组成三格笼子 [(n-3,c),(n-2,c),(n-1,c)]
    返回形如 [ [[r,c],[r,c]], ... ] 或三格 [[r,c],[r,c],[r,c]] 的列表。
    """
    cages = []
    for c in range(n):
        r = 0
        while r + 1 < n:
            if r + 3 == n:
                cages.append([[r, c], [r+1, c], [r+2, c]])
                r += 3
            else:
                cages.append([[r, c], [r+1, c]])
                r += 2
        if r == n - 1:  # 兜底（一般不触发）
            cages.append([[n-2, c], [n-1, c]])
    return cages

def make_cages(n, pattern):
    """
    统一笼子生成入口。
    pattern:
      - 'row_pairs'：按行两两配对（奇数维尾部为三格）
      - 'col_pairs'：按列两两配对（奇数维尾部为三格）
    """
    if pattern == 'row_pairs':
        return make_row_pairs(n)
    elif pattern == 'col_pairs':
        return make_col_pairs(n)
    else:
        return make_row_pairs(n)

def choose_ops_and_targets(cages, grid_vals, prefer_div=True):
    """
    根据已求出的网格数值，为每个笼子选择稳定可满足的运算与目标。
    规则：
      - 两格笼子：
          * 若 prefer_div 且可整除，则用 'div'（比值为整数目标，且>1）；
          * 否则用 'sub'（绝对差）。
      - 三格及以上笼子：统一用 'add'（和）。
    返回 (ops_list, targets_list)。
    """
    ops = []
    targets = []
    for cells in cages:
        vals = [grid_vals[r][c] for r, c in cells]
        if len(vals) == 2:
            a, b = vals[0], vals[1]
            if prefer_div and min(a, b) > 0 and (a % b == 0 or b % a == 0) and max(a, b) // min(a, b) > 1:
                op = 'div'
                t = (a // b) if (a >= b and b != 0 and a % b == 0) else (b // a)
            else:
                op = 'sub'
                t = abs(a - b)
        else:
            op = 'add'
            t = sum(vals)
        ops.append(op)
        targets.append(t)
    return ops, targets

def apply_cage_constraints(symbol_dict, cages, ops, targets, row_keys=None, col_keys=None):
    """
    将笼子运算目标转为 Z3 约束并合取。
    - add: Sum(格值) == target
    - sub: 两值绝对差 == target -> Or(a-b==t, b-a==t)
    - div: 比值判定（避免除法/取模）：Or(a == t*b, b == t*a)
    参数：
      - symbol_dict: 以 (row_key, col_key) 为键的符号字典
      - cages: 形如 [ [[r,c],[r,c]], ... ] 的整数坐标列表
      - ops, targets: 与 cages 对应的运算与目标
      - row_keys, col_keys: 将整数 r,c 映射为字符串键的列表（例如 ['r0',...], ['c0',...]）
    """
    conj = []
    for i, cells in enumerate(cages):
        op = ops[i]
        t = targets[i]
        zvals = []
        for r, c in cells:
            if row_keys is not None and col_keys is not None:
                zvals.append(symbol_dict[(row_keys[r], col_keys[c])])
            else:
                zvals.append(symbol_dict[(r, c)])
        if op == 'add':
            conj.append(Sum(zvals) == t)
        elif op == 'sub':
            assert len(zvals) == 2, "sub 仅支持两格笼子"
            a, b = zvals[0], zvals[1]
            conj.append(Or(a - b == t, b - a == t))
        elif op == 'div':
            assert len(zvals) == 2, "div 仅支持两格笼子"
            a, b = zvals[0], zvals[1]
            conj.append(Or(a == t * b, b == t * a))
        else:
            conj.append(And(True))
    return And(conj)

def gen_perm(n):
    """生成 1..n 的随机排列。"""
    return random.sample(list(range(1, n + 1)), n)

def diag_mode_to_flags(mode):
    """
    将对角线模式字符串转为布尔标志字典。
      - 'none': {'main': False, 'anti': False}
      - 'main': {'main': True,  'anti': False}
      - 'anti': {'main': False, 'anti': True}
      - 'both': {'main': True,  'anti': True}
    """
    return {
        'main': mode in ('main', 'both'),
        'anti': mode in ('anti', 'both'),
    }

def make_checker_cells(n, origin):
    """
    生成棋盘格的奇偶分配坐标：
      - origin = 'black_odd' 表示 (i+j)%2==0 为奇数格；'white_odd' 表示偶数格为奇数。
    返回 (odd_cells, even_cells)，元素为 (r,c) 元组。
    """
    odd_cells = []
    even_cells = []
    for i in range(n):
        for j in range(n):
            black = ((i + j) % 2 == 0)
            is_odd_cell = (black and origin == 'black_odd') or ((not black) and origin == 'white_odd')
            if is_odd_cell:
                odd_cells.append((i, j))
            else:
                even_cells.append((i, j))
    return odd_cells, even_cells

def _find_cyclic_shift(a_row, b_row):
    """若存在 s 使得对所有 j 有 b[j] == a[(j+s) % n]，返回 s；否则返回 None。"""
    n = len(a_row)
    for s in range(n):
        ok = True
        for j in range(n):
            if b_row[j] != a_row[(j + s) % n]:
                ok = False
                break
        if ok:
            return s
    return None

def _build_value_map_from_cells(cells, grid_l1, grid_l2, n):
    """
    尝试按首轮解在若干坐标上抽取一个 1..n 的双射 f，使得 f(grid_l1[r][c]) = grid_l2[r][c]。
    返回 (mapping, used_cells)：
      - mapping: 长度 n+1 的列表，mapping[v] 给出 f(v)，下标 0 保留未用
      - used_cells: 实际可用且互不冲突的坐标子集
    """
    mapping = [None] * (n + 1)
    used_target = set()
    picked = []
    random.shuffle(cells)
    for (r, c) in cells:
        v1 = grid_l1[r][c]
        v2 = grid_l2[r][c]
        if mapping[v1] is None and v2 not in used_target:
            mapping[v1] = v2
            used_target.add(v2)
            picked.append((r, c))
    remaining_dom = [v for v in range(1, n+1) if mapping[v] is None]
    remaining_cod = [v for v in range(1, n+1) if v not in used_target]
    random.shuffle(remaining_cod)
    for i, v in enumerate(remaining_dom):
        mapping[v] = remaining_cod[i]
    return mapping, picked

def _parity(v):
    """整数奇偶：True 表示奇数，False 表示偶数。"""
    return (v % 2) == 1

def choose_cross_rule_pack(cross_mode, parity_type, grid_l1, grid_l2, checker_origin='black_odd'):
    """
    根据首轮解生成跨层约束包（用于最终锁定）。
    统一保障：生成的约束与首轮解一致，若给定模式与首轮解冲突，则降级到 sum_groups。
    返回字典（desc_text 不再包含“跨层约束：”前缀，由题面统一拼接）：
      {
        'mode': str,
        'parity_type': Optional[str],
        'odd_cells': Optional[list[(r,c)]],
        'even_cells': Optional[list[(r,c)]],
        'sum_cells': Optional[list[(r,c)]],
        'sum_targets': Optional[list[int]],
        'equal_cells': Optional[list[(r,c)]],
        'anti_cells': Optional[list[(r,c)]],
        'shift_rows': Optional[list[int]],
        'shift_vals': Optional[list[int]],
        'value_cells': Optional[list[(r,c)]],
        'value_map': Optional[list[int]],
        'desc_text': str
      }
    """
    n = len(grid_l1)
    pack = {'mode': cross_mode, 'parity_type': None, 'odd_cells': None, 'even_cells': None,
            'sum_cells': None, 'sum_targets': None, 'equal_cells': None,
            'anti_cells': None, 'shift_rows': None, 'shift_vals': None,
            'value_cells': None, 'value_map': None, 'desc_text': ''}

    def _to_sum_groups_desc(cells, targets):
        coords_txt = "[" + ", ".join([f"({r},{c})" for (r, c) in cells]) + "]"
        targets_txt = "[" + ", ".join([str(t) for t in targets]) + "]"
        return f"以下坐标两层和值锁定为给定目标；坐标列表为{coords_txt}；对应目标列表为{targets_txt}"

    def _build_sum_groups_fallback():
        cells = []
        for r in range(n):
            k = 1 if n <= 5 else random.choice([1, 2])
            cols = random.sample(list(range(n)), k)
            for c in cols:
                cells.append((r, c))
        cells = list(dict.fromkeys(cells))
        random.shuffle(cells)
        targets = [grid_l1[r][c] + grid_l2[r][c] for (r, c) in cells]
        pack['mode'] = 'sum_groups'
        pack['sum_cells'] = cells
        pack['sum_targets'] = targets
        pack['desc_text'] = _to_sum_groups_desc(cells, targets)

    if cross_mode == 'parity_global':
        parities = [ _parity(grid_l1[i][j] + grid_l2[i][j]) for i in range(n) for j in range(n) ]
        if all(parities) or not any(parities):
            pt = 'odd' if all(parities) else 'even'
            pack['parity_type'] = pt
            pack['desc_text'] = f"同一位置两层值之和为{'奇数' if pt=='odd' else '偶数'}"
        else:
            _build_sum_groups_fallback()

    elif cross_mode == 'checkerboard':
        par = [[_parity(grid_l1[i][j] + grid_l2[i][j]) for j in range(n)] for i in range(n)]
        ok_black_odd = True
        for i in range(n):
            for j in range(n):
                if par[i][j] != (((i + j) % 2) == 0):
                    ok_black_odd = False
                    break
            if not ok_black_odd:
                break
        ok_white_odd = True
        for i in range(n):
            for j in range(n):
                if par[i][j] != (((i + j) % 2) == 1):
                    ok_white_odd = False
                    break
            if not ok_white_odd:
                break
        if ok_black_odd or ok_white_odd:
            origin = 'black_odd' if ok_black_odd else 'white_odd'
            odd_cells, even_cells = make_checker_cells(n, origin)
            pack['odd_cells'] = odd_cells
            pack['even_cells'] = even_cells
            pack['desc_text'] = f"棋盘奇偶模式（(r+c)%2==0 的格为{'奇数' if origin=='black_odd' else '偶数'}，另一色为{'偶数' if origin=='black_odd' else '奇数'}）"
        else:
            _build_sum_groups_fallback()

    elif cross_mode == 'sum_groups':
        cells = []
        for r in range(n):
            k = 1 if n <= 5 else random.choice([1, 2])
            cols = random.sample(list(range(n)), k)
            for c in cols:
                cells.append((r, c))
        cells = list(dict.fromkeys(cells))
        random.shuffle(cells)
        targets = [grid_l1[r][c] + grid_l2[r][c] for (r, c) in cells]
        pack['sum_cells'] = cells
        pack['sum_targets'] = targets
        pack['desc_text'] = _to_sum_groups_desc(cells, targets)

    elif cross_mode == 'equal_pairs':
        cells = [(r, c) for r in range(n) for c in range(n) if grid_l1[r][c] == grid_l2[r][c]]
        random.shuffle(cells)
        if not cells:
            _build_sum_groups_fallback()
        else:
            keep = min(len(cells), n + random.randint(0, n // 2))
            cells = cells[:keep]
            pack['equal_cells'] = cells
            coords_txt = "[" + ", ".join([f"({r},{c})" for (r, c) in cells]) + "]"
            pack['desc_text'] = f"以下坐标两层数值相等；坐标列表为{coords_txt}"

    elif cross_mode == 'anti_match_cells':
        candidates = [(r, c) for r in range(n) for c in range(n) if grid_l1[r][c] != grid_l2[r][c]]
        random.shuffle(candidates)
        k = min(len(candidates), n + random.randint(0, n // 2))
        cells = candidates[:k]
        if not cells:
            _build_sum_groups_fallback()
        else:
            pack['anti_cells'] = cells
            coords_txt = "[" + ", ".join([f"({r},{c})" for (r, c) in cells]) + "]"
            pack['desc_text'] = f"以下坐标两层数值不相等；坐标列表为{coords_txt}"

    elif cross_mode == 'row_shift':
        rows = []
        shifts = []
        row_ids = list(range(n))
        random.shuffle(row_ids)
        for i in row_ids:
            s = _find_cyclic_shift(grid_l1[i], grid_l2[i])
            if s is not None:
                rows.append(i)
                shifts.append(s)
        if not rows:
            _build_sum_groups_fallback()
        else:
            keep = random.randint(1, min(len(rows), max(1, n // 2)))
            rows = rows[:keep]
            shifts = shifts[:keep]
            pack['shift_rows'] = rows
            pack['shift_vals'] = shifts
            pairs_txt = "[" + ", ".join([f"(r={rows[idx]}, shift={shifts[idx]})" for idx in range(len(rows))]) + "]"
            pack['desc_text'] = f"给定若干行上，层2为层1按列循环位移；行与位移列表为{pairs_txt}"

    elif cross_mode == 'value_map':
        all_cells = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(all_cells)
        mapping, cells = _build_value_map_from_cells(all_cells[:2*n], grid_l1, grid_l2, n)
        if not cells:
            _build_sum_groups_fallback()
        else:
            pack['value_map'] = mapping
            k = min(len(cells), n + random.randint(0, n // 2))
            cells = cells[:k]
            pack['value_cells'] = cells
            coords_txt = "[" + ", ".join([f"({r},{c})" for (r, c) in cells]) + "]"
            map_txt = "[" + ", ".join([f"{i}->{mapping[i]}" for i in range(1, n+1)]) + "]"
            pack['desc_text'] = f"在若干坐标上满足层2等于映射 f 作用于层1的值；坐标列表为{coords_txt}；映射表为{map_txt}"

    else:
        _build_sum_groups_fallback()

    return pack

def apply_cross_constraints(L1_dict, L2_dict, cross_pack, row_keys, col_keys):
    """
    将跨层约束包转为 Z3 合取。
    支持模式：
      - parity_global: parity_condition(L1[i,j], L2[i,j], parity_type)
      - checkerboard: odd_sum_condition 于 odd_cells，even_sum_condition 于 even_cells
      - sum_groups: L1[i,j] + L2[i,j] == target
      - equal_pairs: L1[i,j] == L2[i,j]
      - anti_match_cells: L1[i,j] != L2[i,j]
      - row_shift: 对若干行 i，∀j L2[i,j] == L1[i,(j+s) mod n]
      - value_map: 对若干坐标 (i,j)，存在双射 f 使 L2[i,j] == f(L1[i,j])
    """
    conj = []
    n_rows = len(row_keys)
    n_cols = len(col_keys)

    def cell_val(dict_obj, r, c):
        return dict_obj[(row_keys[r], col_keys[c])]

    mode = cross_pack.get('mode')
    if mode == 'parity_global':
        pt = cross_pack.get('parity_type', 'even')
        for i in range(n_rows):
            for j in range(n_cols):
                conj.append(parity_condition(cell_val(L1_dict, i, j), cell_val(L2_dict, i, j), pt))

    elif mode == 'checkerboard':
        odd_cells = cross_pack.get('odd_cells', [])
        even_cells = cross_pack.get('even_cells', [])
        for (i, j) in odd_cells:
            conj.append(odd_sum_condition(cell_val(L1_dict, i, j), cell_val(L2_dict, i, j)))
        for (i, j) in even_cells:
            conj.append(even_sum_condition(cell_val(L1_dict, i, j), cell_val(L2_dict, i, j)))

    elif mode == 'sum_groups':
        cells = cross_pack.get('sum_cells', [])
        targets = cross_pack.get('sum_targets', [])
        for idx, (i, j) in enumerate(cells):
            t = targets[idx]
            conj.append(cell_val(L1_dict, i, j) + cell_val(L2_dict, i, j) == t)

    elif mode == 'equal_pairs':
        cells = cross_pack.get('equal_cells', [])
        for (i, j) in cells:
            conj.append(cell_val(L1_dict, i, j) == cell_val(L2_dict, i, j))

    elif mode == 'anti_match_cells':
        cells = cross_pack.get('anti_cells', [])
        for (i, j) in cells:
            conj.append(cell_val(L1_dict, i, j) != cell_val(L2_dict, i, j))

    elif mode == 'row_shift':
        rows = cross_pack.get('shift_rows', [])
        shifts = cross_pack.get('shift_vals', [])
        n = n_cols
        for idx, i in enumerate(rows):
            s = shifts[idx] % n
            for j in range(n):
                conj.append(cell_val(L2_dict, i, j) == cell_val(L1_dict, i, (j + s) % n))

    elif mode == 'value_map':
        cells = cross_pack.get('value_cells', [])
        mapping = cross_pack.get('value_map', [])
        for (i, j) in cells:
            disj = []
            for k in range(1, len(mapping)):
                disj.append(And(cell_val(L1_dict, i, j) == k, cell_val(L2_dict, i, j) == mapping[k]))
            conj.append(Or(disj))

    else:
        conj.append(And(True))

    return And(conj)

# ====== 新增：示例答案文本、给定格挑选与锁定、文本格式化 ======

def make_example_answer_text(n):
    """
    生成与 n×n 一致的示例答案文本，如：(([1,2],[2,1]), ([2,1],[1,2]))。
    采用基础拉丁构造：G1[i][j] = (i+j)%n+1，G2 为列循环位移 1 的变体。
    """
    g1 = [[(i + j) % n + 1 for j in range(n)] for i in range(n)]
    g2 = [[(i + j + 1) % n + 1 for j in range(n)] for i in range(n)]
    return "(" + str(g1) + ", " + str(g2) + ")"

def choose_givens(grid_vals):
    """
    基于首轮解选择若干给定格（随规模自适应）：
      - n <= 4: 选 2 格
      - n == 5 或 6: 选 3 格
      - n >= 7: 选 4 格
    返回 (cells, vals)，cells 为 [[r,c], ...]，vals 为对应值列表。
    """
    n = len(grid_vals)
    if n <= 4:
        k = 2
    elif n <= 6:
        k = 3
    else:
        k = 4
    all_cells = [(r, c) for r in range(n) for c in range(n)]
    random.shuffle(all_cells)
    picked = all_cells[:k]
    cells = [[r, c] for (r, c) in picked]
    vals = [grid_vals[r][c] for (r, c) in picked]
    return cells, vals

def apply_given_cells(symbol_dict, cells, vals, row_keys, col_keys):
    """
    将给定格 (cells, vals) 转为 Z3 合取：∀t, L[row_keys[r], col_keys[c]] == v
    cells 为 [[r,c], ...]，vals 为对应值列表。
    """
    conj = []
    for idx, rc in enumerate(cells):
        r, c = rc[0], rc[1]
        v = vals[idx]
        conj.append(symbol_dict[(row_keys[r], col_keys[c])] == v)
    return And(conj) if conj else And(True)

def format_givens_as_text(cells, vals):
    """
    将给定格渲染为文本：形如 [((r,c),v), ...]
    """
    items = [f"(({rc[0]},{rc[1]}),{vals[idx]})" for idx, rc in enumerate(cells)]
    return "[" + ", ".join(items) + "]"