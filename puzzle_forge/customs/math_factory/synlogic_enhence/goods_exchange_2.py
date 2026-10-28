# goods_exchange_5.py
import random
from typing import List, Dict, Tuple, Any


# ---------- Core pools ----------
def _name_pool() -> List[str]:
    return [
        '安琪','柏林','曹宁','丁磊','尹涛','文杰','高远','贺兰','金昆','孔媛','蓝雨','蒙川',
        '宁晓','欧阳','潘霖','乔骁','任航','石磊','唐越','乌兰','夏晨','燕霖','张瑜','陈航',
        '刘岚','周毅','王珂','赵楠','钱诚','孙琳','李昂','朱赫','马宁','郭远','何洁','陶然',
        '鲁冰','谢恺','蒋澜','崔弛','尧宁','冯硕','侯杰','黎昊','景瑞','顾澄'
    ]


def _colors() -> List[str]:
    return ['红色','蓝色','绿色','紫色','橙色','银色','金色','黑色','白色','灰色','粉色','棕色','青色','褐色','靛色']


def _themes() -> List[str]:
    return ['创新徽','编程徽','生态徽','AI徽','设计徽','管理徽','创业徽','安全徽','合作徽','逻辑徽','公益徽','工业徽','数据徽','工程徽','数学徽']


# ---------- Public operators used by YAML ----------
def pick_unique_names(n: int) -> List[str]:
    pool = _name_pool()
    if n > len(pool):
        raise ValueError('Requested more names than available in pool')
    return random.sample(pool, n)


def gen_badges(n: int) -> List[str]:
    # Build a large pool of color+theme combos, then sample n unique ones
    combos = [c + t for c in _colors() for t in _themes()]
    unique_combos = list(dict.fromkeys(combos))
    if n > len(unique_combos):
        raise ValueError('Not enough unique badges available')
    return random.sample(unique_combos, n)


def assign_initial(names: List[str], badges: List[str]) -> List[List[str]]:
    # Random bijection between names and badges
    shuffled = badges[:]
    random.shuffle(shuffled)
    return [[n, b] for n, b in zip(names, shuffled)]


def pick_volatile_badge(badges: List[str]) -> str:
    return random.choice(badges)


def choose_style() -> int:
    # 0/1/2 三种文本渲染风格
    return random.choice([0, 1, 2])


def pick_hazard_rule(names: List[str]) -> Dict[str, Any]:
    """
    随机选择一种“易变规则”
    type ∈ {'last_finisher', 'alpha_next', 'prev_step_other'}
    alpha_next 需要字典序信息，预先计算
    """
    t = random.choice(['last_finisher', 'alpha_next', 'prev_step_other'])
    meta: Dict[str, Any] = {}
    if t == 'alpha_next':
        sorted_names = sorted(names)
        meta['sorted'] = sorted_names
    return {'type': t, 'meta': meta}


def semantics_text() -> str:
    """
    向题面明确公开“完成交换的人”的统一判定，与内部事件序列完全一致：
    - 两人交换：按题面书写次序的第二个名字视为“完成交换的人”；
    - 三/四人轮换：以链表中最后一个名字视为“完成交换的人”；
    - 相邻交换链：以链表中最后一个名字视为“完成交换的人”；
    - “以下两两交换（按列出顺序逐一执行）”：以最后一对中的第二个名字为“完成交换的人”；
    - 所有附加交换也遵循同一判定规则；下文所称“上一步”均包含该步的附加交换。
    """
    return '两人交换以第二个名字为完成者；三/四人轮换以链表最后一个名字为完成者；相邻交换链以链表最后一个名字为完成者；“以下两两交换（按列出顺序逐一执行）”以最后一对的第二个名字为完成者；所有附加交换也遵循上述同一判定；下文所称“上一步”均包含该步的附加交换'


