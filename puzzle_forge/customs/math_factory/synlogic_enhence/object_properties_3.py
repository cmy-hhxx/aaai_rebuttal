# object_properties_5.py
import random
from copy import deepcopy

# --------------------------
# Supersets for attributes
# --------------------------
SIZES = ['超小', '小', '中', '大', '特大']
MATERIALS = ['玻璃', '陶瓷', '金属', '塑料', '木', '石']
COLORS = ['蓝', '黑', '银', '绿', '白', '红', '米色', '紫', '棕']
SCENTS = ['薄荷', '海盐', '柠檬', '樟脑', '松木', '丁香', '檀香']
OCEANS = ['北大西洋', '南太平洋', '印度洋', '北冰洋', '南大西洋', '北太平洋']
LABELS = ['A', 'B', 'C', 'D']

# --------------------------
# Random subset generators
# --------------------------
def gen_size_values():
    k = random.choice([3, 4, 5])
    return sorted(random.sample(SIZES, k), key=lambda x: SIZES.index(x))

def gen_material_values():
    k = random.choice([3, 4, 5])
    return random.sample(MATERIALS, k)

def gen_color_values():
    k = random.choice([4, 6, 7])
    return random.sample(COLORS, k)

def gen_scent_values():
    k = random.choice([3, 4, 5])
    return random.sample(SCENTS, k)

def gen_ocean_values():
    k = random.choice([3, 4, 5])
    return random.sample(OCEANS, k)

def gen_label_values():
    k = random.choice([2, 3, 4])
    return random.sample(LABELS, k)

# --------------------------
# Helpers
# --------------------------
def _choose_distinct(pool, avoid=None):
    avail = [x for x in pool if (avoid is None or x != avoid)]
    if not avail:
        return random.choice(pool)
    return random.choice(avail)

def _rand_from(pool):
    return random.choice(pool)

def _make_random_item(next_id, size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals):
    return {
        'id': next_id,
        '尺寸': _rand_from(size_vals),
        '材质': _rand_from(material_vals),
        '颜色': _rand_from(color_vals),
        '气味': _rand_from(scent_vals),
        '海域': _rand_from(ocean_vals),
        '标签': _rand_from(label_vals),
    }

def _next_id(current_list):
    if not current_list:
        return 1
    return max(item.get('id', 0) for item in current_list) + 1

def _sort_by_id(items):
    return sorted(items, key=lambda it: it.get('id', 0))

# --------------------------
# Transform spec generator (v2)
# --------------------------
def gen_transform_spec(size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals):
    return gen_transform_spec_v2(size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals)

