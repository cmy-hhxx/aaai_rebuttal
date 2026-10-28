# cryptarithm_0.py
# Helper functions for parameterized cryptarithm generation with randomized constraints and text styles
# 改进点（与 YAML 同步）：
# - 仿射线索：排除首字母与已固定字母；强制系数互素；至多 1 条，降低“显见线索”风险。
# - checksum：由全量字母改为随机子集（3~6 个或不超过总字母数），避免形成过强的线性方程组。
# - 其余线索仍做互斥与去重；故事文本保持“Additional hints:”固定前缀；答案格式说明保持严格。

import random
import string
import math

def _int_to_base_digits(n, base):
    # Returns list of digits (most significant first)
    if n == 0:
        return [0]
    digs = []
    while n > 0:
        digs.append(n % base)
        n //= base
    return list(reversed(digs))

def _rand_nonzero_digit(base):
    return random.randint(1, base - 1)

def _rand_number_with_length(base, length):
    # length >= 1, leading digit nonzero
    leading = _rand_nonzero_digit(base)
    other = [random.randint(0, base - 1) for _ in range(length - 1)]
    digits = [leading] + other
    val = 0
    for d in digits:
        val = val * base + d
    return val

def _digits_to_word(digits, digit_to_letter):
    # digits: list (MSD first)
    return ''.join(digit_to_letter[d] for d in digits)

def extract_letters(words):
    # words is a list of strings
    s = set()
    for w in words:
        for ch in w:
            s.add(ch)
    return sorted(s)

def get_max_len(words):
    return max(len(w) for w in words)

def gen_powers(base, max_len):
    # returns [base**0, base**1, ..., base**(max_len-1)]
    res = [1]
    for _ in range(1, max_len):
        res.append(res[-1] * base)
    return res

def _render_expression(words, coeffs):
    # Build human-readable expression like W1 + W2 = W3 (+ W4)
    lhs = []
    rhs = []
    for w, c in zip(words, coeffs):
        if c > 0:
            lhs.append(w)
        else:
            rhs.append(w)
    lhs_str = ' + '.join(lhs) if lhs else '0'
    rhs_str = ' + '.join(rhs) if rhs else '0'
    return f'{lhs_str} = {rhs_str}'

def _choose_template():
    # Operation templates: add2, add3, sub2, sub3
    t = random.choice(['add2', 'add3', 'sub2', 'sub3'])
    if t == 'add2':
        return t, 3
    if t == 'add3':
        return t, 4
    if t == 'sub2':
        return t, 3
    return 'sub3', 4

def _gen_numbers_for_template(base, tpl):
    # Generate numeric operands consistent with template
    if tpl == 'add2':
        la = random.randint(3, 6)
        lb = random.randint(3, 6)
        a = _rand_number_with_length(base, la)
        b = _rand_number_with_length(base, lb)
        c = a + b
        return [a, b, c]
    if tpl == 'add3':
        la = random.randint(3, 5)
        lb = random.randint(3, 5)
        lc = random.randint(3, 5)
        a = _rand_number_with_length(base, la)
        b = _rand_number_with_length(base, lb)
        c = _rand_number_with_length(base, lc)
        d = a + b + c
        return [a, b, c, d]
    if tpl == 'sub2':
        la = random.randint(3, 6)
        lb = random.randint(3, 6)
        a = _rand_number_with_length(base, la)
        b = _rand_number_with_length(base, lb)
        if a <= b:
            a, b = b, a
        c = a - b
        return [a, b, c]
    # sub3
    la = random.randint(3, 5)
    lb = random.randint(3, 5)
    lc = random.randint(3, 5)
    a = _rand_number_with_length(base, la)
    b = _rand_number_with_length(base, lb)
    c = _rand_number_with_length(base, lc)
    if a <= b + c:
        a = a + (b + c) + random.randint(1, base - 1)
    d = a - b - c
    return [a, b, c, d]

