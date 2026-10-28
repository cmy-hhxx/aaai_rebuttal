import sys, json, random, math
from typing import List, Dict, Any, Tuple, Optional

# ----------------------------
# Utilities
# ----------------------------

def rng_choice(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]

def safe_int(x):
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, int):
        return x
    raise TypeError("Expected int")

def json_dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

def gcd_list(nums):
    g = 0
    for x in nums:
        g = math.gcd(g, abs(x))
    return g

# ----------------------------
# Domain model: counting objects, focusing on "my" possessions.
# Core task: compute | (#clothing I own) - (#cars I own) |
# with lots of distracting statements about others.
# Supports multiple generation families, including a "story arithmetic" clause.
# ----------------------------

CLOTHING = [
    "夹克", "毛衣", "睡衣", "牛仔裤", "运动鞋", "领带", "帽子", "围巾", "手套", "短裤", "衬衫"
]
# We treat some as clothing consistently. "运动鞋" counts as clothing.
# "领带" could be clothing but often appears with grandma in seed; still clothing if owned by me.

CAR_MODELS = [
    ("日产", "劲客"),
    ("日产", "Armada"),
    ("沃尔沃", "XC90"),
    ("宝马", "X5"),
    ("奥迪", "A4"),
    ("马自达", "CX-90"),
    ("斯巴鲁", "傲虎"),
    ("现代", "伊兰特"),
    ("现代", "胜达"),
    ("丰田", "卡罗拉"),
]

OTHER_ITEMS = [
    "椅子", "凳子", "餐桌", "咖啡桌", "书桌", "梳妆台", "长凳",
    "教科书", "参考书", "儿童书籍", "历史书籍", "旅游指南", "漫画",
    "平板电脑", "VR头盔", "显示器", "耳机",
    "无人机", "鸟", "鸭子", "老鼠", "螃蟹", "狗",
    "草莓", "蓝莓", "橙子", "香蕉", "石榴", "火龙果", "面包果", "枣",
    "蝎子"
]

PEOPLE = ["老师", "阿姨", "朋友", "表兄弟", "奶奶", "父亲", "哥哥", "邻居", "教授", "同事", "老板", "叔叔", "母亲", "室友"]

ADJ_PHRASES = [
    "（都是全新的）", "（是我昨天买的）", "（都是古董）", "（配置很高）", "（情节很有趣）",
    "（都停在车库里）", "（都是有机的）", "（我刚购买的）"
]

def make_story_arithmetic(rng: random.Random, final_value: int) -> Tuple[str, int]:
    """
    Create a clause describing how I end up with final_value via simple +/- steps.
    Returns (text, computed_final) ensuring computed_final == final_value.
    """
    # Choose a 2-3 step narrative: start -> gain -> total -> lose -> remaining (or multiple loses/gains)
    steps = rng_choice(rng, [2, 3])
    # We'll construct backwards to ensure final.
    # Start with an initial base, then apply gains and losses.
    if steps == 2:
        # start + gain - loss = final
        start = rng.randint(1, 30)
        gain = rng.randint(20, 120)
        total = start + gain
        # choose loss so final positive
        loss = total - final_value
        if loss <= 0:
            # adjust gain so that loss positive
            gain += (final_value - total) + rng.randint(1, 20)
            total = start + gain
            loss = total - final_value
        txt = f"(我是这样拥有这{final_value}个的：最初我有{start}个，然后我又获得了{gain}个，总共有{total}个，然后我失去了{loss}个，剩下{final_value}个)"
        return txt, start + gain - loss
    else:
        # start - loss1 + gain1 - loss2 = final OR start + gain1 - loss1 - loss2 = final
        pattern = rng_choice(rng, ["-+-", "+--"])
        start = rng.randint(40, 140)
        if pattern == "-+-":
            loss1 = rng.randint(5, 40)
            after1 = start - loss1
            if after1 <= 0:
                loss1 = max(1, start - 1)
                after1 = start - loss1
            gain1 = rng.randint(10, 120)
            after2 = after1 + gain1
            loss2 = after2 - final_value
            if loss2 <= 0:
                gain1 += (final_value - after2) + rng.randint(1, 30)
                after2 = after1 + gain1
                loss2 = after2 - final_value
            txt = f"(我是这样拥有这{final_value}个的：最初我有{start}个，然后我失去了{loss1}个，剩下{after1}个，然后我又获得了{gain1}个，总共有{after2}个，然后我失去了{loss2}个，剩下{final_value}个)"
            return txt, start - loss1 + gain1 - loss2
        else:
            gain1 = rng.randint(10, 120)
            after1 = start + gain1
            loss1 = rng.randint(5, 60)
            after2 = after1 - loss1
            if after2 <= 0:
                loss1 = max(1, after1 - 1)
                after2 = after1 - loss1
            loss2 = after2 - final_value
            if loss2 <= 0:
                # increase start to allow positive loss2
                start += (final_value - after2) + rng.randint(1, 40)
                after1 = start + gain1
                after2 = after1 - loss1
                loss2 = after2 - final_value
                if loss2 <= 0:
                    gain1 += (final_value - after2) + rng.randint(1, 40)
                    after1 = start + gain1
                    after2 = after1 - loss1
                    loss2 = after2 - final_value
            txt = f"(我是这样拥有这{final_value}个的：最初我有{start}个，然后我又获得了{gain1}个，总共有{after1}个，然后我失去了{loss1}个，剩下{after2}个，然后我又失去了{loss2}个，剩下{final_value}个)"
            return txt, start + gain1 - loss1 - loss2