def gen_transform_spec_v2(size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals):
    """
    基础规则集：update_by_material, replace_by_ocean, clone_by_size, merge_by_label
    另保证至少一条可选规则：recolor_by_ocean / swap_colors / relocate_label_by_material / retag_by_ocean / swap_labels
    同时定义谓词：mode ∈ {or, and}，clauses 2-4 条，字段覆盖多属性。
    """
    # 基础规则参数
    mat_a = random.choice(material_vals)
    upd_color = random.choice(color_vals)
    upd_scent = random.choice(scent_vals)

    ocean_from = random.choice(ocean_vals)
    ocean_b = _choose_distinct(ocean_vals, avoid=ocean_from)

    size_b = random.choice(size_vals)
    mat_b = random.choice(material_vals)
    color_b = random.choice(color_vals)
    scent_b = random.choice(scent_vals)
    label_b = random.choice(label_vals)

    size_c = random.choice(size_vals)
    clone_fields_pool = ['颜色', '海域', '气味']
    f1, f2 = random.sample(clone_fields_pool, 2)
    v1 = random.choice(color_vals if f1 == '颜色' else ocean_vals if f1 == '海域' else scent_vals)
    v2 = random.choice(color_vals if f2 == '颜色' else ocean_vals if f2 == '海域' else scent_vals)

    merge_label = random.choice(label_vals)
    merged_attrs = {
        '尺寸': random.choice(size_vals),
        '材质': random.choice(material_vals),
        '颜色': random.choice(color_vals),
        '气味': random.choice(scent_vals),
        '海域': random.choice(ocean_vals),
        '标签': random.choice(label_vals)
    }

    # 可选规则参数
    ocean2 = _choose_distinct(ocean_vals, avoid=ocean_from)
    recolor_target = random.choice(color_vals)

    if len(color_vals) >= 2:
        color_a, color_b2 = random.sample(color_vals, 2)
    else:
        color_a, color_b2 = color_b, recolor_target

    mat2 = _choose_distinct(material_vals, avoid=mat_a)
    new_label_for_mat2 = _choose_distinct(label_vals, avoid=merge_label)

    ocean3 = random.choice(ocean_vals)
    new_label_ocean3 = _choose_distinct(label_vals, avoid=merge_label)

    if len(label_vals) >= 2:
        l1, l2 = random.sample(label_vals, 2)
    else:
        l1, l2 = label_b, _choose_distinct(label_vals, avoid=label_b)

    rules = []
    rules.append({
        'type': 'update_by_material',
        'material_trigger': mat_a,
        'updates': {'颜色': upd_color, '气味': upd_scent}
    })
    rules.append({
        'type': 'replace_by_ocean',
        'ocean_from': ocean_from,
        'new_attrs': {'尺寸': size_b, '材质': mat_b, '颜色': color_b, '气味': scent_b, '海域': ocean_b, '标签': label_b}
    })
    rules.append({
        'type': 'clone_by_size',
        'size_trigger': size_c,
        'edits': [{'field': f1, 'value': v1}, {'field': f2, 'value': v2}]
    })
    rules.append({
        'type': 'merge_by_label',
        'merge_label': merge_label,
        'merged_attrs': merged_attrs
    })

    # 强制至少一条可选规则
    optional = random.choice(['recolor_by_ocean', 'swap_colors', 'relocate_label_by_material', 'retag_by_ocean', 'swap_labels'])
    if optional == 'recolor_by_ocean':
        rules.append({
            'type': 'recolor_by_ocean',
            'ocean': ocean2,
            'color': recolor_target
        })
    elif optional == 'swap_colors':
        rules.append({
            'type': 'swap_colors',
            'color_a': color_a,
            'color_b': color_b2
        })
    elif optional == 'relocate_label_by_material':
        rules.append({
            'type': 'relocate_label_by_material',
            'material': mat2,
            'new_label': new_label_for_mat2
        })
    elif optional == 'retag_by_ocean':
        rules.append({
            'type': 'retag_by_ocean',
            'ocean': ocean3,
            'new_label': new_label_ocean3
        })
    elif optional == 'swap_labels':
        rules.append({
            'type': 'swap_labels',
            'label_a': l1,
            'label_b': l2
        })

    # 初始谓词（仅占位，实际会被校准函数改写以保证非平凡）
    all_fields = ['材质', '颜色', '气味', '海域', '标签', '尺寸']
    k = random.choice([2, 3, 4])
    chosen_fields = random.sample(all_fields, k)
    clauses = []
    for fld in chosen_fields:
        pool = (material_vals if fld == '材质' else
                color_vals if fld == '颜色' else
                scent_vals if fld == '气味' else
                ocean_vals if fld == '海域' else
                label_vals if fld == '标签' else
                size_vals)
        clauses.append({'field': fld, 'value': random.choice(pool)})
    mode = random.choice(['or', 'and'])

    return {
        'rules': rules,
        'predicate': {'mode': mode, 'clauses': clauses}
    }

def get_predicate(tf_spec):
    return tf_spec['predicate']

def get_predicate_clause_num_v2(tf_spec_or_pred):
    pred = tf_spec_or_pred['predicate'] if isinstance(tf_spec_or_pred, dict) and 'predicate' in tf_spec_or_pred else tf_spec_or_pred
    return len(pred.get('clauses', []))

