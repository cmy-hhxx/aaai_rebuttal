# object_properties_0.py

import random
from copy import deepcopy

# -----------------------------
# Basic random helpers
# -----------------------------
def pick_one(seq):
    """Return a random element from a non-empty sequence."""
    return random.choice(list(seq))

def pick_k_distinct(seq, k):
    """Return k distinct elements from seq."""
    if k > len(seq):
        k = len(seq)
    return random.sample(list(seq), k)

# -----------------------------
# Formatting helpers for compact answers
# -----------------------------
def format_list_compact(lst):
    """
    Render a Python list of ints as a compact string without spaces, e.g., [1,3,5].
    """
    if not isinstance(lst, (list, tuple)):
        return '[]'
    try:
        return '[' + ','.join(str(int(x)) for x in lst) + ']'
    except Exception:
        return '[' + ','.join(str(x) for x in lst) + ']'

def format_dict_parenthesized(dct):
    """
    Render a dict[str,int] to a parenthesized string with single quotes and one leading/trailing space:
    ( '金色':7,'蓝色':12,'红色':4 )
    The key order follows the insertion order of dct (which we ensure equals band_colors order).
    """
    if not isinstance(dct, dict):
        return '( )'
    parts = []
    for k in list(dct.keys()):
        parts.append("'" + str(k) + "':" + str(int(dct[k])))
    return '( ' + ','.join(parts) + ' )'

def format_items_text_compact_cn(items):
    """
    Render initial items list into a compact single-line Chinese string:
    1:尺寸=小,产地=法国,材质=玻璃,气味=玫瑰,类别=瓶子；2:尺寸=...
    """
    if not isinstance(items, list):
        return ''
    segs = []
    for i, it in enumerate(items, start=1):
        segs.append(f"{i}:尺寸={it.get('size')},产地={it.get('origin')},材质={it.get('material')},气味={it.get('smell')},类别={it.get('type')}")
    return '；'.join(segs)

# -----------------------------
# Sequence generator
# -----------------------------
def gen_color_seq_cn(item_num, band_colors, band_counts):
    """
    Generate initial color sequence by 3 bands.
    band_colors: list[str] of length 3
    band_counts: list[int] of length 3, sum == item_num and each >= 1
    """
    if len(band_colors) != 3 or len(band_counts) != 3:
        raise ValueError('band_colors and band_counts must be length 3')
    if sum(band_counts) != item_num:
        raise ValueError('Sum of band_counts must equal item_num')
    if any(c <= 0 for c in band_counts):
        raise ValueError('Each band count must be positive')
    seq = []
    for color, cnt in zip(band_colors, band_counts):
        seq.extend([color] * cnt)
    return seq

