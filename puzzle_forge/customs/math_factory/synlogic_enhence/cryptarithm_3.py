# cryptarithm_5.py
# Utility functions and generators for generalized alphametic puzzles

from z3 import Or, And
import random
import string

# ----------------------------
# Core numeric construction
# ----------------------------
def make_number(digits):
    """
    Build a base-10 number from a list of z3 Int digits [d1, d2, ..., dn].
    Returns the z3 expression: d1*10^(n-1) + d2*10^(n-2) + ... + dn.
    This is linear in the z3 Int variables (coefficients are constants).
    """
    n = len(digits)
    total = 0
    for i, d in enumerate(digits):
        total += d * (10 ** (n - 1 - i))
    return total

def in_set(x, values):
    """
    Constrain that x equals one of the provided concrete integers.
    Returns Or(x == v for v in values).
    """
    return Or(*[x == v for v in values])

# ----------------------------
# Random helpers for YAML
# ----------------------------
def alphabet_pool(n):
    """
    Return a list of n distinct uppercase single-letter symbols (e.g., ['S','E','N',...]).
    If n > 26, it clips to 26 letters (A..Z).
    """
    n = max(1, min(int(n), 26))
    letters = list(string.ascii_uppercase)
    random.shuffle(letters)
    return letters[:n]

def random_parity():
    """
    Return 'even' or 'odd' randomly.
    """
    return 'even' if random.choice([True, False]) else 'odd'

# ----------------------------
# Parity utilities
# ----------------------------
def sum_has_parity(dlist, parity_str):
    """
    Constrain that the sum of given digits has required parity ('even' or 'odd'),
    by enumerating all feasible totals consistent with that parity.
    """
    total = 0
    for d in dlist:
        total = total + d
    n = len(dlist)
    max_sum = 9 * n
    offset = 0 if parity_str == 'even' else 1
    targets = list(range(offset, max_sum + 1, 2))
    if not targets:
        return True
    return Or(*[total == e for e in targets])

# Bridge functions for external synthesizers
def even_sum(dlist):
    """
    External bridge: enforce that the sum of digits in dlist is even.
    """
    return sum_has_parity(dlist, 'even')

def odd_sum(dlist):
    """
    External bridge: enforce that the sum of digits in dlist is odd.
    """
    return sum_has_parity(dlist, 'odd')

# ----------------------------
# Template generators (structure)
# ----------------------------
def pick_result_length(add_lengths):
    """
    Choose result length as either max(add_lengths) or max(add_lengths)+1 randomly.
    """
    m = max(add_lengths) if add_lengths else 3
    return m if random.choice([True, False]) else (m + 1)

def gen_cryptarithm_words(letter_pool, add_num, add_lengths, res_length):
    """
    Generate a list of words (each is a list of uppercase letters) for an alphametic:
    - There are add_num addends and one result word (total add_num + 1 words).
    - Leading letters are distinct.
    - Letters are chosen from letter_pool (a list of single uppercase letters).
    Mapping is consistent across all words by construction (same symbol set).
    """
    words = []
    total_words = add_num + 1
    pool = list(letter_pool)
    if len(pool) < total_words:
        # extend with remaining alphabet if needed
        extra = [ch for ch in string.ascii_uppercase if ch not in pool]
        pool.extend(extra)
    # distinct leading letters
    lead_letters = random.sample(pool, total_words)
    # build addend words
    for i in range(add_num):
        L = add_lengths[i] if i < len(add_lengths) else random.randint(3, 6)
        w = [lead_letters[i]]
        for _ in range(L - 1):
            w.append(random.choice(pool))
        words.append(w)
    # build result word
    w = [lead_letters[-1]]
    for _ in range(res_length - 1):
        w.append(random.choice(pool))
    words.append(w)
    return words

def collect_used_letters(words):
    """
    Return a list of distinct letters used in 'words', preserving first occurrence order.
    """
    seen = set()
    ordered = []
    for w in words:
        for ch in w:
            if ch not in seen:
                seen.add(ch)
                ordered.append(ch)
    return ordered

def get_leading_letters(words):
    """
    Return a list of leading letters for each word in order.
    """
    leads = []
    for w in words:
        if w:
            leads.append(w[0])
    return leads

def word_to_string(w):
    """
    Convert a list of letters to a compact word string.
    """
    return ''.join(w)

def compute_max_len(add_lengths, res_length):
    """
    Compute the maximum column length for column-wise constraints.
    Equal to max(max(add_lengths), res_length).
    """
    return max(max(add_lengths) if add_lengths else 3, res_length)

# ----------------------------
# Clue generators and constraints
# ----------------------------
def gen_parity_clues(used_letters, k):
    """
    Generate k parity clues: [(letter, 'even'/'odd'), ...], letters distinct.
    """
    pool = list(used_letters)
    if not pool or k <= 0:
        return []
    k = max(0, min(k, len(pool)))
    picks = random.sample(pool, k)
    clues = []
    for ch in picks:
        clues.append((ch, 'even' if random.choice([True, False]) else 'odd'))
    return clues

def pick_lead_pair(lead_letters):
    """
    Pick an inequality between two distinct leading letters.
    Returns a tuple (L1, op, L2) where op is '>' or '<', or None if insufficient leads.
    """
    if len(lead_letters) < 2:
        return None
    a, b = random.sample(list(lead_letters), 2)
    op = '>' if random.choice([True, False]) else '<'
    return (a, op, b)

def gen_digit_band_clues(used_letters, k):
    """
    Generate k digit-band clues: [(letter, 'low'/'high'), ...].
    low -> digits [0,1,2,3,4]; high -> digits [5,6,7,8,9]
    """
    pool = list(used_letters)
    if not pool or k <= 0:
        return []
    k = max(0, min(k, len(pool)))
    picks = random.sample(pool, k)
    clues = []
    for ch in picks:
        clues.append((ch, 'low' if random.choice([True, False]) else 'high'))
    return clues

def digit_band_constraint(d, band_clues):
    """
    Constrain band clues: low in [0..4], high in [5..9].
    """
    if not band_clues:
        return True
    clauses = []
    for ch, band in band_clues:
        if band == 'low':
            clauses.append(in_set(d[ch], [0, 1, 2, 3, 4]))
        else:
            clauses.append(in_set(d[ch], [5, 6, 7, 8, 9]))
    return And(*clauses) if clauses else True

def gen_letter_ineqs(used_letters, k):
    """
    Generate k inequality pairs among letters: [(A, '>', B), ...] or '<', all A!=B.
    """
    pool = list(used_letters)
    if len(pool) < 2 or k <= 0:
        return []
    pairs = []
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            pairs.append((pool[i], pool[j]))
    if not pairs:
        return []
    k = max(0, min(k, len(pairs)))
    chosen = random.sample(pairs, k)
    res = []
    for a, b in chosen:
        op = '>' if random.choice([True, False]) else '<'
        if random.choice([True, False]):
            res.append((a, op, b))
        else:
            res.append((b, '<' if op == '>' else '>', a))
    return res

def letter_ineq_constraint(d, ineqs):
    """
    Build conjunction of letter inequalities.
    """
    if not ineqs:
        return True
    clauses = []
    for a, op, b in ineqs:
        if op == '>':
            clauses.append(d[a] > d[b])
        else:
            clauses.append(d[a] < d[b])
    return And(*clauses) if clauses else True

def gen_add_parity_clues(add_words, k):
    """
    Generate k parity clues on addend words: [(index, 'even'/'odd'), ...].
    """
    n = len(add_words)
    if n == 0 or k <= 0:
        return []
    idx_pool = list(range(n))
    k = max(0, min(k, n))
    picks = random.sample(idx_pool, k)
    clues = []
    for i in picks:
        clues.append((i, 'even' if random.choice([True, False]) else 'odd'))
    return clues

def add_parity_constraint(d, add_words, clues):
    """
    Apply parity constraints on selected addend words.
    """
    if not clues:
        return True
    clauses = []
    for i, p in clues:
        digits = [d[ch] for ch in add_words[i]]
        clauses.append(sum_has_parity(digits, p))
    return And(*clauses) if clauses else True

