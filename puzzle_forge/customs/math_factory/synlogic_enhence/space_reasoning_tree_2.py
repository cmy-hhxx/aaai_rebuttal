# space_reasoning_tree_0.py

import random
from typing import List, Dict, Tuple


# 名称库，含部分带数字的名称，支持 200+ 题目
_WORD_BANK = [
    '蜂蜜', '珊瑚', '画布', '海螺', '柳树', '水壶', '地图', '灯塔', '铅笔', '向日葵', '葡萄', '橄榄', '茶壶', '火炬',
    '纽扣', '背包', '雨伞', '风铃', '草帽', '灯泡', '石榴', '棉花', '毛衣', '蜡烛', '衣架', '羊毛', '稻草', '雪松',
    '指南针', '手鼓', '纸鹤', '果酱', '酒杯', '相框', '花瓶', '饼干', '桌布', '火柴', '铃铛', '颜料', '口琴',
    '信封', '木盒', '水桶', '扇子', '陶罐', '珐琅', '尺子', '便签', '窗帘', '枕头', '被子', '藤篮', '串珠',
    '剪刀', '线轴', '钩针', '手套', '围巾', '靠垫', '拉链', '油灯', '火炉', '口袋', '贝壳', '喷壶', '泥瓦',
    '石板', '木桩', '树桩', '铜铃', '铁盒', '银杯', '彩绳', '丝线', '鹅毛', '羽扇', '柳笛', '竹篮', '竹笛',
    '木琴', '鼓槌', '花架', '藤椅', '茶杯', '茶盘', '咖啡', '奶酪', '面包', '蜜蜡', '桂皮', '豆蔻', '肉桂',
    '百里香', '薄荷', '胡椒', '盐罐', '糖罐', '果盘', '果篮', '果叉', '餐巾', '刀叉', '盘子', '勺子', '水壶2',
    '茶壶2', '木盒2', '藤篮2', '陶罐2', '窗帘2', '枕头2', '围巾2', '靠垫2', '拉链2', '油灯2', '火炉2',
    '海螺2', '柳树2', '地图2', '灯塔2', '铅笔2', '葡萄2', '橄榄2', '火炬2', '纽扣2', '背包2', '雨伞2',
    '风铃2', '草帽2', '灯泡2', '石榴2', '棉花2', '毛衣2', '蜡烛2', '衣架2', '羊毛2', '稻草2', '雪松2',
    '指南针2', '手鼓2', '纸鹤2', '果酱2', '酒杯2', '相框2', '花瓶2', '饼干2', '桌布2', '火柴2', '铃铛2',
    '颜料2', '口琴2', '信封2', '水桶2', '扇子2', '珐琅2', '尺子2', '便签2'
]

# 稳定的步骤优先级（用于渲染与计算顺序稳定化，题目为集合交集，顺序不影响结果，但展示要稳定）
_STEP_ORDER = [
    'name_len_parity',     # 名称长度奇偶
    'has_digit',           # 名称含数字
    'len_mod',             # 名称长度取模
    'parent_parity_equal', # 父级奇偶相同
    'parent_parity_diff',  # 父级奇偶不同
    'parent_xor_equal',    # 父级 XOR 相同
    'parent_xor_diff'      # 父级 XOR 不同
]


def _sample_unique(pool: List[str], k: int, exclude: set) -> List[str]:
    """从池中采样 k 个唯一名称，避开 exclude；不足则合成补齐。"""
    available = [x for x in pool if x not in exclude]
    if len(available) < k:
        idx = 1
        while len(available) < k:
            candidate = f'物品_{idx}'
            if candidate not in exclude and candidate not in available:
                available.append(candidate)
            idx += 1
    random.shuffle(available)
    return available[:k]


