# blood_donation_puzzle_0.py
import random
from typing import List, Dict, Any, Tuple

# -----------------------------
# Utility to access Z3 Int values
# -----------------------------
def _get_pos(model: Any, sym: Any) -> int:
    try:
        val = model.evaluate(sym, model_completion=True)
    except Exception:
        val = model.eval(sym, model_completion=True)
    try:
        return int(val.as_long())
    except Exception:
        return int(val.num_as_long())

# -----------------------------
# Sampling helper for variables
# -----------------------------
def sample_k(seq: List[Any], k: int) -> List[Any]:
    """Return k distinct elements sampled from seq."""
    return random.sample(list(seq), min(k, len(seq)))

# -----------------------------
# Build the answer spec and prompt/example
# -----------------------------
def _build_prompt_and_example(fields: List[Dict[str, Any]]) -> Tuple[str, str]:
    labels = []
    for f in fields:
        t = f['type']
        v = f['value']
        if t == 'owner_of_blood':
            labels.append(f"{v}的拥有者")
        elif t == 'color_of_weight':
            labels.append(f"{v}磅者所穿颜色")
        elif t == 'age_of_name':
            labels.append(f"{v}的年龄")
        elif t == 'blood_of_profession':
            labels.append(f"{v}对应的血型")
        else:
            labels.append("信息")
    prompt = "顺序为 " + " ".join(labels)
    example = "示例 值1====值2====值3====值4"
    return prompt, example

