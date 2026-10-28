# object_properties_1.py
# 高阶泛化规则引擎（改进版：防显见线索、非平凡性、规则生效验证）
from typing import List, Dict, Sequence, Any, Optional, Tuple
import random
import time
import copy

# 兼容桩（外部可能导入）
def partition_segments(*args, **kwargs):
    return []

# 通用随机助手
def choose_one(seq: Sequence[Any]) -> Any:
    if not seq:
        raise ValueError("choose_one: empty sequence")
    return random.choice(list(seq))

def choose_one_excluding(seq: Sequence[Any], exclude: Any) -> Any:
    cands = [x for x in seq if x != exclude]
    return random.choice(cands) if cands else exclude

# 初始清单生成
def gen_initial_boxes(n: int,
                      volumes: List[str],
                      origins: List[str],
                      materials: List[str],
                      rads: List[str],
                      categories: List[str],
                      colors: List[str]) -> List[Dict[str, str]]:
    boxes: List[Dict[str, str]] = []
    for i in range(n):
        boxes.append({
            'id': i + 1,
            'volume': choose_one(volumes),
            'origin': choose_one(origins),
            'material': choose_one(materials),
            'rad': choose_one(rads),
            'cat': choose_one(categories),
            'color': choose_one(colors),
        })
    return boxes

# 规则配置生成（含守卫与序列）
def gen_rules_config(volumes: List[str],
                     origins: List[str],
                     materials: List[str],
                     rads: List[str],
                     categories: List[str],
                     colors: List[str]) -> Dict[str, Any]:
    rules: List[Dict[str, Any]] = []
    rule_types_pool = ['rewrite', 'replace', 'duplicate']
    main_num = random.randint(3, 5)

    def maybe_guard() -> Optional[Dict[str, Any]]:
        if random.random() < 0.45:
            g_mod = random.randint(3, 7)
            hit = random.randint(0, g_mod - 1)
            return {'g_mod': g_mod, 'hit': hit, 'use_fields': ['volume', 'material', 'color']}
        return None

    for _ in range(main_num):
        t = choose_one(rule_types_pool)
        if t == 'rewrite':
            field_pool = ['material', 'origin', 'color', 'rad', 'cat']
            match_field = choose_one(field_pool)
            match_val = {
                'material': choose_one(materials),
                'origin': choose_one(origins),
                'color': choose_one(colors),
                'rad': choose_one(rads),
                'cat': choose_one(categories)
            }[match_field]
            set_fields_pool = ['color', 'rad', 'material']
            kset = random.randint(1, min(3, len(set_fields_pool)))
            set_fields = random.sample(set_fields_pool, k=kset)
            setter = {}
            for sf in set_fields:
                setter[sf] = {
                    'color': choose_one(colors),
                    'rad': choose_one(rads),
                    'material': choose_one(materials)
                }[sf]
            r = {
                'type': 'rewrite',
                'match': {'attr': match_field, 'op': 'eq', 'value': match_val},
                'set': setter
            }
            g = maybe_guard()
            if g:
                r['guard'] = g
            rules.append(r)

        elif t == 'replace':
            match_field = choose_one(['origin', 'material'])
            match_val = choose_one(origins) if match_field == 'origin' else choose_one(materials)
            keep = random.random() < 0.2
            new_box = {
                'volume': choose_one(volumes),
                'origin': choose_one(origins),
                'material': choose_one(materials),
                'rad': choose_one(rads),
                'color': choose_one(colors),
                'copy_cat': True
            }
            r = {
                'type': 'replace',
                'match': {'attr': match_field, 'op': 'eq', 'value': match_val},
                'new': new_box,
                'keep_original': keep
            }
            g = maybe_guard()
            if g:
                r['guard'] = g
            rules.append(r)

        elif t == 'duplicate':
            copies = []
            copy_num = random.randint(1, 3)
            transform_choices = ['decrease_volume', 'set_color', 'set_rad', 'set_material']
            for _k in range(copy_num):
                seq_ops = []
                seq_len = random.randint(1, 3)
                for _s in range(seq_len):
                    op = choose_one(transform_choices)
                    if op == 'decrease_volume':
                        seq_ops.append({'op': 'decrease_volume'})
                    elif op == 'set_color':
                        seq_ops.append({'op': 'set', 'field': 'color', 'value': choose_one(colors)})
                    elif op == 'set_rad':
                        seq_ops.append({'op': 'set', 'field': 'rad', 'value': choose_one(rads)})
                    elif op == 'set_material':
                        seq_ops.append({'op': 'set', 'field': 'material', 'value': choose_one(materials)})
                copies.append({'seq': seq_ops})
            match_tpl = choose_one(['cat_rad', 'mat_color', 'single'])
            if match_tpl == 'cat_rad':
                m = {'and': [{'attr': 'cat', 'op': 'eq', 'value': choose_one(categories)},
                             {'attr': 'rad', 'op': 'eq', 'value': choose_one(rads)}]}
            elif match_tpl == 'mat_color':
                m = {'and': [{'attr': 'material', 'op': 'eq', 'value': choose_one(materials)},
                             {'attr': 'color', 'op': 'eq', 'value': choose_one(colors)}]}
            else:
                attr = choose_one(['material', 'origin', 'color', 'rad', 'cat'])
                val = {'material': choose_one(materials),
                       'origin': choose_one(origins),
                       'color': choose_one(colors),
                       'rad': choose_one(rads),
                       'cat': choose_one(categories)}[attr]
                m = {'attr': attr, 'op': 'eq', 'value': val}
            r = {
                'type': 'duplicate',
                'match': m,
                'copies': copies,
                'keep_original': True
            }
            g = maybe_guard()
            if g:
                r['guard'] = g
            rules.append(r)

    # 去重
    keys_all = ['volume', 'origin', 'material', 'rad', 'cat', 'color']
    dedup_keys = random.sample(keys_all, k=random.randint(5, 6))
    rules.append({'type': 'dedup', 'keys': dedup_keys})

    # 联动
    if random.random() < 0.85:
        cond_color = choose_one(colors)
        threshold_t = random.randint(2, 5)
        target_material = choose_one(materials)
        change_rad = choose_one(rads)
        r = {
            'type': 'cascade',
            'if': {'field': 'color', 'value': cond_color, 'cmp': '>=', 'threshold': threshold_t},
            'then': {'match': {'attr': 'material', 'op': 'eq', 'value': target_material},
                     'set': {'rad': change_rad}}
        }
        g = maybe_guard()
        if g:
            r['guard'] = g
        rules.append(r)

    return {'rules': rules, 'lists': {'volumes': volumes, 'materials': materials, 'colors': colors}}

