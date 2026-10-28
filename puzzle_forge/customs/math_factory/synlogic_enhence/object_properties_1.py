# object_properties_4.py
# ------------------------------------------------------------
# 超随机高阶版辅助代码：
# - gen_modules: 随机生成初始模块列表
# - gen_type_order: 随机生成类型排列
# - gen_ruleset: 随机生成完整规则集（含分组规则与固件窗口）
# - build_rules_desc: 规则集转为可读文本
# - function_2: 执行规则集（严格顺序）并返回最终在架模块列表
# - function_1: 计算查询计数
# - verify_unique_answer: 唯一解验证（双通道重放+不变性检查+稳定性检测，含超时）
# ------------------------------------------------------------

from typing import List, Dict, Tuple, Any
import random, time, math
import copy

# ---------------------------
# 基础工具
# ---------------------------
def _round_fw(val: float, digits: int = 1) -> float:
    """固件版本四舍五入到指定位数（默认一位）。"""
    return round(float(val), digits)

def gen_modules(n: int, types: List[str], size_order: List[str],
                origins: List[str], materials: List[str],
                powers: List[str], colors: List[str]) -> List[Dict]:
    """
    生成初始模块列表：
    - 各字段从提供的池中均匀随机抽取
    - 固件版本在 [1.0, 2.6] 区间随机，一位小数
    - 每个模块携带生成序号 gen（从 1 递增）
    """
    mods: List[Dict] = []
    for i in range(n):
        m = {
            'type': random.choice(types),
            'size': random.choice(size_order),
            'origin': random.choice(origins),
            'material': random.choice(materials),
            'power': random.choice(powers),
            'color': random.choice(colors),
            'fw': _round_fw(random.uniform(1.0, 2.6), 1),
            'gen': i + 1
        }
        mods.append(m)
    return mods

def gen_type_order(types: List[str]) -> List[str]:
    """返回类型的随机排列，用于容量控制第3阶段的类型优先级（从后往前移除）。"""
    t = list(types)
    random.shuffle(t)
    return t

def _size_rank(size_order: List[str]) -> Dict[str, int]:
    return {s: i for i, s in enumerate(size_order)}

def _power_rank(powers: List[str]) -> Dict[str, int]:
    return {p: i for i, p in enumerate(powers)}

def _next_size(size: str, size_order: List[str], step: int = 1, direction: str = 'up') -> str:
    rank = _size_rank(size_order)
    idx = rank.get(size, 0)
    if direction == 'up':
        idx = min(idx + step, len(size_order) - 1)
    else:
        idx = max(idx - step, 0)
    return size_order[idx]

def _adj_power(power: str, powers: List[str], step: int = 1, direction: str = 'down') -> str:
    rank = _power_rank(powers)
    idx = rank.get(power, 0)
    if direction == 'up':
        idx = min(idx + step, len(powers) - 1)
    else:
        idx = max(idx - step, 0)
    return powers[idx]

def _clone_module(m: Dict, gen_order: int) -> Dict:
    c = dict(m)
    c['gen'] = gen_order
    return c

