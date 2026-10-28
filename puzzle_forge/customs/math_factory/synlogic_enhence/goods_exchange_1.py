# goods_exchange_0.py
from typing import List, Tuple, Dict, Optional, Any
import random
import re

# ---------------------------
# Name and item synthesis
# ---------------------------

_SURNAME_POOL = [
    '赵','钱','孙','李','周','吴','郑','王','冯','陈','褚','卫','蒋','沈','韩','杨','朱','秦','尤','许','何','吕','施','张',
    '孔','曹','严','华','金','魏','陶','姜','戚','谢','邹','喻','柏','水','窦','章','云','苏','潘','葛','奚','范','彭','郎',
    '鲁','韦','昌','马','苗','凤','花','方','俞','任','袁','柳','酆','鲍','史','唐','费','廉','岑','薛','雷','贺','倪','汤'
]

_GIVEN_A = list('一乙二十廿三山川之子文明国强军峰亮勇磊刚超浩涛宁宇航翔博涵昊辰晨杰凯瑞鑫泽哲志斌')
_GIVEN_B = list('东南西北中华安康天辰林峰洋诚俊奇龙斐瑜琪然雪冰洁兰敏慧姗琳倩可婧婕媛茜玲洁颖萌')

_COLOR_POOL = [
    '银色','灰色','古铜色','米色','蓝色','草绿色','墨绿色','白色','浅绿色','橙色','明黄色','酒红色','深蓝色',
    '黑色','粉色','浅灰色','藏青色','棕色','玫红色','紫色','天蓝色','咖啡色','淡紫色','靛蓝色','青色','姜黄色',
    '豆绿色','烟灰色','宝蓝色','鹅黄色','樱花粉','海蓝色','孔雀蓝','翠绿色','月白色','竹青色','朱红色','石榴红'
]

_ITEM_TYPES = [
    '钱包','电脑','明信片','耳机','戒指','眼镜','手绢','地图','纪念币','水壶','小刀','项链','口哨','发夹',
    '腰带','雨伞','手表','围巾','钥匙扣','书包','钢笔','本子','台灯','相框','风铃','徽章','手链','书签','茶杯','闹钟',
]

def _sample_unique_names(n: int, rng: random.Random) -> List[str]:
    if n < 1:
        return []
    candidates = []
    for s in _SURNAME_POOL:
        for a in _GIVEN_A:
            for b in _GIVEN_B:
                candidates.append(s + a + b)
    rng.shuffle(candidates)
    if n > len(candidates):
        raise ValueError('Requested player count exceeds name pool capacity')
    return candidates[:n]

def _sample_unique_items(n: int, rng: random.Random) -> List[str]:
    combos = []
    for c in _COLOR_POOL:
        for t in _ITEM_TYPES:
            combos.append(c + t)
    rng.shuffle(combos)
    if n > len(combos):
        raise ValueError('Requested item count exceeds item pool capacity')
    return combos[:n]

def _random_bijection(players: List[str], items: List[str], rng: random.Random) -> Dict[str, str]:
    perm = items[:]
    rng.shuffle(perm)
    return {p: it for p, it in zip(players, perm)}

# ---------------------------
# Mapping helpers
# ---------------------------

def _owner_of_item(mapping: Dict[str, str], item: str) -> str:
    for p, it in mapping.items():
        if it == item:
            return p
    raise ValueError(f'Item not found: {item}')

def _swap_by_players(mapping: Dict[str, str], p1: str, p2: str) -> None:
    mapping[p1], mapping[p2] = mapping[p2], mapping[p1]

def _swap_by_items(mapping: Dict[str, str], item_a: str, item_b: str) -> Tuple[str, str]:
    owner_a = _owner_of_item(mapping, item_a)
    owner_b = _owner_of_item(mapping, item_b)
    if owner_a == owner_b:
        return owner_a, owner_b  # no-op corner case
    _swap_by_players(mapping, owner_a, owner_b)
    return owner_a, owner_b

