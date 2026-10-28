# dyck_language_reasoning_errors_7.py
import random
import json
import string
from typing import List, Dict, Any, Tuple

def _tokenize_brackets_outside_string(json_str: str) -> List[str]:
    """
    Extract only { } [ ] tokens that are outside quoted strings in the JSON-like text.
    Toggle in_string only when encountering a double quote that is NOT escaped by an odd number of backslashes.
    """
    tokens: List[str] = []
    in_string = False
    i = 0
    while i < len(json_str):
        ch = json_str[i]
        if ch == '"':
            # Count consecutive backslashes before this quote
            j = i - 1
            backslashes = 0
            while j >= 0 and json_str[j] == '\\':
                backslashes += 1
                j -= 1
            # Only flip when quote is not escaped by an odd number of backslashes
            if backslashes % 2 == 0:
                in_string = not in_string
        else:
            if not in_string and ch in '{}[]':
                tokens.append(ch)
        i += 1
    return tokens

def _rand_string_with_possible_brackets(prob_with_brackets: int) -> str:
    """
    Generate a random string. With given probability (0-100),
    embed braces/brackets characters in the string to stress 'ignore inside quotes'.
    """
    length = random.randint(3, 10)
    base_chars = string.ascii_letters + string.digits
    s = ''.join(random.choice(base_chars) for _ in range(length))
    if random.randint(1, 100) <= prob_with_brackets:
        inserts = random.randint(1, 3)
        brs = ['{', '}', '[', ']']
        s_list = list(s)
        for _ in range(inserts):
            pos = random.randint(0, len(s_list))
            s_list.insert(pos, random.choice(brs))
        s = ''.join(s_list)
    return s

def _gen_value(depth: int, max_depth: int, str_prob: int) -> Any:
    """
    Recursively generate a JSON-serializable Python object.
    Mix objects, arrays, numbers, and strings (some with braces/brackets inside).
    """
    if depth >= max_depth:
        if random.random() < 0.5:
            return random.randint(0, 9)
        return _rand_string_with_possible_brackets(str_prob)

    choice = random.random()
    if choice < 0.4:
        obj: Dict[str, Any] = {}
        keys_count = random.randint(0, 3)
        keys_pool = list(string.ascii_lowercase[:12])
        random.shuffle(keys_pool)
        for i in range(keys_count):
            key = keys_pool[i]
            obj[key] = _gen_value(depth + 1, max_depth, str_prob)
        return obj
    elif choice < 0.8:
        arr_len = random.randint(0, 4)
        return [_gen_value(depth + 1, max_depth, str_prob) for _ in range(arr_len)]
    else:
        if random.random() < 0.5:
            return random.randint(0, 9)
        return _rand_string_with_possible_brackets(str_prob)

def _random_json_text(pair_budget: int, min_depth: int, max_depth: int, str_prob: int) -> str:
    """
    Generate a random JSON-like text with roughly controlled structural complexity.
    Try multiple times to hit a bracket count band around 'pair_budget'.
    """
    attempts = 0
    while attempts < 60:
        attempts += 1
        if random.random() < 0.5:
            root = _gen_value(0, max_depth, str_prob)
            if not isinstance(root, (dict, list)):
                root = {'x': root}
        else:
            if random.random() < 0.5:
                root = _gen_value(1, max_depth, str_prob)
                if not isinstance(root, dict):
                    root = {'a': root, 'b': _gen_value(2, max_depth, str_prob)}
            else:
                root = [_gen_value(1, max_depth, str_prob) for _ in range(random.randint(1, 4))]
        text = json.dumps(root, ensure_ascii=False)
        brs = _tokenize_brackets_outside_string(text)
        if len(brs) >= max(4, min_depth * 2) and len(brs) <= max(18, pair_budget * 3):
            return text
    # fallback
    return '{"a":[1,{"b":[]}]}'

