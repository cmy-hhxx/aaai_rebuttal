# campsite_0.py
# Helper functions for the generalized Tents and Trees generator.

def neighbors4(i, j, r, c):
    """
    Return in-bounds 4-neighborhood coordinates of (i, j)
    using up/down/left/right moves.
    """
    res = []
    cand = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]
    for ni, nj in cand:
        if 0 <= ni < r and 0 <= nj < c:
            res.append((ni, nj))
    return res

def neighbors8(i, j, r, c):
    """
    Return in-bounds 8-neighborhood coordinates of (i, j)
    including diagonals.
    """
    res = []
    cand = [
        (i-1, j-1), (i-1, j), (i-1, j+1),
        (i,   j-1),             (i,   j+1),
        (i+1, j-1), (i+1, j), (i+1, j+1),
    ]
    for ni, nj in cand:
        if 0 <= ni < r and 0 <= nj < c:
            res.append((ni, nj))
    return res

def neighbors_diag(i, j, r, c):
    """
    Return in-bounds diagonal neighbors only of (i, j).
    """
    res = []
    cand = [(i-1, j-1), (i-1, j+1), (i+1, j-1), (i+1, j+1)]
    for ni, nj in cand:
        if 0 <= ni < r and 0 <= nj < c:
            res.append((ni, nj))
    return res

def example_grid_str():
    """
    Return a concise example of the required 2D list answer format
    using single-quoted cell values, exactly matching Python's str(list) style.
    """
    return "[['T', 'X'], ['X', 'C']]"