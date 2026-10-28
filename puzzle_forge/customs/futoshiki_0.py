# futoshiki_0.py
# 修正与增强：
# - 约束一律从解导出，确保与提示相容（避免“平方((1,1)) ≤ 平方((2,1))”与(1,1)=3,(2,1)=1矛盾；避免“三角数((2,2)) = 三角数((2,1)) - 5”不可满足）
# - 差值K始终为正整数；ADD用于TR = TL + K（当TR>TL），SUB用于TR = TL - K（当TR<TL），不会生成“+ -K”
# - 维持唯一解校验：若不唯一，优先增加提示，其次增加相容关系约束，直到唯一或重采样
import random
from typing import List, Tuple
from z3 import Int, Solver, And, Distinct, Or, Sum, sat

# 全局场景缓存
_SCENARIO = {
    "n": None,
    "solution": None,
    "given": None,
    "con_left": None,
    "con_right": None,
    "con_op": None,
    "con_k": None,
    "con_layer": None,
    "affine_params": None,
    "clue_pos": None,
    "clue_val": None,
    "diag_type": None,
    "diag_sum": None
}

def _latin_square(n: int) -> List[List[int]]:
    base = [[(i + j) % n + 1 for j in range(n)] for i in range(n)]
    rows_perm = list(range(n))
    cols_perm = list(range(n))
    random.shuffle(rows_perm)
    random.shuffle(cols_perm)
    grid = [[base[rows_perm[i]][cols_perm[j]] for j in range(n)] for i in range(n)]
    digits_perm = list(range(1, n + 1))
    random.shuffle(digits_perm)
    mapping = {d: digits_perm[d - 1] for d in range(1, n + 1)}
    grid = [[mapping[grid[i][j]] for j in range(n)] for i in range(n)]
    return grid

def _adjacent_pairs(n: int) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    pairs = []
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if j < n:
                pairs.append(((i, j), (i, j + 1)))
            if i < n:
                pairs.append(((i, j), (i + 1, j)))
    return pairs

def compose_rel(L, R, op: str, k: int, layer: str, affine_params: List[int]):
    """
    复合层与操作符封装为Z3表达式：
      层 layer ∈ {'raw','sq','tri','aff'}：
        raw: TL=L, TR=R
        sq:  TL=L^2, TR=R^2
        tri: TL=T(L)=L*(L+1)/2, TR=T(R)=R*(R+1)/2
        aff: TL=a*L+b, TR=a*R+b（a,b来自affine_params）
      操作 op ∈ {'gt','ge','lt','le','add','sub'}：
        比较：TL > / ≥ / < / ≤ TR
        加减：TR = TL + k 或 TR = TL - k（k为正整数）
    """
    a, b = affine_params[0], affine_params[1]
    if layer == 'raw':
        TL, TR = L, R
    elif layer == 'sq':
        TL, TR = L * L, R * R
    elif layer == 'tri':
        TL, TR = (L * (L + 1)) / 2, (R * (R + 1)) / 2
    elif layer == 'aff':
        TL, TR = a * L + b, a * R + b
    else:
        TL, TR = L, R

    if op == 'gt':
        return TL > TR
    elif op == 'ge':
        return TL >= TR
    elif op == 'lt':
        return TL < TR
    elif op == 'le':
        return TL <= TR
    elif op == 'add':
        return TR == TL + k
    elif op == 'sub':
        return TR == TL - k
    else:
        return TL == TR  # 安全兜底

