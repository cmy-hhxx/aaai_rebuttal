import sys, json, random, itertools
from collections import defaultdict, deque

# ----------------------------
# Tree model + utilities
# ----------------------------

class Tree:
    def __init__(self):
        self.parent = {}              # child -> parent
        self.children = defaultdict(list)  # parent -> [children]
        self.nodes = set()

    def add_node(self, x):
        self.nodes.add(x)

    def add_edge(self, p, c):
        # enforce single-parent tree condition
        self.add_node(p)
        self.add_node(c)
        if c in self.parent and self.parent[c] != p:
            raise ValueError(f"Node {c} already has parent {self.parent[c]}, cannot set parent {p}")
        self.parent[c] = p
        if c not in self.children[p]:
            self.children[p].append(c)

    def set_children(self, p, child_list):
        for c in child_list:
            self.add_edge(p, c)

    def get_parent(self, x):
        return self.parent.get(x)

    def get_children(self, x):
        return list(self.children.get(x, []))

    def is_leaf(self, x):
        return len(self.get_children(x)) == 0

    def get_grandchildren(self, x):
        g = []
        for c in self.get_children(x):
            g.extend(self.get_children(c))
        return g

    def get_root_candidates(self):
        # nodes that never appear as children
        return [n for n in self.nodes if n not in self.parent]

    def siblings(self, x):
        p = self.get_parent(x)
        if p is None:
            return []
        return [c for c in self.get_children(p) if c != x]

    def cousins(self, x):
        """
        '堂兄弟节点' interpreted as children of parent's siblings (first cousins).
        i.e., nodes that share the same grandparent but not the same parent.
        """
        p = self.get_parent(x)
        if p is None:
            return []
        gp = self.get_parent(p)
        if gp is None:
            return []
        cousins = []
        for uncle in self.get_children(gp):
            if uncle == p:
                continue
            cousins.extend(self.get_children(uncle))
        # exclude self just in case of malformed
        return [c for c in cousins if c != x]

    def validate_tree(self):
        # Check no cycles
        for n in list(self.nodes):
            seen = set()
            cur = n
            while cur in self.parent:
                if cur in seen:
                    raise ValueError("Cycle detected")
                seen.add(cur)
                cur = self.parent[cur]

        # Optionally: check connectedness not required (tree in prompt says tree, we can enforce single root)
        roots = self.get_root_candidates()
        # In generation we enforce exactly 1 root by construction; here just sanity
        if len(roots) != 1:
            raise ValueError(f"Expected exactly 1 root, found {len(roots)} roots: {roots[:5]}{'...' if len(roots)>5 else ''}")

    def render_facts(self, rng, style_variant=0):
        """
        Render natural language constraints describing the tree.
        We'll output a list of sentences in Chinese.
        style_variant controls phrasing variety.
        """
        sents = []
        # We'll present mixed facts:
        # 1) Some nodes have k children listed.
        # 2) Some groups described as siblings.
        # 3) Some nodes have no children / no grandchildren.
        # We ensure all referenced nodes are in the tree.
        nodes = sorted(self.nodes)
        # Choose a subset of internal nodes to describe with explicit children listing
        internal = [n for n in nodes if len(self.get_children(n)) > 0]
        leaves = [n for n in nodes if len(self.get_children(n)) == 0]

        rng.shuffle(internal)
        rng.shuffle(leaves)

        # Always describe the query-related neighborhood robustly (ensures solvability).
        # We'll fill in later in problem assembly by adding required nodes to "must_include".
        # Here render_facts takes no must_include; it returns full coverage-ish facts.
        # We'll render:
        # - For many internal nodes: list all children.
        # - For many leaves: "没有孩子" or "没有孙子" (both true for leaves).
        # - For some internal nodes: maybe "没有孙子" if depth <=1 under it.
        # - For some sibling groups: pick parent and list as siblings.

        # Describe children for most internal nodes to make it self-contained.
        # But avoid too verbose: keep within manageable length.
        max_children_facts = 14 + style_variant * 2
        max_leaf_facts = 18 + style_variant * 2
        max_sibling_facts = 10 + style_variant * 2

        internal_pick = internal[:max_children_facts]
        leaf_pick = leaves[:max_leaf_facts]

        # children facts
        for p in internal_pick:
            ch = self.get_children(p)
            if style_variant % 2 == 0:
                sents.append(f"{p}的孩子是：{', '.join(ch)}。")
            else:
                sents.append(f"{p}有{len(ch)}个孩子：{', '.join(ch)}。")

        # leaf facts
        for x in leaf_pick:
            # Randomly say no children or no grandchildren (both okay for leaf); diversify
            if rng.random() < 0.5:
                sents.append(f"{x}没有孩子。")
            else:
                sents.append(f"{x}没有孙子。")

        # sibling facts: choose some parents with >=3 children to describe siblings
        sib_parents = [p for p in internal if len(self.get_children(p)) >= 3]
        rng.shuffle(sib_parents)
        for p in sib_parents[:max_sibling_facts]:
            ch = self.get_children(p)
            if len(ch) < 3:
                continue
            # pick 3-5 of them, and phrase "A与B,C是兄弟节点"
            k = rng.randint(3, min(5, len(ch)))
            pick = rng.sample(ch, k)
            first = pick[0]
            rest = pick[1:]
            if style_variant == 0:
                sents.append(f"{first}与{', '.join(rest)}是兄弟节点。")
            elif style_variant == 1:
                sents.append(f"{first}和{', '.join(rest)}互为兄弟节点。")
            else:
                sents.append(f"在同一个父节点下，{', '.join(pick)}是兄弟节点。")

        # Some "no grandchildren" facts for nodes with depth<=1 below them
        shallow = []
        for p in internal:
            # no grandchildren means all children are leaves
            if all(len(self.get_children(c)) == 0 for c in self.get_children(p)):
                shallow.append(p)
        rng.shuffle(shallow)
        for p in shallow[:8]:
            # avoid contradicting if already "有孩子..." that's fine
            sents.append(f"{p}没有孙子。")

        rng.shuffle(sents)
        return sents


