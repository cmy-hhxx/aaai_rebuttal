# cryptarithm_4.py
# -*- coding: utf-8 -*-
"""
高阶逆向字母算式生成与唯一解验证（改进版）：
- 运算：ADD 或 SUB；
- 计数规则：进位/借位次数的 eq/ge（k≥1）与目标 k；
- 模 m 同余规则（m ∈ {3,9}，唯一/计重模式，左右集合各≥2且并集≥4且不相同）；
- 模 10 字母三元关系（x ≡ y ± z (mod 10)，y≠z，x∉{y,z}，z≠0）；
- 差值模约束：digit(U) − digit(V) ≡ T (mod R)，R ∈ {7,9,11,13}，U≠V，T≠0（若生成为 0 则自动调整权重或常数保证非零）；
- 加权校验与位权校验（公开全部参数；位权按右对齐至 L，不足位按 0 计）。
- 列对齐回溯求解器 + 候选计数上限=2 + 数字域上限控制，保证唯一性验证高效（总体≤3分钟）。
"""

import random
import time
from typing import Dict, List, Tuple, Optional, Callable

ALPHABET = [chr(ord('A') + i) for i in range(26)]

# -------------------- 基础工具 --------------------

def _digits_of(num: int, n: int) -> List[int]:
    s = f"{num:0{n}d}"
    return [int(c) for c in s]

def _num_from_digits(digs: List[int]) -> int:
    res = 0
    for d in digs:
        res = res * 10 + d
    return res

def _borrow_count_sub(a: int, b: int, n: int) -> Tuple[int, List[int]]:
    """减法借位统计：返回借位次数与各列是否借位（高->低）。"""
    ad = _digits_of(a, n)
    bd = _digits_of(b, n)
    bor_flags = []
    borrow = 0
    count = 0
    for i in range(n - 1, -1, -1):
        ai = ad[i]
        bi = bd[i]
        cur = ai - borrow
        if cur < bi:
            count += 1
            bor_flags.append(1)
            borrow = 1
        else:
            bor_flags.append(0)
            borrow = 0
    bor_flags.reverse()
    return count, bor_flags

def _carry_count_add(a: int, b: int, n: int) -> Tuple[int, List[int], int]:
    """加法进位统计：返回进位次数、各列是否产生进位（高->低），以及结果位数 m（=n 或 n+1）。"""
    ad = _digits_of(a, n)
    bd = _digits_of(b, n)
    car_flags_rev = []
    carry = 0
    count = 0
    for i in range(n - 1, -1, -1):
        s = ad[i] + bd[i] + carry
        if s >= 10:
            count += 1
            car_flags_rev.append(1)
            carry = 1
        else:
            car_flags_rev.append(0)
            carry = 0
    car_flags = list(reversed(car_flags_rev))
    m = n + 1 if carry == 1 else n
    return count, car_flags, m

def _build_letter_mapping(digits_used: List[int]) -> Dict[int, str]:
    """为出现的不同数字建立数字->字母的双射（字母互异）。"""
    letters_pool = ALPHABET.copy()
    random.shuffle(letters_pool)
    mapping = {}
    for d in sorted(set(digits_used)):
        mapping[d] = letters_pool.pop()
    return mapping

def _encode_word(digs: List[int], d2l: Dict[int, str]) -> str:
    return ''.join(d2l[d] for d in digs)

def _unique_letters(word: str) -> List[str]:
    seen = set()
    res = []
    for ch in word:
        if ch not in seen:
            seen.add(ch)
            res.append(ch)
    return res

# -------------------- 模约束与校验生成 --------------------

def _sum_letters(letters: List[str], l2d: Dict[str, int], multiplicity: bool, words: Tuple[str, str, str]) -> int:
    """对 letters 求和：multiplicity=True 则按在三词中出现次数计数，否则按唯一计数。"""
    if not multiplicity:
        return sum(l2d[ch] for ch in set(letters))
    counts = {}
    for w in words:
        for ch in w:
            counts[ch] = counts.get(ch, 0) + 1
    total = 0
    for ch in set(letters):
        total += l2d[ch] * counts.get(ch, 0)
    return total

