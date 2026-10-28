import random
import json
import uuid
import copy
import z3
from typing import List, Tuple, Dict

# ==========================================
# 核心生成逻辑：基于区域生长
# ==========================================

def generate_arrow_maze(num_of_questions: int = 100, max_attempts: int = 10000,
                        width: int = 8, height: int = 8, 
                        arrow_fill_rate_min: float = 0.0, arrow_fill_rate_max: float = 0.0):
    """
    生成严格符合规则的箭头迷宫（保证有解且无孤立箭头）。
    采用“区域生长法”确保完美分割。
    """
    
    ARROWS = {
        "↑": (-1, 0), "↓": (1, 0), "←": (0, -1), "→": (0, 1),
        "↖": (-1, -1), "↗": (-1, 1), "↘": (1, 1), "↙": (1, -1)
    }
    
    game_data_list = []
    global_attempts = 0
    
    while len(game_data_list) < num_of_questions and global_attempts < max_attempts:
        global_attempts += 1
        
        # 1. 初始化
        n, m = height, width
        # grid 用于存放最终的显示内容 (数字 或 X)
        grid = [["X" for _ in range(m)] for _ in range(n)]
        # solution 用于存放答案 (数字 或 箭头)
        solution = [[None for _ in range(m)] for _ in range(n)]
        # 记录已占用的格子
        occupied = [[False for _ in range(m)] for _ in range(n)]
        
        # 获取所有坐标并打乱，用于随机选择生长点
        all_coords = [(r, c) for r in range(n) for c in range(m)]
        random.shuffle(all_coords)
        
        generation_failed = False
        
        # 2. 循环填满所有格子
        # 只要还有没被占用的格子，就从中选一个作为新的数字源头
        while any(not occupied[r][c] for r in range(n) for c in range(m)):
            
            # A. 寻找下一个数字的放置位置
            start_pos = None
            for r, c in all_coords:
                if not occupied[r][c]:
                    start_pos = (r, c)
                    break
            
            if not start_pos: 
                break # 理论上不会进这里，因为外层 while 检查了
            
            sr, sc = start_pos
            occupied[sr][sc] = True # 标记源头已占用
            
            # B. 随机决定这个数字向哪些方向生长
            # 为了增加随机性，打乱方向
            directions = list(ARROWS.items())
            random.shuffle(directions)
            
            total_length = 0
            
            # 尝试向每个方向生长
            for arrow_char, (dr, dc) in directions:
                # 随机决定这个方向的生长长度 (贪婪生长，或者随机截断)
                # 为了让迷宫更复杂，我们尝试尽可能长，但偶尔随机停止
                cr, cc = sr + dr, sc + dc
                ray_len = 0
                
                # 记录这条射线上的点，以便确认生长
                path_cells = []
                
                while 0 <= cr < n and 0 <= cc < m:
                    if occupied[cr][cc]:
                        # 撞到了别的数字或箭头，停止
                        break
                    
                    # 记录这个点
                    path_cells.append((cr, cc))
                    
                    # 随机停止机制 (防止射线全部贯穿到底，增加数字多样性)
                    # 30% 概率停止生长，或者如果长度太长也停止
                    if random.random() < 0.3:
                        break
                        
                    cr += dr
                    cc += dc
                
                # 确认生长这些格子
                for pr, pc in path_cells:
                    occupied[pr][pc] = True
                    solution[pr][pc] = arrow_char
                    ray_len += 1
                
                total_length += ray_len
            
            # C. 检查生成的数字是否合法
            # 规则：数字必须大于 0 (题目通常要求非0长度)
            if total_length == 0:
                # 这是一个死格子，无法向任何地方生长。
                # 这会导致生成失败（因为我们要求完美分割，不能有孤立的数字0）
                generation_failed = True
                break
                
            # 记录数字
            grid[sr][sc] = str(total_length)
            solution[sr][sc] = str(total_length)

        if generation_failed:
            continue

        # 3. 构造输出数据
        # 此时 grid 中非数字的地方是 "X"，solution 中是箭头
        
        # 验证一下是否有解（虽然构造法保证了至少有 solution 这个解）
        # 使用你之前的严格 get_solution_count 确保万无一失
        try:
            count = get_solution_count(grid, max_count=11)
            if count == 0 or count == 11:
                continue
        except Exception:
            # 如果求解器报错，保守起见跳过
            continue

        # 生成 Prompt
        question = prompt_arrow_maze(grid, n, m, random.choice([True, False]))
        answer = json.dumps(solution)
        
        data = Data(
            question=question,
            answer=answer,
            metadata={
                "trace_id": str(uuid.uuid4()),
                "maze": grid,
                "solution": solution,
                "height": n,
                "width": m,
                "solution_count": count 
            }
        )
        game_data_list.append(data)
        
    return game_data_list

# ==========================================
# 辅助类与函数 (保持不变或微调)
# ==========================================