# ---------------------------
# 规则集生成
# ---------------------------
def gen_ruleset(types: List[str], size_order: List[str],
                origins: List[str], materials: List[str],
                powers: List[str], colors: List[str],
                module_num: int) -> Dict[str, Any]:
    """
    随机生成完整规则集（高阶版）：
    - 固件增量规则：1~3条
    - 替换规则：1~2条
    - 复制规则：0~3条（副本操作2~3个，来自 op 库）
    - 统一外观规则：0~2条
    - 分组规则：0~2条（两种模板，详见下方）
    - 固件窗口：50% 概率启用（fw[min,max], round_digits=1）
    - 容量控制：cap = module_num + delta(12~20)， phases 从3种策略中随机选2~3并随机排序
    - 去重字段：从7个候选字段随机选5~7个
    - 查询条件：类型/颜色/材质各1~3个，排除功耗随机
    """
    # 固件增量
    inc_num = random.randint(1, 3)
    inc_types = random.sample(types, k=min(inc_num, len(types)))
    inc_rules = [{'type': t, 'delta': round(random.uniform(0.1, 0.4), 1)} for t in inc_types]

    # 替换规则
    rep_num = random.randint(1, 2)
    rep_origins = random.sample(origins, k=min(rep_num, len(origins)))
    replace_rules = []
    for ro in rep_origins:
        new_origin = random.choice([o for o in origins if o != ro]) if len(origins) > 1 else ro
        new_material = random.choice(materials)
        new_size = random.choice(size_order)
        new_power = random.choice(powers)
        new_color = random.choice(colors)
        new_fw = round(random.uniform(1.0, 2.5), 1)
        replace_rules.append({
            'match': {'attr': 'origin', 'op': 'eq', 'value': ro},
            'keep_type': True,
            'new_fields': {
                'origin': new_origin, 'material': new_material, 'size': new_size,
                'power': new_power, 'color': new_color, 'fw': new_fw
            }
        })

    # 复制规则
    copy_num = random.randint(0, 3)
    copy_rules = []
    op_library = [
        {'change': 'power', 'direction': 'down', 'step': 1},
        {'change': 'power', 'direction': 'up', 'step': 1},
        {'change': 'size', 'direction': 'up', 'step': 1},
        {'change': 'size', 'direction': 'down', 'step': 1},
        {'change': 'color', 'to': None},  # None 表示随机色
    ]
    for _ in range(copy_num):
        trig_power = random.choice(powers)
        trig_material = random.choice(materials)
        ops = random.sample(op_library, k=random.randint(2, min(3, len(op_library))))
        copy_rules.append({
            'match': {'power': trig_power, 'material': trig_material},
            'copies': ops,
            'keep_original': True
        })

    # 统一外观规则
    unify_num = random.randint(0, 2)
    unify_rules = []
    for _ in range(unify_num):
        utype = random.choice(types)
        trigger_color = random.choice(colors)
        target_candidates = [c for c in colors if c != trigger_color] or [trigger_color]
        target_color = random.choice(target_candidates)
        unify_rules.append({
            'type': utype,
            'trigger': {'attr': 'color', 'value': trigger_color},
            'apply': {'attr': 'color', 'value': target_color}
        })

    # 分组规则（两种模板）
    group_rules = []
    grp_num = random.randint(0, 2)
    for _ in range(grp_num):
        template = random.choice(['color_unify_if_trigger', 'power_normalize_if_fwavg_high'])
        group_by = random.choice(['type', 'origin', 'material'])
        if template == 'color_unify_if_trigger':
            trig_color = random.choice(colors)
            target_candidates = [c for c in colors if c != trig_color] or [trig_color]
            target_color = random.choice(target_candidates)
            group_rules.append({
                'group_by': group_by,
                'template': template,
                'trigger_color': trig_color,
                'target_color': target_color
            })
        else:
            # 组内平均fw > 阈值，则统一降一级功耗
            fw_threshold = round(random.uniform(1.4, 2.2), 1)
            group_rules.append({
                'group_by': group_by,
                'template': template,
                'fw_threshold': fw_threshold
            })

    # 固件窗口（50% 概率开启）
    fw_window = None
    if random.random() < 0.5:
        lo = round(random.uniform(1.0, 1.5), 1)
        hi = round(random.uniform(2.0, 2.6), 1)
        if hi < lo: lo, hi = hi, lo
        fw_window = {'min': lo, 'max': hi, 'round_digits': 1}

    # 容量控制
    cap_delta = random.randint(12, 20)
    cap_limit = module_num + cap_delta
    methods = ['remove_by_power', 'remove_by_size', 'remove_by_type_order']
    phases = random.sample(methods, k=random.randint(2, len(methods)))
    remove_first_power = random.choice(powers)
    type_order = gen_type_order(types)
    capacity_rule = {
        'cap': cap_limit,
        'phases': phases,
        'params': {
            'remove_first_power': remove_first_power,
            'type_order': type_order
        }
    }

    # 去重字段
    dedup_candidates = ['type', 'size', 'origin', 'material', 'power', 'color', 'fw']
    dedup_fields = random.sample(dedup_candidates, k=random.randint(5, len(dedup_candidates)))

    # 查询条件
    include_types = random.sample(types, k=random.randint(1, min(3, len(types))))
    condition_colors = random.sample(colors, k=random.randint(1, min(3, len(colors))))
    condition_materials = random.sample(materials, k=random.randint(1, min(3, len(materials))))
    exclude_power = random.choice(powers)

    return {
        'size_order': size_order,
        'powers': powers,
        'inc_rules': inc_rules,
        'replace_rules': replace_rules,
        'copy_rules': copy_rules,
        'unify_rules': unify_rules,
        'group_rules': group_rules,
        'fw_window': fw_window,
        'capacity_rule': capacity_rule,
        'dedup_fields': dedup_fields,
        'query': {
            'include_types': include_types,
            'condition_colors': condition_colors,
            'condition_materials': condition_materials,
            'exclude_power': exclude_power
        }
    }

