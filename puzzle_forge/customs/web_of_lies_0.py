# web_of_lies_fast.py
# 优化版真假话谜题构造器 - 大幅提升生成速度
from typing import List, Dict, Tuple, Optional
import random
from z3 import Solver, Bool, And, Not, Or, sat

# 基础词库
BASE_PERSON_POOL = [
    '冯雅','陈刚','卫平','杨光','金铭','张伟','何方','张丽','曹操','郑晓','韩梅','孙文',
    '李强','王芳','赵敏','周凯','刘璐','吴彤','郭林','胡宁','马骞','陶然','谢昊','袁野'
]
BASE_PLACE_POOL = [
    '办公室','图书馆','广场','银行','商场','动物园','咖啡店','电影院','机场','书店','超市','社区中心',
    '码头','车站','公园','展馆','邮局','学校','餐厅','花园','剧院','酒店','体育馆','美术馆'
]

def _choose_unique(lst: List[str], k: int, rng: random.Random) -> List[str]:
    pool = lst[:]
    rng.shuffle(pool)
    return pool[:k]

def _count_solutions_fast(vars_map: Dict[str, Bool], constraints: List, limit: int = 2):
    """优化版的解计数函数"""
    s = Solver()
    s.set("timeout", 5000)  # 设置5秒超时
    for c in constraints:
        s.add(c)
    
    count = 0
    models = []
    while s.check() == sat and count < limit:
        m = s.model()
        models.append(m)
        # 阻塞当前解
        block = Or([var != m.evaluate(var) for var in vars_map.values()])
        s.add(block)
        count += 1
    return count, models