# -----------------------------
# Rule system with enforced linkage and depth
# -----------------------------
def gen_rules_cn(sizes_pool, origins_pool, materials_pool, smells_pool, types_pool, colors_pool, band_colors, rule_num):
    """
    Generate a list of 4 rule blocks (dict) with enforced linkage:
      - Exactly two 'set' rules first
      - Exactly one 'swap' rule next
      - Exactly one 'recolor_by_count' LAST
    Linkage:
      - The trigger of set rule #2 is taken from one of the actions of set rule #1 (same field & value).
      - The trigger of the swap rule is taken from one of the actions of set rule #1 or #2.
    Additional constraints:
      - For 'color' triggers, trigger value chosen from band_colors to guarantee initial presence.
      - Set rules only modify NON-COLOR attributes to reduce ambiguity.
      - Ensure at least ONE action among the two 'set' rules modifies 'material' to enhance linkage with recolor parity.
    """
    rnum = 4  # force to 4 rules for depth

    pools = {
        'size': list(sizes_pool),
        'origin': list(origins_pool),
        'material': list(materials_pool),
        'smell': list(smells_pool),
        'type': list(types_pool),
        'color': list(colors_pool),
    }

    trigger_fields_candidates = ['material', 'origin', 'type', 'color', 'size']
    # 设置规则动作不包含 color
    action_fields_candidates = ['smell', 'size', 'origin', 'material', 'type']

    # 1) First set rule
    trig_field_1 = pick_one(trigger_fields_candidates)
    trig_value_1 = pick_one(band_colors) if trig_field_1 == 'color' else pick_one(pools[trig_field_1])
    act_num_1 = 2 if random.random() < 0.7 else 1
    actions_1 = []
    used_fields_1 = set()
    for _a in range(act_num_1):
        af_candidates = [f for f in action_fields_candidates if f not in used_fields_1]
        af = pick_one(af_candidates)
        used_fields_1.add(af)
        av = pick_one(pools[af])
        actions_1.append({'field': af, 'value': av})
    set_rule_1 = {
        'kind': 'set',
        'trigger': {'field': trig_field_1, 'value': trig_value_1},
        'actions': actions_1
    }

    # 2) Second set rule: trigger must be one of actions from rule #1
    action_ref = pick_one(actions_1)
    trig_field_2 = action_ref['field']
    trig_value_2 = action_ref['value']
    act_num_2 = 2 if random.random() < 0.7 else 1
    actions_2 = []
    used_fields_2 = {trig_field_2}  # avoid modifying trigger field
    for _a in range(act_num_2):
        af_candidates = [f for f in action_fields_candidates if f not in used_fields_2]
        af = pick_one(af_candidates)
        used_fields_2.add(af)
        av = pick_one(pools[af])
        actions_2.append({'field': af, 'value': av})
    set_rule_2 = {
        'kind': 'set',
        'trigger': {'field': trig_field_2, 'value': trig_value_2},
        'actions': actions_2
    }

    # Ensure at least one material modification across the two set rules
    if not any(a['field'] == 'material' for a in (actions_1 + actions_2)):
        if actions_2:
            actions_2[-1] = {'field': 'material', 'value': pick_one(pools['material'])}
        else:
            actions_2.append({'field': 'material', 'value': pick_one(pools['material'])})
        set_rule_2['actions'] = actions_2

    # 3) Swap rule: trigger chosen from actions of set #1 or #2 (non-color by construction)
    action_union = actions_1 + actions_2
    swap_ref = pick_one(action_union)
    trig_field_swap = swap_ref['field']
    trig_value_swap = swap_ref['value']
    swap_rule = {
        'kind': 'swap',
        'trigger': {'field': trig_field_swap, 'value': trig_value_swap},
    }

    rules = [set_rule_1, set_rule_2, swap_rule]

    # 4) Recolor rule LAST: target_band_color from band_colors
    target_band_color = pick_one(band_colors)
    recolor_rule = {
        'kind': 'recolor_by_count',
        'trigger': {'field': 'color', 'value': target_band_color}
    }
    rules.append(recolor_rule)

    return rules

def _field_cn(field):
    """Chinese name mapping for fields."""
    mapping = {
        'material': '材质',
        'size': '尺寸',
        'color': '颜色',
        'smell': '气味',
        'origin': '产地',
        'type': '类别',
    }
    return mapping.get(field, field)

def format_rules_legend_cn(rules):
    """
    Render rule type legends for kinds present in this instance.
    """
    present = {r['kind'] for r in rules}
    legend_texts = []
    legend_texts.append('执行顺序说明：先两条【设置】，再【交换】，最后【重着色】；同一设置规则内多项动作按列出顺序依次生效；所有判断与修改均基于即时最新状态')

    if 'set' in present:
        legend_texts.append('【设置】当触发条件满足时，按给出的动作逐项改值（只更改非颜色属性，不直接改颜色；每条设置规则依次执行且顺序固定）')
    if 'swap' in present:
        legend_texts.append('【交换】当触发条件满足时，按索引从小到大依序处理所有触发位置（命中位置在执行交换前一次性确定），将该物品的颜色与相邻物品交换（默认与右侧交换，若无右侧邻居则与左侧交换；每个命中索引仅交换一次；每次交换立即生效并影响后续处理）')
    if 'recolor_by_count' in present:
        legend_texts.append('【重着色】在前三条规则（两条设置与交换）执行完毕后最后执行：将所有目标颜色的物品重新着色——以此时列表中材质为‘金属’的物品总数的奇偶性决定（奇数改为灰色，偶数改为紫色；若新色与目标色相同，则颜色保持不变）')

    return '规则类型说明：' + ('；'.join(legend_texts) + '。' if legend_texts else '。')

