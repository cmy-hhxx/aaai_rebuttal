import sys, json, random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any, Set

from z3 import Solver, Bool, Or, Not, Implies, sat, is_true


# ----------------------------
# Core logic model
# ----------------------------

@dataclass(frozen=True)
class Person:
    name: str
    location: str


@dataclass(frozen=True)
class Statement:
    speaker: str  # person name or special "LOC:<place>" pseudo-speaker
    text: str
    z3expr: Any   # z3 Bool expr for statement content


@dataclass
class Puzzle:
    people: List[Person]
    places: List[str]
    statements: List[Statement]
    forced_truth: Dict[str, bool]  # speaker -> must_be_truthful (True) or must_be_liar (False)
    queries: List[str]
    output_language: str = "zh"


# ----------------------------
# Utilities
# ----------------------------

def _loc_speaker(place: str) -> str:
    return f"LOC:{place}"

def _is_loc_speaker(s: str) -> bool:
    return s.startswith("LOC:")

def _speaker_display(s: str) -> str:
    if _is_loc_speaker(s):
        return f"在{s[4:]}的人"
    return s

def _rand_unique_sample(rng: random.Random, items: List[Any], k: int) -> List[Any]:
    if k > len(items):
        raise ValueError("sample too large")
    items2 = list(items)
    rng.shuffle(items2)
    return items2[:k]

def _pick_weighted(rng: random.Random, choices: List[Tuple[Any, int]]) -> Any:
    total = sum(w for _, w in choices)
    x = rng.randrange(total)
    s = 0
    for v, w in choices:
        s += w
        if x < s:
            return v
    return choices[-1][0]


# ----------------------------
# Generator
# ----------------------------