# --------------------------
# Initial sample construction (v2) — 强化为“必有非空效果”
# --------------------------
def _collect_requirements(rules):
    reqs = []
    for r in rules:
        t = r['type']
        if t == 'update_by_material':
            reqs.append({'need': {'材质': r['material_trigger']}, 'type': t, 'ensure': {'颜色_not': r['updates']['颜色'], '气味_not': r['updates']['气味']}})
        elif t == 'replace_by_ocean':
            reqs.append({'need': {'海域': r['ocean_from']}, 'type': t})
        elif t == 'clone_by_size':
            reqs.append({'need': {'尺寸': r['size_trigger']}, 'type': t})
        elif t == 'merge_by_label':
            reqs.append({'need': {'标签': r['merge_label']}, 'type': t})
        elif t == 'recolor_by_ocean':
            reqs.append({'need': {'海域': r['ocean']}, 'type': t, 'ensure': {'颜色_not': r['color']}})
        elif t == 'swap_colors':
            reqs.append({'need': {'颜色': r['color_a']}, 'type': t})
            reqs.append({'need': {'颜色': r['color_b']}, 'type': t})
        elif t == 'relocate_label_by_material':
            reqs.append({'need': {'材质': r['material']}, 'type': t, 'ensure': {'标签_not': r['new_label']}})
        elif t == 'retag_by_ocean':
            reqs.append({'need': {'海域': r['ocean']}, 'type': t, 'ensure': {'标签_not': r['new_label']}})
        elif t == 'swap_labels':
            reqs.append({'need': {'标签': r['label_a']}, 'type': t})
            reqs.append({'need': {'标签': r['label_b']}, 'type': t})
    return reqs

def build_initial_samples(n, size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals, tf_spec):
    return build_initial_samples_v2(n, size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals, tf_spec)

def build_initial_samples_v2(n, size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals, tf_spec):
    rules = tf_spec['rules']
    reqs = _collect_requirements(rules)
    items = []
    nid = 1

    # 先满足各规则需求样本，并确保“有效果”
    for req in reqs:
        need = req['need']
        it = _make_random_item(nid, size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals)
        for k, v in need.items():
            it[k] = v
        # 按类型强制避免无效变换
        ens = req.get('ensure', {})
        if '颜色_not' in ens:
            it['颜色'] = _choose_distinct(color_vals, avoid=ens['颜色_not'])
        if '气味_not' in ens:
            it['气味'] = _choose_distinct(scent_vals, avoid=ens['气味_not'])
        if '标签_not' in ens:
            it['标签'] = _choose_distinct(label_vals, avoid=ens['标签_not'])
        items.append(it)
        nid += 1
        if len(items) >= n:
            break

    # 补齐数量，并增加一定概率的合并标签
    merge_label = None
    for r in rules:
        if r['type'] == 'merge_by_label':
            merge_label = r['merge_label']
            break

    while len(items) < n:
        it = _make_random_item(nid, size_vals, material_vals, color_vals, scent_vals, ocean_vals, label_vals)
        if merge_label and random.random() < 0.30:
            it['标签'] = merge_label
        items.append(it)
        nid += 1

    return items

# --------------------------
# Transform application (v2) — 确定性的 ID 规则与处理顺序
# --------------------------
def apply_transforms(samples, tf_spec):
    return apply_transforms_v2(samples, tf_spec)

