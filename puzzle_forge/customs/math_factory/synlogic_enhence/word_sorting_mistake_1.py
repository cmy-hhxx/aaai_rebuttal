# word_sorting_mistake_0.py
"""
改进版：保证合法性验证 + 唯一答案
"""

import random, string
from typing import List, Tuple, Dict

VOWELS=set('aeiou')

# ------------ 基础 ------------ #
def rand_word():
    return ''.join(random.choices(string.ascii_lowercase,k=random.randint(4,9)))

def make_words(n):
    s=set()
    while len(s)<n: s.add(rand_word())
    return list(s)

def get_attributes(words):
    return {w:('even' if len(w)%2==0 else 'odd',
               'vowel' if any(c in VOWELS for c in w) else 'novowel')
            for w in words}

# ------------ 操作实现 ------------ #
def op_min_front(st,lx):
    for i,w in enumerate(st):
        if w!=lx[i]:
            tgt=min(st[i:])
            ns=st[:]; ns.remove(tgt); ns.insert(i,tgt)
            return ns,f'将余下单词里最小的 {tgt} 放到位置 {i+1}'
    return st,None

def op_group_parity(st,attrs,tgt):
    blk=[w for w in st if attrs[w][0]==tgt]
    if not blk: return st,None
    ns=blk+[w for w in st if w not in blk]
    if ns==st: return st,None
    return ns,f'把所有长度为{tgt}的单词整体提前'

def op_vowel_sort(st,attrs):
    idx=[i for i,w in enumerate(st) if attrs[w][1]=='vowel']
    if len(idx)<2: return st,None
    l,r=idx[0],idx[-1]
    ns=st[:l]+sorted(st[l:r+1])+st[r+1:]
    return ns,f'将包含元音的子序列(位置 {l+1}-{r+1})按字典序排序'

def op_rotate(st):
    if len(st)<4: return st,None
    l=random.randint(0,len(st)-3)
    r=random.randint(l+2,len(st)-1)
    k=random.randint(1,r-l)
    seg=st[l:r+1]
    ns=st[:l]+seg[-k:]+seg[:-k]+st[r+1:]
    return ns,f'将位置 {l+1}-{r+1} 的子列表循环右移 {k} 位'

def op_interleave(st,attrs):
    if len(st)<6: return st,None
    k=min(len(st),random.randint(6,8))
    part=st[:k]
    even=[w for w in part if attrs[w][0]=='even']
    odd=[w for w in part if attrs[w][0]=='odd']
    merged=[]
    for e,o in zip(even,odd): merged.extend([e,o])
    merged+=even[len(odd):]+odd[len(even):]
    ns=merged+st[k:]
    return ns,f'将前 {k} 个单词按长度奇偶交替重新排列'

def op_shuffle_three(st):
    if len(st)<3: return st,None
    idx=sorted(random.sample(range(len(st)),3))
    rep=sorted(st[i] for i in idx)
    ns=st[:]
    for p,v in zip(idx,rep): ns[p]=v
    return ns,f'取出位置 {idx[0]+1},{idx[1]+1},{idx[2]+1} 的单词按字典序重排'

OP_FUNCS=[op_min_front,op_vowel_sort,op_rotate,op_interleave,op_shuffle_three]

# ------------ 错误生成 ------------ #
def err_swap_adj(st):
    ns=st[:]; i=random.randint(0,len(st)-2)
    ns[i],ns[i+1]=ns[i+1],ns[i]
    return ns,'（此处出错）我误交换了相邻单词'

def err_reverse_seg(st):
    if len(st)<4: return err_swap_adj(st)
    l=random.randint(0,len(st)-3); r=random.randint(l+2,len(st)-1)
    ns=st[:l]+list(reversed(st[l:r+1]))+st[r+1:]
    return ns,f'（此处出错）把位置 {l+1}-{r+1} 的单词倒序'

ERRORS=[err_swap_adj,err_reverse_seg]

# ------------ 合法性检查 ------------ #
def is_sorted(lst): return lst==sorted(lst)

def is_legal(prev,next_state,attrs,lx):
    """粗略合法性：若 prev 已全序则 next==prev"""
    if is_sorted(prev): return next_state==prev
    return prev!=next_state

# ------------ 主生成 ------------ #
def gen_sort_puzzle(n:int,err_p=0.7,retry=120):
    for _ in range(retry):
        words=make_words(n)
        attrs=get_attributes(words)
        lx=sorted(words)

        total=random.randint(8,10)
        planned_err=0
        if random.random()<err_p:
            planned_err=random.randint(5,total-1)

        logs=[f'你需要判断以下排序思考链第一次出现错误的步骤（若全过程正确写 No）。',
              '初始单词列表(未排序): '+' '.join(words)]
        states=[]
        cur=words[:]
        # 前3步保证合法且不同模板
        used=set()
        for step in range(1,total+1):
            if step==planned_err:
                cur,desc=random.choice(ERRORS)(cur)
            else:
                if step<=3:
                    func=random.choice([f for f in OP_FUNCS if f not in used])
                    used.add(func)
                else:
                    func=random.choice(OP_FUNCS)
                if func==op_min_front:
                    cur,desc=func(cur,lx)
                elif func==op_group_parity:
                    tgt=random.choice(['even','odd'])
                    cur,desc=func(cur,attrs,tgt)
                else:
                    cur,desc=func(cur,attrs) if func in (op_vowel_sort,op_interleave) else func(cur)
                # 保证改动
                if cur==states[-1] if states else False:
                    continue
            states.append(cur[:])
            logs.append(f'思考 {step}: {desc}\n当前结果: '+' '.join(cur))

        # 无错时最终必须全序
        if planned_err==0 and not is_sorted(states[-1]): continue
        # 合法性/唯一性
        legal=True
        for idx,(p,nx) in enumerate(zip([words]+states[:-1],states),1):
            if idx==planned_err: continue
            if not is_legal(p,nx,attrs,lx): legal=False;break
        if not legal: continue
        # 检查唯一
        if planned_err>0 and is_sorted(states[-1]): continue

        ans='No' if planned_err==0 else str(planned_err)
        return {'problem':'\n'.join(logs),'answer':ans}
    raise RuntimeError('generate_fail')

# 占位函数
def function_1(*a,**k): ...
def function_2(*a,**k): ...