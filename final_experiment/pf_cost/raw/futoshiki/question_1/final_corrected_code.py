# pf_futoshiki_0.py
from typing import List, Any

def to_grid(n: int, rows: List[str], cols: List[str], cell: Any, model: Any):
    grid = []
    for r in rows:
        row = []
        for c in cols:
            v = model.evaluate(cell[(r, c)], model_completion=True)
            row.append(int(str(v)))
        grid.append(row)
    return grid

def format_grid(grid):
    return "[" + ",".join(["[" + ", ".join(str(x) for x in row) + "]" for row in grid]) + "]"