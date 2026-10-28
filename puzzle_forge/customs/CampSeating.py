import itertools
import math
from functools import lru_cache

def comb(n, k):
    return math.comb(n, k)

def enumerate_team_distributions(r, k, S):
    """
    枚举所有可能的 (n1,...,nr)，其中 n_i >= 1, n_i <= S, sum(n_i) = k
    返回 list of tuples
    """
    results = []
    def dfs(i, remain, cur):
        if i == r:
            if remain == 0:
                results.append(tuple(cur))
            return
        for x in range(1, S+1):
            if remain - x < 0: break
            dfs(i+1, remain-x, cur+[x])
    dfs(0, k, [])
    return results

def check_distribution_constraints(d, k, S, m):
    """
    检查分配是否符合条件：
    1. sum == k
    2. 每个 <= S
    3. 至少有一个等于 m
    """
    if sum(d) != k:
        return False
    if any(x > S for x in d):
        return False
    if m not in d:
        return False
    return True

def count_non_adjacent_arrangements(d, k, S):
    """
    计算在分配 d = (n1,...,nr) 下的合法座位排列数：
    条件：相邻位置不能来自同一队。
    假设每个队内的个体是不同的，因此同队有排列因子 n_i!。
    思路：
    - 首先计算在 r 种颜色（队伍）的限制下的排列数（即非相邻的序列个数）
    - 然后乘上 ∏ n_i! （因为队内营员可交换）
    """

    r = len(d)

    # DP状态：位置pos，上一支队伍last，已放计数tuple
    @lru_cache(None)
    def dp(pos, last, counts):
        if pos == k:
            return 1
        total = 0
        counts = list(counts)
        for i in range(r):
            if i == last: 
                continue
            if counts[i] < d[i]:
                new_counts = tuple(counts[j] + (1 if j == i else 0) for j in range(r))
                total += dp(pos+1, i, new_counts)
        return total

    base = dp(0, -1, tuple([0]*r))

    # 乘上 ∏ n_i! 因为队内每个人不同
    fact = 1
    for x in d:
        fact *= math.perm(S, x)  # 从每个队 S 人中挑出 x 人并全排列
    return base * fact

def total_valid_arrangements(T, S, k, r, m):
    choose_r = comb(T, r)
    team_distributions = enumerate_team_distributions(r, k, S)
    valid = [d for d in team_distributions if check_distribution_constraints(d, k, S, m)]
    arrangements = [count_non_adjacent_arrangements(d, k, S) for d in valid]
    return choose_r * sum(arrangements)

def min_num(a, b):
    return min(a, b)