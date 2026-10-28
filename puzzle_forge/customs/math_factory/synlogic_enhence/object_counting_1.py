# Filename: object_counting_5.py
import random
from typing import Dict, List, Tuple, Union, Optional

Step = str  # 'received' | 'scrapped' | 'sent' | 'returned'


def generate_weekly_events(weeks: int, category: str) -> Dict[str, List[int]]:
    """
    Generate weekly event sequences for a given category.
    Keys: 'received', 'scrapped', 'sent', 'returned'
    """
    if not isinstance(weeks, int) or weeks < 1:
        raise ValueError('weeks must be a positive integer')
    if category not in ('suits', 'rovers'):
        raise ValueError('category must be "suits" or "rovers"')

    # Category-specific ranges to diversify distributions
    if category == 'suits':
        rcv_range = (40, 120)
        scrap_range = (0, 25)
        sent_range = (0, 40)
        ret_range = (0, 20)
    else:  # rovers
        rcv_range = (5, 20)
        scrap_range = (0, 6)
        sent_range = (0, 10)
        ret_range = (0, 5)

    def gen_seq(lo: int, hi: int) -> List[int]:
        return [random.randint(lo, hi) for _ in range(weeks)]

    events = {
        'received': gen_seq(*rcv_range),
        'scrapped': gen_seq(*scrap_range),
        'sent': gen_seq(*sent_range),
        'returned': gen_seq(*ret_range),
    }
    return events


def generate_rule_order() -> List[Step]:
    """
    Randomize the weekly update order.
    Always include subtractive steps 'scrapped' and 'sent'.
    Randomly include 'returned' or not. 'received' is always included.
    Shuffle the chosen steps.
    """
    steps = ['received', 'scrapped', 'sent']
    if random.random() < 0.7:
        steps.append('returned')
    random.shuffle(steps)
    return steps


def generate_cap_policy() -> Dict[Step, bool]:
    """
    Policy for subtractive steps. Keep it simple and consistent:
    subtractive steps are capped to current stock. Additive steps are ignored here.
    """
    return {'scrapped': True, 'sent': True}


def compute_final_inventory(initial_count: Union[int, float],
                            events: Dict[str, List[int]],
                            rule_order: Optional[List[Step]] = None,
                            cap_policy: Optional[Dict[Step, bool]] = None) -> int:
    """
    Compute final inventory following a configurable per-week order. Supported steps:
    - received: add
    - scrapped: subtract (capped if policy says so)
    - sent: subtract (capped if policy says so)
    - returned: add
    """
    if not isinstance(initial_count, int):
        raise TypeError('initial_count must be int')
    for k in ('received', 'scrapped', 'sent', 'returned'):
        if k not in events or not isinstance(events[k], list):
            raise ValueError('events must contain lists for received, scrapped, sent, returned')
        if any((not isinstance(x, int) or x < 0) for x in events[k]):
            raise ValueError('event lists must contain non-negative integers')

    weeks = len(events['received'])
    if any(len(events[k]) != weeks for k in events):
        raise ValueError('all event lists must have the same length')

    if rule_order is None:
        rule_order = ['received', 'scrapped', 'sent', 'returned']
    if cap_policy is None:
        cap_policy = {'scrapped': True, 'sent': True}

    valid_steps = {'received', 'scrapped', 'sent', 'returned'}
    if any(step not in valid_steps for step in rule_order):
        raise ValueError('rule_order contains invalid steps')

    stock = int(initial_count)
    for i in range(weeks):
        for step in rule_order:
            if step == 'received':
                stock += events['received'][i]
            elif step == 'scrapped':
                v = events['scrapped'][i]
                if cap_policy.get('scrapped', True):
                    v = min(v, stock)
                stock -= v
            elif step == 'sent':
                v = events['sent'][i]
                if cap_policy.get('sent', True):
                    v = min(v, stock)
                stock -= v
            elif step == 'returned':
                stock += events['returned'][i]
            if stock < 0:
                stock = 0
    return int(stock)