def _as_tuple_in_order(mapping: Dict[str, str], players: List[str]) -> Tuple[Tuple[str, str], ...]:
    return tuple((p, mapping[p]) for p in players)

def _rotate_values(vals: List[str], direction_forward: bool) -> List[str]:
    if not vals:
        return vals
    if direction_forward:
        return [vals[-1]] + vals[:-1]
    else:
        return vals[1:] + [vals[0]]

# ---------------------------
# Single-attempt scenario build (internal) with canonical sentences
# ---------------------------

def _build_once(player_num: int, step_num: int, noise_min: int, noise_max: int, rng: random.Random) -> Dict[str, Any]:
    # normalize lower bounds
    if player_num < 10:
        player_num = 10
    if step_num < 6:
        step_num = 6

    players = _sample_unique_names(player_num, rng)
    items = _sample_unique_items(player_num, rng)
    mapping = _random_bijection(players, items, rng)
    initial_pairs = [[p, mapping[p]] for p in players]

    # Locks: item -> remaining locked steps
    locks: Dict[str, int] = {}

    def _dec_locks():
        remove = []
        for it, k in list(locks.items()):
            if k > 1:
                locks[it] = k - 1
            else:
                remove.append(it)
        for it in remove:
            locks.pop(it, None)

    def _locked_item(it: str) -> bool:
        return locks.get(it, 0) > 0

    def _player_has_locked_item(p: str) -> bool:
        return _locked_item(mapping[p])

    # Decide noise and operation counts
    noise_max_eff = max(noise_min, min(noise_max, max(1, step_num - 4)))  # keep at least 4 ops
    noise_count = rng.randint(max(1, noise_min), noise_max_eff)
    op_total = step_num - noise_count
    if op_total < 4:
        # ensure minimum operations
        op_total = 4
        noise_count = step_num - op_total
        if noise_count < 0:
            noise_count = 0

    # Operation tags
    binary_tags = ['swap_players', 'swap_items', 'pivot_swap', 'conditional_swap', 'mirror_with_last']
    nonbinary_tags = ['rotate_players', 'rotate_items', 'lock_item']

    # Build labels with required presence
    labels: List[str] = []
    # ensure at least two binary ops
    labels.append(rng.choice(binary_tags))
    if op_total >= 2:
        labels.append(rng.choice(binary_tags))
    # ensure at least one rotation
    if op_total >= 3:
        labels.append(rng.choice(['rotate_players', 'rotate_items']))
    # ensure at least one lock or conditional
    if op_total >= 4:
        labels.append(rng.choice(['lock_item', 'conditional_swap']))

    while len(labels) < op_total:
        # bias slightly towards binary tags to increase effective swaps
        tag_pool = binary_tags + binary_tags + nonbinary_tags
        labels.append(rng.choice(tag_pool))
    labels += ['noop'] * noise_count
    rng.shuffle(labels)

    steps_doc: List[str] = []
    step_player_pairs: List[Optional[Tuple[str, str]]] = []

    last_binary_pair: Optional[Tuple[str, str]] = None

    def _format_noop_like() -> str:
        p = rng.choice(players)
        it = rng.choice(items)
        if rng.random() < 0.5:
            return f'{p}很喜欢{it}（无操作）'
        else:
            return f'{p}正在寻找{it}，但未找到（无操作）'

    # Simulate with canonical templates (lock-aware)
    for i, lab in enumerate(labels, start=1):
        _dec_locks()  # decrement locks at the start of each step

        if lab == 'noop':
            text = _format_noop_like()
            steps_doc.append(f'{i}. ' + text)
            step_player_pairs.append(None)
            continue

        if lab == 'swap_players':
            tries = 0
            while True:
                p1, p2 = rng.sample(players, 2)
                if not _player_has_locked_item(p1) and not _player_has_locked_item(p2):
                    _swap_by_players(mapping, p1, p2)
                    steps_doc.append(f'{i}. ' + f'{p1}与{p2}交换')
                    step_player_pairs.append((p1, p2))
                    last_binary_pair = tuple(sorted((p1, p2)))
                    break
                tries += 1
                if tries > 100:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'swap_items':
            tries = 0
            while True:
                it1, it2 = rng.sample(items, 2)
                if not _locked_item(it1) and not _locked_item(it2):
                    owner_a, owner_b = _swap_by_items(mapping, it1, it2)
                    steps_doc.append(f'{i}. ' + f'拥有{it1}者与拥有{it2}者交换')
                    step_player_pairs.append((owner_a, owner_b))
                    last_binary_pair = tuple(sorted((owner_a, owner_b)))
                    break
                tries += 1
                if tries > 100:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'pivot_swap':
            tries = 0
            while True:
                p = rng.choice(players)
                it = rng.choice(items)
                if mapping[p] != it and not _player_has_locked_item(p) and not _locked_item(it):
                    owner_it = _owner_of_item(mapping, it)
                    if not _player_has_locked_item(owner_it):
                        _swap_by_players(mapping, p, owner_it)
                        steps_doc.append(f'{i}. ' + f'{p}与拥有{it}的玩家交换')
                        step_player_pairs.append((p, owner_it))
                        last_binary_pair = tuple(sorted((p, owner_it)))
                        break
                tries += 1
                if tries > 120:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'rotate_players':
            tries = 0
            while True:
                gsz = rng.choice([3, 3, 4, 5])
                group = rng.sample(players, gsz)
                order = {p: idx for idx, p in enumerate(players)}
                group.sort(key=lambda x: order[x])
                direction_forward = rng.random() < 0.5
                if all(not _player_has_locked_item(p) for p in group):
                    current_items = [mapping[p] for p in group]
                    rotated = _rotate_values(current_items, direction_forward)
                    for p, new_item in zip(group, rotated):
                        mapping[p] = new_item
                    seq = '、'.join(group)
                    if direction_forward:
                        arrow = '→'.join(group + [group[0]])
                        steps_doc.append(f'{i}. ' + f'{seq}按顺序轮换（{arrow}）')
                    else:
                        arrow = '→'.join(list(reversed(group)) + [group[-1]])
                        steps_doc.append(f'{i}. ' + f'{seq}按逆序轮换（{arrow}）')
                    step_player_pairs.append(None)
                    last_binary_pair = None
                    break
                tries += 1
                if tries > 120:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'rotate_items':
            tries = 0
            while True:
                gsz = rng.choice([3, 3, 4])
                g_items = rng.sample(items, gsz)
                direction_forward = rng.random() < 0.5
                if all(not _locked_item(it) for it in g_items):
                    owners = [_owner_of_item(mapping, it) for it in g_items]
                    if all(not _player_has_locked_item(o) for o in owners):
                        rotated_items = _rotate_values(g_items, direction_forward)
                        for owner, new_item in zip(owners, rotated_items):
                            mapping[owner] = new_item
                        seq_items = '、'.join(g_items)
                        if direction_forward:
                            arrow_items = '→'.join(g_items + [g_items[0]])
                            steps_doc.append(f'{i}. ' + f'拥有{seq_items}的玩家按顺序轮换（{arrow_items}）')
                        else:
                            arrow_items = '→'.join(list(reversed(g_items)) + [g_items[-1]])
                            steps_doc.append(f'{i}. ' + f'拥有{seq_items}的玩家按逆序轮换（{arrow_items}）')
                        step_player_pairs.append(None)
                        last_binary_pair = None
                        break
                tries += 1
                if tries > 120:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'lock_item':
            tries = 0
            while True:
                it = rng.choice(items)
                if not _locked_item(it):
                    n = rng.choice([1, 2])
                    locks[it] = n
                    steps_doc.append(f'{i}. ' + f'将{it}锁定{n}步（锁定期间该物品不可参与任何交换或轮换）')
                    step_player_pairs.append(None)
                    last_binary_pair = None
                    break
                tries += 1
                if tries > 120:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'conditional_swap':
            tries = 0
            while True:
                it = rng.choice(items)
                sur = rng.choice(_SURNAME_POOL)
                p = rng.choice(players)
                owner_it = _owner_of_item(mapping, it)
                if not _locked_item(it) and not _player_has_locked_item(owner_it) and not _player_has_locked_item(p):
                    if owner_it.startswith(sur):
                        _swap_by_players(mapping, owner_it, p)
                        step_player_pairs.append((owner_it, p))
                        last_binary_pair = tuple(sorted((owner_it, p)))
                    else:
                        step_player_pairs.append(None)
                        last_binary_pair = None
                    steps_doc.append(f'{i}. ' + f'若持有{it}的玩家姓{sur}，则该玩家与{p}交换，否则无操作')
                    break
                tries += 1
                if tries > 150:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        if lab == 'mirror_with_last':
            tries = 0
            while True:
                p = rng.choice(players)
                if last_binary_pair is None:
                    steps_doc.append(f'{i}. ' + f'上一次发生交换的两人中，按玩家列表顺序靠前的那位与{p}交换（无操作）')
                    step_player_pairs.append(None)
                    break
                idx_map = {pl: j for j, pl in enumerate(players)}
                a, b = last_binary_pair
                base = a if idx_map[a] <= idx_map[b] else b
                if not _player_has_locked_item(base) and not _player_has_locked_item(p):
                    _swap_by_players(mapping, base, p)
                    steps_doc.append(f'{i}. ' + f'上一次发生交换的两人中，按玩家列表顺序靠前的那位与{p}交换')
                    step_player_pairs.append((base, p))
                    last_binary_pair = tuple(sorted((base, p)))
                    break
                tries += 1
                if tries > 150:
                    steps_doc.append(f'{i}. ' + _format_noop_like())
                    step_player_pairs.append(None)
                    break
            continue

        # Fallback
        steps_doc.append(f'{i}. ' + _format_noop_like())
        step_player_pairs.append(None)

    # If no swap happened, force one at the end
    swap_indices = [idx for idx, pair in enumerate(step_player_pairs) if pair is not None]
    if not swap_indices:
        p1, p2 = rng.sample(players, 2)
        _swap_by_players(mapping, p1, p2)
        steps_doc.append(f'{len(steps_doc) + 1}. ' + f'{p1}与{p2}交换')
        step_player_pairs.append((p1, p2))
        swap_indices = [len(step_player_pairs) - 1]

    # Final mapping tuple
    final_tuple = _as_tuple_in_order(mapping, players)

    # Validate bijection
    seen_items = set(mapping.values())
    assert len(seen_items) == len(items) == len(players), 'Mapping must remain bijective'

    # Pick targets for queries
    target_item = rng.choice(items)
    target_player = rng.choice(players)

    # Choose a binary swap index for q4 (only among effective swaps)
    q_step_index = rng.choice(swap_indices)

    # Derived text fields
    initial_pairs_str = ", ".join([f"({p},{it})" for p, it in initial_pairs])
    steps_text = "\n".join(steps_doc)
    players_str = "、".join(players)

    # Rule guide string
    rules_guide = (
        '规则说明：\n'
        '1) “A与B交换/互换/互相交换”：两位玩家交换各自所持物品；\n'
        '2) “拥有X者与拥有Y者交换”：当前持有物品X的玩家与当前持有物品Y的玩家交换；\n'
        '3) “P与拥有I的玩家交换”：玩家P与当前持有物品I的玩家交换；\n'
        '4) “按顺序/依次轮换”：给定玩家序列的物品右移一位；“按逆序/倒序轮换”则左移一位；\n'
        '5) “拥有S1、S2、...的玩家按顺序/逆序轮换”：序列中的物品在其持有者之间顺/逆序轮换；\n'
        '6) “将I锁定N步”：在接下来的N步中，物品I不可参与任何交换或轮换；\n'
        '7) “若持有I的玩家姓X，则其与P交换，否则无操作”；\n'
        '8) “上一次发生交换的两人中，按玩家列表顺序靠前的那位与P交换”；若之前无交换则该步无操作；\n'
        '9) 文本中含“（无操作）”表示该步不改变任何持有关系。'
    )

    return {
        'players': players,
        'items': items,
        'initial_pairs': initial_pairs,
        'initial_pairs_str': initial_pairs_str,
        'players_str': players_str,
        'steps_doc': steps_doc,
        'steps_text': steps_text,
        'final_tuple': final_tuple,
        'step_player_pairs': step_player_pairs,
        'target_item': target_item,
        'target_player': target_player,
        'q_step_index': q_step_index,
        'rules_guide': rules_guide,
    }

