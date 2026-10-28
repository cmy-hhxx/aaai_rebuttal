# dyck_language_errors_5.py
# ============================================================
# High-complexity lazy-bracket puzzle helper library
# ============================================================
import random
import string
from typing import List, Tuple, Dict


# ── Formatting helpers ───────────────────────────────────────
def format_pairs(pairs: List[Tuple[str, str]]) -> str:
    """
    Convert pairs to string like "() , [] , {}".
    Curly braces are doubled for safe f-string embedding.
    """
    res = []
    for o, c in pairs:
        if o == '{':
            res.append('{{}}')
        else:
            res.append(o + c)
    return ', '.join(res)


def escape_braces(s: str) -> str:
    """Escape braces in arbitrary text to survive f-string rendering."""
    return s.replace('{', '{{').replace('}', '}}')


# ── Parser core ──────────────────────────────────────────────
def _parse(text: str,
           normal_pairs: List[Tuple[str, str]],
           wild_open: str = '<') -> Tuple[int, int, int]:
    opens = {o for o, _ in normal_pairs} | {wild_open}
    closes = {c for _, c in normal_pairs}
    match: Dict[str, str] = {c: o for o, c in normal_pairs}

    stack: List[Tuple[str, int]] = []
    err = -1
    unmatched = 0

    for pos, ch in enumerate(text, 1):
        if ch in opens:
            stack.append((ch, pos))
        elif ch in closes:
            if not stack:
                err = pos
                unmatched += 1
                break
            o, _ = stack.pop()
            if o == wild_open:
                continue
            if match[ch] != o:
                err = pos
                unmatched += 2
                break

    if err == -1:
        for ch, p in stack:
            if ch != wild_open:
                unmatched += 1
                if err == -1:
                    err = p
        if unmatched == 0:
            err = -1

    residue = sum(1 for ch, _ in stack if ch == wild_open)
    return err, residue, unmatched


# ── Complexity filter ────────────────────────────────────────
def _complex_enough(vals: Tuple[int, int, int]) -> bool:
    err, res_lazy, unmatch = vals
    return err >= 12 and res_lazy >= 1 and unmatch >= 2


# ── Puzzle generator ─────────────────────────────────────────
def generate_case() -> dict:
    for _ in range(300):
        normal_pool = [('(', ')'), ('[', ']'), ('{', '}')]
        normal_pairs = random.sample(normal_pool, random.randint(2, 3))

        length = random.randint(120, 250)
        extra = random.sample(
            list(set(string.ascii_lowercase + string.digits) - set('()[]{}<>')),
            random.randint(10, 20)
        )
        mandatory = [b for p in normal_pairs for b in p] + ['<']
        char_pool = mandatory + extra
        while len(char_pool) < length:
            char_pool.append(random.choice(mandatory + extra))
        random.shuffle(char_pool)

        # ensure first char not right bracket
        right_set = {c for _, c in normal_pairs}
        if char_pool[0] in right_set:
            for i in range(1, len(char_pool)):
                if char_pool[i] not in right_set:
                    char_pool[0], char_pool[i] = char_pool[i], char_pool[0]
                    break

        script = ''.join(char_pool)
        metrics = _parse(script, normal_pairs)
        if _complex_enough(metrics):
            err, res_lazy, unmatch = metrics
            return {
                'script': script,
                'script_len': length,
                'error_index': err,
                'residue': res_lazy,
                'unmatched_normal': unmatch,
                'normal_pairs': normal_pairs
            }
    raise RuntimeError("Could not generate adequate puzzle")


# ── Verifier ─────────────────────────────────────────────────
def verify_unique(case_data: dict) -> bool:
    metrics = _parse(case_data['script'], case_data['normal_pairs'])
    return metrics == (
        case_data['error_index'],
        case_data['residue'],
        case_data['unmatched_normal']
    ) and _complex_enough(metrics)


# ── Stub for framework compatibility ─────────────────────────
def gen_rulebook_v24(*args, **kwargs):
    return {}