# ----------------------------
# Column-wise carry constraints and clues
# ----------------------------
def column_addition_constraints(d, add_words, result_word, carry, add_num):
    """
    Column-wise addition with carries:
    - carry[0] == 0
    - For each column i (0 = units/rightmost), S_i = carry[i] + sum(addend digits at column i)
      If i < last, then S_i == result_digit_i + 10*carry[i+1]
      Else            S_i == result_digit_i
    - Carry bounds: 0 <= carry[i] <= add_num - 1
    """
    Lr = len(result_word)
    clauses = []
    # carry-in to units is zero
    clauses.append(carry[0] == 0)
    # per-column equations
    for i in range(Lr):
        S = carry[i]
        for w in add_words:
            idx = len(w) - 1 - i
            if idx >= 0:
                S = S + d[w[idx]]
        r_digit = d[result_word[Lr - 1 - i]]
        if i < Lr - 1:
            clauses.append(S == r_digit + 10 * carry[i + 1])
        else:
            clauses.append(S == r_digit)
    # carry bounds
    for i in range(Lr):
        clauses.append(And(carry[i] >= 0, carry[i] <= add_num - 1))
    return And(*clauses) if clauses else True

def gen_carry_clues(max_len, add_num, k):
    """
    Generate k carry clues: [(col_index, value), ...], with distinct columns.
    IMPORTANT: avoid column 0 (units) since carry[0] == 0 is enforced by the model and would be a trivial clue.
    Columns are chosen from 1..max_len-1. If that range is empty, no clues are generated.
    Values are small: 0..min(add_num-1, 2).
    """
    if max_len <= 1 or k <= 0:
        return []
    # candidate columns exclude 0
    cols = list(range(1, max_len))
    if not cols:
        return []
    k = max(0, min(k, len(cols)))
    picks = random.sample(cols, k)
    vmax = min(add_num - 1, 2)
    clues = []
    for c in picks:
        clues.append((c, random.randint(0, vmax)))
    return clues

def carry_clue_constraint(carry, clues):
    """
    Fix selected carry columns to provided values.
    """
    if not clues:
        return True
    clauses = []
    for c, v in clues:
        clauses.append(carry[c] == v)
    return And(*clauses) if clauses else True

# ----------------------------
# Pair sum and pair difference clues
# ----------------------------
def gen_pair_sum_clues(used_letters, k):
    """
    Generate k sum clues: [(A, B, T), ...] with T in {8, 9, 10}.
    """
    pool = list(used_letters)
    if len(pool) < 2 or k <= 0:
        return []
    pairs = []
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            pairs.append((pool[i], pool[j]))
    if not pairs:
        return []
    k = max(0, min(k, len(pairs)))
    chosen = random.sample(pairs, k)
    targets = [8, 9, 10]
    res = []
    for a, b in chosen:
        res.append((a, b, random.choice(targets)))
    return res

def pair_sum_constraint(d, clues):
    """
    Enforce A + B == T for each clue.
    """
    if not clues:
        return True
    clauses = []
    for a, b, t in clues:
        clauses.append(d[a] + d[b] == t)
    return And(*clauses) if clauses else True

def gen_pair_diff_clues(used_letters, k):
    """
    Generate k difference clues: [(A, B, c, dir), ...], where dir in {'forward','reverse'}:
    forward: A == B + c
    reverse: B == A + c
    c in {1,2,3}
    """
    pool = list(used_letters)
    if len(pool) < 2 or k <= 0:
        return []
    pairs = []
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            pairs.append((pool[i], pool[j]))
    if not pairs:
        return []
    k = max(0, min(k, len(pairs)))
    chosen = random.sample(pairs, k)
    res = []
    for a, b in chosen:
        c = random.choice([1, 2, 3])
        dirflag = 'forward' if random.choice([True, False]) else 'reverse'
        res.append((a, b, c, dirflag))
    return res

def pair_diff_constraint(d, clues):
    """
    Enforce A == B + c (forward) or B == A + c (reverse).
    """
    if not clues:
        return True
    clauses = []
    for a, b, c, dirflag in clues:
        if dirflag == 'forward':
            clauses.append(d[a] == d[b] + c)
        else:
            clauses.append(d[b] == d[a] + c)
    return And(*clauses) if clauses else True

# ----------------------------
# Anchor prime clue
# ----------------------------
def pick_anchor(used_letters):
    """
    Pick a random anchor letter from used_letters, or None if empty.
    """
    return random.choice(list(used_letters)) if used_letters else None