# 查询配置生成（带防冗余）
def gen_query_config(volumes: List[str],
                     origins: List[str],
                     materials: List[str],
                     rads: List[str],
                     categories: List[str],
                     colors: List[str]) -> Dict[str, Any]:
    conds: List[Dict[str, Any]] = []
    m = random.randint(1, 3)
    attempts = 0
    while len(conds) < m and attempts < 20:
        attempts += 1
        tpl = choose_one(['EQ', 'NEQ', 'RAD_NOT_ORIGIN', 'MAT_AND_CAT'])
        if tpl == 'EQ':
            field = choose_one(['material', 'origin', 'color', 'rad', 'cat', 'volume'])
            value = choose_one({'material': materials, 'origin': origins, 'color': colors,
                                'rad': rads, 'cat': categories, 'volume': volumes}[field])
            conds.append({'type': 'EQ', 'field': field, 'value': value})
        elif tpl == 'NEQ':
            field = choose_one(['material', 'origin', 'color', 'rad', 'cat', 'volume'])
            # 防冗余：禁止在相同字段上重复NEQ（OR模式下会趋于恒真）
            if any(c.get('type') == 'NEQ' and c.get('field') == field for c in conds):
                continue
            value = choose_one({'material': materials, 'origin': origins, 'color': colors,
                                'rad': rads, 'cat': categories, 'volume': volumes}[field])
            conds.append({'type': 'NEQ', 'field': field, 'value': value})
        elif tpl == 'RAD_NOT_ORIGIN':
            conds.append({'type': 'AND',
                          'conds': [{'type': 'EQ', 'field': 'rad', 'value': choose_one(rads)},
                                    {'type': 'NEQ', 'field': 'origin', 'value': choose_one(origins)}]})
        elif tpl == 'MAT_AND_CAT':
            conds.append({'type': 'AND',
                          'conds': [{'type': 'EQ', 'field': 'material', 'value': choose_one(materials)},
                                    {'type': 'EQ', 'field': 'cat', 'value': choose_one(categories)}]})

    # 若全部是NEQ，则强制替换一个为EQ，保证非平凡性潜力
    if conds and all(c['type'] == 'NEQ' for c in conds):
        # 替换第一个为等式条件
        c0 = conds[0]
        fld = c0['field']
        pool = {'material': materials, 'origin': origins, 'color': colors,
                'rad': rads, 'cat': categories, 'volume': volumes}[fld]
        conds[0] = {'type': 'EQ', 'field': fld, 'value': choose_one(pool)}

    return {'mode': 'ANY', 'conds': conds}