def _build_digit_letter_bijection(used_digits):
    # Map each used digit to a unique uppercase letter
    letters_pool = list(string.ascii_uppercase)
    random.shuffle(letters_pool)
    if len(used_digits) > len(letters_pool):
        raise ValueError('Not enough letters for used digits')
    digit_to_letter = {}
    for d, L in zip(sorted(used_digits), letters_pool):
        digit_to_letter[d] = L
    return digit_to_letter

def _numbers_to_words(nums, base, digit_to_letter):
    # Convert integers to words under the bijection
    words = []
    for n in nums:
        digs = _int_to_base_digits(n, base)
        w = _digits_to_word(digs, digit_to_letter)
        words.append(w)
    return words

def _collect_used_digits(nums, base):
    s = set()
    for n in nums:
        digs = _int_to_base_digits(n, base)
        for d in digs:
            s.add(d)
    return s

def _leading_letters(words):
    return sorted({w[0] for w in words if len(w) > 0})

def get_leading_letters(words):
    # Public wrapper for YAML
    return _leading_letters(words)

def _compute_coeffs(tpl):
    if tpl == 'add2':
        return [1, 1, -1]
    if tpl == 'add3':
        return [1, 1, 1, -1]
    if tpl == 'sub2':
        return [1, -1, -1]
    return [1, -1, -1, -1]

def compute_primes(base):
    # Simple sieve for primes in [0, base-1]
    if base <= 2:
        return []
    sieve = [True] * base
    sieve[0] = False
    if base > 1:
        sieve[1] = False
    for p in range(2, int(base ** 0.5) + 1):
        if sieve[p]:
            step = p
            for m in range(p * p, base, step):
                sieve[m] = False
    return [i for i in range(base) if sieve[i]]

def _choose_fixed_pairs(letter_to_digit, count, exclude=None):
    # Choose up to 'count' fixed letter->digit hints, excluding letters in exclude
    exclude = exclude or set()
    fixed_pairs = []
    if count <= 0:
        return fixed_pairs
    pool = [L for L in letter_to_digit.keys() if L not in exclude]
    random.shuffle(pool)
    for L in pool[:count]:
        fixed_pairs.append((L, letter_to_digit[L]))
    return fixed_pairs

def _choose_gt_pairs(letter_to_digit, count, exclude=None):
    # Choose ordered pairs A>B, excluding any letter in exclude
    exclude = exclude or set()
    gt_pairs = []
    if count <= 0:
        return gt_pairs
    letters_all = [L for L in letter_to_digit.keys() if L not in exclude]
    if len(letters_all) < 2:
        return gt_pairs
    tries = 0
    used = set()
    while len(gt_pairs) < count and tries < 100:
        tries += 1
        a, b = random.sample(letters_all, 2)
        key = tuple(sorted([a, b]))
        if key in used:
            continue
        da, db = letter_to_digit[a], letter_to_digit[b]
        gt_pairs.append((a, b) if da > db else (b, a))
        used.add(key)
    return gt_pairs

def choose_sum_pairs(letter_to_digit, count, exclude=None):
    # Return list of (L1, L2, s) meaning assign[L1] + assign[L2] == s, excluding letters in exclude
    exclude = exclude or set()
    pairs = []
    if count <= 0:
        return pairs
    letters_all = [L for L in letter_to_digit.keys() if L not in exclude]
    if len(letters_all) < 2:
        return pairs
    used = set()
    tries = 0
    while len(pairs) < count and tries < 100:
        tries += 1
        L1, L2 = random.sample(letters_all, 2)
        key = tuple(sorted([L1, L2]))
        if key in used:
            continue
        s = letter_to_digit[L1] + letter_to_digit[L2]
        pairs.append((L1, L2, s))
        used.add(key)
    return pairs

