# space_reasoning_tree_5.py

from typing import Dict, List, Tuple, Set, Callable
import random
import re


# -----------------------------
# 基础工具：由 child_facts 与 sibling_facts 等构建“可知的”知识图谱
# -----------------------------
def build_tree(child_facts: List[Tuple[str, List[str]]]) -> Tuple[Dict[str, List[str]], Dict[str, Set[str]]]:
    adjacency: Dict[str, List[str]] = {}
    parent_map: Dict[str, Set[str]] = {}
    for parent, children in child_facts:
        adjacency.setdefault(parent, [])
        for c in children:
            if c not in adjacency[parent]:
                adjacency[parent].append(c)
            parent_map.setdefault(c, set()).add(parent)
    return adjacency, parent_map


def build_knowledge_maps(
    child_facts: List[Tuple[str, List[str]]],
    sibling_facts: List[Tuple[str, List[str]]],
    leaf_facts: List[str],
    degree_bounds: List[Tuple[str, int, int]],
) -> Tuple[Dict[str, List[str]], Dict[str, Set[str]], Callable[[str], bool]]:
    # 已知子集合（可能不全）
    known_children: Dict[str, Set[str]] = {}
    complete_by_cf: Set[str] = set()

    # 1) child_facts 提供完整子集合
    for p, ch in child_facts:
        known_children.setdefault(p, set()).update(ch)
        complete_by_cf.add(p)

    # 2) sibling_facts 提供父的一部分子集合（不保证全）
    for p, subs in sibling_facts:
        known_children.setdefault(p, set()).update(subs)

    # 3) 精确度界（lo==hi）可让“部分子集合”在数量相等时变为“完整子集合”
    deg_map: Dict[str, Tuple[int, int]] = {u: (lo, hi) for (u, lo, hi) in degree_bounds}

    def is_complete(u: str) -> bool:
        if u in complete_by_cf:
            return True
        if u in leaf_facts:
            return True
        if u in deg_map:
            lo, hi = deg_map[u]
            k = len(known_children.get(u, set()))
            if lo == hi == k:
                return True
        return False

    # 父映射
    parent_map: Dict[str, Set[str]] = {}
    for p, chset in known_children.items():
        for c in chset:
            parent_map.setdefault(c, set()).add(p)

    # 统一输出为列表形式
    adjacency_list: Dict[str, List[str]] = {p: sorted(list(chset)) for p, chset in known_children.items()}

    return adjacency_list, parent_map, is_complete


# -----------------------------
# 关系计算：基于知识图谱，无法判定则返回 'unknown'
# -----------------------------
def _compute_siblings_with_kb(
    child_facts, leaf_facts, sibling_facts, degree_bounds, target
) -> str:
    adj, pmap, is_complete = build_knowledge_maps(child_facts, sibling_facts, leaf_facts, degree_bounds)
    parents = list(pmap.get(target, set()))
    if len(parents) != 1:
        return "unknown"
    p = parents[0]
    if not is_complete(p):
        return "unknown"
    sibs = [x for x in adj.get(p, []) if x != target]
    return ",".join(sorted(sibs)) if sibs else "unknown"


def _compute_uncles_aunts_with_kb(
    child_facts, leaf_facts, sibling_facts, degree_bounds, target
) -> str:
    adj, pmap, is_complete = build_knowledge_maps(child_facts, sibling_facts, leaf_facts, degree_bounds)
    parents = list(pmap.get(target, set()))
    if len(parents) != 1:
        return "unknown"
    p = parents[0]
    gps = [g for g, kids in adj.items() if p in kids]
    if len(gps) != 1:
        return "unknown"
    g = gps[0]
    if not is_complete(g):
        return "unknown"
    rel = [x for x in adj.get(g, []) if x != p]
    return ",".join(sorted(rel)) if rel else "unknown"


