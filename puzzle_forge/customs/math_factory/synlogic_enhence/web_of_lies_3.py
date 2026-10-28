# file: web_of_lies_8.py
import random

def build_answer(focus_list, true_count):
    """
    兼容旧版：构造答案字典（已排序）
    - focus_list: [(name:str, truth:bool), ...]
    - true_count: int
    """
    focus_sorted = sorted(focus_list, key=lambda t: t[0])
    return {"focus": focus_sorted, "true_count": true_count}

def build_answer_focus_and_lead(focus_list, lead_truth):
    """
    新版：构造答案字典（已排序）
    - focus_list: [(name:str, truth:bool), ...] 关注房间的两名成员及其真假
    - lead_truth: bool lead 的陈述真假
    """
    focus_sorted = sorted(focus_list, key=lambda t: t[0])
    return {"focus": focus_sorted, "lead_truth": bool(lead_truth)}

def choose_indices(n, k):
    """
    从 range(n) 中选取 k 个互不相同的索引
    """
    if k > n:
        raise ValueError("k cannot be greater than n")
    return random.sample(range(n), k)

def choose_distinct_from(n, k, exclude_list):
    """
    从 range(n) 中选取 k 个不在 exclude_list 中的互不相同的索引
    """
    pool = [i for i in range(n) if i not in set(exclude_list)]
    if k > len(pool):
        raise ValueError("Not enough candidates to choose from")
    return random.sample(pool, k)

def gen_room_labels(n):
    """
    生成 n 个不重复的房间标签
    """
    pool = ["Chem", "Phys", "Server", "Bio", "EE", "AI", "DataLab", "Optics", "Nano", "Mech"]
    random.shuffle(pool)
    return pool[:n]

def exclude_by_indices(lst, idx_list):
    """
    从列表lst中排除索引位于idx_list的元素，返回新列表
    """
    idx_set = set(idx_list)
    return [lst[i] for i in range(len(lst)) if i not in idx_set]

def render_ring_desc(rooms):
    """
    描述环状与“下一间/上一间”的参照规则
    """
    chain = " -> ".join(rooms)
    return f"房间按所给顺序构成环（{chain} -> {rooms[0]}），“下一间/上一间”均以说话者自己所处的房间为参照"

def render_chain_desc(speaker, mode_code, rooms):
    """
    渲染链式陈述文本（保留以兼容，但当前未直接使用）
    """
    if mode_code == 1:
        claim = "相对于说话者所在房间的下一间中恰有一人说真话"
    else:
        claim = "相对于说话者所在房间的下一间中两人真假相同"
    return f"{speaker} 说“{claim}”。"

def render_personal_desc(speaker, tmpl_code, a_name, b_name, claim_room, orient, lead_name):
    """
    渲染个人陈述文本，支持多个模板：
    - tmpl_code:
        0: '{lead_name} 在 {claim_room} 且 {lead_name} 正在说谎'
        1: 链式（相对于说话者所在房间的下一间）：
           orient=True -> 恰有一人说真话；False -> 两人真假相同
        2: '{a_name} 与 {b_name} 同处一室'
    """
    if tmpl_code == 0:
        return f"{speaker} 说“{lead_name} 在 {claim_room} 且 {lead_name} 正在说谎”。"
    elif tmpl_code == 1:
        claim = "相对于说话者所在房间的下一间中恰有一人说真话" if orient else "相对于说话者所在房间的下一间中两人真假相同"
        return f"{speaker} 说“{claim}”。"
    else:
        return f"{speaker} 说“{a_name} 与 {b_name} 同处一室”。"

def count_true(truth_list):
    """
    统计布尔列表中 True 的个数
    - truth_list: List[bool-like]
    """
    return sum(1 for v in truth_list if bool(v))

def render_balance_desc(rooms, balance_indices):
    """
    描述被选中需“恰有一人说真话”的房间集合
    """
    labels = [rooms[i] for i in balance_indices]
    return "以下房间中恰有一人说真话：" + "; ".join(labels)

def render_contrast_desc(room_a, room_b):
    """
    描述两间房间真话人数不同的对比规则
    """
    return f"房间 {room_a} 与房间 {room_b} 中说真话的人数不同"

def render_lead_rule_desc(lead_name):
    """
    描述 lead 的本地规则（其所在房间的上一间恰有一人说真话）
    """
    return f"{lead_name} 的陈述：其所在房间的上一间恰有一人说真话"

def render_observer_rule_desc(observer_name, focus_room, orient):
    """
    描述观察者关于关注房间的规则
    - orient: True => 关注房间恰有一人说真话；False => 关注房间两人真假相同
    """
    s = "恰有一人说真话" if orient else "两人真假相同"
    return f"{observer_name} 的陈述：关注房间 {focus_room} 中{s}"