def _build_solver(n: int,
                  con_left: List[List[str]], con_right: List[List[str]],
                  con_op: List[str], con_k: List[int], con_layer: List[str],
                  affine_params: List[int],
                  clue_pos: List[List[str]], clue_val: List[int],
                  diag_type: str, diag_sum: int) -> Tuple[Solver, List[List[Int]]]:
    X = [[Int(f"x_{i+1}_{j+1}") for j in range(n)] for i in range(n)]
    s = Solver()
    # 值域
    for i in range(n):
        for j in range(n):
            s.add(And(X[i][j] >= 1, X[i][j] <= n))
    # 行列Distinct
    for i in range(n):
        s.add(Distinct(X[i]))
    for j in range(n):
        s.add(Distinct([X[i][j] for i in range(n)]))
    # 预填提示
    for k in range(len(clue_val)):
        i = int(clue_pos[k][0]) - 1
        j = int(clue_pos[k][1]) - 1
        s.add(X[i][j] == clue_val[k])
    # 复合关系约束
    for k in range(len(con_op)):
        i1 = int(con_left[k][0]) - 1
        j1 = int(con_left[k][1]) - 1
        i2 = int(con_right[k][0]) - 1
        j2 = int(con_right[k][1]) - 1
        s.add(compose_rel(X[i1][j1], X[i2][j2], con_op[k], con_k[k], con_layer[k], affine_params))
    # 对角线求和（条件分支）
    if diag_type == 'main':
        s.add(Sum([X[i][i] for i in range(n)]) == diag_sum)
    else:
        s.add(Sum([X[i][n-1-i] for i in range(n)]) == diag_sum)
    return s, X

def _check_unique(n: int,
                  con_left: List[List[str]], con_right: List[List[str]],
                  con_op: List[str], con_k: List[int], con_layer: List[str],
                  affine_params: List[int],
                  clue_pos: List[List[str]], clue_val: List[int],
                  diag_type: str, diag_sum: int) -> bool:
    s, X = _build_solver(n, con_left, con_right, con_op, con_k, con_layer,
                         affine_params, clue_pos, clue_val, diag_type, diag_sum)
    if s.check() != sat:
        return False
    m = s.model()
    # 排除当前解，检查是否存在第二解
    block = Or([X[i][j] != m.evaluate(X[i][j]) for i in range(n) for j in range(n)])
    s.add(block)
    return s.check() != sat

