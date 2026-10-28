# goods_exchange_6.py
import random
from typing import List, Tuple, Dict, Any


# ---------- 基础池与工具 ----------

_NAME_POOL = [
    '沈舟','唐月','尤亮','范行','葛微','霍云','卢遥','马歌','倪晨','浦林',
    '李杉','张楚','王聿','赵杭','周晓','钱澄','孙澜','吴奕','郑墨','陈岚',
    '韩冰','杨宁','高越','邵齐','陶弦','袁川','贾敏','顾岚','何渊','许棠'
]
_BANNED_SURNAME_CANDIDATES = ['马','李','张','王','赵','孙','周','吴','郑','陈','杨','何','许','韩','顾']

_COLORS = ['红色','蓝色','绿色','紫色','橙色','银色','金色','黑色','白色','灰色','青色','粉色','褐色','琥珀色','赭色']
_TYPES = ['心电仪','除颤器','急救包','输液泵','担架','监护仪','呼吸机','血氧仪','体温枪','药品箱','注射泵','吸引器','喉镜','血压计','氧气袋']
_GROUP_LABELS = ['甲组','乙组','丙组','丁组']


def _make_devices(n: int) -> List[str]:
    combos = [f'{c}{t}' for c in _COLORS for t in _TYPES]
    random.shuffle(combos)
    return combos[:n]


def _get_color(dev: str) -> str:
    for c in _COLORS:
        if dev.startswith(c):
            return c
    return ''


def list_join(lst: List[str], sep: str = ',') -> str:
    return sep.join(lst)


def groups_to_text(persons: List[str], groups: Dict[str, str]) -> str:
    return ','.join([f'{p}-{groups.get(p, "")}' for p in persons])


def assignments_to_text(assignments: List[List[str]]) -> str:
    return ','.join([f'{p}-{d}' for p, d in assignments])


def constraints_to_text(rules: List[Dict[str, Any]], groups: Dict[str, str]) -> str:
    lines = []
    # 通用执行规则（新增）：任何违反规则的步骤视为失败且不发生互换
    lines.append('通用执行规则：任何一步若违反任一规则，该步失败且不发生互换（失败的步骤不会改变任何人的设备持有情况）')
    for i, r in enumerate(rules, 1):
        t = r['type']
        if t == 'block_device_pair':
            a, b = r['devices']
            lines.append(f'规则{i}：{a} 与 {b} 不可直接互换')
        elif t == 'block_person_pair':
            a, b = r['persons']
            lines.append(f'规则{i}：{a} 与 {b} 不可直接互换')
        elif t == 'limit_device_pair':
            a, b, c = r['devices'][0], r['devices'][1], r['limit_count']
            lines.append(f'规则{i}：{a} 与 {b} 的直接互换本局最多 {c} 次（仅成功的互换计数一次）')
        elif t == 'limit_person_pair':
            a, b, c = r['persons'][0], r['persons'][1], r['limit_count']
            lines.append(f'规则{i}：{a} 与 {b} 的直接互换本局最多 {c} 次（仅成功的互换计数一次）')
        elif t == 'ban_device_to_surname':
            dev, sn = r['device'], r['surname_prefix']
            lines.append(f'规则{i}：{dev} 不可互换给姓“{sn}”的人')
        elif t == 'ban_device_to_group':
            dev, g = r['device'], r['group']
            lines.append(f'规则{i}：{dev} 不可互换给“{g}”组的人员')
        elif t == 'phase_lock_device':
            dev, owner, until_step = r['device'], r['owner'], r['until_step']
            lines.append(f'规则{i}：阶段锁——在第1至第{until_step}步期间，{dev} 不可离开其原持有者 {owner}')
        elif t == 'limit_adjacent_pair':
            a, b, c = r['persons'][0], r['persons'][1], r['limit_count']
            lines.append(f'规则{i}：相邻限次——若 {a} 与 {b} 在人员顺序中相邻，则两人直接互换本局最多 {c} 次（仅成功的互换计数一次；“相邻”以题面给定的人员顺序为准）')
        elif t == 'group_color_quota':
            grp, color, limit_count = r['group'], r['color'], r['limit_count']
            lines.append(f'规则{i}：颜色配额——任一步若某次互换会使“{grp}”组的“{color}”设备数超过 {limit_count}，该互换禁止（设备颜色以设备名的前缀颜色为准）')
        else:
            lines.append(f'规则{i}：未知规则')
    return '；'.join(lines) + '。'


