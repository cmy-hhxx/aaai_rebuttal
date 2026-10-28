import sys, json, random
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any

# ---------- Domain definitions ----------
SIZES = ["超超小", "超小", "小", "中", "大", "超大", "超超大"]
MATERIALS = ["布", "纸", "钛", "金属", "陶瓷", "玻璃", "混凝土", "木头"]
SMELLS = ["烤面包", "香草", "巧克力", "燃烧的木头", "咖啡", "大蒜", "玫瑰", "薄荷"]
ORIGINS = ["意大利", "德国", "葡萄牙", "加拿大", "墨西哥", "俄罗斯", "土耳其", "日本", "法国", "西班牙"]
TYPES = ["灯", "铅笔", "瓶子", "鞋", "尺子", "碗", "垃圾桶", "钥匙", "杯子", "书"]
COLORS = ["金色", "黄色", "黑色", "米色", "蓝色", "红色", "绿色", "白色"]

# For nicer Chinese rendering
def cn_join(items: List[str], sep="，", last="或") -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return sep.join(items[:-1]) + f"{last}" + items[-1]

@dataclass(frozen=True)
class Item:
    size: str
    origin: str
    material: str
    smell: str
    obj_type: str
    color: str

def item_to_text(it: Item) -> str:
    # Example: "一个大尺寸的意大利产的由布制成的散发烤面包气味的灯（颜色：金色）"
    return f"一个{it.size}尺寸的{it.origin}产的由{it.material}制成的散发{it.smell}气味的{it.obj_type}"

def deep_copy_items(items: List[Item]) -> List[Item]:
    # Items are frozen dataclass; just return list copy
    return list(items)

# ---------- Transformations ----------
def transform_glass(items: List[Item], new_color: str, new_smell: str) -> List[Item]:
    out = []
    for it in items:
        if it.material == "玻璃":
            out.append(Item(it.size, it.origin, it.material, new_smell, it.obj_type, new_color))
        else:
            out.append(it)
    return out

def swap_origin(items: List[Item], origin_target: str, replacement_size: str, replacement_material: str, rng: random.Random) -> Tuple[List[Item], int]:
    """
    Replace all items whose origin == origin_target with same count of items
    that have given size and material. Other attributes (origin/smell/type/color)
    are randomized but consistent and explicit in final state.
    """
    survivors = []
    replaced_count = 0
    for it in items:
        if it.origin == origin_target:
            replaced_count += 1
        else:
            survivors.append(it)
    new_items = []
    for _ in range(replaced_count):
        origin = rng.choice([o for o in ORIGINS if o != origin_target])
        smell = rng.choice(SMELLS)
        obj_type = rng.choice(TYPES)
        color = rng.choice(COLORS)
        new_items.append(Item(replacement_size, origin, replacement_material, smell, obj_type, color))
    return survivors + new_items, replaced_count

def duplicate_size(items: List[Item], size_target: str, size_copy: str, color_copy: str) -> Tuple[List[Item], int]:
    """
    For each item with size == size_target, replace it by two copies:
    - one copy changes size to size_copy (other attrs same)
    - the other copy changes color to color_copy (other attrs same)
    Returns (new_items, number_of_originals_duplicated)
    """
    out = []
    dup = 0
    for it in items:
        if it.size == size_target:
            dup += 1
            out.append(Item(size_copy, it.origin, it.material, it.smell, it.obj_type, it.color))
            out.append(Item(it.size, it.origin, it.material, it.smell, it.obj_type, color_copy))
        else:
            out.append(it)
    return out, dup

# ---------- Counting / verification ----------
def predicate_or(it: Item, conditions: List[Tuple[str, str]]) -> bool:
    # conditions list like [("material","陶瓷"), ("size","超小"), ...]
    for k, v in conditions:
        if getattr(it, k) == v:
            return True
    return False

def count_satisfy(items: List[Item], conditions: List[Tuple[str, str]]) -> int:
    return sum(1 for it in items if predicate_or(it, conditions))