def gen_tree(parent_num: int, child_min: int, child_max: int, name_pool_size: int) -> Dict[str, object]:
    """
    生成两层树：
      - root_name: 根名称
      - parents: 根的直接孩子（父级）
      - children_map: 每个父级的孩子列表
      - parent_of_target: 目标父级
      - target_node: 目标节点（为某父级的孩子）
      - total_nodes: 总节点数
    """
    if parent_num < 3:
        parent_num = 3
    if child_min < 2:
        child_min = 2
    if child_max < child_min:
        child_min, child_max = child_max, child_min

    rng_pool = _WORD_BANK[:]
    if name_pool_size > len(rng_pool):
        needed = name_pool_size - len(rng_pool)
        rng_pool += [f'物品X_{i}' for i in range(needed)]
    random.shuffle(rng_pool)
    rng_pool = rng_pool[:name_pool_size]

    used = set()

    root_name = _sample_unique(rng_pool, 1, used)[0]
    used.add(root_name)

    parents = _sample_unique(rng_pool, parent_num, used)
    used.update(parents)

    children_map: Dict[str, List[str]] = {}
    total_children = 0
    for p in parents:
        cnt = random.randint(child_min, child_max)
        kids = _sample_unique(rng_pool, cnt, used)
        used.update(kids)
        kids = sorted(kids)  # 孩子按字典序升序
        children_map[p] = kids
        total_children += cnt

    parent_of_target = random.choice(parents)
    target_node = random.choice(children_map[parent_of_target])

    total_nodes = 1 + len(parents) + total_children

    return {
        'root_name': root_name,
        'parents': parents,
        'children_map': children_map,
        'parent_of_target': parent_of_target,
        'target_node': target_node,
        'total_nodes': total_nodes
    }


def _has_digit(s: str) -> bool:
    return any(ch.isdigit() for ch in s)


def _len_parity(s: str) -> str:
    return 'even' if (len(s) % 2 == 0) else 'odd'


def _len_mod(s: str, base: int) -> int:
    return len(s) % base


def _xor_flag(s: str) -> int:
    """名称长度奇偶与是否包含数字构造 XOR 标志：p=0(偶数)/1(奇数)，d=1(含数字)/0(不含数字)，返回 p^d。"""
    p = 0 if _len_parity(s) == 'even' else 1
    d = 1 if _has_digit(s) else 0
    return p ^ d


def _build_child_to_parent(tree_data: Dict[str, object]) -> Dict[str, str]:
    """构建孩子 -> 父级 的映射。"""
    c2p: Dict[str, str] = {}
    cmap: Dict[str, List[str]] = tree_data['children_map']
    for p, kids in cmap.items():
        for k in kids:
            c2p[k] = p
    return c2p


def _select_relevant_uncles(tree_data: Dict[str, object], cfg: Dict[str, object]) -> List[str]:
    """按规则选择相关叔辈（根的其他孩子）。"""
    parents: List[str] = tree_data['parents']
    target_parent: str = tree_data['parent_of_target']
    others = [p for p in parents if p != target_parent]

    t = cfg.get('uncle_sel', 'all_others')
    if t == 'all_others':
        return sorted(others)
    elif t == 'name_len_parity':
        parity = cfg.get('uncle_parity', 'even')
        return sorted([p for p in others if _len_parity(p) == parity])
    elif t == 'has_digit':
        return sorted([p for p in others if _has_digit(p)])
    elif t == 'xor_with_target':
        target_flag = _xor_flag(target_parent)
        return sorted([p for p in others if _xor_flag(p) == target_flag])
    return sorted(others)


def _filter_children(tree_data: Dict[str, object], uncles: List[str], cfg: Dict[str, object]) -> List[str]:
    """在叔辈的孩子集合上应用过滤规则管线（集合交集），得到有效堂兄弟。"""
    children_map: Dict[str, List[str]] = tree_data['children_map']
    acc: List[str] = []
    for u in uncles:
        acc.extend(children_map.get(u, []))

    acc = sorted(set(acc))  # 初始全集（去重 + 升序）

    c2p = _build_child_to_parent(tree_data)
    target_parent = tree_data['parent_of_target']
    target_parent_parity = _len_parity(target_parent)
    target_parent_xor = _xor_flag(target_parent)

    pipeline = cfg.get('child_pipeline', [])
    for step in pipeline:
        stype = step.get('type')
        if stype == 'name_len_parity':
            parity = step.get('parity', 'even')
            acc = [x for x in acc if _len_parity(x) == parity]
        elif stype == 'has_digit':
            acc = [x for x in acc if _has_digit(x)]
        elif stype == 'len_mod':
            base = step.get('base', 3)
            value = step.get('value', 0)
            acc = [x for x in acc if _len_mod(x, base) == value]
        elif stype == 'parent_parity_equal':
            acc = [x for x in acc if _len_parity(c2p.get(x, '')) == target_parent_parity]
        elif stype == 'parent_parity_diff':
            acc = [x for x in acc if _len_parity(c2p.get(x, '')) != target_parent_parity]
        elif stype == 'parent_xor_equal':
            acc = [x for x in acc if _xor_flag(c2p.get(x, '')) == target_parent_xor]
        elif stype == 'parent_xor_diff':
            acc = [x for x in acc if _xor_flag(c2p.get(x, '')) != target_parent_xor]
        acc = sorted(set(acc))

    return acc