# ---------------------------
# 规则描述生成
# ---------------------------
def build_rules_desc(ruleset: Dict[str, Any]) -> str:
    parts: List[str] = []
    inc = ruleset.get('inc_rules', [])
    if inc:
        inc_text = ', '.join([f"固件:类型={r['type']} +{r['delta']}" for r in inc])
        parts.append(f"[增量] {inc_text}（加后统一一位小数）")

    rep = ruleset.get('replace_rules', [])
    if rep:
        rep_texts = []
        for r in rep:
            nf = r['new_fields']
            rep_texts.append(f"{r['match']['attr']}={r['match']['value']} -> 新模块(origin={nf['origin']}, material={nf['material']}, size={nf['size']}, power={nf['power']}, color={nf['color']}, fw={nf['fw']}; 类型不变)")
        parts.append("[替换] " + "； ".join(rep_texts))

    cp = ruleset.get('copy_rules', [])
    if cp:
        cp_texts = []
        for r in cp:
            ops = []
            for o in r['copies']:
                if o['change'] == 'color':
                    ops.append("颜色改为随机")
                elif o['change'] == 'power':
                    ops.append(f"功耗{('升' if o['direction']=='up' else '降')}一级")
                elif o['change'] == 'size':
                    ops.append(f"尺寸{('升' if o['direction']=='up' else '降')}一级")
            cp_texts.append(f"触发[power={r['match']['power']}, material={r['match']['material']}] -> 生成副本[{', '.join(ops)}]（原件保留）")
        parts.append("[复制] " + "； ".join(cp_texts))

    uf = ruleset.get('unify_rules', [])
    if uf:
        uf_texts = []
        for r in uf:
            uf_texts.append(f"若存在类型={r['type']} 且颜色={r['trigger']['value']}，则该类型{r['apply']['attr']}统一为 {r['apply']['value']}")
        parts.append("[统一] " + "； ".join(uf_texts))

    gr = ruleset.get('group_rules', [])
    if gr:
        gr_texts = []
        for r in gr:
            if r['template'] == 'color_unify_if_trigger':
                gr_texts.append(f"按{r['group_by']}分组：若组内出现颜色={r['trigger_color']}，则组内颜色统一为 {r['target_color']}")
            else:
                gr_texts.append(f"按{r['group_by']}分组：若组内平均固件超过 {r['fw_threshold']}，则组内功耗统一降一级")
        parts.append("[分组] " + "； ".join(gr_texts))

    fw_win = ruleset.get('fw_window')
    if fw_win:
        parts.append(f"[固件窗口] 限制所有固件到区间[{fw_win['min']}, {fw_win['max']}]并四舍五入到{fw_win['round_digits']}位小数")

    cap = ruleset.get('capacity_rule', {})
    if cap:
        phase_map = {
            'remove_by_power': f"按功耗先移除(目标功耗={cap.get('params',{}).get('remove_first_power','?')}, 最近生成优先)",
            'remove_by_size': "按尺寸从大到小移除(同尺寸最近生成优先)",
            'remove_by_type_order': "按类型顺序从后往前移除(同优先级最近生成优先)"
        }
        phases = cap.get('phases', [])
        phase_text = " -> ".join([phase_map.get(p, p) for p in phases])
        parts.append(f"[容量] 上限={cap.get('cap')}，阶段=[{phase_text}]")

    dedup = ruleset.get('dedup_fields', [])
    if dedup:
        parts.append(f"[去重] 字段=[{', '.join(dedup)}]（完全相同仅保留最早生成）")

    q = ruleset.get('query', {})
    if q:
        parts.append(f"[查询] 类型∈[{', '.join(q['include_types'])}]；颜色∈[{', '.join(q['condition_colors'])}] 或 材质∈[{', '.join(q['condition_materials'])}]；排除功耗={q['exclude_power']}")
    return "; ".join(parts)

