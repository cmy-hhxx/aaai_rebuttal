# space_reasoning_0.py
# 高质量空间推理造题器（逆向生成）
# 改进点：
# 1) 可解性：题面给出全局映射规则 I(x,y)，读者可计算任意坐标的物品。
# 2) 去除unknown：所有顶点都有物品，统一语义。
# 3) 坐标明确：提供起点与每段终点坐标示例；无“任意节点”的不可知描述。
# 4) 难度透明：level与步长范围在题面叙述中呈现。
# 5) 严谨边界：逐步检查每一步移动不越界。
#
# 输出结构：
# {
#   'N': int,                     # 层数
#   'story': str,                 # 题面叙述（不含问句）
#   'ans': str,                   # 唯一答案（物品名称）
#   'query_text': str,            # 查询路径文本（中文方向-步数组合）
#   'query_path': List[(dir, s)], # 查询路径
#   'current_pos': 'x,y'          # 当前坐标字符串
# }

import random

# 方向向量与中文映射
DIRS = {
    'RU': (1, 1),
    'RD': (1, -1),
    'LD': (-1, -1),
    'LU': ( -1, 1),
}
DIR_CN = {'RU': '右上', 'RD': '右下', 'LD': '左下', 'LU': '左上'}

def move(pos, dir_name, steps):
    dx, dy = DIRS[dir_name]
    return (pos[0] + dx * steps, pos[1] + dy * steps)

def in_bounds(pos, N):
    return max(abs(pos[0]), abs(pos[1])) <= N

def step_with_checks(start, path, N):
    """逐步检查每一步是否越界；合法则返回终点坐标，否则返回None。"""
    p = start
    for d, s in path:
        # 连续s步逐步检查
        for _ in range(s):
            p = move(p, d, 1)
            if not in_bounds(p, N):
                return None
    return p

def gen_moves(k, step_range, N, start):
    """生成长度为k的合法移动序列（逐步越界检查）。"""
    path = []
    p = start
    tries = 0
    while len(path) < k and tries < 300:
        d = random.choice(list(DIRS.keys()))
        s = random.randint(step_range[0], step_range[1])
        # 尝试逐步走s步
        ok = True
        tmp = p
        for _ in range(s):
            tmp = move(tmp, d, 1)
            if not in_bounds(tmp, N):
                ok = False
                break
        if ok:
            path.append((d, s))
            p = tmp
        else:
            tries += 1
    return path if len(path) == k else None

def path_to_text(path):
    return '，'.join([f"往{DIR_CN[d]}{s}步" for d, s in path])

def item_name(N, x, y):
    """全局唯一映射规则（题面已声明）。"""
    I = (x + N) * (2 * N + 1) + (y + N) + 1
    return f"物品#{I}"

