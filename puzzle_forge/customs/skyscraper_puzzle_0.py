# skyscraper_puzzle_0.py
# 改进版（高质量题面）：
# - 1 基索引（R1..Rn, C1..Cn）
# - 引言模板在 Python 侧完成格式化（避免未替换占位符）
# - 聚合约束改为子集和，提升信息量、避免冗余
# - 条件分支规则基于子集和，保证一致性与可满足性
# - 唯一性：按需固定少量格子确保唯一解，并在求解器中验证

import random
from z3 import Int, Solver, And, Or, Distinct, If, Sum, sat

def function_1(seq, expected):
    """构造“可见摩天楼数 == expected”的Z3约束。"""
    assert len(seq) >= 1, "Visibility sequence must be non-empty."
    terms = [1]  # 第一个总可见
    for i in range(1, len(seq)):
        prev = seq[:i]
        cond = And(*[seq[i] > p for p in prev]) if prev else True
        terms.append(If(cond, 1, 0))
    return Sum(terms) == expected

def function_2(model, row_keys, col_keys, cell_dict):
    """将Z3模型转为Python二维列表。"""
    n = len(row_keys)
    grid = []
    for i in range(n):
        row_vals = []
        for j in range(n):
            v = model.evaluate(cell_dict[(row_keys[i], col_keys[j])], model_completion=True)
            try:
                row_vals.append(v.as_long())
            except Exception:
                row_vals.append(int(str(v)))
        grid.append(row_vals)
    return grid

def generate_solution_grid(n):
    """生成一个随机拉丁方网格（作为可行解），元素取值为 1..n。"""
    base = [[(i + j) % n + 1 for j in range(n)] for i in range(n)]
    # 随机行列置换
    row_perm = list(range(n))
    col_perm = list(range(n))
    random.shuffle(row_perm)
    random.shuffle(col_perm)
    grid = [[base[row_perm[i]][col_perm[j]] for j in range(n)] for i in range(n)]
    return grid

def _count_visible(seq):
    """纯Python统计可见摩天楼数量。"""
    vis = 0
    max_seen = 0
    for h in seq:
        if h > max_seen:
            vis += 1
            max_seen = h
    return vis

def compute_views(grid):
    """根据解网格计算四个方向的视野提示。"""
    n = len(grid)
    left = [_count_visible(row) for row in grid]
    right = [_count_visible(list(reversed(row))) for row in grid]
    top = [_count_visible([grid[i][j] for i in range(n)]) for j in range(n)]
    bottom = [_count_visible(list(reversed([grid[i][j] for i in range(n)]))) for j in range(n)]
    return {'top': top, 'bottom': bottom, 'left': left, 'right': right}

def gen_relational_constraints(n, grid, count, op_pool):
    """
    生成单元格间的关系约束（与解一致）。
    每条约束：{'i': r1, 'j': c1, 'k': r2, 'l': c2, 'op': 'gt'/'lt'/'eq'/'neq'/'ge'/'le'}
    索引 i,j,k,l 为 0..n-1（内部索引，与 1 基标签分离）。
    """
    ops_valid = set(op_pool)
    constraints = []
    used = set()
    all_positions = [(i, j) for i in range(n) for j in range(n)]

    def candidate_ops(a, b):
        res = []
        if a > b: res += ['gt', 'ge', 'neq']
        if a < b: res += ['lt', 'le', 'neq']
        if a == b: res += ['eq', 'ge', 'le']
        return [op for op in res if op in ops_valid]

    tries = 0
    while len(constraints) < count and tries < n*n*6:
        (i, j) = random.choice(all_positions)
        (k, l) = random.choice(all_positions)
        tries += 1
        if i == k and j == l:
            continue
        a, b = grid[i][j], grid[k][l]
        c_ops = candidate_ops(a, b)
        if not c_ops:
            continue
        op = random.choice(c_ops)
        key = (i, j, k, l, op)
        if key in used:
            continue
        used.add(key)
        constraints.append({'i': i, 'j': j, 'k': k, 'l': l, 'op': op})
    return constraints