def choose_gap_pairs(letter_to_digit, count, exclude=None):
    # Return list of (A, B, g) meaning assign[A] - assign[B] >= g, with g in {1,2}, excluding letters in exclude
    exclude = exclude or set()
    pairs = []
    if count <= 0:
        return pairs
    letters_all = [L for L in letter_to_digit.keys() if L not in exclude]
    if len(letters_all) < 2:
        return pairs
    used = set()
    tries = 0
    while len(pairs) < count and tries < 100:
        tries += 1
        A, B = random.sample(letters_all, 2)
        if A in exclude or B in exclude:
            continue
        key = (A, B)
        if key in used:
            continue
        da, db = letter_to_digit[A], letter_to_digit[B]
        diff = da - db
        if diff >= 1:
            g = random.choice([1, 2]) if diff >= 2 else 1
            pairs.append((A, B, g))
            used.add(key)
        elif db - da >= 1:
            g = random.choice([1, 2]) if (db - da) >= 2 else 1
            pairs.append((B, A, g))
            used.add((B, A))
    return pairs

def choose_subset_hints(letter_to_digit, base, count, leading_letters, exclude=None):
    # Return list of (L, digits_list) meaning assign[L] in digits_list
    # Use primes, low-half, high-half; exclude letters in exclude; exclude 0 for leading letters; ensure >=2 digits
    exclude = exclude or set()
    hints = []
    if count <= 0:
        return hints
    letters_all = [L for L in letter_to_digit.keys() if L not in exclude]
    if not letters_all:
        return hints
    primes = compute_primes(base)
    low_end = base // 2
    high_start = (base + 1) // 2
    low_set = list(range(0, low_end)) if low_end > 0 else []
    high_set = list(range(high_start, base)) if high_start < base else []
    candidates_sets = []
    if primes:
        candidates_sets.append(('primes', primes))
    if low_set:
        candidates_sets.append(('low', low_set))
    if high_set:
        candidates_sets.append(('high', high_set))
    if not candidates_sets:
        return hints
    pool_letters = letters_all[:]
    random.shuffle(pool_letters)
    for L in pool_letters:
        if len(hints) >= count:
            break
        d = letter_to_digit[L]
        viable = [digits for name, digits in candidates_sets if d in digits]
        if not viable:
            continue
        digits_list = list(random.choice(viable))
        if L in leading_letters:
            digits_list = [x for x in digits_list if x != 0]
        digits_list = list(sorted(set(digits_list)))
        if len(digits_list) < 2:
            continue
        hints.append((L, digits_list))
    # Deduplicate by letter
    res = []
    seen = set()
    for (L, digits) in hints:
        if L in seen:
            continue
        res.append((L, list(digits)))
        seen.add(L)
    return res

def _choose_parity_hints(letter_to_digit, words, exclude=None):
    # Choose small sets of even/odd letters, excluding letters in exclude
    exclude = exclude or set()
    letters_all = sorted(letter_to_digit.keys())
    candidates = [L for L in letters_all if L not in exclude]
    even_letters_all = [L for L in candidates if letter_to_digit[L] % 2 == 0]
    odd_letters_all = [L for L in candidates if letter_to_digit[L] % 2 == 1]
    cnt_even = random.choice([0, 1, 2])
    cnt_odd = random.choice([0, 1, 2])
    chosen_even = random.sample(even_letters_all, k=min(cnt_even, len(even_letters_all))) if even_letters_all else []
    avail_odd = [L for L in odd_letters_all if L not in chosen_even]
    chosen_odd = random.sample(avail_odd, k=min(cnt_odd, len(avail_odd))) if avail_odd else []
    return chosen_even, chosen_odd

