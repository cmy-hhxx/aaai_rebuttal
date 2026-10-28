import sys, json, random
from typing import List, Dict, Any, Optional, Tuple

# We will use z3 for robust equation solving (digits 0..9)
from z3 import Ints, Solver, And, Or, sat

# -----------------------------
# Utilities
# -----------------------------

def fmt_eq(template: str, vals: Dict[str, int], target: int) -> str:
    """Fill placeholders like a,b,c,... in template and append =target already inside template."""
    s = template
    for k, v in vals.items():
        s = s.replace(k, str(v))
    # ensure it's wrapped as required
    return f"[[{s}={target}]]"

def z3_digit(varname: str):
    from z3 import Int
    v = Int(varname)
    return v

def model_to_int(m, v):
    return int(m[v].as_long())

def pick_nonzero_digit(rng: random.Random) -> int:
    return rng.choice([1,2,3,4,5,6,7,8,9])

def pick_digit(rng: random.Random) -> int:
    return rng.randrange(10)

def stable_hashable_problem(problem: str) -> str:
    # exact string is enough; keep stable
    return problem

# -----------------------------
# Problem families
# -----------------------------

class Family1_LinearMul:
    """
    Form: a + b*c - d = T
    digits 0..9, normal precedence.
    Goal: provide one feasible solution.
    """
    template = "a+b*c-d"
    vars = ["a", "b", "c", "d"]

    def generate(self, rng: random.Random) -> Tuple[str, Dict[str,int], int, str]:
        # choose target with controlled range for easy existence
        T = rng.randint(-5, 25)
        # build a guaranteed solution by construction, then later verify with z3.
        # choose b,c then choose a,d to hit target: a - d = T - b*c
        b = pick_digit(rng)
        c = pick_digit(rng)
        bc = b*c
        rhs = T - bc
        # Need digits a,d such that a-d = rhs in [-9,9]
        # If not, resample T,b,c a bit.
        for _ in range(200):
            if -9 <= rhs <= 9:
                # Choose a,d within 0..9 with that difference
                # a = d + rhs
                # pick d such that a within 0..9
                ds = [d for d in range(10) if 0 <= d + rhs <= 9]
                if ds:
                    d = rng.choice(ds)
                    a = d + rhs
                    sol = {"a": a, "b": b, "c": c, "d": d}
                    eq = fmt_eq(self.template, sol, T)
                    expl = (
                        f"按运算顺序先算乘法：{b}*{c}={bc}。\n"
                        f"然后计算：{a}+{bc}-{d}={a+bc-d}，等于目标 {T}。"
                    )
                    return eq, sol, T, expl
            # resample b,c,T
            T = rng.randint(-5, 25)
            b = pick_digit(rng)
            c = pick_digit(rng)
            bc = b*c
            rhs = T - bc
        raise RuntimeError("Family1_LinearMul: failed to construct instance")

    def solve_with_z3(self, target: int) -> Optional[Dict[str,int]]:
        a,b,c,d = Ints("a b c d")
        s = Solver()
        s.add(And(a>=0,a<=9,b>=0,b<=9,c>=0,c<=9,d>=0,d<=9))
        s.add(a + b*c - d == target)
        if s.check() != sat:
            return None
        m = s.model()
        return {"a": model_to_int(m,a), "b": model_to_int(m,b), "c": model_to_int(m,c), "d": model_to_int(m,d)}

class Family2_FractionCombo:
    """
    Form: a/b + c/d - e - f = T
    digits 0..9, denominators nonzero.
    Using rational arithmetic (z3 Int with cross-multiply).
    """
    template = "a/b+c/d-e-f"
    vars = ["a","b","c","d","e","f"]

    def generate(self, rng: random.Random) -> Tuple[str, Dict[str,int], int, str]:
        # Keep targets in a comfortable range
        T = rng.randint(-12, 12)

        # Construct by choosing b=d=1 to simplify (still valid fractions).
        b = 1
        d = 1
        a = pick_digit(rng)
        c = pick_digit(rng)
        # Need e+f = a+c - T, with digits 0..9
        need = a + c - T
        for _ in range(200):
            if 0 <= need <= 18:
                # pick e in [0,9], f=need-e in [0,9]
                candidates = [(e, need-e) for e in range(10) if 0 <= need-e <= 9]
                if candidates:
                    e,f = rng.choice(candidates)
                    sol = {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f}
                    eq = fmt_eq(self.template, sol, T)
                    expl = (
                        f"因为 b=d=1，所以 {a}/{b}={a}，{c}/{d}={c}。\n"
                        f"代入：{a}+{c}-{e}-{f}={a+c-e-f}，等于目标 {T}。"
                    )
                    return eq, sol, T, expl
            # resample
            T = rng.randint(-12, 12)
            a = pick_digit(rng)
            c = pick_digit(rng)
            need = a + c - T
        raise RuntimeError("Family2_FractionCombo: failed to construct instance")

    def solve_with_z3(self, target: int) -> Optional[Dict[str,int]]:
        # enforce exact rational equality by cross-multiplying: (a*d + c*b) / (b*d) - e - f == T
        # => a*d + c*b - (e+f+T)*b*d == 0
        a,b,c,d,e,f = Ints("a b c d e f")
        s = Solver()
        s.add(And(a>=0,a<=9,c>=0,c<=9,e>=0,e<=9,f>=0,f<=9))
        s.add(And(b>=1,b<=9,d>=1,d<=9))
        s.add(a*d + c*b - (e+f+target)*b*d == 0)
        if s.check() != sat:
            return None
        m = s.model()
        return {
            "a": model_to_int(m,a), "b": model_to_int(m,b),
            "c": model_to_int(m,c), "d": model_to_int(m,d),
            "e": model_to_int(m,e), "f": model_to_int(m,f)
        }