# ----------------------------
# Name pool
# ----------------------------

def make_name_pool():
    # Use a large pool of distinct Chinese item names (no punctuation that could confuse parsing)
    pool = [
        "书包","铅笔","橡皮","尺子","圆规","笔记本","字典","书架","台灯","电脑","键盘","鼠标","耳机","音箱","相机",
        "手机","平板","手表","闹钟","充电器","插线板","路由器","打印机","扫描仪","投影仪","电视","空调","风扇","加湿器",
        "扫地机器人","洗衣机","冰箱","微波炉","电饭煲","咖啡机","榨汁机","蒸笼","锅","碗","盘子","筷子","勺子","水果刀",
        "菜板","调味瓶","酱油","醋","盐罐","胡椒瓶","茶","咖啡","牛奶","果汁","矿泉水","可乐","面包","饼干","巧克力",
        "冰淇淋","香蕉","苹果","梨","葡萄","草莓","西瓜","番茄","黄瓜","土豆","胡萝卜","洋葱","大蒜","小麦","水稻",
        "花生","葵花籽","芝麻","坚果","蜂蜜","果酱","酸奶","奶酪","披萨","汉堡","寿司","饭盒","保温杯","水杯","洗漱杯",
        "牙刷","牙膏","毛巾","浴巾","沐浴露","洗发水","护发素","精华液","乳液","面霜","口红","腮红","睫毛膏","指甲油",
        "发梳","卷发棒","镜子","香水","手套","帽子","围巾","外套","T恤","衬衫","运动裤","牛仔裤","裙子","衣橱","鞋柜",
        "凉鞋","高跟鞋","运动鞋","拖鞋","雨靴","腰带","皮带","领结","领带","手帕","太阳镜","泳镜","泳帽","泳装","护膝",
        "羽毛球拍","乒乓球","网球","篮球","排球","足球","高尔夫球杆","滑板","自行车","划船机","仰卧板","哑铃","跳绳",
        "棋盘","积木","磁力积木","玩具琴","泡泡机","白板笔","胶带","回形针","订书机","文件夹","记事本夹","白板",
        "扳手","螺丝刀","锤子","钳子","铲子","锉刀","电烙铁","电钻","梯子","茶几","餐桌","吧台","休闲椅","屏风",
        "花架","兰花","牡丹","玫瑰","向日葵","榕树","橡树","松树","竹子","盆栽","花盆","园艺剪","洒水壶","水果去核器",
        "压蒜器","剃须刀","智能手表","杂志","报纸","柜子"
    ]
    # Ensure uniqueness
    uniq = []
    seen = set()
    for x in pool:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


# ----------------------------
# Generator family: cousin query in a tree
# ----------------------------