def compute_inventory_diff(suits_final: Union[int, float], rovers_final: Union[int, float]) -> int:
    """
    Absolute difference of final inventories between suits and rovers.
    """
    if not isinstance(suits_final, int) or not isinstance(rovers_final, int):
        raise TypeError('Inputs must be integers')
    return abs(suits_final - rovers_final)


def total_changes_summary(seq: List[int]) -> str:
    """
    Render a list of integers as a single string separated by Chinese comma '，'
    to avoid using English quotes in desc templates.
    """
    if not isinstance(seq, list) or any(not isinstance(x, int) for x in seq):
        raise TypeError('seq must be a list of integers')
    return '，'.join(str(x) for x in seq)


def format_rule_order_text(rule_order: List[Step]) -> str:
    """
    Convert rule order into a natural Chinese sentence:
    e.g., '每周的库存更新顺序为先到货，再报废，然后调拨，最后退回'
    """
    cn = {
        'received': '到货',
        'scrapped': '报废',
        'sent': '调拨',
        'returned': '退回'
    }
    n = len(rule_order)
    if n == 0:
        return '每周的库存更新顺序为空'
    parts = []
    for idx, step in enumerate(rule_order):
        word = cn.get(step, step)
        if idx == 0:
            parts.append(f'先{word}')
        elif idx < n - 1:
            parts.append(f'再{word}' if idx == 1 else f'然后{word}')
        else:
            parts.append(f'最后{word}')
    return '每周的库存更新顺序为' + '，'.join(parts)


def render_category_events_text(events: Dict[str, List[int]], rule_order: List[Step]) -> str:
    """
    Only render the sequences for steps actually used in rule_order.
    e.g., '到货为1，2，3，报废为0，1，0，调拨为5，4，3'
    """
    label = {
        'received': '到货',
        'scrapped': '报废',
        'sent': '调拨',
        'returned': '退回'
    }
    segs = []
    for step in rule_order:
        segs.append(f"{label.get(step, step)}为{total_changes_summary(events[step])}")
    return '，'.join(segs)


def pick_category_names() -> Tuple[str, str]:
    """
    Randomly pick a pair of category names for suits and rovers.
    """
    candidates = [
        ('防护服', '探测车'),
        ('太空服', '巡视车'),
        ('作业服', '月面车'),
        ('防护服', '月面车'),
        ('太空服', '探测车')
    ]
    return random.choice(candidates)


def compare_final(suits_final: int, rovers_final: int, suits_label: str, rovers_label: str) -> str:
    """
    Compare final counts: return suits_label if suits > rovers,
    rovers_label if rovers > suits, else 'equal'.
    """
    if suits_final > rovers_final:
        return suits_label
    if rovers_final > suits_final:
        return rovers_label
    return 'equal'


def pack_finals(suits_final: int, rovers_final: int) -> List[int]:
    """
    Return both finals as a list [suits_final, rovers_final].
    """
    return [int(suits_final), int(rovers_final)]