def _rand_mod_constraint(letters_all: List[str], l2d: Dict[str, int], words: Tuple[str, str, str]) -> Dict:
    """随机生成一条模 m 同余约束，保证成立且非平凡：左右集合不相同，左右并集≥4；两侧各≥2个字母。"""
    m = random.choice([9, 3])
    mode = random.choice(['unique', 'with_multiplicity'])

    def sum_mod(L: List[str]) -> int:
        return _sum_letters(L, l2d, multiplicity=(mode == 'with_multiplicity'), words=words) % m

    MAX_TRY = 600
    letters = list(set(letters_all))
    if len(letters) < 4:
        # 兜底
        Ls = letters_all[:]
        Rs = list(reversed(Ls))
        return {'m': m, 'mode': mode, 'left': _unique_letters(''.join(Ls)), 'right': _unique_letters(''.join(Rs))}
    for _ in range(MAX_TRY):
        szL = random.randint(2, min(6, len(letters)))
        szR = random.randint(2, min(6, len(letters)))
        left = random.sample(letters, k=szL)
        right = random.sample(letters, k=szR)
        if set(right) == set(left):
            continue
        if len(set(left) | set(right)) < 4:
            continue
        if sum_mod(left) == sum_mod(right):
            return {'m': m, 'mode': mode, 'left': _unique_letters(''.join(left)), 'right': _unique_letters(''.join(right))}
    # 兜底：尽量不同
    left = random.sample(letters, k=min(2, len(letters)))
    right = random.sample([ch for ch in letters if ch not in left] or letters, k=min(2, len(letters)))
    return {'m': m, 'mode': mode, 'left': _unique_letters(''.join(left)), 'right': _unique_letters(''.join(right))}

def _pick_mod10_triple(letters: List[str], l2d: Dict[str, int]) -> Dict:
    """生成 (x,y,z,op10) 使 digit(x) ≡ digit(y) ± digit(z) (mod 10)，且 y≠z、x∉{y,z}、z≠0。"""
    if not letters:
        ch = 'A'
        return {'x': ch, 'y': ch, 'z': ch, 'op10': '+'}
    tries = 3000
    for _ in range(tries):
        op10 = random.choice(['+', '-'])
        y, z = random.sample(letters, 2) if len(letters) >= 2 else (letters[0], letters[0])
        if y == z:
            continue
        if l2d[z] == 0:
            continue
        if op10 == '+':
            dx = (l2d[y] + l2d[z]) % 10
        else:
            dx = (l2d[y] - l2d[z]) % 10
        x_candidates = [ch for ch in letters if l2d[ch] == dx and ch not in (y, z)]
        if x_candidates:
            x = random.choice(x_candidates)
            return {'x': x, 'y': y, 'z': z, 'op10': op10}
    # 兜底
    return {'x': letters[0], 'y': letters[0], 'z': letters[0], 'op10': '+'}

def _make_weight_checksum(letters_all: List[str], l2d: Dict[str, int]) -> Dict:
    """字母加权校验：随机权重与模 M，返回约束并保证成立；若 T=0 则微调权重使 T≠0。"""
    M = random.choice([11, 13, 17, 19])
    weights = {}
    for ch in letters_all:
        weights[ch] = random.randint(1, 7)
    T = sum(weights[ch] * l2d[ch] for ch in letters_all) % M
    if T == 0 and letters_all:
        # 选择一个字母，权重+1，确保 T ≠ 0
        ch = random.choice(letters_all)
        weights[ch] += 1
        T = sum(weights[c] * l2d[c] for c in letters_all) % M
        if T == 0:
            # 若仍为 0，再增一次
            weights[ch] += 1
            T = sum(weights[c] * l2d[c] for c in letters_all) % M
    return {'M': M, 'weights': weights, 'T': T}

def _make_pos_weight_checks(w1: str, w2: str, w3: str, l2d: Dict[str, int]) -> Dict:
    """位权一致性与交错位权校验（均保证成立），公开全部参数；按右对齐到统一长度 L，不足位按 0 计。"""
    n1 = len(w1); n2 = len(w2); n3 = len(w3)
    L = max(n1, n2, n3)
    def pad(w: str, L: int) -> List[str]:
        return list(w.rjust(L))
    W1 = pad(w1, L); W2 = pad(w2, L); W3 = pad(w3, L)

    Q1 = random.choice([7, 11, 13])
    posW1 = [random.randint(1, 4) for _ in range(L)]
    posW2 = [random.randint(1, 4) for _ in range(L)]
    posW3 = [random.randint(1, 4) for _ in range(L)]
    def val(w, pw):
        return sum((l2d[ch] if ch != ' ' else 0) * pw[i] for i, ch in enumerate(w))
    diff = (val(W1, posW1) + val(W2, posW2) - val(W3, posW3)) % Q1
    if diff != 0:
        posW3[0] = ((posW3[0] + diff - 1) % Q1) + 1
    # 交错位权
    Q2 = random.choice([7, 11, 13])
    altW = [1 if i % 2 == 0 else 2 for i in range(L)]
    ALT = (val(W1, altW) + 2 * val(W2, altW) + 3 * val(W3, altW)) % Q2
    return {
        'L': L,
        'pos_mod': Q1,
        'posW1': posW1, 'posW2': posW2, 'posW3': posW3,
        'target_pos': 0,
        'alt_mod': Q2,
        'altW': altW, 'target_alt': ALT
    }

