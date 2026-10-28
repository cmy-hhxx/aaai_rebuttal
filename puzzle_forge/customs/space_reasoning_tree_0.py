# space_reasoning_tree_0.py
# 生成与验证“堂兄弟”题目的通用工具
import random

def _unique(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _ensure_enough_names(names_pool, need, used):
    """确保有足够不重复的名称；若不足，生成占位名以补足。"""
    extra = []
    idx = 1
    while len(extra) + sum(1 for n in names_pool if n not in used) < need:
        extra_name = f"物品{idx}"
        if extra_name not in used and extra_name not in names_pool:
            extra.append(extra_name)
            used.add(extra_name)
        idx += 1
    return extra

def build_core_tree(names_pool, parents_count, child_min, child_max):
    """
    构建核心三层树：
      gp -> parents
      each parent -> children
    返回：
      {
        'gp': <祖父名>,
        'parent_children': { gp: [parent...], parent1: [leaf...], ... },
        'facts_core': [事实句子...],
        'nodes_count': <唯一节点总数>
      }
    """
    pool = _unique(list(names_pool))
    random.shuffle(pool)
    used = set()

    # 选祖父
    if not pool:
        pool = ["ROOT"]
    gp = pool.pop(0)
    used.add(gp)

    # 选父辈（至少2个）
    parents = []
    for _ in range(max(2, parents_count)):
        if not pool:
            pool.extend(_ensure_enough_names(names_pool, 1, used))
        p = pool.pop(0)
        while p in used:
            if not pool:
                pool.extend(_ensure_enough_names(names_pool, 1, used))
            p = pool.pop(0)
        parents.append(p)
        used.add(p)

    parent_children = {gp: parents[:]}

    # 每个父分配子节点
    core_facts = []
    for p in parents:
        k = random.randint(max(1, child_min), max(child_min, child_max))
        children = []
        for _ in range(k):
            if not pool:
                pool.extend(_ensure_enough_names(names_pool, 1, used))
            c = pool.pop(0)
            while c in used:
                if not pool:
                    pool.extend(_ensure_enough_names(names_pool, 1, used))
                c = pool.pop(0)
            children.append(c)
            used.add(c)
        parent_children[p] = children

    # 核心事实：祖父→父；父→子
    core_facts.append(f"{gp}的孩子是：{'、'.join(parents)}")
    for p in parents:
        core_facts.append(f"{p}的孩子是：{'、'.join(parent_children[p])}")

    # 节点总数
    node_set = set([gp]) | set(parents)
    for p in parents:
        node_set |= set(parent_children[p])
    nodes_count = len(node_set)

    return {
        'gp': gp,
        'parent_children': parent_children,
        'facts_core': core_facts,
        'nodes_count': nodes_count
    }

def _build_parent_map(parent_children):
    """由 {父:[子...]} 生成 {子:父} 反向映射。"""
    pmap = {}
    for par, childs in parent_children.items():
        for c in childs:
            pmap[c] = par
    return pmap

def _find_grandparent(parent_children, parent):
    """已知父节点，找到其祖父（谁把该父列为孩子）。"""
    for maybe_gp, kids in parent_children.items():
        if parent in kids:
            return maybe_gp
    return None

def pick_target(parent_children):
    """
    从树中挑选一个目标叶子：
      - 必须存在祖父（父节点属于某个更高层的孩子列表）
      - 父节点至少有一个兄弟父节点
    """
    pmap = _build_parent_map(parent_children)
    candidates = []
    for leaf, parent in pmap.items():
        gp = _find_grandparent(parent_children, parent)
        if gp is None:
            continue
        siblings_parents = parent_children.get(gp, [])
        if parent in siblings_parents and len(siblings_parents) >= 2:
            candidates.append(leaf)
    if not candidates:
        return ""  # 触发unknown
    return random.choice(candidates)

def get_cousins(parent_children, target):
    """
    返回 target 的堂兄弟集合（不排序，去重保序）：
      堂兄弟 = 其父的兄弟节点的所有孩子（父不同但祖父相同）
    """
    if not target:
        return []
    pmap = _build_parent_map(parent_children)
    if target not in pmap:
        return []
    parent = pmap[target]
    gp = _find_grandparent(parent_children, parent)
    if gp is None:
        return []
    res = []
    for par in parent_children.get(gp, []):
        if par == parent:
            continue
        res.extend(parent_children.get(par, []))
    return _unique(res)

def sort_unicode(values):
    """按Unicode代码点顺序排序（与Python内置sorted一致）。"""
    if not isinstance(values, (list, tuple)):
        return []
    return sorted(values)

def gen_noise(parent_children, noise_count):
    """
    生成与解无关但为真的噪声事实：
      - 一些叶子：X没有孩子
      - 一些父节点：Y没有孙子（因叶子无子）
      - 一些兄弟事实：Z与...是兄弟节点（同一父下的孩子之间互为兄弟）
    """
    facts = []
    pmap = _build_parent_map(parent_children)
    leaves = [x for x in pmap.keys() if x not in parent_children]
    parents = [k for k, v in parent_children.items() if all((c not in parent_children) for c in v)]

    # 1) 叶子没有孩子
    random.shuffle(leaves)
    for leaf in leaves[:max(0, noise_count // 2)]:
        facts.append(f"{leaf}没有孩子")

    # 2) 父节点没有孙子
    random.shuffle(parents)
    for p in parents[:max(0, (noise_count + 1) // 2)]:
        facts.append(f"{p}没有孙子")

    # 3) 兄弟事实
    sib_facts = []
    for par, childs in parent_children.items():
        if len(childs) >= 3:
            base = random.choice(childs)
            others = [c for c in childs if c != base]
            if others:
                show = random.sample(others, min(2, len(others)))
                sib_facts.append(f"{base}与{'、'.join(show)}是兄弟节点")
    random.shuffle(sib_facts)
    for s in sib_facts[:max(0, noise_count - len(facts))]:
        facts.append(s)

    return _unique(facts[:noise_count])

def format_facts(facts_core, facts_noise):
    """
    合并并打乱核心与噪声事实，生成自然语言文本。
    """
    core_head = [facts_core[0]] if facts_core else []
    core_rest = facts_core[1:] if len(facts_core) > 1 else []
    random.shuffle(core_rest)
    shuffle_noise = facts_noise[:]
    random.shuffle(shuffle_noise)
    parts = core_head + core_rest + shuffle_noise
    return "。".join(parts) + "。"

def validate_cousins(parent_children, target, answers):
    """
    通用校验：
      - 若target无效，则answers应为空（框架会输出unknown）
      - 否则 set(answers) == set(get_cousins(...))
    """
    if not isinstance(answers, (list, tuple)):
        return False
    gold = set(get_cousins(parent_children, target))
    got = set(answers)
    return got == gold