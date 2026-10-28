import random
from copy import deepcopy

def gen_attributes(n):
    """
    随机生成 n 件物品的初始属性（并行列表），满足以下约束：
      - 至少1件材质=“玻璃”（使步骤1生效）
      - 至少1件产地=“葡萄牙”（使步骤2生效）
      - 至少1件尺寸=“超超小”（使步骤3生效）
    返回：
      {
        'sizes': [...],
        'origins': [...],
        'materials': [...],
        'smells': [...],
        'types': [...]
      }
    """
    sizes_set = ['超超小', '超小', '小', '中', '大', '超大', '超超大']
    origins_set = ['意大利', '德国', '葡萄牙', '加拿大', '墨西哥', '土耳其', '俄罗斯']
    materials_set = ['布', '纸', '钛', '金属', '陶瓷', '玻璃', '混凝土']
    smells_set = ['烤面包', '香草', '燃烧的木头', '巧克力', '大蒜', '咖啡', '玫瑰']
    types_set = ['灯', '铅笔', '瓶子', '鞋', '尺子', '碗', '垃圾桶']

    # 多次尝试以满足约束
    for _ in range(1000):
        sizes = [random.choice(sizes_set) for __ in range(n)]
        origins = [random.choice(origins_set) for __ in range(n)]
        materials = [random.choice(materials_set) for __ in range(n)]
        smells = [random.choice(smells_set) for __ in range(n)]
        types = [random.choice(types_set) for __ in range(n)]

        cond_glass = any(m == '玻璃' for m in materials)
        cond_pt = any(o == '葡萄牙' for o in origins)
        cond_xxs = any(s == '超超小' for s in sizes)

        if cond_glass and cond_pt and cond_xxs:
            return {
                'sizes': sizes,
                'origins': origins,
                'materials': materials,
                'smells': smells,
                'types': types,
            }

    # 兜底策略：若极端情况下未能满足（几乎不会发生），强制植入必要元素
    sizes = [random.choice(sizes_set) for __ in range(n)]
    origins = [random.choice(origins_set) for __ in range(n)]
    materials = [random.choice(materials_set) for __ in range(n)]
    smells = [random.choice(smells_set) for __ in range(n)]
    types = [random.choice(types_set) for __ in range(n)]
    # 植入必要条件
    sizes[0] = '超超小'
    origins[1] = '葡萄牙'
    materials[2] = '玻璃'
    return {
        'sizes': sizes,
        'origins': origins,
        'materials': materials,
        'smells': smells,
        'types': types,
    }

def build_collection(sizes, origins, materials, smells, types, colors):
    """
    将并行属性列表组装为物品字典列表
    """
    n = len(sizes)
    coll = []
    for i in range(n):
        coll.append({
            'size': sizes[i],
            'origin': origins[i],
            'material': materials[i],
            'smell': smells[i],
            'type': types[i],
            'color': colors[i],
        })
    return coll

def transform_glass(coll):
    """
    步骤1：材质=玻璃 -> color='金色', smell='香草'
    """
    res = []
    for it in coll:
        x = deepcopy(it)
        if x.get('material') == '玻璃':
            x['color'] = '金色'
            x['smell'] = '香草'
        res.append(x)
    return res

def swap_portugal(coll):
    """
    步骤2：origin=葡萄牙 -> size='超大', material='布'
    其余属性保持不变
    """
    res = []
    for it in coll:
        x = deepcopy(it)
        if x.get('origin') == '葡萄牙':
            x['size'] = '超大'
            x['material'] = '布'
        res.append(x)
    return res

def duplicate_xxs_keep_original(coll):
    """
    步骤3：对 size='超超小' 的物品，原件保留，并新增两件副本：
      - 副本A：仅 size='小'
      - 副本B：仅 color='米色'
    返回扩展后的集合
    """
    res = []
    for it in coll:
        res.append(deepcopy(it))  # 原件
        if it.get('size') == '超超小':
            a = deepcopy(it)
            a['size'] = '小'
            b = deepcopy(it)
            b['color'] = '米色'
            res.append(a)
            res.append(b)
    return res

def count_target(coll):
    """
    计数满足以下任一条件的物品数量：
      - material == '陶瓷'
      - size == '超小'
      - color == '米色'
      - smell == '大蒜'
      - origin == '俄罗斯'
    """
    cnt = 0
    for it in coll:
        if (
            it.get('material') == '陶瓷'
            or it.get('size') == '超小'
            or it.get('color') == '米色'
            or it.get('smell') == '大蒜'
            or it.get('origin') == '俄罗斯'
        ):
            cnt += 1
    return cnt