# ---------------------------
# 规则执行引擎：各阶段
# ---------------------------
def _apply_inc_rules(mods: List[Dict], inc_rules: List[Dict]) -> None:
    for r in inc_rules:
        t = r['type']
        delta = float(r['delta'])
        for m in mods:
            if m['type'] == t:
                m['fw'] = _round_fw(m['fw'] + delta, 1)

def _apply_replace_rules(mods: List[Dict], start_gen: int, replace_rules: List[Dict]) -> Tuple[List[Dict], int]:
    gen = start_gen
    new_mods: List[Dict] = []
    for m in mods:
        replaced = False
        for r in replace_rules:
            match = r['match']
            attr = match['attr']
            op = match['op']
            val = match['value']
            if (op == 'eq' and m.get(attr) == val) or (op == 'in' and m.get(attr) in val):
                gen += 1
                nf = r['new_fields']
                nm = {
                    'type': m['type'] if r.get('keep_type', True) else nf.get('type', m['type']),
                    'size': nf['size'],
                    'origin': nf['origin'],
                    'material': nf['material'],
                    'power': nf['power'],
                    'color': nf['color'],
                    'fw': _round_fw(nf['fw'], 1),
                    'gen': gen
                }
                new_mods.append(nm)
                replaced = True
                break
        if not replaced:
            new_mods.append(m)
    return new_mods, gen

def _apply_copy_rules(mods: List[Dict], start_gen: int, copy_rules: List[Dict],
                      size_order: List[str], powers: List[str], colors: List[str]) -> Tuple[List[Dict], int]:
    gen = start_gen
    new_mods = list(mods)
    for m in mods:
        for r in copy_rules:
            cond = r['match']
            if m.get('power') == cond.get('power') and m.get('material') == cond.get('material'):
                for op in r.get('copies', []):
                    gen += 1
                    cp = _clone_module(m, gen)
                    if op['change'] == 'power':
                        cp['power'] = _adj_power(m['power'], powers, step=op.get('step',1), direction=op.get('direction','down'))
                    elif op['change'] == 'size':
                        cp['size'] = _next_size(m['size'], size_order, step=op.get('step',1), direction=op.get('direction','up'))
                    elif op['change'] == 'color':
                        target = op.get('to')
                        if target is None:
                            candidates = [c for c in colors if c != m['color']] or [m['color']]
                            target = random.choice(candidates)
                        cp['color'] = target
                    new_mods.append(cp)
    return new_mods, gen

def _apply_unify_rules(mods: List[Dict], unify_rules: List[Dict]) -> None:
    for r in unify_rules:
        utype = r['type']
        trig = r['trigger']
        apply = r['apply']
        has_trigger = any(m['type'] == utype and m.get(trig['attr']) == trig['value'] for m in mods)
        if has_trigger:
            for m in mods:
                if m['type'] == utype:
                    m[apply['attr']] = apply['value']