def gen_rule_config(tree_data: Dict[str, object]) -> Dict[str, object]:
    """
    随机生成规则配置，含多阶段过滤与 XOR 叔辈选择：
      - uncle_sel ∈ {'all_others','name_len_parity','has_digit','xor_with_target'}
      - 如果 name_len_parity，uncle_parity ∈ {'even','odd'}
      - child_pipeline: 由 3~4 个步骤构成（集合交集）
         类型 ∈ {'name_len_parity','has_digit','len_mod','parent_parity_equal','parent_parity_diff','parent_xor_equal','parent_xor_diff'}
         * 至少包含 1 个“孩子名称属性”步骤（name_len_parity / has_digit / len_mod）
         * 至少包含 1 个“父级属性相关”步骤（parent_parity_* / parent_xor_*）
         * len_mod 的 base ∈ {3,5}，value 由目标节点名称长度奇偶映射：even->0, odd->1
      - 快速重试 + 网格搜索，确保非平凡性：1 <= 有效堂兄弟数 <= 6 且不等于原始全集
      - 渲染与计算统一按 _STEP_ORDER 排序，稳定输出，顺序不影响结果
    """
    parents: List[str] = tree_data['parents']
    parent_of_target: str = tree_data['parent_of_target']
    target_node: str = tree_data['target_node']

    target_parity = _len_parity(target_node)
    target_parent_parity = _len_parity(parent_of_target)
    mod_value = 0 if target_parity == 'even' else 1
    mod_bases = [3, 5]

    def _ok(uncles: List[str], filtered: List[str], children_map: Dict[str, List[str]]) -> bool:
        all_cousins = sorted(set([x for u in uncles for x in children_map.get(u, [])]))
        if len(uncles) < 1:
            return False
        if len(all_cousins) == 0:
            return False
        if len(filtered) == 0:
            return False
        if filtered == all_cousins:
            return False
        if len(filtered) > 6:
            return False
        return True

    children_map: Dict[str, List[str]] = tree_data['children_map']

    name_steps = ['name_len_parity', 'has_digit', 'len_mod']
    parent_steps = ['parent_parity_equal', 'parent_parity_diff', 'parent_xor_equal', 'parent_xor_diff']

    def _sorted_pipeline(types_set: set) -> List[Dict[str, object]]:
        """按照固定优先级输出稳定的步骤列表，并为各步骤生成参数。"""
        ordered_types = sorted(list(types_set), key=lambda x: _STEP_ORDER.index(x))
        finalized = []
        for st in ordered_types:
            if st == 'name_len_parity':
                parity = target_parent_parity if random.random() < 0.5 else ('even' if target_parent_parity == 'odd' else 'odd')
                finalized.append({'type': 'name_len_parity', 'parity': parity})
            elif st == 'has_digit':
                finalized.append({'type': 'has_digit'})
            elif st == 'len_mod':
                base = random.choice(mod_bases)
                finalized.append({'type': 'len_mod', 'base': base, 'value': mod_value})
            elif st == 'parent_parity_equal':
                finalized.append({'type': 'parent_parity_equal'})
            elif st == 'parent_parity_diff':
                finalized.append({'type': 'parent_parity_diff'})
            elif st == 'parent_xor_equal':
                finalized.append({'type': 'parent_xor_equal'})
            elif st == 'parent_xor_diff':
                finalized.append({'type': 'parent_xor_diff'})
        return finalized

    # 快速随机尝试
    for _ in range(200):
        uncle_sel = random.choice(['all_others', 'name_len_parity', 'has_digit', 'xor_with_target'])
        cfg = {'uncle_sel': uncle_sel}

        if uncle_sel == 'name_len_parity':
            cfg['uncle_parity'] = target_parent_parity if random.random() < 0.5 else ('even' if target_parent_parity == 'odd' else 'odd')

        step_count = random.choice([3, 4])
        pipeline_types = set()
        # 保证至少一个“孩子属性”与一个“父级属性”步骤
        pipeline_types.add(random.choice(name_steps))
        pipeline_types.add(random.choice(parent_steps))
        all_steps_pool = list(set(name_steps + parent_steps))
        while len(pipeline_types) < step_count:
            pipeline_types.add(random.choice(all_steps_pool))

        cfg['child_pipeline'] = _sorted_pipeline(pipeline_types)

        uncles = _select_relevant_uncles(tree_data, cfg)
        filtered = _filter_children(tree_data, uncles, cfg)
        if _ok(uncles, filtered, children_map):
            return cfg

    # 网格搜索回退（同样使用稳定排序）
    uncle_types = ['all_others', 'name_len_parity', 'has_digit', 'xor_with_target']
    parity_opts = ['even', 'odd']
    pipe_types_sets = [
        ['name_len_parity', 'has_digit', 'parent_parity_equal'],
        ['name_len_parity', 'len_mod', 'parent_parity_diff'],
        ['has_digit', 'len_mod', 'parent_xor_equal'],
        ['name_len_parity', 'has_digit', 'parent_xor_diff'],
        ['name_len_parity', 'has_digit', 'len_mod', 'parent_parity_equal'],
        ['name_len_parity', 'len_mod', 'parent_parity_diff', 'parent_xor_equal'],
        ['has_digit', 'len_mod', 'parent_parity_equal', 'parent_xor_diff'],
    ]
    for utype in uncle_types:
        for pipes in pipe_types_sets:
            cfg_base = {'uncle_sel': utype}
            up_candidates = ['even', 'odd'] if utype == 'name_len_parity' else [None]
            for up in up_candidates:
                cfg = dict(cfg_base)
                if up is not None:
                    cfg['uncle_parity'] = up

                variants = []

                def add_variant(parity=None, base=None):
                    steps_set = set(pipes)
                    # 生成稳定排序后的步骤，并注入参数
                    ordered_types = sorted(list(steps_set), key=lambda x: _STEP_ORDER.index(x))
                    steps = []
                    for t in ordered_types:
                        if t == 'name_len_parity':
                            steps.append({'type': 'name_len_parity', 'parity': parity if parity is not None else 'even'})
                        elif t == 'has_digit':
                            steps.append({'type': 'has_digit'})
                        elif t == 'len_mod':
                            steps.append({'type': 'len_mod', 'base': base if base is not None else 3, 'value': (0 if _len_parity(tree_data['target_node']) == 'even' else 1)})
                        elif t == 'parent_parity_equal':
                            steps.append({'type': 'parent_parity_equal'})
                        elif t == 'parent_parity_diff':
                            steps.append({'type': 'parent_parity_diff'})
                        elif t == 'parent_xor_equal':
                            steps.append({'type': 'parent_xor_equal'})
                        elif t == 'parent_xor_diff':
                            steps.append({'type': 'parent_xor_diff'})
                    variants.append(steps)

                for pp in parity_opts:
                    for bb in [3, 5]:
                        add_variant(parity=pp, base=bb)

                for pipeline in variants:
                    cfg['child_pipeline'] = pipeline
                    uncles = _select_relevant_uncles(tree_data, cfg)
                    filtered = _filter_children(tree_data, uncles, cfg)
                    if _ok(uncles, filtered, children_map):
                        return cfg

    # 兜底：尽力选择一个非平凡的配置（稳定排序）
    base_cfg = {'uncle_sel': 'xor_with_target'}
    for pp in ['even', 'odd', target_parent_parity, ('even' if target_parent_parity == 'odd' else 'odd')]:
        cfg = dict(base_cfg)
        pipe_types = {'name_len_parity', 'parent_xor_equal', 'len_mod'}
        ordered_types = sorted(list(pipe_types), key=lambda x: _STEP_ORDER.index(x))
        cfg['child_pipeline'] = []
        for t in ordered_types:
            if t == 'name_len_parity':
                cfg['child_pipeline'].append({'type': 'name_len_parity', 'parity': pp})
            elif t == 'len_mod':
                cfg['child_pipeline'].append({'type': 'len_mod', 'base': 3, 'value': (0 if _len_parity(tree_data['target_node']) == 'even' else 1)})
            elif t == 'parent_xor_equal':
                cfg['child_pipeline'].append({'type': 'parent_xor_equal'})
        uncles = _select_relevant_uncles(tree_data, cfg)
        filtered = _filter_children(tree_data, uncles, cfg)
        if _ok(uncles, filtered, children_map):
            return cfg

        pipe_types = {'name_len_parity', 'parent_parity_equal', 'has_digit'}
        ordered_types = sorted(list(pipe_types), key=lambda x: _STEP_ORDER.index(x))
        cfg['child_pipeline'] = []
        for t in ordered_types:
            if t == 'name_len_parity':
                cfg['child_pipeline'].append({'type': 'name_len_parity', 'parity': pp})
            elif t == 'has_digit':
                cfg['child_pipeline'].append({'type': 'has_digit'})
            elif t == 'parent_parity_equal':
                cfg['child_pipeline'].append({'type': 'parent_parity_equal'})
        uncles = _select_relevant_uncles(tree_data, cfg)
        filtered = _filter_children(tree_data, uncles, cfg)
        if _ok(uncles, filtered, children_map):
            return cfg

    # 最终兜底
    return {
        'uncle_sel': 'xor_with_target',
        'child_pipeline': [
            {'type': 'name_len_parity', 'parity': _len_parity(tree_data['parent_of_target'])},
            {'type': 'len_mod', 'base': 3, 'value': (0 if _len_parity(tree_data['target_node']) == 'even' else 1)},
            {'type': 'parent_xor_equal'}
        ]
    }