def hazard_to_text(hazard_struct: Dict[str, Any]) -> str:
    t = hazard_struct.get('type')
    if t == 'last_finisher':
        # 明确主步骤触发与不连锁；并指向完成者判定规则
        return '每当有人在任一步“主步骤”结束后获得这枚“易变徽章”，该人须立即与“最近一次完成交换的人（包含附加交换）”再进行一次交换；完成者判定见“完成者判定规则”。若该人即为最近一次完成交换者，则改为与“倒数第二位完成交换的人”交换；若此前无人完成过交换或不存在可选对象，则本次易变规则不触发（该附加交换不再触发其他附加规则）'
    elif t == 'alpha_next':
        sorted_names = hazard_struct.get('meta', {}).get('sorted', [])
        order_str = '→'.join(sorted_names) if sorted_names else ''
        extra = f'（本题姓名字典序顺序：{order_str}）' if order_str else ''
        return f'每当有人在任一步“主步骤”结束后获得这枚“易变徽章”，该人须立即与“姓名按字典序紧随其后的那个人”交换；若该人按字典序位于最后，则改为与按字典序第一位的人交换；若不存在可选对象，则本次易变规则不触发（该附加交换不再触发其他附加规则）{extra}'
    elif t == 'prev_step_other':
        return '每当有人在任一步“主步骤”结束后获得这枚“易变徽章”，该人须立即与“上一步（包含该步的附加交换）参与交换且与他不同名的人中最后完成交换者”交换；完成者判定见“完成者判定规则”。若上一步不存在可选对象（例如只有他一人参与或无参与者），则本次易变规则不触发（该附加交换不再触发其他附加规则）'
    else:
        return '（规则未定义）'


# ---------- New endeavour: bonus (联动规则) ----------
def _extract_color(badge: str) -> str:
    for c in _colors():
        if badge.startswith(c):
            return c
    return ''


def _extract_theme(badge: str) -> str:
    for t in _themes():
        if t in badge:
            return t
    return ''


def pick_bonus_rule(names: List[str], badges: List[str]) -> Dict[str, Any]:
    """
    随机选择一种“联动规则”（至少一种）：
      - color_follow_next: 若获得的徽章颜色属于给定集合，则与字典序后继交换（末尾与首位）。题面将给出固定顺序。
      - theme_link: 若获得的徽章主题为 src，则与当前持有 dst 的人交换（dst 在本题中唯一出现）。
    关键改动：
      - theme_link 仅在目标主题 dst 在 badges 中出现次数为 1 时启用，确保文本中的“当前持有‘dst’的人”为唯一持有者。
      - 需要字典序的规则将附带已计算好的排序序列。
    """
    present_colors = sorted({_extract_color(b) for b in badges if _extract_color(b)})
    themes_list = [_extract_theme(b) for b in badges if _extract_theme(b)]
    present_themes = sorted(set(themes_list))
    theme_counts: Dict[str, int] = {}
    for t in themes_list:
        theme_counts[t] = theme_counts.get(t, 0) + 1

    choices = []
    if len(present_colors) >= 1:
        choices.append('color_follow_next')
    unique_theme_candidates = [t for t, c in theme_counts.items() if c == 1]
    if len(present_themes) >= 2 and len(unique_theme_candidates) >= 1:
        choices.append('theme_link')

    if not choices:
        return {'type': 'none', 'meta': {}}

    if 'theme_link' in choices and random.random() < 0.6:
        t = 'theme_link'
    else:
        t = random.choice(choices)

    meta: Dict[str, Any] = {}
    if t == 'color_follow_next':
        k = 2 if len(present_colors) >= 2 else 1
        colors = random.sample(present_colors, k)
        meta['colors'] = colors
        meta['sorted'] = sorted(names)
    elif t == 'theme_link':
        dst = random.choice(unique_theme_candidates)
        src_pool = [x for x in present_themes if x != dst]
        if not src_pool:
            return {'type': 'color_follow_next', 'meta': {'colors': random.sample(present_colors, 1), 'sorted': sorted(names)}} if present_colors else {'type': 'none', 'meta': {}}
        src = random.choice(src_pool)
        meta['src'] = src
        meta['dst'] = dst
    return {'type': t, 'meta': meta}


def bonus_to_text(bonus_struct: Dict[str, Any]) -> str:
    t = bonus_struct.get('type')
    meta = bonus_struct.get('meta', {})
    if t == 'color_follow_next':
        colors = meta.get('colors', [])
        order = meta.get('sorted', [])
        order_str = '→'.join(order) if order else ''
        extra = f'（本题姓名字典序顺序：{order_str}）' if order_str else ''
        return f'联动规则：每当有人在任一步“主步骤”结束后获得的徽章颜色属于“{"、".join(colors)}”之一，该人须立即与“姓名按字典序紧随其后的那个人”交换；若该人按字典序位于最后，则改为与按字典序第一位的人交换；若不存在可选对象，则本联动规则不触发（该附加交换不再触发其他附加规则；每步先判定易变规则，再判定本联动规则）{extra}'
    elif t == 'theme_link':
        src = meta.get('src', '')
        dst = meta.get('dst', '')
        return f'联动规则：每当有人在任一步“主步骤”结束后获得的徽章主题为“{src}”，该人须立即与当前持有“{dst}”主题徽章的唯一持有者交换；若不存在可选对象，则本联动规则不触发（该附加交换不再触发其他附加规则；每步先判定易变规则，再判定本联动规则）'
    else:
        return '联动规则：本题无联动规则'