def plan_to_text(plan: List[Dict[str, Any]]) -> str:
    lines = []
    for i, step in enumerate(plan, 1):
        if step['type'] == 'swap':
            a, b = step['a'], step['b']
            lines.append(f'{i}) {a}与{b}互换')
        elif step['type'] == 'try_then':
            a, b, c = step['a'], step['b'], step['c']
            lines.append(f'{i}) {a}尝试与{b}互换，若失败则改与{c}互换')
        else:
            lines.append(f'{i}) 未知步骤')
    return '；'.join(lines) + '。'


def answer_format_example() -> str:
    # 不包含省略号的示例，明确每项为“姓名-设备”
    return "('张三-红色急救包','李四-蓝色除颤器','王五-绿色监护仪')"


# ---------- 通用规则检查 ----------

def _violates_any_rule(name_a: str,
                       name_b: str,
                       dev_a: str,
                       dev_b: str,
                       rules: List[Dict[str, Any]],
                       groups: Dict[str, str],
                       counters: Dict[int, int],
                       persons: List[str],
                       origin_owner: Dict[str, str],
                       step_idx: int,
                       mapping: Dict[str, str],
                       check_only: bool = False) -> bool:
    for idx, r in enumerate(rules):
        t = r['type']
        if t == 'block_device_pair':
            if {dev_a, dev_b} == set(r['devices']):
                return True
        elif t == 'block_person_pair':
            if {name_a, name_b} == set(r['persons']):
                return True
        elif t == 'limit_device_pair':
            if {dev_a, dev_b} == set(r['devices']):
                used = counters.get(idx, 0)
                if used >= r['limit_count']:
                    return True
                if not check_only:
                    counters[idx] = used + 1
        elif t == 'limit_person_pair':
            if {name_a, name_b} == set(r['persons']):
                used = counters.get(idx, 0)
                if used >= r['limit_count']:
                    return True
                if not check_only:
                    counters[idx] = used + 1
        elif t == 'ban_device_to_surname':
            sn = r['surname_prefix']
            dev = r['device']
            if dev_a == dev and name_b.startswith(sn):
                return True
            if dev_b == dev and name_a.startswith(sn):
                return True
        elif t == 'ban_device_to_group':
            grp = r['group']
            dev = r['device']
            if dev_a == dev and groups.get(name_b, '') == grp:
                return True
            if dev_b == dev and groups.get(name_a, '') == grp:
                return True
        elif t == 'phase_lock_device':
            dev = r['device']
            owner = r['owner']
            until = r['until_step']
            if step_idx <= until:
                if dev_a == dev and name_a == owner and name_b != owner:
                    return True
                if dev_b == dev and name_b == owner and name_a != owner:
                    return True
        elif t == 'limit_adjacent_pair':
            a, b, limit_count = r['persons'][0], r['persons'][1], r['limit_count']
            pa = persons.index(a)
            pb = persons.index(b)
            if abs(pa - pb) == 1 and {name_a, name_b} == {a, b}:
                used = counters.get(idx, 0)
                if used >= limit_count:
                    return True
                if not check_only:
                    counters[idx] = used + 1
        elif t == 'group_color_quota':
            grp = r['group']
            color = r['color']
            limit_count = r['limit_count']
            def count_color_in_group(m: Dict[str, str], group: str, clr: str) -> int:
                return sum(1 for p, d in m.items() if groups.get(p, '') == group and _get_color(d) == clr)
            new_map = dict(mapping)
            new_map[name_a] = dev_b
            new_map[name_b] = dev_a
            after_count = count_color_in_group(new_map, grp, color)
            if after_count > limit_count:
                return True
        else:
            pass
    return False


# ---------- 执行器（核心 6 参数） ----------

