# web_of_lies_0.py
import random
from itertools import product

# ---------- 工具 ----------
def format_cn_bool_list(bools):
    return ', '.join('是' if b else '否' for b in bools)

def generate_truth_values(n, seed=None):
    rng = random.Random(seed)
    while True:
        vec = [rng.choice([True, False]) for _ in range(n)]
        if any(vec) and any(not v for v in vec):
            return vec

# ---------- 谓词工厂 ----------
def _predicate_factory(template_id, variant, j, k):
    """
    返回 lambda a: <布尔表达式>
    template_id ∈ {0,1,2,3}
    variant 根据 Task-2 说明定义
    """
    if template_id == 0:          # 单目标真假
        return (lambda a: a[j]) if variant == 0 else (lambda a: not a[j])
    if template_id == 1:          # 相同 / 不同
        return (lambda a: a[j] == a[k]) if variant == 0 else (lambda a: a[j] != a[k])
    if template_id == 2:          # XOR / NOT XOR
        return (lambda a: a[j] ^ a[k]) if variant == 0 else (lambda a: not (a[j] ^ a[k]))
    # template_id == 3            # 至少一假 / 全真
    return (lambda a: (not a[j]) or (not a[k])) if variant == 0 else (lambda a: a[j] and a[k])

# ---------- 语句生成 ----------
def generate_statements(truth_values, locations, persons, seed=None):
    """
    随机生成语句并确保唯一解。
    """
    rng = random.Random(seed)
    n = len(truth_values)

    for _ in range(100):  # 最多尝试 100 次寻找唯一解局面
        tpl_meta = []     # (tpl, variant, j, k)
        sentences = []

        for i in range(n):
            tpl = rng.choice([0, 1, 2, 3])
            variant = rng.choice([0, 1])

            if tpl == 0:                 # 只需 1 个目标
                j = rng.choice([x for x in range(n) if x != i])
                k = None
            else:                        # 需要 2 个不同目标
                j, k = rng.sample([x for x in range(n) if x != i], 2)

            tpl_meta.append((tpl, variant, j, k))

            # ----- 生成中文句子 -----
            if tpl == 0:
                phrase = '说真话' if variant == 0 else '说谎话'
                sent = f'在{locations[i]}的人说在{locations[j]}的人{phrase}。'

            elif tpl == 1:
                phrase = '说的话真假相同' if variant == 0 else '说的话真假不同'
                sent = f'在{locations[i]}的人说在{locations[j]}的人和在{locations[k]}的人{phrase}。'

            elif tpl == 2:
                phrase = '恰好一人说真话' if variant == 0 else '说的话真假相同'
                sent = f'在{locations[i]}的人说在{locations[j]}的人和在{locations[k]}的人中{phrase}。'

            else:  # tpl == 3
                phrase = '至少一人说谎话' if variant == 0 else '两人都说真话'
                sent = f'在{locations[i]}的人说在{locations[j]}的人和在{locations[k]}的人{phrase}。'

            sentences.append(sent)

        # 唯一解校验
        if _has_unique_solution(truth_values, tpl_meta):
            return sentences

    raise RuntimeError('无法在限制次数内生成唯一解场景')

# ---------- 唯一解判定 ----------
def _has_unique_solution(real_truth, tpl_meta):
    n = len(real_truth)
    solutions = []
    for assign in product([False, True], repeat=n):
        ok = True
        for i, (tpl, variant, j, k) in enumerate(tpl_meta):
            if assign[i] != _predicate_factory(tpl, variant, j, k)(assign):
                ok = False
                break
        if ok:
            solutions.append(assign)
            if len(solutions) > 1:
                return False
    return len(solutions) == 1 and list(solutions[0]) == real_truth