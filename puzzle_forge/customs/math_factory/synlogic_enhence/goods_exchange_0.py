# goods_exchange_0.py
# -*- coding: utf-8 -*-
"""
Robust generator & verifier for the item-exchange puzzle.
"""

from typing import Dict, List, Tuple, Set   # <-- moved to top before any usage
import random
import re

# --------------------  Data pools  --------------------
COLORS = [
    '红色','蓝色','黑色','白色','灰色','银色','金色','紫色','粉色','米色',
    '橙色','黄色','绿色','深蓝色','浅灰色','玫红色','酒红色','藏青色','草绿色',
    '墨绿色','古铜色','棕色'
]
OBJECTS = [
    '钱包','电脑','明信片','耳机','戒指','眼镜','手绢','地图',
    '纪念币','水壶','项链','小刀','发夹','口哨'
]
SURNAMES = ['赵','钱','孙','李','周','吴','郑','王','冯','陈','蒋','沈','韩',
            '杨','朱','秦','尤','许','何','吕','施','张','孔','曹','华']
GIVEN = ['凯','亮','晨','强','磊','杰','军','勇','辉','明','峰','洋','超',
         '浩','鹏','林','刚','伟','东','航','涛','龙','翔','旭','轩','城',
         '阳','博','宁','然','琪','欣']

# --------------------  Templates  --------------------
LIKE_PHRS  = ['很喜欢', '十分想要', '非常钟爱']
SEEK_PHRS  = ['正在寻找', '四处寻找', '苦苦寻找']
SWAP_PHRS  = ['交换了他们的物品', '互换了手中的物品']
OWNER_SWAP = ['交换了各自的物品', '完成了交换']
GIFT_PHRS  = [
    '{p1}把自己的{item1}赠与{p2}，并收下了{p2}的{item2}',
    '{p1}用{item1}与{p2}的{item2}交换'
]
COLOUR_SWAP = '唯一持有{c1}物品的玩家与唯一持有{c2}物品的玩家互换了物品'

INTRO_TMPL  = '{n} 名玩家 {plist} 正在参与一场烧脑的物品交换游戏。'
ITEM_TMPL   = '可流转物品有[{ilist}]。'
ALLOC_TMPL  = '最初物品归属：{alloc}。'
EX_INTRO_TMPL = '之后，他们依次进行了 {k} 步操作：{exch}。'

# --------------------  Helper functions  --------------------
def _rand_names(n:int)->List[str]:
    names=set()
    while len(names)<n:
        names.add(random.choice(SURNAMES)+random.choice(GIVEN)+random.choice(GIVEN))
    return list(names)

def _rand_items(n:int)->List[str]:
    pool=[f'{c}{o}' for c in COLORS for o in OBJECTS]
    random.shuffle(pool)
    return pool[:n]

def _swap(mp:Dict[str,str],a:str,b:str):
    mp[a], mp[b] = mp[b], mp[a]

def _owner_item(mp:Dict[str,str], item:str)->str:
    return next(p for p,v in mp.items() if v==item)

def _unique_colour_map(mp:Dict[str,str])->Dict[str,str]:
    d={}
    for p,it in mp.items():
        for col in COLORS:
            if it.startswith(col):
                d.setdefault(col,[]).append(p)
                break
    return {c: lst[0] for c,lst in d.items() if len(lst)==1}

def _owner_color(mp:Dict[str,str], color:str)->str:
    return _unique_colour_map(mp)[color]

# backward aliases
owner_of_unique_colour=_owner_color
owner_of_unique_color=_owner_color

