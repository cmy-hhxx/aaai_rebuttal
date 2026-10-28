import random, math
from itertools import product
from typing import Dict
import z3
from z3 import Int, Solver, And, Or, Distinct, Sum, If, set_param

set_param('timeout', 1500)  # 1.5 s per call

PRIMES = [
     2, 3, 5, 7,11,13,17,19,23,29,31,37,41,43,47,
    53,59,61,67,71,73,79,83,89,97,101,103,107,109,113
]

def generate_grid() -> Dict[str, object]:
    while True:
        res = _try_once()
        if res:
            return res

def _try_once(force_n=None):
    n = force_n or random.randint(4,5)
    prime_set = random.sample(PRIMES, random.randint(n+3, 11))
    corners_even = [x for x in range(4,120,2) if x not in prime_set]
    corner_values = random.sample(corners_even,4)

    unique_scope = random.choice(['row','col'])
    mod_M, mod_a, mod_b = random.choice([3,4,5]), random.randint(1,2), random.randint(1,2)
    K = random.randint(0, mod_M-1)

    prime_sorted = sorted(prime_set)
    high_threshold = prime_sorted[max(math.ceil(len(prime_sorted)*0.65), n-1)]
    high_req = max(2, n//3)  # >=2

    row_parity=[random.randint(0,1) for _ in range(n)]
    if len(set(row_parity))==1:
        row_parity[random.randrange(n)] ^=1
    anti_diag_parity=random.randint(0,1)

    X=[[Int(f"x{r}_{c}") for c in range(n)] for r in range(n)]
    s=Solver()
    corners=[(0,0),(0,n-1),(n-1,0),(n-1,n-1)]
    for (r,c),v in zip(corners,corner_values):
        s.add(X[r][c]==v)
    for r,c in product(range(n),range(n)):
        if (r,c) in corners:continue
        s.add(Or([X[r][c]==p for p in prime_set]))
    if unique_scope=='row':
        for r in range(n): s.add(Distinct(X[r]))
    else:
        for c in range(n): s.add(Distinct([X[r][c] for r in range(n)]))
    for r,c in product(range(n),range(n)):
        if (r,c) in corners:continue
        s.add((mod_a*(r+1)+mod_b*(c+1)+X[r][c])%mod_M==K)
    for c in range(n):
        s.add(Sum([If(X[r][c]>high_threshold,1,0) for r in range(n)])>=high_req)
    diag_sym=Sum([X[i][i] for i in range(n)])
    s.add((Sum([X[i][n-1-i] for i in range(n)])%2)==anti_diag_parity)
    row_syms=[Sum(X[r]) for r in range(n)]
    col_syms=[Sum([X[r][c] for r in range(n)]) for c in range(n)]
    for r in range(n):
        s.add(row_syms[r]%2==row_parity[r])

    if s.check()!=z3.sat: return None
    m=s.model()
    grid=[[m.evaluate(X[r][c]).as_long() for c in range(n)] for r in range(n)]
    row_sums=[m.evaluate(row_syms[r]).as_long() for r in range(n)]
    col_sums=[m.evaluate(col_syms[c]).as_long() for c in range(n)]
    diag_val=m.evaluate(diag_sym).as_long()
    s.add(Or([X[r][c]!=m[X[r][c]] for r in range(n) for c in range(n)]))
    if s.check()==z3.sat: return None

    return {
        'n':n,'prime_set':prime_set,'grid':grid,
        'row_sums':row_sums,'col_sums':col_sums,
        'mod_a':mod_a,'mod_b':mod_b,'mod_M':mod_M,'K':K,
        'unique_scope':unique_scope,
        'corner_values':corner_values,
        'diag_sum':diag_val,
        'row_parity':row_parity,
        'high_threshold':high_threshold,
        'anti_diag_parity':anti_diag_parity,
        'high_req':high_req
    }