# ---------------------------
# Public scenario builder with quality constraints
# ---------------------------

def exchange_build_scenario(player_num: int, step_num: int, noise_min: int, noise_max: int) -> Dict[str, Any]:
    """
    Build a randomized exchange scenario with canonical rule templates and lock-aware operations.
    Enhanced Quality constraints:
    - at least 3 effective binary exchanges
    - at least 1 rotation (players/items)
    - at least 1 lock step that is not the last step
    - at least ONE of:
        * a mirror-with-last step that actually executes an exchange
        * a conditional swap that actually executes an exchange
    If constraints fail, regenerate up to 50 attempts.
    """
    sys_rng = random.SystemRandom()
    scenario: Dict[str, Any] = {}
    for _ in range(50):
        seed = sys_rng.randint(1, 10**9)
        rng = random.Random(seed)
        scenario = _build_once(player_num, step_num, noise_min, noise_max, rng)

        swaps = sum(1 for x in scenario['step_player_pairs'] if x is not None)
        has_rotation = any('轮换' in line for line in scenario['steps_doc'])
        # lock exists and not last step
        if scenario['steps_doc']:
            last_idx = len(scenario['steps_doc']) - 1
            has_lock_non_last = any(('锁定' in line) and (i < last_idx) for i, line in enumerate(scenario['steps_doc']))
        else:
            has_lock_non_last = False

        # mirror or conditional success
        mirror_success = any(('上一次发生交换' in line) and (scenario['step_player_pairs'][i] is not None)
                             for i, line in enumerate(scenario['steps_doc']))
        cond_success = any(('若持有' in line) and (scenario['step_player_pairs'][i] is not None)
                           for i, line in enumerate(scenario['steps_doc']))

        # ensure parser consistency too
        if swaps >= 3 and has_rotation and has_lock_non_last and (mirror_success or cond_success) and scenario_uniqueness_ok(scenario):
            scenario['total_steps'] = len(scenario['steps_doc'])
            return scenario
    # fallback: return last scenario even if not ideal, but should still be valid
    scenario['total_steps'] = len(scenario.get('steps_doc', []))
    return scenario