def compute_dual_final(initial_suits: int,
                       initial_rovers: int,
                       suits_events: Dict[str, List[int]],
                       rovers_events: Dict[str, List[int]],
                       rule_order: List[Step],
                       cap_policy: Optional[Dict[Step, bool]],
                       coupling_policy: Dict[str, int],
                       maintenance_plan: List[Optional[str]]) -> Dict[str, Union[int, List[int]]]:
    """
    Dual-category weekly simulation with coupling and maintenance:
    - Per week, apply steps in rule_order to each category
      - If the category is under maintenance in that week: scrapped doubles, returned ignored
      - For subtractive steps, cap by current stock if cap_policy says so
    - After both categories updated in a week, apply emergency share once:
      - If A < safety_A and B > reserve_B, transfer min(share_cap, B - reserve_B, safety_A - A)
      - Else if B < safety_B and A > reserve_A, similar reverse
      - Otherwise no transfer
    Returns: dict with suits_final, rovers_final, transfer_weeks (1-based), weekly_total
    """
    # Basic checks
    for ev in (suits_events, rovers_events):
        for k in ('received', 'scrapped', 'sent', 'returned'):
            if k not in ev or not isinstance(ev[k], list):
                raise ValueError('events must contain lists for received, scrapped, sent, returned')
            if any((not isinstance(x, int) or x < 0) for x in ev[k]):
                raise ValueError('event lists must contain non-negative integers')
    weeks = len(suits_events['received'])
    if any(len(suits_events[k]) != weeks for k in suits_events) or any(len(rovers_events[k]) != weeks for k in rovers_events):
        raise ValueError('all event lists must have the same length')
    if not isinstance(maintenance_plan, list) or len(maintenance_plan) != weeks:
        raise ValueError('maintenance_plan must be a list with length == weeks')

    valid_steps = {'received', 'scrapped', 'sent', 'returned'}
    if any(step not in valid_steps for step in rule_order):
        raise ValueError('invalid step in rule_order')

    if cap_policy is None:
        cap_policy = {'scrapped': True, 'sent': True}

    # Coupling params
    s_safe = int(coupling_policy['suits_safety'])
    r_safe = int(coupling_policy['rovers_safety'])
    s_resv = int(coupling_policy['suits_reserve'])
    r_resv = int(coupling_policy['rovers_reserve'])
    share_cap = int(coupling_policy['share_cap'])

    s_stock = int(initial_suits)
    r_stock = int(initial_rovers)
    transfer_weeks: List[int] = []
    weekly_total: List[int] = []

    for i in range(weeks):
        m_target = maintenance_plan[i]  # 'suits', 'rovers', or None

        # suits
        for step in rule_order:
            if step == 'received':
                v = suits_events['received'][i]
                s_stock += v
            elif step == 'scrapped':
                v = suits_events['scrapped'][i]
                if m_target == 'suits':
                    v *= 2
                if cap_policy.get('scrapped', True):
                    v = min(v, s_stock)
                s_stock -= v
            elif step == 'sent':
                v = suits_events['sent'][i]
                if cap_policy.get('sent', True):
                    v = min(v, s_stock)
                s_stock -= v
            elif step == 'returned':
                v = suits_events['returned'][i]
                if m_target == 'suits':
                    v = 0
                s_stock += v
            if s_stock < 0:
                s_stock = 0

        # rovers
        for step in rule_order:
            if step == 'received':
                v = rovers_events['received'][i]
                r_stock += v
            elif step == 'scrapped':
                v = rovers_events['scrapped'][i]
                if m_target == 'rovers':
                    v *= 2
                if cap_policy.get('scrapped', True):
                    v = min(v, r_stock)
                r_stock -= v
            elif step == 'sent':
                v = rovers_events['sent'][i]
                if cap_policy.get('sent', True):
                    v = min(v, r_stock)
                r_stock -= v
            elif step == 'returned':
                v = rovers_events['returned'][i]
                if m_target == 'rovers':
                    v = 0
                r_stock += v
            if r_stock < 0:
                r_stock = 0

        # Emergency share (one-direction per week)
        if s_stock < s_safe and r_stock > r_resv:
            transfer = min(share_cap, r_stock - r_resv, s_safe - s_stock)
            if transfer > 0:
                s_stock += transfer
                r_stock -= transfer
                transfer_weeks.append(i + 1)
        elif r_stock < r_safe and s_stock > s_resv:
            transfer = min(share_cap, s_stock - s_resv, r_safe - r_stock)
            if transfer > 0:
                r_stock += transfer
                s_stock -= transfer
                transfer_weeks.append(i + 1)

        weekly_total.append(int(s_stock + r_stock))

    return {
        'suits_final': int(s_stock),
        'rovers_final': int(r_stock),
        'transfer_weeks': transfer_weeks,
        'weekly_total': weekly_total
    }


