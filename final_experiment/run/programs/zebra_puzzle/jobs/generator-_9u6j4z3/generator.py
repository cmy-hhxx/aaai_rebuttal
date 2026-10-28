import sys, json, random, itertools, math
from typing import Dict, List, Tuple, Any, Optional

# We will use z3 for robust constraint solving
from z3 import (
    Solver, Int, Distinct, And, Or, Implies, sat, Not
)

# -----------------------------
# Utilities
# -----------------------------

def jdump(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=None))

def eprint(*args):
    print(*args, file=sys.stderr)

def shuffled(rng, xs):
    xs = list(xs)
    rng.shuffle(xs)
    return xs

def sample_without_replacement(rng, xs, k):
    xs = list(xs)
    rng.shuffle(xs)
    return xs[:k]

# -----------------------------
# Zebra puzzle (Einstein's riddle) generator/solver
# Core domain: 5-house logic grid with relational constraints (left/right/next to/middle/first, etc.)
# We generate isomorphic variants by permuting labels of categories and items, while preserving the
# underlying constraint structure. This maintains reasoning skill but avoids copying the seed text.
# -----------------------------

CATEGORIES = ["国籍", "颜色", "饮料", "香烟", "宠物"]

BASE_ITEMS = {
    "国籍": ["英国人", "西班牙人", "乌克兰人", "挪威人", "日本人"],
    "颜色": ["红色", "绿色", "象牙色", "黄色", "蓝色"],
    "饮料": ["咖啡", "茶", "牛奶", "橙汁", "水"],
    "香烟": ["旧金", "酷儿", "切斯特", "幸运", "议会"],
    "宠物": ["狗", "蜗牛", "狐狸", "马", "斑马"],
}

# Base constraints expressed in terms of base item names.
# Each constraint will later be remapped by label permutations.
#
# Representation:
#   ("same", (catA, itemA), (catB, itemB))
#   ("right_of", (catA, itemA), (catB, itemB))  A immediately right of B
#   ("next_to", (catA, itemA), (catB, itemB))   adjacent either side
#   ("pos", (catA, itemA), position_index_1based)
#
BASE_CONSTRAINTS = [
    ("same", ("国籍", "英国人"), ("颜色", "红色")),
    ("same", ("国籍", "西班牙人"), ("宠物", "狗")),
    ("same", ("饮料", "咖啡"), ("颜色", "绿色")),
    ("same", ("国籍", "乌克兰人"), ("饮料", "茶")),
    ("right_of", ("颜色", "绿色"), ("颜色", "象牙色")),
    ("same", ("香烟", "旧金"), ("宠物", "蜗牛")),
    ("same", ("香烟", "酷儿"), ("颜色", "黄色")),
    ("pos", ("饮料", "牛奶"), 3),
    ("pos", ("国籍", "挪威人"), 1),
    ("next_to", ("香烟", "切斯特"), ("宠物", "狐狸")),
    ("next_to", ("香烟", "酷儿"), ("宠物", "马")),
    ("same", ("香烟", "幸运"), ("饮料", "橙汁")),
    ("same", ("国籍", "日本人"), ("香烟", "议会")),
    ("next_to", ("国籍", "挪威人"), ("颜色", "蓝色")),
]

# Query: who drinks water? who owns zebra?
BASE_QUERIES = [
    ("who_has", ("饮料", "水"), "国籍"),
    ("who_has", ("宠物", "斑马"), "国籍"),
]

