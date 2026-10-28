import sys, json, random
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional, Any


# -----------------------------
# Coordinate model
# -----------------------------
# Use axial coordinates (q,r) for a triangular/hex-like lattice with 4 diagonal moves.
# Moves:
#   RD (right-down) : ( +1,  0)
#   LU (left-up)    : ( -1,  0)
#   LD (left-down)  : (  0, +1)
#   RU (right-up)   : (  0, -1)
#
# This makes:
#   LU is inverse of RD
#   RU is inverse of LD
#
# Network shape: "N-layer diamond network" -> we model as a bounded diamond:
#   0 <= q <= N
#   0 <= r <= N
#   0 <= q + r <= N
# This is a common "triangular/diamond" bounded region in these coordinates.
#
# Vertices are the integer lattice points satisfying the above. Moving along edges preserves integer points.
# If at any step a move would leave the region, the path is invalid (seen object = unknown, etc.).
#
# We generate puzzles by:
#   - Pick N and a hidden object assignment per vertex (unique objects).
#   - Choose a start S, and several "walk segments" producing sightings that constrain locations.
#   - Ensure all referenced sightings are inside the network.
#   - Ask for the object at the end of a final query walk from a given current position.
#   - Provide answer; if query ends outside network => "unknown".
#
# Importantly, we do NOT reveal coordinates or the mapping rule; only sightings + moves.


@dataclass(frozen=True)
class Move:
    name: str
    dq: int
    dr: int


MOVES = {
    "右下": Move("右下", 1, 0),   # RD
    "左上": Move("左上", -1, 0),  # LU
    "左下": Move("左下", 0, 1),   # LD
    "右上": Move("右上", 0, -1),  # RU
}


def add(p: Tuple[int, int], dq: int, dr: int) -> Tuple[int, int]:
    return (p[0] + dq, p[1] + dr)


def inside(N: int, p: Tuple[int, int]) -> bool:
    q, r = p
    return (0 <= q <= N) and (0 <= r <= N) and (0 <= q + r <= N)


def walk(N: int, start: Tuple[int, int], steps: List[Tuple[str, int]]) -> Optional[Tuple[int, int]]:
    """Return final point if stays inside for all intermediate vertices; else None."""
    p = start
    if not inside(N, p):
        return None
    for dir_name, k in steps:
        mv = MOVES[dir_name]
        for _ in range(k):
            p = add(p, mv.dq, mv.dr)
            if not inside(N, p):
                return None
    return p


def expand_steps(seq: List[Tuple[str, int]]) -> str:
    # Render like: 向右下方向2步，然后向左上方向1步
    parts = []
    for d, k in seq:
        parts.append(f"向{d}方向{k}步")
    return "，然后".join(parts)


# -----------------------------
# Object pool (unique labels)
# -----------------------------
def build_object_pool() -> List[str]:
    base = [
        "打孔器", "投影仪", "椅子", "樱花树", "打印机", "智能音箱", "吊兰", "台灯", "书架", "咖啡杯",
        "路由器", "键盘", "鼠标", "扫地机器人", "相机", "吉他", "闹钟", "望远镜", "雨伞", "毛绒熊",
        "水壶", "花瓶", "画框", "积木", "电风扇", "耳机", "麦克风", "电饭煲", "烤面包机", "滑板",
        "篮球", "哑铃", "地球仪", "显微镜", "手表", "橡皮", "铅笔", "笔记本", "文件夹", "订书机",
        "台历", "沙漏", "蜡烛", "钥匙", "行李箱", "围巾", "帽子", "盆景", "仙人掌", "风铃",
        "指南针", "小提琴", "钢笔", "墨水瓶", "眼镜", "口红", "香水", "扑克", "棋盘", "茶叶罐",
        "收音机", "相册", "工具箱", "螺丝刀", "锤子", "尺子", "胶带", "剪刀", "电池", "充电器",
    ]
    # Ensure enough unique items even for larger N (vertex count ~ (N+1)(N+2)/2).
    # Add indexed extras.
    extras = [f"物品{idx}" for idx in range(1, 500)]
    return base + extras


def all_vertices(N: int) -> List[Tuple[int, int]]:
    vs = []
    for q in range(N + 1):
        for r in range(N + 1):
            if 0 <= q + r <= N:
                vs.append((q, r))
    return vs


def assign_objects(rng: random.Random, N: int) -> Dict[Tuple[int, int], str]:
    vs = all_vertices(N)
    pool = build_object_pool()
    if len(pool) < len(vs):
        raise RuntimeError("Object pool insufficient")
    rng.shuffle(pool)
    return {v: pool[i] for i, v in enumerate(vs)}


