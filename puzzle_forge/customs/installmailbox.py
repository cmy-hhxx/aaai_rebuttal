from typing import List
import math

def minDistance(houses, K):
    houses.sort()
    n = len(houses)
        
    # 预处理：使用前缀和优化距离计算
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + houses[i]
        
    # 快速计算区间[i, j]内放置一个邮箱的最小距离和
    def calc_dist(i, j):
        if i > j:
            return 0
        mid = (i + j) // 2
        left_count = mid - i
        right_count = j - mid
        left_sum = houses[mid] * left_count - (prefix[mid] - prefix[i])
        right_sum = (prefix[j + 1] - prefix[mid + 1]) - houses[mid] * right_count
        return left_sum + right_sum
        
    # DP优化：使用滚动数组
    dp_prev = [math.inf] * (n + 1)
    dp_prev[0] = 0
        
    for k in range(1, K + 1):
        dp_curr = [math.inf] * (n + 1)
        # 对于每个i，枚举最后一个邮箱覆盖的范围
        for i in range(k, n + 1):
            # 优化：从k-1开始，避免无效计算
            min_val = math.inf
            for j in range(k - 1, i):
                cost = dp_prev[j] + calc_dist(j, i - 1)
                if cost < min_val:
                    min_val = cost
            dp_curr[i] = min_val
        dp_prev = dp_curr
        
    return dp_prev[n]