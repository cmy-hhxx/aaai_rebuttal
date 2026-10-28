# minesweeper_3.py  – updated: ≥2 slice clues & clearer notes
from itertools import product
import random, time
from typing import Tuple, List
from z3 import Solver, Bool, Sum, If, Or, sat

__all__ = ['generate_puzzle', 'grid_to_text']

MAX_SHOW_MINES = 8
MAX_SHOW_SAFE  = 8
GLOBAL_TIME    = 100
SOLVER_TIMEOUT = 50000
MAX_TRIES      = 5000

OFFSETS = {
    'face':  [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)],
    'moore': [(x,y,z) for x,y,z in product((-1,0,1), repeat=3) if (x,y,z)!=(0,0,0)]
}
NEIGH_TXT = {'face':'six face-adjacent neighbours',
             'moore':'all twenty-six surrounding cells'}

def inside(x:int,n:int)->bool: return 0<=x<n
def neigh(p, n, mode):
    l,r,c=p
    for dl,dr,dz in OFFSETS[mode]:
        nl,nr,nc=l+dl,r+dr,c+dz
        if inside(nl,n) and inside(nr,n) and inside(nc,n):
            yield (nl,nr,nc)

def compute_numbers(n,mines,mode):
    g=[[['*']*n for _ in range(n)] for _ in range(n)]
    for l,r,c in product(range(n),repeat=3):
        if (l,r,c) in mines: continue
        g[l][r][c]=sum(q in mines for q in neigh((l,r,c),n,mode))
    return g

def hide_numbers(g, keep=0.85):
    n=len(g)
    numeric=[(l,r,c) for l,r,c in product(range(n),repeat=3)
             if isinstance(g[l][r][c],int)]
    for l,r,c in numeric:
        if random.random()>keep:
            g[l][r][c]='*'
    if all(g[l][r][c]=='*' for l,r,c in numeric):
        l,r,c=random.choice(numeric); g[l][r][c]=0

def slice_cells(n,t,l,idx=None):
    if t=='layer':  return [(l,r,c) for r,c in product(range(n),repeat=2)]
    if t=='row':    return [(l,idx,c) for c in range(n)]
    if t=='column': return [(l,r,idx) for r in range(n)]

def slice_txt(t,l,idx,cnt):
    word='mine' if cnt==1 else 'mines'
    if t=='layer':  return f'Layer {l} has exactly {cnt} {word}'
    if t=='row':    return f'Row {idx} of Layer {l} has exactly {cnt} {word}'
    if t=='column': return f'Column {idx} of Layer {l} has exactly {cnt} {word}'

def build_solver(g,n,mode,slices):
    v={p:Bool(f"m_{p[0]}_{p[1]}_{p[2]}") for p in product(range(n),repeat=3)}
    s=Solver(); s.set('timeout',SOLVER_TIMEOUT)
    for l,r,c in product(range(n),repeat=3):
        val=g[l][r][c]
        if isinstance(val,int):
            s.add(Sum([If(v[q],1,0) for q in neigh((l,r,c),n,mode)])==val)
    for t,l,idx,c in slices:
        s.add(Sum([If(v[p],1,0) for p in slice_cells(n,t,l,idx)])==c)
    return s,v

def trim(lst,limit): 
    return sorted(random.sample(lst,limit)) if len(lst)>limit else sorted(lst)

def select_mode(): return 'face' if random.random()<0.7 else 'moore'

def generate_puzzle(n:int):
    start=time.time()
    attempts=0
    while time.time()-start<GLOBAL_TIME and attempts<MAX_TRIES:
        attempts+=1
        mode=select_mode()
        neigh=NEIGH_TXT[mode]
        mines=set(random.sample(list(product(range(n),repeat=3)),random.randint(3,6)))
        grid=compute_numbers(n,mines,mode)
        hide_numbers(grid)

        # create 2–3 slice clues with ≤1 layer clue and ≥1 row/col clue
        slices=[]; desc=[]
        layer_used=False; rowcol_used=False
        while len(slices)<3:
            t=random.choice(['layer','row','column'])
            if t=='layer' and layer_used: continue
            if t in ('row','column'): rowcol_used=True
            l=random.randint(0,n-1)
            idx=None
            if t!='layer': idx=random.randint(0,n-1)
            if any((t,l,idx)==(s[0],s[1],s[2]) for s in slices): continue
            cells=slice_cells(n,t,l,idx)
            cnt=sum(p in mines for p in cells)
            if cnt in (0,len(cells)): continue
            slices.append((t,l,idx,cnt))
            desc.append(slice_txt(t,l,idx,cnt))
            if t=='layer': layer_used=True
            if len(slices)==2 and rowcol_used: break  # ensure at least 2 clues

        if not rowcol_used: continue  # enforce variety

        s,vm=build_solver(grid,n,mode,slices)
        if s.check()!=sat: continue
        m=s.model()
        s.push(); s.add(Or([v!=m.eval(v,model_completion=True) for v in vm.values()]))
        if s.check()==sat:
            s.pop(); continue
        s.pop()

        fm=[p for p,vb in vm.items() if m.eval(vb,model_completion=True)]
        fs=[p for p,vb in vm.items() if not m.eval(vb,model_completion=True)]
        if not fm or not fs: continue

        disp_m=trim(fm,MAX_SHOW_MINES)
        disp_s=trim(fs,MAX_SHOW_SAFE)
        note=[]
        if len(fm)>MAX_SHOW_MINES: note.append('[Only part of the forced-mine list is shown]')
        if len(fs)>MAX_SHOW_SAFE:  note.append('[Only part of the forced-safe list is shown]')

        return grid, disp_m, disp_s, neigh, '; '.join(desc), ' '.join(note)

    raise RuntimeError('Generation timeout')

def grid_to_text(g)->str:
    n=len(g)
    return ' // '.join(
        f'Layer {l}: ' + ' | '.join(' '.join(str(g[l][r][c]) for c in range(n)) for r in range(n))
        for l in range(n)
    )