def build_random_tree_with_cousin_structure(rng, pool):
    """
    Construct a valid rooted tree, ensuring at least one node X has non-empty cousins.
    We'll also ensure answer uniqueness by querying a single node's cousin set (deterministic set).
    """
    # pick sizes
    n = rng.randint(50, 90)
    names = rng.sample(pool, n)

    T = Tree()
    for x in names:
        T.add_node(x)

    root = names[0]

    # Build backbone ensuring cousin structure:
    # root -> GP -> {P, U1, U2} ; P -> {X, S} ; U1 -> {c1,c2,...}; U2 -> {d1,...}
    # plus attach remaining nodes randomly as tree.
    # Ensure degrees moderate.
    gp = names[1]
    p = names[2]
    u1 = names[3]
    u2 = names[4]
    x = names[5]

    T.add_edge(root, gp)
    T.add_edge(gp, p)
    T.add_edge(gp, u1)
    T.add_edge(gp, u2)

    # parent p children
    s_count = rng.randint(1, 3)
    p_children = [x] + rng.sample([nm for nm in names[6:] if nm not in {gp,p,u1,u2,x}], s_count)
    for c in p_children:
        T.add_edge(p, c)

    # u1 children (cousins)
    remaining = [nm for nm in names if nm not in {root,gp,p,u1,u2} and nm not in p_children]
    u1_k = rng.randint(2, 5)
    u1_children = rng.sample(remaining, u1_k)
    for c in u1_children:
        T.add_edge(u1, c)
    remaining = [nm for nm in remaining if nm not in u1_children]

    # u2 children (cousins)
    u2_k = rng.randint(1, 4)
    u2_children = rng.sample(remaining, u2_k)
    for c in u2_children:
        T.add_edge(u2, c)
    remaining = [nm for nm in remaining if nm not in u2_children]

    # attach the rest under random existing nodes, keeping it a tree
    attachables = [root, gp, p, u1, u2] + p_children + u1_children + u2_children
    for nm in remaining:
        par = rng.choice(attachables)
        # avoid making structure too deep sometimes; but it's okay
        T.add_edge(par, nm)
        attachables.append(nm)

    T.validate_tree()

    # choose query node: x (guaranteed to have cousins)
    query = x
    cousins = T.cousins(query)
    if not cousins:
        raise RuntimeError("Construction failed: no cousins")
    return T, query


def compute_answer_and_explain(T, query):
    cousins = T.cousins(query)
    if not cousins:
        ans = "unknown"
        exp = f"无法从树中找到{query}的堂兄弟节点（父节点没有兄弟节点或兄弟节点没有孩子）。"
        return ans, exp

    # Sort by Chinese lexicographic (Python default)
    cousins_sorted = sorted(cousins)
    ans = ", ".join(cousins_sorted)

    # Explanation: show parent, grandparent, uncles, and their children
    p = T.get_parent(query)
    gp = T.get_parent(p) if p else None
    uncles = []
    if gp is not None:
        uncles = [u for u in T.get_children(gp) if u != p]
    parts = []
    parts.append(f"{query}的父节点是{p}，祖父节点是{gp}。")
    if uncles:
        parts.append(f"{p}在{gp}下的兄弟节点（叔伯节点）是：{', '.join(uncles)}。")
        for u in uncles:
            parts.append(f"{u}的孩子是：{', '.join(T.get_children(u))}。")
    parts.append(f"因此，{query}的堂兄弟节点（叔伯节点的孩子）为：{ans}。")
    exp = "\n".join(parts)
    return ans, exp