class Family3_ParenVariant:
    """
    Add a structurally different variant within same domain:
    Form: (a+b)*c - d = T
    digits 0..9.
    """
    template = "(a+b)*c-d"
    vars = ["a","b","c","d"]

    def generate(self, rng: random.Random) -> Tuple[str, Dict[str,int], int, str]:
        T = rng.randint(-10, 60)
        # Construct: choose a,b,c then choose d to match: d = (a+b)*c - T
        for _ in range(400):
            a = pick_digit(rng)
            b = pick_digit(rng)
            c = pick_digit(rng)
            val = (a+b)*c
            d = val - T
            if 0 <= d <= 9:
                sol = {"a": a, "b": b, "c": c, "d": d}
                eq = fmt_eq(self.template, sol, T)
                expl = (
                    f"先算括号：({a}+{b})={a+b}；再乘：({a+b})*{c}={val}；最后减：{val}-{d}={val-d}，得到 {T}。"
                )
                return eq, sol, T, expl
            T = rng.randint(-10, 60)
        raise RuntimeError("Family3_ParenVariant: failed to construct instance")

    def solve_with_z3(self, target: int) -> Optional[Dict[str,int]]:
        a,b,c,d = Ints("a b c d")
        s = Solver()
        s.add(And(a>=0,a<=9,b>=0,b<=9,c>=0,c<=9,d>=0,d<=9))
        s.add((a+b)*c - d == target)
        if s.check() != sat:
            return None
        m = s.model()
        return {"a": model_to_int(m,a), "b": model_to_int(m,b), "c": model_to_int(m,c), "d": model_to_int(m,d)}

class Family4_TwoFractionsMinusProduct:
    """
    Another variant:
    Form: a/b + c/d - e*f = T
    digits 0..9, denominators nonzero.
    """
    template = "a/b+c/d-e*f"
    vars = ["a","b","c","d","e","f"]

    def generate(self, rng: random.Random) -> Tuple[str, Dict[str,int], int, str]:
        # pick denominators 1..9 and try construct with b=d=1 often, but not always
        T = rng.randint(-20, 20)
        for _ in range(600):
            # bias to simple denominators but allow variety
            b = 1 if rng.random() < 0.6 else pick_nonzero_digit(rng)
            d = 1 if rng.random() < 0.6 else pick_nonzero_digit(rng)
            a = pick_digit(rng)
            c = pick_digit(rng)
            e = pick_digit(rng)
            f = pick_digit(rng)
            # compute value as exact rational via integer check by scaling with lcm = b*d
            # value = a/b + c/d - e*f
            num = a*d + c*b
            den = b*d
            # want num/den - e*f = T => num = (T + e*f) * den
            want = (T + e*f) * den
            # adjust one variable to make it work: choose c to satisfy
            # num = a*d + c*b => c = (want - a*d)/b must be integer 0..9
            rem = want - a*d
            if rem % b == 0:
                c2 = rem // b
                if 0 <= c2 <= 9:
                    c = int(c2)
                    sol = {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f}
                    eq = fmt_eq(self.template, sol, T)
                    # Explain with common denominator
                    expl = (
                        f"通分到分母 {b}*{d}={den}：\n"
                        f"{a}/{b}+{c}/{d} = ({a}*{d}+{c}*{b})/{den} = ({a*d}+{c*b})/{den} = {want}/{den} = {T+e*f}。\n"
                        f"再减去 {e}*{f}={e*f}，得到 {T}。"
                    )
                    return eq, sol, T, expl
            T = rng.randint(-20, 20)
        raise RuntimeError("Family4_TwoFractionsMinusProduct: failed to construct instance")

    def solve_with_z3(self, target: int) -> Optional[Dict[str,int]]:
        a,b,c,d,e,f = Ints("a b c d e f")
        s = Solver()
        s.add(And(a>=0,a<=9,c>=0,c<=9,e>=0,e<=9,f>=0,f<=9))
        s.add(And(b>=1,b<=9,d>=1,d<=9))
        # a/b + c/d - e*f = T  => a*d + c*b - (T+e*f)*b*d == 0
        s.add(a*d + c*b - (target + e*f)*b*d == 0)
        if s.check() != sat:
            return None
        m = s.model()
        return {
            "a": model_to_int(m,a), "b": model_to_int(m,b),
            "c": model_to_int(m,c), "d": model_to_int(m,d),
            "e": model_to_int(m,e), "f": model_to_int(m,f)
        }