def render_children_desc(tree_data: Dict[str, object]) -> str:
    """单行描述每个父级的孩子（孩子名称按字典序升序）。"""
    parts = []
    children_map: Dict[str, List[str]] = tree_data['children_map']
    for p in sorted(tree_data['parents']):
        kids = sorted(children_map.get(p, []))
        segment = f'{p}的孩子是({", ".join(kids)})'
        parts.append(segment)
    return '; '.join(parts)


def render_rule_desc(tree_data: Dict[str, object], cfg: Dict[str, object]) -> str:
    """
    渲染规则配置为自然语言，单行说明：
      - 相关叔辈定义（自然语言）
      - 堂兄弟过滤管线每步说明（集合交集，顺序无关）
      - 排序与口径说明（必要信息）
      - 异或标志的定义
    """
    parent_of_target = tree_data['parent_of_target']
    target_node = tree_data['target_node']
    tn_parity = _len_parity(target_node)
    mod_value = 0 if tn_parity == 'even' else 1

    uncle_sel = cfg.get('uncle_sel', 'all_others')
    if uncle_sel == 'all_others':
        uncle_desc = '相关叔辈为除目标父级外的所有父级'
    elif uncle_sel == 'name_len_parity':
        p = cfg.get('uncle_parity', 'even')
        uncle_desc = f'相关叔辈为除目标父级外, 名称长度为{"偶数" if p=="even" else "奇数"}的父级'
    elif uncle_sel == 'has_digit':
        uncle_desc = '相关叔辈为除目标父级外, 名称中包含数字的父级'
    else:
        uncle_desc = '相关叔辈为除目标父级外, 以异或标志筛选(定义: p为名称长度奇偶, 偶数取0奇数取1; d为是否含数字, 含取1不含取0; 异或标志为p XOR d), 标志与目标父级相同者'

    pipe = cfg.get('child_pipeline', [])
    pipe_desc_parts = []
    for step in pipe:
        st = step.get('type')
        if st == 'name_len_parity':
            parity = step.get('parity', 'even')
            pipe_desc_parts.append(f'步骤: 名称长度为{"偶数" if parity=="even" else "奇数"}')
        elif st == 'has_digit':
            pipe_desc_parts.append('步骤: 名称中包含数字')
        elif st == 'len_mod':
            base = step.get('base', 3)
            value = step.get('value', mod_value)
            pipe_desc_parts.append(f'步骤: 名称长度对{base}取模等于{value}')
        elif st == 'parent_parity_equal':
            pipe_desc_parts.append('步骤: 其父级的名称长度奇偶与目标父级相同')
        elif st == 'parent_parity_diff':
            pipe_desc_parts.append('步骤: 其父级的名称长度奇偶与目标父级不同')
        elif st == 'parent_xor_equal':
            pipe_desc_parts.append('步骤: 其父级的异或标志与目标父级相同')
        elif st == 'parent_xor_diff':
            pipe_desc_parts.append('步骤: 其父级的异或标志与目标父级不同')
    pipe_desc = '; '.join(pipe_desc_parts) if pipe_desc_parts else '步骤: 无'

    extra = '结果按字典序升序输出(逐字符比较); 名称长度按字符数计算; 含数字指含0-9任意一位; 父级属性均指堂兄弟的父级名称属性; 所有步骤为集合交集且步骤顺序不影响结果'
    return f'{uncle_desc}; 堂兄弟过滤管线为[{pipe_desc}], {extra}'


