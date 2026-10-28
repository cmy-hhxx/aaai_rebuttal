def max_money(arr):
    if not arr:
        return 0

    size = len(arr)
    if size == 1:
        return arr[0]
        
    dp = [0] * size
    dp[0] = arr[0]
    dp[1] = max(arr[0], arr[1])
    for i in range(2, size):
        dp[i] = max(dp[i - 2] + arr[i], dp[i - 1])
        
    return dp[size - 1]