def make_problem_text(T, query, rng, lang="zh"):
    # We will provide enough constraints by listing children for all nodes up to depth 2 around query,
    # plus many additional global facts to be non-trivial.
    # Ensure self-contained: all needed parent relations for cousin calculation are explicitly present.

    # Gather neighborhood: gp, p, uncles, their children, and query siblings.
    p = T.get_parent(query)
    gp = T.get_parent(p) if p else None
    neighborhood = set([query])
    if p:
        neighborhood.add(p)
        neighborhood.update(T.get_children(p))
    if gp:
        neighborhood.add(gp)
        neighborhood.update(T.get_children(gp))
        for u in T.get_children(gp):
            neighborhood.update(T.get_children(u))

    # Create sentences that MUST include:
    must_sents = []

    def children_fact(node):
        ch = T.get_children(node)
        if len(ch) == 0:
            # leaf
            return f"{node}没有孩子。"
        # mix phrasing
        if rng.random() < 0.5:
            return f"{node}的孩子是：{', '.join(ch)}。"
        else:
            return f"{node}有{len(ch)}个孩子：{', '.join(ch)}。"

    # Add explicit children facts for neighborhood internal nodes and also for gp to show uncles.
    for node in sorted(neighborhood):
        # to avoid too many leaf "没有孩子", only include for key leaves (query, plus some)
        if node in {query, p, gp} or len(T.get_children(node)) > 0:
            must_sents.append(children_fact(node))

    # Add a few sibling facts derived from some parents in neighborhood
    if gp:
        sibs = T.get_children(gp)
        if len(sibs) >= 3:
            a = sibs[0]
            rest = sibs[1: min(len(sibs), 5)]
            must_sents.append(f"{a}与{', '.join(rest)}是兄弟节点。")
    if p:
        sibs = T.get_children(p)
        if len(sibs) >= 3:
            pick = sibs[:min(5, len(sibs))]
            must_sents.append(f"{pick[0]}与{', '.join(pick[1:])}是兄弟节点。")

    # Add some random extra facts (global) for distraction but consistent
    extra = T.render_facts(rng, style_variant=rng.randint(0, 2))
    # Avoid duplicating too much: simple set-based dedupe preserving order
    all_sents = must_sents + extra
    seen = set()
    dedup = []
    for s in all_sents:
        if s not in seen:
            dedup.append(s)
            seen.add(s)

    # Limit length
    max_total = 38
    if len(dedup) > max_total:
        # keep all must_sents, sample extras
        must_set = set(must_sents)
        must_kept = [s for s in dedup if s in must_set]
        extras = [s for s in dedup if s not in must_set]
        rng.shuffle(extras)
        dedup = must_kept + extras[: max_total - len(must_kept)]

    # Compose problem
    n_nodes = len(T.nodes)
    preface_variants = [
        f"这是一个树结构推理题：你被给定了一个有{n_nodes}个节点的树。下面给出若干关于父子关系/兄弟关系的描述：",
        f"给定一棵包含{n_nodes}个节点的树结构。已知部分节点关系如下：",
        f"你面对一棵{n_nodes}个节点的树。请根据以下关系描述进行推理："
    ]
    question = rng.choice(preface_variants)
    body = " ".join(dedup)
    ask = f"根据给定的树结构，{query}的堂兄弟节点是什么？你的最终答案必须只包含物品名称。如果有多个物品，请按字典序排列并用逗号分隔。若无法确定答案，请回答unknown。"
    return f"{question} {body} {ask}"


# ----------------------------
# Main synthesis loop
# ----------------------------

def generate_one(rng, pool, lang):
    # Try a few times to avoid accidental rendering insufficiency (should not happen).
    for _ in range(30):
        T, query = build_random_tree_with_cousin_structure(rng, pool)
        ans, exp = compute_answer_and_explain(T, query)
        problem = make_problem_text(T, query, rng, lang=lang)

        # Cross-check by brute: compute cousins purely from explicit parent pointers (already)
        # Independent-ish check: compute using grandparent children scan (same concept, but via BFS ancestor map)
        def brute_cousins(q):
            p = T.get_parent(q)
            if p is None:
                return []
            gp = T.get_parent(p)
            if gp is None:
                return []
            res = []
            for child_of_gp in T.get_children(gp):
                if child_of_gp == p:
                    continue
                res.extend(T.get_children(child_of_gp))
            return sorted([z for z in res if z != q])

        if ans != "unknown":
            a2 = ", ".join(brute_cousins(query))
            if a2 != ans:
                continue

        # Basic self-containedness heuristic: ensure the crucial facts are present as plain text:
        # the children list for gp, and for each uncle, and for p.
        # Since make_problem_text includes children facts for neighborhood internal nodes, it should.
        p = T.get_parent(query)
        gp = T.get_parent(p) if p else None
        must_phrases = []
        if p:
            must_phrases.append(p)
            # presence of a children fact line for p (contains "p的孩子是" or "p有")
            if (f"{p}的孩子是：" not in problem) and (f"{p}有" not in problem):
                continue
        if gp:
            if (f"{gp}的孩子是：" not in problem) and (f"{gp}有" not in problem):
                continue
            for u in T.get_children(gp):
                if u == p:
                    continue
                if (f"{u}的孩子是：" not in problem) and (f"{u}有" not in problem):
                    continue

        return {"problem": problem, "answer": ans if ans == "unknown" else ans, "explanation": exp}

    raise RuntimeError("Failed to generate a valid problem after many attempts")


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # optional config from wrapper (not required by protocol but provided in user message)
    # output_language already requested in the chat; keep zh default
    lang = "zh"

    pool = make_name_pool()

    results = []
    seen_problems = set()
    attempts = 0
    while len(results) < count:
        attempts += 1
        if attempts > count * 60:
            print(f"Generation failed: only {len(results)}/{count} created after {attempts} attempts", file=sys.stderr)
            break
        item = generate_one(rng, pool, lang)
        # de-dup by problem text
        if item["problem"] in seen_problems:
            continue
        seen_problems.add(item["problem"])
        results.append(item)

    if len(results) != count:
        # Hard fail to respect protocol
        raise SystemExit(f"Could not generate required count={count}, got {len(results)}")

    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()