# 文本渲染
def _field_cn(field: str) -> str:
    mapping = {'volume': '体积', 'origin': '原产', 'material': '材质', 'rad': '辐射', 'cat': '类别', 'color': '颜色'}
    return mapping.get(field, field)

def _simple_match_str(m: Dict[str, Any]) -> str:
    if 'attr' in m:
        op = '为' if m.get('op') == 'eq' else '不为'
        return f"{_field_cn(m['attr'])}{op}{m['value']}"
    if 'and' in m:
        return '(' + ' 且 '.join([_simple_match_str(sub) for sub in m['and']]) + ')'
    return '匹配条件'

def _set_str(setter: Dict[str, Any]) -> str:
    return '、'.join([f"{_field_cn(k)}改为{v}" for k, v in setter.items()])

def _guard_str(g: Dict[str, Any]) -> str:
    return f"仅对校验值等于{g['hit']}的货箱生效。校验值定义为(体积索引 + 材质索引 + 颜色索引)对{g['g_mod']}取模的结果；索引从0开始按枚举池顺序计数。"

def render_rules_text(rules_config: Dict[str, Any]) -> str:
    lines: List[str] = []
    rules = rules_config.get('rules', [])
    for i, r in enumerate(rules, start=1):
        if r['type'] == 'rewrite':
            m = r['match']; setter = r['set']
            line = f"{i}) 若{_simple_match_str(m)}，则{_set_str(setter)}。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
        elif r['type'] == 'replace':
            m = r['match']; nb = r['new']
            keep = r.get('keep_original', False)
            parts = [f"体积={nb['volume']}", f"原产={nb['origin']}", f"材质={nb['material']}",
                     f"辐射={nb['rad']}", "类别=沿用原货箱类别", f"颜色={nb['color']}"]
            line = f"{i}) 若{_simple_match_str(m)}，用同数量新货箱替换（" + '、'.join(parts) + f"），原件{'保留' if keep else '不保留'}。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
        elif r['type'] == 'duplicate':
            m = r['match']; copies = r['copies']
            descs = []
            for cp in copies:
                seq = cp.get('seq', [])
                step_strs = []
                for st in seq:
                    if st['op'] == 'decrease_volume':
                        step_strs.append('体积降低一档(下限为超小)')
                    elif st['op'] == 'set':
                        step_strs.append(f"{_field_cn(st['field'])}改为{st['value']}")
                descs.append(' → '.join(step_strs) if step_strs else '无变化')
            line = f"{i}) 若{_simple_match_str(m)}，为每件货箱复制{len(copies)}个副本（" + '；'.join(descs) + "），原件保留。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
        elif r['type'] == 'dedup':
            keys = r['keys']
            cn_keys = ','.join([_field_cn(k) for k in keys])
            lines.append(f"{i}) 去重：若在[{cn_keys}]上完全相同，则只保留一件。")
        elif r['type'] == 'cascade':
            cond = r['if']; th = cond['threshold']
            line = f"{i}) 条件联动：若{_field_cn(cond['field'])}为{cond['value']}的货箱数量≥{th}，则将{_simple_match_str(r['then']['match'])}的货箱，{_set_str(r['then']['set'])}。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
    return '\n'.join(lines)

def _cond_to_str(c: Dict[str, Any]) -> str:
    t = c.get('type')
    if t == 'EQ':
        return f"{_field_cn(c['field'])}为{c['value']}"
    if t == 'NEQ':
        return f"{_field_cn(c['field'])}不为{c['value']}"
    if t == 'AND':
        return '(' + ' 且 '.join([_cond_to_str(sub) for sub in c['conds']]) + ')'
    return '未知条件'

def render_query_text(query_config: Dict[str, Any]) -> str:
    mode = query_config.get('mode', 'ANY')
    conds = query_config.get('conds', [])
    if not conds:
        return '在最终清单中，满足条件的货箱有多少个？'
    joiner = ' 或 ' if mode == 'ANY' else ' 且 '
    inner = joiner.join([_cond_to_str(c) for c in conds])
    return f"在最终清单中，满足以下任一条件的货箱有多少个？ {inner}"