# ---------------------------
# Text-to-semantic parser for uniqueness verification
# ---------------------------

def _parse_and_reconstruct(players: List[str], items: List[str],
                           initial_pairs: List[List[str]],
                           steps_doc: List[str]) -> Tuple[Tuple[str, str], ...]:
    mapping: Dict[str, str] = {p: it for p, it in initial_pairs}
    locks: Dict[str, int] = {}

    def dec_locks():
        remove = []
        for it, k in list(locks.items()):
            if k > 1:
                locks[it] = k - 1
            else:
                remove.append(it)
        for it in remove:
            locks.pop(it, None)

    def locked(it: str) -> bool:
        return locks.get(it, 0) > 0

    def player_locked(p: str) -> bool:
        return locked(mapping[p])

    idx_map = {p: i for i, p in enumerate(players)}
    last_pair: Optional[Tuple[str, str]] = None

    # Regex patterns (canonical)
    re_noop = re.compile(r'（无操作）')
    # 收紧玩家交换正则，排除“拥有…”和“上一次…”的句式
    re_swap_players = [
        re.compile(r'^(?P<p1>(?!上一次)(?!拥有).+?)与(?P<p2>(?!拥有).+?)交换$'),
    ]
    re_swap_items = [
        re.compile(r'^拥有(?P<it1>.+?)者与拥有(?P<it2>.+?)者交换$'),
    ]
    re_pivot = [
        re.compile(r'^(?P<p>.+?)与拥有(?P<it>.+?)的玩家交换$'),
    ]
    re_rot_players_forward = [
        re.compile(r'^(?P<seq>.+?)按顺序轮换（.+?）$'),
    ]
    re_rot_players_backward = [
        re.compile(r'^(?P<seq>.+?)按逆序轮换（.+?）$'),
    ]
    re_rot_items_forward = [
        re.compile(r'^拥有(?P<seq_items>.+?)的玩家按顺序轮换（.+?）$'),
    ]
    re_rot_items_backward = [
        re.compile(r'^拥有(?P<seq_items>.+?)的玩家按逆序轮换（.+?）$'),
    ]
    re_lock_item = re.compile(r'^将(?P<it>.+?)锁定(?P<n>\d+)步（锁定期间该物品不可参与任何交换或轮换）$')
    re_conditional = re.compile(r'^若持有(?P<it>.+?)的玩家姓(?P<sur>.)，则该玩家与(?P<p>.+?)交换，否则无操作$')
    re_mirror = re.compile(r'^上一次发生交换的两人中，按玩家列表顺序靠前的那位与(?P<p>.+?)交换$')

    for line in steps_doc:
        body = line.split('. ', 1)[-1].strip()
        dec_locks()

        # No-op lines
        if re_noop.search(body):
            continue

        matched = False

        # 1) 物品持有者交换（更具体，优先）
        for pat in re_swap_items:
            m = pat.match(body)
            if m:
                it1 = m.group('it1'); it2 = m.group('it2')
                if it1 in items and it2 in items and not locked(it1) and not locked(it2):
                    owner_a, owner_b = _swap_by_items(mapping, it1, it2)
                    last_pair = tuple(sorted((owner_a, owner_b)))
                matched = True
                break
        if matched:
            continue

        # 2) 枢纽式交换（更具体，优先）
        for pat in re_pivot:
            m = pat.match(body)
            if m:
                p = m.group('p'); it = m.group('it')
                if p in mapping and it in items and mapping[p] != it and not player_locked(p) and not locked(it):
                    owner_it = _owner_of_item(mapping, it)
                    if not player_locked(owner_it):
                        _swap_by_players(mapping, p, owner_it)
                        last_pair = tuple(sorted((p, owner_it)))
                matched = True
                break
        if matched:
            continue

        # 3) 条件交换（更具体，优先）
        m = re_conditional.match(body)
        if m:
            it = m.group('it'); sur = m.group('sur'); p = m.group('p')
            if it in items and p in mapping:
                owner_it = _owner_of_item(mapping, it)
                if owner_it.startswith(sur) and not player_locked(owner_it) and not player_locked(p) and not locked(it):
                    _swap_by_players(mapping, owner_it, p)
                    last_pair = tuple(sorted((owner_it, p)))
            continue

        # 4) 镜像交换（更具体，优先）
        m = re_mirror.match(body)
        if m:
            p = m.group('p')
            if last_pair is not None and p in mapping:
                a, b = last_pair
                base = a if idx_map[a] <= idx_map[b] else b
                if not player_locked(base) and not player_locked(p):
                    _swap_by_players(mapping, base, p)
                    last_pair = tuple(sorted((base, p)))
            continue

        # 5) 玩家序列轮换（顺序/逆序）
        for pat in re_rot_players_forward:
            m = pat.match(body)
            if m:
                seq = [s.strip() for s in m.group('seq').split('、')]
                if all(p in mapping for p in seq) and all(not player_locked(p) for p in seq):
                    cur_items = [mapping[p] for p in seq]
                    rotated = _rotate_values(cur_items, True)
                    for p, it in zip(seq, rotated):
                        mapping[p] = it
                matched = True
                break
        if matched:
            continue

        for pat in re_rot_players_backward:
            m = pat.match(body)
            if m:
                seq = [s.strip() for s in m.group('seq').split('、')]
                if all(p in mapping for p in seq) and all(not player_locked(p) for p in seq):
                    cur_items = [mapping[p] for p in seq]
                    rotated = _rotate_values(cur_items, False)
                    for p, it in zip(seq, rotated):
                        mapping[p] = it
                matched = True
                break
        if matched:
            continue

        # 6) 物品序列轮换（顺序/逆序）
        for pat in re_rot_items_forward:
            m = pat.match(body)
            if m:
                seq_items = [s.strip() for s in m.group('seq_items').split('、')]
                if all(it in items for it in seq_items) and all(not locked(it) for it in seq_items):
                    owners = [_owner_of_item(mapping, it) for it in seq_items]
                    if all(not player_locked(o) for o in owners):
                        rotated_items = _rotate_values(seq_items, True)
                        for owner, new_item in zip(owners, rotated_items):
                            mapping[owner] = new_item
                matched = True
                break
        if matched:
            continue

        for pat in re_rot_items_backward:
            m = pat.match(body)
            if m:
                seq_items = [s.strip() for s in m.group('seq_items').split('、')]
                if all(it in items for it in seq_items) and all(not locked(it) for it in seq_items):
                    owners = [_owner_of_item(mapping, it) for it in seq_items]
                    if all(not player_locked(o) for o in owners):
                        rotated_items = _rotate_values(seq_items, False)
                        for owner, new_item in zip(owners, rotated_items):
                            mapping[owner] = new_item
                matched = True
                break
        if matched:
            continue

        # 7) 锁定
        m = re_lock_item.match(body)
        if m:
            it = m.group('it'); n = int(m.group('n'))
            if it in items and n >= 1:
                locks[it] = n
            continue

        # 8) 玩家与玩家交换（最后匹配，且已排除歧义）
        for pat in re_swap_players:
            m = pat.match(body)
            if m:
                p1 = m.group('p1'); p2 = m.group('p2')
                if p1 in mapping and p2 in mapping and not player_locked(p1) and not player_locked(p2):
                    _swap_by_players(mapping, p1, p2)
                    last_pair = tuple(sorted((p1, p2)))
                matched = True
                break
        if matched:
            continue

        # 未匹配的视为无操作
        continue

    return _as_tuple_in_order(mapping, players)

