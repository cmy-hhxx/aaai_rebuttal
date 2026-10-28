import sys, json, math, random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

# -----------------------------
# Utilities
# -----------------------------

def abs_int(x: int) -> int:
    return -x if x < 0 else x

def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs_int(a)

@dataclass(frozen=True)
class Rat:
    n: int
    d: int = 1

    def __post_init__(self):
        if self.d == 0:
            raise ZeroDivisionError("Denominator cannot be zero")
        n, d = self.n, self.d
        if d < 0:
            n, d = -n, -d
        g = gcd(abs_int(n), d)
        object.__setattr__(self, "n", n // g)
        object.__setattr__(self, "d", d // g)

    def __add__(self, other: "Rat") -> "Rat":
        return Rat(self.n * other.d + other.n * self.d, self.d * other.d)

    def __sub__(self, other: "Rat") -> "Rat":
        return Rat(self.n * other.d - other.n * self.d, self.d * other.d)

    def __mul__(self, other: "Rat") -> "Rat":
        return Rat(self.n * other.n, self.d * other.d)

    def __truediv__(self, other: "Rat") -> "Rat":
        if other.n == 0:
            raise ZeroDivisionError("division by zero")
        return Rat(self.n * other.d, self.d * other.n)

    def __neg__(self) -> "Rat":
        return Rat(-self.n, self.d)

    def __pow__(self, k: int) -> "Rat":
        if k < 0:
            # invert
            if self.n == 0:
                raise ZeroDivisionError("0 cannot be raised to negative power")
            return Rat(self.d, self.n) ** (-k)
        return Rat(self.n ** k, self.d ** k)

    def is_int(self) -> bool:
        return self.d == 1

    def to_json_value(self):
        if self.d == 1:
            return self.n
        return f"{self.n}/{self.d}"

    def __str__(self) -> str:
        if self.d == 1:
            return str(self.n)
        return f"{self.n}/{self.d}"

def rat_from_int(x: int) -> Rat:
    return Rat(x, 1)

def rat_abs(r: Rat) -> Rat:
    return Rat(abs_int(r.n), r.d)

# -----------------------------
# Expression AST and evaluation
# -----------------------------

class Expr:
    def eval(self) -> Rat:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError

class Num(Expr):
    def __init__(self, r: Rat):
        self.r = r

    def eval(self) -> Rat:
        return self.r

    def to_str(self) -> str:
        # Render negative rationals with parentheses when used as atom in larger expressions;
        # caller decides. Here return canonical.
        return str(self.r)

class BinOp(Expr):
    def __init__(self, op: str, a: Expr, b: Expr):
        self.op = op
        self.a = a
        self.b = b

    def eval(self) -> Rat:
        A, B = self.a.eval(), self.b.eval()
        if self.op == "+":
            return A + B
        if self.op == "-":
            return A - B
        if self.op == "*":
            return A * B
        if self.op == "/":
            return A / B
        if self.op == "%":
            # define for integers only (like Python)
            if not (A.is_int() and B.is_int()):
                raise ValueError("Modulo only defined for integers in this generator")
            if B.n == 0:
                raise ZeroDivisionError("modulo by zero")
            return Rat(A.n % B.n, 1)
        if self.op == "**":
            if not B.is_int():
                raise ValueError("Exponent must be integer in this generator")
            k = B.n
            # Keep k small; enforced by generator
            return A ** k
        if self.op == "⊙":
            # x ⊙ y = x**2 * Abs(y), on reals. Here with rationals.
            # x**2 always non-negative rational; Abs(y) defined.
            x2 = A ** 2
            return x2 * rat_abs(B)
        raise ValueError(f"Unknown op {self.op}")

    def to_str(self) -> str:
        return f"{self.a.to_str()} {self.op} {self.b.to_str()}"

class Paren(Expr):
    def __init__(self, e: Expr):
        self.e = e

    def eval(self) -> Rat:
        return self.e.eval()

    def to_str(self) -> str:
        return f"({self.e.to_str()})"

# -----------------------------
# Pretty rendering with precedence control
# -----------------------------

# precedence: higher number => binds tighter
PREC = {
    "+": 1, "-": 1,
    "*": 2, "/": 2, "%": 2,
    "**": 3, "⊙": 3,
    "ATOM": 4
}

RIGHT_ASSOC = {"**"}  # ⊙ treat as left-assoc like * here

def expr_to_string(e: Expr) -> str:
    def helper(node: Expr, parent_prec: int, is_right_child: bool, parent_op: Optional[str]) -> str:
        if isinstance(node, Num):
            s = node.to_str()
            # if negative number and in non-atom context, parenthesize
            if node.r.n < 0 and node.r.d == 1 and parent_prec < PREC["ATOM"]:
                return f"({s})"
            if node.r.n < 0 and node.r.d != 1 and parent_prec < PREC["ATOM"]:
                return f"({s})"
            return s
        if isinstance(node, Paren):
            return node.to_str()
        if isinstance(node, BinOp):
            op = node.op
            prec = PREC[op]
            left_s = helper(node.a, prec, False, op)
            right_s = helper(node.b, prec, True, op)

            s = f"{left_s} {op} {right_s}"

            need_paren = False
            if prec < parent_prec:
                need_paren = True
            elif prec == parent_prec:
                # For left-assoc ops, right child with same prec needs parentheses to preserve tree
                # For right-assoc ops (**), left child with same prec needs parentheses
                if parent_op in RIGHT_ASSOC:
                    # parent right associative
                    if not is_right_child:
                        need_paren = True
                else:
                    # parent left associative (including ⊙ here)
                    if is_right_child:
                        # Exception: for associative ops like +, * we could omit,
                        # but to be safe keep parentheses to match exact structure.
                        need_paren = True
            if need_paren:
                return f"({s})"
            return s
        raise TypeError("Unknown node type")

    return helper(e, 0, False, None)

# -----------------------------
# Independent verification (tokenize -> parse -> eval)
# -----------------------------

def tokenize(expr: str) -> List[str]:
    # Tokens: integers, '/', '+-*/%()⊙', '**'
    tokens = []
    i = 0
    while i < len(expr):
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit() or (c == '-' and i + 1 < len(expr) and expr[i+1].isdigit()):
            # parse signed integer (sign only if directly attached)
            j = i + 1 if c == '-' else i
            while j < len(expr) and expr[j].isdigit():
                j += 1
            tokens.append(expr[i:j])
            i = j
            continue
        if c == '*':
            if i + 1 < len(expr) and expr[i+1] == '*':
                tokens.append('**')
                i += 2
            else:
                tokens.append('*')
                i += 1
            continue
        if c in '+/()%':
            tokens.append(c)
            i += 1
            continue
        if c == '-':
            tokens.append('-')
            i += 1
            continue
        if c == '⊙':
            tokens.append('⊙')
            i += 1
            continue
        # For safety accept some unicode spaces etc.
        raise ValueError(f"Unexpected char {c!r} in expr {expr!r}")
    return tokens

class Parser:
    def __init__(self, tokens: List[str]):
        self.toks = tokens
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def pop(self, expected: Optional[str] = None) -> str:
        if self.i >= len(self.toks):
            raise ValueError("Unexpected end of tokens")
        t = self.toks[self.i]
        if expected is not None and t != expected:
            raise ValueError(f"Expected {expected}, got {t}")
        self.i += 1
        return t

    def parse(self) -> Expr:
        e = self.parse_add()
        if self.peek() is not None:
            raise ValueError(f"Extra tokens: {self.toks[self.i:]}")
        return e

    def parse_add(self) -> Expr:
        e = self.parse_mul()
        while self.peek() in ('+', '-'):
            op = self.pop()
            r = self.parse_mul()
            e = BinOp(op, e, r)
        return e

    def parse_mul(self) -> Expr:
        e = self.parse_pow()
        while self.peek() in ('*', '/', '%'):
            op = self.pop()
            r = self.parse_pow()
            e = BinOp(op, e, r)
        return e

    def parse_pow(self) -> Expr:
        # precedence group: ** and ⊙ (same level); ** right-assoc, ⊙ left-assoc.
        # We'll parse as: parse_atom then while next is ⊙ apply left; if next is ** do right recursion.
        # To respect the "same precedence" declaration, we need a deterministic association.
        # We choose:
        # - '**' is right associative
        # - '⊙' is left associative
        # and both higher than * / %.
        e = self.parse_atom()
        # handle chains with mixture: we will process by reading operators and building
        # using precedence ties: '**' binds right, '⊙' binds left. We'll implement
        # a small shunting-yard for this level only.
        ops = []
        vals = [e]

        def op_prec(op: str) -> int:
            return PREC[op]

        def op_right_assoc(op: str) -> bool:
            return op in RIGHT_ASSOC

        def reduce_once():
            op = ops.pop()
            b = vals.pop()
            a = vals.pop()
            vals.append(BinOp(op, a, b))

        while self.peek() in ('**', '⊙'):
            op = self.pop()
            # read next atom
            rhs = self.parse_atom()
            # reduce based on precedence (equal) and associativity
            while ops:
                top = ops[-1]
                if op_prec(top) > op_prec(op):
                    reduce_once()
                elif op_prec(top) == op_prec(op):
                    # if current op is right-assoc, do not reduce on equal
                    # if left-assoc, reduce on equal
                    if not op_right_assoc(op):
                        reduce_once()
                    else:
                        break
                else:
                    break
            ops.append(op)
            vals.append(rhs)

        while ops:
            reduce_once()
        return vals[0]

    def parse_atom(self) -> Expr:
        t = self.peek()
        if t is None:
            raise ValueError("Unexpected end")
        if t == '(':
            self.pop('(')
            e = self.parse_add()
            self.pop(')')
            return Paren(e)
        # number or rational a/b (rendered without spaces by our renderer)
        # However tokenization splits '/', so we handle here:
        if t.lstrip('-').isdigit():
            a = int(self.pop())
            if self.peek() == '/':
                self.pop('/')
                b_tok = self.pop()
                if not b_tok.lstrip('-').isdigit():
                    raise ValueError("Invalid rational")
                b = int(b_tok)
                return Num(Rat(a, b))
            return Num(Rat(a, 1))
        if t == '-':
            # unary minus: - atom
            self.pop('-')
            e = self.parse_atom()
            return BinOp("*", Num(Rat(-1, 1)), e)
        raise ValueError(f"Unexpected token {t}")

def independent_eval(expr_str: str) -> Rat:
    toks = tokenize(expr_str)
    ast = Parser(toks).parse()
    return ast.eval()

# -----------------------------
# Generation logic
# -----------------------------

def rand_nonzero_int(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        x = rng.randint(lo, hi)
        if x != 0:
            return x

def rand_small_rat(rng: random.Random, allow_negative=True) -> Rat:
    # produce small rational a/b with small b
    b = rng.choice([1, 1, 1, 2, 3, 4, 5])
    a = rng.randint(-12, 12) if allow_negative else rng.randint(0, 12)
    if b != 1 and a == 0:
        return Rat(0, 1)
    if b == 1:
        return Rat(a, 1)
    # avoid denominator 0; ensure reduced in Rat
    return Rat(a, b)

def make_atom(rng: random.Random) -> Expr:
    r = rand_small_rat(rng, allow_negative=True)
    return Num(r)

def make_expr_family_simple(rng: random.Random) -> Expr:
    # Direct x ⊙ y, where x, y are integers/rationals
    x = make_atom(rng)
    y = make_atom(rng)
    # Ensure not too trivial
    return BinOp("⊙", x, y)

def make_expr_family_mix(rng: random.Random) -> Expr:
    # Mix with +,*,/,%,**, parentheses ensuring validity and manageable size
    # Template examples:
    # (a ⊙ b) + (c ⊙ d)
    # (a + b) ⊙ (c - d)
    # (a ⊙ b) * (c + d)
    # (a ** k) ⊙ (b + c)
    # (a ⊙ b) / m
    choice = rng.randint(1, 6)
    if choice == 1:
        a, b, c, d = make_atom(rng), make_atom(rng), make_atom(rng), make_atom(rng)
        return BinOp("+", Paren(BinOp("⊙", a, b)), Paren(BinOp("⊙", c, d)))
    if choice == 2:
        a, b, c, d = make_atom(rng), make_atom(rng), make_atom(rng), make_atom(rng)
        left = Paren(BinOp("+", a, b))
        right = Paren(BinOp("-", c, d))
        return BinOp("⊙", left, right)
    if choice == 3:
        a, b, c, d = make_atom(rng), make_atom(rng), make_atom(rng), make_atom(rng)
        return BinOp("*", Paren(BinOp("⊙", a, b)), Paren(BinOp("+", c, d)))
    if choice == 4:
        a = make_atom(rng)
        k = rng.choice([2, 3, 4])
        b, c = make_atom(rng), make_atom(rng)
        left = Paren(BinOp("**", a, Num(Rat(k, 1))))
        right = Paren(BinOp("+", b, c))
        return BinOp("⊙", left, right)
    if choice == 5:
        a, b = make_atom(rng), make_atom(rng)
        m = rand_nonzero_int(rng, 2, 9)
        return BinOp("/", Paren(BinOp("⊙", a, b)), Num(Rat(m, 1)))
    # include modulo with integers only
    # ((p ⊙ q) % t) + u
    p = Num(Rat(rng.randint(-9, 9), 1))
    q = Num(Rat(rng.randint(-9, 9), 1))
    t = Num(Rat(rand_nonzero_int(rng, 2, 9), 1))
    u = make_atom(rng)
    return BinOp("+", Paren(BinOp("%", Paren(BinOp("⊙", p, q)), t)), u)

def make_expr_family_chain(rng: random.Random) -> Expr:
    # Chain with precedence: ⊙ and ** higher than * etc. Ensure parentheses sometimes.
    # Example: a ⊙ b + c * (d ⊙ e) - f
    a, b, c, d, e, f = [make_atom(rng) for _ in range(6)]
    part1 = BinOp("⊙", a, b)
    part2 = BinOp("*", c, Paren(BinOp("⊙", d, e)))
    expr = BinOp("+", part1, part2)
    expr = BinOp("-", expr, f)
    return expr

def safe_eval(expr: Expr) -> Rat:
    return expr.eval()

def build_problem_text(expr_str: str, op_def_variant: int, output_language: str) -> str:
    # Multiple statement variants, same core definition
    if output_language != "zh":
        # As per instruction, no translation API; fallback to Chinese
        output_language = "zh"

    variants = [
        "在实数域上定义运算 ⊙：对任意实数 x, y，规定 x ⊙ y = x**2 * Abs(y)。",
        "给定二元运算 ⊙（定义在实数上）：x ⊙ y := (x 的平方) × |y|，即 x ⊙ y = x**2*Abs(y)。",
        "定义符号运算 ⊙：x ⊙ y = x**2·Abs(y)，其中 Abs(y) 表示 y 的绝对值。"
    ]
    prec = "运算优先级规定：括号最高；其后 ** 与 ⊙ 同级且高于 * / %；最后是 + -。"
    ask = f"请计算下列表达式的值：{expr_str}。"
    return variants[op_def_variant % len(variants)] + "\n" + prec + "\n" + ask

def build_explanation(expr_str: str, value: Rat, steps: List[str], output_language: str) -> str:
    if output_language != "zh":
        output_language = "zh"
    s = "按题目给定优先级与定义计算：\n"
    for st in steps:
        s += f"- {st}\n"
    s += f"因此结果为 {value}。"
    return s

def derive_steps(expr: Expr, expr_str: str, val: Rat) -> List[str]:
    # Provide brief, checkable steps for common structures
    # We'll compute some key subexpressions by traversing.
    steps = []
    # If expression contains top-level op, show evaluation of each BinOp one layer deep
    def show(node: Expr) -> str:
        return expr_to_string(node)

    if isinstance(expr, BinOp) and expr.op == "⊙":
        A = expr.a.eval()
        B = expr.b.eval()
        steps.append(f"先算 x={show(expr.a)}={A}，y={show(expr.b)}={B}。")
        steps.append(f"根据定义 x ⊙ y = x**2*Abs(y)，有 {A} ⊙ {B} = ({A})**2 * Abs({B})。")
        steps.append(f"({A})**2 = {(A**2)}，Abs({B}) = {rat_abs(B)}，相乘得 {(A**2)*rat_abs(B)}。")
        return steps

    if isinstance(expr, BinOp):
        # generic: compute left and right then apply op
        try:
            A = expr.a.eval()
            B = expr.b.eval()
            steps.append(f"先分别计算：左边 {show(expr.a)} = {A}，右边 {show(expr.b)} = {B}。")
            if expr.op == "⊙":
                steps.append(f"再用定义：{A} ⊙ {B} = ({A})**2 * Abs({B}) = {(A**2)} * {rat_abs(B)} = {(A**2)*rat_abs(B)}。")
            elif expr.op == "**":
                steps.append(f"再算幂：{A} ** {B} = {Rat(A.n, A.d) ** B.n}（指数为整数 {B.n}）。")
            elif expr.op == "%":
                steps.append(f"取模：{A.n} % {B.n} = {A.n % B.n}。")
            elif expr.op == "/":
                steps.append(f"相除：{A} / {B} = {A / B}。")
            elif expr.op == "*":
                steps.append(f"相乘：{A} * {B} = {A * B}。")
            elif expr.op == "+":
                steps.append(f"相加：{A} + {B} = {A + B}。")
            elif expr.op == "-":
                steps.append(f"相减：{A} - {B} = {A - B}。")
        except Exception:
            steps.append(f"逐步代入定义与运算优先级计算，可得 {expr_str} = {val}。")
        return steps

    steps.append(f"直接计算可得 {expr_str} = {val}。")
    return steps

# -----------------------------
# Main generate loop with checks
# -----------------------------

def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # choose a family
    family = rng.choices(
        population=["simple", "mix", "chain"],
        weights=[3, 5, 2],
        k=1
    )[0]

    if family == "simple":
        expr = make_expr_family_simple(rng)
    elif family == "mix":
        expr = make_expr_family_mix(rng)
    else:
        expr = make_expr_family_chain(rng)

    expr_str = expr_to_string(expr)

    # Solve
    val = safe_eval(expr)

    # Independent cross-check by parsing rendered string (different code path)
    val2 = independent_eval(expr_str)
    if val.n != val2.n or val.d != val2.d:
        raise AssertionError(f"Cross-check failed: {expr_str} -> {val} vs {val2}")

    # Keep numbers reasonable (avoid huge)
    if abs_int(val.n) > 10**8 or val.d > 10**6:
        raise ValueError("Value too large, resample")

    # Build problem
    op_def_variant = rng.randint(0, 10)
    problem = build_problem_text(expr_str, op_def_variant, output_language)

    steps = derive_steps(expr, expr_str, val)
    explanation = build_explanation(expr_str, val, steps, output_language)

    ans = val.to_json_value()
    return {"problem": problem, "answer": ans, "explanation": explanation}

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = data.get("output_language", "zh")

    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = max(200, count * 40)

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng, output_language)
            key = item["problem"]
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
        except Exception as e:
            print(f"[warn] generation failed attempt={attempts}: {e}", file=sys.stderr)
            continue

    if len(results) < count:
        raise RuntimeError(f"Could not generate enough problems: got {len(results)} / {count} after {attempts} attempts")

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()