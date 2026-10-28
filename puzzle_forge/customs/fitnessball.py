import math
import random

def generate_diverse_array(n, l):
    """
    生成总和为 n、长度为 l 的数组，元素 >1 且尽可能不同
    
    参数:
        n (int): 数组元素总和
        l (int): 数组长度
    
    返回:
        list: 符合条件的数组，若无法满足则返回 None
    """
    if n < 2 * l:
        return None  # 无法满足所有元素 >1
    if n == 2 * l:
        return [2] * l  # 唯一解
    
    # 初始分配：从 2 开始递增，保证尽可能不同
    arr = []
    remaining = n
    for i in range(l):
        next_val = max(2, 2 + i)  # 从 2 开始递增
        if remaining - next_val < 2 * (l - i - 1):  # 确保剩余部分能分配 >1
            next_val = remaining - 2 * (l - i - 1)
        arr.append(next_val)
        remaining -= next_val
    
    # 如果剩余 >0，均匀分配到部分元素上
    while remaining > 0:
        idx = random.randint(0, l-1)
        arr[idx] += 1
        remaining -= 1
    
    # 打乱顺序（可选）
    random.shuffle(arr)
    print(n,l,arr)
    return arr

def cal_gcd(a,b):
    return math.gcd(a, b)

def prod_list(arr):
    # arr = [2, 3, 4]
    return math.prod(arr)  # 输出: 24

def cal_eff(denom_list,molecula_list,production_each_workshop,colors,workshops):
    
    res = []

    for i in range(len(production_each_workshop)):
        temp = []
        molecula = molecula_list[i]
        denom = denom_list[i]
        produc = production_each_workshop[i]
        for j in range(len(molecula)):
            temp.append(produc/(molecula[j]/denom*30))
            # res[(workshops[i],colors[j])] = produc/(molecula[j]/denom*30)
        res.append(temp)
    
    # print(denom_list,molecula_list,production_each_workshop)
    # print(res)

    return res
# And(sum(workdays[(x,y)]*efficiency[i][j] for i, x in enumerate(workshops)) >= vars['total'] for j, y in enumerate(colors))

# print([random.sample([3,5,6,10,15],1) for _ in range(3)][0])
# if __name__ == '__main__':
    # from z3 import *

    # # 创建优化器
    # opt = Optimize()

    # # 定义决策变量
    # # 甲车间生产黑球和白球的时间（天）
    # t1_black = Int('t1_black')
    # t1_white = Int('t1_white')

    # # 乙车间生产黑球和白球的时间（天）
    # t2_black = Int('t2_black')
    # t2_white = Int('t2_white')

    # # 每个车间的总时间约束
    # opt.add(t1_black + t1_white == 30)
    # opt.add(t2_black + t2_white == 30)

    # # 时间非负约束
    # opt.add(t1_black >= 0, t1_white >= 0)
    # opt.add(t2_black >= 0, t2_white >= 0)

    # # 计算生产的黑球和白球数量
    # # 甲车间生产效率：黑球=270/(30*3/5)=15个/天，白球=270/(30*2/5)=22.5个/天
    # # 乙车间生产效率：黑球=300/(30*1/3)=30个/天，白球=300/(30*2/3)=15个/天
    # # black_total = 15 * t1_black + 30 * t2_black
    # # white_total = 22.5 * t1_white + 15 * t2_white

    # black_total = 18 * t1_black + 310/18 * t2_black
    # white_total = 18 * t1_white + 310/12 * t2_white

    # # 完整套数由黑球和白球中较少的数量决定
    # sets = Int('sets')
    # opt.add(sets <= black_total)
    # opt.add(sets <= white_total)

    # # 最大化完整套数
    # opt.maximize(sets)

    # # black_total = 15 * t1_black + 30 * t2_black
    # # white_total = 22.5 * t1_white + 15 * t2_white

    # # 求解优化问题
    # if opt.check() == sat:
    #     model = opt.model()
    #     print(opt.check(),model)
    #     print("最大套数:", model[sets])
    #     print("甲车间:")
    #     print(f"  生产黑球时间: {model[t1_black]} 天")
    #     print(f"  生产白球时间: {model[t1_white]} 天")
    #     print("乙车间:")
    #     print(f"  生产黑球时间: {model[t2_black]} 天")
    #     print(f"  生产白球时间: {model[t2_white]} 天")
    #     print("黑球总数:", black_total)
    #     print("白球总数:", white_total)
    # else:
    #     print("问题无解")