import sys, json, random, itertools
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any

# We will use z3 for robust constraint solving and uniqueness checks.
from z3 import Solver, Bool, And, Or, Not, Implies, sat, is_true


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
    text: str     # rendered natural-language statement
    z3expr: Any   # z3 Bool expression meaning "statement content is true"


@dataclass
class Puzzle:
    people: List[Person]
    places: List[str]
    statements: List[Statement]
    forced_truth: Dict[str, bool]  # speaker -> must_be_truthful
    queries: List[str]  # list of speakers to ask "does this speaker tell truth?"
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
        return f"在{ s[4:] }的人"
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
# Puzzle generator families
# ----------------------------

class Generator:
    def __init__(self, seed: int, output_language: str = "zh"):
        self.rng = random.Random(seed)
        self.output_language = output_language

        # Name and place pools (Chinese, self-contained; no external data).
        self.name_pool = [
            "张伟","王芳","李娜","刘强","陈刚","杨光","韩梅","郑晓","金铭","冯雅",
            "孙文","卫平","何方","张丽","赵磊","周敏","吴涛","宋倩","林浩","许静",
            "马宁","胡杰","高飞","丁一","唐雨","秦朗","姜珊","罗丹","蒋欣","邱晨"
        ]
        self.place_pool = [
            "机场","电影院","办公室","书店","咖啡店","广场","图书馆","超市","商场","银行",
            "动物园","社区中心","公园","体育馆","餐厅","博物馆"
        ]
        # Some adjective predicates to add non-location statements (kept but optional)
        self.adj_pool = ["友好","谨慎","健谈","幽默","认真","慷慨","安静","热心"]

    # --- Building blocks for constraints ---

    def build_model(self, puzzle: Puzzle):
        # Variables: each speaker (person and each location-speaker used) has a truthfulness Bool.
        all_speakers = set(p.name for p in puzzle.people)
        for st in puzzle.statements:
            all_speakers.add(st.speaker)
        # Ensure location speakers for all places (may be referenced)
        for pl in puzzle.places:
            all_speakers.add(_loc_speaker(pl))

        T = {sp: Bool(f"T_{sp.replace(':','_')}") for sp in all_speakers}  # True -> truthful, False -> liar

        s = Solver()

        # forced truthfulness constraints
        for sp, val in puzzle.forced_truth.items():
            if sp not in T:
                # still allow forcing; create variable
                T[sp] = Bool(f"T_{sp.replace(':','_')}")
            s.add(T[sp] if val else Not(T[sp]))

        # Every statement: if speaker truthful then content true; if liar then content false.
        for st in puzzle.statements:
            s.add(Implies(T[st.speaker], st.z3expr))
            s.add(Implies(Not(T[st.speaker]), Not(st.z3expr)))

        return s, T

    def solve_unique_truth_values(self, puzzle: Puzzle, query_speakers: List[str]) -> Optional[Dict[str, bool]]:
        s, T = self.build_model(puzzle)
        if s.check() != sat:
            return None
        m = s.model()

        # We require uniqueness of truth values for queried speakers (not necessarily full uniqueness).
        base_vals = {q: bool(is_true(m.evaluate(T[q], model_completion=True))) for q in query_speakers}

        # Check uniqueness by forbidding at least one queried truth value to differ.
        diff_clause = Or(*[
            (T[q] if (not base_vals[q]) else Not(T[q]))
            for q in query_speakers
        ])
        s2, T2 = self.build_model(puzzle)
        s2.add(diff_clause)
        if s2.check() == sat:
            return None
        return base_vals

    # --- Statement constructors ---

    def st_person_says_truth_of(self, speaker: str, target: str, Tvars: Dict[str, Any]) -> Statement:
        # content: target is truthful
        text = f"{speaker}说{_speaker_display(target)}说的是真话。"
        return Statement(speaker=speaker, text=text, z3expr=Tvars[target])

    def st_person_says_lie_of(self, speaker: str, target: str, Tvars: Dict[str, Any]) -> Statement:
        text = f"{speaker}说{_speaker_display(target)}说的是假话。"
        return Statement(speaker=speaker, text=text, z3expr=Not(Tvars[target]))

    def st_loc_says_truth_of(self, loc: str, target: str, Tvars: Dict[str, Any]) -> Statement:
        speaker = _loc_speaker(loc)
        text = f"在{loc}的人说{_speaker_display(target)}说的是真话。"
        return Statement(speaker=speaker, text=text, z3expr=Tvars[target])

    def st_loc_says_lie_of(self, loc: str, target: str, Tvars: Dict[str, Any]) -> Statement:
        speaker = _loc_speaker(loc)
        text = f"在{loc}的人说{_speaker_display(target)}说的是假话。"
        return Statement(speaker=speaker, text=text, z3expr=Not(Tvars[target]))

    def st_person_property(self, speaker: str, person: str, adj: str, Pvars: Dict[Tuple[str,str], Any]) -> Statement:
        # Optional: "X说Y很adj" where content is a separate boolean predicate.
        # We will add consistency constraints through additional structure if used.
        text = f"{speaker}说{person}很{adj}。"
        return Statement(speaker=speaker, text=text, z3expr=Pvars[(person, adj)])

    # --- Families ---

    def gen_family_graph(self) -> Puzzle:
        """
        Generate a liar/truth-teller graph puzzle.
        Speakers include: people and 'at location' pseudo-speakers.
        Statements are of form "A says B is truthful/lying".
        Optionally force one location to always tell truth or always lie to ensure solvability and diversity.
        """
        rng = self.rng

        # Choose number of people and places
        n_people = _pick_weighted(rng, [(7, 2), (8, 4), (9, 3), (10, 1)])
        n_places = _pick_weighted(rng, [(6, 2), (7, 4), (8, 3), (9, 1)])

        people_names = _rand_unique_sample(rng, self.name_pool, n_people)
        places = _rand_unique_sample(rng, self.place_pool, n_places)

        # Assign each person a unique location (injective mapping for clarity).
        chosen_places_for_people = _rand_unique_sample(rng, places, n_people)
        people = [Person(name=nm, location=pl) for nm, pl in zip(people_names, chosen_places_for_people)]

        # Determine which locations will appear as "LOC speakers"
        # We'll include all places; statements may reference any.
        loc_speakers = [_loc_speaker(pl) for pl in places]

        # Create z3 variables placeholder for constructing statements
        # We'll use a temporary dictionary; actual model builder will recreate but we need consistent keys.
        all_speakers = set(people_names) | set(loc_speakers)
        Ttmp = {sp: Bool(f"Ttmp_{sp.replace(':','_')}") for sp in all_speakers}

        statements: List[Statement] = []

        # Build a backbone cycle among several speakers to create determinacy.
        backbone = list(all_speakers)
        rng.shuffle(backbone)
        backbone = backbone[:max(5, min(8, len(backbone)))]

        for i in range(len(backbone)):
            a = backbone[i]
            b = backbone[(i + 1) % len(backbone)]
            # Randomly choose claim type
            if rng.random() < 0.5:
                # a says b truthful
                if _is_loc_speaker(a):
                    statements.append(self.st_loc_says_truth_of(a[4:], b, Ttmp))
                else:
                    statements.append(self.st_person_says_truth_of(a, b, Ttmp))
            else:
                # a says b lying
                if _is_loc_speaker(a):
                    statements.append(self.st_loc_says_lie_of(a[4:], b, Ttmp))
                else:
                    statements.append(self.st_person_says_lie_of(a, b, Ttmp))

        # Add extra random edges
        extra = rng.randint(n_people + 3, n_people + 9)
        for _ in range(extra):
            a = rng.choice(list(all_speakers))
            b = rng.choice(list(all_speakers))
            if a == b:
                continue
            typ = rng.random()
            if typ < 0.5:
                if _is_loc_speaker(a):
                    statements.append(self.st_loc_says_truth_of(a[4:], b, Ttmp))
                else:
                    statements.append(self.st_person_says_truth_of(a, b, Ttmp))
            else:
                if _is_loc_speaker(a):
                    statements.append(self.st_loc_says_lie_of(a[4:], b, Ttmp))
                else:
                    statements.append(self.st_person_says_lie_of(a, b, Ttmp))

        # Force 0-2 speakers to be always truthful/liar (variety)
        forced_truth: Dict[str, bool] = {}
        if rng.random() < 0.85:
            # at least one force to avoid too many symmetric solutions
            sp = rng.choice(list(all_speakers))
            forced_truth[sp] = True if rng.random() < 0.5 else False
        if rng.random() < 0.35:
            sp2 = rng.choice(list(all_speakers))
            if sp2 not in forced_truth:
                forced_truth[sp2] = True if rng.random() < 0.5 else False

        # Choose 5-7 queries among mix of persons and location speakers
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
        """
        Two-tier: locations speak about people and people speak about locations.
        This tends to couple variables more strongly and yields different flavor.
        """
        rng = self.rng

        n_people = _pick_weighted(rng, [(6, 2), (7, 4), (8, 3), (9, 1)])
        n_places = _pick_weighted(rng, [(6, 3), (7, 4), (8, 3)])

        people_names = _rand_unique_sample(rng, self.name_pool, n_people)
        places = _rand_unique_sample(rng, self.place_pool, n_places)
        chosen_places_for_people = _rand_unique_sample(rng, places, n_people)
        people = [Person(name=nm, location=pl) for nm, pl in zip(people_names, chosen_places_for_people)]

        loc_speakers = [_loc_speaker(pl) for pl in places]
        all_speakers = set(people_names) | set(loc_speakers)
        Ttmp = {sp: Bool(f"Ttmp_{sp.replace(':','_')}") for sp in all_speakers}

        statements: List[Statement] = []
        forced_truth: Dict[str, bool] = {}

        # Force exactly one location to be always truthful or always lying (clear anchor)
        anchor_loc = rng.choice(places)
        forced_truth[_loc_speaker(anchor_loc)] = True if rng.random() < 0.6 else False

        # Locations speak about people; people speak about locations
        for pl in places:
            # each location speaker makes 1-2 statements about random people
            for _ in range(rng.randint(1, 2)):
                target_person = rng.choice(people_names)
                if rng.random() < 0.5:
                    statements.append(self.st_loc_says_truth_of(pl, target_person, Ttmp))
                else:
                    statements.append(self.st_loc_says_lie_of(pl, target_person, Ttmp))

        for nm in people_names:
            # each person makes 1 statement about a random location speaker
            target_loc = _loc_speaker(rng.choice(places))
            if rng.random() < 0.5:
                statements.append(self.st_person_says_truth_of(nm, target_loc, Ttmp))
            else:
                statements.append(self.st_person_says_lie_of(nm, target_loc, Ttmp))

        # Add 2-5 cross statements among people for extra coupling
        for _ in range(rng.randint(2, 5)):
            a = rng.choice(people_names)
            b = rng.choice(list(all_speakers))
            if a == b:
                continue
            if rng.random() < 0.5:
                statements.append(self.st_person_says_truth_of(a, b, Ttmp))
            else:
                statements.append(self.st_person_says_lie_of(a, b, Ttmp))

        # Queries: include at least one location and at least three people
        query_k = rng.randint(5, 7)
        q = set()
        q.add(_loc_speaker(rng.choice(places)))
        while len([x for x in q if not _is_loc_speaker(x)]) < 3:
            q.add(rng.choice(people_names))
        while len(q) < query_k:
            q.add(rng.choice(list(all_speakers)))
        queries = list(q)
        rng.shuffle(queries)

        return Puzzle(
            people=people,
            places=places,
            statements=statements,
            forced_truth=forced_truth,
            queries=queries,
            output_language=self.output_language
        )

    # --- Rendering ---

    def render_problem(self, puzzle: Puzzle) -> str:
        # Build readable Chinese problem statement.
        lines = []
        lines.append("在这个问题中，每个“说话者”要么总是说真话，要么总是说谎话。")
        lines.append("说话者包括：每个人，以及“在某地点的人”（表示该地点里那位说话者）。")
        lines.append("")
        lines.append("已知每个人所在地点如下：")
        for p in puzzle.people:
            lines.append(f"- {p.name}在{p.location}。")
        if puzzle.forced_truth:
            lines.append("")
            lines.append("额外已知（用于缩小范围）：")
            for sp, val in puzzle.forced_truth.items():
                who = _speaker_display(sp)
                lines.append(f"- {who}{'从不撒谎' if val else '从不说真话'}。")

        lines.append("")
        lines.append("线索（他们的陈述）如下：")
        for st in puzzle.statements:
            lines.append(f"- {st.text}")

        lines.append("")
        qtxt = "，".join([f"{_speaker_display(q)}说的是真话吗？" for q in puzzle.queries])
        lines.append("问题：" + qtxt)
        lines.append("请在最后一行按如下格式作答：")
        lines.append("答案是 $YOUR_ANSWER。$YOUR_ANSWER 是由若干个词组成的列表，每个词为“是”或“否”，顺序与问题中的询问一致（例如：是,否,是）。")
        return "\n".join(lines)

    def render_explanation(self, puzzle: Puzzle, truth_vals: Dict[str, bool]) -> str:
        # Provide short, checkable evidence: list forced anchors and final queried truth values.
        # Also give one or two derived implications using specific clues (without solver-opaque claims).
        lines = []
        lines.append("将每个说话者设为变量：真话者/说谎者。对每条陈述套用规则：")
        lines.append("若说话者是真话者，则其陈述内容为真；若说话者是说谎者，则其陈述内容为假。")
        if puzzle.forced_truth:
            lines.append("题面还给出部分说话者固定为真话者或说谎者，用来打破对称。")

        # Give 2 concrete constraint examples from the instance
        if puzzle.statements:
            pick = puzzle.statements[:min(2, len(puzzle.statements))]
            lines.append("例如：")
            for st in pick:
                lines.append(f"- 若{_speaker_display(st.speaker)}是真话者，则“{st.text}”所断言的内容成立；若其为说谎者，则该内容不成立。")

        lines.append("在满足全部线索的一致性约束下，可唯一推出下列询问对象的真话/假话属性：")
        for q in puzzle.queries:
            lines.append(f"- {_speaker_display(q)}：{'是' if truth_vals[q] else '否'}")
        return "\n".join(lines)

    # --- Generation loop with validation ---

    def generate_one(self, max_tries: int = 200) -> Tuple[str, Any, str]:
        # Try multiple times to get a satisfiable puzzle with unique answers for the queries.
        for _ in range(max_tries):
            fam = _pick_weighted(self.rng, [(self.gen_family_graph, 6), (self.gen_family_two_tier, 4)])
            puzzle = fam()

            # Ensure enough statements
            if len(puzzle.statements) < 8:
                continue

            # Uniqueness of truth values for queries
            truth_vals = self.solve_unique_truth_values(puzzle, puzzle.queries)
            if truth_vals is None:
                continue

            # Build answer list ("是"/"否")
            ans_list = ["是" if truth_vals[q] else "否" for q in puzzle.queries]
            problem = self.render_problem(puzzle)
            explanation = self.render_explanation(puzzle, truth_vals)

            # Sanity: problem non-empty and contains each query speaker text
            if not problem.strip() or not explanation.strip():
                continue
            return problem, ", ".join(ans_list), explanation

        raise RuntimeError("生成失败：在尝试次数上限内未能构造出满足“可满足且询问项唯一确定”的题目。")


# ----------------------------
# Main I/O
# ----------------------------

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    if count <= 0:
        print("[]")
        return

    output_language = "zh"
    gen = Generator(seed=seed, output_language=output_language)

    results = []
    seen = set()

    # bounded attempts to avoid infinite loops
    attempts = 0
    max_attempts = 4000

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
        results.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(results) != count:
        print(f"仅生成了 {len(results)}/{count} 道题（达到尝试上限或生成困难）。", file=sys.stderr)

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()