def cousins_list_str(tree_data: Dict[str, object]) -> str:
    """原始堂兄弟（不带过滤）：目标父级的兄弟的孩子全集，逗号分隔；为空返回 none。"""
    parents: List[str] = tree_data['parents']
    children_map: Dict[str, List[str]] = tree_data['children_map']
    target_parent: str = tree_data['parent_of_target']
    sibs = [p for p in parents if p != target_parent]
    cousins: List[str] = []
    for s in sibs:
        if s not in children_map:
            return 'none'
        cousins.extend(children_map[s])
    unique_sorted = sorted(set(cousins))
    return ', '.join(unique_sorted) if unique_sorted else 'none'


def cousins_count(tree_data: Dict[str, object]) -> int:
    """原始堂兄弟数量（不带过滤）。"""
    parents: List[str] = tree_data['parents']
    children_map: Dict[str, List[str]] = tree_data['children_map']
    target_parent: str = tree_data['parent_of_target']
    sibs = [p for p in parents if p != target_parent]
    cousins: List[str] = []
    for s in sibs:
        if s not in children_map:
            return 0
        cousins.extend(children_map[s])
    return len(set(cousins))


def cousins_list_py(tree_data: Dict[str, object]) -> str:
    """原始堂兄弟列表的 Python 字符串（单引号、升序）。"""
    parents: List[str] = tree_data['parents']
    children_map: Dict[str, List[str]] = tree_data['children_map']
    target_parent: str = tree_data['parent_of_target']
    sibs = [p for p in parents if p != target_parent]
    cousins: List[str] = []
    for s in sibs:
        if s not in children_map:
            return '[]'
        cousins.extend(children_map[s])
    unique_sorted = sorted(set(cousins))
    if not unique_sorted:
        return '[]'
    return '[' + ', '.join(f"'{x}'" for x in unique_sorted) + ']'