def format_rules_text_cn(rules):
    """
    Render human-friendly Chinese text for the rule list with explicit type labels.
    """
    def idx_word(i):
        table = ['其一', '其二', '其三', '其四', '其五', '其六', '其七', '其八', '其九']
        return table[i] if i < len(table) else f'其{i+1}'

    label = {
        'set': '【设置】',
        'swap': '【交换】',
        'recolor_by_count': '【重着色】',
    }

    parts = []
    for i, r in enumerate(rules):
        head = idx_word(i) + '，' + label.get(r['kind'], '')
        k = r['kind']
        trig = r.get('trigger', {})
        tf = trig.get('field')
        tv = trig.get('value')
        if k == 'set':
            action_texts = []
            for act in r['actions']:
                action_texts.append(f"将{_field_cn(act['field'])}改为{act['value']}")
            actions_str = '，并'.join([action_texts[0]] + action_texts[1:]) if len(action_texts) > 1 else action_texts[0]
            parts.append(f"{head}如果物品的{_field_cn(tf)}为{tv}，则{actions_str}")
        elif k == 'swap':
            parts.append(f"{head}如果物品的{_field_cn(tf)}为{tv}，则按索引从小到大依序处理所有触发位置（命中位置在执行交换前一次性确定），将该物品的颜色与其相邻物品的颜色交换（默认与右侧交换，若无右侧邻居则与左侧交换）")
        elif k == 'recolor_by_count':
            parts.append(f"{head}在前三条规则执行完毕后最后执行：将所有颜色为{tv}的物品重新着色——以此时列表中材质为‘金属’的物品总数的奇偶性决定（奇数改为灰色，偶数改为紫色；若新色与目标色相同，则颜色保持不变）")
    txt = '；'.join(parts) + '。' if parts else '。'
    return txt

# -----------------------------
# Base items generator (ensures triggers presence + swap depth)
# -----------------------------
def gen_items_general_cn(item_num, sizes_pool, origins_pool, materials_pool, smells_pool, types_pool, rules_list):
    """
    Generate base items ensuring:
      - For triggers on material/origin/type/size: force at least one item with that value.
      - For swap trigger: ensure at least TWO positions hit before applying rules to increase depth.
      - For 'color' triggers: initial colors guaranteed by band_colors; ignore here.
    """
    items = []
    for _ in range(item_num):
        it = {
            'size': pick_one(sizes_pool),
            'origin': pick_one(origins_pool),
            'material': pick_one(materials_pool),
            'smell': pick_one(smells_pool),
            'type': pick_one(types_pool),
        }
        items.append(it)

    required_simple = []
    swap_trigger = None
    for r in rules_list:
        trig = r.get('trigger', {})
        f = trig.get('field')
        v = trig.get('value')
        if r.get('kind') == 'swap':
            swap_trigger = (f, v)
        if f in ['material', 'origin', 'type', 'size'] and v is not None:
            required_simple.append((f, v))

    for f, v in required_simple:
        if not any(it.get(f) == v for it in items):
            idx = random.randrange(len(items))
            items[idx][f] = v

    if swap_trigger is not None:
        f, v = swap_trigger
        if f in ['material', 'origin', 'type', 'size']:
            positions = [i for i, it in enumerate(items) if it.get(f) == v]
            while len(positions) < 2 and len(items) > 1:
                candidate_indices = [i for i in range(len(items)) if items[i].get(f) != v]
                if not candidate_indices:
                    break
                idx = pick_one(candidate_indices)
                items[idx][f] = v
                positions.append(idx)

    return items

# -----------------------------
# Core apply (extended with pre-swap stats)
# -----------------------------
def _apply_rules_extended(items_base, color_seq, rules_list, sizes_pool):
    """
    Apply rules sequentially:
      Step 0: assign initial color by color_seq
      Then apply set, swap, recolor_by_count in order.
    Returns:
      final_items: list of item dicts
      stats: dict with counts and pre-swap info
      items_step0: items after color assignment
    """
    items_step0 = []
    for i, base in enumerate(items_base):
        it = dict(base)
        it['color'] = color_seq[i]
        items_step0.append(it)

    current = deepcopy(items_step0)
    stats = {
        'set_counts': [],
        'swap_counts': [],
        'swap_positions_before': 0,
        'recolor_hits': [],
        'recolor_changed': [],
    }

    for idx, r in enumerate(rules_list):
        kind = r['kind']
        trig = r.get('trigger', {})
        tf = trig.get('field')
        tv = trig.get('value')

        if kind == 'set':
            cnt = 0
            for it in current:
                if it.get(tf) == tv:
                    for act in r['actions']:
                        it[act['field']] = act['value']
                    cnt += 1
            stats['set_counts'].append(cnt)

        elif kind == 'swap':
            positions = [i for i, it in enumerate(current) if it.get(tf) == tv]
            stats['swap_positions_before'] = len(positions)
            cnt = 0
            colors = [it.get('color') for it in current]
            for i in positions:
                j = i + 1 if i + 1 < len(current) else i - 1 if i - 1 >= 0 else None
                if j is not None and j != i:
                    colors[i], colors[j] = colors[j], colors[i]
                    cnt += 1
            for i, it in enumerate(current):
                it['color'] = colors[i]
            stats['swap_counts'].append(cnt)

        elif kind == 'recolor_by_count':
            metal_cnt = sum(1 for it in current if it.get('material') == '金属')
            new_color = '灰色' if (metal_cnt % 2 == 1) else '紫色'
            hits = 0
            changed = 0
            for it in current:
                if it.get('color') == tv:
                    hits += 1
                    if new_color != tv:
                        it['color'] = new_color
                        changed += 1
            stats['recolor_hits'].append(hits)
            stats['recolor_changed'].append(changed)

        else:
            pass

    return current, stats, items_step0