def _choose_checksum(letter_to_digit, min_k=3, max_k=6):
    # Build a subset checksum: pick a random subset (size in [min_k, max_k], clipped by total letters),
    # weights in {1,2,3}, ensure not all 1's
    letters_all = sorted(letter_to_digit.keys())
    if not letters_all:
        return [], 0
    ub = min(max_k, len(letters_all))
    lb = min(min_k, ub)
    k = random.randint(lb, ub) if ub >= lb and ub > 0 else ub
    chosen = random.sample(letters_all, k=k) if k > 0 else []
    weights = {}
    for L in chosen:
        weights[L] = random.choice([1, 2, 3])
    if chosen and all(w == 1 for w in weights.values()) and len(chosen) >= 2:
        for L in random.sample(chosen, 1):
            weights[L] = 2
    value = sum(weights[L] * letter_to_digit[L] for L in chosen)
    pairs = [(L, weights[L]) for L in chosen]
    return pairs, value

def _choose_affine_pairs(letter_to_digit, max_count=2, exclude=None):
    # Choose up to max_count affine pair equations a*X + b*Y = t with a,b in {1,2,3},
    # excluding letters in exclude; force gcd(a,b)==1 to avoid trivial reduction.
    exclude = exclude or set()
    letters_all = [L for L in letter_to_digit.keys() if L not in exclude]
    res = []
    if len(letters_all) < 2:
        return res
    count = min(max_count, 1)  # at most 1 affine hint to avoid over-strength
    used = set()
    tries = 0
    while len(res) < count and tries < 80:
        tries += 1
        X, Y = random.sample(letters_all, 2)
        key = tuple(sorted([X, Y]))
        if key in used:
            continue
        a = random.choice([1, 2, 3])
        b = random.choice([1, 2, 3])
        if math.gcd(a, b) != 1:
            continue
        t = a * letter_to_digit[X] + b * letter_to_digit[Y]
        res.append((X, Y, a, b, t))
        used.add(key)
    return res

def build_extra_text(even_letters, odd_letters, fixed_pairs, gt_pairs, sum_pairs, gap_pairs, subset_hints, checksum_pairs=None, checksum_value=None, affine_pairs=None):
    parts = []
    if even_letters:
        parts.append('even letters: ' + ','.join(sorted(even_letters)))
    if odd_letters:
        parts.append('odd letters: ' + ','.join(sorted(odd_letters)))
    if fixed_pairs:
        parts.append('fixed letters: ' + ','.join([f'{L}={d}' for (L, d) in fixed_pairs]))
    if gt_pairs:
        parts.append('order: ' + ','.join([f'{a}>{b}' for (a, b) in gt_pairs]))
    if sum_pairs:
        parts.append('sum pairs: ' + ','.join([f'{a}+{b}={s}' for (a, b, s) in sum_pairs]))
    if gap_pairs:
        parts.append('gap pairs: ' + ','.join([f'{a}-{b}>={g}' for (a, b, g) in gap_pairs]))
    if subset_hints:
        parts.append('subset: ' + '; '.join([f'{L} in [{",".join(str(x) for x in digits)}]' for (L, digits) in subset_hints]))
    if checksum_pairs and checksum_value is not None:
        parts.append('checksum: ' + ' + '.join([f'{w}*{L}' for (L, w) in checksum_pairs]) + f' = {checksum_value}')
    if affine_pairs:
        parts.append('affine: ' + '; '.join([f'{a}*{X}+{b}*{Y}={t}' for (X, Y, a, b, t) in affine_pairs]))
    # Always return with explicit prefix
    return 'Additional hints: ' + ('; '.join(parts) if parts else 'none')