def render_statement(person: str, item: str, qty: int, rng: random.Random, is_me: bool) -> str:
    adj = ""
    if rng.random() < (0.45 if is_me else 0.18):
        adj = rng_choice(rng, ADJ_PHRASES)
    if is_me:
        return f"我还有{qty}个{item}{adj}。"
    else:
        # sometimes use "还有"
        verb = "还有" if rng.random() < 0.35 else "有"
        return f"我的{person}{verb}{qty}个{item}{adj}。"

def compute_answer(my_clothing_counts: Dict[str, int], my_car_counts: Dict[str, int]) -> int:
    clothing_total = sum(my_clothing_counts.values())
    car_total = sum(my_car_counts.values())
    return abs(clothing_total - car_total)

def build_explanation(my_clothing_counts: Dict[str, int], my_car_counts: Dict[str, int]) -> str:
    # Provide concise, checkable steps with category totals.
    clothing_items = sorted(my_clothing_counts.items(), key=lambda x: x[0])
    car_items = sorted(my_car_counts.items(), key=lambda x: x[0])

    clothing_total = sum(v for _, v in clothing_items)
    car_total = sum(v for _, v in car_items)
    diff = abs(clothing_total - car_total)

    parts = []
    parts.append("只统计“我拥有”的物品，并按题目定义将其分为衣物与汽车两类。")
    parts.append("衣物数量汇总：")
    parts.append(" + ".join([f"{k}{v}" for k, v in clothing_items]) + f" = {clothing_total}")
    parts.append("汽车数量汇总：")
    parts.append(" + ".join([f"{k}{v}" for k, v in car_items]) + f" = {car_total}")
    parts.append(f"两者数量差的绝对值：|{clothing_total} - {car_total}| = {diff}")
    return "\n".join(parts)

# ----------------------------
# Problem generation families
# ----------------------------