def anchor_prime_constraint(d, anchor_letter):
    """
    Constrain the anchor letter to be a prime digit: 2, 3, 5, or 7.
    """
    if not anchor_letter:
        return True
    return in_set(d[anchor_letter], [2, 3, 5, 7])

# ----------------------------
# Text renderer: unify all clues into one line
# ----------------------------
def build_clue_text(parity_clues, lead_pair, use_result_sum_parity, parity_str,
                    result_word_str, extra_letter_ineqs, digit_band_clues,
                    add_parity_clues, add_word_strs,
                    pair_sum_clues, pair_diff_clues, carry_clues,
                    anchor_letter, use_anchor_prime):
    """
    Build a human-readable text for all clues, joined by '; '.
    Includes:
      - Letter parity clues: X is even/odd digit
      - Leading letter inequality: A > B or A < B
      - Result word digit-sum parity: digit sum of RESULT is even/odd
      - Extra letter inequalities: A > B / A < B
      - Digit band clues: X in [0-4] or [5-9]
      - Addend word digit-sum parity: digit sum of WORD is even/odd
      - Pair sum clues: A + B = T
      - Pair diff clues: A = B + c or B = A + c
      - Anchor prime clue: only if use_anchor_prime is True
      - Carry clues: carry into column k = v (units/rightmost column is 0)
    """
    parts = []
    if parity_clues:
        parts.append('; '.join([f"{ch} is {p} digit" for ch, p in parity_clues]))
    if lead_pair:
        parts.append(f"{lead_pair[0]} {lead_pair[1]} {lead_pair[2]}")
    if use_result_sum_parity and parity_str in ('even', 'odd'):
        parts.append(f"digit sum of {result_word_str} is {parity_str}")
    if extra_letter_ineqs:
        parts.append('; '.join([f"{a} {op} {b}" for (a, op, b) in extra_letter_ineqs]))
    if digit_band_clues:
        parts.append('; '.join([f"{ch} in {'[0-4]' if band=='low' else '[5-9]'}" for ch, band in digit_band_clues]))
    if add_parity_clues and add_word_strs:
        segs = []
        for i, p in add_parity_clues:
            if 0 <= i < len(add_word_strs):
                segs.append(f"digit sum of {add_word_strs[i]} is {p}")
        if segs:
            parts.append('; '.join(segs))
    if pair_sum_clues:
        parts.append('; '.join([f"{a} + {b} = {t}" for (a, b, t) in pair_sum_clues]))
    if pair_diff_clues:
        ph = []
        for (a, b, c, dirflag) in pair_diff_clues:
            if dirflag == 'forward':
                ph.append(f"{a} = {b} + {c}")
            else:
                ph.append(f"{b} = {a} + {c}")
        if ph:
            parts.append('; '.join(ph))
    if use_anchor_prime and anchor_letter:
        parts.append(f"{anchor_letter} is a prime digit (2,3,5,7)")
    if carry_clues:
        parts.append('; '.join([f"carry into column {col} = {val}" for (col, val) in carry_clues]))
    return '; '.join([p for p in parts if p])

def parity_constraint(d, parity_clues):
    """
    Build a conjunction for parity clues on mapping dict 'd'.
    """
    if not parity_clues:
        return True
    clauses = []
    for ch, p in parity_clues:
        if p == 'even':
            clauses.append(in_set(d[ch], [0, 2, 4, 6, 8]))
        else:
            clauses.append(in_set(d[ch], [1, 3, 5, 7, 9]))
    return And(*clauses) if clauses else True

def lead_ineq_constraint(d, lead_pair):
    """
    Build inequality constraint for two leading letters, or return True if None.
    """
    if not lead_pair or len(lead_pair) != 3:
        return True
    a, op, b = lead_pair
    if op == '>':
        return d[a] > d[b]
    else:
        return d[a] < d[b]

def result_sum_parity_constraint(d, result_word, parity_str):
    """
    Constrain the digit sum of the result word to be even/odd.
    """
    digits = [d[ch] for ch in result_word]
    return sum_has_parity(digits, parity_str)

# --------------------------------------------------------------------
# Bridge functions expected by some synthesizer pipelines.
# These are lightweight wrappers to avoid ImportError.
# --------------------------------------------------------------------
def function_1(*args, **kwargs):
    return True

def function_2(*args, **kwargs):
    return True