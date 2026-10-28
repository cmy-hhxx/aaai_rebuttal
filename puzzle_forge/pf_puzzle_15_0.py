# pf_puzzle_15_0.py
# 将二维数组解格式化为题目要求的字符串：[[row1,row2,...]]，行内空格分隔，行间逗号分隔
def format_grid(grid):
    rows = [" ".join(str(v) for v in row) for row in grid]
    return "[[" + ",".join(rows) + "]]"