# -----------------------------
# Puzzle family generator
# -----------------------------
@dataclass
class Sighting:
    # A sighting is an observed object at some reached vertex
    obj: str
    steps: List[Tuple[str, int]]
    # If steps empty => "从某点开始看到了X"
    # Otherwise => "然后...看到了X"


@dataclass
class JumpBlock:
    # "跳到任意节点，看到了X，然后走...看到了Y..."
    start_obj: str
    follow: List[Sighting]  # subsequent sightings after the jump start


def pick_valid_path(rng: random.Random, N: int, start: Tuple[int, int],
                    max_segments: int = 4, max_step: int = 6) -> List[Sighting]:
    """
    Create a chain of sightings from start, by random segments that remain inside.
    Each segment ends with a sighting at final vertex.
    """
    sightings = []
    cur = start
    for _ in range(rng.randint(2, max_segments)):
        # sample a steps list of 2-4 directional commands with small lengths
        for attempt in range(200):
            m = rng.randint(2, 4)
            steps = []
            for __ in range(m):
                d = rng.choice(list(MOVES.keys()))
                k = rng.randint(1, max_step)
                steps.append((d, k))
            end = walk(N, cur, steps)
            if end is not None:
                sightings.append(Sighting(obj="", steps=steps))  # obj to be filled later
                cur = end
                break
        else:
            # If we can't find a valid segment, stop
            break
    return sightings


def steps_from_text(steps: List[Tuple[str, int]]) -> str:
    # Render with Chinese connectors; keep consistent
    if not steps:
        return ""
    return expand_steps(steps)


def render_problem(N: int,
                   blocks: List[Any],
                   query_steps: List[Tuple[str, int]],
                   output_language: str = "zh") -> str:
    # Only zh supported per request; keep structure flexible.
    intro = (
        f"构建了一个{N}层的菱形网络：第1层有1个菱形，第2层有2个菱形，…，第{N}层有{N}个菱形。"
        f"网络的每个顶点上都有一个独特的物品。你沿着菱形边在顶点间移动。"
        f"移动方向只有四种：右下、左下、右上、左上；每走1步表示沿一条边到相邻顶点。"
    )

    story_parts = []
    # blocks are either ("chain", start_obj, [Sighting...]) or ("jump", JumpBlock)
    for b in blocks:
        if b[0] == "chain":
            start_obj, chain = b[1], b[2]
            # first sentence
            story_parts.append(f"你从其中某一个点开始，看到了一个{start_obj}。")
            for s in chain:
                story_parts.append(f"然后{steps_from_text(s.steps)}，看到了一个{s.obj}。")
        elif b[0] == "jump":
            jb: JumpBlock = b[1]
            story_parts.append(f"然后你跳到了一个任意的节点，看到了一个{jb.start_obj}。")
            for s in jb.follow:
                story_parts.append(f"然后{steps_from_text(s.steps)}，看到了一个{s.obj}。")
        else:
            raise RuntimeError("Unknown block type")

    query_text = steps_from_text(query_steps)
    ask = (
        f"问题：从当前位置开始，{query_text}，看到的物品是什么？"
        f"如果最终位置不在网络中则输出unknown。"
    )
    return intro + "\n" + "\n".join(story_parts) + "\n" + ask


def solve_and_explain(N: int,
                      mapping: Dict[Tuple[int, int], str],
                      # we store true internal positions for explanation checking
                      chain_start: Tuple[int, int],
                      chain_objs: List[str],
                      chain_steps: List[List[Tuple[str, int]]],
                      jump_start: Tuple[int, int],
                      jump_objs: List[str],
                      jump_steps: List[List[Tuple[str, int]]],
                      query_steps: List[Tuple[str, int]]) -> Tuple[Any, str]:
    # Current position = end of jump block (the last reached point in jump sequence)
    # We'll compute that and then run query.
    # Recompute for cross-check via expanded step-by-step.
    def walk_stepwise(start: Tuple[int, int], steps: List[Tuple[str, int]]) -> Optional[Tuple[int, int]]:
        p = start
        if not inside(N, p):
            return None
        for d, k in steps:
            mv = MOVES[d]
            for _ in range(k):
                p = (p[0] + mv.dq, p[1] + mv.dr)
                if not inside(N, p):
                    return None
        return p

    # Validate chain
    p = chain_start
    for obj, steps in zip(chain_objs[1:], chain_steps):  # first obj at start
        p2 = walk_stepwise(p, steps)
        if p2 is None or mapping[p2] != obj:
            raise RuntimeError("Internal consistency failed (chain)")
        p = p2

    # Validate jump
    p = jump_start
    if mapping[p] != jump_objs[0]:
        raise RuntimeError("Internal consistency failed (jump start)")
    for obj, steps in zip(jump_objs[1:], jump_steps):
        p2 = walk_stepwise(p, steps)
        if p2 is None or mapping[p2] != obj:
            raise RuntimeError("Internal consistency failed (jump)")
        p = p2

    current = p
    qend = walk_stepwise(current, query_steps)
    if qend is None:
        ans = "unknown"
    else:
        ans = mapping[qend]

    # Provide brief, checkable explanation (do not expose full map)
    # We can show that the "当前位置" is the last mentioned object in jump block,
    # and then apply net displacement. But do not reveal coords; just compute final object.
    # We'll state the last known object and that we follow query steps to reach the answer.
    expl = (
        f"当前位置是最后一次明确看到物品的顶点（即跳转段最后看到的“{jump_objs[-1]}”所在顶点）。"
        f"从该顶点按题目给定方向依次移动：{expand_steps(query_steps)}。"
    )
    if ans == "unknown":
        expl += "过程中或最终位置超出网络边界，因此结果为unknown。"
    else:
        expl += f"移动后到达的顶点上对应的物品是“{ans}”。"
    return ans, expl