def render_rel_desc(row_keys, col_keys, rel_constraints):
    """渲染单元格关系约束为自然语言（使用 1 基标签）。"""
    op_to_templates = {
        'gt': ["{X} 的高度大于 {Y}", "{Y} 的高度小于 {X}"],
        'ge': ["{X} 的高度不小于 {Y}", "{Y} 的高度不大于 {X}"],
        'lt': ["{X} 的高度小于 {Y}", "{Y} 的高度大于 {X}"],
        'le': ["{X} 的高度不大于 {Y}", "{Y} 的高度不小于 {X}"],
        'eq': ["{X} 的高度等于 {Y}", "{Y} 的高度等于 {X}"],
        'neq': ["{X} 的高度不等于 {Y}", "{Y} 的高度不等于 {X}"],
    }
    lines = []
    for item in rel_constraints:
        # 1 基标签映射：i,j 是 0 基索引；row_keys[i] = R{i+1}, col_keys[j] = C{j+1}
        X = f"{row_keys[item['i']]}-{col_keys[item['j']]}"
        Y = f"{row_keys[item['k']]}-{col_keys[item['l']]}"
        templates = op_to_templates.get(item['op'], ["{X} 与 {Y} 满足关系"])
        tpl = random.choice(templates)
        lines.append(tpl.replace("{X}", X).replace("{Y}", Y))
    return "\n  - " + "\n  - ".join(lines) if lines else "\n  - （无）"

def gen_aux_constraints(n, grid, count, aux_pool):
    """
    生成子集和的聚合约束，提升信息量，避免冗余。
    类型：
      - row_part_diff_eq: Sum(row i, subset A) - Sum(row k, subset B) == const
      - col_part_diff_eq: Sum(col j, subset A) - Sum(col l, subset B) == const
      - row_col_part_comp: Sum(row i, subset A) op Sum(col l, subset B)
    其中 subset A/B 是列或行索引的子集（长度 1..n-1）。
    """
    constraints = []
    used = set()
    rows = list(range(n))
    cols = list(range(n))

    def sum_row_subset(i, subset_cols): return sum(grid[i][c] for c in subset_cols)
    def sum_col_subset(j, subset_rows): return sum(grid[r][j] for r in subset_rows)

    def pick_subset(full, min_len=1, max_len=None):
        if max_len is None: max_len = len(full) - 1
        L = random.randint(min_len, max_len)
        return sorted(random.sample(full, L))

    def pick_op(a, b):
        cand = []
        if a > b: cand += ['gt', 'ge']
        if a < b: cand += ['lt', 'le']
        if a == b: cand += ['eq', 'ge', 'le']
        return cand or ['eq']

    tries = 0
    while len(constraints) < count and tries < n*n*8:
        tries += 1
        t = random.choice(aux_pool)

        if t == 'row_part_diff_eq':
            i, k = random.sample(rows, 2)
            A = pick_subset(cols, 1, n-1)
            B = pick_subset(cols, 1, n-1)
            const = sum_row_subset(i, A) - sum_row_subset(k, B)
            key = ('row_part_diff_eq', i, tuple(A), k, tuple(B), const)
            if key in used: continue
            used.add(key)
            constraints.append({'type':'row_part_diff_eq','i':i,'A':A,'k':k,'B':B,'const':const})

        elif t == 'col_part_diff_eq':
            j, l = random.sample(cols, 2)
            A = pick_subset(rows, 1, n-1)
            B = pick_subset(rows, 1, n-1)
            const = sum_col_subset(j, A) - sum_col_subset(l, B)
            key = ('col_part_diff_eq', j, tuple(A), l, tuple(B), const)
            if key in used: continue
            used.add(key)
            constraints.append({'type':'col_part_diff_eq','j':j,'A':A,'l':l,'B':B,'const':const})

        elif t == 'row_col_part_comp':
            i = random.choice(rows)
            l = random.choice(cols)
            A = pick_subset(cols, 1, n-1)
            B = pick_subset(rows, 1, n-1)
            a = sum_row_subset(i, A)
            b = sum_col_subset(l, B)
            op = random.choice(pick_op(a, b))
            key = ('row_col_part_comp', i, tuple(A), l, tuple(B), op)
            if key in used: continue
            used.add(key)
            constraints.append({'type':'row_col_part_comp','i':i,'A':A,'l':l,'B':B,'op':op})

    return constraints

