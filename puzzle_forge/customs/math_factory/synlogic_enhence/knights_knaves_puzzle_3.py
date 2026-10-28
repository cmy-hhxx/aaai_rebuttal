# knights_knaves_puzzle_1.py
import random

# 足够大的姓名池，保证较强的去重与多样性
_MASTER_NAMES = [
    'Ethan','Benjamin','Isabella','Zoey','Joseph','Henry','Luke','Lily','Olivia','Mason',
    'Sophia','Noah','Ava','William','Emma','James','Charlotte','Michael','Amelia','Alexander',
    'Mia','Daniel','Harper','Matthew','Evelyn','Jackson','Abigail','Logan','Emily','Elijah',
    'Elizabeth','Aiden','Sofia','Samuel','Avery','David','Ella','Josephine','Grace','Chloe',
    'Anthony','Victoria','Andrew','Madison','Joshua','Scarlett','Aria','Gabriel','Hannah'
]

def pick_names(n):
    """
    从姓名池中无放回抽取 n 个唯一名字。
    """
    if n > len(_MASTER_NAMES):
        raise ValueError('Requested more names than available in the master pool.')
    return random.sample(_MASTER_NAMES, n)

def format_names(names):
    """
    将名字列表用逗号拼接用于题干展示。
    """
    return ', '.join(names)

def to_2d_sorted(knaves, knights):
    """
    返回 [[按字母序的骗子列表],[按字母序的骑士列表]]。
    """
    return [sorted(knaves), sorted(knights)]

def render_answer(ans):
    """
    将二维列表答案转为字符串（强制标准格式：单引号、无空格，用于严格机判）。
    例如：[['A','B'],['C','D']]
    """
    def pack(lst):
        return '[' + ','.join([f"'{x}'" for x in lst]) + ']'
    return '[' + ','.join([pack(ans[0]), pack(ans[1])]) + ']'

def _has_faction_template(pool):
    """
    判断模板池中是否包含至少一条阵营相关模板。
    阵营相关模板集合：{8, 11, 7, 9, 10}
    """
    faction_templates = {8, 11, 7, 9, 10}
    return any(t in faction_templates for t in (pool or []))

def choose_template_pool(min_k=3, max_k=6, max_template_id=12):
    """
    从 [0..max_template_id-1] 的模板编号中选择一个大小在 [min_k, max_k] 的子集。
    稳健性策略：
      - 重模板 heavy_set = {7,9,10}，最多纳入 1 个，且概率降低至 0.4。
      - 至少保证一条阵营相关模板（优先选择轻量 8 或 11）。
      - 至少保证一条身份类模板（如 {0,1,2,3,6}）。
    """
    if max_template_id <= 0:
        return []
    all_ids = list(range(0, max_template_id))
    heavy_set = {7, 9, 10}
    faction_all = {8, 11, 7, 9, 10}
    faction_light = [8, 11]  # 轻量阵营模板优先
    identity_set = {0, 1, 2, 3, 6}  # 轻量身份模板集合

    normal_ids = [i for i in all_ids if i not in heavy_set]
    min_k = max(1, min_k)
    max_k = max(min_k, min(max_k, len(all_ids)))
    k = random.randint(min_k, max_k)

    heavy_k = 0
    if len(heavy_set) > 0 and random.random() < 0.4:
        heavy_k = 1
    heavy_ids_chosen = random.sample(list(heavy_set), heavy_k) if heavy_k > 0 else []
    remaining_k = max(0, k - heavy_k)
    normal_ids_chosen = random.sample(normal_ids, min(remaining_k, len(normal_ids)))

    pool = sorted(heavy_ids_chosen + normal_ids_chosen)

    # 保证至少一条阵营模板
    if not _has_faction_template(pool):
        cands_f = [t for t in faction_light if t in all_ids]
        if cands_f:
            pool = sorted(set(pool + [random.choice(cands_f)]))

    # 保证至少一条身份模板
    if not any(t in identity_set for t in pool):
        cands_i = [t for t in identity_set if t in all_ids]
        if cands_i:
            pool = sorted(set(pool + [random.choice(cands_i)]))

    # 若长度超过 k，则移除非关键项（优先移除非阵营/非身份模板），直至长度为 k
    def is_key(t):
        return (t in faction_all) or (t in identity_set)
    while len(pool) > k:
        non_key = [x for x in pool if not is_key(x)]
        if non_key:
            drop = random.choice(non_key)
            pool.remove(drop)
        else:
            # 若全为关键项，随机移除一个，但确保仍保留至少一个阵营和一个身份模板
            drop = random.choice(pool)
            pool.remove(drop)
            if not _has_faction_template(pool):
                pool = sorted(set(pool + [random.choice(faction_light)]))
            if not any(t in identity_set for t in pool):
                pool = sorted(set(pool + [random.choice(list(identity_set))]))
    # 若长度小于 k，补位
    if len(pool) < k:
        rest = [i for i in normal_ids if i not in pool]
        need = k - len(pool)
        if need > 0 and rest:
            pool += random.sample(rest, min(need, len(rest)))
            pool = sorted(pool)
    return pool