def scenario_uniqueness_ok(scenario: Dict[str, Any]) -> bool:
    try:
        recon = _parse_and_reconstruct(
            scenario['players'],
            scenario['items'],
            scenario['initial_pairs'],
            scenario['steps_doc']
        )
        return tuple(recon) == tuple(scenario['final_tuple'])
    except Exception:
        return False

# ---------------------------
# Answer helpers (for YAML ans_formula calls)
# ---------------------------

def scenario_final_tuple(scenario: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
    return scenario['final_tuple']

def scenario_final_str(scenario: Dict[str, Any]) -> str:
    """
    Return a canonical, whitespace-free string:
    玩家1,物品1;玩家2,物品2;... (in players list order)
    """
    pairs = scenario['final_tuple']
    return ';'.join([f'{p},{it}' for (p, it) in pairs])

def scenario_owner_of_item(scenario: Dict[str, Any]) -> str:
    target_item = scenario['target_item']
    players = scenario['players']
    final_map: Dict[str, str] = {p: it for p, it in scenario['final_tuple']}
    for p in players:
        if final_map[p] == target_item:
            return p
    raise ValueError('Target item not found in final mapping')

def scenario_item_of_player(scenario: Dict[str, Any]) -> str:
    target_player = scenario['target_player']
    final_map: Dict[str, str] = {p: it for p, it in scenario['final_tuple']}
    return final_map[target_player]

def scenario_step_players_str(scenario: Dict[str, Any]) -> str:
    idx = scenario['q_step_index']
    p_pair = scenario['step_player_pairs'][idx]
    if p_pair is None:
        return ''
    p1, p2 = p_pair
    order = {p: i for i, p in enumerate(scenario['players'])}
    if order[p1] <= order[p2]:
        return f'{p1},{p2}'
    else:
        return f'{p2},{p1}'