# 规则引擎（支持元数据跟踪）
def function_1(initial_boxes: List[Dict[str, str]],
               volumes_order: List[str],
               rules_config: Dict[str, Any],
               track_meta: bool = False) -> Any:
    working: List[Dict[str, str]] = [{'volume': b['volume'], 'origin': b['origin'], 'material': b['material'],
                                      'rad': b['rad'], 'cat': b['cat'], 'color': b['color']} for b in initial_boxes]

    lists = rules_config.get('lists', {})
    mat_list = lists.get('materials', [])
    col_list = lists.get('colors', [])
    meta_touched: List[bool] = []

    def match_box(box: Dict[str, str], m: Dict[str, Any]) -> bool:
        if 'and' in m:
            return all(match_box(box, sub) for sub in m['and'])
        if 'attr' in m:
            op = m.get('op')
            if op == 'eq':
                return box[m['attr']] == m['value']
            elif op == 'neq':
                return box[m['attr']] != m['value']
        return False

    def guard_hit(box: Dict[str, str], guard: Dict[str, Any]) -> bool:
        g_mod = guard['g_mod']; hit = guard['hit']
        v_idx = volumes_order.index(box['volume']) if box['volume'] in volumes_order else 0
        m_idx = mat_list.index(box['material']) if box['material'] in mat_list else 0
        c_idx = col_list.index(box['color']) if box['color'] in col_list else 0
        val = (v_idx + m_idx + c_idx) % g_mod
        return val == hit

    def decrease_volume(v: str) -> str:
        if v not in volumes_order:
            return v
        idx = volumes_order.index(v)
        return volumes_order[max(0, idx - 1)]

    for r in rules_config.get('rules', []):
        rtype = r['type']
        guard = r.get('guard', None)
        touched = False

        if rtype == 'rewrite':
            m = r['match']; setter = r['set']
            for box in working:
                if match_box(box, m) and (guard is None or guard_hit(box, guard)):
                    before = tuple(box[k] for k in setter.keys())
                    for k, v in setter.items():
                        box[k] = v
                    after = tuple(box[k] for k in setter.keys())
                    if before != after:
                        touched = True

        elif rtype == 'replace':
            m = r['match']; nb = r['new']; keep = r.get('keep_original', False)
            new_list: List[Dict[str, str]] = []
            for box in working:
                if match_box(box, m) and (guard is None or guard_hit(box, guard)):
                    if keep:
                        new_list.append(dict(box))
                    new_box = {
                        'volume': nb['volume'],
                        'origin': nb['origin'],
                        'material': nb['material'],
                        'rad': nb['rad'],
                        'cat': box['cat'] if nb.get('copy_cat') else box['cat'],
                        'color': nb['color'],
                    }
                    new_list.append(new_box)
                    touched = True
                else:
                    new_list.append(box)
            working = new_list

        elif rtype == 'duplicate':
            m = r['match']; copies = r['copies']; keep = r.get('keep_original', True)
            new_working: List[Dict[str, str]] = []
            for box in working:
                if match_box(box, m) and (guard is None or guard_hit(box, guard)):
                    if keep:
                        new_working.append(dict(box))
                    for cp in copies:
                        nb = dict(box)
                        for st in cp.get('seq', []):
                            if st['op'] == 'decrease_volume':
                                nb['volume'] = decrease_volume(nb['volume'])
                            elif st['op'] == 'set':
                                nb[st['field']] = st['value']
                        new_working.append(nb)
                    touched = True
                else:
                    new_working.append(box)
            working = new_working

        elif rtype == 'dedup':
            keys = r['keys']
            seen = set()
            uniq: List[Dict[str, str]] = []
            for box in working:
                key = tuple(box[k] for k in keys)
                if key not in seen:
                    seen.add(key)
                    uniq.append(box)
            if len(uniq) != len(working):
                touched = True
            working = uniq

        elif rtype == 'cascade':
            cond = r['if']; th = cond['threshold']
            count = sum(1 for b in working if b.get(cond['field']) == cond['value'])
            if count >= th:
                m = r['then']['match']; setter = r['then']['set']
                for box in working:
                    if match_box(box, m) and (guard is None or guard_hit(box, guard)):
                        before = tuple(box.get(k) for k in setter.keys())
                        for k, v in setter.items():
                            box[k] = v
                        after = tuple(box.get(k) for k in setter.keys())
                        if before != after:
                            touched = True

        meta_touched.append(touched)

    if track_meta:
        return working, meta_touched
    return working

# 查询计数
def function_2(final_boxes: List[Dict[str, str]], query_config: Dict[str, Any]) -> int:
    mode = query_config.get('mode', 'ANY')
    conds = query_config.get('conds', [])

    def eval_cond(box: Dict[str, str], c: Dict[str, Any]) -> bool:
        t = c.get('type')
        if t == 'EQ':
            return box.get(c['field']) == c['value']
        if t == 'NEQ':
            return box.get(c['field']) != c['value']
        if t == 'AND':
            return all(eval_cond(box, sub) for sub in c.get('conds', []))
        return False

    count = 0
    for b in final_boxes:
        vals = [eval_cond(b, c) for c in conds]
        ok = any(vals) if mode == 'ANY' else all(vals)
        if ok:
            count += 1
    return count

