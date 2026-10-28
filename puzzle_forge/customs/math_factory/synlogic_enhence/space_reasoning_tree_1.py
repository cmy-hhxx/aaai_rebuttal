# space_reasoning_tree_4.py
# ============================================================================
# 高阶泛化版自定义辅助函数库（修订版；题面不暴露唯一性提示）
# - 组合式SKU名称生成器function_8替代超大Faker唯一池，避免唯一性不足报错。
# - 唯一性模块function_7通过叠加可见约束（行掩码/枢纽/模数/地区集合调整）实现唯一解。
# - 题面仅渲染可见约束，逻辑清晰且需多步推理。
# ============================================================================

from typing import Dict, List, Any, Tuple, Optional
import random
import time


# ------------------------- 通用工具 ------------------------- #
def _unique_pop(pool: List[str]) -> str:
    """
    从名称池中随机抽取一个唯一名称，并从池中移除，保证后续不会重复。
    若池空，则回退生成一个备用名称（极少发生）。
    """
    if pool:
        idx = random.randrange(len(pool))
        return pool.pop(idx)
    return f"备用产品{random.randint(10000, 99999)}"


def _find_parent_line_and_group(
    sku_data: Dict[str, List[Dict[str, Any]]],
    product_lines_by_group: Dict[str, List[str]],
    target_sku_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    根据目标SKU名称，找出其父产品线与所属事业群。
    """
    parent_line = None
    for line, skus in sku_data.items():
        for item in skus:
            if str(item.get("name", "")) == target_sku_name:
                parent_line = line
                break
        if parent_line is not None:
            break

    if parent_line is None:
        return None, None

    group_name = None
    for g, lines in product_lines_by_group.items():
        if parent_line in lines:
            group_name = g
            break

    return parent_line, group_name


def _collect_relation_candidates(
    sku_data: Dict[str, List[Dict[str, Any]]],
    product_lines_by_group: Dict[str, List[str]],
    parent_line: str,
    group_name: str,
    target_sku_name: str,
    relation_type: str,
) -> List[Dict[str, Any]]:
    """
    根据关系类型收集候选SKU字典对象列表。
    """
    candidates: List[Dict[str, Any]] = []

    if relation_type == "same_group_diff_line":
        # 同事业群但不同父产品线（类似堂兄弟）
        for line in product_lines_by_group.get(group_name, []):
            if line == parent_line:
                continue
            candidates.extend(sku_data.get(line, []))

    elif relation_type == "same_line_diff_sku":
        # 同一父产品线但不同SKU（类似兄弟）
        for item in sku_data.get(parent_line, []):
            if str(item.get("name", "")) != target_sku_name:
                candidates.append(item)

    elif relation_type == "same_group_any_line_excluding_self":
        # 同一事业群内所有SKU，排除自身
        for line in product_lines_by_group.get(group_name, []):
            for item in sku_data.get(line, []):
                if str(item.get("name", "")) != target_sku_name:
                    candidates.append(item)

    return candidates


def _name_to_line_map(sku_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    """
    构造SKU名称到所属产品线的映射。
    """
    mapping: Dict[str, str] = {}
    for line, skus in sku_data.items():
        for item in skus:
            nm = str(item.get("name", ""))
            if nm:
                mapping[nm] = line
    return mapping


# ------------------------- 组合式SKU名称生成器 ------------------------- #
def function_8(groups_num: int, line_range: List[int], sku_range: List[int]) -> List[str]:
    """
    根据规模安全生成足量唯一SKU名称。
    需要量估计 = groups_num * line_range[1] * sku_range[1] + 安全余量(50)
    名称生成策略：前缀(形容词) + 主题(名词) + 序号 的组合，保证唯一。
    """
    max_lines = int(line_range[1])
    max_skus = int(sku_range[1])
    need = max(10, groups_num * max_lines * max_skus + 50)
    adjs = [
        "云", "星", "影", "火", "光", "蓝", "天", "迅", "锐", "卓",
        "极", "新", "超", "晶", "智", "灵", "迅驰", "浩", "霆", "曜",
    ]
    nouns = [
        "影", "航", "翼", "驰", "途", "雷", "浪", "峰", "巅", "耀",
        "擎", "云", "星", "光", "弧", "甲", "盾", "辰", "霄", "澜",
    ]
    names: List[str] = []
    idx = 1
    while len(names) < need:
        a = random.choice(adjs)
        n = random.choice(nouns)
        names.append(f"{a}{n}{idx}")
        idx += 1
    random.shuffle(names)
    return names


# ------------------------- 随机树构造 ------------------------- #
def function_3(
    groups: List[str],
    line_range: List[int],
    sku_range: List[int],
    version_range: List[int],
    region_pool: List[str],
    sku_name_pool: List[str],
) -> Dict[str, Any]:
    """
    随机构造层级树，并选取一个目标SKU。
    """
    # 生成产品线（对每个事业群）
    product_lines_by_group: Dict[str, List[str]] = {}
    all_lines: List[Tuple[str, str]] = []  # (group, line)
    for gi, g in enumerate(groups):
        line_count = random.randint(int(line_range[0]), int(line_range[1]))
        lines = [f"G{gi + 1}_L{j + 1}" for j in range(line_count)]
        product_lines_by_group[g] = lines
        for ln in lines:
            all_lines.append((g, ln))

    # 生成SKU数据（每条产品线）
    sku_data: Dict[str, List[Dict[str, Any]]] = {}
    all_sku_names: List[str] = []
    for _, line_name in all_lines:
        sku_count = random.randint(int(sku_range[0]), int(sku_range[1]))
        line_skus: List[Dict[str, Any]] = []
        for _ in range(sku_count):
            sku_name = _unique_pop(sku_name_pool)
            version = random.randint(int(version_range[0]), int(version_range[1]))
            # 随机确定地区数量：偏向1-2个地区
            k = random.choice([1, 1, 1, 2, 2, 3])
            k = min(k, len(region_pool))
            regions = random.sample(region_pool, k)
            item = {"name": sku_name, "version": version, "regions": regions}
            line_skus.append(item)
            all_sku_names.append(sku_name)
        sku_data[line_name] = line_skus

    # 随机选取一个目标SKU名称
    target_sku_name = random.choice(all_sku_names) if all_sku_names else "备用产品X"

    return {
        "product_lines_by_group": product_lines_by_group,
        "sku_data": sku_data,
        "target_sku_name": target_sku_name,
    }


# ------------------------- 基础规则生成 ------------------------- #
def _rand_bool(p_true: float = 0.5) -> bool:
    return random.random() < p_true


def function_5(version_range: List[int], region_pool: List[str]) -> Dict[str, Any]:
    """
    基础随机规则配置（初始可见约束的基座）：
    - version_rule: 操作符/阈值与启用标记。
    - region_rule: 类型/集合与启用标记。
    - extra_rules: 0-2个附加约束（version_mod/region_count_min/region_count_max）。
    """
    op = random.choice(["gt", "ge", "lt", "le"])
    threshold = random.randint(int(version_range[0]), max(int(version_range[0]), int(version_range[1]) - 1))
    version_enabled = _rand_bool(0.8)  # 80%概率启用版本规则

    region_rule_type = random.choice(["include_any", "exclude_any", "include_all"])
    k = random.choice([1, 1, 2, 2, 3])  # 偏向选择较小集合
    k = min(k, len(region_pool))
    regions = random.sample(region_pool, k)
    region_enabled = _rand_bool(0.8)  # 80%概率启用地区规则

    extra_rules: List[Dict[str, Any]] = []
    extra_candidates = ["version_mod", "region_count_min", "region_count_max"]
    random.shuffle(extra_candidates)
    extra_num = random.choice([0, 1, 2])
    for i in range(extra_num):
        kind = extra_candidates[i]
        if kind == "version_mod":
            m = random.choice([2, 3])
            r = random.randint(0, m - 1)
            extra_rules.append({"type": "version_mod", "m": m, "r": r})
        elif kind == "region_count_min":
            extra_rules.append({"type": "region_count_min", "k": random.choice([1, 2])})
        elif kind == "region_count_max":
            extra_rules.append({"type": "region_count_max", "k": random.choice([1, 2, 3])})

    return {
        "version_rule": {"enabled": version_enabled, "op": op, "threshold": threshold},
        "region_rule": {"enabled": region_enabled, "type": region_rule_type, "regions": regions},
        "extra_rules": extra_rules,
    }


# ------------------------- 规则描述渲染（仅可见约束） ------------------------- #
def function_6(target_sku_name: str, rule_config: Dict[str, Any]) -> str:
    """
    生成单行规则描述文本，解释关系类型与可见筛选条件，并提醒答案格式。
    同时解释‘枢纽SKU约束’：枢纽低/高为题面给出的SKU作为参照，用其版本或地区与候选进行比较。
    """
    # 关系类型说明
    mapping = {
        "same_group_diff_line": "亲属定义: 同一事业群但不同父产品线的SKU(类似堂兄弟)",
        "same_line_diff_sku": "亲属定义: 同一父产品线但不同SKU(类似兄弟)",
        "same_group_any_line_excluding_self": "亲属定义: 同一事业群内所有SKU(排除自身)",
    }
    relation_type = str(rule_config.get("relation_type", "same_group_diff_line"))
    relation_part = mapping.get(relation_type, "亲属定义: 同一事业群但不同父产品线的SKU")

    # 版本规则说明
    vr = rule_config.get("version_rule", {})
    v_desc = "版本不作限制"
    if vr.get("enabled", False):
        op_map = {"gt": "大于", "ge": "大于等于", "lt": "小于", "le": "小于等于"}
        v_desc = f"版本需{op_map.get(vr.get('op', 'gt'), '大于')}{vr.get('threshold', 0)}"

    # 地区规则说明
    rr = rule_config.get("region_rule", {})
    r_desc = "上市地区不作限制"
    if rr.get("enabled", False):
        rset = rr.get("regions", [])
        rset_str = "|".join(rset) if rset else ""
        rtype_map = {
            "include_any": "上市地区需至少包含以下之一",
            "include_all": "上市地区需全部包含以下集合",
            "exclude_any": "上市地区需不包含以下任一",
        }
        r_desc = f"{rtype_map.get(rr.get('type', 'include_any'), '上市地区需至少包含以下之一')}({rset_str})"

    # 行掩码说明（可见）
    mask = rule_config.get("line_mask", [])
    mask_desc = f"候选产品线限定为[{', '.join(mask)}]" if mask else ""

    # 枢纽规则说明（可见）
    pivot = rule_config.get("pivot_rules", {})
    pivot_desc = ""
    if pivot:
        mode = pivot.get("mode", "")
        low = pivot.get("low", {})
        high = pivot.get("high", {})
        desc_parts = []
        if mode == "gt_low":
            desc_parts.append(f"版本需大于枢纽低({low.get('name', '')}, 版本:{low.get('version', '')})")
        elif mode == "lt_high":
            desc_parts.append(f"版本需小于枢纽高({high.get('name', '')}, 版本:{high.get('version', '')})")
        elif mode == "between":
            desc_parts.append(
                f"版本需介于枢纽低({low.get('version', '')})与枢纽高({high.get('version', '')})之间"
            )
        # 不常见定义解释：共享或避免关系
        if pivot.get("share_any_with_high", False):
            desc_parts.append(
                f"上市地区需与枢纽高({high.get('name', '')})至少有一个重叠"
            )
        if pivot.get("avoid_any_of_low", False):
            desc_parts.append(
                f"上市地区不得包含枢纽低({low.get('name', '')})的任一地区"
            )
        pivot_desc = "; ".join(desc_parts)

    # 额外规则说明（可见）
    extras = rule_config.get("extra_rules", [])
    if not extras:
        e_desc = ""
    else:
        parts = []
        for ex in extras:
            if ex.get("type") == "version_mod":
                parts.append(f"版本需满足version%{ex.get('m', 1)}=={ex.get('r', 0)}")
            elif ex.get("type") == "region_count_min":
                parts.append(f"上市地区数量至少为{ex.get('k', 1)}")
            elif ex.get("type") == "region_count_max":
                parts.append(f"上市地区数量至多为{ex.get('k', 3)}")
        e_desc = "; ".join(parts)

    parts = [
        f"以目标SKU({target_sku_name})为中心, {relation_part}",
        f"过滤条件: {v_desc}",
        f"{r_desc}",
        f"{mask_desc}" if mask_desc else "",
        f"{pivot_desc}" if pivot_desc else "",
        f"{e_desc}" if e_desc else "",
        "答案格式: 输出满足条件的SKU名称; 若有多个请按字母顺序并用逗号分隔; 若无满足条件请写unknown",
    ]
    return "; ".join([p for p in parts if p])


# ------------------------- 过滤判定（仅可见约束） ------------------------- #
def _version_ok(version: int, vr: Dict[str, Any]) -> bool:
    if not vr.get("enabled", False):
        return True
    op = vr.get("op", "gt")
    t = int(vr.get("threshold", 0))
    if op == "gt":
        return version > t
    if op == "ge":
        return version >= t
    if op == "lt":
        return version < t
    if op == "le":
        return version <= t
    return True


def _region_ok(regions: List[str], rr: Dict[str, Any]) -> bool:
    if not rr.get("enabled", False):
        return True
    rset = rr.get("regions", [])
    rtype = rr.get("type", "include_any")
    if not rset:
        return True
    s = set(regions)
    R = set(rset)
    if rtype == "include_any":
        return len(s.intersection(R)) > 0
    if rtype == "include_all":
        return R.issubset(s)
    if rtype == "exclude_any":
        return len(s.intersection(R)) == 0
    return True


def _extra_ok(item: Dict[str, Any], extras: List[Dict[str, Any]]) -> bool:
    """
    检查可见的附加约束是否满足。
    """
    version = int(item.get("version", -10))
    regions = list(item.get("regions", []))
    for ex in extras:
        t = ex.get("type")
        if t == "version_mod":
            m = int(ex.get("m", 1))
            r = int(ex.get("r", 0))
            if m <= 0:
                continue
            if version % m != r:
                return False
        elif t == "region_count_min":
            k = int(ex.get("k", 1))
            if len(regions) < k:
                return False
        elif t == "region_count_max":
            k = int(ex.get("k", 3))
            if len(regions) > k:
                return False
    return True


def _pivot_ok(item: Dict[str, Any], pivot: Dict[str, Any]) -> bool:
    """
    检查可见的枢纽约束：版本与地区关系。
    """
    if not pivot:
        return True
    version = int(item.get("version", -10))
    regions = set(item.get("regions", []))
    mode = pivot.get("mode", "")
    low = pivot.get("low", {})
    high = pivot.get("high", {})
    lv = low.get("version", None)
    hv = high.get("version", None)

    # 版本关系
    if mode == "gt_low" and lv is not None:
        if not (version > int(lv)):
            return False
    elif mode == "lt_high" and hv is not None:
        if not (version < int(hv)):
            return False
    elif mode == "between" and (lv is not None) and (hv is not None):
        if not (int(lv) < version < int(hv)):
            return False

    # 地区关系
    if pivot.get("share_any_with_high", False):
        high_regions = set(high.get("regions", []))
        if len(regions.intersection(high_regions)) == 0:
            return False
    if pivot.get("avoid_any_of_low", False):
        low_regions = set(low.get("regions", []))
        if len(regions.intersection(low_regions)) > 0:
            return False

    return True


# ------------------------- 主过滤函数（仅可见约束） ------------------------- #
def function_1(
    sku_data: Dict[str, List[Dict[str, Any]]],
    product_lines_by_group: Dict[str, List[str]],
    target_sku_name: str,
    rule_config: Dict[str, Any],
) -> List[str]:
    """
    根据最终可见规则配置计算候选集合并进行条件过滤（不使用隐式tie-breaker）。
    """
    parent_line, group_name = _find_parent_line_and_group(
        sku_data, product_lines_by_group, target_sku_name
    )
    if parent_line is None or group_name is None:
        return []

    # 收集关系候选
    relation_type = str(rule_config.get("relation_type", "same_group_diff_line"))
    candidates = _collect_relation_candidates(
        sku_data, product_lines_by_group, parent_line, group_name, target_sku_name, relation_type
    )

    # 行掩码检查（可见）
    line_mask = set(rule_config.get("line_mask", []))
    name_to_line = _name_to_line_map(sku_data)

    # 应用筛选条件（可见）
    vr = rule_config.get("version_rule", {})
    rr = rule_config.get("region_rule", {})
    extras = rule_config.get("extra_rules", [])
    pivot = rule_config.get("pivot_rules", {})

    results: List[str] = []
    for item in candidates:
        name = str(item.get("name", ""))
        version = int(item.get("version", -10))
        regions = list(item.get("regions", []))

        # 行掩码限定
        if line_mask:
            ln = name_to_line.get(name, None)
            if ln is None or ln not in line_mask:
                continue

        if not _version_ok(version, vr):
            continue
        if not _region_ok(regions, rr):
            continue
        if not _extra_ok(item, extras):
            continue
        if not _pivot_ok(item, pivot):
            continue

        results.append(name)

    # 去重处理，保证唯一性
    unique_results = []
    seen = set()
    for n in results:
        if n and (n not in seen):
            unique_results.append(n)
            seen.add(n)
    return unique_results


# ------------------------- 唯一性约束综合器（仅使用可见约束） ------------------------- #
def function_7(
    sku_data: Dict[str, List[Dict[str, Any]]],
    product_lines_by_group: Dict[str, List[str]],
    target_sku_name: str,
    version_range: List[int],
    region_pool: List[str],
    base_rules: Dict[str, Any],
    time_limit_sec: int,
) -> Dict[str, Any]:
    """
    在给定时限内（≤3分钟）通过叠加可见约束（行掩码/枢纽/模数/地区集合调整）实现唯一解：
    策略：
      1) 选择关系类型与初始版本/地区/额外约束；
      2) 若候选>1，则逐步增强可见约束：行掩码 -> 枢纽(between或gt_low/lt_high) -> version_mod -> 地区集合调整；
      3) 若仍非唯一且时限到达，返回unknown（空集），保持题面与解一致。
    """
    start = time.time()

    parent_line, group_name = _find_parent_line_and_group(
        sku_data, product_lines_by_group, target_sku_name
    )
    if parent_line is None or group_name is None:
        empty_cfg = {
            "relation_type": "same_group_diff_line",
            "version_rule": base_rules.get("version_rule", {}),
            "region_rule": base_rules.get("region_rule", {}),
            "extra_rules": base_rules.get("extra_rules", []),
        }
        return {"rule_config": empty_cfg, "answer_skus": []}

    group_lines = list(product_lines_by_group.get(group_name, []))

    # 尝试不同关系类型以提高可选空间
    relation_types = [
        "same_group_diff_line",
        "same_group_any_line_excluding_self",
        "same_line_diff_sku",
    ]

    # 预先随机一个目标关系类型
    random.shuffle(relation_types)

    for relation_type in relation_types:
        # 初始可见约束：来自base_rules
        version_rule = dict(base_rules.get("version_rule", {}))
        region_rule = dict(base_rules.get("region_rule", {}))
        extras = list(base_rules.get("extra_rules", []))
        line_mask: List[str] = []
        pivot_rules: Dict[str, Any] = {}

        # 初始过滤
        rule_config = {
            "relation_type": relation_type,
            "version_rule": version_rule,
            "region_rule": region_rule,
            "extra_rules": extras,
            "line_mask": line_mask,
            "pivot_rules": pivot_rules,
        }
        ans = function_1(sku_data, product_lines_by_group, target_sku_name, rule_config)
        if len(ans) == 1:
            return {"rule_config": rule_config, "answer_skus": ans}

        # 若候选为空或>1，进入增强阶段
        # 选择一个目标候选（若为空则换关系）
        candidates_full = _collect_relation_candidates(
            sku_data, product_lines_by_group, parent_line, group_name, target_sku_name, relation_type
        )
        if not candidates_full:
            continue

        # 目标候选：随机选取一个作为预期唯一答案
        target_item = random.choice(candidates_full)

        # 增强1：行掩码（限定到包含目标候选的产品线）
        target_line_name = _name_to_line_map(sku_data).get(str(target_item.get("name", "")), None)
        if target_line_name:
            line_mask = [target_line_name]
            rule_config["line_mask"] = line_mask
            ans = function_1(sku_data, product_lines_by_group, target_sku_name, rule_config)
            if len(ans) == 1:
                return {"rule_config": rule_config, "answer_skus": ans}

        # 增强2：枢纽约束（between优先）
        # 选取low与high，使target版本落在两者之间（或使用gt_low/lt_high）
        # 枢纽从候选中取；若数量不足则退化为gt_low或lt_high
        cand_sorted_by_ver = sorted(candidates_full, key=lambda it: int(it.get("version", 0)))
        low = None
        high = None
        t_ver = int(target_item.get("version", 0))
        # 找到小于target的作为low，大于target的作为high
        lows = [it for it in cand_sorted_by_ver if int(it.get("version", 0)) < t_ver]
        highs = [it for it in cand_sorted_by_ver if int(it.get("version", 0)) > t_ver]
        mode = None
        if lows and highs:
            low = random.choice(lows)
            high = random.choice(highs)
            mode = "between"
        elif lows:
            low = random.choice(lows)
            mode = "gt_low"
        elif highs:
            high = random.choice(highs)
            mode = "lt_high"

        if mode:
            pivot_rules = {
                "mode": mode,
                "low": {
                    "name": str((low or target_item).get("name", "")),
                    "version": int((low or target_item).get("version", 0)),
                    "regions": list((low or target_item).get("regions", [])),
                },
                "high": {
                    "name": str((high or target_item).get("name", "")),
                    "version": int((high or target_item).get("version", 0)),
                    "regions": list((high or target_item).get("regions", [])),
                },
                "share_any_with_high": _rand_bool(0.4),
                "avoid_any_of_low": _rand_bool(0.4),
            }
            rule_config["pivot_rules"] = pivot_rules
            ans = function_1(sku_data, product_lines_by_group, target_sku_name, rule_config)
            if len(ans) == 1:
                return {"rule_config": rule_config, "answer_skus": ans}

        # 增强3：version_mod，令target满足且尽量排除其他
        # 选择m ∈ {2,3} 与 r = target.version % m
        m = random.choice([2, 3])
        r = t_ver % m
        # 将version_mod插入extras（可见）
        extras = [ex for ex in extras if ex.get("type") != "version_mod"]
        extras.append({"type": "version_mod", "m": m, "r": r})
        rule_config["extra_rules"] = extras
        ans = function_1(sku_data, product_lines_by_group, target_sku_name, rule_config)
        if len(ans) == 1:
            return {"rule_config": rule_config, "answer_skus": ans}

        # 增强4：地区集合调整
        # 目标的地区集
        t_regs = list(target_item.get("regions", []))
        if t_regs:
            # 优先使用include_all目标的一个或两个地区，提高辨析度
            use_k = 2 if len(t_regs) >= 2 else 1
            pick = random.sample(t_regs, use_k)
            region_rule = {
                "enabled": True,
                "type": random.choice(["include_all", "include_any"]),
                "regions": pick,
            }
            rule_config["region_rule"] = region_rule
            ans = function_1(sku_data, product_lines_by_group, target_sku_name, rule_config)
            if len(ans) == 1:
                return {"rule_config": rule_config, "answer_skus": ans}

        # 若仍非唯一，尝试增加地区数量限制（可见）
        extras = [ex for ex in extras if ex.get("type") != "region_count_min"]
        extras.append({"type": "region_count_min", "k": max(1, len(t_regs))})
        rule_config["extra_rules"] = extras
        ans = function_1(sku_data, product_lines_by_group, target_sku_name, rule_config)
        if len(ans) == 1:
            return {"rule_config": rule_config, "answer_skus": ans}

        # 时限检查
        if time.time() - start > min(time_limit_sec, 180):
            break

    # 超时或无法唯一：返回unknown（空集），题面与解一致
    fallback_cfg = {
        "relation_type": "same_group_diff_line",
        "version_rule": base_rules.get("version_rule", {}),
        "region_rule": base_rules.get("region_rule", {}),
        "extra_rules": base_rules.get("extra_rules", []),
    }
    return {"rule_config": fallback_cfg, "answer_skus": []}


# ------------------------- 答案与描述渲染 ------------------------- #
def function_2(names: List[str]) -> str:
    """
    将SKU名称列表按字母顺序（Python默认Unicode序）排序后，用逗号分隔输出。
    若列表为空，返回'unknown'。
    """
    if not names:
        return "unknown"
    ordered = sorted(names)
    return ",".join(ordered)


def function_4(
    groups: List[str],
    product_lines_by_group: Dict[str, List[str]],
    sku_data: Dict[str, List[Dict[str, Any]]],
) -> str:
    """
    生成单行的树结构描述文本：
    - 列出集团的孩子（事业群）；
    - 对每个事业群列出产品线；
    - 对每条产品线列出SKU及其(版本: x, 上市地区: A|B|...)。
    注意：不使用双引号、不使用直接换行，统一单行输出。
    """
    group_part = f"集团的孩子为[{', '.join(groups)}]"
    group_lines_parts: List[str] = []
    for g in groups:
        lines = product_lines_by_group.get(g, [])
        group_lines_parts.append(f"{g}的孩子为产品线[{', '.join(lines)}]")

    line_sku_parts: List[str] = []
    for g in groups:
        for line in sorted(product_lines_by_group.get(g, [])):
            skus = sku_data.get(line, [])
            sku_details: List[str] = []
            for item in skus:
                name = str(item.get("name", ""))
                version = int(item.get("version", 0))
                regions = list(item.get("regions", []))
                regions_str = "|".join(regions)
                sku_details.append(f"{name}(版本:{version}, 上市地区:{regions_str})")
            part = f"{line}的SKU有[{', '.join(sku_details)}]" if sku_details else f"{line}的SKU有[]"
            line_sku_parts.append(part)

    return "; ".join([group_part] + group_lines_parts + line_sku_parts)