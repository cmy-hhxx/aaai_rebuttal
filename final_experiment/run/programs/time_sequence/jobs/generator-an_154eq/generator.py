import sys, json, random, math, itertools
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Any

# ----------------------------- Time utilities -----------------------------

DAYS_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五"]

def hm_to_min(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)

def min_to_hm(t: int) -> str:
    h = t // 60
    m = t % 60
    return f"{h:02d}:{m:02d}"

WORK_START = hm_to_min("09:00")
WORK_END = hm_to_min("17:00")

def clamp_interval(a: int, b: int, lo: int, hi: int) -> Optional[Tuple[int,int]]:
    a2, b2 = max(a, lo), min(b, hi)
    if a2 >= b2:
        return None
    return (a2, b2)

def merge_intervals(intervals: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    out = []
    cur_s, cur_e = intervals[0]
    for s, e in intervals[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            out.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    out.append((cur_s, cur_e))
    return out

def subtract_intervals(base: List[Tuple[int,int]], blocks: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    """Return base minus union(blocks). All lists are intervals [s,e), assumed within same day."""
    if not base:
        return []
    blocks_u = merge_intervals([iv for iv in blocks if iv is not None])
    out = []
    for bs, be in base:
        cur = bs
        for s, e in blocks_u:
            if e <= cur:
                continue
            if s >= be:
                break
            if s > cur:
                out.append((cur, min(s, be)))
            cur = max(cur, e)
            if cur >= be:
                break
        if cur < be:
            out.append((cur, be))
    return out

def complement_within_work(free: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    """Given free intervals, return busy intervals within work hours."""
    free_u = merge_intervals([iv for iv in free if iv is not None])
    return subtract_intervals([(WORK_START, WORK_END)], free_u)

def intersect_many(lists: List[List[Tuple[int,int]]]) -> List[Tuple[int,int]]:
    """Intersect interval lists (each already within work hours)."""
    if not lists:
        return [(WORK_START, WORK_END)]
    cur = merge_intervals(lists[0])
    for nxt in lists[1:]:
        nxt = merge_intervals(nxt)
        i, j = 0, 0
        out = []
        while i < len(cur) and j < len(nxt):
            a1, a2 = cur[i]
            b1, b2 = nxt[j]
            s = max(a1, b1)
            e = min(a2, b2)
            if s < e:
                out.append((s, e))
            if a2 < b2:
                i += 1
            else:
                j += 1
        cur = out
        if not cur:
            break
    return cur

# ----------------------------- Modeling -----------------------------

@dataclass
class PersonDaySpec:
    mode: str  # "free" or "busy"
    intervals: List[Tuple[int,int]]  # as given, inside possibly outside but we clamp

@dataclass
class PersonSpec:
    name: str
    days: Dict[int, PersonDaySpec]  # day index -> spec
    can_clear: bool = False
    clear_limit: int = 0  # minutes, inclusive threshold (<= limit removable)

def normalize_spec_to_free(pspec: PersonDaySpec) -> List[Tuple[int,int]]:
    """Convert a day spec to free-interval list within work window."""
    clamped = []
    for s, e in pspec.intervals:
        iv = clamp_interval(s, e, WORK_START, WORK_END)
        if iv:
            clamped.append(iv)
    if pspec.mode == "free":
        return merge_intervals(clamped)
    elif pspec.mode == "busy":
        # free = work - busy
        busy_u = merge_intervals(clamped)
        return subtract_intervals([(WORK_START, WORK_END)], busy_u)
    else:
        raise ValueError("Unknown mode")

def apply_clearable(busy: List[Tuple[int,int]], clear_limit: int) -> List[Tuple[int,int]]:
    """
    Given busy intervals, remove any interval whose duration <= clear_limit.
    Then merge again (though removing won't create overlaps, but safe).
    """
    kept = []
    for s, e in busy:
        if (e - s) > clear_limit:
            kept.append((s, e))
    return merge_intervals(kept)

def compute_free_for_person_day(person: PersonSpec, day: int) -> List[Tuple[int,int]]:
    spec = person.days[day]
    free = normalize_spec_to_free(spec)
    # If can clear: clearing applies to their busy meetings, regardless of how spec presented.
    if person.can_clear:
        # derive busy from free, clear eligible busy intervals, recompute free
        busy = complement_within_work(free)
        busy2 = apply_clearable(busy, person.clear_limit)
        free2 = subtract_intervals([(WORK_START, WORK_END)], busy2)
        return merge_intervals(free2)
    else:
        return merge_intervals(free)

# ----------------------------- Meeting constraints -----------------------------

def longest_meeting_and_count(all_people: List[PersonSpec], start_grid: int = 30) -> Tuple[int,int, Dict[int, List[Tuple[int,int]]]]:
    """
    start_grid: 60 (on the hour) or 30 (hour/half-hour).
    Returns (max_len_minutes, count_options_of_max_len, details_by_day with common_free intervals)
    """
    common_by_day = {}
    max_len = 0
    count = 0

    for day in range(5):
        frees = [compute_free_for_person_day(p, day) for p in all_people]
        common = intersect_many(frees)
        # Options must start at times aligned to grid within common intervals.
        options = []  # (start, end) maximal possible end within common, but grid affects starts only
        for s, e in common:
            # find first grid-aligned >= s
            first = ((s + start_grid - 1) // start_grid) * start_grid
            t = first
            while t < e:
                # meeting can last up to e - t (end can be any minute up to e)
                options.append((t, e))
                t += start_grid
        common_by_day[day] = common

        for start, endlim in options:
            L = endlim - start
            if L > max_len:
                max_len = L
                count = 1
            elif L == max_len and L > 0:
                count += 1

    if max_len <= 0:
        return (0, 0, common_by_day)
    return (max_len, count, common_by_day)

# ----------------------------- Rendering -----------------------------

def render_intervals(intervals: List[Tuple[int,int]]) -> str:
    return "、".join([f"{min_to_hm(s)} - {min_to_hm(e)}" for s, e in intervals])

def choose_mode_word(mode: str, rng: random.Random) -> str:
    if mode == "free":
        return rng.choice(["以下时间空闲", "仅在以下时间有空", "除以下时间之外都没空"])
    else:
        return rng.choice(["以下时间无法安排会议", "以下时间已经占用", "已预定了以下时间"])

def render_day_spec(day_word: str, spec: PersonDaySpec, rng: random.Random) -> str:
    phrase = choose_mode_word(spec.mode, rng)
    return f"{day_word}：{phrase}：{render_intervals(spec.intervals)}、"

def build_explanation(all_people: List[PersonSpec], grid: int, max_len: int, count: int) -> str:
    grid_txt = "整点或半点" if grid == 30 else "整点"
    # Provide one witness option if exists: find earliest option with max_len.
    witness = None
    for day in range(5):
        frees = [compute_free_for_person_day(p, day) for p in all_people]
        common = intersect_many(frees)
        for s, e in common:
            first = ((s + grid - 1) // grid) * grid
            t = first
            while t < e:
                if e - t == max_len and max_len > 0:
                    witness = (day, t, e)
                    break
                t += grid
            if witness:
                break
        if witness:
            break

    lines = []
    lines.append(f"将每个人每天可用时间转为[{min_to_hm(WORK_START)},{min_to_hm(WORK_END)})内的空闲区间；若某人允许清除≤{all_people[0].clear_limit}分钟会议，则把该人的忙碌区间中时长≤阈值的段删除后再求空闲。")
    lines.append(f"对每个工作日取三人空闲区间交集，得到共同空闲区间；会议开始必须落在{grid_txt}网格上（每{grid}分钟一个起点），长度可延伸到所在共同空闲区间末端。")
    if max_len == 0:
        lines.append("所有网格起点都无法落在共同空闲区间内，因此不存在可安排会议。")
    else:
        d, st, en = witness
        lines.append(f"最长可安排时长为 {max_len} 分钟；例如{DAYS_ZH[d]} {min_to_hm(st)} 开始可持续到 {min_to_hm(en)}。共有 {count} 个网格起点能达到该最长时长。")
    lines.append(f"答案为[{max_len}, {count}]。")
    return "\n".join(lines)

# ----------------------------- Random instance generation -----------------------------

def rand_partition_intervals(rng: random.Random, day_len: int, n: int, min_d: int, max_d: int) -> List[Tuple[int,int]]:
    """
    Generate up to n non-overlapping intervals within work hours.
    """
    intervals = []
    attempts = 0
    while len(intervals) < n and attempts < 2000:
        attempts += 1
        dur = rng.randint(min_d, max_d)
        s = rng.randint(WORK_START, WORK_END - dur)
        e = s + dur
        # keep with minute precision
        ok = True
        for a, b in intervals:
            if not (e <= a or s >= b):
                ok = False
                break
        if ok:
            intervals.append((s, e))
    return merge_intervals(intervals)

def gen_person_week(rng: random.Random, name: str, allow_clear: bool, clear_limit: int) -> PersonSpec:
    days = {}
    for d in range(5):
        mode = rng.choice(["free", "busy"])
        # interval count and durations vary
        k = rng.randint(3, 7)
        if mode == "busy":
            intervals = rand_partition_intervals(rng, WORK_END - WORK_START, k, 5, 80)
        else:
            intervals = rand_partition_intervals(rng, WORK_END - WORK_START, k, 5, 90)
        # Occasionally force some adjacency to create longer contiguous blocks
        if rng.random() < 0.35 and len(intervals) >= 2:
            # try to snap one end to another
            ivs = intervals[:]
            rng.shuffle(ivs)
            a = ivs[0]
            b = ivs[1]
            # snap b.start to a.end or vice versa if possible
            if b[0] < a[1] < b[1]:
                pass
            else:
                if rng.random() < 0.5:
                    newb = (a[1], min(WORK_END, a[1] + (b[1] - b[0])))
                else:
                    newb = (max(WORK_START, b[0]), b[0])  # invalid, skip
                if newb[0] < newb[1]:
                    ivs[1] = newb
                    intervals = merge_intervals([iv for iv in ivs if iv[0] < iv[1]])
        days[d] = PersonDaySpec(mode=mode, intervals=intervals)
    return PersonSpec(name=name, days=days, can_clear=allow_clear, clear_limit=clear_limit)

def names_pool_zh():
    return ["赫伟", "丰杰", "郜磊", "雅婷", "子轩", "思涵", "宇航", "雨桐", "梓涵", "俊杰", "嘉怡", "明哲", "欣妍", "浩然"]

def generate_instance(rng: random.Random) -> Dict[str, Any]:
    # choose 3 people distinct
    pool = names_pool_zh()
    rng.shuffle(pool)
    nms = pool[:3]

    # pick which person can clear (maybe none or one)
    clear_mode = rng.choices(["none", "one"], weights=[0.35, 0.65])[0]
    clear_limit = rng.choice([20, 25, 30, 35, 40])
    clear_idx = None
    if clear_mode == "one":
        clear_idx = rng.randrange(3)

    people = []
    for i, nm in enumerate(nms):
        allow_clear = (clear_idx == i)
        people.append(gen_person_week(rng, nm, allow_clear, clear_limit if allow_clear else 0))

    # meeting start grid
    grid = rng.choice([30, 60])

    # solve
    max_len, count, _ = longest_meeting_and_count(people, start_grid=grid)

    # Ensure non-trivial variety; accept 0 sometimes but not too often
    return {
        "people": people,
        "grid": grid,
        "max_len": max_len,
        "count": count
    }

def render_problem(inst: Dict[str, Any]) -> str:
    people: List[PersonSpec] = inst["people"]
    grid: int = inst["grid"]

    header = []
    header.append(f"{people[0].name}、{people[1].name}、{people[2].name}的工作时间为工作日当地时间早上9点到下午5点，他们想在本周的某个时间一起开会。\n")
    for p in people:
        header.append(f"{p.name} 当地时间本周的日程安排如下：")
        # Render each day
        for d in range(5):
            header.append(render_day_spec(DAYS_ZH[d], p.days[d], rng=random.Random(12345 + d)))  # deterministic phrasing per day
        header.append("")  # blank line

    # Clearable rule
    clear_people = [p for p in people if p.can_clear]
    if clear_people:
        cp = clear_people[0]
        header.append(f"{cp.name}可以从日程安排中清除任何{cp.clear_limit}分钟或更短的会议")
    else:
        header.append("三人都不能从日程安排中清除已安排的会议")

    if grid == 30:
        header.append("如果会议必须在整点或半点开始，请给出可以安排的会议的最长时间（以分钟为单位），以及可安排的选项数(必须是最长时间的)。如果无法安排符合条件的会议，都回答0即可。")
    else:
        header.append("如果会议必须在整点开始，请给出可以安排的会议的最长时间（以分钟为单位），以及可安排的选项数(必须是最长时间的)。如果无法安排符合条件的会议，都回答0即可。")

    header.append("\n请在回答的末尾将可安排的会议最长时间和选项数，按顺序放在[ ]中，无需其他内容，形如：\n[45, 3]")
    return "\n".join(header)

# ----------------------------- Validation / uniqueness-style checks -----------------------------

def verify_solution(inst: Dict[str, Any]) -> None:
    people = inst["people"]
    grid = inst["grid"]
    max_len, count, _ = longest_meeting_and_count(people, start_grid=grid)
    if max_len != inst["max_len"] or count != inst["count"]:
        raise AssertionError("Internal answer mismatch on recomputation.")

    # Cross-check by brute minute scan (independent path):
    # Enumerate all grid-aligned starts, compute maximal end by scanning minute-by-minute within common availability.
    max2 = 0
    count2 = 0
    for d in range(5):
        # build common availability bitmap per minute [540..1020)
        avail = [True] * (WORK_END - WORK_START)
        for p in people:
            free = compute_free_for_person_day(p, d)
            free_mask = [False] * (WORK_END - WORK_START)
            for s, e in free:
                for t in range(s, e):
                    free_mask[t - WORK_START] = True
            for i in range(WORK_END - WORK_START):
                avail[i] = avail[i] and free_mask[i]
        for start in range(WORK_START, WORK_END, grid):
            if not avail[start - WORK_START]:
                continue
            end = start
            while end < WORK_END and avail[end - WORK_START]:
                end += 1
            L = end - start
            if L > max2:
                max2 = L
                count2 = 1
            elif L == max2 and L > 0:
                count2 += 1
    if max2 == 0:
        count2 = 0
    if max2 != max_len or count2 != count:
        raise AssertionError(f"Cross-check failed: got ({max2},{count2}) vs ({max_len},{count}).")

# ----------------------------- Main -----------------------------

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()
    attempts = 0
    max_attempts = 4000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        inst = generate_instance(rng)

        # Avoid too many zero-answer questions by resampling sometimes
        if inst["max_len"] == 0 and rng.random() < 0.7:
            continue

        # Deduplicate by a signature of intervals (to avoid repeats for same seed/count variations)
        sig_parts = [str(inst["grid"])]
        for p in inst["people"]:
            sig_parts.append(p.name + ("C" if p.can_clear else "N") + (str(p.clear_limit) if p.can_clear else ""))
            for d in range(5):
                spec = p.days[d]
                sig_parts.append(spec.mode + ":" + ",".join([f"{s}-{e}" for s, e in spec.intervals]))
        sig = "|".join(sig_parts)
        if sig in seen:
            continue

        # Validate and render
        try:
            verify_solution(inst)
        except Exception as e:
            print(f"[warn] instance rejected due to verification error: {e}", file=sys.stderr)
            continue

        problem = render_problem(inst)
        answer = [inst["max_len"], inst["count"]]
        explanation = build_explanation(inst["people"], inst["grid"], inst["max_len"], inst["count"])

        if not problem.strip() or explanation is None:
            continue

        seen.add(sig)
        out.append({"problem": problem, "answer": answer, "explanation": explanation})

    if len(out) != count:
        print(f"[error] Could not generate enough unique problems. Requested={count}, generated={len(out)}, attempts={attempts}", file=sys.stderr)
        # Fail loudly to avoid silent underfill
        raise SystemExit(1)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()