def apply_transforms_v2(samples, tf_spec):
    current = deepcopy(samples)
    rules = tf_spec['rules']

    for r in rules:
        # 每步开始前，按 ID 升序处理集合
        current = _sort_by_id(current)
        t = r['type']

        if t == 'update_by_material':
            mat_a = r['material_trigger']
            updates = r['updates']
            # 修改不改变 ID，按 ID 升序遍历
            for it in current:
                if it['材质'] == mat_a:
                    for k, v in updates.items():
                        it[k] = v

        elif t == 'replace_by_ocean':
            ocean_from = r['ocean_from']
            new_attrs = r['new_attrs']
            # 删除满足条件的样本，其 ID 不保留；新样本 ID 从当前最大值+1 递增
            to_replace = [it for it in current if it['海域'] == ocean_from]
            remain = [it for it in current if it['海域'] != ocean_from]
            remain = _sort_by_id(remain)
            count = len(to_replace)
            nid = _next_id(remain)
            new_items = []
            for _ in range(count):
                new_item = {'id': nid}
                new_item.update(new_attrs)
                new_items.append(new_item)
                nid += 1
            current = remain + new_items

        elif t == 'clone_by_size':
            size_c = r['size_trigger']
            edits = r['edits']
            # 按源样本 ID 升序逐个处理：先生成应用第一个编辑的副本，再生成应用第二个编辑的副本
            clones = []
            src = [it for it in current if it['尺寸'] == size_c]
            src = _sort_by_id(src)
            nid = _next_id(current)
            for it in src:
                c1 = deepcopy(it); c1['id'] = nid; nid += 1
                c2 = deepcopy(it); c2['id'] = nid; nid += 1
                c1[edits[0]['field']] = edits[0]['value']
                c2[edits[1]['field']] = edits[1]['value']
                clones.extend([c1, c2])
            current = current + clones

        elif t == 'merge_by_label':
            merge_label = r['merge_label']
            merged_attrs = r['merged_attrs']
            merge_group = [it for it in current if it['标签'] == merge_label]
            others = [it for it in current if it['标签'] != merge_label]
            others = _sort_by_id(others)
            if merge_group:
                nid = _next_id(others)
                merged = {'id': nid}
                merged.update(merged_attrs)
                current = others + [merged]
            else:
                current = others

        elif t == 'recolor_by_ocean':
            oc = r['ocean']
            new_c = r['color']
            for it in current:
                if it['海域'] == oc:
                    it['颜色'] = new_c

        elif t == 'swap_colors':
            ca, cb = r['color_a'], r['color_b']
            for it in current:
                if it['颜色'] == ca:
                    it['颜色'] = cb
                elif it['颜色'] == cb:
                    it['颜色'] = ca

        elif t == 'relocate_label_by_material':
            m = r['material']
            new_label = r['new_label']
            for it in current:
                if it['材质'] == m:
                    it['标签'] = new_label

        elif t == 'retag_by_ocean':
            oc = r['ocean']
            new_label = r['new_label']
            for it in current:
                if it['海域'] == oc:
                    it['标签'] = new_label

        elif t == 'swap_labels':
            la, lb = r['label_a'], r['label_b']
            for it in current:
                if it['标签'] == la:
                    it['标签'] = lb
                elif it['标签'] == lb:
                    it['标签'] = la

        # 每步结束后，按 ID 升序排序
        current = _sort_by_id(current)

    return current

# --------------------------
# Effects statistics and validation — 与 apply 同步的确定性顺序
# --------------------------
def _apply_and_count_effects(samples, tf_spec):
    current = deepcopy(samples)
    rules = tf_spec['rules']
    effects = []

    for r in rules:
        current = _sort_by_id(current)
        t = r['type']

        if t == 'update_by_material':
            mat_a = r['material_trigger']
            updates = r['updates']
            cnt = 0
            for it in current:
                if it['材质'] == mat_a:
                    # 计算变更数量（至少一个字段变更）
                    changed = False
                    for k, v in updates.items():
                        if it.get(k) != v:
                            changed = True
                        it[k] = v
                    if changed:
                        cnt += 1
            effects.append(cnt)

        elif t == 'replace_by_ocean':
            ocean_from = r['ocean_from']
            new_attrs = r['new_attrs']
            to_replace = [it for it in current if it['海域'] == ocean_from]
            remain = [it for it in current if it['海域'] != ocean_from]
            remain = _sort_by_id(remain)
            count = len(to_replace)
            nid = _next_id(remain)
            new_items = []
            for _ in range(count):
                new_item = {'id': nid}
                new_item.update(new_attrs)
                new_items.append(new_item)
                nid += 1
            current = remain + new_items
            effects.append(count)

        elif t == 'clone_by_size':
            size_c = r['size_trigger']
            edits = r['edits']
            clones = []
            src = [it for it in current if it['尺寸'] == size_c]
            src = _sort_by_id(src)
            nid = _next_id(current)
            for it in src:
                c1 = deepcopy(it); c1['id'] = nid; nid += 1
                c2 = deepcopy(it); c2['id'] = nid; nid += 1
                c1[edits[0]['field']] = edits[0]['value']
                c2[edits[1]['field']] = edits[1]['value']
                clones.extend([c1, c2])
            current = current + clones
            effects.append(len(clones))

        elif t == 'merge_by_label':
            merge_label = r['merge_label']
            merged_attrs = r['merged_attrs']
            merge_group = [it for it in current if it['标签'] == merge_label]
            others = [it for it in current if it['标签'] != merge_label]
            others = _sort_by_id(others)
            cnt = len(merge_group)
            if merge_group:
                nid = _next_id(others)
                merged = {'id': nid}
                merged.update(merged_attrs)
                current = others + [merged]
            else:
                current = others
            effects.append(cnt)

        elif t == 'recolor_by_ocean':
            oc = r['ocean']
            new_c = r['color']
            cnt = 0
            for it in current:
                if it['海域'] == oc and it['颜色'] != new_c:
                    it['颜色'] = new_c
                    cnt += 1
            effects.append(cnt)

        elif t == 'swap_colors':
            ca, cb = r['color_a'], r['color_b']
            cnt = 0
            for it in current:
                if it['颜色'] == ca:
                    it['颜色'] = cb
                    cnt += 1
                elif it['颜色'] == cb:
                    it['颜色'] = ca
                    cnt += 1
            effects.append(cnt)

        elif t == 'relocate_label_by_material':
            m = r['material']
            new_label = r['new_label']
            cnt = 0
            for it in current:
                if it['材质'] == m and it['标签'] != new_label:
                    it['标签'] = new_label
                    cnt += 1
            effects.append(cnt)

        elif t == 'retag_by_ocean':
            oc = r['ocean']
            new_label = r['new_label']
            cnt = 0
            for it in current:
                if it['海域'] == oc and it['标签'] != new_label:
                    it['标签'] = new_label
                    cnt += 1
            effects.append(cnt)

        elif t == 'swap_labels':
            la, lb = r['label_a'], r['label_b']
            cnt = 0
            for it in current:
                if it['标签'] == la:
                    it['标签'] = lb
                    cnt += 1
                elif it['标签'] == lb:
                    it['标签'] = la
                    cnt += 1
            effects.append(cnt)

        current = _sort_by_id(current)

    return effects, current