def build_answer_spec(
    _model: Any,
    names: List[str],
    professions: List[str],
    colors: List[str],
    ages: List[int],
    weights: List[int],
    blood_types: List[str],
    pos_name: Dict[str, Any],
    pos_prof: Dict[str, Any],
    pos_color: Dict[str, Any],
    pos_age: Dict[int, Any],
    pos_weight: Dict[int, Any],
    pos_blood: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Randomly pick four task types and concrete items for each.
    """
    task_types = ['owner_of_blood', 'color_of_weight', 'age_of_name', 'blood_of_profession']
    random.shuffle(task_types)
    chosen = task_types[:4]
    fields = []
    for t in chosen:
        if t == 'owner_of_blood':
            fields.append({'type': t, 'value': random.choice(blood_types)})
        elif t == 'color_of_weight':
            fields.append({'type': t, 'value': random.choice(weights)})
        elif t == 'age_of_name':
            fields.append({'type': t, 'value': random.choice(names)})
        elif t == 'blood_of_profession':
            fields.append({'type': t, 'value': random.choice(professions)})
    prompt, example = _build_prompt_and_example(fields)
    return {'fields': fields, 'prompt': prompt, 'example': example}

# -----------------------------
# Derive relational clues from a single solution
# -----------------------------
def derive_clues(
    _model: Any,
    names: List[str],
    professions: List[str],
    colors: List[str],
    ages: List[int],
    weights: List[int],
    blood_types: List[str],
    pos_name: Dict[str, Any],
    pos_prof: Dict[str, Any],
    pos_color: Dict[str, Any],
    pos_age: Dict[int, Any],
    pos_weight: Dict[int, Any],
    pos_blood: Dict[str, Any],
    eq_na_count: int,
    eq_bw_count: int,
    adj_blood_count: int,
    left_cw_count: int,
    between_pc_count: int,
    order_prof_count: int,
    cw_color_left: bool,
    adj_blood_distance: int,
    prof_chain_asc: bool,
    gap_np_count: int,
    gap_np_distance: int,
    style_mode: int,
    end_prof_left_count: int,
    end_prof_right_count: int,
    color_not_ends_count: int,
    mirror_nw_count: int,
    nc_gap_count: int,
    nc_distance: int,
    anchor_color_count: int,
    anchor_age_count: int,
    anchor_weight_count: int,
    max_eq_name_color: int,
    max_eq_prof_blood: int,
    max_eq_name_weight: int,
    max_eq_name_prof: int,
    max_eq_color_blood: int,
    max_eq_age_weight: int,
    anchor_prof_count: int,
    anchor_blood_count: int,
    force_uniq_anchors: bool,
) -> Dict[str, Any]:
    """
    Build several families of clues that are true in the chosen model.
    Return lists for each clue family and a human-readable block of clue texts.
    Only emit relative/relational clues in text for depth; avoid absolute position reveals.
    """

    # Build position maps
    name_pos = {nm: _get_pos(_model, pos_name[nm]) for nm in names}
    prof_pos = {pr: _get_pos(_model, pos_prof[pr]) for pr in professions}
    color_pos = {co: _get_pos(_model, pos_color[co]) for co in colors}
    age_pos = {ag: _get_pos(_model, pos_age[ag]) for ag in ages}
    weight_pos = {we: _get_pos(_model, pos_weight[we]) for we in weights}
    blood_pos = {bt: _get_pos(_model, pos_blood[bt]) for bt in blood_types}

    # Helper to invert maps
    def invert(m: Dict[Any, int]) -> Dict[int, Any]:
        return {v: k for k, v in m.items()}

    inv_age = invert(age_pos)
    inv_weight = invert(weight_pos)
    inv_color = invert(color_pos)
    inv_blood = invert(blood_pos)
    inv_prof = invert(prof_pos)

    posmax = max(name_pos.values()) if name_pos else 0

    # Equality: name == age
    eq_name_age = []
    if eq_na_count > 0 and len(names) > 0:
        all_pairs = []
        for nm in names:
            p = name_pos[nm]
            ag = inv_age.get(p, None)
            if ag is not None:
                all_pairs.append((nm, ag))
        random.shuffle(all_pairs)
        eq_name_age = all_pairs[:min(eq_na_count, len(all_pairs))]

    # Equality: blood == weight
    eq_blood_weight = []
    if eq_bw_count > 0 and len(blood_types) > 0:
        all_pairs = []
        for bt in blood_types:
            p = blood_pos[bt]
            we = inv_weight.get(p, None)
            if we is not None:
                all_pairs.append((bt, we))
        random.shuffle(all_pairs)
        eq_blood_weight = all_pairs[:min(eq_bw_count, len(all_pairs))]

    # Adjacency at chosen distance: blood-blood
    adj_pairs = []
    for a in blood_types:
        for b in blood_types:
            if a == b:
                continue
            if abs(blood_pos[a] - blood_pos[b]) == adj_blood_distance:
                if blood_pos[a] < blood_pos[b]:
                    adj_pairs.append((a, b))
    seen = set()
    adj_pairs_unique = []
    for a, b in adj_pairs:
        if (a, b) not in seen and (b, a) not in seen:
            seen.add((a, b))
            adj_pairs_unique.append((a, b))
    random.shuffle(adj_pairs_unique)
    adj_blood = adj_pairs_unique[:min(adj_blood_count, len(adj_pairs_unique))]

    # Relative: color vs weight orientation (with fallback)
    left_color_weight: List[Tuple[str, int]] = []
    weight_left_color: List[Tuple[int, str]] = []
    c_w_pairs = []
    w_c_pairs = []
    for c in colors:
        for w in weights:
            if color_pos[c] < weight_pos[w]:
                c_w_pairs.append((c, w))
            if weight_pos[w] < color_pos[c]:
                w_c_pairs.append((w, c))
    random.shuffle(c_w_pairs)
    random.shuffle(w_c_pairs)
    if cw_color_left:
        left_color_weight = c_w_pairs[:min(left_cw_count, len(c_w_pairs))]
        if not left_color_weight and left_cw_count > 0 and len(w_c_pairs) > 0:
            weight_left_color = w_c_pairs[:min(left_cw_count, len(w_c_pairs))]
    else:
        weight_left_color = w_c_pairs[:min(left_cw_count, len(w_c_pairs))]
        if not weight_left_color and left_cw_count > 0 and len(c_w_pairs) > 0:
            left_color_weight = c_w_pairs[:min(left_cw_count, len(c_w_pairs))]

    # Between in order: profession between two colors (color_left < prof < color_right)
    p_between = []
    for p in professions:
        for c1 in colors:
            for c2 in colors:
                if c1 == c2:
                    continue
                if color_pos[c1] < prof_pos[p] and prof_pos[p] < color_pos[c2]:
                    p_between.append((p, c1, c2))
    random.shuffle(p_between)
    between_prof_color = p_between[:min(between_pc_count, len(p_between))]

    # Chains of three professions with orientation (with fallback)
    asc_chains = []
    desc_chains = []
    for i in range(len(professions)):
        for j in range(len(professions)):
            if j == i:
                continue
            for k in range(len(professions)):
                if k == i or k == j:
                    continue
                p1, p2, p3 = professions[i], professions[j], professions[k]
                if prof_pos[p1] < prof_pos[p2] and prof_pos[p2] < prof_pos[p3]:
                    asc_chains.append((p1, p2, p3))
                if prof_pos[p1] > prof_pos[p2] and prof_pos[p2] > prof_pos[p3]:
                    desc_chains.append((p1, p2, p3))
    random.shuffle(asc_chains)
    random.shuffle(desc_chains)
    order_prof_chain_asc: List[Tuple[str, str, str]] = []
    order_prof_chain_desc: List[Tuple[str, str, str]] = []
    if prof_chain_asc:
        order_prof_chain_asc = asc_chains[:min(order_prof_count, len(asc_chains))]
        if not order_prof_chain_asc and order_prof_count > 0 and len(desc_chains) > 0:
            order_prof_chain_desc = desc_chains[:min(order_prof_count, len(desc_chains))]
    else:
        order_prof_chain_desc = desc_chains[:min(order_prof_count, len(desc_chains))]
        if not order_prof_chain_desc and order_prof_count > 0 and len(asc_chains) > 0:
            order_prof_chain_asc = asc_chains[:min(order_prof_count, len(asc_chains))]

    # Name–Profession fixed gap constraints
    gap_name_prof: List[Tuple[str, str]] = []
    if gap_np_count > 0:
        pairs = []
        for nm in names:
            for pr in professions:
                if abs(name_pos[nm] - prof_pos[pr]) == gap_np_distance:
                    pairs.append((nm, pr))
        random.shuffle(pairs)
        gap_name_prof = pairs[:min(gap_np_count, len(pairs))]

    # 0) Optional anchor: name at leftmost and blood at rightmost (low count, text kept)
    anchor_name_left: List[str] = []
    anchor_blood_right: List[str] = []
    left_name_cands = [nm for nm in names if name_pos[nm] == 1]
    right_blood_cands = [bt for bt in blood_types if blood_pos[bt] == posmax]
    if left_name_cands:
        anchor_name_left = [random.choice(left_name_cands)]
    if right_blood_cands:
        anchor_blood_right = [random.choice(right_blood_cands)]

    # 1) End-anchored professions: left or right (optional counts, text kept)
    ends_prof_left: List[str] = []
    ends_prof_right: List[str] = []
    left_cands = [p for p in professions if prof_pos[p] == 1]
    right_cands = [p for p in professions if prof_pos[p] == posmax]
    random.shuffle(left_cands)
    random.shuffle(right_cands)
    ends_prof_left = left_cands[:min(end_prof_left_count, len(left_cands))]
    ends_prof_right = right_cands[:min(end_prof_right_count, len(right_cands))]

    # 2) Not-at-ends colors
    not_ends_color: List[str] = []
    if color_not_ends_count > 0:
        cands = [c for c in colors if color_pos[c] != 1 and color_pos[c] != posmax]
        random.shuffle(cands)
        not_ends_color = cands[:min(color_not_ends_count, len(cands))]

    # 3) Mirror name-weight pairs: pos(name)+pos(weight) == posmax + 1
    mirror_name_weight: List[Tuple[str, int]] = []
    if mirror_nw_count > 0:
        pairs = []
        for nm in names:
            for w in weights:
                if name_pos[nm] + weight_pos[w] == posmax + 1:
                    pairs.append((nm, w))
        random.shuffle(pairs)
        mirror_name_weight = pairs[:min(mirror_nw_count, len(pairs))]

    # 4) Fixed gap name-color pairs: |pos(name)-pos(color)| == nc_distance
    gap_name_color: List[Tuple[str, str]] = []
    if nc_gap_count > 0:
        pairs = []
        for nm in names:
            for c in colors:
                if abs(name_pos[nm] - color_pos[c]) == nc_distance:
                    pairs.append((nm, c))
        random.shuffle(pairs)
        gap_name_color = pairs[:min(nc_gap_count, len(pairs))]

    # 5) Strong-coupling families (capped)
    eq_name_color: List[Tuple[str, str]] = []
    if len(names) > 0 and max_eq_name_color > 0:
        all_pairs = []
        for nm in names:
            p = name_pos[nm]
            col = invert(color_pos).get(p, None)
            if col is not None:
                all_pairs.append((nm, col))
        random.shuffle(all_pairs)
        eq_name_color = all_pairs[:min(max_eq_name_color, len(all_pairs))]

    eq_prof_blood: List[Tuple[str, str]] = []
    if len(professions) > 0 and max_eq_prof_blood > 0:
        all_pairs = []
        for pr in professions:
            p = prof_pos[pr]
            bt = invert(blood_pos).get(p, None)
            if bt is not None:
                all_pairs.append((pr, bt))
        random.shuffle(all_pairs)
        eq_prof_blood = all_pairs[:min(max_eq_prof_blood, len(all_pairs))]

    eq_name_weight: List[Tuple[str, int]] = []
    if len(names) > 0 and max_eq_name_weight > 0:
        all_pairs = []
        for nm in names:
            p = name_pos[nm]
            w = invert(weight_pos).get(p, None)
            if w is not None:
                all_pairs.append((nm, w))
        random.shuffle(all_pairs)
        eq_name_weight = all_pairs[:min(max_eq_name_weight, len(all_pairs))]

    eq_name_prof: List[Tuple[str, str]] = []
    if len(names) > 0 and len(professions) > 0 and max_eq_name_prof > 0:
        all_pairs = []
        for nm in names:
            p = name_pos[nm]
            pr = inv_prof.get(p, None)
            if pr is not None:
                all_pairs.append((nm, pr))
        random.shuffle(all_pairs)
        eq_name_prof = all_pairs[:min(max_eq_name_prof, len(all_pairs))]

    eq_color_blood: List[Tuple[str, str]] = []
    if len(colors) > 0 and len(blood_types) > 0 and max_eq_color_blood > 0:
        all_pairs = []
        for c in colors:
            p = color_pos[c]
            bt = inv_blood.get(p, None)
            if bt is not None:
                all_pairs.append((c, bt))
        random.shuffle(all_pairs)
        eq_color_blood = all_pairs[:min(max_eq_color_blood, len(all_pairs))]

    eq_age_weight: List[Tuple[int, int]] = []
    if len(ages) > 0 and len(weights) > 0 and max_eq_age_weight > 0:
        all_pairs = []
        for a in ages:
            p = age_pos[a]
            w = inv_weight.get(p, None)
            if w is not None:
                all_pairs.append((a, w))
        random.shuffle(all_pairs)
        eq_age_weight = all_pairs[:min(max_eq_age_weight, len(all_pairs))]

    # Human-readable text lines with style variations (no absolute-position reveals)
    lines = []
    line_set = set()

    def add_line(s: str):
        if s not in line_set:
            lines.append(s)
            line_set.add(s)

    # anchor name left / blood right (low count, helpful but not too revealing)
    for nm in anchor_name_left:
        if style_mode == 0:
            add_line(f"最左端是{nm}")
        elif style_mode == 1:
            add_line(f"{nm}在最左端")
        else:
            add_line(f"{nm}位于队伍最左侧")
    for bt in anchor_blood_right:
        if style_mode == 0:
            add_line(f"最右端的献血类型是{bt}")
        elif style_mode == 1:
            add_line(f"{bt}位于最右端")
        else:
            add_line(f"最右端对应献血类型为{bt}")

    # name-age equality
    for nm, ag in eq_name_age:
        if style_mode == 0:
            add_line(f"{nm}是{ag}岁")
        elif style_mode == 1:
            add_line(f"{nm}对应年龄为{ag}")
        else:
            add_line(f"{nm}的年龄为{ag}")
    # blood-weight equality
    for bt, we in eq_blood_weight:
        if style_mode == 0:
            add_line(f"{bt}对应{we}磅")
        elif style_mode == 1:
            add_line(f"献血类型{bt}与体重{we}匹配")
        else:
            add_line(f"体重{we}的人献血类型为{bt}")
    # adjacency of bloods with distance wording
    for a, b in adj_blood:
        if style_mode == 0:
            add_line(f"{a}与{b}相邻且间隔为{adj_blood_distance}")
        elif style_mode == 1:
            add_line(f"{a}与{b}紧挨着且相距{adj_blood_distance}")
        else:
            add_line(f"{a}和{b}相邻距离为{adj_blood_distance}")
    # color vs weight orientation
    for c, w in left_color_weight:
        if style_mode == 0:
            add_line(f"{c}在{w}左侧")
        elif style_mode == 1:
            add_line(f"{c}位于{w}的左边")
        else:
            add_line(f"{w}在{c}右侧")
    for w, c in weight_left_color:
        if style_mode == 0:
            add_line(f"{w}在{c}左侧")
        elif style_mode == 1:
            add_line(f"{w}位于{c}的左边")
        else:
            add_line(f"{c}在{w}右侧")
    # profession between colors
    for p, c1, c2 in between_prof_color:
        if style_mode == 0:
            add_line(f"{p}在{c1}与{c2}之间且顺序为{c1}在左")
        elif style_mode == 1:
            add_line(f"{p}介于{c1}和{c2}之间且{c1}在左侧")
        else:
            add_line(f"{c1}在左 {p}位于其中 {c2}在右")
    # ascending and descending chains
    for p1, p2, p3 in order_prof_chain_asc:
        if style_mode == 0:
            add_line(f"从左到右依次为{p1} {p2} {p3}")
        elif style_mode == 1:
            add_line(f"左到右三者顺序是{p1} 然后{p2} 最后{p3}")
        else:
            add_line(f"{p1}在最左 {p2}居中 {p3}在最右")
    for p1, p2, p3 in order_prof_chain_desc:
        if style_mode == 0:
            add_line(f"从右到左依次为{p1} {p2} {p3}")
        elif style_mode == 1:
            add_line(f"右到左三者顺序是{p1} 然后{p2} 最后{p3}")
        else:
            add_line(f"{p1}在最右 {p2}居中 {p3}在最左")
    # name-prof gap
    for nm, pr in gap_name_prof:
        if style_mode == 0:
            add_line(f"{nm}与{pr}相隔{gap_np_distance}位")
        elif style_mode == 1:
            add_line(f"{nm}和{pr}之间隔着{gap_np_distance}人")
        else:
            add_line(f"{nm}的位置与{pr}相差{gap_np_distance}")
    # end-anchored professions
    for p in ends_prof_left:
        if style_mode == 0:
            add_line(f"{p}在最左端")
        elif style_mode == 1:
            add_line(f"{p}位于队伍最左侧")
        else:
            add_line(f"最左端是{p}")
    for p in ends_prof_right:
        if style_mode == 0:
            add_line(f"{p}在最右端")
        elif style_mode == 1:
            add_line(f"{p}位于队伍最右侧")
        else:
            add_line(f"最右端是{p}")
    # not-at-ends colors
    for c in not_ends_color:
        if style_mode == 0:
            add_line(f"{c}不在两端")
        elif style_mode == 1:
            add_line(f"{c}不会出现在最左或最右")
        else:
            add_line(f"{c}在中间位置而非端点")
    # mirror name-weight
    for nm, w in mirror_name_weight:
        if style_mode == 0:
            add_line(f"{nm}与{w}为镜像位置")
        elif style_mode == 1:
            add_line(f"{nm}和{w}位于队伍对称位置")
        else:
            add_line(f"{nm}和{w}左右对称")
    # gap name-color
    for nm, c in gap_name_color:
        if style_mode == 0:
            add_line(f"{nm}与{c}相距{nc_distance}")
        elif style_mode == 1:
            add_line(f"{nm}和{c}之间隔着{nc_distance}人")
        else:
            add_line(f"{nm}的位置与{c}相差{nc_distance}")
    # strong-coupling families (capped)
    for nm, col in eq_name_color:
        if style_mode == 0:
            add_line(f"{nm}所对应的颜色是{col}")
        elif style_mode == 1:
            add_line(f"{nm}与颜色{col}对应同一位置")
        else:
            add_line(f"{nm}对应的颜色为{col}")
    for pr, bt in eq_prof_blood:
        if style_mode == 0:
            add_line(f"{pr}对应的献血类型是{bt}")
        elif style_mode == 1:
            add_line(f"{pr}与{bt}在同一位置")
        else:
            add_line(f"{pr}的血型为{bt}")
    for nm, w in eq_name_weight:
        if style_mode == 0:
            add_line(f"{nm}对应体重为{w}")
        elif style_mode == 1:
            add_line(f"{nm}与{w}磅在同一位置")
        else:
            add_line(f"{nm}的体重是{w}")
    for nm, pr in eq_name_prof:
        if style_mode == 0:
            add_line(f"{nm}对应的职业是{pr}")
        elif style_mode == 1:
            add_line(f"{nm}与职业{pr}对应同一位置")
        else:
            add_line(f"{nm}的职业为{pr}")
    for c, bt in eq_color_blood:
        if style_mode == 0:
            add_line(f"{c}对应的献血类型是{bt}")
        elif style_mode == 1:
            add_line(f"颜色{c}与血型{bt}在同一位置")
        else:
            add_line(f"{c}对应血型为{bt}")
    for a, w in eq_age_weight:
        if style_mode == 0:
            add_line(f"{a}岁对应体重为{w}")
        elif style_mode == 1:
            add_line(f"{a}岁与{w}磅在同一位置")
        else:
            add_line(f"{a}岁的人的体重是{w}")

    # Build an answer spec here to keep a single pass
    answer_spec = build_answer_spec(
        _model, names, professions, colors, ages, weights, blood_types,
        pos_name, pos_prof, pos_color, pos_age, pos_weight, pos_blood
    )

    return {
        'eq_name_age': eq_name_age,
        'eq_blood_weight': eq_blood_weight,
        'adj_blood': adj_blood,
        'left_color_weight': left_color_weight,
        'weight_left_color': weight_left_color,
        'between_prof_color': between_pc_count and between_prof_color or [],
        'order_prof_chain_asc': order_prof_chain_asc,
        'order_prof_chain_desc': order_prof_chain_desc,
        'gap_name_prof': gap_name_prof,
        'ends_prof_left': ends_prof_left,
        'ends_prof_right': ends_prof_right,
        'not_ends_color': not_ends_color,
        'mirror_name_weight': mirror_name_weight,
        'gap_name_color': gap_name_color,
        'eq_name_color': eq_name_color,
        'eq_prof_blood': eq_prof_blood,
        'eq_name_weight': eq_name_weight,
        'anchor_name_left': anchor_name_left,
        'anchor_blood_right': anchor_blood_right,
        'eq_name_prof': eq_name_prof,
        'eq_color_blood': eq_color_blood,
        'eq_age_weight': eq_age_weight,
        'clue_text': "\n".join(lines),
        'answer_spec': answer_spec
    }

# -----------------------------
# Compute final answer string
# -----------------------------
def compute_answers(
    _model: Any,
    names: List[str],
    weights: List[int],
    colors: List[str],
    ages: List[int],
    blood_types: List[str],
    pos_name: Dict[str, Any],
    pos_weight: Dict[int, Any],
    pos_color: Dict[str, Any],
    pos_age: Dict[int, Any],
    pos_blood: Dict[str, Any],
    pos_prof: Dict[str, Any],
    answer_spec: Dict[str, Any]
) -> str:
    # Precompute inverse maps to avoid repeated loops
    pos_to_name = { _get_pos(_model, pos_name[nm]): nm for nm in names }
    pos_to_color = { _get_pos(_model, pos_color[c]): c for c in colors }
    pos_to_age = { _get_pos(_model, pos_age[a]): a for a in ages }
    pos_to_blood = { _get_pos(_model, pos_blood[bt]): bt for bt in blood_types }

    def owner_of_blood(bt: str) -> str:
        bpos = _get_pos(_model, pos_blood[bt])
        return pos_to_name.get(bpos, "")

    def color_of_weight(w: int) -> str:
        wpos = _get_pos(_model, pos_weight[w])
        return pos_to_color.get(wpos, "")

    def age_of_name(nm: str) -> int:
        npos = _get_pos(_model, pos_name[nm])
        return pos_to_age.get(npos, -1)

    def blood_of_profession(p: str) -> str:
        ppos = _get_pos(_model, pos_prof[p])
        return pos_to_blood.get(ppos, "")

    segs = []
    for f in answer_spec['fields']:
        t = f['type']
        v = f['value']
        if t == 'owner_of_blood':
            segs.append(owner_of_blood(v))
        elif t == 'color_of_weight':
            segs.append(color_of_weight(int(v)))
        elif t == 'age_of_name':
            segs.append(str(age_of_name(v)))
        elif t == 'blood_of_profession':
            segs.append(blood_of_profession(v))
        else:
            segs.append("")
    return "====".join(segs)