# -----------------------------
# Criteria & formatting
# -----------------------------
def gen_criteria_cn(sizes_pool, origins_pool, materials_pool, smells_pool, colors_pool, cond_num):
    """
    Generate a list of OR-criteria with distinct attribute categories.
    cond_num in [3,4], categories from: material, size, color, smell, origin.
    """
    fields = ['material', 'size', 'color', 'smell', 'origin']
    if cond_num < 1:
        cond_num = 1
    if cond_num > len(fields):
        cond_num = len(fields)
    chosen_fields = random.sample(fields, cond_num)

    mapping = {
        'material': materials_pool,
        'size': sizes_pool,
        'color': colors_pool,
        'smell': smells_pool,
        'origin': origins_pool,
    }
    criteria = []
    for f in chosen_fields:
        v = pick_one(mapping[f])
        criteria.append({'field': f, 'value': v})
    return criteria

def format_criteria_text_cn(criteria_list):
    """
    Convert criteria list to human-readable Chinese string joined by '，或'.
    """
    cname = {
        'material': '材质为',
        'size': '尺寸为',
        'color': '颜色为',
        'smell': '气味为',
        'origin': '产地为',
    }
    parts = [f"{cname[c['field']]}{c['value']}" for c in criteria_list]
    return '，或'.join(parts)

# -----------------------------
# Qualification helpers
# -----------------------------
def _qualifies(item, criteria_list):
    """Return True if item satisfies any criterion in criteria_list."""
    for c in criteria_list:
        if item.get(c['field']) == c['value']:
            return True
    return False

def _count_qualifies(items, criteria_list):
    return sum(1 for it in items if _qualifies(it, criteria_list))

# -----------------------------
# Extended computations
# -----------------------------
def compute_final_count_cn_extended(items_base, color_seq, rules_list, criteria_list, sizes_pool):
    """
    Compute final count of items satisfying at least one criterion after applying rules.
    """
    final_items, _, _ = _apply_rules_extended(items_base, color_seq, rules_list, sizes_pool)
    return _count_qualifies(final_items, criteria_list)

def compute_top_indices_cn(items_base, color_seq, rules_list, criteria_list, sizes_pool):
    """
    Compute the smallest up to 5 indices (1-based, ascending) of items qualifying after rules.
    """
    final_items, _, _ = _apply_rules_extended(items_base, color_seq, rules_list, sizes_pool)
    idxs = [i + 1 for i, it in enumerate(final_items) if _qualifies(it, criteria_list)]
    idxs.sort()
    return idxs[:5]

def compute_band_color_counts_cn(items_base, color_seq, rules_list, band_colors, sizes_pool):
    """
    Compute final counts for the three initial band colors (by final color labels).
    Keys strictly follow the band_colors order (band1, band2, band3).
    """
    final_items, _, _ = _apply_rules_extended(items_base, color_seq, rules_list, sizes_pool)
    counts = {c: 0 for c in band_colors}
    for it in final_items:
        c = it.get('color')
        if c in counts:
            counts[c] += 1
    return counts