def gen_rules(names: List[str],
              badges: List[str],
              initial_pairs: List[List[str]],
              steps_num: int,
              volatile_badge: str) -> Dict[str, Any]:
    """
    混合生成步骤：
      - swap_holders: 持有 badge1 的人与持有 badge2 的人交换
      - swap_people: 指定两人交换
      - cycle3: 三人轮换（p1->p2, p2->p3, p3->p1）
      - cycle4: 四人轮换（p1->p2, p2->p3, p3->p4, p4->p1）
      - multi_swap: 两对或三对交换（题面对外文案：以下两两交换（按列出顺序逐一执行））
      - line_shift: 相邻交换链，如 [A,B,C] 则先 A↔B，再 B↔C
    """
    steps_num = max(10, steps_num)
    steps: List[Dict[str, Any]] = []

    def _pick_distinct_two(seq: List[str]) -> Tuple[str, str]:
        a, b = random.sample(seq, 2)
        return a, b

    def _pick_distinct_three(seq: List[str]) -> Tuple[str, str, str]:
        a, b, c = random.sample(seq, 3)
        return a, b, c

    def _pick_distinct_four(seq: List[str]) -> Tuple[str, str, str, str]:
        a, b, c, d = random.sample(seq, 4)
        return a, b, c, d

    # 先确保至少包含两类基础模板
    base_counts = {
        'swap_holders': random.randint(2, 3),
        'swap_people': random.randint(2, 3),
    }
    consumed = base_counts['swap_holders'] + base_counts['swap_people']

    # 必含一个 cycle3 或 cycle4
    include_cycle4 = random.random() < 0.5 and len(names) >= 4
    consumed += 1

    remaining = max(0, steps_num - consumed)

    # 1) 基础：swap_holders
    chosen_badge_pairs = set()
    for _ in range(base_counts['swap_holders']):
        b1, b2 = _pick_distinct_two(badges)
        key = tuple(sorted([b1, b2]))
        while key in chosen_badge_pairs:
            b1, b2 = _pick_distinct_two(badges)
            key = tuple(sorted([b1, b2]))
        chosen_badge_pairs.add(key)
        steps.append({'type': 'swap_holders', 'badge1': b1, 'badge2': b2})

    # 2) 基础：swap_people
    chosen_people_pairs = set()
    for _ in range(base_counts['swap_people']):
        p1, p2 = _pick_distinct_two(names)
        key = tuple(sorted([p1, p2]))
        while key in chosen_people_pairs:
            p1, p2 = _pick_distinct_two(names)
            key = tuple(sorted([p1, p2]))
        chosen_people_pairs.add(key)
        steps.append({'type': 'swap_people', 'p1': p1, 'p2': p2})

    # 3) 一个 cycle3 或 cycle4
    if include_cycle4:
        p1, p2, p3, p4 = _pick_distinct_four(names)
        steps.append({'type': 'cycle4', 'people': [p1, p2, p3, p4]})
    else:
        p1, p2, p3 = _pick_distinct_three(names)
        steps.append({'type': 'cycle3', 'people': [p1, p2, p3]})

    # 4) 用剩余步数填充高级模板
    advanced_templates = ['multi_swap', 'line_shift', 'swap_people', 'swap_holders']
    while remaining > 0:
        tpl = random.choice(advanced_templates)
        if tpl == 'multi_swap':
            # 2或3对
            num_pairs = random.choice([2, 3]) if len(names) >= 6 else 2
            pairs: List[Tuple[str, str]] = []
            pool = names[:]
            random.shuffle(pool)
            used: set = set()
            for _ in range(num_pairs):
                candidates = [x for x in pool if x not in used]
                if len(candidates) >= 2:
                    a, b = random.sample(candidates, 2)
                    used.add(a); used.add(b)
                    pairs.append((a, b))
            if len(pairs) >= 2:
                steps.append({'type': 'multi_swap', 'pairs': pairs})
                remaining -= 1
            else:
                a, b = _pick_distinct_two(names)
                steps.append({'type': 'swap_people', 'p1': a, 'p2': b})
                remaining -= 1

        elif tpl == 'line_shift':
            chain_len = random.choice([3, 4]) if len(names) >= 4 else 3
            chain = random.sample(names, chain_len)
            steps.append({'type': 'line_shift', 'people': chain})
            remaining -= 1

        elif tpl == 'swap_people':
            a, b = _pick_distinct_two(names)
            steps.append({'type': 'swap_people', 'p1': a, 'p2': b})
            remaining -= 1

        else:  # swap_holders
            b1, b2 = _pick_distinct_two(badges)
            steps.append({'type': 'swap_holders', 'badge1': b1, 'badge2': b2})
            remaining -= 1

    # 轻度洗牌以混排模板种类
    random.shuffle(steps)

    return {
        'volatile_badge': volatile_badge,
        'steps': steps
    }