def format_coupling_text(suits_label: str,
                         rovers_label: str,
                         coupling_policy: Dict[str, int]) -> str:
    """
    Render the coupling policy to natural language, no trailing punctuation here.
    """
    s_safe = coupling_policy['suits_safety']
    r_safe = coupling_policy['rovers_safety']
    s_resv = coupling_policy['suits_reserve']
    r_resv = coupling_policy['rovers_reserve']
    share_cap = coupling_policy['share_cap']
    return (
        f'每周所有步骤执行完成后，若{suits_label}库存低于{s_safe}且{rovers_label}库存高于{r_resv}，'
        f'则从{rovers_label}向{suits_label}进行紧急调剂，单周最多调剂{share_cap}；'
        f'调剂不会让{rovers_label}跌破{r_resv}，且不会超过将{suits_label}拉回到{s_safe}所需的数量。'
        f'若{rovers_label}低于{r_safe}且{suits_label}高于{s_resv}，则方向相反；'
        f'每周至多发生一次且仅单向执行；若不满足条件则不调剂'
    )


def generate_maintenance_plan(weeks: int,
                              suits_label: str,
                              rovers_label: str) -> Dict[str, Union[List[Optional[str]], str]]:
    """
    Randomly generate maintenance weeks and targets.
    plan: a list of length weeks with values in {'suits','rovers',None}
    text: human-readable summary
    Rule on a maintenance week for the target:
      - scrapped doubles
      - returned is ignored
    """
    if weeks < 1:
        raise ValueError('weeks must be positive')
    m_count = random.randint(1, max(1, weeks // 2))
    chosen_weeks = sorted(random.sample(list(range(1, weeks + 1)), m_count))
    plan: List[Optional[str]] = [None] * weeks
    segments: List[str] = []
    for w in chosen_weeks:
        target = 'suits' if random.random() < 0.5 else 'rovers'
        plan[w - 1] = target
        label = suits_label if target == 'suits' else rovers_label
        segments.append(f'第{w}周对{label}执行维护，报废翻倍且退回忽略')
    text = '；'.join(segments) if segments else f'本期不安排维护'
    return {'plan': plan, 'text': text}


def generate_coupling_policy(weeks: int,
                             initial_suits: int,
                             initial_rovers: int,
                             suits_events: Dict[str, List[int]],
                             rovers_events: Dict[str, List[int]],
                             rule_order: List[Step],
                             cap_policy: Dict[Step, bool],
                             maintenance_plan: List[Optional[str]]) -> Dict[str, int]:
    """
    Construct coupling thresholds/reserves/share_cap ensuring at least one transfer occurs
    under the ACTUAL maintenance plan. Additionally ensure safety thresholds are >= 1
    for clearer, reasonable text.
    Strategy:
    1) Simulate per-week stocks without coupling using maintenance_plan.
    2) Pick a week where one category is low and the other has room; set safety/reserve accordingly.
    3) Validate by running compute_dual_final with constructed policy. If still no transfer, fallback to
       short random sampling under maintenance_plan until a transfer occurs.
    """
    def simulate_no_coupling(init_s: int, init_r: int) -> Tuple[List[int], List[int]]:
        s_stock = int(init_s)
        r_stock = int(init_r)
        s_list: List[int] = []
        r_list: List[int] = []
        valid_steps = {'received', 'scrapped', 'sent', 'returned'}
        if any(step not in valid_steps for step in rule_order):
            raise ValueError('invalid step in rule_order')

        for i in range(weeks):
            m_target = maintenance_plan[i]
            for step in rule_order:
                if step == 'received':
                    s_stock += suits_events['received'][i]
                elif step == 'scrapped':
                    v = suits_events['scrapped'][i]
                    if m_target == 'suits':
                        v *= 2
                    if cap_policy.get('scrapped', True):
                        v = min(v, s_stock)
                    s_stock -= v
                elif step == 'sent':
                    v = suits_events['sent'][i]
                    if cap_policy.get('sent', True):
                        v = min(v, s_stock)
                    s_stock -= v
                elif step == 'returned':
                    v = suits_events['returned'][i]
                    if m_target == 'suits':
                        v = 0
                    s_stock += v
                if s_stock < 0:
                    s_stock = 0
            for step in rule_order:
                if step == 'received':
                    r_stock += rovers_events['received'][i]
                elif step == 'scrapped':
                    v = rovers_events['scrapped'][i]
                    if m_target == 'rovers':
                        v *= 2
                    if cap_policy.get('scrapped', True):
                        v = min(v, r_stock)
                    r_stock -= v
                elif step == 'sent':
                    v = rovers_events['sent'][i]
                    if cap_policy.get('sent', True):
                        v = min(v, r_stock)
                    r_stock -= v
                elif step == 'returned':
                    v = rovers_events['returned'][i]
                    if m_target == 'rovers':
                        v = 0
                    r_stock += v
                if r_stock < 0:
                    r_stock = 0
            s_list.append(int(s_stock))
            r_list.append(int(r_stock))
        return s_list, r_list

    s_traj, r_traj = simulate_no_coupling(initial_suits, initial_rovers)

    def construct_policy() -> Optional[Dict[str, int]]:
        # Prefer ensuring a forward transfer suits <- rovers
        candidates = [(i, s_traj[i], r_traj[i]) for i in range(weeks) if r_traj[i] > 0]
        if candidates:
            i_min = min(candidates, key=lambda t: t[1])[0]
            s_safe = max(1, s_traj[i_min] + random.randint(1, 3))
            r_resv = max(0, r_traj[i_min] - random.randint(1, min(5, r_traj[i_min])))
            share_cap = random.randint(5, 20)
            # keep a small positive rover safety to avoid "低于0" in text
            r_safe = max(1, r_traj[i_min] // 10)
            s_resv = random.randint(0, max(0, s_safe - 1))
            policy = {
                'suits_safety': int(max(s_resv + 1, s_safe)),
                'rovers_safety': int(max(1, r_safe)),
                'suits_reserve': int(s_resv),
                'rovers_reserve': int(r_resv),
                'share_cap': int(share_cap)
            }
            return policy

        # Or ensure a reverse transfer rovers <- suits
        candidates2 = [(i, r_traj[i], s_traj[i]) for i in range(weeks) if s_traj[i] > 0]
        if candidates2:
            i_min = min(candidates2, key=lambda t: t[0])[0]
            r_safe = max(1, r_traj[i_min] + random.randint(1, 3))
            s_resv = max(0, s_traj[i_min] - random.randint(1, min(5, s_traj[i_min])))
            share_cap = random.randint(5, 20)
            s_safe = max(1, s_traj[i_min] // 10)
            r_resv = random.randint(0, max(0, r_safe - 1))
            policy = {
                'suits_safety': int(max(1, s_safe)),
                'rovers_safety': int(max(r_resv + 1, r_safe)),
                'suits_reserve': int(s_resv),
                'rovers_reserve': int(r_resv),
                'share_cap': int(share_cap)
            }
            return policy

        return None

    policy = construct_policy()
    if policy is not None:
        res = compute_dual_final(
            initial_suits, initial_rovers,
            suits_events, rovers_events,
            rule_order, cap_policy,
            policy,
            maintenance_plan
        )
        if len(res['transfer_weeks']) > 0:
            return policy

    def try_policy_random() -> Dict[str, int]:
        s_safe = random.randint(max(30, initial_suits // 5), max(80, initial_suits * 3 // 5))
        r_safe = random.randint(max(8, initial_rovers // 5), max(30, initial_rovers * 3 // 5))
        s_resv = random.randint(0, max(10, s_safe // 2))
        r_resv = random.randint(0, max(8, r_safe // 2))
        s_resv = min(s_resv, max(s_safe - 1, 0))
        r_resv = min(r_resv, max(r_safe - 1, 0))
        share_cap = random.randint(5, 20)
        return {
            'suits_safety': int(max(1, s_resv + 1, s_safe)),
            'rovers_safety': int(max(1, r_resv + 1, r_safe)),
            'suits_reserve': int(s_resv),
            'rovers_reserve': int(r_resv),
            'share_cap': int(share_cap)
        }

    policy = None
    for _ in range(100):
        candidate = try_policy_random()
        res = compute_dual_final(
            initial_suits, initial_rovers,
            suits_events, rovers_events,
            rule_order, cap_policy,
            candidate,
            maintenance_plan
        )
        if len(res['transfer_weeks']) > 0:
            policy = candidate
            break

    if policy is None:
        s_min = min(s_traj) if s_traj else 0
        r_max = max(r_traj) if r_traj else 0
        policy = {
            'suits_safety': int(max(1, s_min + 1)),
            'rovers_safety': 1,
            'suits_reserve': 0,
            'rovers_reserve': int(max(0, r_max - 1)),
            'share_cap': 10
        }

    return policy


def validate_scenario_extended(weeks: int,
                               suits_events: Dict[str, List[int]],
                               rovers_events: Dict[str, List[int]],
                               initial_suits: int,
                               initial_rovers: int,
                               rule_order: List[Step],
                               cap_policy: Optional[Dict[Step, bool]],
                               coupling_policy: Dict[str, int],
                               maintenance_plan: List[Optional[str]]) -> bool:
    """
    Extended validation including:
    - types, lengths, non-negativity
    - rule_order validity and no duplication, and must include both subtractive steps
    - maintenance plan length and values
    - a full run without errors; results non-negative
    """
    try:
        if not isinstance(weeks, int) or weeks < 1:
            return False
        if not isinstance(initial_suits, int) or not isinstance(initial_rovers, int):
            return False
        valid_steps = {'received', 'scrapped', 'sent', 'returned'}
        if (not isinstance(rule_order, list)) or any(s not in valid_steps for s in rule_order):
            return False
        if len(set(rule_order)) != len(rule_order):
            return False
        # enforce both subtractive steps are present
        if 'scrapped' not in rule_order or 'sent' not in rule_order:
            return False
        # check events
        for ev in (suits_events, rovers_events):
            for k in ('received', 'scrapped', 'sent', 'returned'):
                if k not in ev or not isinstance(ev[k], list):
                    return False
                if len(ev[k]) != weeks:
                    return False
                if any((not isinstance(x, int) or x < 0) for x in ev[k]):
                    return False
        # check maintenance plan
        if not isinstance(maintenance_plan, list) or len(maintenance_plan) != weeks:
            return False
        for x in maintenance_plan:
            if x not in (None, 'suits', 'rovers'):
                return False
        # check coupling policy fields
        for key in ('suits_safety', 'rovers_safety', 'suits_reserve', 'rovers_reserve', 'share_cap'):
            if key not in coupling_policy:
                return False
            if not isinstance(coupling_policy[key], int) or coupling_policy[key] < 0:
                return False
        # run one simulation
        res = compute_dual_final(
            initial_suits, initial_rovers,
            suits_events, rovers_events,
            rule_order, cap_policy or {'scrapped': True, 'sent': True},
            coupling_policy,
            maintenance_plan
        )
        if res['suits_final'] < 0 or res['rovers_final'] < 0:
            return False
        return True
    except Exception:
        return False


def unique_solution_guard(weeks: int,
                          initial_suits: int,
                          initial_rovers: int,
                          suits_events: Dict[str, List[int]],
                          rovers_events: Dict[str, List[int]],
                          rule_order: List[Step],
                          cap_policy: Dict[Step, bool],
                          coupling_policy: Dict[str, int],
                          maintenance_plan: List[Optional[str]]) -> bool:
    """
    Guard for uniqueness and non-triviality:
    - Determinism: rerun and compare results
    - Non-triviality: at least one transfer occurred
    """
    try:
        res1 = compute_dual_final(
            initial_suits, initial_rovers,
            suits_events, rovers_events,
            rule_order, cap_policy,
            coupling_policy,
            maintenance_plan
        )
        res2 = compute_dual_final(
            initial_suits, initial_rovers,
            suits_events, rovers_events,
            rule_order, cap_policy,
            coupling_policy,
            maintenance_plan
        )
        if (res1['suits_final'] != res2['suits_final'] or
                res1['rovers_final'] != res2['rovers_final'] or
                res1['transfer_weeks'] != res2['transfer_weeks']):
            return False
        if len(res1['transfer_weeks']) == 0:
            return False
        return True
    except Exception:
        return False