def gen_instance_family_A(rng: random.Random) -> Dict[str, Any]:
    """
    Family A: similar to seed: many lines, some 'story arithmetic' on one car/clothing count.
    Query fixed: absolute difference between my clothing and my cars.
    """
    # Decide how many my clothing types and my car models appear
    num_my_clothes = rng.randint(2, 5)
    num_my_cars = rng.randint(2, 5)

    my_clothes = rng.sample(CLOTHING, num_my_clothes)
    my_cars = rng.sample(CAR_MODELS, num_my_cars)

    my_clothing_counts = {}
    my_car_counts = {}

    # generate counts
    for it in my_clothes:
        my_clothing_counts[it] = rng.randint(5, 120)
    for brand, model in my_cars:
        name = f"{brand}{model}"
        my_car_counts[name] = rng.randint(5, 120)

    # Apply a story arithmetic clause to one of my items (clothing or car) with probability
    story_target_type = None
    if rng.random() < 0.75:
        story_target_type = rng_choice(rng, ["clothing", "car"])
        if story_target_type == "clothing":
            item = rng_choice(rng, list(my_clothing_counts.keys()))
            final = my_clothing_counts[item]
            story_text, check = make_story_arithmetic(rng, final)
            assert check == final
            # mark that item has story_text
            my_clothing_counts[item] = (final, story_text)
        else:
            item = rng_choice(rng, list(my_car_counts.keys()))
            final = my_car_counts[item]
            story_text, check = make_story_arithmetic(rng, final)
            assert check == final
            my_car_counts[item] = (final, story_text)

    # Build statements list: include my items and distractors about others and some my non-relevant items
    statements = []

    # Distractors: others own random items
    distract_n = rng.randint(14, 26)
    for _ in range(distract_n):
        person = rng_choice(rng, PEOPLE)
        item = rng_choice(rng, OTHER_ITEMS + CLOTHING)  # others may own clothing too, but irrelevant
        qty = rng.randint(3, 110)
        statements.append(render_statement(person, item, qty, rng, is_me=False))

    # My irrelevant items
    my_irrelevant_n = rng.randint(6, 14)
    for _ in range(my_irrelevant_n):
        item = rng_choice(rng, [x for x in OTHER_ITEMS if x not in CLOTHING])
        qty = rng.randint(3, 120)
        statements.append(render_statement("", item, qty, rng, is_me=True))

    # My clothing and my cars (ensure included)
    # expand tuples
    for it, val in list(my_clothing_counts.items()):
        if isinstance(val, tuple):
            qty, story = val
            statements.append(f"我还有{qty}个{it}{story}。")
            my_clothing_counts[it] = qty
        else:
            statements.append(render_statement("", it, val, rng, is_me=True))
    for it, val in list(my_car_counts.items()):
        if isinstance(val, tuple):
            qty, story = val
            statements.append(f"我还有{qty}个{it}{story}。")
            my_car_counts[it] = qty
        else:
            statements.append(render_statement("", it, val, rng, is_me=True))

    rng.shuffle(statements)

    problem = (
        "请对以下物品计数问题进行严谨分析和解答。\n\n"
        "问题描述：\n"
        + "".join(statements)
        + "\n\n具体要求：\n"
        "在本题中，将“衣物”定义为：夹克、毛衣、睡衣、牛仔裤、运动鞋、领带、帽子、围巾、手套、短裤、衬衫（若我拥有这些则计入衣物总数）。\n"
        "将“汽车”定义为：题干中以车型形式出现的车辆（例如“宝马X5”“奥迪A4”等，若我拥有则计入汽车总数）。\n"
        "只统计“我拥有”的数量，忽略其他人拥有的任何物品。\n"
        "问：我拥有的衣物总数与汽车总数之差的绝对值是多少？\n"
    )

    answer = compute_answer(my_clothing_counts, my_car_counts)
    explanation = build_explanation(my_clothing_counts, my_car_counts)

    return {"problem": problem, "answer": answer, "explanation": explanation}