def init_futoshiki_ultimate(n: int, con_min: int, con_max: int, clue_min: int, clue_max: int, op_pool: List[str]) -> bool:
    tries = 0
    while tries < 150:
        tries += 1
        sol = _latin_square(n)
        pairs = _adjacent_pairs(n)
        random.shuffle(pairs)

        # 仿射参数（隐变量层）——题面将显示
        a = random.choice([1, 2])
        b = random.choice([0, 1])
        affine_params = [a, b]

        # 目标数量
        target_con = random.randint(con_min, con_max)
        target_clue = random.randint(clue_min, clue_max)

        layer_pool = ['raw', 'sq', 'tri', 'aff']
        con_left, con_right, con_op, con_k, con_layer = [], [], [], [], []

        # 与解一致的候选（严格避免冲突：仅选择满足变换后关系的算子与符号）
        consistent_per_pair = []
        for (aij, bij) in pairs:
            (i1, j1), (i2, j2) = aij, bij
            v1, v2 = sol[i1-1][j1-1], sol[i2-1][j2-1]
            merged = []
            for layer in layer_pool:
                if layer == 'raw':
                    t1, t2 = v1, v2
                elif layer == 'sq':
                    t1, t2 = v1*v1, v2*v2
                elif layer == 'tri':
                    t1, t2 = v1*(v1+1)//2, v2*(v2+1)//2
                elif layer == 'aff':
                    t1, t2 = a*v1 + b, a*v2 + b
                else:
                    t1, t2 = v1, v2
                # 比较类（严格/非严格）
                if 'gt' in op_pool and t1 > t2:
                    merged.append(('gt', 0, layer))
                if 'ge' in op_pool and t1 >= t2:
                    merged.append(('ge', 0, layer))
                if 'lt' in op_pool and t1 < t2:
                    merged.append(('lt', 0, layer))
                if 'le' in op_pool and t1 <= t2:
                    merged.append(('le', 0, layer))
                # 差值类（K为正整数；ADD仅当t2>t1，SUB仅当t1>t2）
                diff = abs(t2 - t1)
                if diff > 0:
                    if t2 > t1 and 'add' in op_pool:
                        merged.append(('add', diff, layer))
                    if t1 > t2 and 'sub' in op_pool:
                        merged.append(('sub', diff, layer))
            consistent_per_pair.append(merged)

        valid_indices = [idx for idx in range(len(pairs)) if len(consistent_per_pair[idx]) > 0]
        random.shuffle(valid_indices)
        chosen = valid_indices[:target_con]
        for idx in chosen:
            (i1, j1), (i2, j2) = pairs[idx]
            op, k, layer = random.choice(consistent_per_pair[idx])
            con_left.append([str(i1), str(j1)])
            con_right.append([str(i2), str(j2)])
            con_op.append(op)
            con_k.append(k)
            con_layer.append(layer)

        # 生成提示（与解一致）
        all_cells = [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)]
        random.shuffle(all_cells)
        clue_cells = all_cells[:target_clue]
        clue_pos = [[str(i), str(j)] for (i, j) in clue_cells]
        clue_val = [sol[i - 1][j - 1] for (i, j) in clue_cells]

        # 对角线约束（与解一致）
        diag_type = random.choice(['main', 'anti'])
        diag_sum = sum(sol[i][i] for i in range(n)) if diag_type == 'main' else sum(sol[i][n-1-i] for i in range(n))

        # 唯一性检测 + 自适应加强（提示优先，其次关系）
        s_con_left, s_con_right = list(con_left), list(con_right)
        s_con_op, s_con_k, s_con_layer = list(con_op), list(con_k), list(con_layer)
        s_clue_pos, s_clue_val = list(clue_pos), list(clue_val)
        s_diag_type, s_diag_sum = diag_type, diag_sum

        unique = _check_unique(n,
                               s_con_left, s_con_right, s_con_op, s_con_k, s_con_layer,
                               affine_params, s_clue_pos, s_clue_val,
                               s_diag_type, s_diag_sum)

        rem_cells = all_cells[target_clue:]
        rem_pairs = [idx for idx in range(len(pairs)) if idx not in chosen and len(consistent_per_pair[idx]) > 0]
        random.shuffle(rem_pairs)
        add_clue_i = target_clue
        add_con_i = target_con

        while not unique and (add_clue_i < clue_max or add_con_i < con_max):
            if add_clue_i < clue_max and rem_cells:
                (ci, cj) = rem_cells.pop()
                s_clue_pos.append([str(ci), str(cj)])
                s_clue_val.append(sol[ci - 1][cj - 1])
                add_clue_i += 1
            elif add_con_i < con_max and rem_pairs:
                idx = rem_pairs.pop()
                (i1, j1), (i2, j2) = pairs[idx]
                op, k, layer = random.choice(consistent_per_pair[idx])
                s_con_left.append([str(i1), str(j1)])
                s_con_right.append([str(i2), str(j2)])
                s_con_op.append(op)
                s_con_k.append(k)
                s_con_layer.append(layer)
                add_con_i += 1
            unique = _check_unique(n,
                                   s_con_left, s_con_right, s_con_op, s_con_k, s_con_layer,
                                   affine_params, s_clue_pos, s_clue_val,
                                   s_diag_type, s_diag_sum)

        if unique:
            # 构造题面矩阵（X或数字）
            given = [['X' for _ in range(n)] for _ in range(n)]
            for k in range(len(s_clue_val)):
                i = int(s_clue_pos[k][0]) - 1
                j = int(s_clue_pos[k][1]) - 1
                given[i][j] = s_clue_val[k]

            _SCENARIO["n"] = n
            _SCENARIO["solution"] = sol
            _SCENARIO["given"] = given
            _SCENARIO["con_left"] = s_con_left
            _SCENARIO["con_right"] = s_con_right
            _SCENARIO["con_op"] = s_con_op
            _SCENARIO["con_k"] = s_con_k
            _SCENARIO["con_layer"] = s_con_layer
            _SCENARIO["affine_params"] = affine_params
            _SCENARIO["clue_pos"] = s_clue_pos
            _SCENARIO["clue_val"] = s_clue_val
            _SCENARIO["diag_type"] = s_diag_type
            _SCENARIO["diag_sum"] = s_diag_sum
            return True
    return False