def _compute_cousins_with_kb(
    child_facts, leaf_facts, sibling_facts, degree_bounds, target
) -> str:
    adj, pmap, is_complete = build_knowledge_maps(child_facts, sibling_facts, leaf_facts, degree_bounds)
    parents = list(pmap.get(target, set()))
    if len(parents) != 1:
        return "unknown"
    p = parents[0]
    gps = [g for g, kids in adj.items() if p in kids]
    if len(gps) != 1:
        return "unknown"
    g = gps[0]
    if not is_complete(g):
        return "unknown"
    cousins: Set[str] = set()
    for s in [x for x in adj.get(g, []) if x != p]:
        if not is_complete(s):
            return "unknown"
        for ch in adj.get(s, []):
            cousins.add(ch)
    return ",".join(sorted(cousins)) if cousins else "unknown"


def _compute_nieces_nephews_with_kb(
    child_facts, leaf_facts, sibling_facts, degree_bounds, target
) -> str:
    adj, pmap, is_complete = build_knowledge_maps(child_facts, sibling_facts, leaf_facts, degree_bounds)
    parents = list(pmap.get(target, set()))
    if len(parents) != 1:
        return "unknown"
    p = parents[0]
    if not is_complete(p):
        return "unknown"
    rel: Set[str] = set()
    sibs = [x for x in adj.get(p, []) if x != target]
    if not sibs:
        return "unknown"
    for s in sibs:
        if not is_complete(s):
            return "unknown"
        for ch in adj.get(s, []):
            rel.add(ch)
    return ",".join(sorted(rel)) if rel else "unknown"


def _compute_grandchildren_with_kb(
    child_facts, leaf_facts, sibling_facts, degree_bounds, target
) -> str:
    adj, pmap, is_complete = build_knowledge_maps(child_facts, sibling_facts, leaf_facts, degree_bounds)
    if not is_complete(target):
        return "unknown"
    gcs: Set[str] = set()
    for c in adj.get(target, []):
        if not is_complete(c):
            return "unknown"
        for cc in adj.get(c, []):
            gcs.add(cc)
    return ",".join(sorted(gcs)) if gcs else "unknown"


def compute_answer_from_scenario(scn: dict) -> str:
    goal = scn["goal"]
    child_facts = scn["child_facts"]
    leaf_facts = scn["leaf_facts"]
    sibling_facts = scn["sibling_facts"]
    degree_bounds = scn.get("degree_bounds", [])
    target = scn["target"]

    if goal == "siblings":
        return _compute_siblings_with_kb(child_facts, leaf_facts, sibling_facts, degree_bounds, target)
    if goal == "uncles_aunts":
        return _compute_uncles_aunts_with_kb(child_facts, leaf_facts, sibling_facts, degree_bounds, target)
    if goal == "cousins":
        return _compute_cousins_with_kb(child_facts, leaf_facts, sibling_facts, degree_bounds, target)
    if goal == "nieces_nephews":
        return _compute_nieces_nephews_with_kb(child_facts, leaf_facts, sibling_facts, degree_bounds, target)
    if goal == "grandchildren":
        return _compute_grandchildren_with_kb(child_facts, leaf_facts, sibling_facts, degree_bounds, target)
    return "unknown"


# -----------------------------
# 文本渲染：仅包含实际参与计算的线索，行间以 \n 连接（返回字面 '\n'）
# -----------------------------
def _format_list(l: List[str]) -> str:
    return "[" + ",".join(sorted(l)) + "]"


def _format_child_facts(cf: List[Tuple[str, List[str]]]) -> List[str]:
    lines = []
    for p, ch in cf:
        lines.append(f"{p} -> " + _format_list(ch))
    return lines


