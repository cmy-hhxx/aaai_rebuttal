# space_reasoning_0.py

from typing import Dict, List, Tuple, Any
import random
import time

# 方向向量（菱形网络）
_DIR_VEC: Dict[str, Tuple[int, int]] = {
    'RD': (1, 0),
    'LD': (0, 1),
    'LU': (-1, 0),
    'RU': (0, -1),
}
_DIRS: List[str] = ['RD', 'LD', 'LU', 'RU']

# 镜像映射：RD<->LU，LD<->RU
_MIRROR_DIR: Dict[str, str] = {
    'RD': 'LU',
    'LU': 'RD',
    'LD': 'RU',
    'RU': 'LD',
}


def _apply_steps(start: Tuple[int, int], steps: List[Tuple[str, int]]) -> Tuple[int, int]:
    """从起点按步骤序列移动并返回终点坐标。"""
    x, y = start
    for d, k in steps:
        if d not in _DIR_VEC:
            raise ValueError(f'Unknown direction: {d}')
        dx, dy = _DIR_VEC[d]
        x += dx * int(k)
        y += dy * int(k)
    return (x, y)


def _assign(pos_to_item: Dict[Tuple[int, int], str], pos: Tuple[int, int], item: str):
    """将物品放置到坐标上，若已放置则检查一致性。"""
    if pos in pos_to_item and pos_to_item[pos] != item:
        raise ValueError(f'Contradiction at {pos}: {pos_to_item[pos]} vs {item}')
    pos_to_item[pos] = item


def _rand_steps(len_min: int, len_max: int, step_max: int) -> List[Tuple[str, int]]:
    """生成随机步序列，长度在 [len_min, len_max]，每步步长在 [1, step_max]。"""
    L = random.randint(len_min, len_max)
    seq: List[Tuple[str, int]] = []
    for _ in range(L):
        d = random.choice(_DIRS)
        k = random.randint(1, step_max)
        seq.append((d, k))
    return seq


def _net_vec(steps: List[Tuple[str, int]]) -> Tuple[int, int]:
    """返回步序列的净位移 (dx, dy)。"""
    dx = dy = 0
    for d, k in steps:
        vx, vy = _DIR_VEC[d]
        dx += vx * int(k)
        dy += vy * int(k)
    return dx, dy


def _rand_steps_nonzero(len_min: int, len_max: int, step_max: int, max_retry: int = 50) -> List[Tuple[str, int]]:
    """生成净位移非零的随机步序列，失败则兜底加一步。"""
    for _ in range(max_retry):
        seq = _rand_steps(len_min, len_max, step_max)
        if _net_vec(seq) != (0, 0):
            return seq
    return [('RD', 1)]


def _random_split(n: int, parts: int) -> List[int]:
    """将正整数 n 拆分为 parts 段正整数和（parts<=n），返回长度为 parts 的列表。"""
    if parts <= 0:
        return []
    if n <= 0:
        return [0] * parts
    parts = min(parts, n)
    cuts = sorted(random.sample(range(1, n), parts - 1)) if parts > 1 else []
    segs = []
    prev = 0
    for c in cuts:
        segs.append(c - prev)
        prev = c
    segs.append(n - prev)
    random.shuffle(segs)
    return segs


def _vector_to_path(dx: int, dy: int, max_segments_per_axis: int = 3) -> List[Tuple[str, int]]:
    """
    将向量 (dx, dy) 转换为由四方向组成的路径。
    对每个轴的绝对位移随机拆分成 1..max_segments_per_axis 段，然后随机交错。
    """
    steps: List[Tuple[str, int]] = []

    if dx != 0:
        sx = abs(dx)
        parts_x = random.randint(1, min(max_segments_per_axis, sx))
        splits_x = _random_split(sx, parts_x)
        dir_x = 'RD' if dx > 0 else 'LU'
        for val in splits_x:
            if val > 0:
                steps.append((dir_x, val))

    if dy != 0:
        sy = abs(dy)
        parts_y = random.randint(1, min(max_segments_per_axis, sy))
        splits_y = _random_split(sy, parts_y)
        dir_y = 'LD' if dy > 0 else 'RU'
        for val in splits_y:
            if val > 0:
                steps.append((dir_y, val))

    random.shuffle(steps)
    if not steps or _net_vec(steps) == (0, 0):
        return [('RD', 1)]
    return steps