def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Choose N big enough to allow longer moves, but not too big.
    N = rng.randint(7, 12)
    mapping = assign_objects(rng, N)
    vertices = list(mapping.keys())

    # Construct a first chain starting somewhere, with 2-3 sightings.
    for attempt in range(400):
        chain_start = rng.choice(vertices)
        chain_segments = pick_valid_path(rng, N, chain_start, max_segments=3, max_step=6)
        if len(chain_segments) < 2:
            continue
        # Fill objects based on endpoints
        chain_objs = [mapping[chain_start]]
        chain_steps = []
        p = chain_start
        ok = True
        for seg in chain_segments:
            end = walk(N, p, seg.steps)
            if end is None:
                ok = False
                break
            chain_steps.append(seg.steps)
            chain_objs.append(mapping[end])
            p = end
        if not ok:
            continue

        # Construct a jump block with 3-4 sightings; ensure ends inside
        jump_start = rng.choice(vertices)
        jump_segments = pick_valid_path(rng, N, jump_start, max_segments=4, max_step=7)
        if len(jump_segments) < 2:
            continue
        jump_objs = [mapping[jump_start]]
        jump_steps = []
        p2 = jump_start
        ok2 = True
        for seg in jump_segments:
            end2 = walk(N, p2, seg.steps)
            if end2 is None:
                ok2 = False
                break
            jump_steps.append(seg.steps)
            jump_objs.append(mapping[end2])
            p2 = end2
        if not ok2:
            continue

        # Query steps: fixed-length 5-7 commands
        for _q in range(200):
            m = rng.randint(5, 7)
            query_steps = []
            for __ in range(m):
                d = rng.choice(list(MOVES.keys()))
                k = rng.randint(1, 6)
                query_steps.append((d, k))
            # no need to ensure inside; unknown allowed, but keep not too often
            qend = walk(N, p2, query_steps)
            # balance: allow unknown sometimes but not all
            if qend is None and rng.random() < 0.65:
                continue
            # ensure answer isn't trivially the same as current too often
            if qend is not None and mapping[qend] == mapping[p2] and rng.random() < 0.7:
                continue
            # Build blocks for rendering with objects inserted.
            chain_sightings = []
            for obj, steps in zip(chain_objs[1:], chain_steps):
                chain_sightings.append(Sighting(obj=obj, steps=steps))

            jump_follow = []
            for obj, steps in zip(jump_objs[1:], jump_steps):
                jump_follow.append(Sighting(obj=obj, steps=steps))

            blocks = [
                ("chain", chain_objs[0], chain_sightings),
                ("jump", JumpBlock(start_obj=jump_objs[0], follow=jump_follow)),
            ]

            problem = render_problem(N, blocks, query_steps, output_language=output_language)
            answer, explanation = solve_and_explain(
                N, mapping,
                chain_start, chain_objs, chain_steps,
                jump_start, jump_objs, jump_steps,
                query_steps
            )
            # Final sanity: problem non-empty, explanation non-empty
            if not problem.strip() or (isinstance(answer, str) and answer == ""):
                continue
            if not explanation.strip():
                continue
            return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("Failed to generate a valid puzzle after many attempts")


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = data.get("output_language", "zh")
    rng = random.Random(seed)

    results = []
    seen = set()
    # bounded retries to avoid infinite loops
    max_total_attempts = 2000
    attempts = 0
    while len(results) < count and attempts < max_total_attempts:
        attempts += 1
        item = generate_one(rng, output_language)
        # deduplicate by problem text hash
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"Only generated {len(results)} / {count} problems after {attempts} attempts.", file=sys.stderr)
        raise SystemExit(1)

    json.dump(results, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()