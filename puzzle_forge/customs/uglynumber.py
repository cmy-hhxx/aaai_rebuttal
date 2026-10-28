from math import lcm

def nthUglyNumber(n, a, b, c):
    """
    使用二分查找和容斥原理找出第n个能被a、b或c整除的丑数
        
    参数:
        n: 要找到的第n个丑数的位置
        a, b, c: 三个除数
            
    返回:
        第n个能被a、b或c整除的丑数
    """
    # 计算两两的最小公倍数
    lcm_ab = lcm(a, b)
    lcm_ac = lcm(a, c)
    lcm_bc = lcm(b, c)
    # 计算三个数的最小公倍数
    lcm_abc = lcm(a, b, c)
        
    def count_ugly_numbers(x: int) -> int:
        """
        使用容斥原理计算小于等于x的丑数数量
            
        公式:
            count = ⌊x/a⌋ + ⌊x/b⌋ + ⌊x/c⌋
                    - ⌊x/lcm(a,b)⌋ - ⌊x/lcm(a,c)⌋ - ⌊x/lcm(b,c)⌋
                    + ⌊x/lcm(a,b,c)⌋
        """
        return (x // a + x // b + x // c 
                - x // lcm_ab - x // lcm_ac - x // lcm_bc 
                + x // lcm_abc)
        
    def is_valid_candidate(x: int) -> bool:
        """检查x是否包含至少n个丑数"""
        return count_ugly_numbers(x) >= n
        
    # 二分查找范围
    left, right = 1, 2 * 10**9
        
    while left < right:
        mid = (left + right) // 2
        if is_valid_candidate(mid):
            right = mid
        else:
            left = mid + 1
                
    return left