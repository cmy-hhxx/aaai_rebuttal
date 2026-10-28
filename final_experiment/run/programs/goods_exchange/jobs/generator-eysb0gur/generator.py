import sys, json, random, itertools, math
from typing import List, Dict, Tuple, Any, Optional

# -----------------------------
# Utilities
# -----------------------------

def eprint(*args):
    print(*args, file=sys.stderr)

def ensure(cond: bool, msg: str):
    if not cond:
        raise ValueError(msg)

def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

# -----------------------------
# Core model: swap-based exchange game
# -----------------------------

class ExchangeGame:
    """
    Players each hold exactly one item. Operations (public rules) transform holdings.
    We generate instances where the final mapping is uniquely determined by the operations,
    and we can compute it deterministically.
    """

    def __init__(self, rng: random.Random, output_language: str = "zh"):
        self.rng = rng
        self.lang = output_language or "zh"

    # ---- Name / item pools (Chinese-friendly, but generated) ----

    def gen_players(self, n: int) -> List[str]:
        # Avoid exactly repeating seed names; generate from surname+given pool.
        surnames = ["赵","钱","孙","李","周","吴","郑","王","冯","陈","褚","卫","蒋","沈","韩","杨","朱","秦","尤","许","何","吕","施","张","孔","曹","严","华","金","魏","陶","姜","戚","谢","邹","喻","柏","水","窦","章","云","苏","潘","葛","奚","范","彭","郎","鲁","韦","昌","马","苗","凤","花","方","俞","任","袁","柳","鲍","史","唐","费","廉","岑","薛","雷","贺","倪","汤","滕","殷","罗","毕","郝","邬","安","常","乐","于","时","傅","皮","卞","齐","康","伍","余","元","卜","顾","孟","平","黄","和","穆","萧","尹"]
        given1 = ["一","二","三","四","五","六","七","八","九","十","子","明","亮","强","勇","华","峰","磊","洋","军","刚","晨","宁","欣","博","瑞","浩","宇","琪","雪","婷","琳","哲","远","昊","彤","凯","飞","涛","瀚","然","昱","泽"]
        given2 = ["","伟","杰","鑫","诚","航","乐","阳","辰","清","然","旭","凡","平","文","武","思","涵","雨","星","森","睿","宁","轩","祺","颖","怡","嘉","弘","鸣","越"]
        names = set()
        tries = 0
        while len(names) < n and tries < 10000:
            tries += 1
            s = self.rng.choice(surnames)
            g = self.rng.choice(given1) + self.rng.choice(given2)
            nm = s + g
            names.add(nm)
        ensure(len(names) == n, "无法生成足够不重复的玩家姓名")
        return list(names)

    def gen_items(self, n: int) -> List[str]:
        colors = ["银色","灰色","古铜色","米色","蓝色","草绿色","墨绿色","白色","浅绿色","橙色","玫红色","酒红色","明黄色","深蓝色","黑色","粉色","浅灰色","藏青色","棕色","紫色","天蓝色","青色","金色","青灰色","亮绿色","象牙白","朱红色","土黄色"]
        kinds = ["钱包","电脑","明信片","耳机","戒指","眼镜","手绢","地图","纪念币","水壶","项链","小刀","口哨","发夹","钥匙扣","手表","笔记本"]
        # Create unique combinations; avoid duplicates.
        all_candidates = [c + k for c in colors for k in kinds]
        self.rng.shuffle(all_candidates)
        ensure(len(all_candidates) >= n, "物品候选不足")
        return all_candidates[:n]

    # ---- Operation templates ----

    def op_swap_players(self, p1: str, p2: str) -> Dict[str, Any]:
        return {"type": "swap_players", "p1": p1, "p2": p2}

    def op_swap_items(self, item1: str, item2: str) -> Dict[str, Any]:
        return {"type": "swap_items", "i1": item1, "i2": item2}

    def op_swap_owner_with_player(self, item: str, player: str) -> Dict[str, Any]:
        # Owner of `item` swaps with `player`
        return {"type": "swap_owner_player", "item": item, "player": player}

    def op_give(self, giver: str, receiver: str) -> Dict[str, Any]:
        # giver gives their item to receiver; receiver gives their item to giver (i.e., swap but narrated as gift exchange)
        return {"type": "give_swap", "giver": giver, "receiver": receiver}

    # Flavor-only lines (do not change state)
    def op_flavor_like_item(self, player: str, item: str) -> Dict[str, Any]:
        return {"type": "flavor_like_item", "player": player, "item": item}

    def op_flavor_search_fail(self, player: str, item: str) -> Dict[str, Any]:
        return {"type": "flavor_search_fail", "player": player, "item": item}

    # ---- Apply operations ----

    def apply_ops(self, init_map: Dict[str, str], ops: List[Dict[str, Any]]) -> Dict[str, str]:
        # Maintain both directions for O(1) owner lookup.
        p2i = dict(init_map)
        i2p = {it: pl for pl, it in p2i.items()}
        ensure(len(i2p) == len(p2i), "初始分配存在重复物品")

        def swap_players(a: str, b: str):
            ia, ib = p2i[a], p2i[b]
            p2i[a], p2i[b] = ib, ia
            i2p[ia], i2p[ib] = b, a

        def swap_items(i1: str, i2: str):
            p1, p2 = i2p[i1], i2p[i2]
            swap_players(p1, p2)

        for op in ops:
            t = op["type"]
            if t == "swap_players":
                swap_players(op["p1"], op["p2"])
            elif t == "swap_items":
                swap_items(op["i1"], op["i2"])
            elif t == "swap_owner_player":
                owner = i2p[op["item"]]
                swap_players(owner, op["player"])
            elif t == "give_swap":
                swap_players(op["giver"], op["receiver"])
            elif t in ("flavor_like_item", "flavor_search_fail"):
                # no state change
                pass
            else:
                raise ValueError(f"未知操作类型: {t}")

        return p2i

    # ---- Rendering in Chinese ----

    def render_op(self, op: Dict[str, Any]) -> str:
        t = op["type"]
        if t == "swap_players":
            return f"{op['p1']} 和 {op['p2']} 互相交换他们的物品"
        if t == "swap_items":
            return f"拥有 {op['i1']} 的人和拥有 {op['i2']} 的人交换了他们的物品"
        if t == "swap_owner_player":
            return f"拥有 {op['item']} 的人和 {op['player']} 交换了他们的物品"
        if t == "give_swap":
            return f"{op['giver']} 把自己的物品送给了 {op['receiver']}，{op['receiver']} 也把自己的物品交给了 {op['giver']}"
        if t == "flavor_like_item":
            return f"{op['player']} 很喜欢 {op['item']}"
        if t == "flavor_search_fail":
            return f"{op['player']} 正在寻找 {op['item']}，但是找不到"
        raise ValueError(f"未知操作类型: {t}")

    def render_problem(
        self,
        players: List[str],
        items: List[str],
        init_map: Dict[str, str],
        ops: List[Dict[str, Any]],
        k_ops: int
    ) -> str:
        # Ensure stable order in statement: list players order, and items order, then assignments in that same players order.
        item_list = "、".join(items)
        assigns = "；".join([f"{p} 拥有 {init_map[p]}" for p in players]) + "。"
        ops_lines = "\n".join([self.render_op(op) for op in ops[:k_ops]])

        return (
            f"{len(players)} 名玩家 { '、'.join(players) } 正在玩一个物品交换游戏。"
            f"游戏中的物品有：{item_list}。\n"
            f"游戏开始时，物品的分配如下：{assigns}\n"
            f"玩家们按顺序执行了以下 {k_ops} 次事件（其中有的只是描述，不一定会改变物品归属）：\n"
            f"{ops_lines}\n"
            f"请计算游戏结束时各玩家拥有的物品。请在回答的最后使用 tuple 格式输出结果，"
            f"顺序必须与题面给出的玩家顺序一致。"
            f"例如：(('甲','红色书'),('乙','蓝色表'))"
        )

    # ---- Explanation ----

    def build_explanation(self, players: List[str], init_map: Dict[str, str], ops: List[Dict[str, Any]], final_map: Dict[str, str]) -> str:
        # Provide a short but checkable trace of the *effective* swaps.
        p2i = dict(init_map)
        i2p = {it: pl for pl, it in p2i.items()}
        effective = []
        for idx, op in enumerate(ops, 1):
            before = (op["type"],)
            if op["type"] == "swap_players":
                a, b = op["p1"], op["p2"]
                ia, ib = p2i[a], p2i[b]
                # apply
                p2i[a], p2i[b] = ib, ia
                i2p[ia], i2p[ib] = b, a
                effective.append(f"{idx}. {a}({ia}) ↔ {b}({ib})")
            elif op["type"] == "swap_items":
                i1, i2 = op["i1"], op["i2"]
                p1, p2 = i2p[i1], i2p[i2]
                ia, ib = p2i[p1], p2i[p2]
                p2i[p1], p2i[p2] = ib, ia
                i2p[ia], i2p[ib] = p2, p1
                effective.append(f"{idx}. {p1}({i1}) ↔ {p2}({i2})（按物品定位持有人）")
            elif op["type"] == "swap_owner_player":
                item, player = op["item"], op["player"]
                owner = i2p[item]
                ia, ib = p2i[owner], p2i[player]
                p2i[owner], p2i[player] = ib, ia
                i2p[ia], i2p[ib] = player, owner
                effective.append(f"{idx}. {owner}({item}) ↔ {player}({ib})（按“拥有{item}的人”定位）")
            elif op["type"] == "give_swap":
                g, r = op["giver"], op["receiver"]
                ig, ir = p2i[g], p2i[r]
                p2i[g], p2i[r] = ir, ig
                i2p[ig], i2p[ir] = r, g
                effective.append(f"{idx}. {g}({ig}) ↔ {r}({ir})（互送等价于交换）")
            elif op["type"] in ("flavor_like_item", "flavor_search_fail"):
                # no change
                continue

        # Cross-check
        if p2i != final_map:
            # Should not happen; if it does, show diagnostic.
            return "校验失败：解释用的逐步推演结果与最终答案不一致。"

        # show a compact mapping diff: only a few samples + guarantee rule
        sample_n = min(6, len(players))
        sample_players = players[:sample_n]
        sample_lines = "；".join([f"{p}->{final_map[p]}" for p in sample_players])

        return (
            "把每一步中真正发生的“交换”按顺序执行即可（喜欢/寻找但找不到不会改变归属）。\n"
            "有效交换步骤摘要：\n"
            + "\n".join(effective[:10])
            + ("" if len(effective) <= 10 else f"\n…（共 {len(effective)} 次有效交换）")
            + "\n最终将每位玩家对应到其物品即可。例如前几位为："
            + sample_lines
        )

    # ---- Generator family ----

    def generate_instance(self) -> Tuple[str, Any, str]:
        # Randomize size and operation mix
        n = self.rng.randint(18, 32)
        players = self.gen_players(n)
        items = self.gen_items(n)

        # Initial bijection
        self.rng.shuffle(items)
        init_map = {p: items[i] for i, p in enumerate(players)}

        # Build operations: ensure all referenced items/players exist; include some flavor.
        ops: List[Dict[str, Any]] = []

        # number of events
        m = self.rng.randint(9, 14)

        # Pre-create some swaps to ensure nontriviality
        # We'll create about 60-80% effective swaps, rest flavor.
        for _ in range(m):
            r = self.rng.random()
            if r < 0.18:
                # flavor like an item
                ops.append(self.op_flavor_like_item(self.rng.choice(players), self.rng.choice(items)))
            elif r < 0.30:
                # flavor search fail
                ops.append(self.op_flavor_search_fail(self.rng.choice(players), self.rng.choice(items)))
            elif r < 0.52:
                # swap players
                p1, p2 = self.rng.sample(players, 2)
                ops.append(self.op_swap_players(p1, p2))
            elif r < 0.73:
                # swap items
                i1, i2 = self.rng.sample(items, 2)
                ops.append(self.op_swap_items(i1, i2))
            elif r < 0.90:
                # swap owner of item with some player
                item = self.rng.choice(items)
                player = self.rng.choice(players)
                # avoid degenerate always, try a few times
                for _t in range(5):
                    if player != init_map.get(item, None):
                        break
                    player = self.rng.choice(players)
                ops.append(self.op_swap_owner_with_player(item, player))
            else:
                # give-swap
                g, rcv = self.rng.sample(players, 2)
                ops.append(self.op_give(g, rcv))

        # Compute final
        final_map = self.apply_ops(init_map, ops)

        # Ensure nontrivial change: at least 30% players changed items
        changed = sum(1 for p in players if final_map[p] != init_map[p])
        if changed < max(3, n * 3 // 10):
            # Force additional swaps to make it interesting
            extra = []
            for _ in range(3):
                a, b = self.rng.sample(players, 2)
                extra.append(self.op_swap_players(a, b))
            ops.extend(extra)
            m = len(ops)
            final_map = self.apply_ops(init_map, ops)

        # Build answer as tuple of tuples, in player order
        answer_tuple = tuple((p, final_map[p]) for p in players)

        problem = self.render_problem(players, items, init_map, ops, len(ops))
        explanation = self.build_explanation(players, init_map, ops, final_map)

        # Final sanity checks: bijection preserved
        ensure(len(set(final_map.values())) == n, "最终物品分配不是一一对应")
        ensure(all(p in final_map for p in players), "最终映射缺少玩家")

        return problem, answer_tuple, explanation


# -----------------------------
# Dedup & main
# -----------------------------

def fingerprint(problem: str) -> str:
    # Simple stable fingerprint to avoid duplicates within one run
    return str(hash(problem))

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # Language is fixed by prompt; default zh
    output_language = "zh"
    game = ExchangeGame(rng, output_language=output_language)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            problem, answer, explanation = game.generate_instance()
            fp = fingerprint(problem)
            if fp in seen:
                continue
            seen.add(fp)
            results.append({
                "problem": problem,
                "answer": answer,
                "explanation": explanation
            })
        except Exception as ex:
            eprint(f"[gen fail #{attempts}] {ex}")
            continue

    if len(results) < count:
        raise RuntimeError(f"生成失败：仅生成 {len(results)}/{count} 道题（已尝试 {attempts} 次）")

    sys.stdout.write(json_dumps(results))

if __name__ == "__main__":
    main()