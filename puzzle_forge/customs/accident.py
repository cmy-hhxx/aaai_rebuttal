import random

def create_color_probs(n,total=100):
    if n == 1:
        return [total]
    
    # 生成第一个随机数（确保后续n-1个数都能至少为1）
    first = random.randint(1, total - n + 1)
    
    # 递归生成剩余的数
    rest = create_color_probs(n-1, total - first)
    
    return [first] + rest

def bayesian_color_inference(colors, ori_proportions, said_color, accuracy=0.8):
    """
    贝叶斯推理：根据目击者描述，推断实际车辆颜色的概率。

    参数：
    - colors: list of str, 颜色名称，如 ['Blue', 'Yellow']
    - proportions: list of float, 各颜色的先验比例，和为1
    - said_color: str, 目击者声称看到的颜色
    - accuracy: float, 目击者正确识别颜色的概率（默认 80%）

    返回：
    - posterior: dict, {颜色: 后验概率}
    """
    proportions = []
    for pro in ori_proportions:
        proportions.append(round(pro/100,2))
    if len(colors) != len(proportions):
        raise ValueError("colors 和 proportions 长度必须一致")
    if abs(sum(proportions) - 1.0) > 1e-6:
        raise ValueError("proportions 的和必须为 1")

    if said_color not in colors:
        raise ValueError(f"said_color '{said_color}' 不在 colors 列表中")

    num_colors = len(colors)
    prior = dict(zip(colors, proportions))
    posterior = {}

    # 计算 P(说 said_color)
    total_prob_said = 0.0

    for actual, p_prior in prior.items():
        if actual == said_color:
            # 正确识别
            p_say = accuracy
        else:
            # 错误识别：均匀分配给其他颜色
            p_say = (1 - accuracy) / (num_colors - 1) if num_colors > 1 else 0
        total_prob_said += p_say * p_prior

    if total_prob_said == 0:
        raise ValueError("P(说某色) 为 0，无法计算")

    # 计算后验概率 P(实际颜色 | 说某色)
    for actual, p_prior in prior.items():
        if actual == said_color:
            p_say_given_actual = accuracy
        else:
            p_say_given_actual = (1 - accuracy) / (num_colors - 1) if num_colors > 1 else 0

        posterior[actual] = (p_say_given_actual * p_prior) / total_prob_said

    return posterior[said_color]


# ======================
# 使用示例
# ======================

if __name__ == "__main__":
    # 原问题：蓝色 70%，黄色 30%
    colors = ['Blue', 'Yellow']
    proportions = create_color_probs(2)
    said_color = 'Blue'
    accuracy = 0.8

    result = bayesian_color_inference(colors, proportions, said_color, accuracy)
    print(proportions)
    print("🚗 肇事车辆颜色贝叶斯推理结果")
    print(f"目击者称车辆为: {said_color}")
    print("-" * 40)
    for color, prob in result.items():
        print(f"P(实际为 {color} | 说 {said_color}) = {prob:.4f} ({prob * 100:.2f}%)")