def rules_to_text(rules_struct: Dict[str, Any], style: int) -> str:
    """
    渲染步骤，支持多种风格：
      style=0: [1] 描述；[2] 描述；...
      style=1: （一）描述；（二）描述；...
      style=2: 1) 描述；2) 描述；...
    """
    steps = rules_struct.get('steps', [])
    lines = []
    for idx, step in enumerate(steps, start=1):
        prefix = ''
        if style == 0:
            prefix = f'[{idx}] '
        elif style == 1:
            prefix = f'（{idx}）'
        else:
            prefix = f'{idx}) '
        t = step['type']
        if t == 'swap_holders':
            lines.append(f"{prefix}持有“{step['badge1']}”的人与持有“{step['badge2']}”的人交换")
        elif t == 'swap_people':
            lines.append(f"{prefix}“{step['p1']}”与“{step['p2']}”交换")
        elif t == 'cycle3':
            a, b, c = step['people']
            lines.append(f"{prefix}“{a}→{b}→{c}”三人轮换各自手中的徽章（{a}给{b}，{b}给{c}，{c}给{a}）")
        elif t == 'cycle4':
            a, b, c, d = step['people']
            lines.append(f"{prefix}“{a}→{b}→{c}→{d}”四人轮换各自手中的徽章（{a}给{b}，{b}给{c}，{c}给{d}，{d}给{a}）")
        elif t == 'multi_swap':
            pairs = step['pairs']
            pair_texts = [f'“{x}”与“{y}”' for x, y in pairs]
            lines.append(f"{prefix}以下两两交换（按列出顺序逐一执行）：{'；'.join(pair_texts)}")
        elif t == 'line_shift':
            chain = step['people']
            chain_text = '→'.join(chain)
            lines.append(f"{prefix}按序相邻交换链“{chain_text}”（依次进行相邻交换）")
        else:
            lines.append(f"{prefix}未知步骤")
    if style == 1:
        return '，'.join(lines)
    else:
        return '；'.join(lines)


def pairs_to_text(initial_pairs: List[List[str]], style: int) -> str:
    if style == 1:
        return '；'.join([f"{n}-{b}" for n, b in initial_pairs])
    else:
        return '，'.join([f"{n}-{b}" for n, b in initial_pairs])


def sample_format() -> str:
    # 提供一致格式示例（与题面命名体系一致的占位形式）
    return "('姓名-徽章', '姓名-徽章', '姓名-徽章', ...)"


def format_tuple(items: List[str]) -> str:
    return '(' + ', '.join([f"'{x}'" for x in items]) + ')'


# ---------- Internal helpers for execution ----------
def _build_mapping(initial_pairs: List[List[str]]) -> Dict[str, str]:
    return {name: badge for name, badge in initial_pairs}


def _find_holder_of(mapping: Dict[str, str], badge: str) -> str:
    for n, b in mapping.items():
        if b == badge:
            return n
    raise ValueError(f'Badge "{badge}" not found in current mapping')


def _swap_people(mapping: Dict[str, str], events: List[str], a: str, b: str) -> None:
    mapping[a], mapping[b] = mapping[b], mapping[a]
    events.append(a)
    events.append(b)


