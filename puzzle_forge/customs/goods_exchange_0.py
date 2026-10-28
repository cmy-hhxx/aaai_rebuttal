# goods_exchange_0.py
# 改进要点（与分析一致）：
# - 去除与求解无关的“规模/函数复合/分组”等冗余信息，聚焦初始分配与交换步骤；
# - 明确题面规则与统一交换表述，仅生成“交换/互换”的动作；
# - 保持正向生成策略：随机实体 -> 生成交换序列（仅交换） -> 顺序模拟 -> 唯一答案；
# - 保证最终状态为严格双射映射（唯一性）。

import random
from typing import List, Tuple, Dict, Any

# ------------------ 基础工具 ------------------
def _assert_bijection(pairs: List[Tuple[str, str]]):
    """检查(name,item)列表是否为严格一一对应的双射。"""
    persons = [p for p, _ in pairs]
    items = [it for _, it in pairs]
    if len(pairs) != len(set(persons)) or len(pairs) != len(set(items)):
        raise ValueError("最终状态不是一一对应的双射映射。")

def _pairs_to_dict(pairs: List[Tuple[str, str]]) -> Dict[str, str]:
    """将(name,item)列表转换为映射字典。"""
    d = {}
    for n, it in pairs:
        if n in d:
            raise ValueError(f"重复的玩家姓名: {n}")
        d[n] = it
    return d

def _dict_to_pairs(inv: Dict[str, str], order: List[str]) -> List[Tuple[str, str]]:
    """按照指定顺序提取(name,item)对。"""
    return [(n, inv[n]) for n in order]

def _find_holder(inv: Dict[str, str], item: str) -> str:
    """根据物品查找当前持有者（姓名）。"""
    for n, it in inv.items():
        if it == item:
            return n
    raise ValueError(f"未找到物品的持有者: {item}")

# ------------------ 语言选择（避免type=str） ------------------
def choose_locale() -> str:
    """随机返回语言环境：zh_CN 或 en_US。"""
    return random.choice(['zh_CN', 'en_US'])

# ------------------ 生成人名与物品 ------------------
ITEM_TYPES = [
    "钱包","电脑","明信片","耳机","戒指","眼镜","手绢","发夹","地图","纪念币","水壶","项链","小刀","口哨","手环","钥匙扣","手表"
]

def gen_names(n: int, locale: str = 'zh_CN') -> List[str]:
    """
    生成n个唯一人名。优先尝试Faker；若不可用或唯一性不足，则回退至编号。
    """
    try:
        from faker import Faker
        faker = Faker(locale)
        names = set()
        for _ in range(n * 5):
            # 使用unique.name确保唯一性
            names.add(faker.unique.name())
            if len(names) >= n:
                break
        if len(names) < n:
            raise RuntimeError("Faker未能生成足够唯一的人名，回退至编号。")
        res = list(names)
        random.shuffle(res)
        return res
    except Exception:
        return [f"P{i+1}" for i in range(n)]

def gen_items(n: int) -> List[str]:
    """
    生成n个唯一的物品名称，形式为“颜色+类型”（确保充足的组合空间）。
    """
    colors = [
        "黑色","白色","灰色","银色","金色","红色","酒红色","玫红色","粉色","橙色","明黄色","黄色",
        "草绿色","浅绿色","墨绿色","深蓝色","浅蓝色","蓝色","青色","紫色","古铜色","米色","棕色","藏青色"
    ]
    combos = [f"{c}{o}" for c in colors for o in ITEM_TYPES]
    random.shuffle(combos)
    if len(combos) < n:
        raise ValueError("颜色与物品组合空间不足，无法生成足够唯一的物品。")
    res = combos[:n]
    random.shuffle(res)
    return res

# ------------------ 初始分配 ------------------
def allocate_initial_pairs(names: List[str], items: List[str]) -> List[Tuple[str, str]]:
    """
    随机打乱物品后与人名一一对应，形成初始分配（严格双射）。
    """
    if len(names) != len(items):
        raise ValueError("玩家数量与物品数量必须一致。")
    items_shuffled = items[:]
    random.shuffle(items_shuffled)
    pairs = list(zip(names, items_shuffled))
    _assert_bijection(pairs)
    return pairs