def gen_instance_family_B(rng: random.Random) -> Dict[str, Any]:
    """
    Family B: Adds a constraint-style clause: some of my clothing counts are given as sums of two bags,
    and one car count given as difference between garage and sold, still fully explicit.
    """
    num_my_clothes = rng.randint(3, 6)
    num_my_cars = rng.randint(2, 4)

    my_clothes = rng.sample(CLOTHING, num_my_clothes)
    my_cars = rng.sample(CAR_MODELS, num_my_cars)

    my_clothing_counts = {}
    my_car_counts = {}

    # clothing: some direct, some decomposed
    for it in my_clothes:
        if rng.random() < 0.45:
            a = rng.randint(1, 70)
            b = rng.randint(1, 70)
            total = a + b
            my_clothing_counts[it] = total
        else:
            my_clothing_counts[it] = rng.randint(5, 130)

    # cars: one maybe described as bought then sold
    for brand, model in my_cars:
        name = f"{brand}{model}"
        my_car_counts[name] = rng.randint(4, 110)

    # Prepare statements
    statements = []
    # Others
    for _ in range(rng.randint(12, 22)):
        person = rng_choice(rng, PEOPLE)
        item = rng_choice(rng, OTHER_ITEMS + CLOTHING)
        qty = rng.randint(2, 140)
        statements.append(render_statement(person, item, qty, rng, is_me=False))

    # My irrelevant
    for _ in range(rng.randint(5, 12)):
        item = rng_choice(rng, OTHER_ITEMS)
        qty = rng.randint(2, 140)
        statements.append(render_statement("", item, qty, rng, is_me=True))

    # My clothing with decomposition rendering
    for it in my_clothes:
        total = my_clothing_counts[it]
        if rng.random() < 0.5:
            # render as two boxes summing to total (choose split)
            x = rng.randint(0, total)
            y = total - x
            statements.append(f"我有两箱{it}，第一箱{x}个，第二箱{y}个，所以我一共有{total}个{it}。")
        else:
            statements.append(render_statement("", it, total, rng, is_me=True))

    # My cars with possible sold narrative
    sold_done = False
    for name in list(my_car_counts.keys()):
        qty = my_car_counts[name]
        if (not sold_done) and rng.random() < 0.6:
            extra = rng.randint(1, 30)
            had = qty + extra
            statements.append(f"我原本有{had}辆{name}，后来卖掉了{extra}辆，所以现在我还有{qty}辆{name}。")
            sold_done = True
        else:
            statements.append(f"我还有{qty}辆{name}。")

    rng.shuffle(statements)

    problem = (
        "请阅读题干并计算所问数量。\n\n"
        "题干：\n"
        + "".join(statements)
        + "\n\n规则说明：\n"
        "1) 只统计“我”的物品数量。\n"
        "2) 衣物指：夹克、毛衣、睡衣、牛仔裤、运动鞋、领带、帽子、围巾、手套、短裤、衬衫。\n"
        "3) 汽车指：题干中以“某品牌某型号”或直接给出车型名称出现，且明确由“我”拥有的车辆数量（按辆计）。\n\n"
        "问题：我拥有的衣物总数与汽车总数之差的绝对值是多少？\n"
    )

    answer = compute_answer(my_clothing_counts, my_car_counts)
    explanation = build_explanation(my_clothing_counts, my_car_counts)
    return {"problem": problem, "answer": answer, "explanation": explanation}

# ----------------------------
# Validation
# ----------------------------

def validate_instance(inst: Dict[str, Any]) -> None:
    assert isinstance(inst, dict)
    assert isinstance(inst.get("problem"), str) and inst["problem"].strip()
    # answer can be int
    assert isinstance(inst.get("answer"), int)
    assert isinstance(inst.get("explanation"), str) and inst["explanation"].strip()
    # Basic sanity: answer non-negative
    assert inst["answer"] >= 0
    # Ensure question asks correct thing
    if "差的绝对值" not in inst["problem"] and "之差的绝对值" not in inst["problem"]:
        raise AssertionError("Problem missing absolute difference query")

def fingerprint(inst: Dict[str, Any]) -> str:
    # Avoid duplicates by hashing the problem text (stable)
    import hashlib
    return hashlib.sha256(inst["problem"].encode("utf-8")).hexdigest()

# ----------------------------
# Main generation loop
# ----------------------------

def generate(seed: int, count: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    out = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    families = [gen_instance_family_A, gen_instance_family_B]

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        fam = rng_choice(rng, families)
        try:
            inst = fam(rng)
            validate_instance(inst)
            fp = fingerprint(inst)
            if fp in seen:
                continue
            seen.add(fp)
            out.append(inst)
        except Exception as e:
            print(f"[gen_error] attempt={attempts} err={repr(e)}", file=sys.stderr)
            continue

    if len(out) < count:
        raise RuntimeError(f"Failed to generate enough instances: got {len(out)}/{count} after {attempts} attempts")

    return out

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
    except Exception as e:
        print(f"Input is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(req, dict) or "seed" not in req or "count" not in req:
        print('Expected JSON object like {"seed": int, "count": int}', file=sys.stderr)
        sys.exit(1)

    seed = req["seed"]
    count = req["count"]
    if not isinstance(seed, int) or not isinstance(count, int) or count <= 0:
        print("seed must be int and count must be positive int", file=sys.stderr)
        sys.exit(1)

    res = generate(seed, count)
    sys.stdout.write(json_dump(res))

if __name__ == "__main__":
    main()