def build_unique_instance(
    seed: Optional[int] = None,
    n_persons: int = 10,
    min_clues: int = 10,
    max_clues: int = 18,
    ensure_unique: bool = True,
    minimal_unique: bool = False,  # 默认关闭最小化以提升速度
    pos_ratio: float = 0.5,
    allow_place_speakers: bool = True,
    allow_person_speakers: bool = True,
    always_true_places_num: int = 0,
    always_false_places_num: int = 0,
    max_attempts: int = 20  # 减少尝试次数
):
    rng = random.Random(seed)

    # 采样人物与地点
    persons = _choose_unique(BASE_PERSON_POOL, n_persons, rng)
    places = _choose_unique(BASE_PLACE_POOL, n_persons, rng)
    place_to_person = {pl: p for pl, p in zip(places, persons)}

    # Z3变量
    tvars = {p: Bool(f"truth_{p}") for p in persons}

    # 恒真/恒假角色
    always_true_places = rng.sample(places, k=min(always_true_places_num, len(places))) if always_true_places_num > 0 else []
    remaining_places = [pl for pl in places if pl not in always_true_places]
    always_false_places = rng.sample(remaining_places, k=min(always_false_places_num, len(remaining_places))) if always_false_places_num > 0 else []
    always_true = [place_to_person[pl] for pl in always_true_places]
    always_false = [place_to_person[pl] for pl in always_false_places]

    # 预生成候选线索池（优化生成逻辑）
    candidates: List[Tuple[str, str, bool, str]] = []
    
    def sample_target(exclude: str) -> str:
        others = [x for x in persons if x != exclude]
        return rng.choice(others)

    # 更高效的候选生成
    candidate_count = min(n_persons * 4, 80)  # 减少候选数量
    for _ in range(candidate_count):
        pol = rng.random() < pos_ratio
        tpl_weights = []
        if allow_place_speakers:
            tpl_weights.append(1)
        if allow_person_speakers:
            tpl_weights.extend([2, 3])  # 增加人物说话者的权重
        
        if not tpl_weights:
            continue
            
        tpl = rng.choice(tpl_weights)
        
        if tpl == 1:  # 地点说话者
            sp_place = rng.choice(places)
            speaker = place_to_person[sp_place]
            target = sample_target(speaker)
            text = f"在{sp_place}的人说{target}说的" + ("真话。" if pol else "假话。")
            candidates.append((speaker, target, pol, text))
        elif tpl == 2:  # 人物说地点人物
            speaker = rng.choice(persons)
            target_place = rng.choice(places)
            target = place_to_person[target_place]
            text = f"{speaker}说在{target_place}的人说的" + ("真话。" if pol else "假话。")
            candidates.append((speaker, target, pol, text))
        elif tpl == 3:  # 人物说人物
            speaker = rng.choice(persons)
            target = sample_target(speaker)
            text = f"{speaker}说{target}说的" + ("真话。" if pol else "假话。")
            candidates.append((speaker, target, pol, text))

    # 约束构造器
    def constraints_from(subset: List[Tuple[str, str, bool]]) -> List:
        cons = []
        for (speaker, target, pol) in subset:
            cons.append(tvars[speaker] == (tvars[target] if pol else Not(tvars[target])))
        for sp in always_true:
            cons.append(tvars[sp] == True)
        for sp in always_false:
            cons.append(tvars[sp] == False)
        return cons

    # 优化搜索策略：从中间开始搜索
    best_solution = None
    for attempt in range(max_attempts):
        rng.shuffle(candidates)
        
        # 尝试几个关键规模
        test_sizes = [
            min(max_clues, len(candidates)),
            (min_clues + max_clues) // 2,
            min_clues
        ]
        
        for k in test_sizes:
            if k > len(candidates):
                continue
                
            subset = candidates[:k]
            core = [(a, b, c) for (a, b, c, _) in subset]
            cons = constraints_from(core)
            num, models = _count_solutions_fast(tvars, cons, limit=2)
            
            if ensure_unique and num == 1:
                chosen = subset
                
                # 可选的最小化（仅在开启时执行）
                if minimal_unique and len(chosen) > min_clues:
                    simplified = []
                    for i, clue in enumerate(chosen):
                        # 测试去掉这个线索是否仍然唯一
                        trial = chosen[:i] + chosen[i+1:]
                        trial_core = [(a, b, c) for (a, b, c, _) in trial]
                        tcons = constraints_from(trial_core)
                        tnum, _ = _count_solutions_fast(tvars, tcons, limit=2)
                        if tnum == 1:
                            continue  # 这个线索冗余
                        simplified.append(clue)
                    chosen = simplified
                
                # 构建返回结果
                speakers = [a for (a, _, _, _) in chosen]
                targets = [b for (_, b, _, _) in chosen]
                pols = [c for (_, _, c, _) in chosen]
                texts = [d for (_, _, _, d) in chosen]
                
                # 生成描述
                rule_lines = []
                if always_true_places:
                    rule_lines.append(f"规则：在{'、'.join(always_true_places)}的人从不撒谎。")
                if always_false_places:
                    rule_lines.append(f"规则：在{'、'.join(always_false_places)}的人从不说真话。")
                
                header = "规则：每个参与者要么总是说真话，要么总是说谎话。"
                assign = "地点分配：" + " ".join([f"{place_to_person[pl]}在{pl}。" for pl in places])
                clue_block = "线索如下：\n" + "\n".join([f"{i+1}. {txt}" for i, txt in enumerate(texts)])
                
                # 查询对象（选择部分人物）
                query_count = min(4, len(persons))  # 减少查询数量
                query_targets = rng.sample(persons, k=query_count)
                
                desc = "\n".join([header, assign] + rule_lines + [clue_block])
                
                return {
                    'persons': persons,
                    'places': places,
                    'place_to_person': place_to_person,
                    'speakers': speakers,
                    'targets': targets,
                    'pols': pols,
                    'always_true': always_true,
                    'always_false': always_false,
                    'desc': desc,
                    'query_targets': query_targets
                }
            
            elif not ensure_unique and num >= 1:
                # 不要求唯一解的情况
                chosen = subset
                speakers = [a for (a, _, _, _) in chosen]
                targets = [b for (_, b, _, _) in chosen]
                pols = [c for (_, _, c, _) in chosen]
                texts = [d for (_, _, _, d) in chosen]
                
                rule_lines = []
                if always_true_places:
                    rule_lines.append(f"规则：在{'、'.join(always_true_places)}的人从不撒谎。")
                if always_false_places:
                    rule_lines.append(f"规则：在{'、'.join(always_false_places)}的人从不说真话。")
                
                header = "规则：每个参与者要么总是说真话，要么总是说谎话。"
                assign = "地点分配：" + " ".join([f"{place_to_person[pl]}在{pl}。" for pl in places])
                clue_block = "线索如下：\n" + "\n".join([f"{i+1}. {txt}" for i, txt in enumerate(texts)])
                query_targets = rng.sample(persons, k=min(4, len(persons)))
                
                desc = "\n".join([header, assign] + rule_lines + [clue_block])
                
                return {
                    'persons': persons,
                    'places': places,
                    'place_to_person': place_to_person,
                    'speakers': speakers,
                    'targets': targets,
                    'pols': pols,
                    'always_true': always_true,
                    'always_false': always_false,
                    'desc': desc,
                    'query_targets': query_targets
                }

    # 回退方案：使用中等数量线索
    fallback_size = min((min_clues + max_clues) // 2, len(candidates))
    fallback = candidates[:fallback_size]
    
    core = [(a, b, c) for (a, b, c, _) in fallback]
    speakers = [a for (a, _, _, _) in fallback]
    targets = [b for (_, b, _, _) in fallback]
    pols = [c for (_, _, c, _) in fallback]
    texts = [d for (_, _, _, d) in fallback]
    
    header = "规则：每个参与者要么总是说真话，要么总是说谎话。"
    rule_lines = []
    if always_true_places:
        rule_lines.append(f"规则：在{'、'.join(always_true_places)}的人从不撒谎。")
    if always_false_places:
        rule_lines.append(f"规则：在{'、'.join(always_false_places)}的人从不说真话。")
    
    assign = "地点分配：" + " ".join([f"{place_to_person[pl]}在{pl}。" for pl in places])
    clue_block = "线索如下：\n" + "\n".join([f"{i+1}. {txt}" for i, txt in enumerate(texts)])
    query_targets = rng.sample(persons, k=min(4, len(persons)))
    
    desc = "\n".join([header, assign] + rule_lines + [clue_block])

    return {
        'persons': persons,
        'places': places,
        'place_to_person': place_to_person,
        'speakers': speakers,
        'targets': targets,
        'pols': pols,
        'always_true': always_true,
        'always_false': always_false,
        'desc': desc,
        'query_targets': query_targets
    }