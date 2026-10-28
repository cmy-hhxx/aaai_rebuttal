# sudoku_0.py
"""
Enhanced Sudoku generator with optional diagonal and anti-knight constraints
plus cage sums. Guarantees unique solution using Z3.

Exposed operators:
    pick_one
    rule_phrase_gen
    cage_phrase_gen
    extra_rule_phrase
    generate_sudoku
"""

import random, time
from typing import Sequence, Any, Tuple, List, Dict
from copy import deepcopy
from z3 import Int, Distinct, And, Solver, Sum, Or, sat

# ---------------- Utilities ----------------
def pick_one(seq: Sequence[Any]) -> Any:
    return random.choice(seq)

# ---------------- Phrase helpers ----------------
def rule_phrase_gen(blank: str) -> str:
    starts  = ["Complete", "Fill", "Solve"]
    gridw   = ["grid", "board", "table"]
    subw    = ["sub-grid", "box", "region"]
    return f"{pick_one(starts)} the {pick_one(gridw)} so each row, column, and every 3×3 {pick_one(subw)} contains all digits 1-9 exactly once. Empty cells are marked '{blank}'."

def extra_rule_phrase(diag: bool, knight: bool) -> str:
    extras = []
    if diag:
        extras.append("both main diagonals must also contain the digits 1-9 without repeats")
    if knight:
        extras.append("no two identical digits may be a chess knight's move apart (Anti-Knight rule)")
    return (" Additionally, " + " and ".join(extras) + ".") if extras else ""

def _cell_str(r: int, c: int) -> str:
    return f"({r+1},{c+1})"

def cage_phrase_gen(cages: List[Dict[str, Any]], blank: str) -> str:
    return '\n- '.join(
        [f"Cage {i+1}: cells " +
         ', '.join(_cell_str(r, c) for r, c in cg['cells']) +
         f" sum to {cg['sum']}."
         for i, cg in enumerate(cages)]
    )

# ---------------- Core generation ----------------
SIZE = 9
SUB  = 3
DIGS = list(range(1, SIZE+1))
KNIGHT_OFF = [(-2,-1), (-2,1), (-1,-2), (-1,2),
              (1,-2),  (1,2),  (2,-1),  (2,1)]

def _place_ok(board, r, c, v, diag=False, knight=False):
    if v in board[r] or any(board[i][c] == v for i in range(SIZE)):
        return False
    sr, sc = (r//SUB)*SUB, (c//SUB)*SUB
    if any(board[rr][cc] == v for rr in range(sr, sr+SUB) for cc in range(sc, sc+SUB)):
        return False
    if diag:
        if r == c and any(board[i][i] == v for i in range(SIZE)):
            return False
        if r + c == SIZE-1 and any(board[i][SIZE-1-i] == v for i in range(SIZE)):
            return False
    if knight:
        for dr, dc in KNIGHT_OFF:
            nr, nc = r+dr, c+dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE and board[nr][nc] == v:
                return False
    return True

def _generate_full(diag=False, knight=False):
    board = [[0]*SIZE for _ in range(SIZE)]
    def bt(idx=0):
        if idx == SIZE*SIZE:
            return True
        r, c = divmod(idx, SIZE)
        nums = DIGS[:]
        random.shuffle(nums)
        for v in nums:
            if _place_ok(board, r, c, v, diag, knight):
                board[r][c] = v
                if bt(idx+1):
                    return True
                board[r][c] = 0
        return False
    bt()
    return board

def _build_cages(full, num, size_range):
    cells = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    random.shuffle(cells)
    cages, used = [], set()
    for _ in range(num):
        free = [cell for cell in cells if cell not in used]
        if len(free) < size_range[0]:
            break
        k = random.randint(size_range[0], size_range[1])
        chosen = random.sample(free, k)
        used.update(chosen)
        cages.append({"cells": chosen, "sum": sum(full[r][c] for r, c in chosen)})
    return cages

def _dig_board(full, clues):
    puzzle = deepcopy(full)
    coords = [(r,c) for r in range(SIZE) for c in range(SIZE)]
    random.shuffle(coords)
    for r, c in coords:
        if sum(1 for row in puzzle for x in row if x) <= clues:
            break
        puzzle[r][c] = 0
    givens = [(r,c,puzzle[r][c]) for r in range(SIZE) for c in range(SIZE) if puzzle[r][c]]
    return puzzle, givens

def _unique_z3(givens, cages, diag, knight, timeout=10000):
    X = [[Int(f"x_{r}_{c}") for c in range(SIZE)] for r in range(SIZE)]
    s = Solver()
    s.set("timeout", timeout)

    # domain
    for r in range(SIZE):
        for c in range(SIZE):
            s.add(And(1 <= X[r][c], X[r][c] <= 9))

    # basic
    for r in range(SIZE):
        s.add(Distinct(X[r]))
    for c in range(SIZE):
        s.add(Distinct([X[r][c] for r in range(SIZE)]))
    for sr in range(0,SIZE,SUB):
        for sc in range(0,SIZE,SUB):
            s.add(Distinct([X[r][c] for r in range(sr,sr+SUB) for c in range(sc,sc+SUB)]))

    if diag:
        s.add(Distinct([X[i][i] for i in range(SIZE)]))
        s.add(Distinct([X[i][SIZE-1-i] for i in range(SIZE)]))

    if knight:
        for r in range(SIZE):
            for c in range(SIZE):
                for dr, dc in KNIGHT_OFF:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < SIZE and 0 <= nc < SIZE:
                        s.add(X[r][c] != X[nr][nc])

    for r,c,v in givens:
        s.add(X[r][c] == v)

    for cg in cages:
        s.add(Sum([X[r][c] for r,c in cg['cells']]) == cg['sum'])

    if s.check() != sat:
        return False, ()
    m = s.model()
    sol = [[m.evaluate(X[r][c]).as_long() for c in range(SIZE)] for r in range(SIZE)]
    s.add(Or([X[r][c] != sol[r][c] for r in range(SIZE) for c in range(SIZE)]))
    unique = s.check() != sat
    return unique, tuple(tuple(row) for row in sol)

def generate_sudoku(clue_num: int,
                    blank_char: str = 'X',
                    cage_num: int = 4,
                    cage_size_range: Tuple[int,int]=(2,4),
                    diag_flag: bool=False,
                    antiknight_flag: bool=False) -> Dict[str, Any]:
    """
    Produce a Sudoku puzzle with optional Diagonal and Anti-Knight rules plus cages.
    """
    start = time.time()
    while True:
        full = _generate_full(diag_flag, antiknight_flag)
        cages = _build_cages(full, cage_num, cage_size_range)
        puzzle, givens = _dig_board(full, clue_num)

        uniq, sol = _unique_z3(givens, cages, diag_flag, antiknight_flag)
        if uniq:
            rows = [''.join(str(v) if v else blank_char for v in row) for row in puzzle]
            return {
                "puzzle_rows": rows,
                "solution": sol,
                "cages": cages,
                "diag": diag_flag,
                "knight": antiknight_flag
            }
        if time.time() - start > 15:
            raise TimeoutError("Generation timeout")

# quick self-test
if __name__ == "__main__":
    d = generate_sudoku(25, 'X', 5, (2,3), True, True)
    print('\n'.join(d['puzzle_rows']))
    print(cage_phrase_gen(d['cages'], 'X'))
    print("diag:", d['diag'], "knight:", d['knight'])