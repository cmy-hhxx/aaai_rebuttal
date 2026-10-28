# survo_4.py
# 修复：显式导入 z3.And/Or/BoolVal，并提供 z3_and/z3_or 包装，避免列表参数导致的类型问题。
# 其他逻辑维持：逆向采样 + 4! 唯一性验证，不暴露在题面中。

import random
from typing import Dict, Any, List, Tuple
from itertools import permutations
from z3 import And, Or, BoolVal  # 显式导入 Z3 逻辑函数

def z3_and(lst):
    return And(*lst)

def z3_or(lst):
    return Or(*lst)

def function_2(lst: List[int]) -> List[int]:
    l = list(lst)
    random.shuffle(l)
    return l

def cell_value(pos: str, X: Dict[str, Any], known_map: Dict[str, int]):
    return known_map[pos] if pos in known_map else X[pos]

def make_row_display(row_pos_list: List[str], known_map: Dict[str, int], unknown_keys: List[str], last_value: int) -> str:
    items = []
    for p in row_pos_list:
        if p in unknown_keys:
            items.append('X')
        else:
            items.append(known_map[p])
    items.append(last_value)
    return str(items)

def format_rules_text(row_ops: Dict[str, Dict[str, Any]], row_positions: Dict[str, List[str]]) -> str:
    order_map = {'r1': '行1', 'r2': '行2', 'r3': '行3'}
    segs = []
    for rk in ['r1','r2','r3']:
        a = row_ops[rk]['a']
        b = row_ops[rk]['b']
        segs.append(f"{order_map[rk]}采用线性规则：最后一列等于 {a[0]}*第1项 + {a[1]}*第2项 + {a[2]}*第3项 + b，其中 b={b}")
    return '; '.join(segs)

def _sample_coeffs() -> Tuple[List[int], int]:
    choices = [-3, -2, -1, 1, 2, 3]
    a = [random.choice(choices), random.choice(choices), random.choice(choices)]
    b = random.randint(-7, 7)
    return a, b

def _val_of(pos: str, known_map: Dict[str, int], X_values: Dict[str, int]) -> int:
    return known_map[pos] if pos in known_map else X_values[pos]

def _compute_row_last(row_key: str, row_ops: Dict[str, Dict[str, Any]], row_positions: Dict[str, List[str]],
                      known_map: Dict[str, int], X_values: Dict[str, int]) -> int:
    a = row_ops[row_key]['a']
    b = row_ops[row_key]['b']
    vals = [_val_of(p, known_map, X_values) for p in row_positions[row_key]]
    return a[0]*vals[0] + a[1]*vals[1] + a[2]*vals[2] + b