class Generator:
    def __init__(self, seed: int, output_language: str = "zh"):
        self.rng = random.Random(seed)
        self.output_language = output_language

        self.name_pool = [
            "张伟","王芳","李娜","刘强","陈刚","杨光","韩梅","郑晓","金铭","冯雅",
            "孙文","卫平","何方","张丽","赵磊","周敏","吴涛","宋倩","林浩","许静",
            "马宁","胡杰","高飞","丁一","唐雨","秦朗","姜珊","罗丹","蒋欣","邱晨"
        ]
        self.place_pool = [
            "机场","电影院","办公室","书店","咖啡店","广场","图书馆","超市","商场","银行",
            "动物园","社区中心","公园","体育馆","餐厅","博物馆"
        ]

    # ----------------------------
    # Z3 modeling
    # ----------------------------

    def build_model(self, puzzle: Puzzle) -> Tuple[Solver, Dict[str, Any]]:
        speakers: Set[str] = set(p.name for p in puzzle.people)
        for st in puzzle.statements:
            speakers.add(st.speaker)
        for pl in puzzle.places:
            speakers.add(_loc_speaker(pl))

        T = {sp: Bool(f"T_{sp.replace(':','_')}") for sp in speakers}
        s = Solver()

        for sp, val in puzzle.forced_truth.items():
            if sp not in T:
                T[sp] = Bool(f"T_{sp.replace(':','_')}")
            s.add(T[sp] if val else Not(T[sp]))

        for st in puzzle.statements:
            s.add(Implies(T[st.speaker], st.z3expr))
            s.add(Implies(Not(T[st.speaker]), Not(st.z3expr)))

        return s, T

    def solve_unique_truth_values(self, puzzle: Puzzle, query_speakers: List[str]) -> Optional[Dict[str, bool]]:
        s, T = self.build_model(puzzle)
        if s.check() != sat:
            return None
        m = s.model()
        base = {q: bool(is_true(m.evaluate(T[q], model_completion=True))) for q in query_speakers}

        # Uniqueness only for queried speakers: forbid any different assignment on them
        s2, T2 = self.build_model(puzzle)
        diff = Or(*[(T2[q] if (not base[q]) else Not(T2[q])) for q in query_speakers])
        s2.add(diff)
        if s2.check() == sat:
            return None
        return base

    # ----------------------------
    # Statement constructors
    # ----------------------------

    def st_says_truth_of(self, speaker: str, target: str, Ttmp: Dict[str, Any]) -> Statement:
        # content: target is truthful
        text = f"{_speaker_display(speaker)}说{_speaker_display(target)}说的是真话。"
        return Statement(speaker=speaker, text=text, z3expr=Ttmp[target])

    def st_says_lie_of(self, speaker: str, target: str, Ttmp: Dict[str, Any]) -> Statement:
        # content: target is liar
        text = f"{_speaker_display(speaker)}说{_speaker_display(target)}说的是假话。"
        return Statement(speaker=speaker, text=text, z3expr=Not(Ttmp[target]))

    # ----------------------------
    # Families
    # ----------------------------

    def gen_family_graph(self) -> Puzzle:
        rng = self.rng

        n_people = _pick_weighted(rng, [(7, 2), (8, 4), (9, 3), (10, 1)])
        n_places = _pick_weighted(rng, [(6, 2), (7, 4), (8, 3), (9, 1)])
        n_places = max(n_places, n_people)  # ensure injective assignment possible

        people_names = _rand_unique_sample(rng, self.name_pool, n_people)
        places = _rand_unique_sample(rng, self.place_pool, n_places)

        chosen_places_for_people = _rand_unique_sample(rng, places, n_people)
        people = [Person(name=nm, location=pl) for nm, pl in zip(people_names, chosen_places_for_people)]

        loc_speakers = [_loc_speaker(pl) for pl in places]
        all_speakers = set(people_names) | set(loc_speakers)
        Ttmp = {sp: Bool(f"Ttmp_{sp.replace(':','_')}") for sp in all_speakers}

        statements: List[Statement] = []

        # Backbone cycle
        backbone = list(all_speakers)
        rng.shuffle(backbone)
        backbone = backbone[:max(5, min(8, len(backbone)))]
        for i in range(len(backbone)):
            a = backbone[i]
            b = backbone[(i + 1) % len(backbone)]
            if rng.random() < 0.5:
                statements.append(self.st_says_truth_of(a, b, Ttmp))
            else:
                statements.append(self.st_says_lie_of(a, b, Ttmp))

        # Extra edges
        extra = rng.randint(n_people + 3, n_people + 9)
        for _ in range(extra):
            a = rng.choice(list(all_speakers))
            b = rng.choice(list(all_speakers))
            if a == b:
                continue
            if rng.random() < 0.5:
                statements.append(self.st_says_truth_of(a, b, Ttmp))
            else:
                statements.append(self.st_says_lie_of(a, b, Ttmp))

        forced_truth: Dict[str, bool] = {}
        if rng.random() < 0.85:
            sp = rng.choice(list(all_speakers))
            forced_truth[sp] = (rng.random() < 0.5)
        if rng.random() < 0.35:
            sp2 = rng.choice(list(all_speakers))
            if sp2 not in forced_truth:
                forced_truth[sp2] = (rng.random() < 0.5)

        query_k = _pick_weighted(rng, [(5, 4), (6, 4), (7, 2)])
        candidates = list(all_speakers)
        rng.shuffle(candidates)
        queries = candidates[:query_k]

        return Puzzle(
            people=people,
            places=places,
            statements=statements,
            forced_truth=forced_truth,
            queries=queries,
            output_language=self.output_language
        )

    def gen_family_two_tier(self) -> Puzzle:
        rng = self.rng

        n_people = _pick_weighted(rng, [(6, 2), (7, 4), (8, 3), (9, 1)])
        n_places = _pick_weighted(rng, [(6, 3), (7, 4), (8, 3)])
        n_places = max(n_places, n_people)  # FIX: ensure enough places for unique assignment

        people_names = _rand_unique_sample(rng, self.name_pool, n_people)
        places = _rand_unique_sample(rng, self.place_pool, n_places)

        chosen_places_for_people = _rand_unique_sample(rng, places, n_people)
        people = [Person(name=nm, location=pl) for nm, pl in zip(people_names, chosen_places_for_people)]

        loc_speakers = [_loc_speaker(pl) for pl in places]
        all_speakers = set(people_names) | set(loc_speakers)
        Ttmp = {sp: Bool(f"Ttmp_{sp.replace(':','_')}") for sp in all_speakers}

        statements: List[Statement] = []
        forced_truth: Dict[str, bool] = {}

        # Anchor: one location forced
        anchor_loc = rng.choice(places)
        forced_truth[_loc_speaker(anchor_loc)] = (rng.random() < 0.6)

        # Each location makes 1-2 statements about people
        for pl in places:
            sp = _loc_speaker(pl)
            for _ in range(rng.randint(1, 2)):
                target_person = rng.choice(people_names)
                if rng.random() < 0.5:
                    statements.append(self.st_says_truth_of(sp, target_person, Ttmp))
                else:
                    statements.append(self.st_says_lie_of(sp, target_person, Ttmp))

        # Each person makes 1 statement about a location
        for nm in people_names:
            target_loc = _loc_speaker(rng.choice(places))
            if rng.random() < 0.5:
                statements.append(self.st_says_truth_of(nm, target_loc, Ttmp))
            else:
                statements.append(self.st_says_lie_of(nm, target_loc, Ttmp))

        # Cross-coupling
        for _ in range(rng.randint(2, 5)):
            a = rng.choice(people_names)
            b = rng.choice(list(all_speakers))
            if a == b:
                continue
            if rng.random() < 0.5:
                statements.append(self.st_says_truth_of(a, b, Ttmp))
            else:
                statements.append(self.st_says_lie_of(a, b, Ttmp))

        # Queries: ensure mixed
        query_k = rng.randint(5, 7)
        qset: Set[str] = set()
        qset.add(_loc_speaker(rng.choice(places)))
        while len([x for x in qset if not _is_loc_speaker(x)]) < 3:
            qset.add(rng.choice(people_names))
        while len(qset) < query_k:
            qset.add(rng.choice(list(all_speakers)))
        queries = list(qset)
        rng.shuffle(queries)

        return Puzzle(
            people=people,
            places=places,
            statements=statements,
            forced_truth=forced_truth,
            queries=queries,
            output_language=self.output_language
        )

    # ----------------------------
    # Rendering
    # ----------------------------

    def render_problem(self, puzzle: Puzzle) -> str:
        lines = []
        lines.append("在这个问题中，每个说话者要么总是说真话，要么总是说谎话。")
        lines.append("说话者包括：每个人，以及“在某地点的人”（表示该地点里的那位说话者）。")
        lines.append("")
        lines.append("已知每个人所在地点如下：")
        for p in puzzle.people:
            lines.append(f"- {p.name}在{p.location}。")
        if puzzle.forced_truth:
            lines.append("")
            lines.append("额外已知：")
            for sp, val in puzzle.forced_truth.items():
                who = _speaker_display(sp)
                lines.append(f"- {who}{'从不撒谎' if val else '从不说真话'}。")
        lines.append("")
        lines.append("线索如下：")
        for st in puzzle.statements:
            lines.append(f"- {st.text}")
        lines.append("")
        qtxt = "，".join([f"{_speaker_display(q)}说的是真话吗？" for q in puzzle.queries])
        lines.append("问题：" + qtxt)
        lines.append("请在最后一行按如下格式作答：")
        lines.append("答案是 $YOUR_ANSWER。$YOUR_ANSWER 是由若干个词组成的列表，每个词为“是”或“否”，顺序与问题一致（例如：是,否,是）。")
        return "\n".join(lines)

    def render_explanation(self, puzzle: Puzzle, truth_vals: Dict[str, bool]) -> str:
        lines = []
        lines.append("对每条线索应用规则：真话者的陈述内容为真；说谎者的陈述内容为假。")
        if puzzle.forced_truth:
            lines.append("题面额外给出的“从不撒谎/从不说真话”用于固定部分变量。")
        lines.append("在满足全部线索的一致性条件下，询问对象的真话/假话属性可被唯一确定为：")
        for q in puzzle.queries:
            lines.append(f"- {_speaker_display(q)}：{'是' if truth_vals[q] else '否'}")
        return "\n".join(lines)

    # ----------------------------
    # Generation with validation
    # ----------------------------

    def generate_one(self, max_tries: int = 250) -> Tuple[str, Any, str]:
        for _ in range(max_tries):
            fam = _pick_weighted(self.rng, [(self.gen_family_graph, 6), (self.gen_family_two_tier, 4)])
            puzzle = fam()

            if len(puzzle.statements) < 10:
                continue

            truth_vals = self.solve_unique_truth_values(puzzle, puzzle.queries)
            if truth_vals is None:
                continue

            ans_list = ["是" if truth_vals[q] else "否" for q in puzzle.queries]
            return (
                self.render_problem(puzzle),
                ", ".join(ans_list),
                self.render_explanation(puzzle, truth_vals)
            )
        raise RuntimeError("生成失败：在尝试次数上限内未能构造出可满足且询问项答案唯一的题目。")


# ----------------------------
# Main I/O
# ----------------------------

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    if count <= 0:
        sys.stdout.write("[]")
        return

    gen = Generator(seed=seed, output_language="zh")
    results = []
    seen = set()

    attempts = 0
    max_attempts = 5000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            problem, answer, explanation = gen.generate_one()
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            break

        key = (problem, answer)
        if key in seen:
            continue
        seen.add(key)
        results.append({"problem": problem, "answer": answer, "explanation": explanation})

    if len(results) != count:
        print(f"仅生成了 {len(results)}/{count} 道题（达到尝试上限或生成困难）。", file=sys.stderr)

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()