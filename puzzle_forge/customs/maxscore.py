from math import gcd

def maxScore(nums: list) -> int:
    """
    计算通过操作数组所能获得的最大分数。
    
    每次操作选择两个未被选过的数字，分数增加当前操作序号 * gcd(选中的两个数字)
    
    参数:
        nums: 整数列表
        
    返回:
        最大分数
    """
    n = len(nums)
    total_states = 1 << n  # 总状态数
    dp = [0] * total_states  # dp[state] 表示在该状态下能获得的最大分数
    
    # 遍历所有可能的状态
    for state in range(total_states):
        selected_count = state.bit_count()  # 当前状态选中的数字个数
        
        # 如果选中的数字个数不是偶数，跳过（因为每次需要选择两个数字）
        if selected_count % 2 != 0:
            continue
            
        # 遍历所有可能的数字对
        for i in range(n):
            # 如果第i个数字在当前状态中未被选中，跳过
            if not (state >> i & 1):
                continue
                
            for j in range(i + 1, n):  # 避免重复计算相同的数字对
                # 如果第j个数字在当前状态中未被选中，跳过
                if not (state >> j & 1):
                    continue
                    
                # 计算移除i和j两个数字后的状态
                prev_state = state ^ (1 << i) ^ (1 << j)
                
                # 计算当前操作序号（即第几次操作）
                operation_num = selected_count // 2
                
                # 更新当前状态的最大分数
                current_score = operation_num * gcd(nums[i], nums[j])
                dp[state] = max(dp[state], dp[prev_state] + current_score)
                
    return dp[total_states - 1]