# ------------------ 构造交换序列（仅交换 + 统一句式） ------------------
def build_exchange_sequence(names: List[str],
                            items: List[str],
                            initial_pairs: List[Tuple[str, str]],
                            step_count: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    构造长度为step_count的合法交换步骤序列，以及对应的统一句式描述。
    交换类型：
      - swap_holders_by_items：持有A的玩家与持有B的玩家交换他们的物品
      - swap_between_persons：X与Y交换他们的物品（带当前物品校验）
      - swap_persons：X与Y交换他们的物品（直接交换）
    仅生成“交换/互换”的动作，不产生与求解无关的叙述。
    """
    if step_count < 1:
        raise ValueError("步骤数过少，无法构建题面。")

    inv = _pairs_to_dict(initial_pairs)
    steps: List[Dict[str, Any]] = []
    descriptions: List[str] = []

    def add_swap_holders_by_items():
        itA, itB = random.sample(items, 2)
        holderA = _find_holder(inv, itA)
        holderB = _find_holder(inv, itB)
        # 执行交换
        inv[holderA], inv[holderB] = inv[holderB], inv[holderA]
        # 记录步骤与统一句式描述
        steps.append({"type": "swap_holders_by_items", "itemA": itA, "itemB": itB})
        descriptions.append(f"持有{itA}的玩家与持有{itB}的玩家交换他们的物品")

    def add_swap_between_persons():
        p1, p2 = random.sample(names, 2)
        item1, item2 = inv[p1], inv[p2]
        # 执行交换
        inv[p1], inv[p2] = inv[p2], inv[p1]
        steps.append({"type": "swap_between_persons", "p1": p1, "item1": item1, "p2": p2, "item2": item2})
        descriptions.append(f"{p1}与{p2}交换他们的物品")

    def add_swap_persons():
        p1, p2 = random.sample(names, 2)
        # 执行交换
        inv[p1], inv[p2] = inv[p2], inv[p1]
        steps.append({"type": "swap_persons", "p1": p1, "p2": p2})
        descriptions.append(f"{p1}与{p2}交换他们的物品")

    # 至少保证若干交换以产生状态变化
    for _ in range(step_count):
        r = random.random()
        if r < 0.33:
            add_swap_holders_by_items()
        elif r < 0.66:
            add_swap_between_persons()
        else:
            add_swap_persons()

    # 构造结束时校验最终状态双射（inv为执行完后的映射，用于生成描述时的连贯性检验）
    _assert_bijection(_dict_to_pairs(inv, names))

    return steps, descriptions

# ------------------ 顺序模拟步骤（唯一答案） ------------------
def simulate_exchanges(names: List[str],
                       initial_pairs: List[Tuple[str, str]],
                       steps: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """
    顺序执行步骤，返回最终(name,item)列表（按names顺序）。
    支持操作类型：
      - 'swap_holders_by_items': {'itemA':..., 'itemB':...}
      - 'swap_between_persons': {'p1':..., 'item1':..., 'p2':..., 'item2':...}
      - 'swap_persons': {'p1':..., 'p2':...}
    """
    inv = _pairs_to_dict(initial_pairs)

    for i, step in enumerate(steps, 1):
        t = step.get('type')

        if t == 'swap_holders_by_items':
            itA = step['itemA']; itB = step['itemB']
            holderA = _find_holder(inv, itA)
            holderB = _find_holder(inv, itB)
            inv[holderA], inv[holderB] = inv[holderB], inv[holderA]

        elif t == 'swap_between_persons':
            p1 = step['p1']; p2 = step['p2']
            item1 = step['item1']; item2 = step['item2']
            # 校验当前物品一致性（确保题面叙述与执行一致）
            if inv[p1] != item1:
                raise ValueError(f"步骤{i}校验失败：{p1}当前不持有{item1}，实际为{inv[p1]}")
            if inv[p2] != item2:
                raise ValueError(f"步骤{i}校验失败：{p2}当前不持有{item2}，实际为{inv[p2]}")
            inv[p1], inv[p2] = inv[p2], inv[p1]

        elif t == 'swap_persons':
            p1 = step['p1']; p2 = step['p2']
            inv[p1], inv[p2] = inv[p2], inv[p1]

        else:
            raise ValueError(f"未知的操作类型: {t}")

        # 运行时校验：合法玩家名
        for n in inv.keys():
            if n not in names:
                raise ValueError(f"出现未定义的玩家：{n}")

    final_pairs = _dict_to_pairs(inv, names)
    _assert_bijection(final_pairs)
    return final_pairs

# ------------------ 答案格式化 ------------------
def format_tuple_answer(final_pairs: List[Tuple[str, str]], names_order: List[str]) -> str:
    """
    将最终分配按names顺序格式化为题面要求的tuple字符串。
    """
    inv = {p: it for p, it in final_pairs}
    ordered = [(n, inv[n]) for n in names_order]
    inner = ",".join([f"('{n}','{it}')" for n, it in ordered])
    return f"({inner})"