def _make_diff_constraint(letters_all: List[str], l2d: Dict[str, int]) -> Dict:
    """差值模约束：digit(U) − digit(V) ≡ T (mod R)，R ∈ {7,9,11,13}，U≠V，T≠0。"""
    R = random.choice([7, 9, 11, 13])
    tries = 1000
    for _ in range(tries):
        if len(letters_all) < 2:
            break
        U, V = random.sample(letters_all, 2)
        T = (l2d[U] - l2d[V]) % R
        if T != 0:
            return {'U': U, 'V': V, 'R': R, 'T': T}
    # 兜底：取一个非零常数
    U = letters_all[0]
    V = letters_all[-1] if len(letters_all) > 1 else letters_all[0]
    return {'U': U, 'V': V, 'R': R, 'T': 1}

# -------------------- 列对齐求解器（唯一性验证，候选计数上限） --------------------

class ColumnSolver:
    """列约束回溯；支持 ADD 与 SUB；限定数字域为 digits_set；候选计数上限避免枚举爆炸。"""
    def __init__(self, op: str, w1: str, w2: str, w3: str, digits_set: List[int], leading_nonzero_letters: List[str], time_budget: float = 120.0):
        self.op = op
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.L = max(len(w1), len(w2), len(w3))
        self.a = list(w1.rjust(self.L))
        self.b = list(w2.rjust(self.L))
        self.c = list(w3.rjust(self.L))
        self.digits_set = digits_set[:]
        self.leading_nonzero_letters = set(leading_nonzero_letters)
        self.assignment: Dict[str, int] = {}
        self.used_digits: set = set()
        self.deadline = time.time() + time_budget
        self.candidates_count = 0

    def _can_assign(self, ch: str, d: int) -> bool:
        if ch == ' ':
            return d == 0
        if ch in self.assignment:
            return self.assignment[ch] == d
        if d in self.used_digits:
            return False
        if ch in self.leading_nonzero_letters and d == 0:
            return False
        if d not in self.digits_set:
            return False
        return True

    def _assign(self, ch: str, d: int):
        if ch != ' ':
            self.assignment[ch] = d
            self.used_digits.add(d)

    def _unassign(self, ch: str, d: int):
        if ch != ' ' and ch in self.assignment:
            del self.assignment[ch]
            if d in self.used_digits:
                self.used_digits.remove(d)

    def _get(self, ch: str) -> Optional[int]:
        if ch == ' ':
            return 0
        return self.assignment.get(ch, None)

    def solve_with_limit(self, mapping_ok: Callable[[Dict[str, int]], bool], limit: int = 2) -> int:
        if self.op == 'ADD':
            self._search_add(self.L - 1, 0, mapping_ok, limit)
        else:
            self._search_sub(self.L - 1, 0, mapping_ok, limit)
        return self.candidates_count

    def _search_add(self, i: int, carry: int, mapping_ok, limit):
        if time.time() > self.deadline or self.candidates_count >= limit:
            return
        if i < 0:
            if carry == 0:
                if mapping_ok(self.assignment):
                    self.candidates_count += 1
            return
        A, B, C = self.a[i], self.b[i], self.c[i]
        Ad = self._get(A)
        Bd = self._get(B)
        Cd = self._get(C)
        A_choices = [Ad] if Ad is not None else self.digits_set
        B_choices = [Bd] if Bd is not None else self.digits_set
        C_choices = [Cd] if Cd is not None else self.digits_set
        for da in A_choices:
            if self.candidates_count >= limit:
                return
            if not self._can_assign(A, da):
                continue
            self._assign(A, da)
            for db in B_choices:
                if self.candidates_count >= limit:
                    break
                if not self._can_assign(B, db):
                    continue
                self._assign(B, db)
                s = da + db + carry
                dc = s % 10
                ncarry = 1 if s >= 10 else 0
                for dc_try in C_choices:
                    if dc_try != dc:
                        continue
                    if not self._can_assign(C, dc_try):
                        continue
                    self._assign(C, dc_try)
                    self._search_add(i - 1, ncarry, mapping_ok, limit)
                    self._unassign(C, dc_try)
                self._unassign(B, db)
            self._unassign(A, da)

    def _search_sub(self, i: int, borrow: int, mapping_ok, limit):
        if time.time() > self.deadline or self.candidates_count >= limit:
            return
        if i < 0:
            if borrow == 0:
                if mapping_ok(self.assignment):
                    self.candidates_count += 1
            return
        A, B, C = self.a[i], self.b[i], self.c[i]
        Ad = self._get(A)
        Bd = self._get(B)
        Cd = self._get(C)
        A_choices = [Ad] if Ad is not None else self.digits_set
        B_choices = [Bd] if Bd is not None else self.digits_set
        C_choices = [Cd] if Cd is not None else self.digits_set
        for da in A_choices:
            if self.candidates_count >= limit:
                return
            if not self._can_assign(A, da):
                continue
            self._assign(A, da)
            for db in B_choices:
                if self.candidates_count >= limit:
                    break
                if not self._can_assign(B, db):
                    continue
                self._assign(B, db)
                tmp = da - borrow
                if tmp < db:
                    dc = tmp + 10 - db
                    nborrow = 1
                else:
                    dc = tmp - db
                    nborrow = 0
                for dc_try in C_choices:
                    if dc_try != dc:
                        continue
                    if not self._can_assign(C, dc_try):
                        continue
                    self._assign(C, dc_try)
                    self._search_sub(i - 1, nborrow, mapping_ok, limit)
                    self._unassign(C, dc_try)
                self._unassign(B, db)
            self._unassign(A, da)