def relevant_uncles_list_str(tree_data: Dict[str, object], cfg: Dict[str, object]) -> str:
    """相关叔辈的逗号分隔字符串，升序；为空返回 none。"""
    uncles = _select_relevant_uncles(tree_data, cfg)
    return ', '.join(uncles) if uncles else 'none'


def relevant_uncles_list_py(tree_data: Dict[str, object], cfg: Dict[str, object]) -> str:
    """相关叔辈的 Python 列表字符串（单引号、升序）。"""
    uncles = _select_relevant_uncles(tree_data, cfg)
    if not uncles:
        return '[]'
    return '[' + ', '.join(f"'{x}'" for x in uncles) + ']'


def filtered_cousins_list_str(tree_data: Dict[str, object], cfg: Dict[str, object]) -> str:
    """按规则过滤后的有效堂兄弟，逗号分隔；为空返回 none。"""
    uncles = _select_relevant_uncles(tree_data, cfg)
    filtered = _filter_children(tree_data, uncles, cfg)
    return ', '.join(filtered) if filtered else 'none'


def filtered_cousins_count(tree_data: Dict[str, object], cfg: Dict[str, object]) -> int:
    """按规则过滤后的有效堂兄弟数量。"""
    uncles = _select_relevant_uncles(tree_data, cfg)
    filtered = _filter_children(tree_data, uncles, cfg)
    return len(filtered)