def render_aux_desc(row_keys, col_keys, aux_constraints):
    """渲染子集和聚合约束为自然语言描述（1 基标签）。"""
    def cols_to_labels(A): return ','.join(col_keys[c] for c in A)
    def rows_to_labels(A): return ','.join(row_keys[r] for r in A)
    op_txt = {'gt':'大于','ge':'不小于','lt':'小于','le':'不大于','eq':'等于'}
    lines = []
    for item in aux_constraints:
        if item['type'] == 'row_part_diff_eq':
            X = f"{row_keys[item['i']]} 行在列子集 [{cols_to_labels(item['A'])}] 的总和"
            Y = f"{row_keys[item['k']]} 行在列子集 [{cols_to_labels(item['B'])}] 的总和"
            lines.append(f"{X} 与 {Y} 的差等于 {item['const']}")
        elif item['type'] == 'col_part_diff_eq':
            X = f"{col_keys[item['j']]} 列在行子集 [{rows_to_labels(item['A'])}] 的总和"
            Y = f"{col_keys[item['l']]} 列在行子集 [{rows_to_labels(item['B'])}] 的总和"
            lines.append(f"{X} 与 {Y} 的差等于 {item['const']}")
        elif item['type'] == 'row_col_part_comp':
            X = f"{row_keys[item['i']]} 行在列子集 [{cols_to_labels(item['A'])}] 的总和"
            Y = f"{col_keys[item['l']]} 列在行子集 [{rows_to_labels(item['B'])}] 的总和"
            lines.append(f"{X} {op_txt.get(item['op'],'等于')} {Y}")
    return "\n  - " + "\n  - ".join(lines) if lines else "\n  - （无）"

def gen_branch_rule(n, grid):
    """
    条件分支规则（子集和）：
      选择一条行 i 的列子集 A，和一条列 l 的行子集 B。
      diff = |Sum(row i, A) - Sum(col l, B)|
      若 Sum(row i, A) > Sum(col l, B)，则差等于 diff；否则相反分支差也等于 diff。
    返回：
      {'i':行索引,'A':列子集,'l':列索引,'B':行子集,'diff':非负整数}
    """
    cols = list(range(n))
    rows = list(range(n))
    def pick_subset(full, min_len=1, max_len=None):
        if max_len is None: max_len = len(full) - 1
        L = random.randint(min_len, max_len)
        return sorted(random.sample(full, L))
    i = random.choice(rows)
    l = random.choice(cols)
    A = pick_subset(cols, 1, n-1)
    B = pick_subset(rows, 1, n-1)
    sum_row = sum(grid[i][c] for c in A)
    sum_col = sum(grid[r][l] for r in B)
    diff = abs(sum_row - sum_col)
    return {'i':i,'A':A,'l':l,'B':B,'diff':diff}

def render_branch_desc(row_keys, col_keys, branch_rule):
    """渲染分支规则的自然语言描述（1 基标签）。"""
    A_lbl = ','.join(col_keys[c] for c in branch_rule['A'])
    B_lbl = ','.join(row_keys[r] for r in branch_rule['B'])
    L = f"{row_keys[branch_rule['i']]} 行在列子集 [{A_lbl}] 的总和"
    R = f"{col_keys[branch_rule['l']]} 列在行子集 [{B_lbl}] 的总和"
    d = branch_rule['diff']
    return f"若 {L} 大于 {R}，则两者总和之差等于 {d}；否则，{R} 大于 {L}，且两者总和之差也等于 {d}。"