# -----------------------------
# Rendering (Chinese)
# -----------------------------

def render_problem(family_name: str, eq_form_desc: str, target: int, extra_rules: str = "") -> str:
    base = (
        "在下面的等式中，每个字母位置都要填入一个 0~9 的数字（每个位置可重复使用）。\n"
        "按照正常运算顺序（括号 > 乘除 > 加减）计算。\n"
        f"请给出任意一个可行解，使等式结果等于 {target}。\n"
    )
    if extra_rules:
        base += extra_rules.strip() + "\n"
    base += (
        f"等式形式：{eq_form_desc}。\n"
        "输出时请把你填好的完整等式用双层方括号括起来，例如：[[...=目标值]]。\n"
    )
    return base

# -----------------------------
# Validation / Cross-check
# -----------------------------

def eval_expr_python(expr: str) -> float:
    # expr uses digits and operators + - * / parentheses
    # safe eval: only allow characters in whitelist
    allowed = set("0123456789+-*/() ")
    if any(ch not in allowed for ch in expr):
        raise ValueError("Unsafe expression")
    return eval(expr, {"__builtins__": {}})

def parse_equation(equation_wrapped: str) -> Tuple[str, int]:
    # expects [[expr=target]]
    if not (equation_wrapped.startswith("[[") and equation_wrapped.endswith("]]")):
        raise ValueError("Missing [[ ]]")
    inner = equation_wrapped[2:-2]
    if "=" not in inner:
        raise ValueError("Missing '='")
    expr, tgt = inner.rsplit("=", 1)
    expr = expr.strip()
    tgt = int(tgt.strip())
    return expr, tgt

def cross_check(equation_wrapped: str) -> None:
    expr, tgt = parse_equation(equation_wrapped)
    val = eval_expr_python(expr)
    # exactness: expressions can be rational; compare with tolerance but should be exact for these constructions
    if abs(val - tgt) > 1e-9:
        raise AssertionError(f"Equation does not match: {expr} = {val}, target {tgt}")

# -----------------------------
# Main generation loop
# -----------------------------

def generate_one(rng: random.Random) -> Dict[str, Any]:
    families = [
        ("F1", Family1_LinearMul(), "a+b*c-d"),
        ("F2", Family2_FractionCombo(), "a/b+c/d-e-f（其中 b,d 不能为 0）"),
        ("F3", Family3_ParenVariant(), "(a+b)*c-d"),
        ("F4", Family4_TwoFractionsMinusProduct(), "a/b+c/d-e*f（其中 b,d 不能为 0）"),
    ]
    # choose a family
    tag, fam, desc = rng.choice(families)

    eq_wrapped, sol, target, expl = fam.generate(rng)

    # z3 independent solve check: ensure at least satisfiable (not necessarily same solution)
    z3_sol = fam.solve_with_z3(target)
    if z3_sol is None:
        raise AssertionError("Z3 says unsat, but we constructed a solution")

    # python evaluation cross-check for our produced equation
    cross_check(eq_wrapped)

    # problem statement
    extra = ""
    if tag in ("F2", "F4"):
        extra = "注意：分母位置必须填 1~9，不能填 0。"
    problem = render_problem(tag, desc, target, extra_rules=extra)

    return {
        "problem": problem,
        "answer": eq_wrapped,
        "explanation": expl
    }

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results: List[Dict[str, Any]] = []
    seen = set()

    max_attempts = 2000
    attempts = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng)
            key = stable_hashable_problem(item["problem"] + "\n" + str(item["answer"]))
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
        except Exception as e:
            print(f"[warn] attempt {attempts} failed: {e}", file=sys.stderr)
            continue

    if len(results) < count:
        raise RuntimeError(f"Failed to generate enough unique problems: {len(results)}/{count}")

    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()