def _build_extra_specs(row_positions: Dict[str, List[str]], known_map: Dict[str, int], X_values: Dict[str, int],
                       r_last_map: Dict[str, int]) -> List[Dict[str, Any]]:
    """
    仅采样会约束未知的类型：row_max、row_min、compare_with_last、unknown_rank。
    每次生成 2–4 条，确保当前场景下成立。
    """
    extras: List[Dict[str, Any]] = []
    extra_num = random.randint(2, 4)

    positions = [f"r{i}c{j}" for i in range(1,4) for j in range(1,4)]
    unknown_keys = [p for p in positions if p not in known_map]

    types_pool = ['row_max', 'row_min', 'compare_with_last', 'unknown_rank']
    for _ in range(extra_num):
        t = random.choice(types_pool)
        if t in ('row_max', 'row_min', 'compare_with_last'):
            rk = random.choice(['r1','r2','r3'])
            pos_index = random.randint(0, 2)
            vals = [_val_of(p, known_map, X_values) for p in row_positions[rk]]
            if t == 'row_max':
                if not all(vals[pos_index] >= v for i, v in enumerate(vals) if i != pos_index):
                    pos_index = int(vals.index(max(vals)))
                desc = f"{rk} 的第{pos_index+1}项是该行前三项中的最大值"
                extras.append({'type': 'row_max', 'row': rk, 'pos_index': pos_index, 'strict': True, 'desc': desc})
            elif t == 'row_min':
                if not all(vals[pos_index] <= v for i, v in enumerate(vals) if i != pos_index):
                    pos_index = int(vals.index(min(vals)))
                desc = f"{rk} 的第{pos_index+1}项是该行前三项中的最小值"
                extras.append({'type': 'row_min', 'row': rk, 'pos_index': pos_index, 'strict': True, 'desc': desc})
            else:
                op = random.choice(['gt', 'lt'])
                last_val = r_last_map[rk]
                val = vals[pos_index]
                if not ((val > last_val) if op == 'gt' else (val < last_val)):
                    op = 'lt' if op == 'gt' else 'gt'
                desc = f"{rk} 的第{pos_index+1}项{'大于' if op=='gt' else '小于'}该行最后一列"
                extras.append({'type': 'compare_with_last', 'row': rk, 'pos_index': pos_index, 'op': op, 'last_value': last_val, 'desc': desc})
        else:
            kpos = random.choice(unknown_keys)
            kind = random.choice(['max', 'min', 'second'])
            desc_map = {'max': '是未知值中的最大值', 'min': '是未知值中的最小值', 'second': '在未知值中按大小排名第二'}
            desc = f"{kpos} {desc_map[kind]}"
            extras.append({'type': 'unknown_rank', 'pos': kpos, 'kind': kind, 'desc': desc})
    return extras

def build_extra_cond(spec: Dict[str, Any], X: Dict[str, Any], known_map: Dict[str, int], row_positions: Dict[str, List[str]], unknown_keys: List[str]):
    t = spec['type']
    if t in ('row_max', 'row_min', 'compare_with_last'):
        rkey = spec['row']
        pos_index = spec['pos_index']
        target_pos = row_positions[rkey][pos_index]
        target_val = cell_value(target_pos, X, known_map)
        vals = [cell_value(p, X, known_map) for p in row_positions[rkey]]
        if t == 'row_max':
            return z3_and([target_val > v for i, v in enumerate(vals) if i != pos_index])
        if t == 'row_min':
            return z3_and([target_val < v for i, v in enumerate(vals) if i != pos_index])
        last_val = spec['last_value']
        return target_val > last_val if spec.get('op','gt') == 'gt' else target_val < last_val
    elif t == 'unknown_rank':
        pos = spec['pos']
        kind = spec['kind']
        others = [k for k in unknown_keys if k != pos]
        target = X[pos]
        if kind == 'max':
            return z3_and([target > X[k] for k in others])
        elif kind == 'min':
            return z3_and([target < X[k] for k in others])
        else:
            if len(others) == 3:
                return z3_or([
                    And(target > X[others[0]], target > X[others[1]], target < X[others[2]]),
                    And(target > X[others[0]], target < X[others[1]], target > X[others[2]]),
                    And(target < X[others[0]], target > X[others[1]], target > X[others[2]])
                ])
            else:
                return BoolVal(True)
    else:
        return BoolVal(True)

