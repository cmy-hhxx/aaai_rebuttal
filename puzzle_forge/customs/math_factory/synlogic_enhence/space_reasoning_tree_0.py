# space_reasoning_tree_2.py
# ------------------------------------------------------------
# 高阶泛化版自定义算子库：
# - function_2：随机生成城市分区树（城市→大区→区→街区→建筑），生成建筑隐式属性，
#               随机定义多层次堂兄弟关系（share_levels & not_share_levels），
#               随机生成复合过滤条件（等级、位置、特征阈值、排名、复合分数）与聚合器（AND/OR/K_OF_N），
#               在有墙钟限制与次数限制的前提下重采样确保唯一解，并生成可读文本。
# - function_1：依据上述规则计算答案（唯一建筑名称或 'unknown'）。
# 目标：
# - 通过函数复合与隐式辅助变量提升逻辑复杂性与隐蔽性，同时保持题面可解与清晰。
# - 保证至少 200 道题目的生成空间，并将唯一解验证过程控制在 3 分钟以内（默认 2 秒）。
# ------------------------------------------------------------

from typing import Dict, List, Tuple, Any
import random
import time

# 名称模板池（中文词根与后缀），用于生成多样化建筑名称
NAME_ROOTS = [
    "湖畔", "春风", "阳光", "松柏", "天际", "海风", "梧桐", "清风", "碧水", "云汀",
    "桂花", "银杏", "映月", "星河", "澜庭", "锦城", "沐光", "竹语", "栖湖", "晴川",
    "锦湾", "玉兰", "紫藤", "天幕", "澜城", "映湖", "星耀", "云樾", "观澜", "栖云"
]
NAME_SUFFIX = ["花园", "公寓", "苑", "里", "居", "大厦", "雅苑", "华庭", "榭", "府", "名邸", "雅居"]

DIRECTIONS = ["东", "西", "南", "北", "中", "新区", "高新", "临港", "滨海", "科创", "栖霞", "青山", "碧湖"]

LEVELS = ["city", "region", "district", "block"]
LEVELS_CN = {"city": "城市", "region": "大区", "district": "区", "block": "街区"}

FEATURE_KEYS = ["eco", "noise", "height", "occup"]  # 隐式特征键


def _unique_name(prefix: str, existing: set, fallback_index: int) -> str:
    """生成唯一名称：若 prefix 已存在，则加序号后缀。"""
    if prefix not in existing:
        existing.add(prefix)
        return prefix
    i = fallback_index
    while True:
        cand = f"{prefix}{i}"
        if cand not in existing:
            existing.add(cand)
            return cand
        i += 1


def _gen_region_names(n: int) -> List[str]:
    """生成 n 个大区名：优先使用方向/功能词，格式为 '大区X'。"""
    used = set()
    names = []
    for i in range(n):
        base = DIRECTIONS[i % len(DIRECTIONS)]
        name = _unique_name(f"大区{base}", used, i + 1)
        names.append(name)
    return names


def _gen_district_names(total_needed: int) -> List[str]:
    """生成全局唯一的区名：'区1', '区2', ...。"""
    return [f"区{idx}" for idx in range(1, total_needed + 1)]


def _gen_block_names(total_needed: int) -> List[str]:
    """生成全局唯一的街区名：'街区A1', '街区B2', ...（字母+序号组合），避免冲突。"""
    names = []
    letters = [chr(ord("A") + i) for i in range(26)]
    count = 0
    while len(names) < total_needed:
        for L in letters:
            count += 1
            names.append(f"街区{L}{count}")
            if len(names) >= total_needed:
                break
    return names


def _gen_building_names(total_needed: int) -> List[str]:
    """生成全局唯一的建筑名：组合词根与后缀，如 '湖畔花园'、'阳光公寓' 等，若冲突则追加序号。"""
    existing = set()
    names = []
    idx = 1
    while len(names) < total_needed:
        root = random.choice(NAME_ROOTS)
        suf = random.choice(NAME_SUFFIX)
        base = f"{root}{suf}"
        bname = _unique_name(base, existing, idx)
        names.append(bname)
        idx += 1
    return names


def _invert_list_dict(d: Dict[str, List[str]]) -> Dict[str, str]:
    """将 '父->子列表' 反向为 '子->父' 映射。"""
    inv = {}
    for parent, children in d.items():
        for c in children:
            inv[c] = parent
    return inv