# --------------------  Action Generator  --------------------
def _generate_actions(players:List[str], mp:Dict[str,str], steps:int)->List[str]:
    used_pairs:Set[Tuple[str,str]] = set()
    used_colors:Set[str] = set()
    narratives=[]
    real_cnt=0
    useless_cnt=0
    while len(narratives)<steps:
        remaining=steps-len(narratives)
        need_real=max(int(steps*0.7)-real_cnt,0)
        must_real=remaining<=need_real
        act=random.choice([3,4,5,6] if must_real else [1,2,3,4,5,6])

        def record(a,b):
            pair=tuple(sorted((a,b)))
            if pair in used_pairs: return False
            used_pairs.add(pair); return True

        if act==1 and useless_cnt<1:
            p=random.choice(players)
            narratives.append(f'{p}{random.choice(LIKE_PHRS)}{mp[p]}')
            useless_cnt+=1
        elif act==2 and useless_cnt<1:
            p=random.choice(players); it=random.choice(list(mp.values()))
            narratives.append(f'{p}{random.choice(SEEK_PHRS)}{it}，但是没有成功')
            useless_cnt+=1
        elif act==3:
            a,b=random.sample(players,2)
            if not record(a,b): continue
            _swap(mp,a,b); real_cnt+=1
            narratives.append(f'{a}和{b}{random.choice(SWAP_PHRS)}')
        elif act==4:
            it1,it2=random.sample(list(mp.values()),2)
            a,b=_owner_item(mp,it1),_owner_item(mp,it2)
            if a==b or not record(a,b): continue
            _swap(mp,a,b); real_cnt+=1
            narratives.append(f'持有{it1}的玩家与持有{it2}的玩家{random.choice(OWNER_SWAP)}')
        elif act==5:
            a,b=random.sample(players,2)
            if not record(a,b): continue
            it1,it2=mp[a],mp[b]
            _swap(mp,a,b); real_cnt+=1
            narratives.append(random.choice(GIFT_PHRS).format(p1=a,item1=it1,p2=b,item2=it2))
        elif act==6:
            cmap=_unique_colour_map(mp)
            avail=[c for c in cmap if c not in used_colors]
            if len(avail)<2: continue
            c1,c2=random.sample(avail,2)
            a,b=cmap[c1],cmap[c2]
            if not record(a,b): continue
            _swap(mp,a,b); real_cnt+=1
            used_colors.update({c1,c2})
            narratives.append(COLOUR_SWAP.format(c1=c1,c2=c2))
    return narratives

# alias
generate_actions=_generate_actions

# --------------------  Parser  --------------------
def _replay(narratives:List[str], mp:Dict[str,str]):
    for s in narratives:
        m=re.match(r'唯一持有(.+?)物品的玩家与唯一持有(.+?)物品的玩家互换了物品',s)
        if m:
            try:_swap(mp,_owner_color(mp,m.group(1)),_owner_color(mp,m.group(2)))
            except:pass
            continue
        m=re.match(r'持有(.+?)的玩家与持有(.+?)的玩家(?:交换了各自的物品|完成了交换)',s)
        if m:
            _swap(mp,_owner_item(mp,m.group(1)),_owner_item(mp,m.group(2)));continue
        m=re.match(r'(.+?)和(.+?)(?:交换了他们的物品|互换了手中的物品)',s)
        if m:
            _swap(mp,m.group(1),m.group(2));continue
        m=re.match(r'(.+)把自己的(.+)赠与(.+)，并收下了(.+)的(.+)',s) \
          or re.match(r'(.+)用(.+)与(.+)的(.+)交换',s)
        if m and mp.get(m.group(1))==m.group(2) and mp.get(m.group(3))==m.group(4):
            _swap(mp,m.group(1),m.group(3))

# --------------------  Main --------------------
def generate_game(player_num:int,exchange_num:int,max_retry:int=400)->Dict[str,object]:
    for _ in range(max_retry):
        players=_rand_names(player_num)
        items=_rand_items(player_num)
        init_mp=dict(zip(players,items))
        mp=init_mp.copy()

        narratives=_generate_actions(players,mp,exchange_num)

        alloc='；'.join(f'{p}拥有{init_mp[p]}' for p in players)
        story='\\n'.join([
            INTRO_TMPL.format(n=player_num, plist="、".join(players)),
            ITEM_TMPL.format(ilist="、".join(items)),
            ALLOC_TMPL.format(alloc=alloc),
            EX_INTRO_TMPL.format(k=exchange_num, exch="；".join(narratives))
        ])

        final=tuple((p,mp[p]) for p in players)
        check=init_mp.copy(); _replay(narratives,check)
        if check==dict(final):
            return {'story':story,'final_result':final}
    raise RuntimeError('Unable to generate a valid puzzle within retry limit.')