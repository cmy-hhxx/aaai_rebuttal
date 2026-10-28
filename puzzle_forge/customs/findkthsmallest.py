from typing import List
from collections import defaultdict
import math

def findKthSmallest(coins, k):
    n = len(coins)
    # 使用字典存储不同长度的最小公倍数组合
    lcm_combinations = defaultdict(list)
    current_combination = []
        
    def backtrack(index):
        """使用回溯法生成所有可能的硬币组合并计算其最小公倍数"""
        if index == n:
            if current_combination:
                # 计算当前组合的最小公倍数
                combination_lcm = math.lcm(*current_combination)
                lcm_combinations[len(current_combination)].append(combination_lcm)
            return
            
        # 包含当前硬币
        current_combination.append(coins[index])
        backtrack(index + 1)
        current_combination.pop()
            
        # 不包含当前硬币
        backtrack(index + 1)
        
    # 生成所有组合
    backtrack(0)
        
    def count_numbers_upto(num):
        """使用容斥原理计算能被至少一个硬币整除的数字数量"""
        count = 0
        # 遍历所有可能的组合长度
        for length in range(1, n + 1):
            sign = 1 if length % 2 == 1 else -1  # 奇正偶负
            for lcm_val in lcm_combinations[length]:
                count += sign * (num // lcm_val)
        return count
        
    # 二分查找第k小的数
    left, right = 1, 10**15
    while left <= right:
        mid = (left + right) // 2
        if count_numbers_upto(mid) < k:
            left = mid + 1
        else:
            right = mid - 1
        
    return left