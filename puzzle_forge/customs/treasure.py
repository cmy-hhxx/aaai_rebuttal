import random

def create_value_matrix(n, low=1, high=20):
    """
    使用纯 Python 生成 n*n 随机整数矩阵
    """
    return [[random.randint(low, high) for _ in range(n)] for _ in range(n)]

def max_treasure_value(value):
    n = len(value)
    if n == 0:
        return 0
    if n == 1:
        return value[0][0]  # 只能拿宝藏然后出去
    
    # dp[i][j] 表示从第i行第j列出发能获得的最大价值
    dp = [[0] * n for _ in range(n)]
    
    # 从右下角开始，倒序遍历
    for i in range(n-1, -1, -1):
        for j in range(n-1, -1, -1):
            # 选项1：不拿宝藏 → 只能向下（如果不在最后一行）
            option1 = 0
            if i < n - 1:
                option1 = dp[i+1][j]
            else:
                option1 = 0  # 在最后一行，不拿就直接出去
            
            # 选项2：拿宝藏 → 获得 value[i][j]，然后只能向右（如果不在最后一列）
            take = value[i][j]
            if j < n - 1:
                take += dp[i][j+1]
            # 如果在最后一列，拿完就出去，不加
            
            dp[i][j] = max(option1, take)
    
    return dp[0][0]