def effects_nonempty(samples, tf_spec):
    effects, _ = _apply_and_count_effects(samples, tf_spec)
    return all(cnt >= 1 for cnt in effects)

# --------------------------
# Counting and summaries
# --------------------------
def count_satisfying(samples, predicate):
    return count_satisfying_v2(samples, predicate)

def count_satisfying_v2(samples, predicate):
    clauses = predicate.get('clauses', [])
    mode = predicate.get('mode', 'or')
    total = 0
    for it in samples:
        if mode == 'or':
            ok = any(it.get(cl['field']) == cl['value'] for cl in clauses)
        else:
            ok = all(it.get(cl['field']) == cl['value'] for cl in clauses)
        if ok:
            total += 1
    return total

def compute_ids_satisfying_v2(samples, predicate):
    """
    返回满足谓词的样本ID升序列表。
    """
    res = []
    clauses = predicate.get('clauses', [])
    mode = predicate.get('mode', 'or')
    for it in samples:
        if mode == 'or':
            ok = any(it.get(cl['field']) == cl['value'] for cl in clauses)
        else:
            ok = all(it.get(cl['field']) == cl['value'] for cl in clauses)
        if ok:
            res.append(it['id'])
    return sorted(res)

def label_counts_v2(samples):
    """
    返回标签计数字典，如 {'A': 3, 'B': 2}
    """
    counts = {}
    for it in samples:
        lab = it['标签']
        counts[lab] = counts.get(lab, 0) + 1
    return counts

def pick_top_label_v2(label_counts):
    """
    返回出现次数最多的标签；若有并列，选择字母升序最靠前者。
    """
    if not label_counts:
        return ''
    max_count = max(label_counts.values())
    candidates = [lab for lab, c in label_counts.items() if c == max_count]
    return sorted(candidates)[0]

def get_total_count(samples):
    return len(samples)

def validate_answer_range(count_value, total_count):
    """
    保证答案非平凡：1 <= count_value <= total_count - 1
    """
    if total_count <= 1:
        return False
    return (count_value >= 1) and (count_value <= (total_count - 1))

def summarize_samples(samples):
    parts = []
    for it in sorted(samples, key=lambda x: x.get('id', 0)):
        parts.append(f"{it['id']}: {it['尺寸']}, {it['材质']}, {it['颜色']}, {it['气味']}, {it['海域']}, {it['标签']}")
    return '; '.join(parts)

# --------------------------
# Text builders
# --------------------------
def build_transform_desc(tf_spec):
    return build_transform_desc_v2(tf_spec)