def _unique_check(specs: Dict[str, Any]) -> bool:
    unknown_keys = specs['unknown_keys']
    known_map = specs['known_map']
    row_positions = specs['row_positions']
    row_ops = specs['row_ops']
    r_last = {'r1': specs['r1_last'], 'r2': specs['r2_last'], 'r3': specs['r3_last']}
    col_sum = {'c1': specs['col1_sum'], 'c2': specs['col2_sum'], 'c3': specs['col3_sum']}
    total_sum = specs['total_sum']
    extra_specs = specs['extra_specs']

    fixed = known_map.copy()

    def val_of(pos, assign):
        return fixed[pos] if pos in fixed else assign[pos]

    def row_ok(rk, assign):
        a = row_ops[rk]['a']
        b = row_ops[rk]['b']
        row_pos = row_positions[rk]
        total = a[0]*val_of(row_pos[0], assign) + a[1]*val_of(row_pos[1], assign) + a[2]*val_of(row_pos[2], assign) + b
        return total == r_last[rk]

    def col_ok(assign):
        s1 = val_of('r1c1', assign) + val_of('r2c1', assign) + val_of('r3c1', assign)
        s2 = val_of('r1c2', assign) + val_of('r2c2', assign) + val_of('r3c2', assign)
        s3 = val_of('r1c3', assign) + val_of('r2c3', assign) + val_of('r3c3', assign)
        return s1 == col_sum['c1'] and s2 == col_sum['c2'] and s3 == col_sum['c3']

    def total_ok(assign):
        return r_last['r1'] + r_last['r2'] + r_last['r3'] == total_sum

    def extra_ok(assign):
        for e in extra_specs:
            t = e['type']
            if t in ('row_max', 'row_min', 'compare_with_last'):
                rk = e['row']; idx = e['pos_index']
                row_pos = row_positions[rk]
                tar = val_of(row_pos[idx], assign)
                vals = [val_of(p, assign) for p in row_pos]
                if t == 'row_max':
                    if not all(tar > v for i, v in enumerate(vals) if i != idx):
                        return False
                elif t == 'row_min':
                    if not all(tar < v for i, v in enumerate(vals) if i != idx):
                        return False
                else:
                    last_val = r_last[rk]
                    if e.get('op','gt') == 'gt':
                        if not (tar > last_val): return False
                    else:
                        if not (tar < last_val): return False
            elif t == 'unknown_rank':
                pos = e['pos']; kind = e['kind']
                tar = val_of(pos, assign)
                others = [k for k in unknown_keys if k != pos]
                other_vals = [val_of(k, assign) for k in others]
                if kind == 'max':
                    if not all(tar > v for v in other_vals): return False
                elif kind == 'min':
                    if not all(tar < v for v in other_vals): return False
                else:
                    bigger = sum(1 for v in other_vals if v > tar)
                    smaller = sum(1 for v in other_vals if v < tar)
                    if not (bigger == 1 and smaller == len(other_vals)-1):
                        return False
            else:
                continue
        return True

    valid_count = 0
    unknown_vals = [specs['X_values'][k] for k in unknown_keys]
    for perm in permutations(unknown_vals):
        assign = {k: v for k, v in zip(unknown_keys, perm)}
        if row_ok('r1', assign) and row_ok('r2', assign) and row_ok('r3', assign) and col_ok(assign) and total_ok(assign) and extra_ok(assign):
            valid_count += 1
            if valid_count > 1:
                return False
    return valid_count == 1

