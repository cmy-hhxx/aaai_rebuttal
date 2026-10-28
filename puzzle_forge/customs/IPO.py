import heapq
from heapq import nlargest
from heapq import heappush
from heapq import heappop

def findMaximizedCapital(k, w, profits, capital):
    if w >= max(capital):
        return w + sum(nlargest(k, profits))

    n = len(profits)
    curr = 0
    arr = [(capital[i], profits[i]) for i in range(n)]
    arr.sort(key = lambda x : x[0])
    
    pq = []
    for _ in range(k):
        while curr < n and arr[curr][0] <= w:
            heappush(pq, -arr[curr][1])
            curr += 1

        if pq:
            w -= heappop(pq)
        else:
            break
        
    return w

import random

def create_increasing_lists(n, min_val=0, max_val=100):
    """
    创建两个递增列表，list1每个元素都大于list2对应位置的元素
    
    Args:
        n: 列表长度
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        list1, list2: 两个递增列表
    """
    # 生成第一个递增列表
    list1 = sorted([random.randint(min_val, max_val) for _ in range(n)])
    
    # 生成第二个列表，确保每个元素都小于list1对应位置的元素
    list2 = []
    for i in range(n):
        # 确保list2[i] < list1[i]，同时保持递增
        if i == 0:
            # 第一个元素：小于list1[0]的随机数
            max_val2 = list1[0] - 1
            list2.append(random.randint(min_val, max_val2))
        else:
            # 后续元素：大于list2[i-1]且小于list1[i]
            min_val2 = list2[i-1] + 1  # 保持递增
            max_val2 = list1[i] - 1    # 小于list1[i]
            if min_val2 <= max_val2:
                list2.append(random.randint(min_val2, max_val2))
            else:
                # 如果无法满足条件，调整list1
                list1[i] = max(list1[i], list2[i-1] + 2)
                list2.append(list2[i-1] + 1)
    
    return list1, list2

def create_increasing_profits(n, min_val=1, max_val=100):
    """
    创建两个递增列表，list1每个元素都大于list2对应位置的元素
    
    Args:
        n: 列表长度
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        list1, list2: 两个递增列表
    """
    # 生成第一个递增列表
    list1 = sorted([random.randint(min_val, max_val) for _ in range(n)])
    
    return list1

def create_increasing_capital(n, list1, min_val=0, max_val=100):
    """
    创建两个递增列表，list1每个元素都大于list2对应位置的元素
    
    Args:
        n: 列表长度
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        list1, list2: 两个递增列表
    """
    
    # 生成第二个列表，确保每个元素都小于list1对应位置的元素
    list2 = []
    for i in range(n):
        # 确保list2[i] < list1[i]，同时保持递增
        if i == 0:
            # 第一个元素：小于list1[0]的随机数
            max_val2 = list1[0] - 1
            # print(min_val, max_val2)
            list2.append(random.randint(min_val, max_val2))
        else:
            # 后续元素：大于list2[i-1]且小于list1[i]
            min_val2 = list2[i-1] + 1  # 保持递增
            max_val2 = list1[i] - 1    # 小于list1[i]
            if min_val2 <= max_val2:
                list2.append(random.randint(min_val2, max_val2))
            else:
                # 如果无法满足条件，调整list1
                list1[i] = max(list1[i], list2[i-1] + 2)
                list2.append(list2[i-1] + 1)
    
    return list2

if __name__ == '__main__':
    profits = create_increasing_profits(10)
    capital = create_increasing_capital(10,profits)
    print(profits,capital)