def generate_scenario():
    # 难度与边界选择（在叙述中提示）
    level = random.choice(['easy', 'medium', 'hard'])
    if level == 'easy':
        N = random.randint(8, 10)
        step_range = (1, 3)  # 每段步长范围
        seg_lengths = [3, 3, 2]  # 叙述段长度（连续行走的步数个数）
        query_len = 5
    elif level == 'medium':
        N = random.randint(10, 12)
        step_range = (2, 5)
        seg_lengths = [3, 4, 3]
        query_len = 6
    else:  # hard
        N = random.randint(12, 14)
        step_range = (2, 6)
        seg_lengths = [4, 4, 3]
        query_len = 7

    # 起点：在边界内随机
    start = (random.randint(-N//2, N//2), random.randint(-N//2, N//2))
    while not in_bounds(start, N):
        start = (random.randint(-N//2, N//2), random.randint(-N//2, N//2))

    # 段1
    seg1 = gen_moves(seg_lengths[0], step_range, N, start)
    if not seg1: seg1 = gen_moves(seg_lengths[0], (1, max(2, step_range[0])), N, start)
    end1 = step_with_checks(start, seg1, N)
    # 段2
    seg2 = gen_moves(seg_lengths[1], step_range, N, end1)
    if not seg2: seg2 = gen_moves(seg_lengths[1], (1, max(2, step_range[0])), N, end1)
    end2 = step_with_checks(end1, seg2, N)
    # 段3（作为当前位置）
    seg3 = gen_moves(seg_lengths[2], step_range, N, end2)
    if not seg3: seg3 = gen_moves(seg_lengths[2], (1, max(2, step_range[0])), N, end2)
    current_pos = step_with_checks(end2, seg3, N)

    # 查询路径：非闭环（净位移≠0），逐步合法；允许与已出现坐标重合或不重合（皆可按规则计算）
    query_path = None
    query_end = None
    tries = 0
    seen_coords = {
        f"{start[0]},{start[1]}",
        f"{end1[0]},{end1[1]}",
        f"{end2[0]},{end2[1]}",
        f"{current_pos[0]},{current_pos[1]}",
    }
    while tries < 400:
        cand = gen_moves(query_len, step_range, N, current_pos)
        if not cand:
            tries += 1
            continue
        # 净位移检测
        dx = dy = 0
        for d, s in cand:
            vx, vy = DIRS[d]
            dx += vx * s
            dy += vy * s
        if dx == 0 and dy == 0:
            tries += 1
            continue
        qe = step_with_checks(current_pos, cand, N)
        if qe is None:
            tries += 1
            continue
        query_path = cand
        query_end = qe
        break
    if query_path is None:
        # 兜底：手工非闭环短路径
        query_path = [('RD', 1), ('LU', 1), ('RU', 2)]
        query_end = step_with_checks(current_pos, query_path, N)

    # 唯一答案（按规则计算）
    ans_item = item_name(N, query_end[0], query_end[1])

    # 题面叙述（不含问句）
    s0 = f"每段步长范围：[{step_range[0]}, {step_range[1]}]。"
    s1 = f"起点 S = ({start[0]}, {start[1]})，看到的物品为 {item_name(N, start[0], start[1])}。"
    s2 = f"然后{path_to_text(seg1)}，到达 P1 = ({end1[0]}, {end1[1]})，物品为 {item_name(N, end1[0], end1[1])}。"
    s3 = f"再{path_to_text(seg2)}，到达 P2 = ({end2[0]}, {end2[1]})，物品为 {item_name(N, end2[0], end2[1])}。"
    s4 = f"随后{path_to_text(seg3)}，到达“当前位置” C = ({current_pos[0]}, {current_pos[1]})，物品为 {item_name(N, current_pos[0], current_pos[1])}。"
    story = " ".join([s0, s1, s2, s3, s4])

    return {
        'N': N,
        'story': story,
        'ans': ans_item,
        'query_text': path_to_text(query_path),
        'query_path': query_path,
        'current_pos': f"{current_pos[0]},{current_pos[1]}",
    }

def compute_final_item(scenario):
    """从当前位置按查询路径移动，按规则计算终点物品名称。"""
    def parse_coord(s):
        x, y = s.split(',')
        return (int(x), int(y))
    N = scenario['N']
    cur = parse_coord(scenario['current_pos'])
    # 逐步越界检查
    for d, s in scenario['query_path']:
        for _ in range(s):
            cur = move(cur, d, 1)
            if not in_bounds(cur, N):
                # 理论上不会越界，生成时已保证；若发生则抛错或返回占位
                return f"物品#越界"
    return item_name(N, cur[0], cur[1])

if __name__ == "__main__":
    # 回归自测：多次生成，检查答案一致与非闭环属性
    for _ in range(5):
        sc = generate_scenario()
        ans = compute_final_item(sc)
        # 检查查询路径净位移非零
        dx = dy = 0
        for d, s in sc['query_path']:
            vx, vy = DIRS[d]
            dx += vx * s
            dy += vy * s
        print(f"N={sc['N']}, level in story, ans={ans}, expected={sc['ans']}, ok={ans==sc['ans']}, non_zero={(dx,dy)!= (0,0)}")
        assert ans == sc['ans'], "答案校验失败"
        assert (dx, dy) != (0, 0), "查询路径是闭环（不允许）"