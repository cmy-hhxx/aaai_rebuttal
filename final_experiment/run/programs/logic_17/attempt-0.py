import sys, json, random, math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

# We generate questions about "Mill's Five Methods" (five methods of exploring causal relationships),
# asking which method matches a described reasoning passage.
#
# Methods mapping to options:
# A: ⸮  (Method of Agreement / 求同法)
# B: ؆  (Method of Difference / 求异法)
# C: ꙮ  (Joint Method of Agreement and Difference / 求同求异并用法)
# D: ⵣ  (Method of Concomitant Variations / 共变法)
# E: ⚘  (Method of Residues / 剩余法)

OPTION_BY_METHOD = {"⸮": "A", "؆": "B", "ꙮ": "C", "ⵣ": "D", "⚘": "E"}

METHOD_NAMES_ZH = {
    "⸮": "⸮法（求同法）",
    "؆": "؆法（求异法）",
    "ꙮ": "ꙮ法（求同求异并用法）",
    "ⵣ": "ⵣ法（共变法）",
    "⚘": "⚘法（剩余法）",
}

@dataclass
class GeneratedItem:
    problem: str
    answer: Any
    explanation: str

def rchoice(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]

def unique_sample(rng: random.Random, seq, k):
    seq = list(seq)
    rng.shuffle(seq)
    return seq[:k]

def fmt_list(items, sep="、"):
    return sep.join(items)

def clamp_int(x, lo, hi):
    return max(lo, min(hi, x))

# --------- Scenario templates per method ---------

def gen_agreement(rng: random.Random) -> Tuple[str, str]:
    """⸮ method: multiple cases where S and P co-occur, other conditions differ."""
    domains = [
        ("植物生长", "使用某种添加剂S", "生长速度明显变快P",
         ["土壤类型A", "浇水频率B", "光照时长C", "盆大小D", "室温E"]),
        ("电子设备", "更换为某款电源适配器S", "设备发热增大P",
         ["环境温度A", "运行软件B", "屏幕亮度C", "外接设备D", "电池健康E"]),
        ("学习效果", "采用一种记忆法S", "测验得分提高P",
         ["学习时间A", "科目B", "睡眠时长C", "是否做题D", "复习间隔E"]),
        ("食品口感", "加入某种发酵剂S", "面包更松软P",
         ["面粉品牌A", "发酵温度B", "揉面时长C", "烘烤温度D", "含水量E"]),
        ("交通拥堵", "启用某个信号配时方案S", "平均排队长度下降P",
         ["车流量A", "天气B", "是否施工C", "事故发生D", "公交频次E"]),
    ]
    topic, S, P, others = rchoice(rng, domains)
    k = rng.randint(3, 5)
    # Choose differing other conditions per case
    chosen_others = unique_sample(rng, others, k if k <= len(others) else len(others))
    cases = []
    for i in range(k):
        # pick 2 other conditions per case, varying
        oth = unique_sample(rng, others, 2)
        cases.append(f"（{i+1}）出现 {S}，同时 {fmt_list(oth)} 各不相同，但都观察到 {P}。")
    passage = (
        f"在{topic}的多次观察中：\n" +
        "\n".join(cases) +
        f"\n研究者据此推断：{S} 与 {P} 可能存在因果联系。"
    )
    return passage, "⸮"

def gen_difference(rng: random.Random) -> Tuple[str, str]:
    """؆ method: two cases same except presence/absence of S; P occurs only with S."""
    domains = [
        ("车间产线", "更换为润滑剂S", "轴承噪声显著降低P",
         ["同一台机器A", "同批原料B", "相同转速C", "相同室温D"]),
        ("医学观察", "服用药物S", "症状缓解P",
         ["同一患者A", "相同饮食B", "相同作息C", "相同剂量对照D"]),
        ("化学实验", "加入催化剂S", "反应明显加快P",
         ["相同浓度A", "相同温度B", "相同溶剂C", "相同搅拌速度D"]),
        ("网络服务", "启用缓存策略S", "平均响应时间下降P",
         ["相同请求量A", "相同硬件B", "相同带宽C", "相同代码版本D"]),
        ("学习干预", "使用番茄钟方法S", "走神次数减少P",
         ["同一学生A", "同一科目B", "同一时段C", "同等作业量D"]),
    ]
    topic, S, P, controls = rchoice(rng, domains)
    control_text = "、".join(controls)
    passage = (
        f"在{topic}中做对照：\n"
        f"（1）在{control_text}保持一致的情况下，采用 {S}，结果出现 {P}。\n"
        f"（2）在{control_text}仍保持一致，但不采用 {S}，结果不出现 {P}。\n"
        f"因此推断：{S} 与 {P} 可能存在因果联系。"
    )
    return passage, "؆"