# -------------------- 文本与竖式 --------------------

def _format_vertical(op: str, w1: str, w2: str, w3: str, a: int, b: int, c: int) -> str:
    op_char = '+' if op == 'ADD' else '-'
    # 字母竖式
    top = w1
    mid = op_char + w2
    bot = '=' + w3
    line_len = max(len(top), len(mid), len(bot))
    s1 = top.rjust(line_len)
    s2 = mid.rjust(line_len)
    s3 = bot.rjust(line_len)
    # 数字竖式
    sd1 = f"{a}".rjust(line_len)
    sd2 = (op_char + f"{b}").rjust(line_len)
    sd3 = ('=' + f"{c}").rjust(line_len)
    return '\n'.join([s1, s2, s3, '', sd1, sd2, sd3])

def _rel_to_cn(rel: str) -> str:
    return {'eq': '恰好等于', 'ge': '至少'}.get(rel, '恰好等于')

# -------------------- 生成与唯一性验证 --------------------

def function_1(n: int, allow_ops: List[str], max_mod_constraints: int, max_digits_used: int) -> Dict:
    """
    生成一个满足复合约束且唯一可解的实例：
    - 随机 op ∈ allow_ops，rel ∈ {eq,ge}，目标 k≥1；
    - 生成 (a,b,c) 与字母映射 (w1,w2,w3)；
    - 限制数字域 |D| ≤ max_digits_used；
    - 生成有效的模 m、模 10（非平凡）、加权（T≠0）、位权、差值模约束（全部参数公开；位权按右对齐至 L，不足位按 0 计）；
    - 列对齐求解器验证唯一（候选上限=2），总时限≤3分钟。
    """
    assert 3 <= n <= 9
    deadline_all = time.time() + 180.0  # 3 min

    while time.time() < deadline_all:
        op = random.choice(allow_ops)
        rel = random.choice(['eq', 'ge'])  # 禁止 'le' 与 k=0 的显见线索

        # 目标次数 k≥1
        if op == 'SUB':
            k = random.randint(1, max(1, n - 1))
        else:
            k = random.randint(1, n)

        low = 10 ** (n - 1)
        high = 10 ** n - 1

        # 搜索满足计数规则的 (a,b,c)
        for _ in range(7000):
            a = random.randint(low, high)
            b = random.randint(low, high)
            if op == 'SUB':
                if b > a:
                    a, b = b, a
                c = a - b
                if len(str(c)) != n:
                    continue
                cnt, flags = _borrow_count_sub(a, b, n)
                ok_cnt = (cnt == k) if rel == 'eq' else (cnt >= k)
                if not ok_cnt:
                    continue
            else:
                c = a + b
                cnt, flags, m = _carry_count_add(a, b, n)
                ok_cnt = (cnt == k) if rel == 'eq' else (cnt >= k)
                if not ok_cnt:
                    continue

            # 数字集合与映射
            digs_a = _digits_of(a, n)
            digs_b = _digits_of(b, n)
            digs_c = _digits_of(c, len(str(c)))
            digits_used = sorted(set(digs_a + digs_b + digs_c))
            if len(digits_used) > max_digits_used:
                continue
            d2l = _build_letter_mapping(digits_used)
            l2d = {v: k for k, v in d2l.items()}

            # 构造单词
            w1 = _encode_word(digs_a, d2l)
            w2 = _encode_word(digs_b, d2l)
            w3 = _encode_word(digs_c, d2l)

            # 反显见（SUB）：禁止个位三字母完全相同
            if op == 'SUB' and len(w1) > 0 and (w1[-1] == w2[-1] == w3[-1]):
                continue

            letters_all = _unique_letters(w1 + w2 + w3)
            words_tuple = (w1, w2, w3)

            # 生成有效模 m 约束（左右集合不相同，且并集≥4；两侧各≥2）
            mod_constraints = []
            num_mods = random.randint(2, max_mod_constraints)
            tries_mc = 0
            while len(mod_constraints) < num_mods and tries_mc < 500:
                mc = _rand_mod_constraint(letters_all, l2d, words_tuple)
                if set(mc['left']) != set(mc['right']) and len(set(mc['left']) | set(mc['right'])) >= 4 and len(set(mc['left'])) >= 2 and len(set(mc['right'])) >= 2:
                    mod_constraints.append(mc)
                tries_mc += 1
            if len(mod_constraints) < 1:
                continue

            # 生成非平凡模10三元组
            triple10 = _pick_mod10_triple(letters_all, l2d)
            if triple10['y'] == triple10['z'] or triple10['x'] in (triple10['y'], triple10['z']) or l2d[triple10['z']] == 0:
                continue

            # 加权校验与位权校验（公开参数；位权按右对齐至 L，不足位按 0 计）
            checksum = _make_weight_checksum(letters_all, l2d)
            poscheck = _make_pos_weight_checks(w1, w2, w3, l2d)

            # 差值模约束
            diffc = _make_diff_constraint(letters_all, l2d)

            # 唯一性验证（列对齐回溯，候选上限=2）
            def mapping_ok(assign: Dict[str, int]) -> bool:
                # 域与首字母非零
                for ch in letters_all:
                    if ch not in assign or assign[ch] not in digits_used:
                        return False
                if assign[w1[0]] == 0 or assign[w2[0]] == 0 or assign[w3[0]] == 0:
                    return False
                # 数值等式与计数规则复核
                A_test = _num_from_digits([assign[ch] for ch in w1])
                B_test = _num_from_digits([assign[ch] for ch in w2])
                C_test = _num_from_digits([assign[ch] for ch in w3])
                if op == 'ADD':
                    if A_test + B_test != C_test:
                        return False
                    cnt_check, _, _ = _carry_count_add(A_test, B_test, n)
                else:
                    if A_test - B_test != C_test:
                        return False
                    cnt_check, _ = _borrow_count_sub(A_test, B_test, n)
                if rel == 'eq' and cnt_check != k:
                    return False
                if rel == 'ge' and cnt_check < k:
                    return False
                # 模 m 约束
                for mc in mod_constraints:
                    mode_mult = (mc['mode'] == 'with_multiplicity')
                    if mode_mult:
                        sumL = _sum_letters(mc['left'], assign, True, words_tuple)
                        sumR = _sum_letters(mc['right'], assign, True, words_tuple)
                    else:
                        sumL = sum(assign[ch] for ch in set(mc['left']))
                        sumR = sum(assign[ch] for ch in set(mc['right']))
                    if (sumL - sumR) % mc['m'] != 0:
                        return False
                # 模 10
                x, y, z, op10 = triple10['x'], triple10['y'], triple10['z'], triple10['op10']
                if op10 == '+':
                    if (assign[x] - (assign[y] + assign[z])) % 10 != 0:
                        return False
                else:
                    if (assign[x] - (assign[y] - assign[z])) % 10 != 0:
                        return False
                # 加权校验
                if sum(checksum['weights'][ch] * assign[ch] for ch in letters_all) % checksum['M'] != checksum['T']:
                    return False
                # 位权一致性与交错位权（右对齐至 L，不足位按 0 计）
                Lpad = poscheck['L']
                def pad_digits(w: str, L: int) -> List[int]:
                    arr = [None] * L
                    s = w.rjust(L)
                    for i, ch in enumerate(s):
                        arr[i] = assign[ch] if ch != ' ' else 0
                    return arr
                d1 = pad_digits(w1, Lpad); d2 = pad_digits(w2, Lpad); d3 = pad_digits(w3, Lpad)
                left_val = (sum(d1[i] * poscheck['posW1'][i] for i in range(Lpad)) +
                            sum(d2[i] * poscheck['posW2'][i] for i in range(Lpad))) % poscheck['pos_mod']
                right_val = (sum(d3[i] * poscheck['posW3'][i] for i in range(Lpad))) % poscheck['pos_mod']
                if (left_val - right_val - poscheck['target_pos']) % poscheck['pos_mod'] != 0:
                    return False
                alt_val = (sum(d1[i] * poscheck['altW'][i] for i in range(Lpad)) +
                           2 * sum(d2[i] * poscheck['altW'][i] for i in range(Lpad)) +
                           3 * sum(d3[i] * poscheck['altW'][i] for i in range(Lpad))) % poscheck['alt_mod']
                if alt_val != poscheck['target_alt']:
                    return False
                # 差值模约束
                if (assign[diffc['U']] - assign[diffc['V']] - diffc['T']) % diffc['R'] != 0:
                    return False
                return True

            solver = ColumnSolver(op=op, w1=w1, w2=w2, w3=w3,
                                  digits_set=digits_used,
                                  leading_nonzero_letters=[w1[0], w2[0], w3[0]],
                                  time_budget=120.0)
            cand_count = solver.solve_with_limit(mapping_ok, limit=2)
            if cand_count == 1:
                # 文本化规则（全部参数公开）
                op_cn = '加法' if op == 'ADD' else '减法'
                count_name = '进位' if op == 'ADD' else '借位'
                rel_str = _rel_to_cn(rel)

                # 模约束句式
                mod_sents = []
                for mc in mod_constraints:
                    mode_cn = '按唯一计数' if mc['mode'] == 'unique' else '按出现次数计数'
                    Ls = '[' + ', '.join(mc['left']) + ']'
                    Rs = '[' + ', '.join(mc['right']) + ']'
                    mod_sents.append(f'在模 {mc["m"]} 下，{Ls} 与 {Rs} 的对应数字和同余（{mode_cn}）')

                # 模10句式
                x, y, z, op10 = triple10['x'], triple10['y'], triple10['z'], triple10['op10']
                mod10_sent = f'模 10 关系：{x} ≡ {y} {op10} {z} (mod 10)'

                # 加权校验句式
                weights_pairs = ', '.join([f'{ch}:{checksum["weights"][ch]}' for ch in sorted(checksum['weights'])])
                checksum_sent = f'加权校验：Σ w(letter)·digit(letter) ≡ {checksum["T"]} (mod {checksum["M"]})，其中权重 w 为 [{weights_pairs}]'

                # 位权校验句式（明确给出数组与目标；并提示右对齐至 L，不足位按 0 计）
                posW1_str = '[' + ', '.join(str(xi) for xi in poscheck['posW1']) + ']'
                posW2_str = '[' + ', '.join(str(xi) for xi in poscheck['posW2']) + ']'
                posW3_str = '[' + ', '.join(str(xi) for xi in poscheck['posW3']) + ']'
                altW_str = '[' + ', '.join(str(xi) for xi in poscheck['altW']) + ']'
                pos_sent = f'位权一致性（右对齐至 L={poscheck["L"]}，不足位按 0 计）：在模 {poscheck["pos_mod"]} 下，Σ {posW1_str}·digits({w1}) + Σ {posW2_str}·digits({w2}) 与 Σ {posW3_str}·digits({w3}) 的差同余于 {poscheck["target_pos"]}；交错位权：权重 {altW_str}，Σ(d1) + 2Σ(d2) + 3Σ(d3) ≡ {poscheck["target_alt"]} (mod {poscheck["alt_mod"]})'

                # 差值模约束句式
                diff_sent = f'差值约束：digit({diffc["U"]}) − digit({diffc["V"]}) ≡ {diffc["T"]} (mod {diffc["R"]})'

                constraints_text = '；'.join([
                    f'字母取自数字集合 D（互不相同且首字母不为 0）',
                    f'{op_cn}列运算，长度 n={n}，{count_name}次数{rel_str} {k}',
                    checksum_sent,
                    pos_sent,
                    diff_sent
                ] + mod_sents + [mod10_sent])

                op_char = '+' if op == 'ADD' else '-'
                equation_text = f'{w1} {op_char} {w2} = {w3}'
                vertical = _format_vertical(op, w1, w2, w3, a, b, c)
                mapping_list = sorted([(ch, l2d[ch]) for ch in _unique_letters(w1 + w2 + w3)], key=lambda x: x[0])
                digits_set_str = '(' + ', '.join(str(d) for d in digits_used) + ')'

                return {
                    'op': op, 'op_cn': op_cn, 'count_name': count_name, 'rel_str': rel_str, 'k': k,
                    'n': n, 'A': a, 'B': b, 'C': c,
                    'w1': w1, 'w2': w2, 'w3': w3,
                    'result_len': len(str(c)),
                    'flags': flags,
                    'letters': _unique_letters(w1 + w2 + w3),
                    'mapping': mapping_list,
                    'digits_set': digits_used,
                    'digits_set_str': digits_set_str,
                    'mod_constraints': mod_constraints,
                    'triple10': triple10,
                    'checksum': checksum,
                    'poscheck': poscheck,
                    'diffc': diffc,
                    'equation_text': equation_text,
                    'constraints_text': constraints_text,
                    'vertical': vertical,
                }
    raise RuntimeError('Unique-instance generation timed out; please rerun.')