def summarize_steps(initial: List[Item], after1: List[Item], after2: List[Item], after3: List[Item],
                    glass_rule: Tuple[str, str], swap_rule: Tuple[str, str, str], dup_rule: Tuple[str, str, str],
                    conditions: List[Tuple[str, str]]) -> str:
    new_color, new_smell = glass_rule
    origin_target, rep_size, rep_mat = swap_rule
    size_target, size_copy, color_copy = dup_rule

    # Step-wise counts to give a concrete, checkable explanation
    def cnt(items: List[Item]) -> int:
        return count_satisfy(items, conditions)

    # Provide also how many were affected by each operation (computed by comparing or counting)
    affected_glass_before = sum(1 for it in initial if it.material == "玻璃")
    affected_swap_before = sum(1 for it in after1 if it.origin == origin_target)
    affected_dup_before = sum(1 for it in after2 if it.size == size_target)

    lines = []
    lines.append("解题思路：按顺序执行三次变化，并在每一步统计满足条件的物品数量（条件为“以下任一成立”："
                 + "，".join([f"{'材质' if k=='material' else '尺寸' if k=='size' else '颜色' if k=='color' else '气味' if k=='smell' else '产地'}是{v}" for k, v in conditions])
                 + "）。")
    lines.append(f"1）初始共有{len(initial)}件；其中材质为玻璃的有{affected_glass_before}件。初始满足条件的有{cnt(initial)}件。")
    lines.append(f"2）变化一：所有玻璃制品颜色→{new_color}、气味→{new_smell}。变化后满足条件的有{cnt(after1)}件。")
    lines.append(f"3）变化二：把所有{origin_target}产地的物品全部换成“{rep_size}尺寸且材质为{rep_mat}”的新物品（数量相同）。被替换的共有{affected_swap_before}件。变化后满足条件的有{cnt(after2)}件。")
    lines.append(f"4）变化三：把所有{size_target}尺寸的物品用两个副本替换：一个尺寸变为{size_copy}，另一个颜色变为{color_copy}。被替换的原物品共有{affected_dup_before}件。最终共有{len(after3)}件，满足条件的有{cnt(after3)}件。")
    lines.append("最终答案即第4步统计值。")
    return "\n".join(lines)

# ---------- Instance generation ----------
def gen_initial_items(rng: random.Random, n: int) -> List[Item]:
    items = []
    # Ensure diversity and controllability:
    # We'll sample attributes with mild constraints to avoid too many duplicates.
    used = set()
    attempts = 0
    while len(items) < n and attempts < 5000:
        attempts += 1
        size = rng.choice(SIZES)
        origin = rng.choice(ORIGINS)
        material = rng.choice(MATERIALS)
        smell = rng.choice(SMELLS)
        obj_type = rng.choice(TYPES)
        color = rng.choice([c for c in COLORS if c != "米色"])  # keep beige special for later steps
        key = (size, origin, material, smell, obj_type, color)
        if key in used:
            continue
        used.add(key)
        items.append(Item(size, origin, material, smell, obj_type, color))
    if len(items) < n:
        raise RuntimeError("生成初始物品失败：无法在尝试上限内生成足够多的互异物品。")
    return items

