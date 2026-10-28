
def superEggDrop(k, n):
    """
    使用动态规划解决鸡蛋掉落问题（反向思维）
        
    参数:
        k: 鸡蛋数量
        n: 楼层数
            
    返回:
        确定安全楼层的最小操作次数
    """
    # 如果只有一层楼，只需一次测试
    if n == 1:
        return 1
        
    # dp[moves][eggs] 表示使用moves次操作和eggs个鸡蛋能确定的最大楼层数
    dp = [[0] * (k + 1) for _ in range(n + 1)]
        
    # 初始化：一次操作时，无论有多少鸡蛋，最多只能确定一层楼
    for eggs in range(1, k + 1):
        dp[1][eggs] = 1
        
    min_moves = -1
        
    # 遍历可能的操作次数
    for moves in range(2, n + 1):
        # 遍历可能的鸡蛋数量
        for eggs in range(1, k + 1):
            # 状态转移方程：
            # 当前操作能确定的楼层数 = 1（当前测试的楼层） + 
            # 鸡蛋碎了时下方能确定的楼层数 + 
            # 鸡蛋没碎时上方能确定的楼层数
            dp[moves][eggs] = 1 + dp[moves - 1][eggs - 1] + dp[moves - 1][eggs]
            
        # 如果当前操作次数能够确定n层楼
        if dp[moves][k] >= n:
            min_moves = moves
            break
        
    return min_moves