def filtered_cousins_list_py(tree_data: Dict[str, object], cfg: Dict[str, object]) -> str:
    """按规则过滤后的有效堂兄弟的 Python 列表字符串（单引号、升序）。"""
    uncles = _select_relevant_uncles(tree_data, cfg)
    filtered = _filter_children(tree_data, uncles, cfg)
    if not filtered:
        return '[]'
    return '[' + ', '.join(f"'{x}'" for x in filtered) + ']'


def compose_final_answer(tree_data: Dict[str, object], cfg: Dict[str, object]) -> str:
    """
    组合最终答案字符串：'<q1>====<q2>====<q3>'。
    q1: 有效堂兄弟名称的逗号+空格分隔字符串或 none
    q2: 有效堂兄弟数量（整数）
    q3: 相关叔辈的 Python 列表字符串（单引号、升序）
    """
    q1 = filtered_cousins_list_str(tree_data, cfg)
    q2 = str(filtered_cousins_count(tree_data, cfg))
    q3 = relevant_uncles_list_py(tree_data, cfg)
    return f'{q1}===={q2}===={q3}'


def validate_tree(tree_data: Dict[str, object]) -> bool:
    """
    验证基础树结构：
      - 目标父级确属父级列表，目标节点确属该父级孩子列表；
      - 父级数量 >= 3，每个父级至少 1 个孩子；
      - 所有名称唯一。
    """
    root = tree_data['root_name']
    parents = tree_data['parents']
    children_map = tree_data['children_map']
    parent_of_target = tree_data['parent_of_target']
    target_node = tree_data['target_node']

    if parent_of_target not in parents:
        return False
    if parent_of_target not in children_map:
        return False
    if target_node not in children_map[parent_of_target]:
        return False

    if len(parents) < 3:
        return False
    for p in parents:
        if p not in children_map or len(children_map[p]) < 1:
            return False

    all_names = [root] + parents + [x for lst in children_map.values() for x in lst]
    if len(all_names) != len(set(all_names)):
        return False

    return True


def validate_puzzle(tree_data: Dict[str, object], cfg: Dict[str, object]) -> bool:
    """
    验证题目可计算性与一致性：
      - 基础树结构通过；
      - 规则配置字段完备；
      - 应用规则后能正常计算；
    """
    if not validate_tree(tree_data):
        return False

    if 'uncle_sel' not in cfg or 'child_pipeline' not in cfg:
        return False

    try:
        uncles = _select_relevant_uncles(tree_data, cfg)
        _ = _filter_children(tree_data, uncles, cfg)
    except Exception:
        return False

    return True


