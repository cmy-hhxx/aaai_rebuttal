# object_counting_7.py
from math import gcd

def simplify_ratio(a: int, b: int) -> str:
    """
    返回最简分数表示 a/b，当 b 为 0 时返回 'undefined'。
    分母保持为正，符号放分子上。
    """
    if b == 0:
        return 'undefined'
    g = gcd(abs(a), abs(b))
    num = a // g
    den = b // g
    if den < 0:
        num = -num
        den = -den
    return f'{num}/{den}'

def apply_hold_release(count: int, hold_percent: int, release_num: int, release_den: int) -> int:
    """
    质量抽检并返还：
    - 暂扣 = floor(count * hold_percent / 100)
    - 返还 = floor(暂扣 * release_num / release_den)
    最终 = count - 暂扣 + 返还
    """
    if count <= 0:
        return 0
    hold = (count * hold_percent) // 100
    release = (hold * release_num) // release_den if release_den > 0 else 0
    final_count = count - hold + release
    if final_count < 0:
        final_count = 0
    return final_count

def compute_promo_bonus_shirts(shirts: int, pants: int, shoes_pairs: int, socks_pairs: int,
                               include_socks: bool, promo_k: int, gift_per_batch: int) -> int:
    """
    促销赠送上衣：
    - 完整套装数 = min(上衣, 长裤, 鞋(双), [袜(双) 若包含袜子])
    - 每形成 promo_k 套，赠送 gift_per_batch 件上衣
    """
    if shirts <= 0 or pants <= 0 or shoes_pairs <= 0:
        return 0
    if include_socks and socks_pairs <= 0:
        return 0
    base_min = min(shirts, pants, shoes_pairs) if not include_socks else min(shirts, pants, shoes_pairs, socks_pairs)
    if promo_k <= 0:
        return 0
    batches = base_min // promo_k
    if batches <= 0:
        return 0
    bonus = batches * max(0, gift_per_batch)
    return bonus

def apply_cap(count: int, cap: int) -> int:
    """
    应用编制上限裁剪：返回不超过 cap 的非负整数。
    """
    if cap < 0:
        cap = 0
    if count < 0:
        count = 0
    return count if count <= cap else cap

def compute_answer(clothes_total: int, vehicles_total: int) -> str:
    """
    基于最终服装总件数与车辆总数，返回固定格式字符串：
    'diff=<整数>;ratio=<最简分数或undefined>;approx=<四位小数或undefined>'
    """
    diff = vehicles_total - clothes_total
    if clothes_total == 0:
        ratio_str = 'undefined'
        approx_str = 'undefined'
    else:
        ratio_str = simplify_ratio(vehicles_total, clothes_total)
        approx_str = f'{vehicles_total / clothes_total:.4f}'
    return f'diff={diff};ratio={ratio_str};approx={approx_str}'

def validate_instance(clothes_total: int, vehicles_total: int) -> bool:
    """
    基础有效性校验：
    - 服装总件数与车辆总数均为正整数
    - 数值规模合理（≤ 10^7）
    - 非平凡：diff != 0，ratio 既非 undefined 也不等于 1/1
    """
    if not isinstance(clothes_total, int) or not isinstance(vehicles_total, int):
        return False
    if clothes_total <= 0 or vehicles_total <= 0:
        return False
    if clothes_total > 10_000_000 or vehicles_total > 10_000_000:
        return False
    diff = vehicles_total - clothes_total
    if diff == 0:
        return False
    ratio_str = simplify_ratio(vehicles_total, clothes_total)
    if ratio_str == 'undefined' or ratio_str == '1/1':
        return False
    return True

