import random
import itertools

# ==================== 基础工具函数 ====================
def _rand_nonzero_digit():
    return random.randint(1, 9)

def _rand_digit():
    return random.randint(0, 9)

def _make_number_with_len(n_len):
    assert n_len >= 1
    first = _rand_nonzero_digit()
    rest = [str(_rand_digit()) for _ in range(n_len - 1)]
    return int(str(first) + "".join(rest))

def _num_to_digits(n):
    return [int(ch) for ch in str(n)]

def _build_mapping_from_digits(digits_all):
    distinct_digits = sorted(set(digits_all))
    if len(distinct_digits) > 10:
        raise ValueError("Too many distinct digits.")
    base_letters = [chr(ord('A') + i) for i in range(26)]
    random.shuffle(base_letters)
    chosen_letters = base_letters[:len(distinct_digits)]
    digit_to_letter = {d: chosen_letters[i] for i, d in enumerate(distinct_digits)}
    letter_to_digit = {v: k for k, v in digit_to_letter.items()}
    return chosen_letters[:], digit_to_letter, letter_to_digit

def _words_from_numbers(A, B1, B2, C, digit_to_letter):
    word_A = "".join(digit_to_letter[d] for d in _num_to_digits(A))
    word_B1 = "".join(digit_to_letter[d] for d in _num_to_digits(B1))
    word_B2 = "".join(digit_to_letter[d] for d in _num_to_digits(B2))
    word_C = "".join(digit_to_letter[d] for d in _num_to_digits(C))
    return word_A, word_B1, word_B2, word_C

def gen_crypt_instance(nA, nB1, nB2, nC, arith_templates, arith_choice, max_trials=10000):
    tid = int(arith_choice)
    for _ in range(max_trials):
        B1 = _make_number_with_len(nB1)
        B2 = _make_number_with_len(nB2)
        C  = _make_number_with_len(nC)
        
        # 0: A - B1 - B2 = C
        # 1: A - B1 = B2 + C
        # 2: A = B1 + B2 + C
        # 3: A + B1 = B2 + C
        if tid in (0, 1, 2):
            A = B1 + B2 + C
            if len(str(A)) != nA: continue
        else:
            total = B2 + C
            if total <= B1: continue
            A = total - B1
            if len(str(A)) != nA or A <= 0: continue

        digits_all = _num_to_digits(A) + _num_to_digits(B1) + _num_to_digits(B2) + _num_to_digits(C)
        try:
            letters_list, digit_to_letter, letter_to_digit = _build_mapping_from_digits(digits_all)
        except ValueError:
            continue
            
        word_A, word_B1, word_B2, word_C = _words_from_numbers(A, B1, B2, C, digit_to_letter)

        # 确保首位不为0
        if any(letter_to_digit[w[0]] == 0 for w in [word_A, word_B1, word_B2, word_C]):
            continue

        eq_str = (
            f"{A} - {B1} - {B2} = {C}" if tid == 0 else
            f"{A} - {B1} = {B2} + {C}" if tid == 1 else
            f"{A} = {B1} + {B2} + {C}" if tid == 2 else
            f"{A} + {B1} = {B2} + {C}"
        )

        return {
            "words":   {"A": word_A, "B1": word_B1, "B2": word_B2, "C": word_C},
            "numbers": {"A": A, "B1": B1, "B2": B2, "C": C},
            "mapping": letter_to_digit,
            "letters": letters_list,
            "equation_str": eq_str,
            "template": arith_templates[tid],
            "tid": tid
        }
    raise RuntimeError("Failed to generate instance.")

def get_letters_from_instance(ci):
    return ci["letters"]

# ==================== 唯一解验证与生成逻辑 ====================

class SimpleSolver:
    """轻量级回溯求解器，用于验证解的唯一性"""
    def __init__(self, ci, relations):
        self.words = ci['words']
        self.tid = ci['tid']
        self.relations = relations
        self.letters = ci['letters']
        self.leading = {w[0] for w in self.words.values()}
        
    def check_constraints(self, current_map):
        # 检查首位非零
        for l in self.leading:
            if current_map[l] == 0: return False
        
        # 检查生成的关系约束
        for (a, b, op) in self.relations:
            va, vb = current_map[a], current_map[b]
            if op == 'eq' and not (va == vb): return False
            if op == 'gt' and not (va > vb): return False
            if op == 'lt' and not (va < vb): return False
            if op == 'ge' and not (va >= vb): return False
            if op == 'le' and not (va <= vb): return False
            
        # 检查算式是否成立
        val_A = int("".join(str(current_map[c]) for c in self.words['A']))
        val_B1 = int("".join(str(current_map[c]) for c in self.words['B1']))
        val_B2 = int("".join(str(current_map[c]) for c in self.words['B2']))
        val_C = int("".join(str(current_map[c]) for c in self.words['C']))
        
        tid = self.tid
        if tid == 0: return val_A - val_B1 - val_B2 == val_C
        if tid == 1: return val_A - val_B1 == val_B2 + val_C
        if tid == 2: return val_A == val_B1 + val_B2 + val_C
        if tid == 3: return val_A + val_B1 == val_B2 + val_C
        return False

    def solve(self, limit=2):
        solutions = []
        digits = range(10)
        # 简单的全排列搜索，适用于字母数较少的情况
        for perm in itertools.permutations(digits, len(self.letters)):
            current_map = {self.letters[i]: perm[i] for i in range(len(self.letters))}
            
            # 快速剪枝：首位不能为0
            valid_leading = True
            for l in self.leading:
                if current_map[l] == 0:
                    valid_leading = False
                    break
            if not valid_leading: continue
            
            if self.check_constraints(current_map):
                solutions.append(current_map)
                if len(solutions) >= limit:
                    break
        return solutions

