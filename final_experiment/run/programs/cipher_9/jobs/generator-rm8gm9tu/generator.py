import sys, json, random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

OUTER_DISK = "QWERTYUIOPASDFGHJZXCVBNMKL"
INNER_INIT = "JKLZXCVBNMASDFGHJQWERTYUIO"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def rotate_right(s: str, k: int) -> str:
    if not s:
        return s
    k %= len(s)
    if k == 0:
        return s
    return s[-k:] + s[:-k]


def encrypt(plaintext: str, period: int, increment: int,
            outer_disk: str = OUTER_DISK, inner_disk_init: str = INNER_INIT) -> str:
    inner = inner_disk_init
    out = []
    for i, ch in enumerate(plaintext, start=1):
        idx = outer_disk.index(ch)
        out.append(inner[idx])
        if period > 0 and (i % period == 0):
            inner = rotate_right(inner, increment)
    return "".join(out)


def decrypt(ciphertext: str, period: int, increment: int,
            outer_disk: str = OUTER_DISK, inner_disk_init: str = INNER_INIT) -> str:
    inner = inner_disk_init
    out = []
    for i, ch in enumerate(ciphertext, start=1):
        idx = inner.index(ch)
        out.append(outer_disk[idx])
        if period > 0 and (i % period == 0):
            inner = rotate_right(inner, increment)
    return "".join(out)


def mapping_table(outer_disk: str, inner_disk: str) -> Dict[str, str]:
    return {o: inner_disk[i] for i, o in enumerate(outer_disk)}


def inv_mapping_table(outer_disk: str, inner_disk: str) -> Dict[str, str]:
    return {inner_disk[i]: o for i, o in enumerate(outer_disk)}


def format_disk(s: str) -> str:
    # group by 13 for readability
    return s[:13] + " " + s[13:]


def check_upper_letters(s: str) -> bool:
    return len(s) > 0 and all('A' <= c <= 'Z' for c in s)


@dataclass
class Task:
    kind: str  # "enc" or "dec"
    text: str
    period: int
    increment: int


def pick_params(rng: random.Random) -> Tuple[int, int]:
    # keep moderate to show rotations but not too frequent
    period = rng.randint(2, 9)
    increment = rng.randint(1, 12)
    return period, increment


def gen_text(rng: random.Random, length: int) -> str:
    return "".join(rng.choice(ALPHABET) for _ in range(length))