def _random_rule() -> Dict[str, Any]:
    """
    Randomize the checking scope and ignore description for the puzzle.
    """
    scope_choice = random.choice(['both', 'curly', 'square'])
    if scope_choice == 'curly':
        checked_set = ['{', '}']
        checked_name = '仅花括号'
    elif scope_choice == 'square':
        checked_set = ['[', ']']
        checked_name = '仅方括号'
    else:
        checked_set = ['{', '}', '[', ']']
        checked_name = '花括号与方括号'

    ignore_desc = random.choice([
        '忽略除待校验括号外的所有符号',
        '忽略逗号“,”、冒号“:”、空格、引号“\\"”与数字等非括号符号'
    ])

    rule = {
        'checked_set': checked_set,
        'checked_name': checked_name,
        'ignore_desc': ignore_desc
    }
    return rule

def _depth_after_tokens(tokens: List[str]) -> List[int]:
    """
    Compute stack depth after each token in tokens, treating any opening as +1 and any closing as -1.
    Depth may go negative if closings exceed openings.
    """
    depth = 0
    out: List[int] = []
    for t in tokens:
        if t in ['{', '[']:
            depth += 1
        elif t in ['}', ']']:
            depth -= 1
        out.append(depth)
    return out

def _choose_wrong_bracket(tok: str, pool: List[str]) -> str:
    """
    Choose a wrong bracket different from 'tok', restricted to 'pool'.
    """
    options = [c for c in pool if c != tok]
    if not options:
        options = [c for c in ['{', '}', '[', ']'] if c != tok]
    return random.choice(options)

def find_error_steps(json_str: str, steps: List[str], rule: Dict[str, Any]) -> List[int]:
    """
    Compute 1-based indices of error steps under a configurable rule.
    - Only validate the bracket tokens in rule['checked_set'].
    - Ignore any non-checked token in steps; '初始化' is skipped.
    - Build expected stream from JSON by extracting only { } [ ] outside quotes,
      then filtering to checked_set.
    - Sequentially compare: mismatch -> record error (do NOT advance expected pointer);
      match -> advance; extra after exhaustion -> error.
    """
    checked_set = set(rule.get('checked_set', ['{', '}', '[', ']']))
    expected_all = _tokenize_brackets_outside_string(json_str)
    expected = [t for t in expected_all if t in checked_set]

    errors: List[int] = []
    pos = 0

    for idx, tok in enumerate(steps):
        step_no = idx + 1
        if tok == '初始化':
            continue
        if tok not in checked_set:
            continue

        if pos >= len(expected):
            errors.append(step_no)
            continue

        if tok == expected[pos]:
            pos += 1
        else:
            errors.append(step_no)

    return errors

def _counted_positions(steps: List[str], checked_set: set) -> List[int]:
    """
    Return step indices (0-based) of tokens that belong to checked_set.
    """
    return [i for i, tok in enumerate(steps) if tok in checked_set]

def compute_failed_checkpoints(json_str: str,
                               steps: List[str],
                               rule: Dict[str, Any],
                               cp_points: List[int],
                               cp_targets: List[int]) -> List[int]:
    """
    Determine which checkpoints fail (actual depth vs target depth).
    - cp_points: list of 1-based step indices of bracket steps (in checked_set).
    - cp_targets: targets aligned by ordinal among counted bracket steps (1..k), derived from the expected sequence depths.
    Implementation:
      - Build counted tokens (only in checked_set) and compute actual depths after each.
      - Map each cp_point to its ordinal among counted positions; compare depth with cp_targets[ordinal-1].
      - If cp_point is not a counted bracket step, ignore it.
      - If ordinal exceeds len(cp_targets), use cp_targets[-1] as fallback target.
    """
    checked_set = set(rule.get('checked_set', ['{', '}', '[', ']']))
    counted_idxs = _counted_positions(steps, checked_set)  # 0-based
    counted_tokens = [steps[i] for i in counted_idxs]
    actual_depths = _depth_after_tokens(counted_tokens)

    failed: List[int] = []
    for cp in cp_points:
        pos0 = cp - 1
        try:
            ordinal = counted_idxs.index(pos0) + 1  # 1-based ordinal among counted bracket steps
        except ValueError:
            continue
        target = cp_targets[ordinal - 1] if ordinal - 1 < len(cp_targets) else cp_targets[-1]
        actual = actual_depths[ordinal - 1]
        if actual != target:
            failed.append(cp)
    return failed

