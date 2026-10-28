# Filename: dyck_language_7.py
from typing import Dict, Tuple, List
import random

# =========================
# 基础括号对全集
# =========================
BASE_PAIRS: List[Tuple[str, str]] = [('(', ')'), ('[', ']'), ('{', '}'), ('<', '>')]

def choose_bracket_pairs(k: int) -> Dict[str, str]:
    """
    随机选择 k 种不同括号对，返回映射 open->close。
    注意：BASE_PAIRS 中各右括号字符天然两两不同，满足题面约束。
    """
    if k < 1 or k > len(BASE_PAIRS):
        k = max(1, min(k, len(BASE_PAIRS)))
    pairs = random.sample(BASE_PAIRS, k)
    return {o: c for o, c in pairs}

def choose_cost_mode() -> str:
    """
    右括号基础成本分布模式：
      - 'uniform'：均匀分布
      - 'biased_low'：偏低
      - 'biased_high'：偏高
      - 'clustered'：双中心聚类
    """
    return random.choice(['uniform', 'biased_low', 'biased_high', 'clustered'])

def sample_cost_map(open_to_close: Dict[str, str], low: int, high: int, mode: str) -> Dict[str, int]:
    """
    为每种右括号在 [low, high] 抽样一个正整数为基础成本，确保在类型数>1时至少有两种不同值。
    """
    closes = list(open_to_close.values())
    if low > high:
        low, high = high, low
    low = max(low, 1)

    def clamp(x: int) -> int:
        return max(low, min(x, high))

    cost_map: Dict[str, int] = {}

    def sample_uniform() -> int:
        return random.randint(low, high)

    def sample_biased_low() -> int:
        if random.random() < 0.75:
            return clamp(low + random.randint(0, max(1, (high - low) // 3)))
        return clamp(random.randint(low, high))

    def sample_biased_high() -> int:
        if random.random() < 0.75:
            return clamp(high - random.randint(0, max(1, (high - low) // 3)))
        return clamp(random.randint(low, high))

    def sample_clustered(c1: int, c2: int) -> int:
        center = c1 if random.random() < 0.5 else c2
        noise = random.randint(-2, 2)
        return clamp(center + noise)

    c1 = clamp(low + random.randint(0, max(1, (high - low) // 2)))
    c2 = clamp(high - random.randint(0, max(1, (high - low) // 2)))

    for _ in range(20):
        cost_map.clear()
        for rc in closes:
            if mode == 'uniform':
                cost_map[rc] = sample_uniform()
            elif mode == 'biased_low':
                cost_map[rc] = sample_biased_low()
            elif mode == 'biased_high':
                cost_map[rc] = sample_biased_high()
            else:
                cost_map[rc] = sample_clustered(c1, c2)
        if len(closes) == 1 or len(set(cost_map.values())) >= 2:
            break

    return cost_map

def format_cost_desc(costs: Dict[str, int]) -> str:
    """
    将右括号基础成本格式化为中文描述，如 ')=3， ]=1， }=2'。
    """
    order = [')', ']', '}', '>']
    parts = []
    for ch in order:
        if ch in costs:
            parts.append(f"{ch}={costs[ch]}")
    for ch in costs:
        if ch not in order:
            parts.append(f"{ch}={costs[ch]}")
    return '， '.join(parts)

def format_pairs_desc(open_to_close: Dict[str, str]) -> str:
    """
    将允许的括号对格式化为 '(), [], {}, <>' 仅输出存在的那几种。
    """
    order = [('(', ')'), ('[', ']'), ('{', '}'), ('<', '>')]
    parts = []
    for o, c in order:
        if o in open_to_close and open_to_close[o] == c:
            parts.append(f"{o}{c}")
    for o, c in open_to_close.items():
        if (o, c) not in order:
            parts.append(f"{o}{c}")
    return '， '.join(parts)

def choose_prefix_strategy() -> str:
    """
    前缀生成策略：
      - 'stack_heavy': 偏向生成开括号，残余栈更长
      - 'mismatch_heavy': 偏向制造非栈顶匹配
      - 'balanced': 大致均衡
    """
    return random.choice(['stack_heavy', 'mismatch_heavy', 'balanced'])

def generate_prefix(open_to_close: Dict[str, str],
                    min_len: int,
                    max_len: int,
                    require_mismatch: bool,
                    strategy: str) -> str:
    """
    生成可通过仅插入右括号补全为平衡序列的前缀。
    若 require_mismatch 为 True，则保证在扫描过程中至少发生一次“非栈顶匹配”场景；
    若自然生成未满足且栈深不足，则追加必要字符制造一次该场景（可能使长度略超出 max_len）。
    """
    if min_len > max_len:
        min_len, max_len = max_len, min_len

    n = random.randint(max(6, min_len), max(max_len, 6))
    opens = list(open_to_close.keys())
    gen_stack: List[str] = []
    prefix_chars: List[str] = []
    made_mismatch = False

    if strategy == 'stack_heavy':
        p_open = 0.75
        p_non_top = 0.35
    elif strategy == 'mismatch_heavy':
        p_open = 0.55
        p_non_top = 0.70
    else:
        p_open = 0.60
        p_non_top = 0.50

    for _ in range(n):
        if not gen_stack or random.random() < p_open:
            ch_open = random.choice(opens)
            gen_stack.append(ch_open)
            prefix_chars.append(ch_open)
        else:
            if len(gen_stack) == 1 or random.random() > p_non_top:
                j = len(gen_stack) - 1
            else:
                j = random.randrange(0, len(gen_stack) - 1)
            target_open = gen_stack[j]
            close_char = open_to_close[target_open]
            prefix_chars.append(close_char)
            if j != len(gen_stack) - 1:
                made_mismatch = True
            while len(gen_stack) > j + 1:
                gen_stack.pop()
            gen_stack.pop()

    # 兜底制造一次非栈顶匹配
    if require_mismatch and not made_mismatch:
        if len(gen_stack) >= 2:
            j = random.randrange(0, len(gen_stack) - 1)
            target_open = gen_stack[j]
            close_char = open_to_close[target_open]
            prefix_chars.append(close_char)
            while len(gen_stack) > j + 1:
                gen_stack.pop()
            gen_stack.pop()
            made_mismatch = True
        else:
            # 栈深不足：人为构造一次非栈顶匹配（需要至少两种括号类型）
            if len(opens) >= 2:
                o1, o2 = random.sample(opens, 2)
            else:
                o1 = o2 = opens[0]
            gen_stack.append(o1)
            prefix_chars.append(o1)
            gen_stack.append(o2)
            prefix_chars.append(o2)
            close_char = open_to_close[o1]
            prefix_chars.append(close_char)
            while gen_stack and gen_stack[-1] != o1:
                gen_stack.pop()
            if gen_stack and gen_stack[-1] == o1:
                gen_stack.pop()
            made_mismatch = True

    return ''.join(prefix_chars)

def get_prefix_len(prefix: str) -> int:
    return len(prefix)

# =========================
# 深度加价模块
# =========================
def choose_depth_cost_mode() -> str:
    """
    深度加价模式：
      - 'flat'：各深度相同
      - 'increasing'：随深度递增
      - 'decreasing'：随深度递减
      - 'two_step'：前半段低、后半段高
    """
    return random.choice(['flat', 'increasing', 'decreasing', 'two_step'])

def sample_depth_costs(depth_levels: int, low: int, high: int, mode: str) -> Dict[int, int]:
    """
    为 1..depth_levels 每一层生成一个加价，范围在 [low, high]。
    若 depth_levels<1，强制为 1。
    """
    d = max(1, depth_levels)
    if low > high:
        low, high = high, low
    low = max(0, low)

    def clamp(x: int) -> int:
        return max(low, min(x, high))

    costs: Dict[int, int] = {}

    if mode == 'flat':
        v = random.randint(low, high)
        for dep in range(1, d + 1):
            costs[dep] = v
    elif mode == 'increasing':
        base = random.randint(low, high)
        step = max(1, (high - low) // max(1, d - 1)) if high > base else 1
        for dep in range(1, d + 1):
            costs[dep] = clamp(base + (dep - 1) * step)
    elif mode == 'decreasing':
        base = random.randint(low, high)
        step = max(1, (high - low) // max(1, d - 1)) if base > low else 1
        for dep in range(1, d + 1):
            costs[dep] = clamp(base - (dep - 1) * step)
    else:
        mid = (d + 1) // 2
        low_pick = random.randint(low, high)
        high_pick = random.randint(low, high)
        if low_pick > high_pick:
            low_pick, high_pick = high_pick, low_pick
        for dep in range(1, d + 1):
            costs[dep] = low_pick if dep <= mid else high_pick

    return costs

def format_depth_cost_desc(depth_costs: Dict[int, int]) -> str:
    """
    将深度加价映射格式化为中文描述，例如 '深度1:+0， 深度2:+1， 深度3:+2'。
    """
    parts = []
    for dep in sorted(depth_costs.keys()):
        parts.append(f"深度{dep}:+{depth_costs[dep]}")
    return '， '.join(parts)

# =========================
# 复杂成本下的最优补全与校验
# =========================
def compute_min_cost_lex(prefix: str,
                         open_to_close: Dict[str, str],
                         base_costs: Dict[str, int],
                         depth_costs: Dict[int, int],
                         mismatch_surcharge: int,
                         switch_penalty: int) -> Tuple[int, str]:
    """
    计算仅插入右括号的最小总成本补全过程，并返回 (最小总成本, 完整平衡序列)。
    成本由四部分组成：
      1) 基础右括号成本 base_costs
      2) 深度加价 depth_costs，按插入当刻的栈深计算，超出最大深度按最后一层取值
      3) 非栈顶匹配加价 mismatch_surcharge：当处理前缀右括号时，需清空到目标开括号之上的每次插入
      4) 切换加价 switch_penalty：连续两次插入的右括号字符不同则加价
    约定：
      - 前缀自带字符零成本
      - 切换加价仅在两次“插入”之间计算，前缀字符不参与切换判定
      - 任何一次插入必须匹配当时的栈顶开括号以保持序列合法
      - 末尾为使序列平衡而关闭残余开括号不属于非栈顶匹配场景（不加 mismatch_surcharge），但切换加价仍适用
    """
    close_to_open: Dict[str, str] = {v: k for k, v in open_to_close.items()}
    stack: List[str] = []
    output: List[str] = []
    total_cost = 0
    last_inserted: str = ''  # 跟踪上一个插入的右括号字符

    def depth_surcharge(current_depth: int) -> int:
        if not depth_costs:
            return 0
        if current_depth <= 0:
            return 0
        mx = max(depth_costs.keys())
        dep = current_depth if current_depth in depth_costs else mx
        if current_depth > mx:
            dep = mx
        return depth_costs.get(dep, 0)

    for ch in prefix:
        if ch in open_to_close:
            stack.append(ch)
            output.append(ch)
        elif ch in close_to_open:
            target_open = close_to_open[ch]
            # 插入右括号以清空到目标开括号之上（弹出其上所有开括号）
            while stack and stack[-1] != target_open:
                to_close_open = stack.pop()
                to_close_right = open_to_close[to_close_open]
                output.append(to_close_right)
                # 成本叠加
                current_depth = len(stack) + 1  # 插入前的深度
                c = base_costs.get(to_close_right, 0)
                c += depth_surcharge(current_depth)
                c += mismatch_surcharge
                if last_inserted and last_inserted != to_close_right:
                    c += switch_penalty
                total_cost += c
                last_inserted = to_close_right
            if stack and stack[-1] == target_open:
                stack.pop()
                output.append(ch)  # 原前缀右括号自身无成本
                # 前缀字符不是插入，不更新 last_inserted
            else:
                # 理论上不会发生：空栈遇到前缀右括号
                return (0, prefix)
        else:
            # 非括号字符：题面不生成此类，不过做鲁棒处理
            output.append(ch)

    # 关闭末尾残余开括号
    while stack:
        to_close_open = stack.pop()
        to_close_right = open_to_close[to_close_open]
        output.append(to_close_right)
        current_depth = len(stack) + 1
        c = base_costs.get(to_close_right, 0)
        c += depth_surcharge(current_depth)
        # 末尾关闭不属于非栈顶匹配场景，不加 mismatch_surcharge
        if last_inserted and last_inserted != to_close_right:
            c += switch_penalty
        total_cost += c
        last_inserted = to_close_right

    return (total_cost, ''.join(output))

def _is_balanced(sequence: str, open_to_close: Dict[str, str]) -> bool:
    """
    校验序列在给定括号对下是否平衡。
    """
    close_to_open: Dict[str, str] = {v: k for k, v in open_to_close.items()}
    st: List[str] = []
    for ch in sequence:
        if ch in open_to_close:
            st.append(ch)
        elif ch in close_to_open:
            if not st or st[-1] != close_to_open[ch]:
                return False
            st.pop()
        else:
            return False
    return len(st) == 0

def _forced_path_unique(prefix: str, open_to_close: Dict[str, str]) -> bool:
    """
    在仅允许插入右括号并保持括号合法的规则下，补全路径由栈约束决定。
    唯一性判定：
      1) open_to_close 的值域（各右括号）两两不重复；
      2) 每次合法插入只能是“当前栈顶开括号对应的右括号”，不存在其他合法可选项。
    """
    # 1) 检查右括号唯一性（避免不同开括号映射到相同右括号导致歧义）
    closes = list(open_to_close.values())
    if len(set(closes)) != len(closes):
        return False

    close_to_open: Dict[str, str] = {v: k for k, v in open_to_close.items()}
    st: List[str] = []

    for ch in prefix:
        if ch in open_to_close:
            st.append(ch)
        elif ch in close_to_open:
            target_open = close_to_open[ch]
            # 需要插入以清空到目标开括号之上的所有开括号
            while st and st[-1] != target_open:
                top_open = st[-1]
                unique_insert = open_to_close[top_open]
                # 合法插入集合只能是 {unique_insert}
                legal = {unique_insert}
                if len(legal) != 1:
                    return False
                st.pop()
            if st and st[-1] == target_open:
                st.pop()
            else:
                # 异常前缀
                return False
        else:
            # 非括号字符不考虑（题面不会生成）
            return False

    # 末尾关闭过程同样只有唯一合法插入（当前栈顶对应右括号）
    while st:
        top_open = st[-1]
        unique_insert = open_to_close[top_open]
        if not unique_insert:
            return False
        st.pop()

    return True

def verify_answer(prefix: str,
                  open_to_close: Dict[str, str],
                  base_costs: Dict[str, int],
                  depth_costs: Dict[int, int],
                  mismatch_surcharge: int,
                  switch_penalty: int,
                  cost: int,
                  completion: str) -> bool:
    """
    严格校验模块：
      1) 重算参考答案并比对
      2) 校验完成串为平衡序列
      3) 结构性唯一路径判定（每步插入仅有唯一合法右括号，且右括号字符两两不同）
    """
    ref_cost, ref_completion = compute_min_cost_lex(prefix, open_to_close, base_costs,
                                                    depth_costs, mismatch_surcharge, switch_penalty)
    if cost != ref_cost or completion != ref_completion:
        return False
    if not _is_balanced(completion, open_to_close):
        return False
    if not _forced_path_unique(prefix, open_to_close):
        return False
    return True