def choose_extra_rule_pool(min_k=1, max_k=3, max_rule_id=7, templates_pool=None):
    """
    从 [0..max_rule_id-1] 的规则编号中选择一个大小在 [min_k, max_k] 的子集。
    稳健性策略：
      - 重规则 heavy_rules = {3, 4, 6}，最多纳入 1 个，且概率降低至 0.4。
      - 若模板池缺乏阵营模板，则强制加入至少一条阵营规则 {5, 6}。
    规则索引含义：
      0: 恰好一位（X,Y）为骑士
      1: X 与 Y 状态相同
      2: 若 X 是骗子，则 Y 是骑士
      3: (X,Y,Z) 至少一位为骑士
      4: (X,Y,Z) 至多一位为骑士
      5: X 与 Y 同阵营
      6: 若 A 为骑士，则 B 与 C 同阵营
    """
    if max_rule_id <= 0:
        return []
    all_ids = list(range(0, max_rule_id))
    heavy_rules = {3, 4, 6}
    faction_rules = {5, 6}
    normal_ids = [i for i in all_ids if i not in heavy_rules]

    min_k = max(1, min_k)
    max_k = max(min_k, min(max_k, len(all_ids)))
    k = random.randint(min_k, max_k)

    heavy_k = 0
    if len(heavy_rules) > 0 and random.random() < 0.4:
        heavy_k = 1
    heavy_ids_chosen = random.sample(list(heavy_rules), heavy_k) if heavy_k > 0 else []
    remaining_k = max(0, k - heavy_k)
    normal_ids_chosen = random.sample(normal_ids, min(remaining_k, len(normal_ids)))

    pool = sorted(heavy_ids_chosen + normal_ids_chosen)

    # 若模板中缺乏阵营模板，则保证至少一条阵营规则进入
    if not _has_faction_template(templates_pool or []):
        if not any(r in faction_rules for r in pool):
            cands = [r for r in faction_rules if r in all_ids]
            if cands:
                pool = sorted(set(pool + [random.choice(cands)]))
                # 若长度超过 k，移除一个非阵营规则
                if len(pool) > k:
                    non_faction = [x for x in pool if x not in faction_rules]
                    if non_faction:
                        drop = random.choice(non_faction)
                        pool.remove(drop)

    # 补位到 k（如果需要）
    if len(pool) < k:
        rest = [i for i in normal_ids if i not in pool]
        need = k - len(pool)
        if need > 0 and rest:
            pool += random.sample(rest, min(need, len(rest)))
            pool = sorted(pool)
    return pool

def pick_from(options):
    """
    从给定列表中随机选取一个元素（通用选择器，避免在 variables 中使用 type: str）。
    """
    if not options:
        return None
    return random.choice(list(options))

def render_saying(speaker, x, y, t):
    """
    将发言模板编号 t 与参数 (speaker, x, y) 渲染为可读文本。
    模板含义：
      0: 'x 是骑士'
      1: 'x 是骗子'
      2: 'x 与 y 恰好一人是骑士'
      3: 'x 与 y 的身份相同'
      4: '若 x 是骗子则 y 是骑士'
      5: 'x 与 y 不可能同时为骑士'
      6: 'x 与 y 至少一人是骑士'
      7: '与 x 同阵营的所有人都是骑士'
      8: 'x 与 y 同阵营'
      9: '所有骑士都与 x 同阵营'
      10: '若 y 是骑士，则与 y 同阵营的所有人都是骑士'
      11: 'x 的阵营中至少有一名骑士'
    """
    if t == 0:
        core = f'{x} is a knight'
    elif t == 1:
        core = f'{x} is a knave'
    elif t == 2:
        core = f'exactly one of {x} and {y} is a knight'
    elif t == 3:
        core = f'{x} and {y} have the same status'
    elif t == 4:
        core = f'if {x} is a knave then {y} is a knight'
    elif t == 5:
        core = f'not both {x} and {y} are knights'
    elif t == 6:
        core = f'at least one of {x} and {y} is a knight'
    elif t == 7:
        core = f'everyone in the same faction as {x} is a knight'
    elif t == 8:
        core = f'{x} and {y} are in the same faction'
    elif t == 9:
        core = f'all knights are in the same faction as {x}'
    elif t == 10:
        core = f'if {y} is a knight then everyone in the faction of {y} is a knight'
    elif t == 11:
        core = f'the faction of {x} contains at least one knight'
    else:
        core = 'makes an unspecified statement'
    return f'{speaker} says that {core}'