def _build_inverse_maps(
    buildings_by_block: Dict[str, List[str]],
    blocks_by_district: Dict[str, List[str]],
    districts_by_region: Dict[str, List[str]],
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """构建反向映射：building->block, block->district, district->region。"""
    building_to_block = {}
    for blk, blist in buildings_by_block.items():
        for b in blist:
            building_to_block[b] = blk
    block_to_district = _invert_list_dict(blocks_by_district)
    district_to_region = _invert_list_dict(districts_by_region)
    return building_to_block, block_to_district, district_to_region


def _get_level_value_for_building(
    building: str,
    city: str,
    building_to_block: Dict[str, str],
    block_to_district: Dict[str, str],
    district_to_region: Dict[str, str],
    level: str,
) -> str:
    """返回建筑在指定层级上的标识值。"""
    if level == "city":
        return city
    elif level == "region":
        blk = building_to_block.get(building)
        dist = block_to_district.get(blk) if blk else None
        return district_to_region.get(dist) if dist else None
    elif level == "district":
        blk = building_to_block.get(building)
        return block_to_district.get(blk) if blk else None
    elif level == "block":
        return building_to_block.get(building)
    else:
        return None


def _choose_cousin_definition() -> Dict[str, List[str]]:
    """
    随机选择多层次堂兄弟定义：
    - share_levels：从 LEVELS 中选取至少 1 个较高层级；
    - not_share_levels：从严格低于 share_levels 中的层级选取 1~2 个。
    确保层级顺序合法：city > region > district > block。
    """
    # 选择 share 起点（0..2）
    s_idx = random.randint(0, len(LEVELS) - 2)
    share_levels = LEVELS[: s_idx + 1]  # 例如 s_idx=1 -> ['city','region']
    # not_share 从更低层级中选取
    not_pool = LEVELS[s_idx + 1 :]
    not_share_levels = random.sample(not_pool, k=random.randint(1, min(2, len(not_pool))))
    return {"share_levels": share_levels, "not_share_levels": not_share_levels}


def _grade_filter(grade_choices: List[str]) -> Dict[str, Any]:
    """生成等级筛选条件：operator in {'==','!='}, target in grade_choices。"""
    op = random.choice(["==", "!="])
    tgt = random.choice(grade_choices)
    text = f"绿色等级{'为' if op == '==' else '不为'}{tgt}"
    return {"type": "grade", "op": op, "value": tgt, "text": text}


def _location_filter(regions: List[str], district_names: List[str], block_names: List[str]) -> Dict[str, Any]:
    """生成位置筛选条件：scope in {'region','district','block'}，op in {'in','not_in'}，取 1~2 个名称。"""
    scope = random.choice(["region", "district", "block"])
    op = random.choice(["in", "not_in"])
    scope_cn = LEVELS_CN[scope]
    pool = regions if scope == "region" else (district_names if scope == "district" else block_names)
    k = random.randint(1, min(2, max(1, len(pool))))
    values = random.sample(pool, k)
    if k == 1:
        text = f"{'位于' if op == 'in' else '不位于'}{scope_cn}{values[0]}"
    else:
        text = f"{'位于' if op == 'in' else '不位于'}{scope_cn}集合[{', '.join(values)}]{'之一' if op == 'in' else ''}"
    return {"type": "location", "scope": scope, "op": op, "values": values, "text": text}


def _feature_threshold_filter(features_by_building: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """生成特征阈值筛选：随机选取特征与运算符及阈值。"""
    feat = random.choice(FEATURE_KEYS)
    op = random.choice([">=", "<=", ">", "<", "=="])
    # 阈值范围依据全体建筑该特征的统计近似
    vals = [v[feat] for v in features_by_building.values()]
    lo, hi = min(vals), max(vals)
    # 稍微扩大随机范围，提高判别力
    threshold = random.randint(lo, hi)
    text_map = {"eco": "生态分", "noise": "噪音分", "height": "楼高", "occup": "入住数"}
    text = f"{text_map[feat]}{op}{threshold}"
    return {"type": "feature_threshold", "feat": feat, "op": op, "threshold": threshold, "text": text}


def _rank_filter(scope_choice: str, feat_choice: str, k_max: int) -> Dict[str, Any]:
    """
    生成排名筛选：scope in {'district','block'}，feat in FEATURE_KEYS，
    模式：in_top_k 或 not_in_top_k，k 在 1..k_max。
    """
    mode = random.choice(["in_top_k", "not_in_top_k"])
    k = random.randint(1, max(1, k_max))
    text_map = {"eco": "生态分", "noise": "噪音分", "height": "楼高", "occup": "入住数"}
    text = f"在同{LEVELS_CN[scope_choice]}内按{str(text_map[feat_choice])}排名{'前' if mode == 'in_top_k' else '不在前'}{k}"
    return {"type": "rank", "scope": scope_choice, "feat": feat_choice, "mode": mode, "k": k, "text": text}


def _composite_score_filter(weights: Dict[str, float], threshold: float) -> Dict[str, Any]:
    """生成复合分数阈值筛选：w_eco*eco + w_noise*noise + w_height*height + w_occup*occup >= / <= threshold。"""
    op = random.choice([">=", "<="])
    # 文本描述权重精简为两位小数
    wtxt = ", ".join([f"{k}:{round(v,2)}" for k, v in weights.items()])
    text = f"复合分数({wtxt}){op}{round(threshold,2)}"
    return {"type": "composite_score", "weights": weights, "op": op, "threshold": threshold, "text": text}


def _compute_composite_score(feats: Dict[str, int], weights: Dict[str, float]) -> float:
    return sum(weights[k] * feats[k] for k in weights)


def _build_overview_and_attributes(
    city_name: str,
    regions: List[str],
    districts_by_region: Dict[str, List[str]],
    blocks_by_district: Dict[str, List[str]],
    buildings_by_block: Dict[str, List[str]],
    grade_by_building: Dict[str, str],
    features_by_building: Dict[str, Dict[str, int]],
) -> Tuple[str, str]:
    """生成单行结构概述与属性概述文本。"""
    parts = []
    parts.append(f"城市({city_name})包含大区[{', '.join(regions)}]")
    for r in regions:
        parts.append(f"{r}->[{', '.join(districts_by_region[r])}]")
    # 区->街区
    all_districts = []
    for r in regions:
        all_districts.extend(districts_by_region[r])
    for d in all_districts:
        parts.append(f"{d}->[{', '.join(blocks_by_district[d])}]")
    # 街区->建筑
    all_blocks = []
    for d in all_districts:
        all_blocks.extend(blocks_by_district[d])
    for blk in all_blocks:
        parts.append(f"{blk}->[{', '.join(buildings_by_block[blk])}]")
    overview = "; ".join(parts)

    # 属性概述：建筑名(等级X, 生态a, 噪音b, 楼高c, 入住d)
    attr_parts = []
    for blk in all_blocks:
        arr = []
        for b in buildings_by_block[blk]:
            f = features_by_building[b]
            arr.append(f"{b}(等级{grade_by_building[b]}, 生态{f['eco']}, 噪音{f['noise']}, 楼高{f['height']}, 入住{f['occup']})")
        attr_parts.append(f"{blk}->[{'; '.join(arr)}]")
    attributes_text = "; ".join(attr_parts)
    return overview, attributes_text


def _evaluate_filters_for_building(
    b: str,
    city: str,
    building_to_block: Dict[str, str],
    block_to_district: Dict[str, str],
    district_to_region: Dict[str, str],
    grade_by_building: Dict[str, str],
    features_by_building: Dict[str, Dict[str, int]],
    filters_machine: List[Dict[str, Any]],
    filter_agg: Dict[str, Any],
    scope_index: Dict[str, Dict[str, List[str]]],
) -> bool:
    """
    评估建筑对过滤器的满足情况，并依据聚合器输出 True/False。
    scope_index:
      {'district': {district_name: [buildings...]}, 'block': {block_name: [buildings...]}}
    """
    results: List[bool] = []
    for f in filters_machine:
        if f["type"] == "grade":
            res = (grade_by_building.get(b) == f["value"]) if f["op"] == "==" else (grade_by_building.get(b) != f["value"])
            results.append(res)
        elif f["type"] == "location":
            val = _get_level_value_for_building(b, city, building_to_block, block_to_district, district_to_region, f["scope"])
            res = (val in f["values"]) if f["op"] == "in" else (val not in f["values"])
            results.append(res)
        elif f["type"] == "feature_threshold":
            v = features_by_building[b][f["feat"]]
            op = f["op"]
            th = f["threshold"]
            if op == ">=":
                results.append(v >= th)
            elif op == "<=":
                results.append(v <= th)
            elif op == ">":
                results.append(v > th)
            elif op == "<":
                results.append(v < th)
            else:
                results.append(v == th)
        elif f["type"] == "rank":
            scope = f["scope"]
            feat = f["feat"]
            k = f["k"]
            mode = f["mode"]
            # 获取本建筑所在 scope 的候选集
            if scope == "district":
                blk = building_to_block[b]
                dist = block_to_district[blk]
                candidates = scope_index["district"][dist]
            else:
                blk = building_to_block[b]
                candidates = scope_index["block"][blk]
            # 排序（高分靠前）
            sorted_bs = sorted(candidates, key=lambda x: features_by_building[x][feat], reverse=True)
            topk = set(sorted_bs[:k])
            res = (b in topk) if mode == "in_top_k" else (b not in topk)
            results.append(res)
        elif f["type"] == "composite_score":
            score = _compute_composite_score(features_by_building[b], f["weights"])
            op = f["op"]
            th = f["threshold"]
            res = (score >= th) if op == ">=" else (score <= th)
            results.append(res)
        else:
            results.append(False)

    if not results:
        return True
    mode = filter_agg["mode"]
    if mode == "AND":
        return all(results)
    elif mode == "OR":
        return any(results)
    else:  # K_OF_N
        k = int(filter_agg.get("k", 1))
        return sum(1 for r in results if r) >= k


def function_2(
    city_name: str,
    region_num: int,
    district_min: int,
    district_max: int,
    block_min: int,
    block_max: int,
    building_min: int,
    building_max: int,
    grade_choices: List[str],
    a_prob: float,
    eco_range: List[int],
    noise_range: List[int],
    height_range: List[int],
    occup_range: List[int],
    max_search_seconds: int,
    max_attempts: int,
) -> Dict[str, object]:
    """
    随机生成城市树、隐式属性、堂兄弟定义与复合过滤器，并在墙钟限制与次数限制内重采样保证唯一解。
    返回：
      结构映射、属性、规则与可读文本，以及唯一解标记 unique_ok。
    """
    start = time.time()

    # 生成大区
    regions = _gen_region_names(region_num)
    # 为每个大区随机分配区的数量
    district_counts = [random.randint(district_min, max(district_min, district_max)) for _ in regions]
    total_districts = sum(district_counts)
    district_names = _gen_district_names(total_districts)
    # 分配区到各大区
    districts_by_region: Dict[str, List[str]] = {}
    cursor = 0
    for r, cnt in zip(regions, district_counts):
        districts_by_region[r] = district_names[cursor : cursor + cnt]
        cursor += cnt
    # 为每个区随机分配街区数量，并全局生成街区名
    block_counts: Dict[str, int] = {}
    total_blocks = 0
    for dlist in districts_by_region.values():
        for d in dlist:
            cnt = random.randint(block_min, max(block_min, block_max))
            block_counts[d] = cnt
            total_blocks += cnt
    block_names = _gen_block_names(total_blocks)
    # 分配街区到区
    blocks_by_district: Dict[str, List[str]] = {}
    cursor = 0
    for d in district_names:
        cnt = block_counts[d]
        blocks_by_district[d] = block_names[cursor : cursor + cnt]
        cursor += cnt
    # 为每个街区分配建筑数量，并全局生成建筑名
    building_counts: Dict[str, int] = {}
    total_buildings = 0
    for blist in blocks_by_district.values():
        for b in blist:
            cnt = random.randint(building_min, max(building_min, building_max))
            building_counts[b] = cnt
            total_buildings += cnt
    building_names = _gen_building_names(total_buildings)
    # 分配建筑到街区
    buildings_by_block: Dict[str, List[str]] = {}
    cursor = 0
    for b in block_names:
        cnt = building_counts[b]
        buildings_by_block[b] = building_names[cursor : cursor + cnt]
        cursor += cnt
    # 反向映射
    building_to_block, block_to_district, district_to_region = _build_inverse_maps(
        buildings_by_block, blocks_by_district, districts_by_region
    )
    # 赋环保等级
    grade_by_building: Dict[str, str] = {b: (grade_choices[0] if random.random() < a_prob else grade_choices[1]) for b in building_names}
    # 生成隐式属性（整数）
    def rand_in_range(rng: List[int]) -> int:
        return random.randint(min(rng[0], rng[1]), max(rng[0], rng[1]))
    features_by_building: Dict[str, Dict[str, int]] = {}
    for b in building_names:
        features_by_building[b] = {
            "eco": rand_in_range(eco_range),
            "noise": rand_in_range(noise_range),
            "height": rand_in_range(height_range),
            "occup": rand_in_range(occup_range),
        }

    # scope 索引（用于排名）
    district_index: Dict[str, List[str]] = {}
    block_index: Dict[str, List[str]] = {}
    for d in district_names:
        district_index[d] = []
    for blk, blist in buildings_by_block.items():
        block_index[blk] = list(blist)
        d = block_to_district[blk]
        district_index[d].extend(blist)
    scope_index = {"district": district_index, "block": block_index}

    # 目标建筑（参照）
    target_building = random.choice(building_names)

    # 构造唯一解：尝试采样堂兄弟定义与过滤器直到得到唯一候选
    unique_ok = False
    chosen_cousin_def = None
    chosen_filters_machine: List[Dict[str, Any]] = []
    chosen_filter_agg: Dict[str, Any] = {}
    answer_name = "unknown"

    attempts = 0
    while attempts < max_attempts and (time.time() - start) < max_search_seconds:
        attempts += 1
        # 堂兄弟定义
        cousin_def = _choose_cousin_definition()
        # 复合过滤器：2~4 条
        num_filters = random.randint(2, 4)
        filters_machine: List[Dict[str, Any]] = []
        # 多样化选择池
        for _ in range(num_filters):
            t = random.random()
            if t < 0.25:
                filters_machine.append(_grade_filter(grade_choices))
            elif t < 0.50:
                filters_machine.append(_location_filter(regions, district_names, block_names))
            elif t < 0.75:
                filters_machine.append(_feature_threshold_filter(features_by_building))
            else:
                # 排名或复合分数
                if random.random() < 0.5:
                    scope_choice = random.choice(["district", "block"])
                    feat_choice = random.choice(FEATURE_KEYS)
                    # k_max 设为本作用域内平均 2~3
                    k_max = 3
                    filters_machine.append(_rank_filter(scope_choice, feat_choice, k_max))
                else:
                    # 复合分数权重（0.2~1.0）
                    weights = {k: random.uniform(0.2, 1.0) for k in FEATURE_KEYS}
                    # 阈值基于全体建筑复合分的中位附近
                    scores = [_compute_composite_score(features_by_building[b], weights) for b in building_names]
                    threshold = random.choice(scores)
                    filters_machine.append(_composite_score_filter(weights, threshold))

        # 聚合器
        mode = random.choice(["AND", "OR", "K_OF_N"])
        if mode == "K_OF_N":
            k = random.randint(1, num_filters)
            filter_agg = {"mode": "K_OF_N", "k": k}
        else:
            filter_agg = {"mode": mode}

        # 计算候选集合
        # 堂兄弟：share_levels 全相同；not_share_levels 至少一个不同
        share_lv = cousin_def["share_levels"]
        not_lv = cousin_def["not_share_levels"]
        tgt_share_vals = [ _get_level_value_for_building(target_building, city_name, building_to_block, block_to_district, district_to_region, lv) for lv in share_lv ]
        tgt_not_vals = [ _get_level_value_for_building(target_building, city_name, building_to_block, block_to_district, district_to_region, lv) for lv in not_lv ]

        candidates: List[str] = []
        for b in building_names:
            if b == target_building:
                continue
            # share 相同
            share_ok = True
            for i, lv in enumerate(share_lv):
                v = _get_level_value_for_building(b, city_name, building_to_block, block_to_district, district_to_region, lv)
                if v != tgt_share_vals[i] or v is None or tgt_share_vals[i] is None:
                    share_ok = False
                    break
            if not share_ok:
                continue
            # not_share 至少一个不同
            not_ok = False
            for i, lv in enumerate(not_lv):
                v = _get_level_value_for_building(b, city_name, building_to_block, block_to_district, district_to_region, lv)
                if v is None or tgt_not_vals[i] is None:
                    continue
                if v != tgt_not_vals[i]:
                    not_ok = True
                    break
            if not not_ok:
                continue
            # 过滤器
            if _evaluate_filters_for_building(
                b, city_name, building_to_block, block_to_district, district_to_region,
                grade_by_building, features_by_building, filters_machine, filter_agg, scope_index
            ):
                candidates.append(b)

        if len(candidates) == 1:
            unique_ok = True
            chosen_cousin_def = cousin_def
            chosen_filters_machine = filters_machine
            chosen_filter_agg = filter_agg
            answer_name = candidates[0]
            break

    # 文本生成
    overview_text, attributes_text = _build_overview_and_attributes(
        city_name, regions, districts_by_region, blocks_by_district, buildings_by_block, grade_by_building, features_by_building
    )
    # 堂兄弟定义文本
    share_txt = "与参照建筑在" + "与".join([LEVELS_CN[lv] for lv in (chosen_cousin_def or cousin_def)["share_levels"]]) + "相同"
    not_txt = "且在" + "或".join([LEVELS_CN[lv] for lv in (chosen_cousin_def or cousin_def)["not_share_levels"]]) + "不同"
    rule_text = f"{share_txt}{not_txt}"
    # 过滤条件文本
    filters_used = chosen_filters_machine if chosen_filters_machine else filters_machine
    filter_text = "; ".join(f["text"] for f in filters_used)
    # 聚合逻辑文本
    filter_agg_used = chosen_filter_agg if chosen_filter_agg else filter_agg
    if filter_agg_used["mode"] == "AND":
        filter_agg_text = "同时满足全部条件"
    elif filter_agg_used["mode"] == "OR":
        filter_agg_text = "满足任一条件"
    else:
        filter_agg_text = f"至少满足其中{filter_agg_used['k']}条条件"

    return {
        "city": city_name,
        "regions": regions,
        "districts_by_region": districts_by_region,
        "blocks_by_district": blocks_by_district,
        "buildings_by_block": buildings_by_block,
        "grade_by_building": grade_by_building,
        "features_by_building": features_by_building,
        "target_building": target_building,
        "cousin_def": chosen_cousin_def if chosen_cousin_def else cousin_def,
        "filters_machine": filters_used,
        "filter_agg": filter_agg_used,
        "overview_text": overview_text,
        "attributes_text": attributes_text,
        "rule_text": rule_text,
        "filter_text": filter_text,
        "filter_agg_text": filter_agg_text,
        "unique_ok": unique_ok,
    }


def function_1(
    city: str,
    target_building: str,
    buildings_by_block: Dict[str, List[str]],
    grade_by_building: Dict[str, str],
    blocks_by_district: Dict[str, List[str]],
    districts_by_region: Dict[str, List[str]],
    features_by_building: Dict[str, Dict[str, int]],
    cousin_def: Dict[str, List[str]],
    filters_machine: List[Dict[str, Any]],
    filter_agg: Dict[str, Any],
) -> str:
    """
    依据生成的多层次堂兄弟定义与复合过滤器，计算唯一满足条件的建筑名称。
    若集合为空或非唯一，返回 'unknown'。
    """
    building_to_block, block_to_district, district_to_region = _build_inverse_maps(
        buildings_by_block, blocks_by_district, districts_by_region
    )

    # scope 索引（用于排名）
    district_index: Dict[str, List[str]] = {}
    block_index: Dict[str, List[str]] = {}
    for d, blist in blocks_by_district.items():
        district_index[d] = []
    for blk, blist in buildings_by_block.items():
        block_index[blk] = list(blist)
        d = block_to_district[blk]
        district_index[d].extend(blist)
    scope_index = {"district": district_index, "block": block_index}

    share_lv = cousin_def["share_levels"]
    not_lv = cousin_def["not_share_levels"]
    tgt_share_vals = [
        _get_level_value_for_building(target_building, city, building_to_block, block_to_district, district_to_region, lv)
        for lv in share_lv
    ]
    tgt_not_vals = [
        _get_level_value_for_building(target_building, city, building_to_block, block_to_district, district_to_region, lv)
        for lv in not_lv
    ]

    candidates: List[str] = []
    # 全体建筑
    all_buildings = []
    for bl in buildings_by_block.values():
        all_buildings.extend(bl)
    for b in all_buildings:
        if b == target_building:
            continue
        # share 相同
        share_ok = True
        for i, lv in enumerate(share_lv):
            v = _get_level_value_for_building(b, city, building_to_block, block_to_district, district_to_region, lv)
            if v != tgt_share_vals[i] or v is None or tgt_share_vals[i] is None:
                share_ok = False
                break
        if not share_ok:
            continue
        # not_share 至少一个不同
        not_ok = False
        for i, lv in enumerate(not_lv):
            v = _get_level_value_for_building(b, city, building_to_block, block_to_district, district_to_region, lv)
            if v is None or tgt_not_vals[i] is None:
                continue
            if v != tgt_not_vals[i]:
                not_ok = True
                break
        if not not_ok:
            continue
        # 过滤器评估
        if _evaluate_filters_for_building(
            b, city, building_to_block, block_to_district, district_to_region,
            grade_by_building, features_by_building, filters_machine, filter_agg, scope_index
        ):
            candidates.append(b)

    if len(candidates) != 1:
        return "unknown"
    return candidates[0]