def validate_unique(tree_data: Dict[str, object], cfg: Dict[str, object]) -> bool:
    """
    唯一性与一致性验证：
      - 管线步骤均为集合交集，验证不同顺序下结果一致；
      - 三个答案之间一致：list_str 与 list_py 内容匹配，count 与列表长度匹配；
      - 叔辈列表与其字符串表现一致；
      - 最终答案组合与三项一致。
    """
    uncles = _select_relevant_uncles(tree_data, cfg)
    filtered = _filter_children(tree_data, uncles, cfg)
    list_str = ', '.join(filtered) if filtered else 'none'
    list_py = '[' + ', '.join(f"'{x}'" for x in filtered) + ']' if filtered else '[]'
    count = len(filtered)
    uncles_py = '[' + ', '.join(f"'{u}'" for u in uncles) + ']' if uncles else '[]'
    uncles_str = ', '.join(uncles) if uncles else 'none'
    final_ans = compose_final_answer(tree_data, cfg)

    pipe = cfg.get('child_pipeline', [])
    bases = [3, 5]
    c2p = _build_child_to_parent(tree_data)
    target_parent = tree_data['parent_of_target']
    target_parent_parity = _len_parity(target_parent)
    target_parent_xor = _xor_flag(target_parent)

    def apply_pipeline_order(order: List[Dict[str, object]]) -> List[str]:
        children_map: Dict[str, List[str]] = tree_data['children_map']
        acc = sorted(set([x for u in uncles for x in children_map.get(u, [])]))
        for step in order:
            st = step.get('type')
            if st == 'name_len_parity':
                parity = step.get('parity', 'even')
                acc = [x for x in acc if _len_parity(x) == parity]
            elif st == 'has_digit':
                acc = [x for x in acc if _has_digit(x)]
            elif st == 'len_mod':
                base = step.get('base', 3)
                value = step.get('value', 0)
                if base not in bases:
                    return []
                acc = [x for x in acc if _len_mod(x, base) == value]
            elif st == 'parent_parity_equal':
                acc = [x for x in acc if _len_parity(c2p.get(x, '')) == target_parent_parity]
            elif st == 'parent_parity_diff':
                acc = [x for x in acc if _len_parity(c2p.get(x, '')) != target_parent_parity]
            elif st == 'parent_xor_equal':
                acc = [x for x in acc if _xor_flag(c2p.get(x, '')) == target_parent_xor]
            elif st == 'parent_xor_diff':
                acc = [x for x in acc if _xor_flag(c2p.get(x, '')) != target_parent_xor]
            acc = sorted(set(acc))
        return acc

    # 随机打乱顺序验证顺序无关性
    for _ in range(min(25, len(pipe) * 6 + 7)):
        order = pipe[:]
        random.shuffle(order)
        if apply_pipeline_order(order) != filtered:
            return False

    def parse_py_list_str(s: str) -> List[str]:
        if s == '[]':
            return []
        parts = [seg.strip() for seg in s.strip('[]').split(',') if seg.strip()]
        return [p.strip().strip("'") for p in parts]

    parsed_filtered = parse_py_list_str(list_py)
    if count != len(parsed_filtered):
        return False
    if (list_str == 'none' and parsed_filtered != []) or (list_str != 'none' and parsed_filtered == []):
        return False
    if list_str != 'none':
        elems_str = [seg.strip() for seg in list_str.split(',')]
        if [e.strip() for e in elems_str] != parsed_filtered:
            return False

    parsed_uncles = parse_py_list_str(uncles_py)
    if (uncles_str == 'none' and parsed_uncles != []) or (uncles_str != 'none' and parsed_uncles == []):
        return False
    if uncles_str != 'none':
        u_str = [seg.strip() for seg in uncles_str.split(',')]
        if [u.strip() for u in u_str] != parsed_uncles:
            return False

    if final_ans != f'{list_str}===={count}===={uncles_py}':
        return False

    return True


def compute_cousins(tree_data: Dict[str, object] = None,
                    rule_cfg: Dict[str, object] = None) -> Dict[str, object]:
    """
    辅助函数：
      - 若未提供参数，使用默认参数生成一个小规模树与规则配置；
      - 返回相关叔辈与按规则过滤后的有效堂兄弟的多种表示。
    """
    if tree_data is None:
        tree_data = gen_tree(parent_num=3, child_min=2, child_max=4, name_pool_size=80)
    if rule_cfg is None:
        rule_cfg = gen_rule_config(tree_data)

    uncles = _select_relevant_uncles(tree_data, rule_cfg)
    uncles_str = ', '.join(uncles) if uncles else 'none'
    uncles_py = '[' + ', '.join(f"'{u}'" for u in uncles) + ']' if uncles else '[]'

    filtered = _filter_children(tree_data, uncles, rule_cfg)
    filtered_str = ', '.join(filtered) if filtered else 'none'
    filtered_py = '[' + ', '.join(f"'{x}'" for x in filtered) + ']' if filtered else '[]'
    count = len(filtered)
    final_answer = compose_final_answer(tree_data, rule_cfg)

    return {
        'uncles': uncles,
        'uncles_str': uncles_str,
        'uncles_py': uncles_py,
        'filtered': filtered,
        'filtered_str': filtered_str,
        'filtered_py': filtered_py,
        'count': count,
        'final_answer': final_answer
    }


def parents_sorted_py(tree_data: Dict[str, object]) -> str:
    """按字典序升序输出父级列表的 Python 列表字符串（单引号）。"""
    arr = sorted(tree_data.get('parents', []))
    if not arr:
        return '[]'
    return '[' + ', '.join(f"'{x}'" for x in arr) + ']'


def filtered_cousins_limit_ok(tree_data: Dict[str, object], cfg: Dict[str, object], limit: int) -> bool:
    """检查有效堂兄弟数量是否不超过给定上限（与 YAML 断言配合）。"""
    try:
        cnt = filtered_cousins_count(tree_data, cfg)
        return cnt <= limit
    except Exception:
        return False