def _run_exchange_core(persons: List[str],
                       devices: List[str],
                       initial_assignments: List[List[str]],
                       rules: List[Dict[str, Any]],
                       groups: Dict[str, str],
                       swap_plan: List[Dict[str, Any]]) -> Tuple[str, ...]:
    mapping: Dict[str, str] = {p: d for p, d in initial_assignments}
    origin_owner: Dict[str, str] = {d: p for p, d in initial_assignments}
    counters: Dict[int, int] = {}

    def try_swap(name_a: str, name_b: str, step_idx: int) -> bool:
        dev_a = mapping[name_a]
        dev_b = mapping[name_b]
        if _violates_any_rule(name_a, name_b, dev_a, dev_b, rules, groups, counters, persons, origin_owner, step_idx, mapping, check_only=False):
            return False
        mapping[name_a], mapping[name_b] = dev_b, dev_a
        return True

    for sidx, step in enumerate(swap_plan, 1):
        if step['type'] == 'swap':
            _ = try_swap(step['a'], step['b'], sidx)
        elif step['type'] == 'try_then':
            if not try_swap(step['a'], step['b'], sidx):
                _ = try_swap(step['a'], step['c'], sidx)
        else:
            pass

    return tuple(f'{p}-{mapping[p]}' for p in persons)


# ---------- 兼容旧版 7 参数入口 ----------

def _build_compat_rules_and_plan(persons: List[str],
                                 devices: List[str],
                                 initial_assignments: List[List[str]],
                                 blocked_pair: List[str],
                                 pair_counter_devices: List[str],
                                 limit_count: int,
                                 banned_receiver_device: str) -> Tuple[List[Dict[str, Any]], Dict[str, str], List[Dict[str, Any]]]:
    groups: Dict[str, str] = {}
    group_labels = ['甲组', '乙组']
    for idx, p in enumerate(persons):
        groups[p] = group_labels[idx % 2]

    rules: List[Dict[str, Any]] = []
    rules.append({'type': 'block_device_pair', 'devices': blocked_pair})
    rules.append({'type': 'limit_device_pair', 'devices': [pair_counter_devices[0], pair_counter_devices[1]], 'limit_count': int(limit_count)})

    surnames_present = [name[0] for name in persons]
    sn_choice = None
    for sn in _BANNED_SURNAME_CANDIDATES:
        if sn in surnames_present:
            sn_choice = sn
            break
    if sn_choice is None:
        sn_choice = surnames_present[0]
    rules.append({'type': 'ban_device_to_surname', 'device': banned_receiver_device, 'surname_prefix': sn_choice})

    mapping: Dict[str, str] = {p: d for p, d in initial_assignments}
    swap_plan: List[Dict[str, Any]] = []

    def owner_of(dev: str) -> str:
        for p, d in mapping.items():
            if d == dev:
                return p
        for p, d in initial_assignments:
            if d == dev:
                return p
        return persons[0]

    x_owner = owner_of(pair_counter_devices[0])
    y_owner = owner_of(pair_counter_devices[1])
    for i in range(int(limit_count)):
        swap_plan.append({'type': 'swap', 'a': x_owner, 'b': y_owner})
        mapping[x_owner], mapping[y_owner] = mapping[y_owner], mapping[x_owner]
        x_owner = owner_of(pair_counter_devices[0])
        y_owner = owner_of(pair_counter_devices[1])

    x_owner = owner_of(pair_counter_devices[0])
    y_owner = owner_of(pair_counter_devices[1])
    swap_plan.append({'type': 'swap', 'a': x_owner, 'b': y_owner})

    b1_owner = owner_of(blocked_pair[0])
    b2_owner = owner_of(blocked_pair[1])
    swap_plan.append({'type': 'swap', 'a': b1_owner, 'b': b2_owner})

    target_person = None
    for p in persons:
        if p != owner_of(banned_receiver_device) and p.startswith(sn_choice):
            target_person = p
            break
    if target_person is None:
        any_other = persons[0] if persons[0] != owner_of(banned_receiver_device) else (persons[1] if len(persons) > 1 else persons[0])
        swap_plan.append({'type': 'try_then', 'a': owner_of(banned_receiver_device), 'b': any_other, 'c': any_other})
    else:
        swap_plan.append({'type': 'swap', 'a': owner_of(banned_receiver_device), 'b': target_person})

    return rules, groups, swap_plan