# 只读接口
def get_solution_grid(): return _SCENARIO["solution"]
def get_given_grid(): return _SCENARIO["given"]
def get_con_left(): return _SCENARIO["con_left"]
def get_con_right(): return _SCENARIO["con_right"]
def get_con_op(): return _SCENARIO["con_op"]
def get_con_k(): return _SCENARIO["con_k"]
def get_con_layer(): return _SCENARIO["con_layer"]
def get_affine_params(): return _SCENARIO["affine_params"]
def get_diag_type(): return _SCENARIO["diag_type"]
def get_diag_sum(): return _SCENARIO["diag_sum"]
def get_clue_pos(): return _SCENARIO["clue_pos"]
def get_clue_val(): return _SCENARIO["clue_val"]

def format_constraints_text_templates(con_left: List[List[str]], con_right: List[List[str]],
                                      con_op: List[str], con_k: List[int],
                                      con_layer: List[str], templates: List[str]) -> str:
    """
    文本渲染：
    - 修复了加减法模板混合导致的显示错误
    - 确保文本描述与Z3约束逻辑严格一致
    """
    lines = []
    for idx in range(len(con_op)):
        L = f"({con_left[idx][0]},{con_left[idx][1]})"
        R = f"({con_right[idx][0]},{con_right[idx][1]})"
        K = str(con_k[idx])
        op = con_op[idx]
        layer = con_layer[idx]
        
        candidates = []
        
        # 1. Raw 层 (原值)
        if layer == 'raw':
            if op == 'gt': candidates = ['{L} > {R}']
            elif op == 'ge': candidates = ['{L} ≥ {R}']
            elif op == 'lt': candidates = ['{L} < {R}']
            elif op == 'le': candidates = ['{L} ≤ {R}']
            elif op == 'add': candidates = ['{R} = {L} + {K}']
            elif op == 'sub': candidates = ['{R} = {L} - {K}']
            
        # 2. Square 层 (平方)
        elif layer == 'sq':
            if op == 'gt': candidates = ['平方({L}) > 平方({R})'] # 简化模板选择，避免歧义
            elif op == 'ge': candidates = ['平方({L}) ≥ 平方({R})']
            elif op == 'lt': candidates = ['平方({L}) < 平方({R})']
            elif op == 'le': candidates = ['平方({L}) ≤ 平方({R})']
            elif op == 'add': candidates = ['平方({R}) = 平方({L}) + {K}'] # 严格对应 add
            elif op == 'sub': candidates = ['平方({R}) = 平方({L}) - {K}'] # 严格对应 sub
            
        # 3. Tri 层 (三角数)
        elif layer == 'tri':
            if op == 'gt': candidates = ['三角数({L}) > 三角数({R})']
            elif op == 'ge': candidates = ['三角数({L}) ≥ 三角数({R})']
            elif op == 'lt': candidates = ['三角数({L}) < 三角数({R})']
            elif op == 'le': candidates = ['三角数({L}) ≤ 三角数({R})']
            elif op == 'add': candidates = ['三角数({R}) = 三角数({L}) + {K}']
            elif op == 'sub': candidates = ['三角数({R}) = 三角数({L}) - {K}']
            
        # 4. Affine 层 (仿射)
        else: # aff
            if op == 'gt': candidates = ['仿射({L}) > 仿射({R})']
            elif op == 'ge': candidates = ['仿射({L}) ≥ 仿射({R})']
            elif op == 'lt': candidates = ['仿射({L}) < 仿射({R})']
            elif op == 'le': candidates = ['仿射({L}) ≤ 仿射({R})']
            elif op == 'add': candidates = ['仿射({R}) = 仿射({L}) + {K}']
            elif op == 'sub': candidates = ['仿射({R}) = 仿射({L}) - {K}']

        # 安全兜底：如果candidates为空（理论不应发生），给默认值
        if not candidates:
            candidates = [f"Constraint Error: {op} on {layer}"]

        tmpl = random.choice(candidates)
        text = tmpl.replace('{L}', L).replace('{R}', R).replace('{K}', K)
        lines.append(text)
        
    return "\n".join(lines)