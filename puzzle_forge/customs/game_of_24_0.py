from fractions import Fraction
from itertools import permutations, product
from typing import List, Tuple, Dict, Any, Union
import random


def _apply_op(a: Fraction, b: Fraction, op: str) -> Fraction:
    """
    对两个分数 a、b 应用二元算术运算符 op，返回结果。
    """
    if op == '+':
        return a + b
    elif op == '-':
        return a - b
    elif op == '*':
        return a * b
    elif op == '/':
        if b == 0:
            raise ZeroDivisionError("Division by zero")
        return a / b
    raise ValueError(f"Unsupported operator: {op}")


def _eval_right_assoc(nums_order: List[int], ops_seq: List[str]) -> Fraction:
    """
    右结合求值：(n0 op0 (n1 op1 (n2 op2 n3)))
    """
    assert len(nums_order) == len(ops_seq) + 1 == 4
    cur = Fraction(nums_order[-1], 1)
    for i in range(len(ops_seq) - 1, -1, -1):
        cur = _apply_op(Fraction(nums_order[i], 1), cur, ops_seq[i])
    return cur


def _enumerate_solutions(nums: List[int], ops_pool: List[str], target: int,
                         op_repeat_allowed: bool) -> List[Tuple[Tuple[int, ...], Tuple[str, ...]]]:
    """
    枚举所有满足右结合表达式值 == target 的候选解。
    """
    sols = []
    if len(nums) != 4 or len(ops_pool) < 3:
        return sols

    num_perms = permutations(nums, 4)
    op_seqs = permutations(ops_pool, 3) if (not op_repeat_allowed) else product(ops_pool, repeat=3)
    op_seqs = list(op_seqs)

    for perm in num_perms:
        for ops_seq in op_seqs:
            try:
                val = _eval_right_assoc(list(perm), list(ops_seq))
            except ZeroDivisionError:
                continue
            if val == Fraction(target, 1):
                sols.append((perm, tuple(ops_seq)))
    return sols


def _canonical_answer(candidates: List[Tuple[Tuple[int, ...], Tuple[str, ...]]]) -> Dict[str, Any]:
    """
    规范化唯一答案选择，暂时返回内部字典格式，后续转换。
    """
    candidates.sort(key=lambda x: (tuple(x[0]), tuple(x[1])))
    best_nums = list(candidates[0][0])
    best_ops = list(candidates[0][1])
    return {"nums": best_nums, "ops": best_ops}


def format_answer_to_tuple(ans_dict: Dict[str, Any]) -> List[Any]:
    """
    【新增函数】
    将内部字典格式 {"nums": [a,b,c,d], "ops": [x,y,z]}
    转换为题目要求的列表嵌套元组格式 [(a,b,c,d), (x,y,z)]
    """
    return [tuple(ans_dict["nums"]), tuple(ans_dict["ops"])]


def _ops_constraints_valid(ops_pool: List[str],
                           op_repeat_allowed: bool,
                           require_plus_or_div: bool,
                           plus_implies_div: bool) -> bool:
    """
    校验运算符池约束
    """
    if not isinstance(ops_pool, list) or len(ops_pool) < 3:
        return False
    has_plus = '+' in ops_pool
    has_div = '/' in ops_pool
    if require_plus_or_div and not (has_plus or has_div):
        return False
    if plus_implies_div and has_plus and not has_div:
        return False
    return True


def function_1(list_len: int,
               min_num: int,
               max_num: int,
               ops_pool_candidates: List[str],
               target_min: int,
               target_max: int,
               max_tries: int,
               op_repeat_allowed: bool,
               require_plus_or_div: bool,
               plus_implies_div: bool) -> Dict[str, Any]:
    """
    生成题目实例
    """
    if list_len != 4:
        raise ValueError("list_len must be 4")
    
    tries = 0
    while tries < max_tries:
        tries += 1
        nums = [random.randint(min_num, max_num) for _ in range(4)]

        ops_pool = None
        for _ in range(20):
            ops_pool_candidate = random.sample(ops_pool_candidates, 3)
            if _ops_constraints_valid(ops_pool_candidate, op_repeat_allowed, require_plus_or_div, plus_implies_div):
                ops_pool = sorted(ops_pool_candidate)
                break
        if ops_pool is None:
            continue

        target = random.randint(target_min, target_max)

        candidates = _enumerate_solutions(nums, ops_pool, target, op_repeat_allowed)
        if len(candidates) == 1:
            dict_answer = _canonical_answer(candidates)
            
            # 使用新函数将答案格式化为 [(nums...), (ops...)]
            formatted_answer = format_answer_to_tuple(dict_answer)

            # 复查计算正确性
            val = _eval_right_assoc(dict_answer["nums"], dict_answer["ops"])
            if val != Fraction(target, 1):
                continue

            return {
                "nums": nums,
                "ops": ops_pool,
                "target": target,
                "answer": formatted_answer, # 存储新格式的答案
                "eval_mode": "right_assoc",
            }

    raise ValueError("Failed to generate a unique-solution instance.")


def function_2(nums: List[int], ops_pool: List[str], target: int, ans_input: Any,
               eval_mode: str, op_repeat_allowed: bool, require_plus_or_div: bool, plus_implies_div: bool) -> bool:
    """
    验证函数：支持解析 [(num1...),(op1...)] 格式的输入
    """
    try:
        ans_nums = []
        ans_ops = []

        # 1. 解析输入格式
        # 期望格式：列表或元组，长度为2。第一个元素是数字集合，第二个是运算符集合
        if isinstance(ans_input, (list, tuple)) and len(ans_input) == 2:
            # 提取数字部分
            if isinstance(ans_input[0], (list, tuple)) and len(ans_input[0]) == 4:
                ans_nums = list(ans_input[0])
            else:
                return False
            
            # 提取运算符部分
            if isinstance(ans_input[1], (list, tuple)) and len(ans_input[1]) == 3:
                ans_ops = list(ans_input[1])
            else:
                return False
        
        # 兼容旧的字典格式（防止某些特定调用出错，可选）
        elif isinstance(ans_input, dict) and "nums" in ans_input and "ops" in ans_input:
             ans_nums = ans_input["nums"]
             ans_ops = ans_input["ops"]
        else:
            return False

        # 2. 校验数字是否匹配（全排列检查）
        if sorted(ans_nums) != sorted(nums):
            return False

        # 3. 校验运算符是否在可用池中
        if any(op not in ops_pool for op in ans_ops):
            return False

        # 4. 校验运算符重复性
        if not op_repeat_allowed:
            if len(set(ans_ops)) != 3:
                return False

        # 5. 校验特定约束
        has_plus = '+' in ans_ops
        has_div = '/' in ans_ops
        if require_plus_or_div and not (has_plus or has_div):
            return False
        if plus_implies_div and has_plus and not has_div:
            return False

        # 6. 计算值校验
        if eval_mode != "right_assoc":
            return False
        val = _eval_right_assoc(ans_nums, ans_ops)
        if val != Fraction(target, 1):
            return False

        # 7. 唯一性校验（重新生成所有解并比对）
        candidates = _enumerate_solutions(nums, ops_pool, target, op_repeat_allowed)
        if len(candidates) != 1:
            return False

        # 将生成的标准答案也格式化，与输入进行比对
        canon_dict = _canonical_answer(candidates)
        # 比对数字顺序
        if tuple(canon_dict["nums"]) != tuple(ans_nums):
            return False
        # 比对运算符顺序
        if tuple(canon_dict["ops"]) != tuple(ans_ops):
            return False

        return True

    except Exception:
        return False