# file: object_counting_6.py
from typing import List, Tuple

def _clamp_nonneg(x: int) -> int:
    return x if x >= 0 else 0

def clothes_rule_name(code: int) -> str:
    names = ['鞋因尺码错误退回', '鞋有部分报损', '上衣有部分借出', '裤装有部分暂不可用']
    if 0 <= code < len(names):
        return names[code]
    return '无调整'

def vehicles_rule_name(code: int) -> str:
    names = ['SUV报废与轿车借出', '厢式车借出', '轿车借出与SUV小范围报废']
    if 0 <= code < len(names):
        return names[code]
    return '无调整'

def compute_thr_vehicle(vans_bought: int, suv_bought: int, sedan_bought: int) -> int:
    total = _clamp_nonneg(vans_bought) + _clamp_nonneg(suv_bought) + _clamp_nonneg(sedan_bought)
    tv = total // 5
    return tv if tv >= 1 else 1

def compute_thr_clothes(tops_in: int, pants_in: int, shoes_in: int) -> int:
    total = _clamp_nonneg(tops_in) + _clamp_nonneg(pants_in) + _clamp_nonneg(shoes_in)
    tc = total // 6
    return tc if tc >= 1 else 1

def compute_wh_cap(tops_in: int, pants_in: int, shoes_in: int,
                   vans_bought: int, suv_bought: int, sedan_bought: int) -> int:
    # 仓储上限：max(100, floor(服装入库总件数/2) + 50)
    total_clothes_in = _clamp_nonneg(tops_in) + _clamp_nonneg(pants_in) + _clamp_nonneg(shoes_in)
    w = total_clothes_in // 2 + 50
    return w if w >= 100 else 100

def _apply_clothes_local(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int
) -> Tuple[int, int, int]:
    tops = _clamp_nonneg(tops_in)
    pants = _clamp_nonneg(pants_in)
    shoes = _clamp_nonneg(shoes_in)

    if clothes_rule_code == 0:
        shoes = _clamp_nonneg(shoes - _clamp_nonneg(shoes_returned))
    elif clothes_rule_code == 1:
        shoes = _clamp_nonneg(shoes - _clamp_nonneg(shoes_damaged))
    elif clothes_rule_code == 2:
        tops = _clamp_nonneg(tops - _clamp_nonneg(tops_borrowed))
    elif clothes_rule_code == 3:
        pants = _clamp_nonneg(pants - _clamp_nonneg(pants_reserved))
    # else: 无调整
    return tops, pants, shoes

