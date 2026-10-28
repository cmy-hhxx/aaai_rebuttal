import sys, json, random, itertools
from typing import Dict, List, Tuple, Optional, Any

# We will generate alphametic addition puzzles in base 10:
#   WORD1 + WORD2 = WORD3
# Each letter is a distinct digit 0-9, leading letters of multi-digit words != 0.
# We construct puzzles from a hidden digit assignment, then solve and ensure unique solution.

def solve_alphametic_add(word1: str, word2: str, word3: str) -> List[Dict[str, int]]:
    letters = sorted(set(word1 + word2 + word3))
    if len(letters) > 10:
        return []
    leading = {word1[0], word2[0], word3[0]}
    # Prepare column-wise constraints for fast backtracking
    w1 = word1[::-1]
    w2 = word2[::-1]
    w3 = word3[::-1]
    L = max(len(w1), len(w2), len(w3))

    # For each column, the letters involved (or None) at that position
    cols = []
    for i in range(L):
        a = w1[i] if i < len(w1) else None
        b = w2[i] if i < len(w2) else None
        c = w3[i] if i < len(w3) else None
        cols.append((a, b, c))

    # Order letters by heuristic: frequency and leading importance
    freq = {ch: 0 for ch in letters}
    for ch in word1 + word2 + word3:
        freq[ch] += 1
    # Some tie-breakers: leading letters earlier
    def letter_key(ch):
        return (-freq[ch], ch not in leading, ch)

    # But for column backtracking, we will assign as needed per column.
    # We'll do recursive column solving with carry, assigning digits lazily.
    solutions = []
    assign: Dict[str, int] = {}
    used = [False]*10

    def can_assign(ch: str, d: int) -> bool:
        if used[d]:
            return False
        if d == 0 and ch in leading and (len(word1) > 1 or len(word2) > 1 or len(word3) > 1):
            # leading letter of its word cannot be 0 if that word has multiple digits
            if (ch == word1[0] and len(word1) > 1) or (ch == word2[0] and len(word2) > 1) or (ch == word3[0] and len(word3) > 1):
                return False
        return True

    def get_digit(ch: Optional[str]) -> Optional[int]:
        if ch is None:
            return 0
        return assign.get(ch)

    # Try digits for a letter with pruning
    def try_assign_letter(ch: str):
        for d in range(10):
            if can_assign(ch, d):
                yield d

    def rec(col_idx: int, carry: int):
        if col_idx == L:
            if carry == 0:
                solutions.append(dict(assign))
            return

        a, b, c = cols[col_idx]

        # Fetch current assigned digits if any
        da = None if a is None else assign.get(a)
        db = None if b is None else assign.get(b)
        dc = None if c is None else assign.get(c)

        # We need (da + db + carry) % 10 == dc and next_carry = //10
        # We'll handle cases by branching only on unassigned letters in this column.

        # Build list of letters in this column that are unassigned
        unassigned = []
        for ch in (a, b, c):
            if ch is not None and ch not in assign and ch not in unassigned:
                unassigned.append(ch)

        # A bit of ordering: try more constrained letters first (leading, freq)
        unassigned.sort(key=letter_key)

        def proceed():
            # compute after assignments
            va = 0 if a is None else assign[a]
            vb = 0 if b is None else assign[b]
            vc = 0 if c is None else assign[c]
            s = va + vb + carry
            if s % 10 != vc:
                return
            rec(col_idx + 1, s // 10)

        if not unassigned:
            proceed()
            return

        # Backtracking assign unassigned letters one by one
        def assign_rec(i: int):
            if i == len(unassigned):
                proceed()
                return
            ch = unassigned[i]
            for d in try_assign_letter(ch):
                assign[ch] = d
                used[d] = True
                # Early pruning: if c is assigned and a,b assigned enough, check modular constraint partially
                # We can do a quick check when possible:
                # If after assigning some letters, the equation might already be impossible.
                # Implement a conservative prune:
                ok = True
                # If all of a,b,c in this column are assigned, check now
                if (a is None or a in assign) and (b is None or b in assign) and (c is None or c in assign):
                    va = 0 if a is None else assign[a]
                    vb = 0 if b is None else assign[b]
                    vc = 0 if c is None else assign[c]
                    s = va + vb + carry
                    if s % 10 != vc:
                        ok = False
                if ok:
                    assign_rec(i + 1)
                used[d] = False
                del assign[ch]

        assign_rec(0)

    # Extra pruning: leading letters cannot be 0 handled in can_assign
    rec(0, 0)
    return solutions

def word_value(word: str, mapping: Dict[str, int]) -> int:
    return int(''.join(str(mapping[ch]) for ch in word))

def format_answer(mapping: Dict[str, int]) -> str:
    # format as [[A=1,B=2,...]] with letters in alphabetical order
    items = [f"{ch}={mapping[ch]}" for ch in sorted(mapping.keys())]
    return "[[" + ",".join(items) + "]]"

def build_explanation(word1: str, word2: str, word3: str, mapping: Dict[str, int]) -> str:
    v1 = word_value(word1, mapping)
    v2 = word_value(word2, mapping)
    v3 = word_value(word3, mapping)
    # Column-wise check
    rev1, rev2, rev3 = word1[::-1], word2[::-1], word3[::-1]
    L = max(len(word1), len(word2), len(word3))
    carry = 0
    lines = []
    lines.append(f"将字母替换为数字后：{word1}={v1}, {word2}={v2}, {word3}={v3}。")
    lines.append(f"验证加法：{v1}+{v2}={v1+v2}，确实等于 {v3}。")
    lines.append("逐列验算（从个位到高位，写出该列和与进位）：")
    for i in range(L):
        a = rev1[i] if i < len(rev1) else None
        b = rev2[i] if i < len(rev2) else None
        c = rev3[i] if i < len(rev3) else None
        da = mapping[a] if a is not None else 0
        db = mapping[b] if b is not None else 0
        dc = mapping[c] if c is not None else 0
        s = da + db + carry
        lines.append(f"第{i+1}列：{a or '空'}({da}) + {b or '空'}({db}) + 进位{carry} = {s}，个位为 {s%10} 对应 {c or '空'}({dc})，新进位为 {s//10}。")
        carry = s // 10
    lines.append("所有列均满足，且不同字母对应不同数字，首字母不为0。")
    return "\n".join(lines)

def random_word(rng: random.Random, letters: List[str], min_len: int, max_len: int) -> str:
    L = rng.randint(min_len, max_len)
    return "".join(rng.choice(letters) for _ in range(L))

def generate_instance(rng: random.Random) -> Tuple[str, str, str, Dict[str, int], List[Dict[str, int]]]:
    # We generate by picking a set of letters and a random injective digit mapping, then
    # constructing word1, word2 and letting word3 be their sum encoded in letters.
    # But we need words in letters; easiest is to choose word patterns, map to digits, compute sum,
    # then ensure sum digits correspond to existing letters consistently (so we must design patterns
    # that allow sum to reuse letters). This is hard.
    #
    # Alternative: generate directly as an alphametic by choosing words (letters),
    # then solve it; accept only those with unique solution. This is feasible with bounded sizes.

    # Family templates to increase diversity:
    # - lengths 3-5 + 3-5 = 4-6
    # - allow repeated letters within a word
    # - ensure total distinct letters <= 10
    templates = [
        (3, 3, 4),
        (4, 4, 5),
        (4, 3, 5),
        (5, 4, 6),
        (3, 4, 5),
    ]

    # We will sample an alphabet size between 6 and 10
    for _ in range(4000):
        t = rng.choice(templates)
        len1, len2, len3 = t
        k = rng.randint(6, 10)
        # Choose k distinct uppercase letters excluding confusing ones optionally
        pool = [chr(ord('A') + i) for i in range(26)]
        rng.shuffle(pool)
        alphabet = pool[:k]

        w1 = random_word(rng, alphabet, len1, len1)
        w2 = random_word(rng, alphabet, len2, len2)
        w3 = random_word(rng, alphabet, len3, len3)

        # Ensure leading letters distinct sometimes to avoid trivial conflicts
        if w1[0] == w2[0] and rng.random() < 0.7:
            continue
        # Ensure total distinct letters <= 10
        letters = set(w1 + w2 + w3)
        if len(letters) > 10:
            continue
        # Must have at least 6 distinct letters for interest
        if len(letters) < 6:
            continue

        sols = solve_alphametic_add(w1, w2, w3)
        if len(sols) != 1:
            continue
        sol = sols[0]

        # Cross-check by brute forcing all permutations if small enough? Too expensive.
        # Instead, verify numeric equality and constraints directly:
        v1 = word_value(w1, sol)
        v2 = word_value(w2, sol)
        v3 = word_value(w3, sol)
        if v1 + v2 != v3:
            continue
        # Leading zero check:
        if (len(w1) > 1 and sol[w1[0]] == 0) or (len(w2) > 1 and sol[w2[0]] == 0) or (len(w3) > 1 and sol[w3[0]] == 0):
            continue
        # Distinct digits:
        if len(set(sol.values())) != len(sol):
            continue

        return w1, w2, w3, sol, sols

    raise RuntimeError("生成失败：在限定次数内未找到唯一解的字母算式。请更换 seed 或降低 target_count。")

def render_problem_zh(word1: str, word2: str, word3: str) -> str:
    return (
        "你需要解一个字母算式（Alphametic）：每个字母代表一个0-9的数字，且不同字母不能代表同一个数字；"
        "任意多位数的首字母不能为0。\n\n"
        f"题目：{word1}+{word2}={word3}\n\n"
        "请按如下格式给出答案，并用双层方括号包裹：[[A=1,B=2,...]]"
    )

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()

    attempts = 0
    max_attempts = 20000

    while len(results) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"生成失败：已尝试 {attempts} 次但仅生成 {len(results)}/{count} 题。")
        w1, w2, w3, sol, _ = generate_instance(rng)
        key = (w1, w2, w3)
        if key in seen:
            continue
        seen.add(key)

        problem = render_problem_zh(w1, w2, w3)
        answer = format_answer(sol)
        explanation = build_explanation(w1, w2, w3, sol)

        if not problem.strip() or not isinstance(answer, str) or not answer.startswith("[["):
            continue

        results.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise