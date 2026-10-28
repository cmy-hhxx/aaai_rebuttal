import sys, json, random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any, Set

from z3 import Solver, Bool, Or, Not, Implies, sat, is_true


# ----------------------------
# Core structures
# ----------------------------

@dataclass(frozen=True)
class Person:
    name: str
    location: str


@dataclass(frozen=True)
class Statement:
    speaker: str
    text: str
    z3expr: Any


@dataclass
class Puzzle:
    people: List[Person]
    places: List[str]
    statements: List[Statement]
    forced_truth: Dict[str, bool]
    queries: List[str]


# ----------------------------
# Helpers
# ----------------------------

def _loc_speaker(place: str) -> str:
    return f"LOC:{place}"

def _is_loc_speaker(s: str) -> bool:
    return s.startswith("LOC:")

def _speaker_display(s: str) -> str:
    return f"在{s[4:]}的人" if _is_loc_speaker(s) else s

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
    """
    Key repair: ensure high yield by *constructing* a model first, then generating
    statements consistent with it, and finally checking that queried truth values
    are uniquely determined by the public clues.
    """
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.name_pool = [
            "张伟","王芳","李娜","刘强","陈刚","杨光","韩梅","郑晓","金铭","冯雅",
            "孙文","卫平","何方","张丽","赵磊","周敏","吴涛","宋倩","林浩","许静",
            "马宁","胡杰","高飞","丁一","唐雨","秦朗","姜珊","罗丹","蒋欣","邱晨"
        ]
        self.place_pool = [
            "机场","电影院","办公室","书店","咖啡店","广场","图书馆","超市","商场","银行",
            "动物园","社区中心","公园","体育馆","餐厅","博物馆"
        ]

    # ------------- Z3 --------------

    def build_model(self, puzzle: Puzzle) -> Tuple[Solver, Dict[str, Any]]:
        speakers: Set[str] = set(p.name for p in puzzle.people)
        for pl in puzzle.places:
            speakers.add(_loc_speaker(pl))
        for st in puzzle.statements:
            speakers.add(st.speaker)

        T = {sp: Bool(f"T_{sp.replace(':','_')}") for sp in speakers}
        s = Solver()

        for sp, val in puzzle.forced_truth.items():
            s.add(T[sp] if val else Not(T[sp]))

        for st in puzzle.statements:
            s.add(Implies(T[st.speaker], st.z3expr))
            s.add(Implies(Not(T[st.speaker]), Not(st.z3expr)))
        return s, T

    def unique_truth_for_queries(self, puzzle: Puzzle) -> Optional[Dict[str, bool]]:
        s, T = self.build_model(puzzle)
        if s.check() != sat:
            return None
        m = s.model()
        base = {q: bool(is_true(m.evaluate(T[q], model_completion=True))) for q in puzzle.queries}

        # Forbid any change among queried truth values
        s2, T2 = self.build_model(puzzle)
        diff = Or(*[(T2[q] if (not base[q]) else Not(T2[q])) for q in puzzle.queries])
        s2.add(diff)
        if s2.check() == sat:
            return None
        return base

    # --------- statement text/expr ----------

    def _st_says_truth_of(self, speaker: str, target: str, Ttmp: Dict[str, Any]) -> Statement:
        return Statement(
            speaker=speaker,
            text=f"{_speaker_display(speaker)}说{_speaker_display(target)}说的是真话。",
            z3expr=Ttmp[target]
        )

    def _st_says_lie_of(self, speaker: str, target: str, Ttmp: Dict[str, Any]) -> Statement:
        return Statement(
            speaker=speaker,
            text=f"{_speaker_display(speaker)}说{_speaker_display(target)}说的是假话。",
            z3expr=Not(Ttmp[target])
        )

    # ------------- Constructive instance generation --------------

    def _construct_puzzle(self) -> Puzzle:
        rng = self.rng

        # sizes
        n_people = _pick_weighted(rng, [(6, 2), (7, 4), (8, 3), (9, 1)])
        n_places = max(n_people, _pick_weighted(rng, [(6, 2), (7, 4), (8, 3), (9, 1)]))

        people_names = _rand_unique_sample(rng, self.name_pool, n_people)
        places = _rand_unique_sample(rng, self.place_pool, n_places)

        chosen_places = _rand_unique_sample(rng, places, n_people)
        people = [Person(nm, pl) for nm, pl in zip(people_names, chosen_places)]

        loc_speakers = [_loc_speaker(pl) for pl in places]
        all_speakers = list(set(people_names) | set(loc_speakers))

        # Choose queries early to guide construction
        qk = _pick_weighted(rng, [(5, 4), (6, 4), (7, 2)])
        rng.shuffle(all_speakers)
        queries = all_speakers[:qk]

        # Hidden "target model": assign each speaker truthful/liar randomly,
        # then generate statements that are consistent with that assignment.
        hidden_T: Dict[str, bool] = {sp: (rng.random() < 0.5) for sp in all_speakers}

        # Force 1-2 anchors (publicly given) to strongly increase determinacy.
        forced_truth: Dict[str, bool] = {}
        anchors = [rng.choice(all_speakers)]
        if rng.random() < 0.45:
            a2 = rng.choice(all_speakers)
            if a2 != anchors[0]:
                anchors.append(a2)
        for a in anchors:
            forced_truth[a] = hidden_T[a]

        # We'll create statements that *determine* all queried speakers by chaining from anchors.
        # Use a star+chain design:
        # - Anchor(s) speak about some nodes, those speak about others, etc.
        # For each statement "A says (B truthful)" we choose polarity so that statement content truth
        # matches hidden model depending on whether A is truthful or liar.
        #
        # If A is truthful -> statement content must be true.
        # If A is liar     -> statement content must be false.
        #
        # We can choose content as either (B truthful) or (B liar) to satisfy that.
        def add_edge_statements(A: str, B: str, stmts: List[Statement], Ttmp: Dict[str, Any]):
            # Decide whether content should be "B truthful" (T[B]) or "B liar" (~T[B])
            # such that content truth equals hidden_T[A].
            # content_truth = hidden_T[A]
            # If choose content = T[B], then content_truth = hidden_T[B]
            # If choose content = ~T[B], content_truth = not hidden_T[B]
            if hidden_T[B] == hidden_T[A]:
                stmts.append(self._st_says_truth_of(A, B, Ttmp))  # content truth = T[B] = hidden_T[B] = hidden_T[A]
            else:
                stmts.append(self._st_says_lie_of(A, B, Ttmp))    # content truth = ~T[B] = not hidden_T[B] = hidden_T[A]

        # Temp z3 vars just for embedding in Statement.z3expr (by name)
        Ttmp = {sp: Bool(f"Ttmp_{sp.replace(':','_')}") for sp in all_speakers}

        statements: List[Statement] = []

        # Build a connected directed structure covering all queries and many others.
        # Start frontier from anchors.
        frontier = anchors[:]
        remaining = [sp for sp in all_speakers if sp not in anchors]
        rng.shuffle(remaining)

        # Ensure all queries are included early
        for q in queries:
            if q in anchors:
                continue
            if q in remaining:
                remaining.remove(q)
                remaining.insert(0, q)

        # Add edges from frontier to cover remaining nodes
        while remaining:
            B = remaining.pop(0)
            A = rng.choice(frontier)
            add_edge_statements(A, B, statements, Ttmp)
            frontier.append(B)

        # Add extra redundancy constraints to make query uniqueness more likely:
        # - each query is referred by 2-3 different speakers
        extras = rng.randint(6, 12)
        for _ in range(extras):
            B = rng.choice(queries)
            A = rng.choice(all_speakers)
            if A == B:
                continue
            add_edge_statements(A, B, statements, Ttmp)

        # Add a couple of cycles among 3-5 nodes for stronger propagation
        cyc_nodes = rng.sample(all_speakers, k=min(len(all_speakers), rng.randint(3, 5)))
        for i in range(len(cyc_nodes)):
            add_edge_statements(cyc_nodes[i], cyc_nodes[(i + 1) % len(cyc_nodes)], statements, Ttmp)

        # Deduplicate identical text lines (avoid repeats)
        seen_text = set()
        deduped: List[Statement] = []
        for st in statements:
            if st.text in seen_text:
                continue
            seen_text.add(st.text)
            deduped.append(st)
        statements = deduped

        return Puzzle(
            people=people,
            places=places,
            statements=statements,
            forced_truth=forced_truth,
            queries=queries
        )

    # ------------- Rendering -------------

    def render_problem(self, puzzle: Puzzle) -> str:
        lines = []
        lines.append("在这个问题中，每个说话者要么总是说真话，要么总是说谎话。")
        lines.append("说话者包括：每个人，以及“在某地点的人”（表示该地点里的那位说话者）。")
        lines.append("")
        lines.append("已知每个人所在地点如下：")
        for p in puzzle.people:
            lines.append(f"- {p.name}在{p.location}。")
        lines.append("")
        if puzzle.forced_truth:
            lines.append("额外已知：")
            for sp, val in puzzle.forced_truth.items():
                lines.append(f"- {_speaker_display(sp)}{'从不撒谎' if val else '从不说真话'}。")
            lines.append("")
        lines.append("线索（陈述）如下：")
        for st in puzzle.statements:
            lines.append(f"- {st.text}")
        lines.append("")
        qtxt = "，".join([f"{_speaker_display(q)}说的是真话吗？" for q in puzzle.queries])
        lines.append("问题：" + qtxt)
        lines.append("请在最后一行按如下格式作答：")
        lines.append("答案是 $YOUR_ANSWER。$YOUR_ANSWER 是由若干个词组成的列表，每个词为“是”或“否”，顺序与问题一致（例如：是,否,是）。")
        return "\n".join(lines)

    def render_explanation(self, puzzle: Puzzle, truth_vals: Dict[str, bool]) -> str:
        # Keep it brief but checkable: state the rule and list query results.
        lines = []
        lines.append("规则：真话者的每条陈述内容为真；说谎者的每条陈述内容为假。")
        if puzzle.forced_truth:
            lines.append("题面给出的“从不撒谎/从不说真话”用于固定部分说话者。")
        lines.append("在满足全部线索的一致性条件下，询问对象的真话/假话属性唯一确定为：")
        for q in puzzle.queries:
            lines.append(f"- {_speaker_display(q)}：{'是' if truth_vals[q] else '否'}")
        return "\n".join(lines)

    # ------------- Public API -------------

    def generate_one(self, max_tries: int = 120) -> Tuple[str, str, str]:
        # Constructive generation should have high yield; still validate uniqueness.
        for _ in range(max_tries):
            puzzle = self._construct_puzzle()

            # Ensure reasonable clue count
            if len(puzzle.statements) < 14:
                continue

            truth_vals = self.unique_truth_for_queries(puzzle)
            if truth_vals is None:
                continue

            ans = ", ".join(["是" if truth_vals[q] else "否" for q in puzzle.queries])
            return self.render_problem(puzzle), ans, self.render_explanation(puzzle, truth_vals)

        raise RuntimeError("生成失败：在尝试次数上限内未能构造出可满足且询问项答案唯一的题目。")


# ----------------------------
# Main I/O
# ----------------------------

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])

    gen = Generator(seed=seed)

    results = []
    seen = set()

    attempts = 0
    max_attempts = 20000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        problem, answer, explanation = gen.generate_one()
        key = (problem, answer)
        if key in seen:
            continue
        seen.add(key)
        results.append({"problem": problem, "answer": answer, "explanation": explanation})

    if len(results) != count:
        # Hard fail to match platform requirement
        raise SystemExit(f"无法生成足够题目：仅生成 {len(results)}/{count}。请更换seed或提高max_attempts。")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()