def _cycle_k(mapping: Dict[str, str], events: List[str], people: List[str]) -> None:
    # 通用轮换：p1->p2->...->pk->p1；完成者按链表最后一个名字计
    if len(people) < 2:
        return
    badges_seq = [mapping[p] for p in people]
    shifted = badges_seq[-1:] + badges_seq[:-1]
    for p, new_b in zip(people, shifted):
        mapping[p] = new_b
    events.extend(people)


def _line_shift(mapping: Dict[str, str], events: List[str], people: List[str]) -> None:
    # 相邻交换链：依次执行 (p[i], p[i+1]) 的交换；完成者为链表最后一个名字
    if len(people) < 2:
        return
    for i in range(len(people) - 1):
        a, b = people[i], people[i + 1]
        _swap_people(mapping, events, a, b)


def _last_other(events: List[str], exclude_name: str) -> str:
    # 返回“最近一次完成交换的人（不等于 exclude_name）”；若不存在则空字符串
    for n in reversed(events):
        if n != exclude_name:
            return n
    return ''


def compute_final_badges(initial_pairs: List[List[str]],
                         rules_struct: Dict[str, Any],
                         hazard_struct: Dict[str, Any],
                         bonus_struct: Dict[str, Any]) -> List[str]:
    """
    返回：按 initial_pairs 的原始姓名顺序输出 '姓名-徽章' 字符串列表
    执行逻辑（每一步）：
      1) 完成主步骤交换
      2) 若“易变徽章”在主步骤后更换持有者，按 hazard 规则执行一次附加交换（不再触发其他附加规则）
      3) 按“主步骤导致的直接新徽章”判断联动规则，若触发，对触发者执行一次附加交换（不再触发其他附加规则）
         若本步主步骤产生多名获得新徽章者，则按“初始分配”名单顺序从前至后逐一判定执行
    """
    result, _ = _simulate_and_stats(initial_pairs, rules_struct, hazard_struct, bonus_struct)
    return result