def build_story_text(base, text_expr, hint_text, letters, leading_letters):
    # Concise story; single-line with explicit '\n'; no double quotes
    letters_str = '[' + ','.join(letters) + ']'
    lead_letters_str = '[' + ','.join(leading_letters) + ']'
    style = random.choice([0, 1, 2])
    if style == 0:
        lead = f'Cryptarithm under base {base}: letters denote distinct digits from 0 to {base - 1}, and leading letters cannot be zero.'
    elif style == 1:
        lead = f'You are given a letter-digit puzzle in base {base}. Every letter maps to a unique digit in 0..{base - 1}, and leading letters cannot be zero.'
    else:
        lead = f'Base {base} letter-number riddle: assign distinct digits (0..{base - 1}) to letters; leading letters cannot be zero.'
    # Add explicit interpretation sentence
    interp = f'Each word represents a base-{base} number where the same letter always denotes the same digit.'
    core = f'Letters used (alphabetical): {letters_str}. Leading letters: {lead_letters_str}. Equation: {text_expr}.'
    hints = hint_text
    return f'{lead} \\n {interp} \\n {core} \\n {hints}'

def build_answer_guide(letters):
    # Single-line instruction text; example uses first two letters if available, and embeds exact order
    order_str = '[' + ','.join(letters) + ']'
    if len(letters) >= 2:
        ex = f'{letters[0]}:1,{letters[1]}:2'
    elif len(letters) == 1:
        ex = f'{letters[0]}:1'
    else:
        ex = 'A:1'
    return f'Provide the letter-to-digit mapping in the exact order {order_str} as L:digit,L:digit,... with no spaces; example: {ex}'