# -----------------------------
# Validation (extended + uniqueness, stabilized)
# -----------------------------
def validate_puzzle_cn_extended_unique(items_base, color_seq, rules_list, criteria_list,
                                       ans_count, ans_indices, ans_dict, sizes_pool, band_colors):
    """
    Validate scenario and uniqueness under rules:
      - Answers match recomputation.
      - 至少两条设置规则有效（命中数>0）。
      - 交换规则前的命中位置数量至少为2，且有非零交换次数。
      - 重着色规则必存在且目标命中数量>0。
      - 非平凡性：最终与初始在数量或属性或颜色分布上有变化。
      - 边界：1 <= ans_count <= 3 * item_num_pre；最终列表长度不变。
      - 扰动测试：小幅改变条件有至少2种不同的计数结果。
      - 分段颜色计数字典的键顺序必须严格等于 band_colors（题面出现顺序）。
      - q2 长度一致性：len(ans_indices) == min(ans_count, 5)，并且索引合法。
    """
    final_items, stats, items_step0 = _apply_rules_extended(items_base, color_seq, rules_list, sizes_pool)
    recomputed_count = _count_qualifies(final_items, criteria_list)
    if recomputed_count != ans_count:
        return False

    recomputed_indices = [i + 1 for i, it in enumerate(final_items) if _qualifies(it, criteria_list)]
    recomputed_indices.sort()
    if recomputed_indices[:5] != ans_indices:
        return False

    # q2 length consistency and bounds
    expected_len = min(ans_count, 5)
    if len(ans_indices) != expected_len:
        return False
    if any((not isinstance(x, int)) or x < 1 or x > len(items_base) for x in ans_indices):
        return False

    # Band color dict keys must match band_colors order exactly
    if list(ans_dict.keys()) != list(band_colors):
        return False

    # Verify band color counts
    counter = {k: 0 for k in band_colors}
    for it in final_items:
        c = it.get('color')
        if c in counter:
            counter[c] += 1
    for k in band_colors:
        if counter.get(k, 0) != int(ans_dict[k]):
            return False

    # Rule impacts
    set_effects = sum(1 for c in stats['set_counts'] if c > 0)
    swap_effects = sum(1 for c in stats['swap_counts'] if c > 0)
    recolor_present = any(r['kind'] == 'recolor_by_count' for r in rules_list)
    recolor_hits_total = sum(stats['recolor_hits']) if recolor_present else 0

    if set_effects < 2:
        return False
    # strengthened: require pre-swap hit positions >= 2
    if stats['swap_positions_before'] < 2:
        return False
    if swap_effects < 1:
        return False
    if not recolor_present or recolor_hits_total < 1:
        return False

    # Non-triviality
    initial_count = _count_qualifies(items_step0, criteria_list)
    changed_structure = (len(final_items) != len(items_step0))
    changed_attrs = False
    if not changed_structure:
        for i in range(len(final_items)):
            a = final_items[i]
            b = items_step0[i]
            for f in ['size','origin','material','smell','type','color']:
                if a.get(f) != b.get(f):
                    changed_attrs = True
                    break
            if changed_attrs:
                break
    if (initial_count == recomputed_count) and (not changed_structure) and (not changed_attrs):
        return False

    # Bounds
    item_num_pre = len(items_base)
    if not (1 <= ans_count <= 3 * item_num_pre):
        return False
    if len(final_items) > 3 * item_num_pre:
        return False

    # Mutation tests
    distinct_counts = set()
    for _ in range(6):
        if not criteria_list:
            break
        crit = deepcopy(criteria_list)
        idx = random.randrange(len(crit))
        f = crit[idx]['field']
        pools_map = {
            'material': ['陶瓷','玻璃','金属','布','纸','混凝土','木头','钛','塑料'],
            'size': ['超超小','超小','小','中','大','超大'],
            'color': ['金色','黄色','黑色','米色','红色','蓝色','绿色','白色','紫色','橙色','灰色','棕色'],
            'smell': ['香草','巧克力','咖啡','玫瑰','大蒜','烤面包','燃烧的木头','薄荷','海风','泥土'],
            'origin': ['意大利','德国','葡萄牙','墨西哥','加拿大','俄罗斯','土耳其','西班牙','法国','日本','巴西','印度','中国','英国','美国','澳大利亚'],
        }
        pool = pools_map.get(f, [])
        if pool:
            alt_candidates = [v for v in pool if v != crit[idx]['value']]
            alt = pick_one(alt_candidates) if alt_candidates else crit[idx]['value']
            crit[idx]['value'] = alt
        count_mut = _count_qualifies(final_items, crit)
        distinct_counts.add(count_mut)
    if len(distinct_counts) < 2:
        return False

    return True

# -----------------------------
# Final answer composer (for robust evaluation)
# -----------------------------
def compile_final_answer_cn(items_base, color_seq, rules_list, criteria_list, sizes_pool, band_colors):
    """
    Compose the final answer string: '<count>====[i1,i2,...]====( 'C1':x,'C2':y,'C3':z )'
    """
    count = compute_final_count_cn_extended(items_base, color_seq, rules_list, criteria_list, sizes_pool)
    indices = compute_top_indices_cn(items_base, color_seq, rules_list, criteria_list, sizes_pool)
    color_counts = compute_band_color_counts_cn(items_base, color_seq, rules_list, band_colors, sizes_pool)
    return str(count) + '====' + format_list_compact(indices) + '====' + format_dict_parenthesized(color_counts)