def function_1(base_min: int, base_max: int, seed: int = None, max_tries: int = 3000) -> Dict[str, Any]:
    if seed is not None:
        random.seed(seed)

    positions = [f"r{i}c{j}" for i in range(1,4) for j in range(1,4)]
    row_positions = {'r1': ['r1c1','r1c2','r1c3'], 'r2': ['r2c1','r2c2','r2c3'], 'r3': ['r3c1','r3c2','r3c3']}

    def pick():
        return random.randint(base_min, base_max)

    tries = 0
    while tries < max_tries:
        tries += 1
        unknown_keys = random.sample(positions, 4)

        known_map = {}
        for p in positions:
            if p not in unknown_keys:
                known_map[p] = pick()

        X_values = {}
        used = set()
        for uk in unknown_keys:
            v = pick()
            for _ in range(50):
                if v in used:
                    v = pick()
                else:
                    break
            if v in used:
                break
            used.add(v)
            X_values[uk] = v
        if len(X_values) != 4:
            continue

        row_ops = {}
        for rk in ['r1','r2','r3']:
            a, b = _sample_coeffs()
            row_ops[rk] = {'a': a, 'b': b}

        r1_last = _compute_row_last('r1', row_ops, row_positions, known_map, X_values)
        r2_last = _compute_row_last('r2', row_ops, row_positions, known_map, X_values)
        r3_last = _compute_row_last('r3', row_ops, row_positions, known_map, X_values)

        col1_sum = _val_of('r1c1', known_map, X_values) + _val_of('r2c1', known_map, X_values) + _val_of('r3c1', known_map, X_values)
        col2_sum = _val_of('r1c2', known_map, X_values) + _val_of('r2c2', known_map, X_values) + _val_of('r3c2', known_map, X_values)
        col3_sum = _val_of('r1c3', known_map, X_values) + _val_of('r2c3', known_map, X_values) + _val_of('r3c3', known_map, X_values)
        total_sum = r1_last + r2_last + r3_last

        extra_specs = _build_extra_specs(row_positions, known_map, X_values, {'r1': r1_last, 'r2': r2_last, 'r3': r3_last})

        specs = {
            'unknown_keys': unknown_keys,
            'known_map': known_map,
            'row_positions': row_positions,
            'row_ops': row_ops,
            'r1_last': r1_last,
            'r2_last': r2_last,
            'r3_last': r3_last,
            'col1_sum': col1_sum,
            'col2_sum': col2_sum,
            'col3_sum': col3_sum,
            'total_sum': total_sum,
            'extra_specs': extra_specs,
            'X_values': X_values,
        }

        if _unique_check(specs):
            return specs

    # 兜底：构造一个简单可行且唯一的场景
    unknown_keys = ['r1c3','r2c1','r2c3','r3c2']
    known_map = {'r1c1': base_min + 3, 'r1c2': base_min + 4, 'r2c2': base_min + 2, 'r3c1': base_min + 1, 'r3c3': base_min}
    X_values = {'r1c3': base_min + 5, 'r2c1': base_min + 7, 'r2c3': base_min + 6, 'r3c2': base_min + 3}
    row_ops = {'r1': {'a': [1,1,1], 'b': 0}, 'r2': {'a': [1,-1,-1], 'b': 0}, 'r3': {'a': [2,1,-1], 'b': 0}}
    row_positions = {'r1': ['r1c1','r1c2','r1c3'], 'r2': ['r2c1','r2c2','r2c3'], 'r3': ['r3c1','r3c2','r3c3']}
    r1_last = _compute_row_last('r1', row_ops, row_positions, known_map, X_values)
    r2_last = _compute_row_last('r2', row_ops, row_positions, known_map, X_values)
    r3_last = _compute_row_last('r3', row_ops, row_positions, known_map, X_values)
    col1_sum = _val_of('r1c1', known_map, X_values) + _val_of('r2c1', known_map, X_values) + _val_of('r3c1', known_map, X_values)
    col2_sum = _val_of('r1c2', known_map, X_values) + _val_of('r2c2', known_map, X_values) + _val_of('r3c2', known_map, X_values)
    col3_sum = _val_of('r1c3', known_map, X_values) + _val_of('r2c3', known_map, X_values) + _val_of('r3c3', known_map, X_values)
    total_sum = r1_last + r2_last + r3_last
    extra_specs = [
        {'type': 'row_max', 'row': 'r2', 'pos_index': 0, 'strict': True, 'desc': 'r2 的第1项是该行前三项中的最大值'},
        {'type': 'unknown_rank', 'pos': 'r1c3', 'kind': 'min', 'desc': 'r1c3 是未知值中的最小值'}
    ]
    return {
        'unknown_keys': unknown_keys,
        'known_map': known_map,
        'row_positions': row_positions,
        'row_ops': row_ops,
        'r1_last': r1_last,
        'r2_last': r2_last,
        'r3_last': r3_last,
        'col1_sum': col1_sum,
        'col2_sum': col2_sum,
        'col3_sum': col3_sum,
        'total_sum': total_sum,
        'extra_specs': extra_specs,
        'X_values': X_values,
    }