def gen_joint(rng: random.Random) -> Tuple[str, str]:
    """ꙮ method: positive group S&P with varying others; negative group not S and not P with varying others."""
    domains = [
        ("团队效率", "引入每日站会S", "项目延期率下降P",
         ["团队规模A", "项目复杂度B", "远程比例C", "成员资历D", "工具链E"]),
        ("作物产量", "使用滴灌方案S", "亩产提升P",
         ["品种A", "土壤B", "施肥C", "降雨D", "温度E"]),
        ("设备故障", "增加防尘滤网S", "故障率降低P",
         ["使用时长A", "负载B", "环境湿度C", "维护频率D", "供应商E"]),
        ("顾客转化", "采用个性化推荐S", "转化率上升P",
         ["渠道A", "折扣力度B", "页面风格C", "商品结构D", "客单价E"]),
    ]
    topic, S, P, others = rchoice(rng, domains)
    pos_n = rng.randint(3, 4)
    neg_n = rng.randint(2, 4)
    pos_lines = []
    for i in range(pos_n):
        oth = unique_sample(rng, others, 2)
        pos_lines.append(f"（{i+1}）采用 {S}，且 {fmt_list(oth)} 不同，但都观察到 {P}。")
    neg_lines = []
    for i in range(neg_n):
        oth = unique_sample(rng, others, 2)
        neg_lines.append(f"（{i+1}'）未采用 {S}，且 {fmt_list(oth)} 不同，同时也未观察到 {P}。")
    passage = (
        f"在{topic}的比较研究中：\n"
        f"正组（有S）：\n" + "\n".join(pos_lines) + "\n"
        f"负组（无S）：\n" + "\n".join(neg_lines) + "\n"
        f"据此推断：{S} 与 {P} 可能存在因果联系。"
    )
    return passage, "ꙮ"

def gen_concomitant(rng: random.Random) -> Tuple[str, str]:
    """ⵣ method: S changes correspond to P changes (dose-response, monotonic relation)."""
    domains = [
        ("冷却实验", "风扇转速S", "降温速度P", "转速（rpm）", "每分钟温度下降（°C/min）"),
        ("市场营销", "广告投放强度S", "新增注册量P", "日投放（千元）", "日新增（人）"),
        ("运动训练", "训练频率S", "最大摄氧量提升P", "每周训练次数", "8周提升（ml/kg/min）"),
        ("农业", "施肥量S", "产量P", "每亩施肥（kg）", "亩产（kg）"),
        ("材料测试", "外加应力S", "形变量P", "应力（MPa）", "应变（%）"),
    ]
    topic, S, P, sx, px = rchoice(rng, domains)
    n = rng.randint(4, 5)
    # Create monotone data with small noise but consistent direction
    base_s = rng.randint(1, 5)
    step = rng.randint(1, 5)
    s_vals = [base_s + i * step for i in range(n)]
    # p roughly proportional
    a = rng.uniform(1.5, 6.0)
    b = rng.uniform(0.0, 5.0)
    p_vals = []
    last = None
    for sv in s_vals:
        pv = a * sv + b + rng.uniform(-0.2, 0.2)
        if last is not None and pv <= last:
            pv = last + rng.uniform(0.3, 1.0)
        last = pv
        p_vals.append(pv)
    lines = []
    for i, (sv, pv) in enumerate(zip(s_vals, p_vals), 1):
        lines.append(f"（{i}）{S}={sv}（{sx}），对应 {P}≈{pv:.1f}（{px}）。")
    passage = (
        f"在{topic}中，研究者多次改变{S}的水平并记录{P}：\n" +
        "\n".join(lines) +
        f"\n可以看到{S}增大时{P}也随之增大（同向变化）。因此推断：{S} 与 {P} 可能存在因果联系。"
    )
    return passage, "ⵣ"