def compute_max_depth(steps: List[str], rule: Dict[str, Any]) -> int:
    """
    Compute maximum stack depth over the counted bracket tokens under the rule.
    Depth starts at 0; +1 for { or [, -1 for } or ].
    Negative depths do not reduce the maximum; return max([0] + depths).
    """
    checked_set = set(rule.get('checked_set', ['{', '}', '[', ']']))
    counted_tokens = [tok for tok in steps if tok in checked_set]
    depths = _depth_after_tokens(counted_tokens)
    return max([0] + depths)

def sort_int_list(lst: List[int]) -> List[int]:
    """
    Return ascending-sorted copy of an integer list.
    """
    return sorted(lst)

def format_steps(steps: List[str]) -> str:
    """
    Return a safe, human-friendly representation of the steps for display.
    Each token is wrapped in single quotes with proper escaping for backslash and single quote.
    Example: '\'初始化\', \']\', \']\', \'"\', \'[\', ...'
    """
    def esc(s: str) -> str:
        return s.replace('\\', '\\\\').replace("'", "\\'")
    return ', '.join([f"'{esc(s)}'" for s in steps])

def gen_instance(pair_budget: int,
                 min_depth: int,
                 max_depth: int,
                 str_prob: int,
                 noise_between: int,
                 target_errors: int) -> Dict[str, Any]:
    """
    Build one instance with randomized rule and error composition:
    - Randomize checking rule (scope of brackets, ignore description).
    - Generate random JSON text and its expected bracket stream filtered by checked_set.
    - Build steps: '初始化' + noise + bracket tokens (+ optional tail noise).
    - Inject exactly 'target_errors' errors via flips and extras.
    - Sample checkpoints from counted positions; derive targets from expected depths (aligned by ordinal).
    - Validate:
        * error count equals target_errors
        * checkpoint failures count cp_fail_num >= 1
        * set of checkpoint failures != set of error steps (avoid trivial overlap)
    Returns dict with fields: json, steps, rule, cp_points, cp_targets, cp_fail_num.
    """
    min_depth = max(1, min_depth)
    max_depth = max(min_depth + 1, max_depth)
    target_errors = max(1, target_errors)

    attempts = 0
    while attempts < 200:
        attempts += 1

        rule = _random_rule()
        checked_set_list = list(rule['checked_set'])
        checked_set = set(checked_set_list)

        json_text = _random_json_text(pair_budget, min_depth, max_depth, str_prob)
        expected_full = _tokenize_brackets_outside_string(json_text)
        expected = [t for t in expected_full if t in checked_set]
        if len(expected) < max(2, min_depth):
            continue

        steps: List[str] = ['初始化']
        bracket_positions: List[int] = []

        # Build steps with optional noise between brackets
        for tok in expected:
            if noise_between > 0:
                k = random.randint(0, noise_between)
                generic_noise = list('0123456789') + [':', ',', '"']
                if random.random() < 0.5:
                    generic_noise += list(string.ascii_lowercase[:6])
                for _ in range(k):
                    steps.append(random.choice(generic_noise))
            steps.append(tok)
            bracket_positions.append(len(steps) - 1)

        # Optional tail noise
        if noise_between > 0 and random.random() < 0.7:
            tail_k = random.randint(0, noise_between)
            tail_noise = list('0123456789') + [':', ',', '"']
            if random.random() < 0.5:
                tail_noise += list(string.ascii_lowercase[:6])
            for _ in range(tail_k):
                steps.append(random.choice(tail_noise))

        if len(bracket_positions) == 0:
            continue

        # Plan error composition: flips + extras
        max_flips = min(target_errors, len(bracket_positions))
        flip_count = random.randint(max(0, target_errors - 2), max_flips)
        extra_count = target_errors - flip_count

        # Flip some existing checked brackets to wrong ones
        if flip_count > 0:
            flip_positions = random.sample(bracket_positions, flip_count)
            for pos in flip_positions:
                orig = steps[pos]
                steps[pos] = _choose_wrong_bracket(orig, checked_set_list)

        # Inject extra checked brackets at random positions
        if extra_count > 0:
            for _ in range(extra_count):
                insert_tok = random.choice(checked_set_list)
                insert_idx = random.randint(1, len(steps))
                steps.insert(insert_idx, insert_tok)

        # Validate error count
        errors = find_error_steps(json_text, steps, rule)
        if len(errors) != target_errors:
            continue

        counted_idxs = _counted_positions(steps, checked_set)  # 0-based
        if len(counted_idxs) < 2:
            continue

        # Choose checkpoints only from counted bracket steps that map within expected length
        usable_counted = [i for i in counted_idxs if counted_idxs.index(i) < len(expected)]
        if len(usable_counted) < 2:
            continue

        cp_size_min = 2
        cp_size_max = min(5, len(usable_counted))
        cp_size = random.randint(cp_size_min, cp_size_max)
        cp_sample = sorted(random.sample(usable_counted, cp_size))
        cp_points = [idx + 1 for idx in cp_sample]  # 1-based step indices (bracket steps)

        # Targets derived from expected depths by ordinal among counted bracket steps
        expected_depths = _depth_after_tokens(expected)
        ordinals = []
        for step_idx0 in cp_sample:
            try:
                ordinals.append(counted_idxs.index(step_idx0) + 1)
            except ValueError:
                ordinals.append(1)
        cp_targets = [expected_depths[o - 1] if (o - 1) < len(expected_depths) else expected_depths[-1] for o in ordinals]

        cp_failed = compute_failed_checkpoints(json_text, steps, rule, cp_points, cp_targets)
        cp_fail_num = len(cp_failed)
        if cp_fail_num < 1:
            continue
        if set(cp_failed) == set(errors):
            continue

        return {
            'json': json_text,
            'steps': steps,
            'rule': rule,
            'cp_points': cp_points,
            'cp_targets': cp_targets,
            'cp_fail_num': cp_fail_num
        }

    # Fallback construction if random attempts fail
    rule = _random_rule()
    checked = set(rule['checked_set'])
    json_text = '{"a":[1,{"b":[]}]}'
    expected_full = _tokenize_brackets_outside_string(json_text)
    expected = [t for t in expected_full if t in checked]
    steps = ['初始化']
    for tok in expected:
        steps += [':', ',', '"', tok]
    # Flip the first checked token to ensure at least one error
    for i, tok in enumerate(steps):
        if tok in checked:
            steps[i] = _choose_wrong_bracket(tok, list(checked) if len(checked) >= 2 else ['{', '}', '[', ']'])
            break
    counted = _counted_positions(steps, checked)
    if len(counted) >= 2:
        cp_points = [counted[0] + 1, counted[1] + 1]
    else:
        cp_points = [2]
    expected_depths = _depth_after_tokens(expected)
    cp_targets = expected_depths[:len(cp_points)] if expected_depths else [0] * len(cp_points)
    cp_fail_num = len(compute_failed_checkpoints(json_text, steps, rule, cp_points, cp_targets))
    return {
        'json': json_text,
        'steps': steps,
        'rule': rule,
        'cp_points': cp_points,
        'cp_targets': cp_targets,
        'cp_fail_num': cp_fail_num
    }

def compute_all_answers(json_str: str,
                        steps: List[str],
                        rule: Dict[str, Any],
                        cp_points: List[int],
                        cp_targets: List[int]) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
    """
    Compute the three required answers and package them into one tuple:
    ((error_steps_sorted_tuple), (failed_checkpoints_sorted_tuple), max_depth_int)
    """
    q1 = sort_int_list(find_error_steps(json_str, steps, rule))
    q2 = sort_int_list(compute_failed_checkpoints(json_str, steps, rule, cp_points, cp_targets))
    q3 = compute_max_depth(steps, rule)
    return (tuple(q1), tuple(q2), q3)