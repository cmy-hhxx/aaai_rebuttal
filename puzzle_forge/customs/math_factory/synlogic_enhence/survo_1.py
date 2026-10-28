import random, itertools, math
from copy import deepcopy
from typing import List, Tuple, Dict

# -------------------------------------------------
# 占位函数
# -------------------------------------------------
def function_1(*args, **kwargs): 
    return args[0] if args else None

def function_2(*args, **kwargs): 
    return {"args": args, "kwargs": kwargs}

# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def _apply(arr: List[int], op: str) -> int:
    return sum(arr) if op == "sum" else math.prod(arr)

def _within_limit(row_vals, col_vals, total, row_lim, col_lim, total_lim):
    return max(row_vals) <= row_lim and max(col_vals) <= col_lim and total <= total_lim

def _has_hole(cells: List[Tuple[int, int]], holes: set) -> bool:
    return any(cell in holes for cell in cells)

def _valid(mat: List[List[int]], op: str, constraints: List[Dict]) -> bool:
    n = len(mat) - 1
    for r in range(n):
        if _apply(mat[r][:n], op) != mat[r][n]:
            return False
    for c in range(n):
        if _apply([mat[r][c] for r in range(n)], op) != mat[n][c]:
            return False
    if _apply(mat[n][:n], op) != mat[n][n]:
        return False
    if _apply([mat[r][n] for r in range(n)], op) != mat[n][n]:
        return False
    for con in constraints:
        if _apply([mat[r][c] for r, c in con["cells"]], con["op"]) != con["value"]:
            return False
    return True

def _unique(template, pool, op, constraints) -> bool:
    n = len(template) - 1
    holes = [(r, c) for r in range(n) for c in range(n) if template[r][c] == "X"]
    perms = set(itertools.permutations(pool, len(holes)))
    count = 0
    for perm in perms:
        if count > 1:
            break
        mat = [row[:] for row in template]
        for (r, c), v in zip(holes, perm):
            mat[r][c] = v
        if _valid(mat, op, constraints):
            count += 1
    return count == 1

# -------------------------------------------------
# Main generator
# -------------------------------------------------
def generate_survo(
    n_min=3, n_max=4, val_min=1, val_max=5,
    row_lim=50_000, col_lim=50_000, total_lim=2_000_000,
    max_retry=600
) -> Dict:
    """
    Generates a Survo puzzle with either sum or product rules.
    Product puzzles are size- and value-restricted for readability.
    Always returns a unique-solution instance with three distinct
    extra constraints (main diag / anti diag / block), each containing
    at least one X.
    """
    for _ in range(max_retry):
        op = random.choice(["sum", "product"])
        n = random.randint(n_min, n_max if op == "sum" else 4)
        cell_max = val_max if op == "sum" else 5

        # --- build core with size controls ---
        attempt = 0
        while True:
            attempt += 1
            if attempt > 500:
                break
            core = [[random.randint(val_min, cell_max) for _ in range(n)]
                    for _ in range(n)]
            rows = [_apply(r, op) for r in core]
            cols = [_apply([core[r][c] for r in range(n)], op) for c in range(n)]
            total = _apply(rows, op)
            if op == "sum" or _within_limit(rows, cols, total,
                                            row_lim, col_lim, total_lim):
                break
        else:
            continue  # regenerate new n/op

        full = [core[r] + [rows[r]] for r in range(n)]
        full.append(cols + [total])

        # --- dig holes ---
        positions = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(positions)
        hole_num = random.randint(max(3, n), min(7, n * n))
        holes = set(positions[:hole_num])

        template = deepcopy(full)
        pool = []
        for r, c in holes:
            pool.append(template[r][c])
            template[r][c] = "X"
        random.shuffle(pool)

        # --- generate 3 distinct extra constraints ---
        constraint_defs = []
        clue_texts = []
        # main diag
        main_cells = [(i, i) for i in range(n)]
        if not _has_hole(main_cells, holes):
            continue
        val_main = _apply([core[r][c] for r, c in main_cells], op)
        constraint_defs.append({"cells": main_cells, "op": op, "value": val_main})
        clue_texts.append(
            f'主对角线({", ".join([f"行{i+1}列{i+1}" for i in range(n)])})的{"和" if op=="sum" else "积"}为{val_main}')

        # anti diag
        anti_cells = [(i, n - 1 - i) for i in range(n)]
        if not _has_hole(anti_cells, holes):
            continue
        val_anti = _apply([core[r][c] for r, c in anti_cells], op)
        constraint_defs.append({"cells": anti_cells, "op": op, "value": val_anti})
        clue_texts.append(
            f'副对角线({", ".join([f"行{i+1}列{n-i}" for i in range(n)])})的{"和" if op=="sum" else "积"}为{val_anti}')

        # block
        block_found = False
        for _b in range(30):
            r0, c0 = random.randrange(n - 1), random.randrange(n - 1)
            blk_cells = [(r0, c0), (r0, c0 + 1), (r0 + 1, c0), (r0 + 1, c0 + 1)]
            if _has_hole(blk_cells, holes):
                val_blk = _apply([core[r][c] for r, c in blk_cells], op)
                constraint_defs.append({"cells": blk_cells, "op": op, "value": val_blk})
                coords = [f'行{r+1}列{c+1}' for r, c in blk_cells]
                clue_texts.append(
                    f'位于{"、".join(coords)}四格数字的{"和" if op=="sum" else "积"}为{val_blk}')
                block_found = True
                break
        if not block_found:
            continue  # regenerate puzzle

        # --- uniqueness check ---
        if _unique(template, pool, op, constraint_defs):
            return {
                "n": n,
                "op_type": op,
                "matrix_initial": template,
                "available_numbers": pool,
                "final_matrix": full,
                "extra_clues_text": clue_texts
            }

    raise RuntimeError("Survo generation failed after retries")