def format_facts_text(scn: dict) -> str:
    cf_lines = _format_child_facts(scn["child_facts"])
    leaf = scn["leaf_facts"]
    sgroups = scn["sibling_facts"]
    deg_bounds = scn.get("degree_bounds", [])

    # 用于 sibling_facts 行级标注完整/部分
    deg_map: Dict[str, Tuple[int, int]] = {u: (lo, hi) for (u, lo, hi) in deg_bounds}

    title_variants = ["以下父节点的全部子节点为:", "父子全量事实如下:", "已知的父子全量信息如下:"]
    leaf_variants = ["以下节点为叶子(无子节点): ", "叶子节点列表: ", "明确无子节点的有: "]
    sib_title_variants = ["父节点的子节点提示:", "子集合提示:", "父节点的子集信息:"]
    deg_title_variants = ["子节点数量范围提示:", "分支度约束:", "度约束信息:"]

    rnd = random.Random(scn["seed"] if "seed" in scn else 12345)
    parts: List[str] = []
    parts.append(title_variants[rnd.randint(0, len(title_variants) - 1)])
    parts.extend(cf_lines)
    if leaf:
        parts.append(leaf_variants[rnd.randint(0, len(leaf_variants) - 1)] + _format_list(leaf))
    if sgroups:
        parts.append(sib_title_variants[rnd.randint(0, len(sib_title_variants) - 1)])
        for head, members in sgroups:
            tag = "部分"
            if head in deg_map:
                lo, hi = deg_map[head]
                if lo == hi == len(members):
                    tag = "完整"
            parts.append(f"{head} 的子节点提示({tag}): " + _format_list(members))
    if deg_bounds:
        parts.append(deg_title_variants[rnd.randint(0, len(deg_title_variants) - 1)])
        for u, lo, hi in deg_bounds:
            parts.append(f"{u} 的子节点数量在区间 [{lo},{hi}] 内")

    # 返回字面 '\n'
    return "\\n".join(parts)


# -----------------------------
# 场景生成：仅生成与计算一致的线索，保障唯一且非空答案（多步推理 + 有界重试）
# -----------------------------
def _gen_names(n: int) -> List[str]:
    return [f"X{i+1}" for i in range(n)]


