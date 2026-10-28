# web_of_lies_1.py
# Helper functions for YAML custom_operator
import random

def to_yn_list(bools):
    """
    Convert a list of booleans (or truthy/falsy values) to a Python list of Chinese '是'/'否' strings.
    True -> '是', False -> '否'
    Returned as a Python list for easy strict equality checking.
    """
    return ['是' if bool(b) else '否' for b in bools]

def gen_chinese_names(n):
    """
    Generate n unique Chinese names from a large pool.
    If n exceeds pool size (unlikely), extend by appending numeric suffixes.
    """
    pool = [
        '张伟','王芳','李强','刘洋','陈刚','杨光','赵敏','孙文','周磊','吴静',
        '郑晓','冯雅','何方','韩梅','曹操','张丽','罗宁','唐杰','顾彬','沈倩',
        '朱晨','侯宇','董琪','邵明','熊飞','金铭','卫平','蒋岚','崔健','贾玲',
        '于峰','高原','白雪','史航','夏雨','童星','秦川','霍云','卢哲','钱坤'
    ]
    if n <= len(pool):
        return random.sample(pool, n)
    base = pool[:]
    extra = []
    idx = 1
    while len(base) + len(extra) < n:
        extra.append(f'名字{idx}')
        idx += 1
    return base + extra[:(n - len(base))]

def gen_places(n):
    """
    Generate n unique place names from a large pool.
    """
    pool = [
        '机场','电影院','办公室','书店','广场','图书馆','咖啡店','商场','银行','超市',
        '动物园','社区中心','博物馆','美术馆','火车站','地铁站','体育馆','公园','餐厅','旅馆',
        '邮局','展览中心','科技馆','实验室','会议中心','码头','港口','游乐园','学校','医院',
        '研究所','工厂','车站','看台','剧院','音乐厅','纪念馆','展销会','会客厅','天文馆'
    ]
    if n <= len(pool):
        return random.sample(pool, n)
    base = pool[:]
    extra = []
    idx = 1
    while len(base) + len(extra) < n:
        extra.append(f'地点{idx}')
        idx += 1
    return base + extra[:(n - len(base))]

def gen_perm_mapping(places, names):
    """
    Generate a one-to-one mapping from places to occupants (names) by shuffling names.
    Assumes len(places) == len(names).
    Return occupants list aligned with places.
    """
    names_copy = names[:]
    random.shuffle(names_copy)
    return names_copy

def build_mapping_desc(places, occupants):
    """
    Build a display string like '书店-张伟、电影院-王芳、...'
    """
    pairs = [f'{places[i]}-{occupants[i]}' for i in range(len(places))]
    return '、'.join(pairs)

def gen_prop_keys(names, k):
    """
    Generate k unique proposition keys tied to random names and attributes.
    Format: '<name>_<attr>'.
    """
    if k <= 0:
        return []
    attr_pool = ['友好','守时','可信','谨慎','乐于助人','严谨','耐心','果敢','细心','热心']
    chosen_names = random.sample(names, min(k, len(names)))
    chosen_attrs = random.sample(attr_pool, min(k, len(attr_pool)))
    while len(chosen_attrs) < len(chosen_names):
        chosen_attrs.append(random.choice(attr_pool))
    return [f'{chosen_names[i]}_{chosen_attrs[i]}' for i in range(len(chosen_names))]

def gen_target_types(m):
    """
    Generate a list of target types 'place' or 'person' of length m.
    Balanced and randomized composition.
    """
    types = []
    if m >= 2:
        types = ['place','person']
        m -= 2
    for _ in range(m):
        types.append(random.choice(['place','person']))
    random.shuffle(types)
    return types

def pick_targets(names, places, types):
    """
    Pick targets according to types (without replacement within each category).
    Return a list of names or place names aligned with 'types' order.
    """
    place_count = sum(1 for t in types if t == 'place')
    person_count = sum(1 for t in types if t == 'person')
    chosen_places = random.sample(places, min(place_count, len(places))) if place_count > 0 else []
    chosen_persons = random.sample(names, min(person_count, len(names))) if person_count > 0 else []
    pi, ni = 0, 0
    targets = []
    for t in types:
        if t == 'place':
            targets.append(chosen_places[pi])
            pi += 1
        else:
            targets.append(chosen_persons[ni])
            ni += 1
    return targets

def render_targets_desc(types, targets):
    """
    Render numbered lines describing query targets.
    """
    lines = []
    for i, (t, x) in enumerate(zip(types, targets), start=1):
        if t == 'place':
            lines.append(f'{i}) 在{x}的人说的是真话吗？')
        else:
            lines.append(f'{i}) {x}说的是真话吗？')
    return '\n'.join(lines)

def to_codes(types):
    """将 ['place','person',...] 转换为 [0,1,...]，place->0, person->1"""
    return [0 if t == 'place' else 1 for t in types]

# --------------------------
# Phrase generators (desc variations) — all end with '。'
# --------------------------
def say_person_on_place(person, place, is_true):
    verb = random.choice(['说','称','表示','强调'])
    polarity = '在说真话' if is_true else '在讲谎'
    return f'{person}{verb}“在{place}的人{polarity}”。'