def compute_answer_and_explain(task1: Task, task2: Task, lang: str) -> Tuple[str, Any, str]:
    assert lang == "zh"
    # compute
    if task1.kind == "enc":
        ans1 = encrypt(task1.text, task1.period, task1.increment)
    else:
        ans1 = decrypt(task1.text, task1.period, task1.increment)

    if task2.kind == "enc":
        ans2 = encrypt(task2.text, task2.period, task2.increment)
    else:
        ans2 = decrypt(task2.text, task2.period, task2.increment)

    # cross-check via inverse relation
    if task1.kind == "enc":
        back1 = decrypt(ans1, task1.period, task1.increment)
        if back1 != task1.text:
            raise RuntimeError("交叉核验失败：加密后再解密未还原 task1")
    else:
        back1 = encrypt(ans1, task1.period, task1.increment)
        if back1 != task1.text:
            raise RuntimeError("交叉核验失败：解密后再加密未还原 task1")

    if task2.kind == "enc":
        back2 = decrypt(ans2, task2.period, task2.increment)
        if back2 != task2.text:
            raise RuntimeError("交叉核验失败：加密后再解密未还原 task2")
    else:
        back2 = encrypt(ans2, task2.period, task2.increment)
        if back2 != task2.text:
            raise RuntimeError("交叉核验失败：解密后再加密未还原 task2")

    # build explanation with a small, checkable trace for first few chars of each part
    def trace(kind: str, text: str, period: int, inc: int, steps: int = 4) -> str:
        inner = INNER_INIT
        lines = []
        lines.append(f"外盘: {format_disk(OUTER_DISK)}")
        lines.append(f"初始内盘: {format_disk(INNER_INIT)}")
        for i, ch in enumerate(text[:steps], start=1):
            if kind == "enc":
                mp = mapping_table(OUTER_DISK, inner)
                outch = mp[ch]
                lines.append(f"第{i}个字符 {ch}：查外盘索引→内盘同位={outch}（此时内盘={format_disk(inner)}）")
            else:
                mp = inv_mapping_table(OUTER_DISK, inner)
                outch = mp[ch]
                lines.append(f"第{i}个字符 {ch}：查内盘索引→外盘同位={outch}（此时内盘={format_disk(inner)}）")
            if i % period == 0:
                inner2 = rotate_right(inner, inc)
                lines.append(f"已处理满 {period} 个字符，内盘右移 {inc}：{format_disk(inner)} → {format_disk(inner2)}")
                inner = inner2
        return "\n".join(lines)

    exp = []
    exp.append("要点：逐字符按外盘/内盘同位置替换；每处理 period 个字符，内盘向右轮转 increment 位。")
    exp.append("")
    exp.append("（1）第1问计算过程（展示前4步示例）：")
    exp.append(trace(task1.kind, task1.text, task1.period, task1.increment, steps=min(4, len(task1.text))))
    exp.append("")
    exp.append("（2）第2问计算过程（展示前4步示例）：")
    exp.append(trace(task2.kind, task2.text, task2.period, task2.increment, steps=min(4, len(task2.text))))
    exp.append("")
    exp.append("校验：对每一问将结果按同参数做逆运算，均能还原题目给定字符串。")

    problem_parts = []
    problem_parts.append("你需要按如下旋转替换密码执行加密/解密。")
    problem_parts.append("")
    problem_parts.append("规则（必须严格遵守）：")
    problem_parts.append("- 外盘 outer_disk = \"QWERTYUIOPASDFGHJZXCVBNMKL\"")
    problem_parts.append("- 内盘 inner_disk 初始 = \"JKLZXCVBNMASDFGHJQWERTYUIO\"")
    problem_parts.append("- 加密：明文每个字符在外盘找位置，用内盘同位置字符替换；每处理完 period 个字符后，内盘向右轮转 increment 位。")
    problem_parts.append("- 解密：密文每个字符在内盘找位置，用外盘同位置字符替换；每处理完 period 个字符后，内盘向右轮转 increment 位。")
    problem_parts.append("")
    problem_parts.append("请将每问的最终结果用双中括号包裹输出，且两问答案用“====”连接，例如：[[答案1]]====[[答案2]]。")
    problem_parts.append("")
    # Ask two questions, vary kind and wording
    q1_label = "加密" if task1.kind == "enc" else "解密"
    q2_label = "加密" if task2.kind == "enc" else "解密"
    q1_input_name = "明文" if task1.kind == "enc" else "密文"
    q2_input_name = "明文" if task2.kind == "enc" else "密文"

    problem_parts.append(f"1）请{q1_label}：{q1_input_name} \"{task1.text}\"，period={task1.period}，increment={task1.increment}。")
    problem_parts.append(f"2）请{q2_label}：{q2_input_name} \"{task2.text}\"，period={task2.period}，increment={task2.increment}。")

    problem = "\n".join(problem_parts)
    answer = f"[[{ans1}]]====[[{ans2}]]"
    explanation = "\n".join(exp)
    return problem, answer, explanation


def make_instance(rng: random.Random) -> Tuple[str, str, str]:
    # choose variant family
    # A: Q1 encrypt, Q2 decrypt
    # B: Q1 decrypt, Q2 encrypt
    family = rng.choice(["A", "B"])
    # lengths
    len1 = rng.randint(9, 14)
    len2 = rng.randint(9, 14)
    p1, inc1 = pick_params(rng)
    p2, inc2 = pick_params(rng)

    if family == "A":
        pt = gen_text(rng, len1)
        # ensure period <= len for at least one rotation often
        if p1 > len1:
            p1 = max(2, len1 // 2)
        ct = encrypt(gen_text(rng, len2), p2, inc2)  # generate ciphertext by encrypting random plaintext
        # But we must present ciphertext; keep it as ct, and task2 is decrypt
        task1 = Task("enc", pt, p1, inc1)
        task2 = Task("dec", ct, p2, inc2)
    else:
        # Q1 decrypt: generate ciphertext from random plaintext then ask to decrypt that ciphertext
        base_pt1 = gen_text(rng, len1)
        if p1 > len1:
            p1 = max(2, len1 // 2)
        ct1 = encrypt(base_pt1, p1, inc1)
        # Q2 encrypt
        pt2 = gen_text(rng, len2)
        if p2 > len2:
            p2 = max(2, len2 // 2)
        task1 = Task("dec", ct1, p1, inc1)
        task2 = Task("enc", pt2, p2, inc2)

    return compute_answer_and_explain(task1, task2, "zh")


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = count * 30

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            problem, answer, explanation = make_instance(rng)
            key = (problem, answer)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "problem": problem,
                "answer": answer,
                "explanation": explanation
            })
        except Exception as e:
            print(f"[warn] 生成失败重试：{e}", file=sys.stderr)
            continue

    if len(results) != count:
        raise SystemExit(f"无法在尝试次数内生成足够题目：需要{count}，得到{len(results)}，尝试{attempts}")

    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=None))


if __name__ == "__main__":
    main()