def _apply_group_rules(mods: List[Dict], group_rules: List[Dict], powers: List[str]) -> None:
    """分组规则：两种模板"""
    rank = _power_rank(powers)
    for gr in group_rules:
        gfield = gr['group_by']
        groups: Dict[Any, List[Dict]] = {}
        for m in mods:
            key = m[gfield]
            groups.setdefault(key, []).append(m)
        if gr['template'] == 'color_unify_if_trigger':
            trig_color = gr['trigger_color']
            target_color = gr['target_color']
            for key, lst in groups.items():
                if any(mm['color'] == trig_color for mm in lst):
                    for mm in lst:
                        mm['color'] = target_color
        else:
            # 固件均值 > 阈值 -> 功耗统一降一级
            thr = gr['fw_threshold']
            for key, lst in groups.items():
                if not lst:
                    continue
                avg_fw = sum(mm['fw'] for mm in lst) / len(lst)
                if avg_fw > thr:
                    for mm in lst:
                        mm['power'] = _adj_power(mm['power'], powers, step=1, direction='down')

def _apply_fw_window(mods: List[Dict], fw_window: Dict[str, Any]) -> None:
    if not fw_window:
        return
    lo, hi = fw_window['min'], fw_window['max']
    digits = fw_window.get('round_digits', 1)
    for m in mods:
        val = m['fw']
        if val < lo: val = lo
        if val > hi: val = hi
        m['fw'] = _round_fw(val, digits)

def _remove_by_capacity(mods: List[Dict], cap: int,
                        phases: List[str], params: Dict[str, Any],
                        size_order: List[str], type_order: List[str]) -> List[Dict]:
    keep = list(mods)
    size_rank = _size_rank(size_order)
    type_pos = {t: i for i, t in enumerate(type_order)}  # 越大越靠后

    def sort_by_gen_desc(items: List[Dict]) -> List[Dict]:
        return sorted(items, key=lambda x: x.get('gen', 0), reverse=True)

    for phase in phases:
        if len(keep) <= cap:
            break
        if phase == 'remove_by_power':
            target_power = params.get('remove_first_power')
            candidates = [m for m in keep if m['power'] == target_power]
            for m in sort_by_gen_desc(candidates):
                if len(keep) <= cap:
                    break
                keep.remove(m)
        elif phase == 'remove_by_size':
            keep_sorted = sorted(keep, key=lambda x: (size_rank.get(x['size'], 0), x.get('gen', 0)), reverse=True)
            idx = 0
            while len(keep) > cap and idx < len(keep_sorted):
                m = keep_sorted[idx]
                if m in keep:
                    keep.remove(m)
                idx += 1
        elif phase == 'remove_by_type_order':
            keep_sorted = sorted(keep, key=lambda x: (type_pos.get(x['type'], -1), x.get('gen', 0)), reverse=True)
            idx = 0
            while len(keep) > cap and idx < len(keep_sorted):
                m = keep_sorted[idx]
                if m in keep:
                    keep.remove(m)
                idx += 1
        else:
            # 未知策略，跳过
            pass
    return keep

def _dedup(mods: List[Dict], fields: List[str]) -> List[Dict]:
    seen = {}
    for m in mods:
        key_vals = []
        for f in fields:
            if f == 'fw':
                key_vals.append(_round_fw(m[f], 1))
            else:
                key_vals.append(m[f])
        key = tuple(key_vals)
        if key not in seen:
            seen[key] = m
        else:
            # 保留旧件（更早生成），忽略新件
            pass
    return sorted(list(seen.values()), key=lambda x: x.get('gen', 0))

