def numMusicPlaylists(N, L, K):
    MOD = 10**9 + 7
    def inv(x):
        return pow(x, MOD-2, MOD)

    C = 1
    for x in range(1, N-K):
        C *= -x
        C %= MOD
    C = inv(C)

    ans = 0
    for k in range(1, N-K+1):
        ans += pow(k, L-K-1, MOD) * C
        C = C * (k - (N-K)) % MOD * inv(k) % MOD

    for k in range(1, N+1):
        ans = ans * k % MOD
    return ans