def render_extra_rule(a, b, c, rtype):
    """
    渲染全局额外规则文本，仅返回核心内容，以配合外层标题。
      0: 恰好一位（A,B）为骑士
      1: A 与 B 状态相同
      2: 若 A 是骗子，则 B 是骑士
      3: (A,B,C) 至少一位为骑士
      4: (A,B,C) 至多一位为骑士
      5: A 与 B 同阵营
      6: 若 A 为骑士，则 B 与 C 同阵营
    """
    if rtype == 0:
        return f'exactly one of {a} and {b} is a knight'
    elif rtype == 1:
        return f'{a} and {b} have the same status'
    elif rtype == 2:
        return f'if {a} is a knave then {b} is a knight'
    elif rtype == 3:
        return f'at least one of {a}, {b} and {c} is a knight'
    elif rtype == 4:
        return f'at most one of {a}, {b} and {c} is a knight'
    elif rtype == 5:
        return f'{a} and {b} are in the same faction'
    elif rtype == 6:
        return f'if {a} is a knight then {b} and {c} are in the same faction'
    else:
        return 'unspecified global rule'

def gen_sayings_triplets(names, templates_pool):
    """
    为每位说话者生成一条 (x, y, t) 三元组：
    - x != speaker
    - 若 t 需要两个目标（t in needs_two），则 y != speaker 且 y != x；否则令 y = x
    稳健性策略：
      - 重模板 heavy_set = {7, 9, 10} 在整题中最多使用 1 次。
      - 覆盖保障：确保至少一条阵营类发言（优先 8 或 11）与至少一条身份类发言（优先 0、1、2、3、6），优先分配给前两位说话者以增强引导性。
      - 若 templates_pool 为空或仅包含重模板，补充正常模板候选以避免不可满足。
    """
    needs_two = {2, 3, 4, 5, 6, 8, 10}
    heavy_set = {7, 9, 10}
    heavy_max = 1
    heavy_used = 0

    identity_pref = [0, 1, 2, 3, 6]
    faction_light = [8, 11]

    normal_fallback = list(set(identity_pref + faction_light))
    normal_in_pool = [t for t in templates_pool if t not in heavy_set]
    if not normal_in_pool:
        templates_pool = sorted(set(list(templates_pool or []) + normal_fallback))

    has_identity = any(t in identity_pref for t in (templates_pool or []))
    has_faction = _has_faction_template(templates_pool or [])

    triplets = []
    for i, s in enumerate(names):
        candidates = list(templates_pool or normal_fallback)
        # 在前两位说话者上优先满足覆盖（若可用）
        if i == 0 and has_faction:
            prefer = [tt for tt in candidates if tt in faction_light]
            if not prefer and heavy_used < heavy_max:
                prefer = [tt for tt in candidates if tt in heavy_set]
            t = random.choice(prefer) if prefer else random.choice([tt for tt in candidates if tt not in heavy_set] or candidates)
            if t in heavy_set:
                heavy_used += 1
        elif i == 1 and has_identity:
            prefer = [tt for tt in candidates if tt in identity_pref]
            t = random.choice(prefer) if prefer else random.choice([tt for tt in candidates if tt not in heavy_set] or candidates)
        else:
            pool_now = [tt for tt in candidates if tt not in heavy_set] if heavy_used >= heavy_max else candidates
            t = random.choice(pool_now)
            if t in heavy_set:
                heavy_used += 1

        candidates_x = [n for n in names if n != s]
        x = random.choice(candidates_x)
        if t in needs_two:
            candidates_y = [n for n in names if n != s and n != x]
            if not candidates_y:
                candidates_y = candidates_x
            y = random.choice(candidates_y)
        else:
            y = x
        triplets.append((x, y, t))

    return triplets

def build_sayings_text(names, triplets):
    """
    将 (speaker=names[i], x, y, t) 渲染为带编号的多行文本，使用 '\\n' 连接。
    """
    lines = []
    for i, s in enumerate(names):
        x, y, t = triplets[i]
        lines.append(f'({i+1}) ' + render_saying(s, x, y, t))
    return '\\n'.join(lines)

def choose_count_type(templates_pool, extra_rule_pool):
    """
    升级为精确计数模式，显著提升唯一解稳定性。
    返回 'exactly'，并在题面中明确提示。
    """
    return 'exactly'

def choose_knight_count(p_num, templates_pool, extra_rule_pool):
    """
    根据题目强度自适应选取骑士人数阈值（用于精确计数模式）：
    - 下界至少为 3（因两个阵营均需至少一名骑士且人数不相等，最小总骑士数为 3）。
    - 默认取中间范围 [ceil(p_num/3), ceil(2*p_num/3)]，再与 [3, p_num-1] 交集，避免极端与平凡。
    """
    from math import ceil
    # 基础区间
    base_min = max(3, ceil(p_num / 3))
    base_max = min(p_num - 1, ceil(2 * p_num / 3))
    if base_max < base_min:
        base_max = base_min
    return random.randint(base_min, base_max)