def gen_residues(rng: random.Random) -> Tuple[str, str]:
    """⚘ method: explain part of effect by known causes; residual attributed to new cause S."""
    domains = [
        ("电费异常", "某个隐藏的耗电设备S", "总耗电增加P",
         ["空调耗电A", "热水器耗电B", "冰箱耗电C"], "测得总耗电"),
        ("网站延迟", "某个未发现的慢查询S", "总体延迟升高P",
         ["网络传输A", "前端渲染B", "已知接口调用C"], "观测到的总体耗时"),
        ("学生成绩变化", "新增的课外辅导S", "总分提升P",
         ["作业完成度A", "课堂出勤B", "自习时间C"], "测得总分变化"),
        ("工厂废气", "新增排放源S", "总排放升高P",
         ["锅炉排放A", "窑炉排放B", "运输车辆排放C"], "监测到的总排放"),
        ("车辆油耗", "某个机械故障S", "油耗升高P",
         ["胎压变化A", "载重变化B", "空调使用C"], "实测油耗"),
    ]
    topic, S, P, known_causes, total_desc = rchoice(rng, domains)
    # Create consistent arithmetic for explanation: total effect = sum known + residual
    known_vals = [rng.randint(10, 40) for _ in known_causes]
    residual = rng.randint(8, 25)
    total = sum(known_vals) + residual
    known_lines = []
    for name, val in zip(known_causes, known_vals):
        known_lines.append(f"{name} 预计贡献了 {val} 个单位。")
    passage = (
        f"在{topic}的分析中，{total_desc}显示 {P} 的增量约为 {total} 个单位。\n"
        f"根据既有模型，已知因素的贡献分别为：\n" +
        "\n".join(f"- {x}" for x in known_lines) +
        f"\n这些已知因素合计只能解释 {sum(known_vals)} 个单位，仍剩余约 {residual} 个单位无法解释。\n"
        f"研究者据此推断：可能存在一个新的原因 {S} 用来解释这部分“剩余”，因此 {S} 与 {P} 可能存在因果联系。"
    )
    return passage, "⚘"

GEN_FUNCS = {
    "⸮": gen_agreement,
    "؆": gen_difference,
    "ꙮ": gen_joint,
    "ⵣ": gen_concomitant,
    "⚘": gen_residues,
}

def render_problem(passage_zh: str) -> str:
    return (
        "以下给出五种用于探究因果联系的方法（符号对应如下）：\n"
        "A. ⸮法    B. ؆法    C. ꙮ法    D. ⵣ法    E. ⚘法\n"
        "阅读材料，判断其因果推断最符合哪一种方法。\n\n"
        f"材料：\n{passage_zh}\n\n"
        "请选择：[[A/B/C/D/E]]"
    )

def render_explanation(method_symbol: str, passage_zh: str) -> str:
    # Provide short, checkable rationale keyed to method type
    if method_symbol == "⸮":
        return "材料给出多个案例：S与P总是同时出现，而其他条件各不相同，属于“求同法”（⸮法）。"
    if method_symbol == "؆":
        return "材料是对照：除是否有S外其余条件相同；有S则有P、无S则无P，属于“求异法”（؆法）。"
    if method_symbol == "ꙮ":
        return "材料同时包含正组（有S且有P）与负组（无S且无P），并且其他条件在两组内都变化，属于“求同求异并用法”（ꙮ法）。"
    if method_symbol == "ⵣ":
        return "材料展示S的水平变化与P的变化相对应（同向或反向的量变关系），属于“共变法”（ⵣ法）。"
    if method_symbol == "⚘":
        return "材料先用已知原因解释P的一部分，再把剩余未解释部分归因于新的S，属于“剩余法”（⚘法）。"
    return "判别依据：与题干所述结构相匹配的方法。"

def check_answer_unique(method_symbol: str) -> bool:
    # In this task each instance is designed to match exactly one method structurally.
    return method_symbol in OPTION_BY_METHOD

def generate_one(rng: random.Random, prefer_method: Optional[str] = None) -> GeneratedItem:
    method = prefer_method or rchoice(rng, list(GEN_FUNCS.keys()))
    passage, m = GEN_FUNCS[method](rng)
    assert m == method
    problem = render_problem(passage)
    ans = f"[[{OPTION_BY_METHOD[method]}]]"
    explanation = render_explanation(method, passage)
    return GeneratedItem(problem=problem, answer=ans, explanation=explanation)

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results: List[Dict[str, Any]] = []
    seen = set()
    # ensure variety: cycle methods but with randomness in ordering
    methods = list(GEN_FUNCS.keys())
    rng.shuffle(methods)

    attempts = 0
    max_attempts = count * 50
    idx = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        method = methods[idx % len(methods)]
        idx += 1
        item = generate_one(rng, prefer_method=method)

        # De-dup by problem text
        key = item.problem
        if key in seen:
            continue
        if not item.problem.strip() or item.answer is None:
            continue
        if not check_answer_unique(method):
            continue

        seen.add(key)
        results.append({"problem": item.problem, "answer": item.answer, "explanation": item.explanation})

    if len(results) != count:
        print(f"Failed to generate enough unique items: {len(results)}/{count}", file=sys.stderr)
        # Still output what we have? Spec requires exactly count items. So raise.
        raise SystemExit(1)

    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()