def build_transform_desc_v2(tf_spec):
    rules = tf_spec['rules']
    letters = 'abcdefghijklmnopqrstuvwxyz'
    parts = []
    for idx, r in enumerate(rules):
        prefix = f"{letters[idx]}) "
        t = r['type']
        if t == 'update_by_material':
            a = r['material_trigger']
            upc = r['updates']['颜色']; ups = r['updates']['气味']
            parts.append(f"{prefix}将材质为{a}的样本颜色改为{upc}，气味改为{ups}")
        elif t == 'replace_by_ocean':
            ocf = r['ocean_from']; na = r['new_attrs']
            parts.append(f"{prefix}用等数量的尺寸为{na['尺寸']}、材质为{na['材质']}的新样本替换所有采集海域为{ocf}的样本（新样本颜色为{na['颜色']}，气味为{na['气味']}，标签为{na['标签']}，海域为{na['海域']}）")
        elif t == 'clone_by_size':
            sc = r['size_trigger']; e1, e2 = r['edits'][0], r['edits'][1]
            parts.append(f"{prefix}将所有尺寸为{sc}的样本各复制两个副本：一个副本{e1['field']}改为{e1['value']}，另一个副本{e2['field']}改为{e2['value']}")
        elif t == 'merge_by_label':
            ml = r['merge_label']; md = r['merged_attrs']
            parts.append(f"{prefix}将标签为{ml}的样本合并为一个组合样本（尺寸为{md['尺寸']}，材质为{md['材质']}，颜色为{md['颜色']}，气味为{md['气味']}，海域为{md['海域']}，标签为{md['标签']}）")
        elif t == 'recolor_by_ocean':
            oc = r['ocean']; col = r['color']
            parts.append(f"{prefix}将海域为{oc}的样本颜色统一改为{col}")
        elif t == 'swap_colors':
            ca, cb = r['color_a'], r['color_b']
            parts.append(f"{prefix}将颜色为{ca}与{cb}的样本颜色互换")
        elif t == 'relocate_label_by_material':
            m = r['material']; nl = r['new_label']
            parts.append(f"{prefix}将材质为{m}的样本标签改为{nl}")
        elif t == 'retag_by_ocean':
            oc = r['ocean']; nl = r['new_label']
            parts.append(f"{prefix}将海域为{oc}的样本标签统一改为{nl}")
        elif t == 'swap_labels':
            la, lb = r['label_a'], r['label_b']
            parts.append(f"{prefix}将标签为{la}与{lb}的样本标签互换")
    return '；'.join(parts)

def build_question_text(predicate):
    return build_question_text_v2(predicate)

def build_question_text_v2(predicate):
    mode = predicate.get('mode', 'or')
    readable = []
    for cl in predicate.get('clauses', []):
        readable.append(f"{cl['field']}为{cl['value']}")
    cond_text = '或'.join(readable) if readable else '无条件'
    if mode == 'or':
        return f"在最终集合中，有多少样本满足以下任一条件：{cond_text}？答案格式：输出一个整数，例如 7。"
    else:
        return f"在最终集合中，有多少样本同时满足以下全部条件：{cond_text}？答案格式：输出一个整数，例如 7。"

def build_question_text_ids_v2(predicate):
    mode = predicate.get('mode', 'or')
    readable = []
    for cl in predicate.get('clauses', []):
        readable.append(f"{cl['field']}为{cl['value']}")
    cond_text = '或'.join(readable) if readable else '无条件'
    if mode == 'or':
        return f"请列出最终集合中满足以下任一条件的样本ID（升序）：{cond_text}。答案格式：输出一个列表，例如 [1, 3, 5]。"
    else:
        return f"请列出最终集合中同时满足以下全部条件的样本ID（升序）：{cond_text}。答案格式：输出一个列表，例如 [2, 4]。"

def build_question_text_labelmax_v2():
    # 明确为“大写字母”以避免评测歧义
    return "请输出最终集合中出现次数最多的标签；如遇并列，选择按字母升序最靠前的标签。答案格式：输出一个大写字母，例如 A。"

def build_id_policy_text_v1():
    """
    以自然语言输出 ID 分配与处理规则，用于题面说明。
    """
    return "操作按题面列出的顺序依次执行；每一步均按ID升序处理当前集合；修改不改变样本ID；替换与合并会删除旧样本且其ID不保留；每次生成的新样本ID从当前最大ID+1起，按创建顺序递增分配；克隆按源样本ID升序逐个处理，并依次生成应用第一条编辑的副本与应用第二条编辑的副本。"

