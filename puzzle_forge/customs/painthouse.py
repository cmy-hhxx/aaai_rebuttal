import math
import copy

def minCostII(costs):
    copy_costs = copy.deepcopy(costs)
    n = len(copy_costs)
    if n == 0: return 0
    k = len(copy_costs[0])

    for house in range(1, n):
        for color in range(k):
            best = math.inf
            for previous_color in range(k):
                if color == previous_color: continue
                best = min(best, copy_costs[house - 1][previous_color])
            copy_costs[house][color] += best

    return min(copy_costs[-1])