# ---------- Simulation with stats for uniqueness check ----------
def _simulate_and_stats(initial_pairs: List[List[str]],
                        rules_struct: Dict[str, Any],
                        hazard_struct: Dict[str, Any],
                        bonus_struct: Dict[str, Any]) -> Tuple[List[str], Dict[str, int]]:
    mapping = _build_mapping(initial_pairs)
    events: List[str] = []  # 全局事件序列（记录完成交换的先后）
    volatile = rules_struct.get('volatile_badge')
    steps = rules_struct.get('steps', [])
    prev_step_participants: List[str] = []

    hazard_count = 0
    bonus_count = 0

    # 固定的姓名顺序（题面可见）：用于多触发者的执行顺序
    names_order = [name for name, _ in initial_pairs]
    name_index = {n: i for i, n in enumerate(names_order)}

    def _hazard_target(new_holder: str) -> str:
        t = hazard_struct.get('type')
        meta = hazard_struct.get('meta', {})
        if t == 'last_finisher':
            # 最近一次完成交换者；若就是自己则找倒数第二位；若不存在则不触发
            target = _last_other(events, new_holder)
            return target
        elif t == 'alpha_next':
            # 使用题面固定的字典序
            sorted_names = meta.get('sorted', [])
            if not sorted_names:
                sorted_names = sorted([n for n, _ in initial_pairs])
            if new_holder not in sorted_names:
                return ''
            i = sorted_names.index(new_holder)
            j = (i + 1) % len(sorted_names)
            return sorted_names[j] if sorted_names[j] != new_holder else ''
        elif t == 'prev_step_other':
            # 上一步参与交换且不同名者的“最后完成者”（包含附加交换）
            for n in reversed(prev_step_participants):
                if n != new_holder:
                    return n
            return ''
        else:
            return ''

    def _bonus_target(taker: str, new_badge_of_main: str) -> str:
        t = bonus_struct.get('type')
        meta = bonus_struct.get('meta', {})
        if t == 'color_follow_next':
            colors = meta.get('colors', [])
            color = _extract_color(new_badge_of_main)
            if color and color in colors:
                sorted_names = meta.get('sorted', [])
                if not sorted_names:
                    sorted_names = sorted([n for n, _ in initial_pairs])
                if taker not in sorted_names:
                    return ''
                i = sorted_names.index(taker)
                j = (i + 1) % len(sorted_names)
                return sorted_names[j] if sorted_names[j] != taker else ''
            return ''
        elif t == 'theme_link':
            src = meta.get('src', '')
            dst = meta.get('dst', '')
            theme = _extract_theme(new_badge_of_main)
            if src and dst and theme == src:
                # 找持有 dst 主题徽章的人（唯一）
                for p, b in mapping.items():
                    if _extract_theme(b) == dst and p != taker:
                        return p
            return ''
        else:
            return ''

    for step in steps:
        this_step_participants: List[str] = []

        # 记录主步骤前映射
        prev_mapping_before_main = dict(mapping)

        # 主步骤执行
        stype = step.get('type')
        if stype == 'swap_holders':
            b1, b2 = step['badge1'], step['badge2']
            h1 = _find_holder_of(mapping, b1)
            h2 = _find_holder_of(mapping, b2)
            _swap_people(mapping, events, h1, h2)
            this_step_participants.extend([h1, h2])

        elif stype == 'swap_people':
            p1, p2 = step['p1'], step['p2']
            _swap_people(mapping, events, p1, p2)
            this_step_participants.extend([p1, p2])

        elif stype == 'cycle3':
            a, b, c = step['people']
            _cycle_k(mapping, events, [a, b, c])
            this_step_participants.extend([a, b, c])

        elif stype == 'cycle4':
            a, b, c, d = step['people']
            _cycle_k(mapping, events, [a, b, c, d])
            this_step_participants.extend([a, b, c, d])

        elif stype == 'multi_swap':
            pairs = step['pairs']
            for a, b in pairs:
                _swap_people(mapping, events, a, b)
                this_step_participants.extend([a, b])

        elif stype == 'line_shift':
            chain = step['people']
            _line_shift(mapping, events, chain)
            this_step_participants.extend(chain)

        # 记录主步骤完成后的映射（用于确定“主步骤直接获得的新徽章”）
        mapping_after_main = dict(mapping)

        # 易变规则：若易变徽章持有者在主步骤后改变，则立即执行一次附加交换（不连锁）
        try:
            prev_holder = _find_holder_of(prev_mapping_before_main, volatile)
            new_holder = _find_holder_of(mapping_after_main, volatile)
        except Exception:
            prev_holder = ''
            new_holder = ''
        if new_holder and new_holder != prev_holder:
            partner = _hazard_target(new_holder)
            if partner and partner != new_holder:
                _swap_people(mapping, events, new_holder, partner)
                this_step_participants.extend([new_holder, partner])
                hazard_count += 1

        # 联动规则：对“主步骤直接获得新徽章的人”逐个判定（不连锁）
        changed_people = [p for p in mapping_after_main if mapping_after_main[p] != prev_mapping_before_main[p]]
        changed_people_sorted = sorted(changed_people, key=lambda x: name_index.get(x, 10**9))
        for taker in changed_people_sorted:
            new_badge_main = mapping_after_main[taker]
            partner2 = _bonus_target(taker, new_badge_main)
            if partner2 and partner2 != taker:
                _swap_people(mapping, events, taker, partner2)
                this_step_participants.extend([taker, partner2])
                bonus_count += 1

        prev_step_participants = this_step_participants[:]

    names_order = [name for name, _ in initial_pairs]
    result = [f'{n}-{mapping[n]}' for n in names_order]
    stats = {'hazard': hazard_count, 'bonus': bonus_count}
    return result, stats


def verify_unique_solution(initial_pairs: List[List[str]],
                           rules_struct: Dict[str, Any],
                           hazard_struct: Dict[str, Any],
                           bonus_struct: Dict[str, Any]) -> bool:
    """
    唯一性与有效性验证（高效）：
      - 重复独立模拟两次结果必须一致（确定性检查）
      - 结果需构成姓名到徽章的一一对应（双射）
      - 至少一次触发“易变规则”或“联动规则”（提升推理价值）
    """
    r1, s1 = _simulate_and_stats(initial_pairs, rules_struct, hazard_struct, bonus_struct)
    r2, s2 = _simulate_and_stats(initial_pairs, rules_struct, hazard_struct, bonus_struct)
    if r1 != r2:
        return False
    # 双射检查
    names_order = [name for name, _ in initial_pairs]
    badges = [x.split('-', 1)[1] for x in r1]
    if len(set(names_order)) != len(names_order):
        return False
    if len(set(badges)) != len(badges):
        return False
    # 至少一次触发
    if (s1.get('hazard', 0) + s1.get('bonus', 0)) < 1:
        return False
    return True