def run_exchange(*args, **kwargs) -> Tuple[str, ...]:
    if len(args) == 6:
        persons, devices, initial_assignments, rules, groups, swap_plan = args
        return _run_exchange_core(persons, devices, initial_assignments, rules, groups, swap_plan)
    elif len(args) == 7:
        persons, devices, initial_assignments, blocked_pair, pair_counter_devices, limit_count, banned_receiver_device = args
        rules, groups, swap_plan = _build_compat_rules_and_plan(
            persons, devices, initial_assignments,
            blocked_pair, pair_counter_devices, limit_count, banned_receiver_device
        )
        return _run_exchange_core(persons, devices, initial_assignments, rules, groups, swap_plan)
    else:
        raise TypeError(f'run_exchange() expected 6 or 7 arguments, got {len(args)}')


# ---------- 内部一致性与唯一性验证 ----------

def _check_forced_try_then(persons: List[str],
                           initial_assignments: List[List[str]],
                           rules: List[Dict[str, Any]],
                           groups: Dict[str, str],
                           swap_plan: List[Dict[str, Any]]) -> bool:
    mapping: Dict[str, str] = {p: d for p, d in initial_assignments}
    origin_owner: Dict[str, str] = {d: p for p, d in initial_assignments}
    counters: Dict[int, int] = {}

    for sidx, step in enumerate(swap_plan, 1):
        if step['type'] == 'swap':
            dev_a = mapping[step['a']]
            dev_b = mapping[step['b']]
            should_fail = _violates_any_rule(step['a'], step['b'], dev_a, dev_b, rules, groups, counters, persons, origin_owner, sidx, mapping, check_only=True)
            real = not _violates_any_rule(step['a'], step['b'], dev_a, dev_b, rules, groups, counters, persons, origin_owner, sidx, mapping, check_only=False)
            if should_fail and real:
                return False
            if not should_fail and not real:
                return False
            if real:
                mapping[step['a']], mapping[step['b']] = dev_b, dev_a
        elif step['type'] == 'try_then':
            a, b, c = step['a'], step['b'], step['c']
            dev_a = mapping[a]
            dev_b = mapping[b]
            first_fail = _violates_any_rule(a, b, dev_a, dev_b, rules, groups, counters, persons, origin_owner, sidx, mapping, check_only=True)
            if not first_fail:
                if not _violates_any_rule(a, b, dev_a, dev_b, rules, groups, counters, persons, origin_owner, sidx, mapping, check_only=False):
                    return False
            dev_c = mapping[c]
            then_ok = not _violates_any_rule(a, c, dev_a, dev_c, rules, groups, counters, persons, origin_owner, sidx, mapping, check_only=False)
            if not then_ok:
                return False
            mapping[a], mapping[c] = dev_c, dev_a
        else:
            continue
    return True


# ---------- 场景生成（正向） ----------