def _mirror_steps(steps: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    """镜像路径：仅将每一步方向进行 RD<->LU、LD<->RU 的互换，步长与顺序保持不变。"""
    ms = [(_MIRROR_DIR[d], int(k)) for d, k in steps]
    if not ms or _net_vec(ms) == (0, 0):
        return [('RD', 1)]
    return ms


def pretty_steps(steps: List[Tuple[str, int]]) -> str:
    """将步序列格式化为 'RD1, LD2, ...' 文本。"""
    if not steps:
        return 'RD1'
    return ', '.join([f'{d}{int(k)}' for d, k in steps])


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """曼哈顿距离 |dx|+|dy|"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _parity(xy: Tuple[int, int]) -> int:
    """(x+y) 的奇偶：返回 0/1"""
    return (xy[0] + xy[1]) & 1


def _anchor_label(key: str, items: Dict[str, str]) -> str:
    """
    将内部锚点代号映射为题面自然语言标签。
    items: {
      'item_at_proj', 'item_next1', 'item_printer', 'item_speaker'
    }
    """
    mapping = {
        'S0': '起点',
        'P': f'看到{items["item_at_proj"]}的位置',
        'N1': f'看到{items["item_next1"]}的位置',
        'T0': '瞬移起点',
        'PR': f'看到{items["item_printer"]}的位置',
        'SPK': f'看到{items["item_speaker"]}的位置',
        'CUR': '当前位置',
    }
    return mapping.get(key, key)


def diamond_item_solver(data: Dict[str, Any]) -> str:
    """
    求解器：依据题面叙述的多段路径与观测，建立相对坐标与物品映射，
    然后从当前点按查询路径求终点物品，若未知则返回 'unknown'。
    """
    start_item = data['start_item']
    seq_until_proj = data['seq_until_proj']
    item_at_proj = data['item_at_proj']

    seq_to_next1 = data['seq_to_next1']
    item_next1 = data['item_next1']

    jump_item = data['jump_item']
    seq_to_printer = data['seq_to_printer']
    item_printer = data['item_printer']
    seq_back_to_start = data['seq_back_to_start']

    seq_to_speaker = data['seq_to_speaker']
    item_speaker = data['item_speaker']
    seq_to_current = data['seq_to_current']
    current_item = data['current_item']

    query_path = data['query_path']
    extras = data.get('extras', [])

    pos_to_item: Dict[Tuple[int, int], str] = {}

    # S0 = (0,0)
    S0 = (0, 0)
    _assign(pos_to_item, S0, start_item)

    # 到投影仪处
    P = _apply_steps(S0, seq_until_proj)
    _assign(pos_to_item, P, item_at_proj)

    # 再到 next1
    N1 = _apply_steps(P, seq_to_next1)
    _assign(pos_to_item, N1, item_next1)

    # 第二段：未知 T0，满足 T0 + seq_to_printer + seq_back_to_start = S0
    dx3, dy3 = _net_vec(list(seq_to_printer) + list(seq_back_to_start))
    T0 = (S0[0] - dx3, S0[1] - dy3)
    _assign(pos_to_item, T0, jump_item)

    PR = _apply_steps(T0, seq_to_printer)
    _assign(pos_to_item, PR, item_printer)

    back = _apply_steps(PR, seq_back_to_start)
    if back != S0:
        raise ValueError('Inconsistent back-to-start loop.')

    # 第三段：S0 -> SPK -> CUR
    SPK = _apply_steps(S0, seq_to_speaker)
    _assign(pos_to_item, SPK, item_speaker)

    CUR = _apply_steps(SPK, seq_to_current)
    _assign(pos_to_item, CUR, current_item)

    # 应用额外规则
    anchors: Dict[str, Tuple[int, int]] = {
        'S0': S0, 'P': P, 'N1': N1, 'T0': T0, 'PR': PR, 'SPK': SPK, 'CUR': CUR
    }
    for ex in extras:
        src = ex.get('from', 'S0')
        seq = ex['seq']
        item = ex['item']
        if src not in anchors:
            raise ValueError('Unknown anchor in extras.')
        start_pos = anchors[src]
        end_pos = _apply_steps(start_pos, seq)
        _assign(pos_to_item, end_pos, item)

    # 可选隐式约束验证
    meta = data.get('meta_constraints')
    if meta:
        mp = meta.get('manhattan_pair')
        if mp and isinstance(mp, (list, tuple)) and len(mp) == 2:
            if 'CUR' in mp:
                raise ValueError('Manhattan pair must not include CUR.')
            a1 = anchors.get(mp[0])
            a2 = anchors.get(mp[1])
            if a1 is None or a2 is None or a1 == a2:
                raise ValueError('Invalid manhattan pair anchors.')
            if _manhattan(CUR, a1) != _manhattan(CUR, a2):
                raise ValueError('Manhattan constraint violated.')

        pa = meta.get('parity_anchor')
        psame = meta.get('parity_same')
        if pa:
            if pa == 'CUR':
                raise ValueError('Parity anchor must not be CUR.')
            if anchors.get(pa) is None:
                raise ValueError('Unknown anchor in parity_anchor.')
            same_flag = bool(psame)
            if same_flag != (_parity(CUR) == _parity(anchors[pa])):
                raise ValueError('Parity constraint violated.')

    QEND = _apply_steps(CUR, query_path)
    return pos_to_item.get(QEND, 'unknown')


def _build_anchors(
    S0,
    seq_until_proj, seq_to_next1,
    seq_to_printer, seq_back_to_start,
    seq_to_speaker, seq_to_current,
    start_item, item_at_proj, item_next1, jump_item, item_printer, item_speaker, current_item
):
    """构建并返回锚点及映射，若环路不闭合则抛出异常。"""
    pos_to_item: Dict[Tuple[int, int], str] = {}
    _assign(pos_to_item, S0, start_item)
    P = _apply_steps(S0, seq_until_proj)
    _assign(pos_to_item, P, item_at_proj)
    N1 = _apply_steps(P, seq_to_next1)
    _assign(pos_to_item, N1, item_next1)

    dx_all, dy_all = _net_vec(list(seq_to_printer) + list(seq_back_to_start))
    T0 = (S0[0] - dx_all, S0[1] - dy_all)
    _assign(pos_to_item, T0, jump_item)

    PR = _apply_steps(T0, seq_to_printer)
    _assign(pos_to_item, PR, item_printer)

    back = _apply_steps(PR, seq_back_to_start)
    if back != S0:
        raise ValueError('Back-to-start loop invalid.')

    SPK = _apply_steps(S0, seq_to_speaker)
    _assign(pos_to_item, SPK, item_speaker)
    CUR = _apply_steps(SPK, seq_to_current)
    _assign(pos_to_item, CUR, current_item)

    anchors = {'S0': S0, 'P': P, 'N1': N1, 'T0': T0, 'PR': PR, 'SPK': SPK, 'CUR': CUR}
    return anchors, pos_to_item


def verify_uniqueness(story: Dict[str, Any], coord_bound: int, timeout_sec: float = 170.0) -> bool:
    """
    一致性与唯一性（防直达泄露）验证：
    - 路径与环路一致性
    - extras 与隐式约束一致
    - 坐标不越界
    - 一物一地
    - 禁止从 CUR 出发的额外规则
    - 查询终点不与任何从 CUR 出发的额外规则终点重合
    - 规则类型覆盖检查（至少包含 mirror 与 equal_vec）
    - 答案格式合法
    """
    t0 = time.time()

    try:
        S0 = (0, 0)
        A, pos_to_item = _build_anchors(
            S0,
            story['seq_until_proj'], story['seq_to_next1'],
            story['seq_to_printer'], story['seq_back_to_start'],
            story['seq_to_speaker'], story['seq_to_current'],
            story['start_item'], story['item_at_proj'], story['item_next1'],
            story['jump_item'], story['item_printer'], story['item_speaker'], story['current_item']
        )

        # 规则类型覆盖检查
        extras = story.get('extras', [])
        if len(extras) < 2:
            return False
        types = set(ex.get('type') for ex in extras)
        if not ('mirror' in types and 'equal_vec' in types):
            return False

        # 应用额外规则
        ext_endpoints_from_cur: List[Tuple[int, int]] = []
        for ex in extras:
            if time.time() - t0 > timeout_sec:
                return False
            src = ex.get('from', 'S0')
            if src == 'CUR':
                return False  # 严禁从 CUR 出发的额外规则
            seq = ex['seq']
            item = ex['item']
            if src not in A:
                return False
            end_pos = _apply_steps(A[src], seq)
            _assign(pos_to_item, end_pos, item)
            if src == 'CUR':
                ext_endpoints_from_cur.append(end_pos)

        # 隐式约束
        meta = story.get('meta_constraints')
        if meta:
            mp = meta.get('manhattan_pair')
            if mp:
                if 'CUR' in mp:
                    return False
                a1 = A.get(mp[0]); a2 = A.get(mp[1])
                if a1 is None or a2 is None or a1 == a2:
                    return False
                if _manhattan(A['CUR'], a1) != _manhattan(A['CUR'], a2):
                    return False
            pa = meta.get('parity_anchor')
            if pa:
                if pa == 'CUR':
                    return False
                if bool(meta.get('parity_same')) != (_parity(A['CUR']) == _parity(A[pa])):
                    return False

        # 边界检查（含 QEND 与 extras 端点）
        points = list(A.values())
        QEND = _apply_steps(A['CUR'], story['query_path'])
        points.append(QEND)
        for ex in extras:
            st = A[ex['from']]
            ed = _apply_steps(st, ex['seq'])
            points.append(ed)
        max_abs = max(max(abs(px), abs(py)) for (px, py) in points)
        if max_abs > coord_bound:
            return False

        # 一物一地
        item_to_positions: Dict[str, List[Tuple[int, int]]] = {}
        for pos, it in pos_to_item.items():
            item_to_positions.setdefault(it, []).append(pos)
        for it, locs in item_to_positions.items():
            if len(set(locs)) > 1:
                return False

        # 防直达泄露（冗余）：CUR 出发的任何额外规则不可到达与 query_path 相同的终点
        if QEND in ext_endpoints_from_cur:
            return False

        ans = pos_to_item.get(QEND, 'unknown')
        if not isinstance(ans, str):
            return False
        used_items = story['used_items']
        if not (ans == 'unknown' or ans in used_items):
            return False

        for _, v in pos_to_item.items():
            if not isinstance(v, str):
                return False

        return True
    except Exception:
        return False


def gen_story(
    layer_n: int,
    item_pool_size: int,
    len_min: int,
    len_max: int,
    step_max: int,
    coord_bound: int,
    want_known_answer: bool,
    extras_min: int,
    extras_max: int
) -> Dict[str, Any]:
    """
    生成完整故事数据（避免显见线索版本）：
    - 随机物品与多段路径（均为非零净位移，含返回起点的校验环）
    - 至少两条额外规则，强制覆盖 mirror 与 equal_vec 类型
    - 显式规则文本与隐式约束（奇偶性；可选曼哈顿）
    - 查询路径避开从 CUR 出发的任何额外规则终点
    """
    base_items = [
        '打印机', '投影仪', '智能音箱', '显示器', '键盘', '鼠标', '路由器', '交换机', '摄像头', '文件夹',
        '订书机', '打孔器', '订书针', '白板', '白板笔', '水杯', '咖啡机', '雨伞', '书架', '资料盒',
        '窗帘', '台灯', '落地灯', '沙发', '茶几', '吊兰', '绿萝', '发财树', '仙人掌', '相框',
        '时钟', '笔记本', '便签', 'U盘', '移动硬盘', '扩展坞', '耳机', '耳麦', '音响', '热水壶',
        '加湿器', '空气净化器', '插线板', '网线', '电池', '订书钉', '长尾夹', '文件袋', '图钉', '回形针',
        '椅子', '靠垫', '垃圾桶', '擦窗器', '抹布', '扫帚', '簸箕', '地垫', '门牌', '名片盒'
    ]

    start_wall = time.time()
    for _attempt in range(300):
        if time.time() - start_wall > 170.0:
            break
        try:
            pool = random.sample(base_items, k=min(max(9, item_pool_size), len(base_items)))
            chosen = random.sample(pool, 7)
            start_item, item_at_proj, item_next1, jump_item, item_printer, item_speaker, current_item = chosen

            # 路径长度上限轻度受 layer_n 影响
            len_max_adj = min(len_max + (1 if layer_n >= 15 else 0), len_max + 2)

            # 主干路径
            seq_until_proj = _rand_steps_nonzero(len_min, len_max_adj, step_max)
            seq_to_next1 = _rand_steps_nonzero(len_min + 1, len_max_adj + 1, step_max)

            seq_to_printer = _rand_steps_nonzero(len_min, len_max_adj, step_max)
            dxp, dyp = _net_vec(seq_to_printer)
            # 构造闭环的“返回起点”片段
            for _v_try in range(50):
                v_seq = _rand_steps_nonzero(len_min, len_max_adj, step_max)
                dxv, dyv = _net_vec(v_seq)
                if (dxv, dyv) != (0, 0) and (dxv, dyv) != (dxp, dyp):
                    break
            else:
                dxv, dyv = (dxp + 1, dyp if dyp != 0 else 1)
            back_dx = dxv - dxp
            back_dy = dyv - dyp
            seq_back_to_start = _vector_to_path(back_dx, back_dy, max_segments_per_axis=3)

            seq_to_speaker = _rand_steps_nonzero(len_min, len_max_adj, step_max)
            seq_to_current = _rand_steps_nonzero(len_min, len_max_adj, step_max)

            # 锚点与映射
            S0 = (0, 0)
            anchors, pos_to_item = _build_anchors(
                S0,
                seq_until_proj, seq_to_next1,
                seq_to_printer, seq_back_to_start,
                seq_to_speaker, seq_to_current,
                start_item, item_at_proj, item_next1,
                jump_item, item_printer, item_speaker, current_item
            )
            P = anchors['P']; N1 = anchors['N1']; T0 = anchors['T0']; PR = anchors['PR']; SPK = anchors['SPK']; CUR = anchors['CUR']

            # 额外规则文本与集合
            extra_rules: List[Dict[str, Any]] = []
            extra_lines: List[str] = []
            extra_lines.append('基础约定: RD=(x+=1), LD=(y+=1), LU=(x-=1), RU=(y-=1); 净位移为步向量和 (dx,dy); 曼哈顿距离 |dx|+|dy|; 奇偶性为 (x+y) 的奇偶。')
            extra_lines.append('术语定义: 看到X的位置 指首次看到X的坐标; 瞬移起点 指瞬移后首次看到物品的坐标。')
            extra_lines.append('记法: 步序列以 方向+步长 表示, 例如 RD3 表示向 RD 方向走 3 步。')
            extra_lines.append('输出约定: 若某坐标未被题干明确标注某物品, 则该坐标视为未知, 回答时请输出 unknown。')
            extra_lines.append('一物一地: 每个物品名只对应一个唯一坐标, 不会在不同坐标重复出现。')

            # 额外规则数量下限保护（至少 2 条）
            low = max(0, min(extras_min, extras_max))
            high = max(extras_min, extras_max)
            layer_bonus = 1 if layer_n >= 16 else 0
            extra_count = max(2, random.randint(low, min(high + layer_bonus, 6)))

            base_seqs = [
                ('seq_until_proj', seq_until_proj),
                ('seq_to_next1', seq_to_next1),
                ('seq_to_printer', seq_to_printer),
                ('seq_back_to_start', seq_back_to_start),
                ('seq_to_speaker', seq_to_speaker),
                ('seq_to_current', seq_to_current),
            ]
            remaining_items = [x for x in pool if x not in chosen]

            def _append_extra(from_key: str, seq: List[Tuple[str, int]], item: str, text_line: str, etype: str):
                start_pos = anchors[from_key]
                end_pos = _apply_steps(start_pos, seq)
                if end_pos == start_pos:
                    seq = [('RD', 1)]
                    end_pos = _apply_steps(start_pos, seq)
                _assign(pos_to_item, end_pos, item)
                extra_rules.append({'from': from_key, 'seq': seq, 'item': item, 'type': etype})
                extra_lines.append(text_line)

            items_for_label = {
                'item_at_proj': item_at_proj,
                'item_next1': item_next1,
                'item_printer': item_printer,
                'item_speaker': item_speaker,
            }

            # 生成额外规则：剔除 CUR 起点，避免显见线索
            anchor_keys_no_cur_for_from = [k for k in anchors.keys() if k != 'CUR']

            # 强制覆盖：至少包含 mirror 和 equal_vec
            must_types = ['mirror', 'equal_vec']
            plan_types = list(must_types)
            allowed_types_all = ['mirror', 'equal_vec', 'return_known']
            if extra_count > len(plan_types):
                for _ in range(extra_count - len(plan_types)):
                    # 限制 return_known 使用概率（最多约 1/3 次）
                    candidates = ['mirror', 'equal_vec'] + (['return_known'] if random.random() < 0.33 else [])
                    plan_types.append(random.choice(candidates))

            random.shuffle(plan_types)
            for rule_type in plan_types:
                from_key = random.choice(anchor_keys_no_cur_for_from)
                base_name, base_seq = random.choice(base_seqs)
                from_label = _anchor_label(from_key, items_for_label)

                if rule_type == 'mirror':
                    seq_m = _mirror_steps(base_seq)
                    if len(remaining_items) > 0:
                        item_extra = remaining_items.pop(0)
                        text = f'此外, 从 {from_label} 沿 {pretty_steps(seq_m)} 来到并看到 {item_extra}。'
                        _append_extra(from_key, seq_m, item_extra, text, 'mirror')
                    else:
                        candidate_targets = [k for k in anchors.keys() if k != from_key]
                        target_key = random.choice(candidate_targets)
                        dxe = anchors[target_key][0] - anchors[from_key][0]
                        dye = anchors[target_key][1] - anchors[from_key][1]
                        seq_e = _vector_to_path(dxe, dye, 3)
                        tgt_item = pos_to_item[anchors[target_key]]
                        text = f'此外, 从 {from_label} 沿 {pretty_steps(seq_e)} 来到并看到 {tgt_item}。'
                        _append_extra(from_key, seq_e, tgt_item, text, 'mirror')

                elif rule_type == 'equal_vec':
                    dx, dy = _net_vec(base_seq)
                    if random.random() < 0.5:
                        dx, dy = -dx, -dy
                    seq_e = _vector_to_path(dx, dy, 3)
                    if len(remaining_items) == 0:
                        candidate_targets = [k for k in anchors.keys() if k != from_key and k not in ['T0']]
                        target_key = random.choice(candidate_targets)
                        dxe = anchors[target_key][0] - anchors[from_key][0]
                        dye = anchors[target_key][1] - anchors[from_key][1]
                        seq_e = _vector_to_path(dxe, dye, 3)
                        tgt_item = pos_to_item[anchors[target_key]]
                        text = f'此外, 从 {from_label} 沿 {pretty_steps(seq_e)} 来到并看到 {tgt_item}。'
                        _append_extra(from_key, seq_e, tgt_item, text, 'equal_vec')
                    else:
                        item_extra = remaining_items.pop(0)
                        text = f'此外, 从 {from_label} 沿 {pretty_steps(seq_e)} 来到并看到 {item_extra}。'
                        _append_extra(from_key, seq_e, item_extra, text, 'equal_vec')

                else:  # return_known
                    candidate_targets = [k for k in anchors.keys() if k != from_key and k not in ['T0', 'CUR']]
                    if not candidate_targets:
                        continue
                    target_key = random.choice(candidate_targets)
                    dxr = anchors[target_key][0] - anchors[from_key][0]
                    dyr = anchors[target_key][1] - anchors[from_key][1]
                    seq_r = _vector_to_path(dxr, dyr, 3)
                    tgt_item = pos_to_item[anchors[target_key]]
                    text = f'此外, 从 {from_label} 沿 {pretty_steps(seq_r)} 来到并看到 {tgt_item}。'
                    _append_extra(from_key, seq_r, tgt_item, text, 'return_known')

            # 隐式约束：曼哈顿距离相等（不含 CUR，锚点不同）
            anchor_keys = list(anchors.keys())
            anchor_keys_no_cur = [k for k in anchor_keys if k != 'CUR']
            pairs = []
            for i in range(len(anchor_keys_no_cur)):
                for j in range(i + 1, len(anchor_keys_no_cur)):
                    a1 = anchor_keys_no_cur[i]; a2 = anchor_keys_no_cur[j]
                    if anchors[a1] != anchors[a2] and _manhattan(CUR, anchors[a1]) == _manhattan(CUR, anchors[a2]):
                        pairs.append((a1, a2))
            if len(pairs) > 0:
                mp = random.choice(pairs)
                a1_lab = _anchor_label(mp[0], items_for_label)
                a2_lab = _anchor_label(mp[1], items_for_label)
                extra_lines.append(f'补充约束: 以曼哈顿距离定义为 |dx|+|dy|, 当前所在点到 {a1_lab} 与到 {a2_lab} 的曼哈顿距离相等。')
                manhattan_pair = mp
            else:
                manhattan_pair = None

            # 隐式约束：奇偶性关系（参照锚点不为 CUR）
            pk_pool = [k for k in anchor_keys if k != 'CUR']
            pk = random.choice(pk_pool)
            parity_actual_same = (_parity(CUR) == _parity(anchors[pk]))
            pk_lab = _anchor_label(pk, items_for_label)
            extra_lines.append(f'补充约束: 以奇偶性定义为 (x+y) 的奇偶, 当前所在点与 {pk_lab} 的奇偶性{"相同" if parity_actual_same else "不同"}。')

            # 计算从 CUR 出发的额外规则终点（理论上不会存在，但生成端避让查询路径）
            endpoints_from_cur = []
            for ex in extra_rules:
                if ex['from'] == 'CUR':
                    endpoints_from_cur.append(_apply_steps(CUR, ex['seq']))

            # 选择查询路径（放在额外规则之后；避免与 endpoints_from_cur 重合）
            known_positions = [S0, P, N1, T0, PR, SPK, CUR]

            def _gen_query_path_avoiding_conflicts() -> List[Tuple[str, int]]:
                if want_known_answer and random.random() < 0.6:
                    candidates = [pos for pos in known_positions if pos not in endpoints_from_cur]
                    if candidates:
                        target = random.choice(candidates)
                        dxq = target[0] - CUR[0]
                        dyq = target[1] - CUR[1]
                        return _vector_to_path(dxq, dyq, max_segments_per_axis=3)
                for _ in range(100):
                    qp = _rand_steps_nonzero(len_min + 1, len_max_adj + 2, step_max)
                    endp = _apply_steps(CUR, qp)
                    if endp not in endpoints_from_cur:
                        return qp
                return [('RD', 1)]

            query_path = _gen_query_path_avoiding_conflicts()

            # 边界检查（所有锚点、额外规则终点与 QEND）
            all_points = [S0, P, N1, T0, PR, SPK, CUR]
            QEND = _apply_steps(CUR, query_path)
            all_points.append(QEND)
            for ex in extra_rules:
                st = anchors[ex['from']]
                ed = _apply_steps(st, ex['seq'])
                all_points.append(ed)
            max_abs = max(max(abs(px), abs(py)) for (px, py) in all_points)
            if max_abs > coord_bound:
                continue

            extra_text = ''
            if len(extra_lines) > 0:
                extra_text = '\\n' + '\\n'.join(extra_lines)

            used_items = chosen + [ex['item'] for ex in extra_rules if ex['item'] not in chosen]
            extra_types_ok = ('mirror' in {ex['type'] for ex in extra_rules}) and ('equal_vec' in {ex['type'] for ex in extra_rules})
            story = {
                'start_item': start_item,
                'seq_until_proj': seq_until_proj,
                'item_at_proj': item_at_proj,
                'seq_to_next1': seq_to_next1,
                'item_next1': item_next1,
                'jump_item': jump_item,
                'seq_to_printer': seq_to_printer,
                'item_printer': item_printer,
                'seq_back_to_start': seq_back_to_start,
                'seq_to_speaker': seq_to_speaker,
                'item_speaker': item_speaker,
                'seq_to_current': seq_to_current,
                'current_item': current_item,
                'query_path': query_path,
                'extras': extra_rules,
                'extra_text': extra_text,
                'meta_constraints': {
                    'manhattan_pair': manhattan_pair,
                    'parity_anchor': pk,
                    'parity_same': parity_actual_same,
                },
                'ok': True,
                'used_items': used_items,
                'extra_types_ok': extra_types_ok
            }

            ans = diamond_item_solver(story)
            if not isinstance(ans, str):
                continue
            if not (ans == 'unknown' or ans in story['used_items']):
                continue

            uniq_ok = verify_uniqueness(story, coord_bound, timeout_sec=170.0)
            if not uniq_ok:
                continue
            story['unique_ok'] = True

            return story
        except Exception:
            continue

    # 兜底方案：保证至少两条额外规则（mirror + equal_vec），避免显见线索
    fallback_extras_text_lines = [
        '基础约定: RD=(x+=1), LD=(y+=1), LU=(x-=1), RU=(y-=1); 净位移为步向量和 (dx,dy); 曼哈顿距离 |dx|+|dy|; 奇偶性为 (x+y) 的奇偶。',
        '术语定义: 看到X的位置 指首次看到X的坐标; 瞬移起点 指瞬移后首次看到物品的坐标。',
        '记法: 步序列以 方向+步长 表示, 例如 RD3 表示向 RD 方向走 3 步。',
        '输出约定: 若某坐标未被题干明确标注某物品, 则该坐标视为未知, 回答时请输出 unknown。',
        '一物一地: 每个物品名只对应一个唯一坐标, 不会在不同坐标重复出现。'
    ]
    fallback = {
        'start_item': '打孔器',
        'seq_until_proj': [('LD', 1)],
        'item_at_proj': '投影仪',
        'seq_to_next1': [('RD', 2)],
        'item_next1': '椅子',
        'jump_item': '文件夹',
        'seq_to_printer': [('RD', 2)],
        'seq_back_to_start': [('LU', 1), ('LD', 1)],
        'item_printer': '打印机',
        'seq_to_speaker': [('RD', 1)],
        'item_speaker': '智能音箱',
        'seq_to_current': [('LD', 1)],
        'current_item': '吊兰',
        'query_path': [('RD', 1)],
        'extras': [],
        'extra_text': '\\n' + '\\n'.join(fallback_extras_text_lines),
        'meta_constraints': {
            'manhattan_pair': None,
            'parity_anchor': 'S0',
            'parity_same': True
        },
        'used_items': ['打孔器', '投影仪', '椅子', '文件夹', '打印机', '智能音箱', '吊兰']
    }
    try:
        # 构造强制规则覆盖的两条 extras
        S0 = (0, 0)
        anchors_fb, pos_to_item_fb = _build_anchors(
            S0,
            fallback['seq_until_proj'], fallback['seq_to_next1'],
            fallback['seq_to_printer'], fallback['seq_back_to_start'],
            fallback['seq_to_speaker'], fallback['seq_to_current'],
            fallback['start_item'], fallback['item_at_proj'], fallback['item_next1'],
            fallback['jump_item'], fallback['item_printer'], fallback['item_speaker'], fallback['current_item']
        )
        items_for_label_fb = {
            'item_at_proj': fallback['item_at_proj'],
            'item_next1': fallback['item_next1'],
            'item_printer': fallback['item_printer'],
            'item_speaker': fallback['item_speaker'],
        }
        # mirror: 从看到投影仪的位置沿 seq_until_proj 的镜像
        seq_m = _mirror_steps(fallback['seq_until_proj'])
        from_key_m = 'P'
        from_label_m = _anchor_label(from_key_m, items_for_label_fb)
        item_m = '台灯'
        end_m = _apply_steps(anchors_fb[from_key_m], seq_m)
        _assign(pos_to_item_fb, end_m, item_m)
        txt_m = f'此外, 从 {from_label_m} 沿 {pretty_steps(seq_m)} 来到并看到 {item_m}。'

        # equal_vec: 从起点沿与 seq_to_current 等位移路径（或反向）
        dx_ec, dy_ec = _net_vec(fallback['seq_to_current'])
        if random.random() < 0.5:
            dx_ec, dy_ec = -dx_ec, -dy_ec
        seq_ec = _vector_to_path(dx_ec, dy_ec, 3)
        from_key_ec = 'S0'
        from_label_ec = _anchor_label(from_key_ec, items_for_label_fb)
        item_ec = '雨伞'
        end_ec = _apply_steps(anchors_fb[from_key_ec], seq_ec)
        _assign(pos_to_item_fb, end_ec, item_ec)
        txt_ec = f'此外, 从 {from_label_ec} 沿 {pretty_steps(seq_ec)} 来到并看到 {item_ec}。'

        fallback['extras'] = [
            {'from': from_key_m, 'seq': seq_m, 'item': item_m, 'type': 'mirror'},
            {'from': from_key_ec, 'seq': seq_ec, 'item': item_ec, 'type': 'equal_vec'},
        ]
        fallback['extra_text'] = '\\n' + '\\n'.join(fallback_extras_text_lines + [txt_m, txt_ec])
        # 更新 used_items
        for it in [item_m, item_ec]:
            if it not in fallback['used_items']:
                fallback['used_items'].append(it)

        _ = diamond_item_solver(fallback)
        ok_flag = True
        uniq_flag = verify_uniqueness(fallback, coord_bound, timeout_sec=5.0)
    except Exception:
        ok_flag = False
        uniq_flag = False
    fallback['ok'] = ok_flag
    fallback['unique_ok'] = uniq_flag
    fallback['extra_types_ok'] = ('mirror' in {ex.get('type') for ex in fallback.get('extras', [])}) and ('equal_vec' in {ex.get('type') for ex in fallback.get('extras', [])})
    return fallback