def gen_guaranteed_relations(ci, comp_ops, min_constraints=2):
    """
    Solve-then-Constrain 核心逻辑：
    生成能够将解空间锁定为唯一解的最小约束集。
    """
    target_map = ci['mapping']
    letters = ci['letters']
    
    current_relations = []
    
    # 1. 随机添加一些初始约束以增加熵
    pool = []
    Ls = list(letters)
    random.shuffle(Ls)
    attempts = 0
    # 尝试添加 min_constraints 条不冲突的约束
    while len(current_relations) < min_constraints and attempts < 20:
        a, b = random.sample(Ls, 2)
        va, vb = target_map[a], target_map[b]
        op = random.choice(comp_ops)
        ok = (va == vb) if op == 'eq' else \
             (va >  vb) if op == 'gt' else \
             (va <  vb) if op == 'lt' else \
             (va >= vb) if op == 'ge' else \
             (va <= vb) if op == 'le' else False
        
        if ok and (a, b, op) not in current_relations:
             current_relations.append((a, b, op))
        attempts += 1
        
    # 2. 迭代修补 (Verify & Patch)
    for _ in range(5): # 最多5轮迭代，避免无限循环
        solver = SimpleSolver(ci, current_relations)
        solutions = solver.solve(limit=2)
        
        if len(solutions) <= 1:
            # 已经唯一（或者无解，但基于target_map生成通常不会无解）
            break
            
        sol_A = solutions[0]
        sol_B = solutions[1]
        
        # 找出两个解中赋值不同的字母
        diff_letter = None
        for l in letters:
            if sol_A[l] != sol_B[l]:
                diff_letter = l
                break
        if not diff_letter: break
            
        # 寻找区分条件
        patch_found = False
        target_val_diff = target_map[diff_letter]
        
        for other in letters:
            if other == diff_letter: continue
            target_val_other = target_map[other]
            
            # 尝试 'gt' 或 'lt'，寻找在 Target 中成立，但在 干扰解 中不成立 的规则
            for op in ['gt', 'lt']:
                is_true_in_target = (target_val_diff > target_val_other) if op == 'gt' else (target_val_diff < target_val_other)
                
                if is_true_in_target:
                    # 确定 sol_A 和 sol_B 哪个是干扰解
                    alt_sol = sol_B if sol_A == target_map else sol_A
                    # 如果 SimpleSolver 没搜到 target_map (不太可能)，则假设 A 是干扰
                    if alt_sol == target_map: alt_sol = sol_A
                    
                    alt_val_diff = alt_sol[diff_letter]
                    alt_val_other = alt_sol[other]
                    is_true_in_alt = (alt_val_diff > alt_val_other) if op == 'gt' else (alt_val_diff < alt_val_other)
                    
                    if not is_true_in_alt:
                        # 找到区分约束！
                        current_relations.append((diff_letter, other, op))
                        patch_found = True
                        break
            if patch_found: break
            
    return current_relations

def pick_query_desc(word_A, word_B1, word_B2, word_C, arith_choice):
    lens = (len(word_A), len(word_B1), len(word_B2), len(word_C))
    tid = int(arith_choice)
    # 根据模板生成正确的算式字符串
    if tid == 0: eq_fmt = f"{word_A} - {word_B1} - {word_B2} = {word_C}"
    elif tid == 1: eq_fmt = f"{word_A} - {word_B1} = {word_B2} + {word_C}"
    elif tid == 2: eq_fmt = f"{word_A} = {word_B1} + {word_B2} + {word_C}"
    else: eq_fmt = f"{word_A} + {word_B1} = {word_B2} + {word_C}"

    templates = [
        f"Replace letters with digits in the equation: {eq_fmt}. The terms have lengths {lens[0]}, {lens[1]}, {lens[2]}, {lens[3]}.",
        f"Solve the letter-to-digit mapping for {eq_fmt}. Then output the full numeric equation.",
        f"Find the numeric values satisfying {eq_fmt} (lengths: {lens[0]}/{lens[1]}/{lens[2]}/{lens[3]})."
    ]
    return random.choice(templates)

def pick_global_desc(word_A, word_B1, word_B2, word_C):
    lens = (len(word_A), len(word_B1), len(word_B2), len(word_C))
    forms = [
        f"Consider a cryptarithmetic puzzle with terms {word_A}, {word_B1}, {word_B2}, {word_C} (lengths: {lens[0]}/{lens[1]}/{lens[2]}/{lens[3]}). Each letter represents a unique digit (0-9). The leading letter of each term is non-zero.",
        f"A logic puzzle involves four terms: {word_A}, {word_B1}, {word_B2}, {word_C}. Assign unique digits to letters such that no number starts with 0.",
    ]
    return random.choice(forms)

def op_word(op):
    return {
        'eq': 'equals', 'gt': 'is greater than', 'lt': 'is less than',
        'ge': 'is greater than or equal to', 'le': 'is less than or equal to'
    }.get(op, 'compares to')