def build_solver(items_map: Dict[str, List[str]], constraints, queries):
    """
    items_map: category -> list of 5 items (strings)
    constraints: list of remapped constraints (same format as BASE_CONSTRAINTS)
    queries: list of queries
    """
    # position variables: for each item in each category, an Int in 1..5
    pos = {}
    for cat, items in items_map.items():
        for it in items:
            pos[(cat, it)] = Int(f"p_{cat}_{it}")

    s = Solver()

    # domain 1..5
    for v in pos.values():
        s.add(And(v >= 1, v <= 5))

    # each category: all 5 positions are distinct
    for cat, items in items_map.items():
        s.add(Distinct([pos[(cat, it)] for it in items]))

    def p(ci):
        return pos[ci]

    for c in constraints:
        typ = c[0]
        if typ == "same":
            a, b = c[1], c[2]
            s.add(p(a) == p(b))
        elif typ == "right_of":
            a, b = c[1], c[2]
            s.add(p(a) == p(b) + 1)
        elif typ == "next_to":
            a, b = c[1], c[2]
            s.add(Or(p(a) == p(b) + 1, p(a) == p(b) - 1))
        elif typ == "pos":
            a, k = c[1], c[2]
            s.add(p(a) == k)
        else:
            raise ValueError(f"Unknown constraint type: {typ}")

    # Solve
    if s.check() != sat:
        return None, None, None

    m = s.model()

    # Extract assignment by house position: for each position 1..5, which item per category
    # We'll invert pos mapping.
    by_pos = {i: {} for i in range(1, 6)}  # pos -> {cat: item}
    for cat, items in items_map.items():
        for it in items:
            pv = m.evaluate(pos[(cat, it)]).as_long()
            by_pos[pv][cat] = it

    # Answer queries
    answers = []
    for q in queries:
        if q[0] == "who_has":
            target_attr = q[1]      # (cat, item)
            ask_cat = q[2]          # "国籍" typically
            target_pos = m.evaluate(pos[target_attr]).as_long()
            ans_item = by_pos[target_pos][ask_cat]
            answers.append(ans_item)
        else:
            raise ValueError("Unknown query")

    return m, by_pos, answers

def has_unique_solution(items_map, constraints) -> bool:
    """
    Check uniqueness of the full grid solution (up to exact labels, not symmetry).
    """
    # Build solver, get one model, then block it by requiring at least one item-position differs.
    pos = {}
    for cat, items in items_map.items():
        for it in items:
            pos[(cat, it)] = Int(f"p_{cat}_{it}")

    s = Solver()
    for v in pos.values():
        s.add(And(v >= 1, v <= 5))
    for cat, items in items_map.items():
        s.add(Distinct([pos[(cat, it)] for it in items]))

    def p(ci): return pos[ci]

    for c in constraints:
        typ = c[0]
        if typ == "same":
            a, b = c[1], c[2]
            s.add(p(a) == p(b))
        elif typ == "right_of":
            a, b = c[1], c[2]
            s.add(p(a) == p(b) + 1)
        elif typ == "next_to":
            a, b = c[1], c[2]
            s.add(Or(p(a) == p(b) + 1, p(a) == p(b) - 1))
        elif typ == "pos":
            a, k = c[1], c[2]
            s.add(p(a) == k)
        else:
            raise ValueError(f"Unknown constraint type: {typ}")

    if s.check() != sat:
        return False
    m1 = s.model()

    # Block the model
    diffs = []
    for key, v in pos.items():
        diffs.append(v != m1.evaluate(v))
    s.add(Or(diffs))

    # If still sat, not unique
    return s.check() != sat

def permute_variant(rng: random.Random):
    """
    Create a non-trivial isomorphic variant by permuting labels within each category
    and optionally renaming category display names (not necessary, but we can vary wording).
    Returns (items_map, constraints, queries, display_map) where display_map maps internal labels to rendered text.
    """
    # We'll keep category names fixed in Chinese for clarity, but permute items within each category.
    # Ensure non-identity permutation for at least 2 categories to avoid duplicates.
    items_map = {}
    perm_maps = {}
    changed = 0
    for cat in CATEGORIES:
        base = BASE_ITEMS[cat]
        perm = base[:]
        rng.shuffle(perm)
        if perm != base:
            changed += 1
        items_map[cat] = perm
        # map from base item name -> permuted item name
        perm_maps[cat] = {base[i]: perm[i] for i in range(5)}

    # Force some change if accidentally too identity-like
    if changed < 2:
        cat = rng.choice(CATEGORIES)
        base = BASE_ITEMS[cat]
        perm = base[:]
        rng.shuffle(perm)
        items_map[cat] = perm
        perm_maps[cat] = {base[i]: perm[i] for i in range(5)}

    def remap_atom(atom):
        cat, item = atom
        return (cat, perm_maps[cat][item])

    constraints = []
    for c in BASE_CONSTRAINTS:
        typ = c[0]
        if typ in ("same", "right_of", "next_to"):
            constraints.append((typ, remap_atom(c[1]), remap_atom(c[2])))
        elif typ == "pos":
            constraints.append((typ, remap_atom(c[1]), c[2]))
        else:
            raise ValueError("bad constraint")

    queries = []
    for q in BASE_QUERIES:
        if q[0] == "who_has":
            queries.append((q[0], remap_atom(q[1]), q[2]))
        else:
            raise ValueError("bad query")

    return items_map, constraints, queries