# --------------------------
# Predicate calibration — 基于最终集合分布，保证非平凡计数
# --------------------------
def calibrate_predicate_v2(transformed_samples, tf_spec):
    """
    基于最终集合的实际分布校准谓词：
      - 随机尝试生成 2-4 条子句，mode ∈ {'or','and'}
      - 只选取最终集合中真实存在的取值
      - 保证 1 <= count_satisfying <= total_count - 1
    若多次尝试未成功，回退到频次非平凡的单字段子句再扩展为两条子句，直至满足条件。
    """
    fields = ['材质', '颜色', '气味', '海域', '标签', '尺寸']
    total = len(transformed_samples)
    if total <= 1:
        # 极端退化场景（几乎不存在），返回宽松谓词
        return {'mode': 'or', 'clauses': []}

    # 构建每个字段的值域（基于最终集合）
    values_dict = {}
    for f in fields:
        values_dict[f] = sorted({it.get(f) for it in transformed_samples})

    # 快速尝试
    for _ in range(60):
        mode = random.choice(['or', 'and'])
        k = random.choice([2, 3, 4])
        usable_fields = [f for f in fields if values_dict.get(f)]
        if len(usable_fields) < k:
            k = max(1, len(usable_fields))
        chosen_fields = random.sample(usable_fields, k) if usable_fields else []
        clauses = [{'field': f, 'value': random.choice(values_dict[f])} for f in chosen_fields]
        pred = {'mode': mode, 'clauses': clauses}
        cnt = count_satisfying_v2(transformed_samples, pred)
        if 1 <= cnt <= (total - 1):
            return pred

    # 回退：选取某个字段的非平凡频次值
    for f in fields:
        # 统计频次
        freq = {}
        for it in transformed_samples:
            v = it.get(f)
            freq[v] = freq.get(v, 0) + 1
        candidates = [(v, c) for v, c in freq.items() if 1 <= c <= (total - 1)]
        if candidates:
            v, c = random.choice(candidates)
            # 先用一个子句，再补一个不同字段的子句以增加复杂度
            extra_fields = [ff for ff in fields if ff != f and values_dict.get(ff)]
            clauses = [{'field': f, 'value': v}]
            if extra_fields:
                ef = random.choice(extra_fields)
                ev = random.choice(values_dict[ef])
                clauses.append({'field': ef, 'value': ev})
            pred = {'mode': 'or', 'clauses': clauses}
            cnt = count_satisfying_v2(transformed_samples, pred)
            if 1 <= cnt <= (total - 1):
                return pred

    # 最后兜底：返回一个保证至少有元素的单子句（虽然可能 k=1，但满足非平凡）
    # 选择标签作为兜底，尽量可读
    freq = label_counts_v2(transformed_samples)
    for lab, c in freq.items():
        if 1 <= c <= (total - 1):
            return {'mode': 'or', 'clauses': [{'field': '标签', 'value': lab}]}

    # 实在不行，返回空（将导致 count=0，但几乎不达此分支）
    return {'mode': 'or', 'clauses': []}

# --------------------------
# Uniqueness and bundle verification
# --------------------------
def verify_uniqueness_bundle_v2(samples, predicate, final_count, ids_satisfying, label_counts, top_label):
    """
    验证：
      - ids_satisfying 的长度与 final_count 一致
      - ids_satisfying 为严格升序且无重复，且所有ID属于最终集合的ID域
      - 若 label_counts 非空，top_label 属于 keys 且符合最大计数与字母序最前的政策
      - 非平凡（final_count >= 1）
    该验证为高效线性检查。
    """
    if final_count < 1:
        return False
    if len(ids_satisfying) != final_count:
        return False
    # 严格升序与无重复
    if ids_satisfying != sorted(set(ids_satisfying)):
        return False
    # ID域校验：所有ID必须存在于最终集合
    ids_domain = {it['id'] for it in samples}
    for i in ids_satisfying:
        if i not in ids_domain:
            return False
    if not label_counts:
        return False
    max_count = max(label_counts.values())
    candidates = sorted([lab for lab, c in label_counts.items() if c == max_count])
    if not candidates:
        return False
    return top_label == candidates[0]