def _recompute_clothes_total(shirts_after_discard: int,
                             pants_after_discard: int,
                             shoes_pairs_after_discard: int,
                             socks_pairs_after_discard: int,
                             hold_percent: int,
                             release_ratio_num: int,
                             release_ratio_den: int,
                             promo_k: int,
                             gift_shirts_per_batch: int,
                             include_socks: bool,
                             pair_weight: int) -> int:
    """
    从题面参数复算服装总件数。
    """
    s_qc = apply_hold_release(shirts_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    p_qc = apply_hold_release(pants_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    sh_qc = apply_hold_release(shoes_pairs_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    so_qc = apply_hold_release(socks_pairs_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    promo_bonus = compute_promo_bonus_shirts(s_qc, p_qc, sh_qc, so_qc, include_socks, promo_k, gift_shirts_per_batch)
    s_final = s_qc + promo_bonus
    shoes_pieces = sh_qc * pair_weight
    socks_pieces = so_qc * pair_weight
    total = s_final + p_qc + shoes_pieces + socks_pieces
    return total

def _recompute_vehicles_total(buses0: int,
                              vans0: int,
                              cars0: int,
                              scrapped_buses: int,
                              sold_vans: int,
                              rent_cars_in: int,
                              rent_cars_return: int,
                              count_rented_into_ownership: bool,
                              loan_buses_out: int,
                              loan_buses_return: int,
                              loan_vans_out: int,
                              loan_vans_return: int,
                              loan_cars_out: int,
                              loan_cars_return: int,
                              cap_buses: int,
                              cap_vans: int,
                              cap_cars: int) -> int:
    """
    从题面参数复算车辆总数（快照）：报废/卖出、租入净额、临时借调、编制上限。
    """
    buses_after = (buses0 - scrapped_buses) - (loan_buses_out - loan_buses_return)
    vans_after = (vans0 - sold_vans) - (loan_vans_out - loan_vans_return)
    if count_rented_into_ownership:
        cars_mid = cars0 + (rent_cars_in - rent_cars_return)
    else:
        cars_mid = cars0
    cars_after = cars_mid - (loan_cars_out - loan_cars_return)
    b_cap = apply_cap(buses_after, cap_buses)
    v_cap = apply_cap(vans_after, cap_vans)
    c_cap = apply_cap(cars_after, cap_cars)
    return b_cap + v_cap + c_cap

def validate_uniqueness(shirts_after_discard: int,
                        pants_after_discard: int,
                        shoes_pairs_after_discard: int,
                        socks_pairs_after_discard: int,
                        hold_percent: int,
                        release_ratio_num: int,
                        release_ratio_den: int,
                        promo_k: int,
                        gift_shirts_per_batch: int,
                        include_socks: bool,
                        pair_weight: int,
                        loan_buses_out: int,
                        loan_buses_return: int,
                        loan_vans_out: int,
                        loan_vans_return: int,
                        loan_cars_out: int,
                        loan_cars_return: int,
                        count_rented_into_ownership: bool,
                        rent_cars_in: int,
                        rent_cars_return: int,
                        cars0: int,
                        scrapped_buses: int,
                        sold_vans: int,
                        buses0: int,
                        vans0: int,
                        cap_buses: int,
                        cap_vans: int,
                        cap_cars: int,
                        clothes_total: int,
                        vehicles_total: int) -> bool:
    """
    唯一性与多步信息利用校验：
    1) 以题面参数复算服装与车辆总数，必须与 YAML 计算一致；
    2) 构造若干错误理解口径（忽略抽检、忽略促销、按双恒计为1件、不裁编、不计借调），
       计算对应答案字符串，要求至少有两个与正确答案不同；
    3) 至少一种高级规则产生了影响（抽检有扣留、促销有赠送、借调有未回、或裁编触发）。
    """
    # 正确复算
    clothes2 = _recompute_clothes_total(shirts_after_discard, pants_after_discard,
                                        shoes_pairs_after_discard, socks_pairs_after_discard,
                                        hold_percent, release_ratio_num, release_ratio_den,
                                        promo_k, gift_shirts_per_batch, include_socks, pair_weight)
    vehicles2 = _recompute_vehicles_total(buses0, vans0, cars0,
                                          scrapped_buses, sold_vans,
                                          rent_cars_in, rent_cars_return, count_rented_into_ownership,
                                          loan_buses_out, loan_buses_return,
                                          loan_vans_out, loan_vans_return,
                                          loan_cars_out, loan_cars_return,
                                          cap_buses, cap_vans, cap_cars)
    if clothes2 != clothes_total or vehicles2 != vehicles_total:
        return False

    # 正确答案字符串
    ans_true = compute_answer(clothes_total, vehicles_total)

    # 替代口径1：忽略抽检与返还（直接用 after_discard）
    clothes_alt1 = shirts_after_discard + pants_after_discard + \
                   shoes_pairs_after_discard * pair_weight + \
                   socks_pairs_after_discard * pair_weight
    vehicles_alt1 = vehicles2  # 车辆不变
    ans_alt1 = compute_answer(clothes_alt1, vehicles_alt1)

    # 替代口径2：忽略促销赠送（仍保留抽检）
    s_qc = apply_hold_release(shirts_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    p_qc = apply_hold_release(pants_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    sh_qc = apply_hold_release(shoes_pairs_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    so_qc = apply_hold_release(socks_pairs_after_discard, hold_percent, release_ratio_num, release_ratio_den)
    clothes_alt2 = s_qc + p_qc + sh_qc * pair_weight + so_qc * pair_weight  # 无促销
    vehicles_alt2 = vehicles2
    ans_alt2 = compute_answer(clothes_alt2, vehicles_alt2)

    # 替代口径3：按双恒计为1件（而非 pair_weight）
    clothes_alt3 = s_qc + p_qc + sh_qc * 1 + so_qc * 1
    vehicles_alt3 = vehicles2
    ans_alt3 = compute_answer(clothes_alt3, vehicles_alt3)

    # 替代口径4：车辆不裁编（忽略上限）
    buses_after = (buses0 - scrapped_buses) - (loan_buses_out - loan_buses_return)
    vans_after = (vans0 - sold_vans) - (loan_vans_out - loan_vans_return)
    if count_rented_into_ownership:
        cars_mid = cars0 + (rent_cars_in - rent_cars_return)
    else:
        cars_mid = cars0
    cars_after = cars_mid - (loan_cars_out - loan_cars_return)
    vehicles_alt4 = max(0, buses_after) + max(0, vans_after) + max(0, cars_after)
    ans_alt4 = compute_answer(clothes_total, vehicles_alt4)

    # 替代口径5：车辆不计借调（忽略借出影响）
    vehicles_alt5 = apply_cap(buses0 - scrapped_buses, cap_buses) + \
                    apply_cap(vans0 - sold_vans, cap_vans) + \
                    apply_cap((cars0 + (rent_cars_in - rent_cars_return)) if count_rented_into_ownership else cars0, cap_cars)
    ans_alt5 = compute_answer(clothes_total, vehicles_alt5)

    diffs = sum(1 for x in [ans_alt1, ans_alt2, ans_alt3, ans_alt4, ans_alt5] if x != ans_true)
    if diffs < 2:
        return False

    # 至少一种高级规则产生影响（抽检/促销/借调/裁编）
    advanced_effect = False
    if (shirts_after_discard - s_qc) > 0 or (pants_after_discard - p_qc) > 0 or \
       (shoes_pairs_after_discard - sh_qc) > 0 or (socks_pairs_after_discard - so_qc) > 0:
        advanced_effect = True  # 抽检有效
    promo_bonus = compute_promo_bonus_shirts(s_qc, p_qc, sh_qc, so_qc, include_socks, promo_k, gift_shirts_per_batch)
    if promo_bonus > 0:
        advanced_effect = True
    # 借调或裁编是否有效
    if (loan_buses_out - loan_buses_return) > 0 or (loan_vans_out - loan_vans_return) > 0 or (loan_cars_out - loan_cars_return) > 0:
        advanced_effect = True
    if vehicles2 < (max(0, buses_after) + max(0, vans_after) + max(0, cars_after)):
        advanced_effect = True

    return advanced_effect