def render_problem(items_map, constraints) -> str:
    """
    Render a self-contained Chinese puzzle statement.
    """
    # For variety: shuffle clue order in rendering (logic unchanged).
    # We'll render as 5 houses in a row, positions 1..5 from left to right.
    def fmt_atom(a):
        cat, item = a
        # natural phrasing depending on category
        if cat == "国籍":
            return f"住着{item}"
        if cat == "颜色":
            return f"{item}的房子"
        if cat == "饮料":
            return f"喝{item}"
        if cat == "香烟":
            return f"抽{item}牌香烟"
        if cat == "宠物":
            return f"养{item}"
        return f"{cat}:{item}"

    # Translate constraint to sentence
    sentences = []
    for c in constraints:
        typ = c[0]
        if typ == "same":
            a, b = c[1], c[2]
            # choose a nicer linkage: "……的人/房子……"
            sentences.append(f"满足“{fmt_atom(a)}”的那一户也满足“{fmt_atom(b)}”。")
        elif typ == "right_of":
            a, b = c[1], c[2]
            sentences.append(f"满足“{fmt_atom(a)}”的那一户紧挨着在满足“{fmt_atom(b)}”的那一户右边。")
        elif typ == "next_to":
            a, b = c[1], c[2]
            sentences.append(f"满足“{fmt_atom(a)}”的那一户与满足“{fmt_atom(b)}”的那一户相邻（左右皆可）。")
        elif typ == "pos":
            a, k = c[1], c[2]
            if k == 1:
                sentences.append(f"从左到右第1户满足“{fmt_atom(a)}”。")
            elif k == 3:
                sentences.append(f"从左到右第3户满足“{fmt_atom(a)}”。")
            elif k == 5:
                sentences.append(f"从左到右第5户满足“{fmt_atom(a)}”。")
            else:
                sentences.append(f"从左到右第{k}户满足“{fmt_atom(a)}”。")
        else:
            raise ValueError("unknown")

    # Add category item lists for self-containedness
    lines = []
    lines.append("有5户人家从左到右排成一排（位置1到5）。每户各自恰好对应以下5类属性各1个，且同类属性不重复：")
    for cat in CATEGORIES:
        items = items_map[cat]
        lines.append(f"- {cat}：{', '.join(items)}")
    lines.append("已知线索如下：")
    for i, s in enumerate(sentences, 1):
        lines.append(f"{i}. {s}")
    lines.append("问题：")
    lines.append("A) 喝“水”的是哪国人？")
    lines.append("B) 养“斑马”的是哪国人？")
    lines.append("请分别给出两问的国籍答案（用“====”连接，例如：甲====乙）。")
    return "\n".join(lines)

def build_explanation(by_pos, answers) -> str:
    """
    Provide a short, checkable explanation: output the full final table.
    """
    lines = []
    lines.append("一种满足全部线索且唯一的安排如下（位置1到5从左到右）：")
    header = "位置 | 国籍 | 颜色 | 饮料 | 香烟 | 宠物"
    lines.append(header)
    lines.append("-" * len(header))
    for i in range(1, 6):
        row = by_pos[i]
        lines.append(f"{i} | {row['国籍']} | {row['颜色']} | {row['饮料']} | {row['香烟']} | {row['宠物']}")
    lines.append(f"因此：喝水的是 {answers[0]}；养斑马的是 {answers[1]}。")
    return "\n".join(lines)

# -----------------------------
# Main generation loop
# -----------------------------

def generate_one(rng: random.Random, seen_fingerprints: set, max_tries=2000):
    for _ in range(max_tries):
        items_map, constraints, queries = permute_variant(rng)

        # quick fingerprint to avoid repeats: rendered constraints as tuples
        fp = (tuple(tuple(c) for c in constraints),
              tuple((cat, tuple(items_map[cat])) for cat in CATEGORIES))
        if fp in seen_fingerprints:
            continue

        # ensure solvable and unique
        model, by_pos, answers = build_solver(items_map, constraints, queries)
        if model is None:
            continue
        if not has_unique_solution(items_map, constraints):
            continue

        problem = render_problem(items_map, constraints)
        answer = f"{answers[0]}===={answers[1]}"
        explanation = build_explanation(by_pos, answers)

        # sanity: answers must be non-empty
        if not (isinstance(answer, str) and "====" in answer):
            continue

        seen_fingerprints.add(fp)
        return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("在给定尝试次数内未能生成满足条件（可解且唯一且不重复）的题目。")

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()
    for _ in range(count):
        item = generate_one(rng, seen)
        results.append(item)

    jdump(results)

if __name__ == "__main__":
    main()