def build_branch_expr(row_keys, col_keys, cell_dict, branch_rule, n):
    """
    Z3 If 表达式（子集和）：
      If(Sum(row i, A) > Sum(col l, B),
         Sum(row i, A) - Sum(col l, B) == d,
         Sum(col l, B) - Sum(row i, A) == d)
    """
    i = branch_rule['i']; l = branch_rule['l']; A = branch_rule['A']; B = branch_rule['B']; d = branch_rule['diff']
    lhs = Sum([cell_dict[(row_keys[i], col_keys[c])] for c in A])
    rhs = Sum([cell_dict[(row_keys[r], col_keys[l])] for r in B])
    return If(lhs > rhs, lhs - rhs == d, rhs - lhs == d)

def build_aggregate_z3(row_keys, col_keys, cell_dict, aux_constraints, n):
    """
    构造子集和聚合约束的合取表达式（And([...])）。
    """
    conj = []
    for item in aux_constraints:
        t = item['type']
        if t == 'row_part_diff_eq':
            i, k, A, B, const = item['i'], item['k'], item['A'], item['B'], item['const']
            lhs = Sum([cell_dict[(row_keys[i], col_keys[c])] for c in A])
            rhs = Sum([cell_dict[(row_keys[k], col_keys[c])] for c in B])
            conj.append(lhs - rhs == const)
        elif t == 'col_part_diff_eq':
            j, l, A, B, const = item['j'], item['l'], item['A'], item['B'], item['const']
            lhs = Sum([cell_dict[(row_keys[r], col_keys[j])] for r in A])
            rhs = Sum([cell_dict[(row_keys[r], col_keys[l])] for r in B])
            conj.append(lhs - rhs == const)
        elif t == 'row_col_part_comp':
            i, l, A, B, op = item['i'], item['l'], item['A'], item['B'], item['op']
            lhs = Sum([cell_dict[(row_keys[i], col_keys[c])] for c in A])
            rhs = Sum([cell_dict[(row_keys[r], col_keys[l])] for r in B])
            if op == 'gt': conj.append(lhs > rhs)
            elif op == 'ge': conj.append(lhs >= rhs)
            elif op == 'lt': conj.append(lhs < rhs)
            elif op == 'le': conj.append(lhs <= rhs)
            elif op == 'eq': conj.append(lhs == rhs)
    if not conj:
        return And(True)
    return And(conj)

def _apply_rel_constraints(S, cell, rel_constraints):
    """添加单元格关系约束到求解器（内部索引 0..n-1）。"""
    for item in rel_constraints:
        i, j, k, l, op = item['i'], item['j'], item['k'], item['l'], item['op']
        a = cell[i][j]
        b = cell[k][l]
        if op == 'gt':
            S.add(a > b)
        elif op == 'ge':
            S.add(a >= b)
        elif op == 'lt':
            S.add(a < b)
        elif op == 'le':
            S.add(a <= b)
        elif op == 'eq':
            S.add(a == b)
        elif op == 'neq':
            S.add(a != b)

def _build_solver(n, views, fixed_positions, fixed_values, rel_constraints=None, aux_constraints=None, branch_rule=None):
    """构建Z3求解器：摩天楼规则 + 视野 + 关系 + 子集和聚合 + 分支 + 固定。"""
    cell = [[Int(f"X_{i}_{j}") for j in range(n)] for i in range(n)]
    S = Solver()

    # 值域与行列唯一
    for i in range(n):
        for j in range(n):
            S.add(cell[i][j] >= 1, cell[i][j] <= n)
    for i in range(n):
        S.add(Distinct(cell[i]))
    for j in range(n):
        S.add(Distinct([cell[i][j] for i in range(n)]))

    # 视野约束
    left, right, top, bottom = views['left'], views['right'], views['top'], views['bottom']
    for i in range(n):
        S.add(function_1(cell[i], left[i]))
        S.add(function_1(list(reversed(cell[i])), right[i]))
    for j in range(n):
        col = [cell[i][j] for i in range(n)]
        S.add(function_1(col, top[j]))
        S.add(function_1(list(reversed(col)), bottom[j]))

    # 单元格关系约束
    if rel_constraints:
        _apply_rel_constraints(S, cell, rel_constraints)

    # 子集和聚合约束（求解器端）：通过同名构造函数生成并一次性加入
    if aux_constraints:
        agg = build_aggregate_z3([f"R{i+1}" for i in range(n)],
                                 [f"C{j+1}" for j in range(n)],
                                 {(f"R{i+1}", f"C{j+1}"): cell[i][j] for i in range(n) for j in range(n)},
                                 aux_constraints, n)
        S.add(agg)

    # 分支规则
    if branch_rule:
        branch = build_branch_expr([f"R{i+1}" for i in range(n)],
                                   [f"C{j+1}" for j in range(n)],
                                   {(f"R{i+1}", f"C{j+1}"): cell[i][j] for i in range(n) for j in range(n)},
                                   branch_rule, n)
        S.add(branch)

    # 固定格子
    for (i, j), val in zip(fixed_positions, fixed_values):
        S.add(cell[i][j] == val)

    return S, cell

