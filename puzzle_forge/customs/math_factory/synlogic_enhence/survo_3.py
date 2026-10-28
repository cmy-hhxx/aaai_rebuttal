# survo_5.py
import random
from typing import Dict, List, Tuple, Any, Optional
from z3 import Int, Solver, sat

__all__ = ["ctx"]
_CTX: Optional[Dict[str, Any]] = None     # 缓存上下文


# ---------- 基础工具 ----------
def _make_teams(n: int) -> List[str]:
    return [f'T{i+1}' for i in range(n)]


def _row_total(team: str, teams: List[str],
               upper: Dict[Tuple[str, str], int], mp: int) -> int:
    idx = teams.index(team)
    s = 0
    for j, opp in enumerate(teams):
        if j == idx:
            continue
        if idx < j:
            s += upper[(team, opp)]
        else:
            s += mp - upper[(opp, team)]
    return s


# ---------- 唯一性验证 ----------
def _unique_check(hidden: List[Tuple[str, str]],
                  revealed: List[Tuple[str, str]],
                  upper: Dict[Tuple[str, str], int],
                  mp: int,
                  row_tot: Dict[str, int],
                  known_rows: List[str],
                  teams: List[str],
                  tgt: Tuple[str, str]) -> Tuple[bool, int]:
    """
    返回 (is_unique, home_score_of_target)
    """
    s = Solver()
    var = {p: Int(f'v_{p[0]}_{p[1]}') for p in hidden}
    for v in var.values():
        s.add(v >= 0, v <= mp)

    # 反对称：仅当两个方向均为变量时添加
    for h, a in hidden:
        rev = (a, h)
        if rev in var:
            s.add(var[(h, a)] + var[rev] == mp)

    # 已公开比分
    for h, a in revealed:
        if (h, a) in var:
            s.add(var[(h, a)] == upper[(h, a)])
        elif (a, h) in var:
            s.add(var[(a, h)] == mp - upper[(h, a)])

    # 行总分约束（部分球队）
    for t in known_rows:
        idx = teams.index(t)
        expr = 0
        for j, opp in enumerate(teams):
            if j == idx:
                continue
            if idx < j:
                expr += var.get((t, opp), upper.get((t, opp)))
            else:
                expr += mp - var.get((opp, t), upper.get((opp, t)))
        s.add(expr == row_tot[t])

    tgt_var = var[tgt]                       # 目标变量
    if s.check() != sat:
        return False, -1
    model_val = s.model()[tgt_var].as_long()

    # 检查是否存在不同的第二个取值
    s.push()
    s.add(tgt_var != model_val)
    second_check = s.check()
    s.pop()
    is_unique = (second_check != sat)       # unsat => 唯一
    return is_unique, model_val


# ---------- 生成完整上下文 ----------
def _build_ctx() -> Dict[str, Any]:
    while True:
        team_num = random.randint(4, 8)
        mp = random.randint(2, 5)
        teams = _make_teams(team_num)

        # 随机生成上三角主场得分
        upper = {(teams[i], teams[j]): random.randint(0, mp)
                 for i in range(team_num) for j in range(i + 1, team_num)}

        # 计算行总分
        row_tot = {t: _row_total(t, teams, upper, mp) for t in teams}

        # 随机隐藏 30%~50%
        pairs = list(upper.keys())
        hide_cnt = max(1, int(len(pairs) * random.uniform(0.3, 0.5)))
        hidden = random.sample(pairs, hide_cnt)
        revealed = [p for p in pairs if p not in hidden]

        target_pair = random.choice(hidden)
        ask_home = random.choice([True, False])

        # 选 1~2 支球队公布总分（必含目标双方）
        must = list(target_pair)
        others = [t for t in teams if t not in must]
        extra = random.sample(others, random.randint(0, 2))
        known_rows = must + extra

        unique, tgt_home = _unique_check(hidden, revealed, upper, mp,
                                         row_tot, known_rows, teams, target_pair)
        if not unique:
            continue   # 重新生成

        tgt_score = tgt_home if ask_home else mp - tgt_home

        reveal_desc = '; '.join(f'{p[0]}主场对{p[1]}得{upper[p]}分' for p in revealed)
        row_desc = '; '.join(f'{t}:{row_tot[t]}' for t in known_rows)
        warn_line = '至少一条'    # 简易提示文本

        return dict(
            team_num=team_num,
            teams=teams,
            max_points=mp,
            upper_scores=upper,
            hidden_pairs=hidden,
            reveal_pairs=revealed,
            row_total_known_teams=known_rows,
            row_total_known_values=[row_tot[t] for t in known_rows],
            target_pair=target_pair,
            ask_home=ask_home,
            target_score=tgt_score,
            reveal_desc=reveal_desc,
            row_total_desc=row_desc,
            warn_line=warn_line,
            unique_verified=True
        )


# ---------- 对外接口 ----------
def ctx(key: str) -> Any:
    global _CTX
    if _CTX is None:
        _CTX = _build_ctx()
    return _CTX[key]