class Data:
    def __init__(self, question, answer, metadata):
        self.question = question
        self.answer = answer
        self.metadata = metadata
    
    def to_json(self):
        return {
            "question": self.question,
            "answer": self.answer,
            "metadata": self.metadata
        }

def prompt_arrow_maze(maze, n, m, include_example):
    grid_str = "[\n"
    for i, row in enumerate(maze):
        grid_str += "    ["
        grid_str += ", ".join(f'"{cell}"' for cell in row)
        grid_str += "]"
        if i < len(maze) - 1:
            grid_str += ","
        grid_str += "\n"
    grid_str += "]"
    
    prompt = f"""
你需要分析一个 {n}行 x {m}列 的箭头迷宫。

规则如下：
1. X 表示空白格子，数字表示射线箭头串的起点。
2. 你需要在空白格子中填入箭头（↑、↓、←、→、↖、↗、↘、↙）。
3. 每个数字指示从该位置发出的所有射线箭头串的总长度。
4. **所有箭头都必须是某条射线的组成部分（即每个箭头都要能回溯到一个数字源头，不能存在孤立的箭头）。**

初始网格如下：
{grid_str}

**问题：请计算有多少种不同的填充方案可以满足上述所有数字的约束条件？**
（如果只有一种解，请回答 1；如果有多种解，请回答具体的数量。）
"""
    return prompt

# ==========================================
# 严格解计数器 (包含完美分割约束)
# ==========================================
def get_solution_count(initial_grid: List[List[str]], max_count: int = 10) -> int:
    """
    计算箭头迷宫所有可能的解的数量（严格模式：所有箭头必须有源头）。
    """
    n = len(initial_grid)
    m = len(initial_grid[0])
    
    ARROWS = {
        "↑": (-1, 0), "↓": (1, 0), "←": (0, -1), "→": (0, 1),
        "↖": (-1, -1), "↗": (-1, 1), "↘": (1, 1), "↙": (1, -1)
    }
    ARROW_KEYS = list(ARROWS.keys())

    solver = z3.Solver()
    grid_vars = [[z3.String(f"cell_{i}_{j}") for j in range(m)] for i in range(n)]

    # 1. 基础约束
    for i in range(n):
        for j in range(m):
            cell_val = initial_grid[i][j]
            if cell_val.isdigit():
                solver.add(grid_vars[i][j] == cell_val)
            else:
                solver.add(z3.Or([grid_vars[i][j] == a for a in ARROW_KEYS]))

    # 2. 射线长度与覆盖记录
    coverage_matrix = [[[] for _ in range(m)] for _ in range(n)]

    for i in range(n):
        for j in range(m):
            if initial_grid[i][j].isdigit():
                expected_len = int(initial_grid[i][j])
                total_len_terms = []
                
                for arrow, (di, dj) in ARROWS.items():
                    ni, nj = i + di, j + dj
                    path_conds = [] 
                    
                    while 0 <= ni < n and 0 <= nj < m:
                        if initial_grid[ni][nj].isdigit():
                            break
                        is_arrow_match = (grid_vars[ni][nj] == arrow)
                        
                        if not path_conds:
                            current_cond = is_arrow_match
                        else:
                            current_cond = z3.And(path_conds[-1], is_arrow_match)
                        
                        path_conds.append(current_cond)
                        coverage_matrix[ni][nj].append(current_cond)
                        
                        ni += di
                        nj += dj
                    
                    for cond in path_conds:
                        total_len_terms.append(z3.If(cond, 1, 0))
                
                solver.add(sum(total_len_terms) == expected_len)

    # 3. 强制覆盖约束
    for i in range(n):
        for j in range(m):
            if not initial_grid[i][j].isdigit():
                possible_covers = coverage_matrix[i][j]
                if not possible_covers:
                    return 0 # 物理上不可达，无解
                
                # 完美分割约束：每个格子恰好被覆盖1次
                coverage_count = sum([z3.If(cond, 1, 0) for cond in possible_covers])
                solver.add(coverage_count == 1)

    # 4. 计数
    count = 0
    while solver.check() == z3.sat:
        count += 1
        if count >= max_count:
            break
        model = solver.model()
        block = []
        for i in range(n):
            for j in range(m):
                if not initial_grid[i][j].isdigit():
                    current_val = model[grid_vars[i][j]]
                    block.append(grid_vars[i][j] != current_val)
        solver.add(z3.Or(block))

    return count

# 本地测试块
if __name__ == "__main__":
    # 生成 5个 6x4 的迷宫进行测试
    print("Generating mazes...")
    mazes = generate_arrow_maze(5, 100, 4, 6) # width=4, height=6
    
    for idx, data in enumerate(mazes):
        print(f"\n--- Maze {idx+1} ---")
        print(f"Solution Count (Strict): {data.metadata['solution_count']}")
        print("Grid:")
        for row in data.metadata['maze']:
            print(row)
        print("Generated Solution (One of valid solutions):")
        for row in data.metadata['solution']:
            print(row)