def function_2(gen: Dict) -> str:
    """
    标准答案文本（首行提供可比对的简明答案）：
    - 首行：映射====纯数字算式
    - 其后：映射表、竖式、规则核验、数值核对等详细过程
    """
    op = gen['op']
    n = gen['n']
    rel_str = gen['rel_str']
    k = gen['k']
    A, B, C = gen['A'], gen['B'], gen['C']
    w1, w2, w3 = gen['w1'], gen['w2'], gen['w3']
    mapping = gen['mapping']
    mod_constraints = gen['mod_constraints']
    triple10 = gen['triple10']
    checksum = gen['checksum']
    poscheck = gen['poscheck']
    diffc = gen['diffc']
    vertical = gen['vertical']
    digits_set = gen['digits_set']

    l2d = {ch: d for ch, d in mapping}
    words_tuple = (w1, w2, w3)

    # 借/进位复核
    if op == 'SUB':
        cnt_check, _ = _borrow_count_sub(A, B, n)
        count_name = '借位'
    else:
        cnt_check, _, _ = _carry_count_add(A, B, n)
        count_name = '进位'

    # 模 m 核验
    mod_lines = []
    for mc in mod_constraints:
        mode_mult = (mc['mode'] == 'with_multiplicity')
        if mode_mult:
            sumL = _sum_letters(mc['left'], l2d, True, words_tuple)
            sumR = _sum_letters(mc['right'], l2d, True, words_tuple)
        else:
            sumL = sum(l2d[ch] for ch in set(mc['left']))
            sumR = sum(l2d[ch] for ch in set(mc['right']))
        ok = (sumL - sumR) % mc['m'] == 0
        mode_cn = '按唯一计数' if not mode_mult else '按出现次数计数'
        Ls = '[' + ', '.join(mc['left']) + ']'
        Rs = '[' + ', '.join(mc['right']) + ']'
        mod_lines.append(f'  模 {mc["m"]}（{mode_cn}）：{Ls} 与 {Rs} 的和分别为 {sumL} 与 {sumR} → {"通过" if ok else "未通过"}')

    # 模10核验
    x, y, z, op10 = triple10['x'], triple10['y'], triple10['z'], triple10['op10']
    if op10 == '+':
        ok10 = (l2d[x] - (l2d[y] + l2d[z])) % 10 == 0
        expr10 = f'{l2d[x]} ≡ {l2d[y]} + {l2d[z]} (mod 10)'
    else:
        ok10 = (l2d[x] - (l2d[y] - l2d[z])) % 10 == 0
        expr10 = f'{l2d[x]} ≡ {l2d[y]} - {l2d[z]} (mod 10)'

    # 加权校验
    w_pairs = ', '.join([f'{ch}:{checksum["weights"][ch]}' for ch in sorted(checksum['weights'])])
    sum_w = sum(checksum['weights'][ch] * l2d[ch] for ch in checksum['weights'])
    ok_w = (sum_w % checksum['M']) == checksum['T']

    # 位权校验（右对齐至 L，不足位按 0 计）
    Lpad = poscheck['L']
    def pad_digits(w: str, L: int) -> List[int]:
        arr = [None] * L
        s = w.rjust(L)
        for i, ch in enumerate(s):
            arr[i] = l2d[ch] if ch != ' ' else 0
        return arr
    d1 = pad_digits(w1, Lpad); d2 = pad_digits(w2, Lpad); d3 = pad_digits(w3, Lpad)
    left_val = (sum(d1[i] * poscheck['posW1'][i] for i in range(Lpad)) +
                sum(d2[i] * poscheck['posW2'][i] for i in range(Lpad))) % poscheck['pos_mod']
    right_val = (sum(d3[i] * poscheck['posW3'][i] for i in range(Lpad))) % poscheck['pos_mod']
    ok_pos = (left_val - right_val - poscheck['target_pos']) % poscheck['pos_mod'] == 0
    alt_val = (sum(d1[i] * poscheck['altW'][i] for i in range(Lpad)) +
               2 * sum(d2[i] * poscheck['altW'][i] for i in range(Lpad)) +
               3 * sum(d3[i] * poscheck['altW'][i] for i in range(Lpad))) % poscheck['alt_mod']
    ok_alt = alt_val == poscheck['target_alt']

    # 差值模约束核验
    ok_diff = (l2d[diffc['U']] - l2d[diffc['V']] - diffc['T']) % diffc['R'] == 0

    # 简明可比对答案：映射====纯数字算式
    mapping_str = ','.join([f'{ch}={l2d[ch]}' for ch in sorted(l2d.keys())])
    op_char = '+' if op == 'ADD' else '-'
    eq_str = f'{A} {op_char} {B} = {C}'
    header_line = f'{mapping_str}===={eq_str}'

    # 竖式与详细过程
    lines = []
    lines.append(header_line)
    # lines.append('')
    # lines.append('一、字母→数字映射（按字母序）：')
    # lines.append(', '.join([f'{ch}={d}' for ch, d in mapping]))
    # lines.append('')
    # lines.append('二、竖式演算（上为字母；下为数字）：')
    # lines.append(vertical)
    # lines.append('')
    # lines.append(f'三、{count_name}次数规则：{rel_str} {k} 次；实际{count_name}次数：{cnt_check} 次 → ' + ('通过' if ((rel_str == '恰好等于' and cnt_check == k) or (rel_str == '至少' and cnt_check >= k)) else '未通过'))
    # lines.append('')
    # lines.append('四、模 m 同余规则核验：')
    # lines.extend(mod_lines)
    # lines.append('')
    # lines.append(f'五、模 10 字母关系核验：{x} ≡ {y} {op10} {z} (mod 10)；数值验证 {expr10} → ' + ('通过' if ok10 else '未通过'))
    # lines.append('')
    # lines.append(f'六、加权校验：Σ w(letter)·digit(letter) ≡ {checksum["T"]} (mod {checksum["M"]})，权重 w 为 [{w_pairs}]；计算和为 {sum_w} → ' + ('通过' if ok_w else '未通过'))
    # lines.append(f'七、位权一致性：左值 {left_val}，右值 {right_val}，目标 {poscheck["target_pos"]} (mod {poscheck["pos_mod"]})；交错位权：计算值 {alt_val} (mod {poscheck["alt_mod"]})，目标 {poscheck["target_alt"]} → ' + ('通过' if (ok_pos and ok_alt) else '未通过'))
    # lines.append(f'八、差值模约束核验：digit({diffc["U"]}) − digit({diffc["V"]}) ≡ {diffc["T"]} (mod {diffc["R"]}) → ' + ('通过' if ok_diff else '未通过'))
    # lines.append('')
    # lines.append(f'九、数字核对：{A} {op_char} {B} = {C}；数字域 D={tuple(digits_set)}；n={n}；位权对齐长度 L={poscheck["L"]}')
    return header_line#'\n'.join(lines)