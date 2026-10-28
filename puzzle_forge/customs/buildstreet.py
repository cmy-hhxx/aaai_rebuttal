import heapq
from typing import List
import copy

def minBuildTime(input_blocks, split):

    blocks = copy.deepcopy(input_blocks)
    # 直接使用堆操作，避免不必要的列表操作
    heapq.heapify(blocks)
        
    while len(blocks) > 1:
        # 每次弹出两个最小的元素
        a = heapq.heappop(blocks)
        b = heapq.heappop(blocks)
        # 合并时间 = 分裂时间 + 两个中较大的构建时间
        heapq.heappush(blocks, split + max(a, b))
        
    return blocks[0]