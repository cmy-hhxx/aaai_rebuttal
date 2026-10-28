import random

def generate_darts(n, r):
    """
    生成n个互不相同的整数坐标点
    """
    points_set = set()
    
    while len(points_set) < n:
        x = random.randint(-r, r)
        y = random.randint(-r, r)
        points_set.add((x, y))
    
    res = []
    for points in list(points_set):
        res.append(list(points))
    return res

# 使用示例
# darts = generate_darts(10, 5)
# print(darts)

import math
from typing import List

def numPoints(points, r):
    n = len(points)
    if n <= 1:
        return n
        
    # 预计算所有点对之间的向量
    vec = [[0, 0] for _ in range(n * n)]
        
    for i in range(n):
        for j in range(n):
            if i != j:
                idx = i * n + j
                vec[idx][0] = points[j][0] - points[i][0]
                vec[idx][1] = points[j][1] - points[i][1]
        
    ans = 1
    r_sq = r * r
    four_r_sq = 4 * r_sq
        
    for i in range(n):
        angles = []
        for j in range(n):
            if i == j:
                continue
                    
            idx = i * n + j
            dx, dy = vec[idx]
            dist_sq = dx * dx + dy * dy
                
            if dist_sq <= four_r_sq + 1e-8:
                dist = math.sqrt(dist_sq)
                C = math.acos(dist / (2 * r))
                T = math.atan2(dy, dx)
                    
                angles.append((T - C, 1))   # 进入角度
                angles.append((T + C, -1))  # 离开角度
            
        if not angles:
            continue
                
        # 排序：先按角度，然后进入事件在前，离开事件在后
        angles.sort(key=lambda x: (x[0], -x[1]))
            
        # 处理循环边界
        extended_angles = []
        for angle, event in angles:
            extended_angles.append((angle, event))
            extended_angles.append((angle + 2 * math.pi, event))
            extended_angles.append((angle - 2 * math.pi, event))
            
        extended_angles.sort(key=lambda x: (x[0], -x[1]))
            
        cnt = 1
        max_cnt = 1
            
        for angle, event in extended_angles:
            cnt += event
            if cnt > max_cnt:
                max_cnt = cnt
            
        ans = max(ans, max_cnt)
        
    return ans