# ---------------------------
# 统一执行入口
# ---------------------------
def function_2(initial_modules: List[Dict], ruleset: Dict[str, Any]) -> List[Dict]:
    """
    执行规则集（严格顺序）：
      固件增量 -> 替换 -> 复制 -> 统一外观 -> 分组规则 -> 固件窗口 -> 容量控制 -> 去重
    """
    # 初始化
    mods: List[Dict] = []
    gen = 0
    for m in initial_modules:
        gen += 1
        c = dict(m)
        c['fw'] = _round_fw(float(c['fw']), 1)
        c['gen'] = gen
        mods.append(c)

    # 1 增量
    _apply_inc_rules(mods, ruleset.get('inc_rules', []))
    # 2 替换
    mods, gen = _apply_replace_rules(mods, gen, ruleset.get('replace_rules', []))
    # 3 复制
    mods, gen = _apply_copy_rules(mods, gen, ruleset.get('copy_rules', []),
                                  ruleset['size_order'], ruleset['powers'],
                                  colors=list({m['color'] for m in mods}) or ['黑'])
    # 4 统一外观
    _apply_unify_rules(mods, ruleset.get('unify_rules', []))
    # 5 分组规则
    _apply_group_rules(mods, ruleset.get('group_rules', []), ruleset['powers'])
    # 6 固件窗口
    _apply_fw_window(mods, ruleset.get('fw_window'))
    # 7 容量控制
    cap = ruleset.get('capacity_rule', {})
    mods = _remove_by_capacity(mods,
                               cap.get('cap', len(mods)),
                               cap.get('phases', []),
                               cap.get('params', {}),
                               ruleset['size_order'],
                               cap.get('params', {}).get('type_order', []))
    # 8 去重
    mods = _dedup(mods, ruleset.get('dedup_fields', ['type','size','origin','material','power','color','fw']))

    return mods

def function_1(initial_modules: List[Dict], ruleset: Dict[str, Any]) -> int:
    """
    计算最终在架模块中，满足查询条件的数量：
      - 类型 ∈ include_types；
      - (颜色 ∈ condition_colors) 或 (材质 ∈ condition_materials)；
      - 功耗 != exclude_power。
    """
    final_mods = function_2(initial_modules, ruleset)
    q = ruleset.get('query', {})
    include_types = set(q.get('include_types', []))
    condition_colors = set(q.get('condition_colors', []))
    condition_materials = set(q.get('condition_materials', []))
    exclude_power = q.get('exclude_power')

    count = 0
    for m in final_mods:
        if m['type'] in include_types:
            if (m['color'] in condition_colors) or (m['material'] in condition_materials):
                if m['power'] != exclude_power:
                    count += 1
    return count

# ---------------------------
# 唯一解验证（软时限）
# ---------------------------
def verify_unique_answer(initial_modules: List[Dict], ruleset: Dict[str, Any], timeout_s: int = 120) -> bool:
    """
    验证思路：
      - 双通道一致性：深拷贝重放两次，答案应一致；
      - 不变性检查：对无关冗余字段做轻微扰动（如添加无用tag），答案不变；
      - 稳定性检测：容量控制采用稳定排序 + 最近生成优先，理论无分支歧义；进行一次状态哈希比对。
      - 软时限：默认120秒，实际仅需毫秒到秒级。
    """
    t0 = time.time()
    im1 = copy.deepcopy(initial_modules)
    im2 = copy.deepcopy(initial_modules)
    rs1 = copy.deepcopy(ruleset)
    rs2 = copy.deepcopy(ruleset)

    ans1 = function_1(im1, rs1)
    if time.time() - t0 > timeout_s:
        return False

    ans2 = function_1(im2, rs2)
    if ans1 != ans2:
        return False
    if time.time() - t0 > timeout_s:
        return False

    # 不变性扰动：添加无关tag
    im3 = copy.deepcopy(initial_modules)
    for i, m in enumerate(im3):
        m['_tag'] = i % 3  # 与规则无关的字段
    ans3 = function_1(im3, copy.deepcopy(ruleset))
    if ans3 != ans1:
        return False

    # 状态哈希比对（最终在架）
    fm1 = function_2(copy.deepcopy(initial_modules), copy.deepcopy(ruleset))
    fm2 = function_2(copy.deepcopy(initial_modules), copy.deepcopy(ruleset))
    def _state_hash(lst: List[Dict]) -> Tuple:
        # 只用规则相关字段构造哈希，按 gen 升序
        rel = []
        for m in sorted(lst, key=lambda x: x.get('gen', 0)):
            rel.append((
                m['type'], m['size'], m['origin'], m['material'],
                m['power'], m['color'], _round_fw(m['fw'], 1), m['gen']
            ))
        return tuple(rel)
    if _state_hash(fm1) != _state_hash(fm2):
        return False

    return (time.time() - t0) <= timeout_s