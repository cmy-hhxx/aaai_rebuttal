from typing import List, Tuple

# -------------------------------
# Rotating Grille Cipher (4x4)
# Template (original orientation):
# ▮ ▮ ▮ ▮
# ▮ ▮ ▯ ▯
# ▮ ▮ ▮ ▯
# ▯ ▮ ▮ ▮
# White holes (▯) coordinates (row, col) in 0-based indexing:
# (1,2), (1,3), (2,3), (3,0)
# -------------------------------

_HOLES_0: List[Tuple[int, int]] = [(1, 2), (1, 3), (2, 3), (3, 0)]
_N = 4
_BLOCK = 16

def _rotate_ccw(pos: Tuple[int, int], n: int = _N) -> Tuple[int, int]:
    """Rotate a coordinate (r,c) CCW 90 degrees in an n x n grid."""
    r, c = pos
    return (n - 1 - c, r)

def _holes_by_rotation() -> List[List[Tuple[int, int]]]:
    """Return holes for 4 rotations (0,90,180,270 CCW), in fill/read order."""
    holes_all = []
    cur = _HOLES_0
    for _ in range(4):
        holes_all.append(cur)
        cur = [_rotate_ccw(p) for p in cur]
    return holes_all

_HOLES_4 = _holes_by_rotation()

def _chunk(s: str, size: int) -> List[str]:
    return [s[i:i + size] for i in range(0, len(s), size)] if s else [""]

def encrypt_grille(plaintext: str, filler: str = "#") -> str:
    """
    Encrypt using 4x4 rotating grille.
    Split plaintext into 16-char blocks; pad each block with filler to 16.
    Fill 4 holes per rotation for 4 CCW rotations, then read grid row-wise.
    """
    blocks = _chunk(plaintext, _BLOCK)
    out_blocks: List[str] = []

    for b in blocks:
        b_pad = (b + filler * _BLOCK)[:_BLOCK]
        grid = [["" for _ in range(_N)] for _ in range(_N)]
        idx = 0
        for rot in range(4):
            for (r, c) in _HOLES_4[rot]:
                grid[r][c] = b_pad[idx]
                idx += 1
        out_blocks.append("".join("".join(row) for row in grid))

    return "".join(out_blocks)

def decrypt_grille(ciphertext: str, filler: str = "#") -> str:
    """
    Decrypt using 4x4 rotating grille.
    Split ciphertext into 16-char blocks (pad with filler if last block shorter).
    Write into grid row-wise, then read holes per rotation to reconstruct plaintext.
    Filler characters are preserved.
    """
    blocks = _chunk(ciphertext, _BLOCK)
    out_blocks: List[str] = []

    for b in blocks:
        b_pad = (b + filler * _BLOCK)[:_BLOCK]
        grid = [[b_pad[r * _N + c] for c in range(_N)] for r in range(_N)]
        chars: List[str] = []
        for rot in range(4):
            for (r, c) in _HOLES_4[rot]:
                chars.append(grid[r][c])
        out_blocks.append("".join(chars))

    return "".join(out_blocks)

if __name__ == "__main__":
    p1 = "GZHYAWHHUASPLMPWMAUMSRHANOSXPWDBRIN"
    print("enc:", encrypt_grille(p1, "#"))

    c2 = "SECZAFVWISMPVBNKNDCOUYEFGOHLYLLD######WT###B####"
    print("dec:", decrypt_grille(c2, "#"))