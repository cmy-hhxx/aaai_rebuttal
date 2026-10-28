# campsite_smoke_0.py
# 使用 Z3 对“帐篷与树”进行建模并求解，返回最终网格（二维列表）
from z3 import Solver, Bool, Sum, If, And, Or, Not, sat

def build_tents_model(grid, row_constraints, col_constraints):
    """
    构建并返回 (solver, tent, R, C)
    - grid: List[List[str]] with 'T' or 'X'
    - row_constraints: List[int]
    - col_constraints: List[int]
    规则：
      1) 帐篷只能放在原本为 'X' 的格子
      2) 每个帐篷必须与某棵树正交相邻
      3) 帐篷两两不相邻（8邻域）
      4) 行/列帐篷数量满足约束
      5) 帐篷总数 == 树木总数
      6) 每棵树恰好匹配 1 个相邻帐篷（等价于双射）
    """
    R = len(grid)
    C = len(grid[0]) if R else 0

    s = Solver()

    # tent[r][c] == True 表示在 (r,c) 放帐篷
    tent = [[Bool(f"tent_{r}_{c}") for c in range(C)] for r in range(R)]

    # 仅允许在 'X' 放帐篷；'T' 上不允许放
    for r in range(R):
        for c in range(C):
            if grid[r][c] == 'T':
                s.add(tent[r][c] == False)

    # 行/列约束
    for r in range(R):
        s.add(Sum([If(tent[r][c], 1, 0) for c in range(C)]) == row_constraints[r])
    for c in range(C):
        s.add(Sum([If(tent[r][c], 1, 0) for r in range(R)]) == col_constraints[c])

    # 帐篷不能相互接触（包括对角线）：对每个格子，若为帐篷，则其 8 邻域都不能为帐篷
    dirs8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    for r in range(R):
        for c in range(C):
            neigh = []
            for dr, dc in dirs8:
                rr, cc = r + dr, c + dc
                if 0 <= rr < R and 0 <= cc < C:
                    neigh.append(tent[rr][cc])
            if neigh:
                s.add(Implies_safe(tent[r][c], And([Not(x) for x in neigh])))

    # 帐篷必须与至少一棵树正交相邻
    dirs4 = [(-1,0),(1,0),(0,-1),(0,1)]
    for r in range(R):
        for c in range(C):
            if grid[r][c] == 'X':
                adj_trees = []
                for dr, dc in dirs4:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < R and 0 <= cc < C and grid[rr][cc] == 'T':
                        adj_trees.append(True)
                # 若该空地周围根本没有树，则不可能放帐篷
                if not adj_trees:
                    s.add(tent[r][c] == False)
                # 否则 tent 为 True 时必须“存在相邻树”——这里已由结构保证（因为只有树邻域才允许为真），
                # 但仍保留显式约束：tent -> Or(相邻为树)
                else:
                    s.add(Implies_safe(tent[r][c], Or([BoolVal_safe(True) for _ in adj_trees])))

    # 双射匹配：每个帐篷匹配恰好 1 棵相邻树；每棵树匹配恰好 1 个相邻帐篷
    trees = [(r,c) for r in range(R) for c in range(C) if grid[r][c] == 'T']
    tent_cells = [(r,c) for r in range(R) for c in range(C) if grid[r][c] == 'X']

    # match_tr_tc 仅在 “树-帐篷格子正交相邻” 时才创建
    match = {}
    for tr, tc in trees:
        for dr, dc in dirs4:
            rr, cc = tr + dr, tc + dc
            if 0 <= rr < R and 0 <= cc < C and grid[rr][cc] == 'X':
                match[(tr, tc, rr, cc)] = Bool(f"m_{tr}_{tc}_{rr}_{cc}")

    # 若 match 为真，则该帐篷格必须放帐篷
    for (tr, tc, rr, cc), mvar in match.items():
        s.add(Implies_safe(mvar, tent[rr][cc]))

    # 每棵树恰好匹配 1 个相邻帐篷格
    for tr, tc in trees:
        ms = [match[(tr, tc, rr, cc)] for dr, dc in dirs4
              for rr, cc in [(tr+dr, tc+dc)]
              if (tr, tc, rr, cc) in match]
        s.add(Sum([If(m, 1, 0) for m in ms]) == 1)

    # 每个放置了帐篷的格子，恰好被 1 棵相邻树匹配
    for rr, cc in tent_cells:
        ms = [match[(tr, tc, rr, cc)] for dr, dc in dirs4
              for tr, tc in [(rr+dr, cc+dc)]
              if (tr, tc, rr, cc) in match]
        # 若该帐篷格周围没有树，则已强制 tent==False；否则：tent -> exactly1(match)
        if ms:
            s.add(Implies_safe(tent[rr][cc], Sum([If(m, 1, 0) for m in ms]) == 1))
            # 同时 match -> tent 已有；为避免“tent=True但match全False”的情况，上句已足够
        else:
            s.add(tent[rr][cc] == False)

    # 帐篷总数 == 树木总数
    s.add(Sum([If(tent[r][c], 1, 0) for r in range(R) for c in range(C)]) == len(trees))

    return s, tent, R, C


def solve_grid(grid, row_constraints, col_constraints):
    """
    返回解出的最终网格（二维列表），用 'C' 标记帐篷，其余保持 'T'/'X'
    """
    s, tent, R, C = build_tents_model(grid, row_constraints, col_constraints)
    if s.check() != sat:
        # 若无解，返回原网格（也可抛异常；这里选择返回原网格以便数据生成不中断）
        return grid

    m = s.model()
    out = [[grid[r][c] for c in range(C)] for r in range(R)]
    for r in range(R):
        for c in range(C):
            if out[r][c] == 'X' and bool(m.evaluate(tent[r][c], model_completion=True)):
                out[r][c] = 'C'
    return out


# --------- 小工具：避免导入 BoolVal/Implies 的额外开销写法不一致 ----------
def BoolVal_safe(v: bool):
    # z3.BoolVal 在某些环境中需显式导入；此处用 Or/And 构造常量也可
    return And() if v else Or()

def Implies_safe(a, b):
    return Or(Not(a), b)