def gen_cryptarithm_spec(base):
    # Robust generator that guarantees a valid numeric equation, then adds randomized hints
    for _ in range(100):
        tpl, k = _choose_template()
        nums = _gen_numbers_for_template(base, tpl)
        used_digits = _collect_used_digits(nums, base)
        if len(used_digits) > base:
            continue
        digit_to_letter = _build_digit_letter_bijection(used_digits)
        words = _numbers_to_words(nums, base, digit_to_letter)
        coeffs = _compute_coeffs(tpl)
        text_expr = _render_expression(words, coeffs)
        letter_to_digit = {L: d for d, L in digit_to_letter.items()}
        letters_sorted = sorted(letter_to_digit.keys())
        leading_letters = _leading_letters(words)

        # Counts: limit fixed to at most 1, others modest for depth without trivialization
        cnt_fix = random.choice([0, 1])
        cnt_gt = random.choice([0, 1, 2])
        cnt_sum = random.choice([0, 1, 2])
        cnt_gap = random.choice([0, 1])
        cnt_subset = random.choice([0, 1, 2])

        # Exclusions and de-dup
        leading_set = set(leading_letters)
        exclude_letters = set(leading_set)  # fixed may not use leading
        fixed_pairs = _choose_fixed_pairs(letter_to_digit, cnt_fix, exclude=exclude_letters)
        exclude_letters.update([L for (L, _) in fixed_pairs])

        even_letters, odd_letters = _choose_parity_hints(letter_to_digit, words, exclude=exclude_letters)
        exclude_letters.update(even_letters)
        exclude_letters.update(odd_letters)

        gt_pairs = _choose_gt_pairs(letter_to_digit, cnt_gt, exclude=exclude_letters)
        for (a, b) in gt_pairs:
            exclude_letters.add(a)
            exclude_letters.add(b)

        sum_pairs = choose_sum_pairs(letter_to_digit, cnt_sum, exclude=exclude_letters)
        for (L1, L2, _) in sum_pairs:
            exclude_letters.add(L1)
            exclude_letters.add(L2)

        gap_pairs = choose_gap_pairs(letter_to_digit, cnt_gap, exclude=exclude_letters)
        for (A, B, _) in gap_pairs:
            exclude_letters.add(A)
            exclude_letters.add(B)

        subset_hints = choose_subset_hints(letter_to_digit, base, cnt_subset, leading_letters, exclude=exclude_letters)

        # checksum over a subset
        checksum_pairs, checksum_value = _choose_checksum(letter_to_digit)

        # affine pairs: exclude leading + fixed to avoid trivialities; at most 1; gcd(a,b)=1
        exclude_for_affine = set(leading_letters) | {L for (L, _) in fixed_pairs}
        affine_pairs = _choose_affine_pairs(letter_to_digit, max_count=1, exclude=exclude_for_affine)

        hint_text = build_extra_text(
            even_letters, odd_letters, fixed_pairs, gt_pairs, sum_pairs, gap_pairs,
            subset_hints, checksum_pairs=checksum_pairs, checksum_value=checksum_value, affine_pairs=affine_pairs
        )
        story_text = build_story_text(base, text_expr, hint_text, letters_sorted, leading_letters)
        return {
            'words': words,
            'coeffs': coeffs,
            'text_expr': text_expr,
            'even_letters': even_letters,
            'odd_letters': odd_letters,
            'fixed_pairs': fixed_pairs,
            'gt_pairs': gt_pairs,
            'sum_pairs': sum_pairs,
            'gap_pairs': gap_pairs,
            'subset_hints': subset_hints,
            'checksum_pairs': checksum_pairs,
            'checksum_value': checksum_value,
            'affine_pairs': affine_pairs,
            'story_text': story_text
        }

    # Fallback (minimal add2) to keep generation robust (apply same exclusion logic)
    tpl = 'add2'
    nums = _gen_numbers_for_template(base, tpl)
    used_digits = _collect_used_digits(nums, base)
    digit_to_letter = _build_digit_letter_bijection(used_digits)
    words = _numbers_to_words(nums, base, digit_to_letter)
    coeffs = _compute_coeffs(tpl)
    text_expr = _render_expression(words, coeffs)
    letter_to_digit = {L: d for d, L in digit_to_letter.items()}
    letters_sorted = sorted(letter_to_digit.keys())
    leading_letters = _leading_letters(words)

    leading_set = set(leading_letters)
    exclude_letters = set(leading_set)
    fixed_pairs = _choose_fixed_pairs(letter_to_digit, 1, exclude=exclude_letters)
    exclude_letters.update([L for (L, _) in fixed_pairs])
    even_letters, odd_letters = _choose_parity_hints(letter_to_digit, words, exclude=exclude_letters)
    exclude_letters.update(even_letters)
    exclude_letters.update(odd_letters)
    gt_pairs = _choose_gt_pairs(letter_to_digit, 1, exclude=exclude_letters)
    for (a, b) in gt_pairs:
        exclude_letters.add(a)
        exclude_letters.add(b)
    sum_pairs = choose_sum_pairs(letter_to_digit, 1, exclude=exclude_letters)
    for (L1, L2, _) in sum_pairs:
        exclude_letters.add(L1)
        exclude_letters.add(L2)
    gap_pairs = choose_gap_pairs(letter_to_digit, 0, exclude=exclude_letters)
    subset_hints = choose_subset_hints(letter_to_digit, base, 1, leading_letters, exclude=exclude_letters)
    checksum_pairs, checksum_value = _choose_checksum(letter_to_digit)
    exclude_for_affine = set(leading_letters) | {L for (L, _) in fixed_pairs}
    affine_pairs = _choose_affine_pairs(letter_to_digit, max_count=1, exclude=exclude_for_affine)
    hint_text = build_extra_text(
        even_letters, odd_letters, fixed_pairs, gt_pairs, sum_pairs, gap_pairs,
        subset_hints, checksum_pairs=checksum_pairs, checksum_value=checksum_value, affine_pairs=affine_pairs
    )
    story_text = build_story_text(base, text_expr, hint_text, letters_sorted, leading_letters)
    return {
        'words': words,
        'coeffs': coeffs,
        'text_expr': text_expr,
        'even_letters': even_letters,
        'odd_letters': odd_letters,
        'fixed_pairs': fixed_pairs,
        'gt_pairs': gt_pairs,
        'sum_pairs': sum_pairs,
        'gap_pairs': gap_pairs,
        'subset_hints': subset_hints,
        'checksum_pairs': checksum_pairs,
        'checksum_value': checksum_value,
        'affine_pairs': affine_pairs,
        'story_text': story_text
    }