def gen_space_scenario(seed: int, min_nodes: int, max_nodes: int, deg_min: int, deg_max: int) -> dict:
    max_attempts = 12
    last_scn = None

    for attempt in range(max_attempts):
        rnd = random.Random(seed + attempt)
        deg_min_local = max(1, deg_min)
        deg_max_local = max(deg_min_local + 1, deg_max)

        n_nodes = rnd.randint(min_nodes, max_nodes)
        names = _gen_names(n_nodes)

        # 构建随机有根树
        root = names[0]
        full_adj: Dict[str, List[str]] = {root: []}
        parent_of: Dict[str, str] = {}

        def add_edge(u: str, v: str):
            if u == v:
                return
            full_adj.setdefault(u, [])
            if v not in full_adj[u]:
                full_adj[u].append(v)
            parent_of[v] = u

        caps = {u: rnd.randint(deg_min_local, deg_max_local) for u in names}
        for u in names:
            full_adj.setdefault(u, [])

        # root 至少两个子节点（若可能）
        pool = names[1:]
        first_k = min(2, len(pool))
        first_children = rnd.sample(pool, k=first_k) if pool else []
        for c in first_children:
            if c in pool:
                pool.remove(c)
            add_edge(root, c)

        def pick_host(exclude: str) -> str:
            candidates = [u for u in names if u != exclude and len(full_adj[u]) < caps[u]]
            if not candidates:
                fallback_hosts = [u for u in names if u != exclude]
                return rnd.choice(fallback_hosts) if fallback_hosts else root
            return rnd.choice(candidates)

        while pool:
            v = pool.pop(0)
            host = pick_host(v)
            add_edge(host, v)

        leaves = [u for u in names if len(full_adj.get(u, [])) == 0]

        # 计算深度、祖先
        depth: Dict[str, int] = {}
        depth[root] = 0
        order = [root]
        i = 0
        while i < len(order):
            u = order[i]
            for v in full_adj.get(u, []):
                depth[v] = depth[u] + 1
                order.append(v)
            i += 1

        # 关系候选
        sib_targets = [x for x in names if x in parent_of and len(full_adj[parent_of[x]]) >= 2]
        cousin_targets = []
        uncle_targets = []
        for x in names:
            if x not in parent_of:
                continue
            p = parent_of[x]
            if p in parent_of:
                g = parent_of[p]
                if len(full_adj[g]) >= 2 and len(full_adj[p]) >= 1:
                    uncle_targets.append(x)
                others = [s for s in full_adj[g] if s != p]
                if any(len(full_adj.get(s, [])) >= 1 for s in others):
                    cousin_targets.append(x)
        nn_targets = []
        for x in names:
            if x not in parent_of:
                continue
            p = parent_of[x]
            siblings = [s for s in full_adj[p] if s != x]
            if not siblings:
                continue
            if any(len(full_adj.get(s, [])) >= 1 for s in siblings):
                nn_targets.append(x)
        gc_targets = []
        for x in names:
            if full_adj.get(x) and any(full_adj.get(c) for c in full_adj[x]):
                gc_targets.append(x)

        goals_primary = ["cousins", "uncles_aunts", "nieces_nephews", "grandchildren"]
        fallback = ["siblings"]
        all_goals = goals_primary + fallback
        goal = rnd.choice(goals_primary)

        def pick_or_fallback():
            order_goal = [goal] + [g for g in all_goals if g != goal]
            for g in order_goal:
                if g == "cousins" and cousin_targets:
                    return g, rnd.choice(cousin_targets)
                if g == "uncles_aunts" and uncle_targets:
                    return g, rnd.choice(uncle_targets)
                if g == "nieces_nephews" and nn_targets:
                    return g, rnd.choice(nn_targets)
                if g == "grandchildren" and gc_targets:
                    return g, rnd.choice(gc_targets)
                if g == "siblings" and sib_targets:
                    return g, rnd.choice(sib_targets)
            return "siblings", rnd.choice(names[1:]) if len(names) > 1 else names[0]

        if attempt >= max_attempts // 2:
            goal = "siblings"
        goal, target = pick_or_fallback()

        # 组装公开线索（仅限于真正参与计算的线索）
        child_facts: List[Tuple[str, List[str]]] = []
        leaf_facts: List[str] = []
        sibling_facts: List[Tuple[str, List[str]]] = []
        avoid_sib_on: Set[str] = set()  # 对这些父，后续不再生成 sibling_facts
        forbid_member = target          # 禁止非亲父的子集合提示包含目标节点
        degree_bounds: List[Tuple[str, int, int]] = []

        def add_child_fact(u: str):
            rec = (u, list(full_adj[u]))
            if rec not in child_facts:
                child_facts.append(rec)

        def add_complete_sib(u: str):
            # 用 sibling_facts + 精确度界表达“完整子集合”
            kids = list(full_adj[u])
            subset = sorted(kids)
            if (u, subset) not in sibling_facts:
                sibling_facts.append((u, subset))
            if (u, len(kids), len(kids)) not in degree_bounds:
                degree_bounds.append((u, len(kids), len(kids)))
            avoid_sib_on.add(u)

        # 各目标的关键线索组合（确保关键父/祖父“完整”，并避免同一父的重复呈现）
        if goal == "siblings":
            p = parent_of[target]
            if len(full_adj[p]) < 2:
                extra_candidates = [x for x in names if x != target and parent_of.get(x, None) != p]
                if extra_candidates:
                    extra = rnd.choice(extra_candidates)
                    add_edge(p, extra)
            add_complete_sib(p)  # 关键父 p 使用“完整子集合 + 精确度界”
            if p in parent_of:
                add_child_fact(parent_of[p])  # 可选祖父 facts（与 p 不重复形态）

        elif goal == "uncles_aunts":
            p = parent_of[target]
            g = parent_of[p]
            add_child_fact(g)   # 祖父全量，父 p 用完整兄弟提示
            add_complete_sib(p)

        elif goal == "cousins":
            p = parent_of[target]
            g = parent_of[p]
            # 随机选择 p 或 g 用“完整子集合 + 精确度界”，另一个用 child_facts（互斥呈现）
            if rnd.random() < 0.5:
                add_complete_sib(p)
                add_child_fact(g)
            else:
                add_complete_sib(g)
                add_child_fact(p)
            # g 的其他子节点若有子，则给出其完整或 child_facts（二选一，不混用）
            for s in [x for x in full_adj[g] if x != p]:
                if full_adj.get(s):
                    if rnd.random() < 0.5:
                        add_complete_sib(s)
                    else:
                        add_child_fact(s)
                else:
                    if s not in leaf_facts:
                        leaf_facts.append(s)

        elif goal == "nieces_nephews":
            p = parent_of[target]
            # p 的子集合用随机方式表达：完整兄弟提示或 child_facts（不混用）
            if rnd.random() < 0.65:
                add_complete_sib(p)
            else:
                add_child_fact(p)
            sibs = [s for s in full_adj[p] if s != target]
            if not sibs:
                extra_candidates = [x for x in names if x != target and parent_of.get(x, None) != p]
                if extra_candidates:
                    extra = rnd.choice(extra_candidates)
                    add_edge(p, extra)
                    sibs = [extra]
            for s in sibs:
                if full_adj.get(s):
                    if rnd.random() < 0.5:
                        add_complete_sib(s)
                    else:
                        add_child_fact(s)
                else:
                    if s not in leaf_facts:
                        leaf_facts.append(s)

        elif goal == "grandchildren":
            # 若目标暂无子，强制至少创建一层子、孙
            if not full_adj.get(target):
                new_cand = [x for x in names if x not in parent_of]
                if new_cand:
                    new_c = rnd.choice(new_cand)
                    add_edge(target, new_c)
            if not any(full_adj.get(c) for c in full_adj[target]):
                c = full_adj[target][0]
                new_ccand = [x for x in names if x not in parent_of]
                if new_ccand:
                    new_cc = rnd.choice(new_ccand)
                    add_edge(c, new_cc)
            # 目标 target 的子集合以“完整兄弟提示+精确度界”或 child_facts 随机呈现（不混用）
            if rnd.random() < 0.7:
                add_complete_sib(target)
            else:
                add_child_fact(target)
            for c in full_adj[target]:
                if full_adj.get(c):
                    if rnd.random() < 0.6:
                        add_complete_sib(c)
                    else:
                        add_child_fact(c)
                else:
                    if c not in leaf_facts:
                        leaf_facts.append(c)

        # 补充 child_facts：保证线索量充足（总行数≥3），且不与“完整提示”父重复
        used_parents = {p for p, _ in child_facts}
        extra_parents = [u for u in names if full_adj.get(u) and u not in used_parents and u not in avoid_sib_on]  # NEW: 排除已完整提示的父
        rnd.shuffle(extra_parents)
        idx = 0

        def total_lines():
            return len(child_facts) + len(sibling_facts)

        while total_lines() < 3 and idx < len(extra_parents):
            add_child_fact(extra_parents[idx])
            idx += 1

        # 重新计算 used_parents，避免“全量+部分/完整提示”混合到同一父
        used_parents = {p for p, _ in child_facts}

        # 兄弟组提示（避免包含目标节点于非亲父子集合；避免与 child_facts 重复父；避免给已标完整的父）
        parents_for_sib = [u for u in names if full_adj.get(u)]
        rnd.shuffle(parents_for_sib)
        sib_take = rnd.randint(0, min(2, len(parents_for_sib)))
        for u in parents_for_sib[:sib_take]:
            if u in avoid_sib_on:
                continue
            if u in used_parents:
                continue  # 避免与 child_facts 重复，减少显见线索
            kids = list(full_adj[u])
            if len(kids) >= 2:
                k = rnd.randint(2, len(kids))
                subset = rnd.sample(kids, k=k)
            else:
                if rnd.random() < 0.3 and kids:
                    subset = kids[:]
                else:
                    continue
            # 禁止非亲父包含目标节点
            if u != parent_of.get(target, None) and forbid_member in subset:
                subset = [x for x in subset if x != forbid_member]
                if not subset:
                    continue
            sibling_facts.append((u, sorted(subset)))

        # 叶子（小范围补充，且与 child_facts 不冲突）
        leaves_all = [u for u in names if len(full_adj.get(u, [])) == 0]
        parents_in_cf = {p for p, _ in child_facts}
        extra_leaves = [u for u in leaves_all if u not in parents_in_cf]
        rnd.shuffle(extra_leaves)
        leaf_facts.extend(extra_leaves[: rnd.randint(0, min(1, len(extra_leaves)))])
        leaf_facts = sorted(list(set(leaf_facts)))

        # 扩展随机的度约束（不覆盖已设置的精确度约束）
        degree_bounds_existing = set([u for (u, _, _) in degree_bounds])
        cand_deg = [u for u in names if full_adj.get(u) and u not in degree_bounds_existing]
        rnd.shuffle(cand_deg)
        take_deg = rnd.randint(0, min(1, len(cand_deg)))
        for u in cand_deg[:take_deg]:
            true_deg = len(full_adj[u])
            lo = max(1, true_deg - rnd.randint(0, min(2, true_deg - 1 if true_deg > 0 else 0)))
            hi = true_deg + rnd.randint(0, 2)
            degree_bounds.append((u, lo, hi))

        scn = {
            "seed": seed + attempt,
            "nodes_num": n_nodes,
            "child_facts": child_facts,
            "leaf_facts": leaf_facts,
            "sibling_facts": sibling_facts,
            "target": target,
            "goal": goal,
            "degree_bounds": degree_bounds,
        }

        goal_name_map = {
            "siblings": "同层兄弟集合",
            "uncles_aunts": "父系旁系集合",
            "cousins": "堂兄弟集合",
            "nieces_nephews": "侄辈集合",
            "grandchildren": "孙辈集合",
        }
        goal_def_map = {
            "siblings": "与目标节点拥有同一父节点且不包含目标节点本身的所有节点",
            "uncles_aunts": "目标节点的父节点的兄弟节点集合",
            "cousins": "目标节点的父节点的兄弟节点的所有子节点的集合",
            "nieces_nephews": "目标节点的兄弟节点的所有子节点的集合",
            "grandchildren": "目标节点的所有子节点的子节点的集合",
        }
        scn["relation_name"] = goal_name_map[goal]
        scn["relation_def"] = goal_def_map[goal]

        # 计算答案
        ans = compute_answer_from_scenario(scn)

        # 若不充分或不可判定，回退为 siblings（尽量采用完整兄弟提示 + 精确度约束，并补足非重复线索）
        if ans == "unknown" or not ans:
            sib_candidates = [x for x in names if x in parent_of and len(full_adj[parent_of[x]]) >= 2]
            if not sib_candidates:
                exist_kids = list(full_adj[root])
                needed = 2 - len(exist_kids)
                fresh = [x for x in names if x != root and x not in parent_of]
                while needed > 0 and fresh:
                    v = rnd.choice(fresh)
                    fresh.remove(v)
                    add_edge(root, v)
                    needed -= 1
                sib_candidates = list(full_adj[root]) if full_adj.get(root) else [root]
            new_target = rnd.choice(sib_candidates) if sib_candidates else names[0]
            new_child_facts: List[Tuple[str, List[str]]] = []
            new_sibling_facts: List[Tuple[str, List[str]]] = []
            new_degree_bounds: List[Tuple[str, int, int]] = []

            def add_cf2(u: str):
                rec = (u, list(full_adj[u]))
                if rec not in new_child_facts:
                    new_child_facts.append(rec)

            def add_complete_sib2(u: str):
                kids = list(full_adj[u])
                subset = sorted(kids)
                if (u, subset) not in new_sibling_facts:
                    new_sibling_facts.append((u, subset))
                if (u, len(kids), len(kids)) not in new_degree_bounds:
                    new_degree_bounds.append((u, len(kids), len(kids)))

            p = parent_of.get(new_target, None)
            if p is None:
                if new_target != root:
                    add_edge(root, new_target)
                    p = root
            if p is not None:
                # 使用“完整子集合(兄弟提示)+精确度界”
                add_complete_sib2(p)
                # 为了保证线索量≥3，补充祖父与另一个父节点（用 child_facts），避免与 p 冲突
                if p in parent_of:
                    add_cf2(parent_of[p])
                other_parents = [u for u in names if full_adj.get(u) and u != p and (p not in parent_of or u != parent_of[p])]
                if other_parents:
                    add_cf2(rnd.choice(other_parents))
                # 若仍不足，继续补充（不与 p 冲突）
                more_parents = [u for u in names if full_adj.get(u) and u not in {pp for pp, _ in new_child_facts} and u != p]
                idx2 = 0
                while len(new_child_facts) + len(new_sibling_facts) < 3 and idx2 < len(more_parents):
                    add_cf2(more_parents[idx2])
                    idx2 += 1

            scn.update({
                "goal": "siblings",
                "relation_name": goal_name_map["siblings"],
                "relation_def": goal_def_map["siblings"],
                "target": new_target,
                "child_facts": new_child_facts,
                "leaf_facts": leaf_facts,
                "sibling_facts": new_sibling_facts,
                "degree_bounds": new_degree_bounds,
            })
            ans = compute_answer_from_scenario(scn)

        scn["answer"] = ans

        preface = (
            f"某馆藏分类树共有 {n_nodes} 个节点。目标节点为 {scn['target']}。任务: 求{scn['relation_name']}。"
            f"定义: {scn['relation_def']}。线索说明: "
            f"以 A -> [B,C] 形式出现的行为父节点的全部子节点；"
            f"以 子节点提示(...) 出现的行可能为部分或完整，若为完整将以完整字样标注；"
            f"可能出现分支度约束，形如 U 的子节点数量在区间 [lo,hi] 内。"
            f"答案格式: 名称按字典序用逗号分隔; 若无法确定则输出unknown。示例: X1,X3 或 unknown。"
        )
        scn["facts_text"] = format_facts_text(scn)
        scn["preface"] = preface

        last_scn = scn
        if ans != "unknown" and ans and validate_uniqueness_generic(scn):
            return scn

    # 失败兜底：siblings，显式包含“完整兄弟提示+精确度界”并补足非重复线索
    if last_scn is None:
        names = _gen_names(max(min_nodes, 8))
        root = names[0]
        child_facts = [(names[3], [names[4]]), (names[5], [names[6]])]
        sibling_facts = [(root, [names[1], names[2]])]
        degree_bounds = [(root, 2, 2)]
        scn = {
            "seed": seed + max_attempts,
            "nodes_num": len(names),
            "child_facts": child_facts,
            "leaf_facts": [],
            "sibling_facts": sibling_facts,
            "target": names[1],
            "goal": "siblings",
            "degree_bounds": degree_bounds,
            "relation_name": "同层兄弟集合",
            "relation_def": "与目标节点拥有同一父节点且不包含目标节点本身的所有节点",
        }
        scn["answer"] = compute_answer_from_scenario(scn)
        scn["facts_text"] = format_facts_text(scn)
        scn["preface"] = (
            f"某馆藏分类树共有 {scn['nodes_num']} 个节点。目标节点为 {scn['target']}。任务: 求{scn['relation_name']}。"
            f"定义: {scn['relation_def']}。线索说明: "
            f"以 A -> [B,C] 形式出现的行为父节点的全部子节点；"
            f"以 子节点提示(...) 出现的行可能为部分或完整，若为完整将以完整字样标注；"
            f"可能出现分支度约束，形如 U 的子节点数量在区间 [lo,hi] 内。"
            f"答案格式: 名称按字典序用逗号分隔; 若无法确定则输出unknown。示例: X1,X3 或 unknown。"
        )
        return scn

    return last_scn