def _apply_vehicles_local(
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> Tuple[int, int, int]:
    vans = _clamp_nonneg(vans_bought)
    suv = _clamp_nonneg(suv_bought)
    sedan = _clamp_nonneg(sedan_bought)

    if vehicles_rule_code == 0:
        suv = _clamp_nonneg(suv - _clamp_nonneg(suv_scrapped))
        sedan = _clamp_nonneg(sedan - _clamp_nonneg(sedan_borrowed))
    elif vehicles_rule_code == 1:
        vans = _clamp_nonneg(vans - _clamp_nonneg(vans_borrowed_var))
    elif vehicles_rule_code == 2:
        suv = _clamp_nonneg(suv - _clamp_nonneg(suv_scrapped))
        sedan = _clamp_nonneg(sedan - _clamp_nonneg(sedan_borrowed))
    # else: 无调整
    return vans, suv, sedan

def _safety_review_adjust(
    vans: int, suv: int, sedan: int,
    suv_scrapped: int, vehicles_rule_code: int
) -> Tuple[int, int, int]:
    # 若规则包含SUV报废环节且报废数>0，则额外有1辆SUV进入复核暂不可用
    if vehicles_rule_code in (0, 2) and _clamp_nonneg(suv_scrapped) > 0:
        suv = _clamp_nonneg(suv - 1)
    return vans, suv, sedan

def _cross_link_adjust(
    tops_in: int, pants_in: int, shoes_in: int,
    tops: int, pants: int, shoes: int,
    vans_bought: int, suv_bought: int, sedan_bought: int,
    vans: int, suv: int, sedan: int,
    tops_borrowed: int, vans_borrowed_var: int,
    tv: int, tc: int
) -> Tuple[int, int, int, int, int, int, bool, bool]:
    # 车辆损失与服装损失
    vehicle_loss = (_clamp_nonneg(vans_bought) + _clamp_nonneg(suv_bought) + _clamp_nonneg(sedan_bought)) - (vans + suv + sedan)
    clothes_loss = (_clamp_nonneg(tops_in) + _clamp_nonneg(pants_in) + _clamp_nonneg(shoes_in)) - (tops + pants + shoes)

    link_vehicle_applied = False
    link_clothes_applied = False

    # 若车辆损失≥Tv，则服装部紧急调回 up to Tv 件上衣（不超过借出数与入库上限）
    if vehicle_loss >= tv:
        recall_tops = tops_borrowed if tops_borrowed <= tv else tv
        new_tops = min(_clamp_nonneg(tops_in), tops + _clamp_nonneg(recall_tops))
        if new_tops != tops:
            link_vehicle_applied = True
        tops = new_tops

    # 若服装损失≥Tc，则车辆部临时调回 up to Tc 辆厢式车（不超过借出数与采购上限）
    if clothes_loss >= tc:
        recall_vans = vans_borrowed_var if vans_borrowed_var <= tc else tc
        new_vans = min(_clamp_nonneg(vans_bought), vans + _clamp_nonneg(recall_vans))
        if new_vans != vans:
            link_clothes_applied = True
        vans = new_vans

    return tops, pants, shoes, vans, suv, sedan, link_vehicle_applied, link_clothes_applied

def _apply_warehouse_cap(
    tops: int, pants: int, shoes: int, wh_cap: int
) -> Tuple[int, int, int, bool]:
    total = tops + pants + shoes
    if total <= wh_cap:
        return tops, pants, shoes, False
    overflow = total - wh_cap
    applied = overflow > 0

    # 先扣鞋，再扣上衣，再扣裤装
    reduce_shoes = min(shoes, overflow)
    shoes -= reduce_shoes
    overflow -= reduce_shoes
    if overflow <= 0:
        return tops, pants, shoes, applied

    reduce_tops = min(tops, overflow)
    tops -= reduce_tops
    overflow -= reduce_tops
    if overflow <= 0:
        return tops, pants, shoes, applied

    reduce_pants = min(pants, overflow)
    pants -= reduce_pants
    overflow -= reduce_pants
    # 溢出应为0
    return tops, pants, shoes, applied

def _gcd(a: int, b: int) -> int:
    if a < 0: a = -a
    if b < 0: b = -b
    while b:
        a, b = b, a % b
    return a

def _compute_coupled_totals(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> Tuple[int, int]:
    # 1) 各自局部规则
    tops, pants, shoes = _apply_clothes_local(
        tops_in, pants_in, shoes_in, shoes_returned,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged
    )
    vans, suv, sedan = _apply_vehicles_local(
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        vehicles_rule_code, vans_borrowed_var
    )

    # 2) 安全复核（车辆）
    vans, suv, sedan = _safety_review_adjust(vans, suv, sedan, suv_scrapped, vehicles_rule_code)

    # 3) 双向联动（服装↔车辆）
    tv = compute_thr_vehicle(vans_bought, suv_bought, sedan_bought)
    tc = compute_thr_clothes(tops_in, pants_in, shoes_in)
    tops, pants, shoes, vans, suv, sedan, _, _ = _cross_link_adjust(
        tops_in, pants_in, shoes_in,
        tops, pants, shoes,
        vans_bought, suv_bought, sedan_bought,
        vans, suv, sedan,
        tops_borrowed, vans_borrowed_var,
        tv, tc
    )

    # 4) 仓储上限对服装生效
    wh_cap = compute_wh_cap(tops_in, pants_in, shoes_in, vans_bought, suv_bought, sedan_bought)
    tops, pants, shoes, _ = _apply_warehouse_cap(tops, pants, shoes, wh_cap)

    clothes_total = _clamp_nonneg(tops) + _clamp_nonneg(pants) + _clamp_nonneg(shoes)
    vehicles_total = _clamp_nonneg(vans) + _clamp_nonneg(suv) + _clamp_nonneg(sedan)
    return clothes_total, vehicles_total

def _compute_process_flags(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> Tuple[bool, bool, bool]:
    """
    返回三个触发标志：
    - 安全复核是否实际产生影响（SUV数量减少1）
    - 双向联动是否产生实际影响（服装或车辆一侧至少有一次调回导致数量变化）
    - 仓储上限是否实际生效（发生扣减）
    """
    # 1) 局部规则
    tops, pants, shoes = _apply_clothes_local(
        tops_in, pants_in, shoes_in, shoes_returned,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged
    )
    vans, suv, sedan = _apply_vehicles_local(
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        vehicles_rule_code, vans_borrowed_var
    )

    # 2) 安全复核前后对比
    suv_before = suv
    vans, suv, sedan = _safety_review_adjust(vans, suv, sedan, suv_scrapped, vehicles_rule_code)
    safety_applied = suv != suv_before

    # 3) 联动是否产生数量变化
    tv = compute_thr_vehicle(vans_bought, suv_bought, sedan_bought)
    tc = compute_thr_clothes(tops_in, pants_in, shoes_in)
    tops_before, vans_before = tops, vans
    tops, pants, shoes, vans, suv, sedan, link_vehicle_applied, link_clothes_applied = _cross_link_adjust(
        tops_in, pants_in, shoes_in,
        tops, pants, shoes,
        vans_bought, suv_bought, sedan_bought,
        vans, suv, sedan,
        tops_borrowed, vans_borrowed_var,
        tv, tc
    )
    link_applied = link_vehicle_applied or link_clothes_applied

    # 4) 仓储上限是否生效
    wh_cap = compute_wh_cap(tops_in, pants_in, shoes_in, vans_bought, suv_bought, sedan_bought)
    pre_cap_total = tops + pants + shoes
    tops, pants, shoes, cap_applied = _apply_warehouse_cap(tops, pants, shoes, wh_cap)
    # cap_applied 已反映是否扣减

    return safety_applied, link_applied, cap_applied

# 公开的运算接口：供YAML使用
def compute_available_clothes(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int
) -> int:
    # 返回服装在局部规则下的合计值
    t, p, s = _apply_clothes_local(
        tops_in, pants_in, shoes_in, shoes_returned,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged
    )
    return _clamp_nonneg(t) + _clamp_nonneg(p) + _clamp_nonneg(s)

def compute_available_vehicles(
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> int:
    v, s, d = _apply_vehicles_local(
        vans_bought, suv_bought, sedan_bought,
        sedan_borrowed, suv_scrapped,
        vehicles_rule_code, vans_borrowed_var
    )
    # 不含安全复核，仅用于展示局部规则效果
    return _clamp_nonneg(v) + _clamp_nonneg(s) + _clamp_nonneg(d)

def compute_totals_list(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> Tuple[int, int]:
    # 返回二元组以避免集合包装时的不可哈希错误
    clothes, vehicles = _compute_coupled_totals(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    return (clothes, vehicles)

def compute_diff(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> int:
    clothes, vehicles = _compute_coupled_totals(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    d = clothes - vehicles
    return d if d >= 0 else -d

def compute_ratio(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> str:
    clothes, vehicles = _compute_coupled_totals(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    total = clothes + vehicles
    if total <= 0:
        return '0/1'
    g = _gcd(clothes, total)
    return f'{clothes // g}/{total // g}'

def validate_instance(
    tops_in: int,
    pants_in: int,
    shoes_in: int,
    shoes_returned: int,
    vans_bought: int,
    suv_bought: int,
    sedan_bought: int,
    sedan_borrowed: int,
    suv_scrapped: int,
    clothes_rule_code: int,
    tops_borrowed: int,
    pants_reserved: int,
    shoes_damaged: int,
    vehicles_rule_code: int,
    vans_borrowed_var: int
) -> bool:
    # 合理性与一致性验证
    clothes, vehicles = _compute_coupled_totals(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    if clothes < 0 or vehicles < 0:
        return False
    if clothes + vehicles <= 0:
        return False

    # 触发至少一个非局部环节（安全复核或联动或仓储上限）
    safety_applied, link_applied, cap_applied = _compute_process_flags(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    if not (safety_applied or link_applied or cap_applied):
        return False

    # 比例字符串基本格式检查与最简要求
    ratio = compute_ratio(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    if '/' not in ratio:
        return False
    if ' ' in ratio:
        return False
    try:
        p, q = ratio.split('/')
        p_i = int(p)
        q_i = int(q)
        if q_i <= 0 or p_i < 0:
            return False
    except Exception:
        return False

    # 绝对差与二元组一致性检查
    diff = compute_diff(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    pair = compute_totals_list(
        tops_in, pants_in, shoes_in, shoes_returned,
        vans_bought, suv_bought, sedan_bought, sedan_borrowed, suv_scrapped,
        clothes_rule_code, tops_borrowed, pants_reserved, shoes_damaged,
        vehicles_rule_code, vans_borrowed_var
    )
    if len(pair) != 2:
        return False
    if abs(pair[0] - pair[1]) != diff:
        return False

    return True