def say_place_on_person(place, person, is_true):
    verb = random.choice(['说','提到','表示'])
    polarity = '在说真话' if is_true else '在讲谎'
    return f'在{place}的人{verb}“{person}{polarity}”。'

def say_place_on_place(place_a, place_b, is_true):
    verb = random.choice(['说','称','表示'])
    polarity = '在说真话' if is_true else '在讲谎'
    return f'在{place_a}的人{verb}“在{place_b}的人{polarity}”。'

def say_person_on_person(p_a, p_b, is_true):
    verb = random.choice(['说','认为','称','表示'])
    polarity = '在说真话' if is_true else '在讲谎'
    return f'{p_a}{verb}“{p_b}{polarity}”。'

def say_on_prop(actor_type, actor_value, prop_key, is_true):
    verb = random.choice(['说','称','表示'])
    pol = '为真' if is_true else '为假'
    if actor_type == 'person':
        return f'{actor_value}{verb}“关于{prop_key}的命题{pol}”。'
    else:
        return f'在{actor_value}的人{verb}“关于{prop_key}的命题{pol}”。'

# --------------------------
# Global rule picking and rendering
# --------------------------
def pick_global_rule_type(name_num, prop_num):
    """
    Prefer 'exact_k' to tighten the space; allow 'balanced_half' when feasible.
    """
    choices = []
    weights = []
    choices.append('exact_k')
    weights.append(0.7)
    if (name_num // 2) <= prop_num and name_num >= 6:
        choices.append('balanced_half')
        weights.append(0.3)
    return random.choices(choices, weights=weights, k=1)[0]

def render_global_rules_desc(rule_type, k):
    if rule_type == 'exact_k':
        return f'恰有{k}名说真话者。'
    elif rule_type == 'balanced_half':
        return '说真话者的人数恰为总人数的一半（若总人数为奇数，则向下取整）。'
    return '恰有1名说真话者。'

# --------------------------
# Proposition ownership helper
# --------------------------
def prop_key_owner(prop_key):
    if not isinstance(prop_key, str):
        return str(prop_key)
    if '_' in prop_key:
        return prop_key.split('_', 1)[0]
    return prop_key

def render_owner_link_desc(prop_key, link_type):
    owner = prop_key_owner(prop_key)
    if link_type == 'implies_true':
        return f'若关于{prop_key}的命题为真，则{owner}在说真话。'
    elif link_type == 'implies_false':
        return f'若关于{prop_key}的命题为假，则{owner}在讲谎。'
    elif link_type == 'equiv':
        return f'关于{prop_key}的命题真假与{owner}是否在说真话等价。'
    return f'关于{prop_key}的命题与{owner}存在关联。'

# --------------------------
# Zones and advanced constraints helpers
# --------------------------
def gen_zone_assign(places, znum):
    """
    Partition places into znum zones labeled '区域A','区域B','区域C',... (balanced as much as possible).
    Return a list zone_assign where zone_assign[i] is the zone name for places[i].
    """
    labels = ['区域A','区域B','区域C','区域D','区域E']
    znum = max(2, min(3, int(znum)))
    zones = labels[:znum]
    n = len(places)
    idxs = list(range(n))
    random.shuffle(idxs)
    chunks = [[] for _ in range(znum)]
    for i, idx in enumerate(idxs):
        chunks[i % znum].append(idx)
    assign = [''] * n
    random.shuffle(zones)
    for z_i, chunk in enumerate(chunks):
        for idx in chunk:
            assign[idx] = zones[z_i]
    return assign

def get_zones(zone_assign):
    """
    Get unique zones in the order of first appearance.
    """
    seen = set()
    zones = []
    for z in zone_assign:
        if z not in seen:
            zones.append(z)
            seen.add(z)
    return zones

def build_zone_desc(places, zone_assign, zones):
    """
    Render zones description: '区域A: 书店、电影院；区域B: ...'
    """
    by_zone = {z: [] for z in zones}
    for p, z in zip(places, zone_assign):
        by_zone[z].append(p)
    parts = []
    for z in zones:
        parts.append(f'{z}: ' + '、'.join(by_zone[z]))
    return '；'.join(parts)

def get_places_in_zone(places, zone_assign, zone_name):
    """
    Return the list of places belonging to 'zone_name'.
    """
    return [p for p, z in zip(places, zone_assign) if z == zone_name]

def pick_focus_zone(zones):
    """
    Randomly pick one zone as focus zone for a count constraint.
    """
    return random.choice(zones) if zones else ''

def pick_zone_truth_target(zone_places, prop_num):
    """
    Pick an integer in [1, min(len(zone_places)-1, prop_num)] if len>1, else 1.
    """
    m = len(zone_places)
    if m <= 1:
        return 1
    max_target = min(m - 1, int(prop_num))
    max_target = max(1, max_target)
    return random.randint(1, max_target)

def render_zone_count_desc(zone_name, target):
    """
    Text for zone truth-count constraint.
    """
    return f'{zone_name}内的“在该地点的人在说真话”的地点数量恰为{target}。'

def pick_anchor_p1(names):
    return random.choice(names)

def pick_anchor_p2(names, p1):
    candidates = [x for x in names if x != p1]
    return random.choice(candidates) if candidates else p1

def pick_anchor_place(places):
    return random.choice(places)

def render_anchor_rules_desc(p1, p2, pl1):
    return f'{p1}的真假与“{p2}与在{pl1}的人中恰好一方在说真话”这一命题等价。'

def pick_triplet(names):
    if len(names) >= 3:
        return random.sample(names, 3)
    base = names[:]
    while len(base) < 3:
        base.append(random.choice(names))
    return base

def render_triplet_desc(triplet, target):
    return f'在{triplet[0]}、{triplet[1]}、{triplet[2]}三人中，恰有{target}人在说真话。'

def render_counts_equal_desc():
    return '说真话者的总数与为真的命题总数相等。'

# --------------------------
# Feasible truth_k picker for exact_k mode
# --------------------------
def pick_truth_k(name_num, prop_num, zone_size, zone_target):
    """
    Choose a feasible total number of truth-tellers k for exact_k mode.
    """
    outside = max(0, int(name_num) - int(zone_size))
    lo = max(1, int(zone_target))
    hi = min(int(prop_num), int(zone_target) + outside)
    if hi < lo:
        lo, hi = 1, int(prop_num)
    return random.randint(lo, hi)

# --------------------------
# Pair builder to avoid trivial person-place self-mapping in clues
# --------------------------
def build_person_place_pairs(names, places, occupants):
    """
    Build list of (person, place) pairs such that person != occupant(place).
    occupants is aligned with places: occupants[i] is the occupant of places[i].
    """
    pairs = []
    for i, pl in enumerate(places):
        occ = occupants[i]
        for person in names:
            if person != occ:
                pairs.append((person, pl))
    random.shuffle(pairs)
    return pairs

# --------------------------
# Safe person/person and place/place pairs for deeper logic
# --------------------------
def build_safe_person_pairs(names, anchor_p1, anchor_p2, triplet):
    """
    Build person-person pairs (a,b) with a!=b, excluding any pair that touches anchor_p1/anchor_p2,
    and excluding pairs where both a and b are inside the triplet to avoid trivial resolution.
    """
    pairs = []
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                continue
            if a in (anchor_p1, anchor_p2) or b in (anchor_p1, anchor_p2):
                continue
            if (a in triplet) and (b in triplet):
                continue
            pairs.append((a, b))
    random.shuffle(pairs)
    return pairs

def build_safe_place_pairs(places, focus_zone_places, anchor_pl1):
    """
    Build place-place pairs (pa,pb) with pa!=pb, excluding anchor place,
    and excluding pairs where both pa and pb are in the focus zone (to avoid immediate zone deduction).
    """
    focus_set = set(focus_zone_places)
    pairs = []
    for i, pa in enumerate(places):
        for j, pb in enumerate(places):
            if i == j:
                continue
            if pa == anchor_pl1 or pb == anchor_pl1:
                continue
            if pa in focus_set and pb in focus_set:
                continue
            pairs.append((pa, pb))
    random.shuffle(pairs)
    return pairs

def pick_chain_type():
    """Randomly choose positive ('pos') or negative ('neg') chain."""
    return random.choice(['pos', 'neg'])

def pick_one_pair(pairs):
    """Pick a single pair (a,b) from a non-empty pairs list."""
    if not pairs:
        return ('', '')
    return random.choice(pairs)

def render_chain_desc_person(a, b, ctype):
    if ctype == 'pos':
        return f'{a}的陈述若为真，则{b}也在说真话。'
    else:
        return f'{a}的陈述若为真，则{b}在讲谎。'

def render_chain_desc_place(a, b, ctype):
    if ctype == 'pos':
        return f'若在{a}的人在说真话，则在{b}的人也在说真话。'
    else:
        return f'若在{a}的人在说真话，则在{b}的人在讲谎。'

# --------------------------
# NEW: Safe person-prop and place-prop pairs to avoid redundancy/visible clues
# --------------------------
def build_safe_person_prop_pairs(names, prop_keys):
    """
    Build list of (person, prop_key) pairs such that prop_key_owner(prop_key) != person.
    Avoids trivial tautologies when combined with owner-equivalence constraints.
    """
    pairs = []
    for person in names:
        for key in prop_keys:
            if prop_key_owner(key) != person:
                pairs.append((person, key))
    random.shuffle(pairs)
    return pairs

def build_safe_place_prop_pairs(places, prop_keys, occupants):
    """
    Build list of (place, prop_key) pairs such that prop_key_owner(prop_key) != occupant(place).
    Avoids immediate collisions with map_place_truth.
    """
    pairs = []
    for i, place in enumerate(places):
        occ = occupants[i]
        for key in prop_keys:
            if prop_key_owner(key) != occ:
                pairs.append((place, key))
    random.shuffle(pairs)
    return pairs