# -----------------------------
# 唯一性校验：基于知识图谱的关键完整性验证 + 结果一致性
# -----------------------------
def validate_uniqueness_generic(scn: dict) -> bool:
    child_facts = scn["child_facts"]
    leaf_facts = scn["leaf_facts"]
    target = scn["target"]
    goal = scn["goal"]
    ans = scn.get("answer", "")
    sibling_facts = scn.get("sibling_facts", [])
    degree_bounds = scn.get("degree_bounds", [])

    if ans == "unknown" or not ans:
        return False

    # 线索量：允许 child_facts 与 sibling_facts 共同计数
    if len(child_facts) + len(sibling_facts) < 3:
        return False

    # 使用知识图谱检查关键节点完整性
    adj, pmap, is_complete = build_knowledge_maps(child_facts, sibling_facts, leaf_facts, degree_bounds)

    # 基于知识图谱独立重算答案
    recomputed = compute_answer_from_scenario({
        "goal": goal,
        "child_facts": child_facts,
        "leaf_facts": leaf_facts,
        "sibling_facts": sibling_facts,
        "degree_bounds": degree_bounds,
        "target": target,
    })
    if recomputed != ans:
        return False

    # 针对不同目标的必要完整性检查
    if goal == "siblings":
        parents = list(pmap.get(target, set()))
        if len(parents) != 1:
            return False
        if not is_complete(parents[0]):
            return False

    elif goal == "uncles_aunts":
        parents = list(pmap.get(target, set()))
        if len(parents) != 1:
            return False
        p = parents[0]
        gps = [g for g, kids in adj.items() if p in kids]
        if len(gps) != 1:
            return False
        if not is_complete(gps[0]):
            return False

    elif goal == "cousins":
        parents = list(pmap.get(target, set()))
        if len(parents) != 1:
            return False
        p = parents[0]
        gps = [g for g, kids in adj.items() if p in kids]
        if len(gps) != 1:
            return False
        g = gps[0]
        if not is_complete(g):
            return False
        for s in [x for x in adj.get(g, []) if x != p]:
            if not is_complete(s):
                return False

    elif goal == "nieces_nephews":
        parents = list(pmap.get(target, set()))
        if len(parents) != 1:
            return False
        p = parents[0]
        if not is_complete(p):
            return False
        sibs = [x for x in adj.get(p, []) if x != target]
        if not sibs:
            return False
        for s in sibs:
            if not is_complete(s):
                return False

    elif goal == "grandchildren":
        if not is_complete(target):
            return False
        for c in adj.get(target, []):
            if not is_complete(c):
                return False

    return True


# -----------------------------
# 答案格式校验：'unknown' 或 'X数字' 的去重、字典序、逗号分隔
# -----------------------------
def validate_answer_format(ans: str) -> bool:
    if not isinstance(ans, str):
        return False
    s = ans.strip()
    if s == "unknown":
        return True
    parts = s.split(",")
    if any(not p for p in parts):
        return False
    # token 形如 X1、X2...
    if not all(re.fullmatch(r"X\d+", p) for p in parts):
        return False
    # 去重与字典序
    if len(parts) != len(set(parts)):
        return False
    if parts != sorted(parts):
        return False
    return True


__all__ = [
    "build_tree",
    "gen_space_scenario",
    "compute_answer_from_scenario",
    "validate_uniqueness_generic",
    "format_facts_text",
    "validate_answer_format",
]