# 文本渲染（与前版一致）
def render_rules_text(rules_config: Dict[str, Any]) -> str:
    # 重用上方定义
    return _render_rules_text_impl(rules_config)

def render_query_text(query_config: Dict[str, Any]) -> str:
    # 重用上方定义
    return _render_query_text_impl(query_config)

def _render_rules_text_impl(rules_config: Dict[str, Any]) -> str:
    # 复制逻辑，避免循环引用
    lines: List[str] = []
    rules = rules_config.get('rules', [])
    for i, r in enumerate(rules, start=1):
        if r['type'] == 'rewrite':
            m = r['match']; setter = r['set']
            line = f"{i}) 若{_simple_match_str(m)}，则{_set_str(setter)}。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
        elif r['type'] == 'replace':
            m = r['match']; nb = r['new']
            keep = r.get('keep_original', False)
            parts = [f"体积={nb['volume']}", f"原产={nb['origin']}", f"材质={nb['material']}",
                     f"辐射={nb['rad']}", "类别=沿用原货箱类别", f"颜色={nb['color']}"]
            line = f"{i}) 若{_simple_match_str(m)}，用同数量新货箱替换（" + '、'.join(parts) + f"），原件{'保留' if keep else '不保留'}。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
        elif r['type'] == 'duplicate':
            m = r['match']; copies = r['copies']
            descs = []
            for cp in copies:
                seq = cp.get('seq', [])
                step_strs = []
                for st in seq:
                    if st['op'] == 'decrease_volume':
                        step_strs.append('体积降低一档(下限为超小)')
                    elif st['op'] == 'set':
                        step_strs.append(f"{_field_cn(st['field'])}改为{st['value']}")
                descs.append(' → '.join(step_strs) if step_strs else '无变化')
            line = f"{i}) 若{_simple_match_str(m)}，为每件货箱复制{len(copies)}个副本（" + '；'.join(descs) + "），原件保留。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
        elif r['type'] == 'dedup':
            keys = r['keys']
            cn_keys = ','.join([_field_cn(k) for k in keys])
            lines.append(f"{i}) 去重：若在[{cn_keys}]上完全相同，则只保留一件。")
        elif r['type'] == 'cascade':
            cond = r['if']; th = cond['threshold']
            line = f"{i}) 条件联动：若{_field_cn(cond['field'])}为{cond['value']}的货箱数量≥{th}，则将{_simple_match_str(r['then']['match'])}的货箱，{_set_str(r['then']['set'])}。"
            if 'guard' in r:
                line += " " + _guard_str(r['guard'])
            lines.append(line)
    return '\n'.join(lines)

def _render_query_text_impl(query_config: Dict[str, Any]) -> str:
    mode = query_config.get('mode', 'ANY')
    conds = query_config.get('conds', [])
    if not conds:
        return '在最终清单中，满足条件的货箱有多少个？'
    joiner = ' 或 ' if mode == 'ANY' else ' 且 '
    inner = joiner.join([_cond_to_str(c) for c in conds])
    return f"在最终清单中，满足以下任一条件的货箱有多少个？ {inner}"

# 唯一性与质量验证：双通道一致性 + 非平凡性 + 规则实际生效 + 限时
def verify_unique_answer(initial_boxes: List[Dict[str, str]],
                         volumes_order: List[str],
                         rules_config: Dict[str, Any],
                         query_config: Dict[str, Any],
                         time_limit_sec: float = 10.0) -> bool:
    start = time.time()

    # 路径A：跟踪元数据
    final_a, meta_a = function_1(initial_boxes, volumes_order, rules_config, track_meta=True)
    ans_a = function_2(final_a, query_config)
    impact_a = any(meta_a)

    # 路径B：深拷贝独立执行
    rules_b = copy.deepcopy(rules_config)
    query_b = copy.deepcopy(query_config)
    final_b, meta_b = function_1(initial_boxes, volumes_order, rules_b, track_meta=True)
    ans_b = function_2(final_b, query_b)

    # 一致性
    if ans_a != ans_b:
        return False
    if _render_rules_text_impl(rules_config) != _render_rules_text_impl(rules_b):
        return False
    if _render_query_text_impl(query_config) != _render_query_text_impl(query_b):
        return False

    # 非平凡性：答案介于(0, 总数)之间，且至少一条规则有实际影响
    L = len(final_a)
    if not (0 < ans_a < L):
        return False
    if not (impact_a or any(meta_b)):
        return False

    # 限时
    return (time.time() - start) <= time_limit_sec