def assign_color_blocks(items: List[Item], rng: random.Random) -> List[Item]:
    """
    Assign colors in blocks like: first a items -> c1, next b -> c2, rest -> c3.
    Ensures all are from COLORS excluding 米色 (reserved for step 3 copy).
    """
    n = len(items)
    c1, c2, c3 = rng.sample([c for c in COLORS if c != "米色"], 3)
    # block sizes: a>=2, b>=2, rest>=2 if possible
    if n < 6:
        a = max(1, n // 3)
        b = max(1, (n - a) // 2)
    else:
        a = rng.randint(2, n - 4)
        b = rng.randint(2, n - a - 2)
    out = []
    for i, it in enumerate(items):
        if i < a:
            col = c1
        elif i < a + b:
            col = c2
        else:
            col = c3
        out.append(Item(it.size, it.origin, it.material, it.smell, it.obj_type, col))
    return out

def render_problem(initial: List[Item],
                   color_block_desc: str,
                   glass_rule: Tuple[str, str],
                   swap_rule: Tuple[str, str, str],
                   dup_rule: Tuple[str, str, str],
                   query_conditions: List[Tuple[str, str]],
                   output_language: str = "zh") -> str:
    # Only zh supported per user config; keep parameter for extensibility.
    new_color, new_smell = glass_rule
    origin_target, rep_size, rep_mat = swap_rule
    size_target, size_copy, color_copy = dup_rule

    # list items in one paragraph, comma-separated
    item_texts = [item_to_text(it) for it in initial]
    items_sentence = "，".join(item_texts)

    cond_texts = []
    for k, v in query_conditions:
        if k == "material":
            cond_texts.append(f"材质是{v}")
        elif k == "size":
            cond_texts.append(f"尺寸是{v}")
        elif k == "color":
            cond_texts.append(f"颜色是{v}")
        elif k == "smell":
            cond_texts.append(f"气味是{v}")
        elif k == "origin":
            cond_texts.append(f"产地是{v}")
        else:
            cond_texts.append(f"{k}是{v}")
    query_text = "或".join(cond_texts)

    problem = (
        "我在整理一批带有多种属性（尺寸、产地、材质、气味、类别、颜色）的物品，并按顺序经历了三次变化。\n"
        f"最初我有{len(initial)}个物品，分别是：{items_sentence}。\n"
        f"这些物品的颜色按顺序分段给出：{color_block_desc}。\n"
        f"变化一：对当前收藏中所有“材质为玻璃”的物品，把颜色改为{new_color}，并把气味改为{new_smell}。\n"
        f"变化二：把当前收藏中所有“产地为{origin_target}”的物品全部换掉，改为同等数量的新物品；每个新物品都满足“尺寸为{rep_size}且材质为{rep_mat}”，其余属性保持为某些确定值（可视为新的物品）。\n"
        f"变化三：把当前收藏中所有“尺寸为{size_target}”的物品用两个副本替换：一个副本把尺寸改为{size_copy}（其它属性不变），另一个副本把颜色改为{color_copy}（其它属性不变）。\n\n"
        f"问题：在最终收藏中，有多少物品满足以下任一条件：{query_text}？\n"
        "请严格按变化顺序追踪并统计。"
    )
    return problem

def build_color_block_desc(n: int, a: int, b: int, c1: str, c2: str, c3: str) -> str:
    # "前a个是X色，接下来的b个是Y色，其余(n-a-b)个是Z色。"
    c = n - a - b
    parts = []
    parts.append(f"前{a}个是{c1}")
    parts.append(f"接下来的{b}个是{c2}")
    parts.append(f"其余{c}个是{c3}")
    return "，".join(parts) + "。"

def reconstruct_color_blocks(items: List[Item]) -> Tuple[int, int, str, str, str]:
    """
    Detect block sizes/colors from items (which we assigned in exact blocks).
    Returns a,b,c1,c2,c3.
    """
    colors = [it.color for it in items]
    n = len(colors)
    # find first change
    c1 = colors[0]
    i = 0
    while i < n and colors[i] == c1:
        i += 1
    a = i
    if a == n:
        # degenerate, shouldn't happen
        return n, 0, c1, c1, c1
    c2 = colors[a]
    j = a
    while j < n and colors[j] == c2:
        j += 1
    b = j - a
    c3 = colors[j] if j < n else c2
    return a, b, c1, c2, c3

def gen_one(rng: random.Random, idx: int, output_language: str) -> Dict[str, Any]:
    # Sizes for the set
    n = rng.randint(14, 26)

    # Step rules (parameterized)
    glass_new_color = rng.choice(["金色", "黑色", "白色", "蓝色"])
    glass_new_smell = rng.choice([s for s in SMELLS if s != "大蒜"])  # keep garlic sometimes only in query
    glass_rule = (glass_new_color, glass_new_smell)

    origin_target = rng.choice(ORIGINS)
    rep_size = rng.choice(["超大", "大", "中"])
    rep_mat = rng.choice(["布", "纸", "金属", "木头"])
    swap_rule = (origin_target, rep_size, rep_mat)

    size_target = rng.choice(["超超小", "超小"])
    size_copy = "小"
    color_copy = "米色"
    dup_rule = (size_target, size_copy, color_copy)

    # Query conditions: OR over 4~5 attributes, mixing types.
    # Ensure includes at least one from each category across dataset sometimes.
    candidates = [
        ("material", "陶瓷"),
        ("material", "玻璃"),
        ("size", "超小"),
        ("size", "超超小"),
        ("size", "小"),
        ("color", "米色"),
        ("smell", "大蒜"),
        ("smell", "咖啡"),
        ("origin", "俄罗斯"),
        ("origin", "德国"),
    ]
    rng.shuffle(candidates)
    k = rng.randint(4, 5)
    query_conditions = candidates[:k]
    # Make sure "米色" is included sometimes (to make step 3 relevant)
    if rng.random() < 0.6 and ("color", "米色") not in query_conditions:
        # replace last one
        query_conditions[-1] = ("color", "米色")

    # Generate initial items
    initial = gen_initial_items(rng, n)
    initial = assign_color_blocks(initial, rng)
    a, b, c1, c2, c3 = reconstruct_color_blocks(initial)
    color_block_desc = build_color_block_desc(n, a, b, c1, c2, c3)

    # Apply transformations
    after1 = transform_glass(initial, glass_rule[0], glass_rule[1])
    after2, _rep = swap_origin(after1, swap_rule[0], swap_rule[1], swap_rule[2], rng)
    after3, _dup = duplicate_size(after2, dup_rule[0], dup_rule[1], dup_rule[2])

    # Cross-check by two different computations:
    # Path A: direct predicate count
    ans_a = count_satisfy(after3, query_conditions)

    # Path B: enumerate and manually check via set of indices meeting any condition (independent style)
    idx_set = set()
    for i_it, it in enumerate(after3):
        ok = False
        for kf, val in query_conditions:
            if getattr(it, kf) == val:
                ok = True
                break
        if ok:
            idx_set.add(i_it)
    ans_b = len(idx_set)
    if ans_a != ans_b:
        raise RuntimeError("交叉核验失败：两条统计路径不一致。")

    problem = render_problem(initial, color_block_desc, glass_rule, swap_rule, dup_rule, query_conditions, output_language)
    explanation = summarize_steps(initial, after1, after2, after3, glass_rule, swap_rule, dup_rule, query_conditions)

    return {
        "problem": problem,
        "answer": ans_a,
        "explanation": explanation
    }

def main():
    data = sys.stdin.read()
    try:
        inp = json.loads(data)
    except Exception as e:
        print(f"输入不是合法JSON：{e}", file=sys.stderr)
        sys.exit(1)

    seed = int(inp.get("seed", 0))
    count = int(inp.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    # Output language is fixed by user request in this run; keep default zh.
    output_language = "zh"

    rng = random.Random(seed)
    results = []
    seen = set()

    # bounded resampling
    max_attempts = count * 50
    attempts = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            obj = gen_one(rng, len(results), output_language)
        except RuntimeError as e:
            # resample
            continue

        sig = (obj["problem"], json.dumps(obj["answer"], ensure_ascii=False))
        if sig in seen:
            continue
        seen.add(sig)
        results.append(obj)

    if len(results) < count:
        print(f"生成失败：在{max_attempts}次尝试内只生成了{len(results)}题（目标{count}题）。", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()