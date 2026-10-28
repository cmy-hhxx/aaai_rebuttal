from functools import cmp_to_key
from typing import List

def largestNumber(nums: List[int]) -> str:
    num_str = list(map(str, nums))  # 转换为字符串列表（Python3中map返回迭代器，需显式转list）
        
    # 定义比较函数：x+y < y+x 时，x应排在y后面（返回1表示x需要被排序到y之后）
    def compare(x: str, y: str) -> int:
        if x + y < y + x:
            return 1
        else:
            return -1
        
    # 使用cmp_to_key将compare转换为key函数，传入sort
    num_str.sort(key=cmp_to_key(compare))
        
    # 处理全零情况
    if num_str[0] == '0':
        return '0'
        
    return ''.join(num_str)

if __name__ == '__main__':
    nums = [10,2]
    print(largestNumber(nums))