def generate_scenario() -> Dict[str, Any]:
    """
    随机生成完整场景，并确保：
    - 阶段锁失败步发生在锁期内；
    - 颜色配额规则仅在可触发且可失败时启用；
    - try_then 步第一尝试必失败且后备必成功；
    - 至少触发三类不同失败规则；
    - 通过执行器与验证器一致性校验。
    """
    for _try in range(180):
        # 1) 人数与人员
        n = random.randint(8, 12)
        persons = random.sample(_NAME_POOL, n)

        # 2) 设备
        devices = _make_devices(n)

        # 3) 初始分配
        shuffled = devices[:]
        random.shuffle(shuffled)
        initial_assignments = [[p, d] for p, d in zip(persons, shuffled)]

        # 4) 分组信息
        group_labels = random.sample(_GROUP_LABELS, random.randint(2, 3))
        groups: Dict[str, str] = {p: random.choice(group_labels) for p in persons}

        # 5) 规则模板抽样（至少三类）
        rules: List[Dict[str, Any]] = []

        # 5.1 设备对禁止互换
        block_devices = random.sample(devices, 2)
        rules.append({'type': 'block_device_pair', 'devices': block_devices})

        # 5.2 限次（人对或设备对）
        use_person_limit = random.choice([True, False])
        if use_person_limit:
            lp_persons = random.sample(persons, 2)
            rules.append({'type': 'limit_person_pair', 'persons': lp_persons, 'limit_count': random.randint(1, 3)})
        else:
            while True:
                ldevs = random.sample(devices, 2)
                if set(ldevs) != set(block_devices):
                    break
            rules.append({'type': 'limit_device_pair', 'devices': ldevs, 'limit_count': random.randint(1, 3)})

        # 5.3 禁配（组或姓）
        use_group_ban = random.choice([True, False])
        if use_group_ban:
            ban_dev = random.choice(devices)
            ban_grp = random.choice(group_labels)
            rules.append({'type': 'ban_device_to_group', 'device': ban_dev, 'group': ban_grp})
        else:
            ban_dev = random.choice(devices)
            surnames_present = {name[0] for name in persons}
            candidates = [s for s in _BANNED_SURNAME_CANDIDATES if s in surnames_present] or list(surnames_present)
            ban_sn = random.choice(candidates)
            rules.append({'type': 'ban_device_to_surname', 'device': ban_dev, 'surname_prefix': ban_sn})

        # 5.4 可选：人对禁止
        if random.choice([True, False]):
            while True:
                cand = random.sample(persons, 2)
                # 避免与限次人对完全重叠
                if not any(r['type'] == 'limit_person_pair' and set(r['persons']) == set(cand) for r in rules):
                    rules.append({'type': 'block_person_pair', 'persons': cand})
                    break

        # 5.5 阶段锁（保证后续会在锁期内安排失败步）
        phase_until = random.randint(2, 4)
        phase_lock_device = random.choice(devices)
        phase_owner = next((p for p, d in initial_assignments if d == phase_lock_device), None)
        phase_rule_idx = None
        if phase_owner:
            phase_rule_idx = len(rules)
            rules.append({'type': 'phase_lock_device', 'device': phase_lock_device, 'owner': phase_owner, 'until_step': phase_until})

        # 5.6 相邻限次
        adj_index = random.randint(0, n - 2)
        adj_pair = [persons[adj_index], persons[adj_index + 1]]
        rules.append({'type': 'limit_adjacent_pair', 'persons': adj_pair, 'limit_count': random.randint(1, 2)})

        # 5.7 颜色配额（仅当可触发时添加）
        present_colors = { _get_color(d) for d in devices if _get_color(d) }
        quota_rule_added = False
        quota_group = None
        quota_color = None
        if present_colors:
            current_map = {p: d for p, d in initial_assignments}
            for _c_try in range(30):
                grp = random.choice(group_labels)
                col = random.choice(list(present_colors))
                out_with_color = [p for p, d in current_map.items() if groups.get(p, '') != grp and _get_color(d) == col]
                in_any = [p for p in persons if groups.get(p, '') == grp]
                if out_with_color and in_any:
                    init_count = sum(1 for p, d in current_map.items() if groups.get(p, '') == grp and _get_color(d) == col)
                    rules.append({'type': 'group_color_quota', 'group': grp, 'color': col, 'limit_count': max(0, init_count)})
                    quota_rule_added = True
                    quota_group = grp
                    quota_color = col
                    break

        # 6) 构建交换计划（保证阶段锁失败发生在锁期内；try_then 一成一败；配额失败可触发则插入）
        test_mapping: Dict[str, str] = {p: d for p, d in initial_assignments}
        origin_owner: Dict[str, str] = {d: p for p, d in initial_assignments}
        test_counters: Dict[int, int] = {}

        def _violates_with(rules_list: List[Dict[str, Any]], a: str, b: str, sidx: int, check_only=False) -> bool:
            da = test_mapping[a]
            db = test_mapping[b]
            return _violates_any_rule(a, b, da, db, rules_list, groups, test_counters, persons, origin_owner, sidx, test_mapping, check_only=check_only)

        def try_swap(name_a: str, name_b: str, sidx: int) -> bool:
            dev_a = test_mapping[name_a]
            dev_b = test_mapping[name_b]
            if _violates_any_rule(name_a, name_b, dev_a, dev_b, rules, groups, test_counters, persons, origin_owner, sidx, test_mapping, check_only=False):
                return False
            test_mapping[name_a], test_mapping[name_b] = dev_b, dev_a
            return True

        plan: List[Dict[str, Any]] = []
        flags = {
            'ban_fail': False,
            'limit_fail': False,
            'block_device_fail': False,
            'block_person_fail': False,
            'phase_fail': False,
            'adjacent_fail': False,
            'quota_fail': False
        }

        sidx = 0

        # Step A: 1–2 步随机成功互换，若存在阶段锁，则避免涉及锁定所有者，保证锁期内设备不被移动
        a_count = random.randint(1, 2)
        if phase_owner and phase_rule_idx is not None:
            a_count = min(a_count, max(1, rules[phase_rule_idx]['until_step'] - 1))
        for _ in range(a_count):
            for _k in range(60):
                a, b = random.sample(persons, 2)
                if phase_owner and sidx + 1 <= rules[phase_rule_idx]['until_step'] and (a == phase_owner or b == phase_owner):
                    continue
                if not _violates_with(rules, a, b, sidx + 1, check_only=True):
                    sidx += 1
                    plan.append({'type': 'swap', 'a': a, 'b': b})
                    _ = try_swap(a, b, sidx)
                    break

        # Step F (提前): 阶段锁失败尝试（确保在锁期内）
        if phase_owner and phase_rule_idx is not None:
            phase_attempt_target = None
            rules_wo_phase = [rr for rr in rules if rr['type'] != 'phase_lock_device']
            for _k in range(60):
                cand = random.choice([p for p in persons if p != phase_owner])
                if not _violates_with(rules_wo_phase, phase_owner, cand, sidx + 1, check_only=True):
                    phase_attempt_target = cand
                    break
            if phase_attempt_target:
                if sidx + 1 > rules[phase_rule_idx]['until_step']:
                    rules[phase_rule_idx]['until_step'] = sidx + 1
                sidx += 1
                plan.append({'type': 'swap', 'a': phase_owner, 'b': phase_attempt_target})
                if not try_swap(phase_owner, phase_attempt_target, sidx):
                    flags['phase_fail'] = True

        # Step B: “尝试-失败-后备成功”，失败由禁配规则保证
        ban_rules = [r for r in rules if r['type'] in ('ban_device_to_surname', 'ban_device_to_group')]
        if not ban_rules:
            continue
        br = random.choice(ban_rules)
        owner_ban_dev = next((p for p, d in test_mapping.items() if d == br.get('device', None)), None)
        if owner_ban_dev is None:
            continue
        if br['type'] == 'ban_device_to_surname':
            sn = br['surname_prefix']
            candidates = [p for p in persons if p != owner_ban_dev and p.startswith(sn)]
        else:
            grp = br['group']
            candidates = [p for p in persons if p != owner_ban_dev and groups.get(p, '') == grp]
        if not candidates:
            continue
        q_ban = random.choice(candidates)
        c = None
        rules_wo_ban = [r for r in rules if r['type'] not in ('ban_device_to_surname', 'ban_device_to_group')]
        for _k in range(60):
            cand = random.choice([p for p in persons if p not in (q_ban, owner_ban_dev)])
            if not _violates_with(rules_wo_ban, q_ban, owner_ban_dev, sidx + 1, check_only=True) and not _violates_with(rules, q_ban, cand, sidx + 1, check_only=True):
                c = cand
                break
        if c is None:
            continue
        sidx += 1
        plan.append({'type': 'try_then', 'a': q_ban, 'b': owner_ban_dev, 'c': c})
        if not try_swap(q_ban, owner_ban_dev, sidx):
            flags['ban_fail'] = True
            _ = try_swap(q_ban, c, sidx)

        # Step C: 针对限次——执行至上限，再多一次失败
        for r in rules:
            if r['type'] == 'limit_device_pair':
                for _rep in range(r['limit_count']):
                    x_owner = next((p for p, d in test_mapping.items() if d == r['devices'][0]), None)
                    y_owner = next((p for p, d in test_mapping.items() if d == r['devices'][1]), None)
                    if not x_owner or not y_owner:
                        break
                    sidx += 1
                    plan.append({'type': 'swap', 'a': x_owner, 'b': y_owner})
                    _ = try_swap(x_owner, y_owner, sidx)
                x_owner = next((p for p, d in test_mapping.items() if d == r['devices'][0]), None)
                y_owner = next((p for p, d in test_mapping.items() if d == r['devices'][1]), None)
                if x_owner and y_owner:
                    sidx += 1
                    plan.append({'type': 'swap', 'a': x_owner, 'b': y_owner})
                    if not try_swap(x_owner, y_owner, sidx):
                        flags['limit_fail'] = True
            elif r['type'] == 'limit_person_pair':
                a, b = r['persons']
                for _rep in range(r['limit_count']):
                    sidx += 1
                    plan.append({'type': 'swap', 'a': a, 'b': b})
                    _ = try_swap(a, b, sidx)
                sidx += 1
                plan.append({'type': 'swap', 'a': a, 'b': b})
                if not try_swap(a, b, sidx):
                    flags['limit_fail'] = True

        # Step D: 设备禁止对失败尝试
        bp1_owner = next((p for p, d in test_mapping.items() if d == block_devices[0]), None)
        bp2_owner = next((p for p, d in test_mapping.items() if d == block_devices[1]), None)
        if bp1_owner and bp2_owner:
            sidx += 1
            plan.append({'type': 'swap', 'a': bp1_owner, 'b': bp2_owner})
            if not try_swap(bp1_owner, bp2_owner, sidx):
                flags['block_device_fail'] = True

        # Step E: 若有人对禁止，安排一次失败尝试
        for r in rules:
            if r['type'] == 'block_person_pair':
                a, b = r['persons']
                sidx += 1
                plan.append({'type': 'swap', 'a': a, 'b': b})
                if not try_swap(a, b, sidx):
                    flags['block_person_fail'] = True
                break

        # Step G: 相邻限次——达到上限后再尝试一次失败
        adj_a, adj_b = adj_pair
        limit_adj = next(r['limit_count'] for r in rules if r['type'] == 'limit_adjacent_pair')
        if {test_mapping[adj_a], test_mapping[adj_b]} != set(block_devices):
            for _rep in range(limit_adj):
                sidx += 1
                plan.append({'type': 'swap', 'a': adj_a, 'b': adj_b})
                _ = try_swap(adj_a, adj_b, sidx)
            sidx += 1
            plan.append({'type': 'swap', 'a': adj_a, 'b': adj_b})
            if not try_swap(adj_a, adj_b, sidx):
                flags['adjacent_fail'] = True

        # Step H: 颜色配额失败（仅当已添加该规则且可构造）
        if quota_rule_added and quota_group and quota_color:
            out_with_color = [p for p, d in test_mapping.items() if groups.get(p, '') != quota_group and _get_color(d) == quota_color]
            in_any = [p for p in persons if groups.get(p, '') == quota_group]
            quota_fail_made = False
            if out_with_color and in_any:
                for src in out_with_color:
                    dst = random.choice(in_any)
                    rules_wo_quota = [rr for rr in rules if rr['type'] != 'group_color_quota']
                    if _violates_with(rules_wo_quota, src, dst, sidx + 1, check_only=True):
                        continue
                    sidx += 1
                    plan.append({'type': 'swap', 'a': src, 'b': dst})
                    if not try_swap(src, dst, sidx):
                        flags['quota_fail'] = True
                        quota_fail_made = True
                        break

        # Step I: 再随机添加 1–2 步成功互换
        for _ in range(random.randint(1, 2)):
            for _k in range(60):
                a, b = random.sample(persons, 2)
                if not _violates_with(rules, a, b, sidx + 1, check_only=True):
                    sidx += 1
                    plan.append({'type': 'swap', 'a': a, 'b': b})
                    _ = try_swap(a, b, sidx)
                    break

        # 至少三类失败
        failed_types = set()
        if flags['ban_fail']:
            failed_types.add('ban')
        if flags['limit_fail']:
            failed_types.add('limit')
        if flags['block_device_fail']:
            failed_types.add('block_device')
        if flags['block_person_fail']:
            failed_types.add('block_person')
        if flags['phase_fail']:
            failed_types.add('phase')
        if flags['adjacent_fail']:
            failed_types.add('adjacent')
        if flags['quota_fail']:
            failed_types.add('quota')
        if len(failed_types) < 3:
            continue

        # 真实执行器校验
        final_tuple = _run_exchange_core(
            persons, devices, initial_assignments,
            rules, groups,
            plan
        )
        if len(final_tuple) != len(persons):
            continue

        if not _check_forced_try_then(persons, initial_assignments, rules, groups, plan):
            continue

        return {
            'persons': persons,
            'devices': devices,
            'initial_assignments': initial_assignments,
            'groups': groups,
            'rules': rules,
            'swap_plan': plan
        }

    raise RuntimeError('Failed to generate a valid scenario after multiple attempts.')