def _find_one_solution(n, views, fixed_positions, fixed_values, rel_constraints=None, aux_constraints=None, branch_rule=None):
    """寻找一个可行解并返回。"""
    S, cell = _build_solver(n, views, fixed_positions, fixed_values, rel_constraints, aux_constraints, branch_rule)
    if S.check() != sat:
        return None
    m = S.model()
    sol = [[m.evaluate(cell[i][j]).as_long() for j in range(n)] for i in range(n)]
    return sol

def _has_second_solution(n, views, fixed_positions, fixed_values, first_solution, rel_constraints=None, aux_constraints=None, branch_rule=None):
    """判断是否存在第二个不同的解。"""
    S, cell = _build_solver(n, views, fixed_positions, fixed_values, rel_constraints, aux_constraints, branch_rule)
    if S.check() != sat:
        return False
    diff_clause = []
    for i in range(n):
        for j in range(n):
            diff_clause.append(cell[i][j] != first_solution[i][j])
    S.add(Or(diff_clause))
    return S.check() == sat

def select_fixed_positions_for_uniqueness(n, grid, left_view, right_view, top_view, bottom_view, cap, rel_constraints=None, aux_constraints=None, branch_rule=None):
    """
    在视野+关系+子集和聚合+分支条件下，若存在多解，则逐步揭示少量格子，确保唯一解。
    """
    views = {'left': left_view, 'right': right_view, 'top': top_view, 'bottom': bottom_view}
    first = _find_one_solution(n, views, [], [], rel_constraints, aux_constraints, branch_rule)
    if first is not None and not _has_second_solution(n, views, [], [], first, rel_constraints, aux_constraints, branch_rule):
        return []
    all_positions = [(i, j) for i in range(n) for j in range(n)]
    random.shuffle(all_positions)
    fixed_pos = []
    fixed_vals = []
    target_cap = max(1, cap)
    for k in range(target_cap):
        (i, j) = all_positions[k % len(all_positions)]
        fixed_pos.append((i, j))
        fixed_vals.append(grid[i][j])
        first = _find_one_solution(n, views, fixed_pos, fixed_vals, rel_constraints, aux_constraints, branch_rule)
        if first is None:
            continue
        if not _has_second_solution(n, views, fixed_pos, fixed_vals, first, rel_constraints, aux_constraints, branch_rule):
            return fixed_pos
    for (i, j) in all_positions[target_cap:]:
        fixed_pos.append((i, j))
        fixed_vals.append(grid[i][j])
        first = _find_one_solution(n, views, fixed_pos, fixed_vals, rel_constraints, aux_constraints, branch_rule)
        if first is None:
            continue
        if not _has_second_solution(n, views, fixed_pos, fixed_vals, first, rel_constraints, aux_constraints, branch_rule):
            return fixed_pos
    return fixed_pos

def pick_intro_resolved(templates, grid_size):
    """选择并格式化引言模板，避免未替换占位符残留。"""
    tpl = random.choice(templates)
    # 模板中可能包含 {grid_size} 占位符，这里完成格式化
    try:
        return tpl.format(grid_size=grid_size)
    except Exception:
        return tpl