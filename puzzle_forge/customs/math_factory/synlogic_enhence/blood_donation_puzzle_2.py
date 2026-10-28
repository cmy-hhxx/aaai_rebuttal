# blood_donation_puzzle_11.py
# 自定义操作符：索引查找、列表打乱、抽取不重复元素
import random

def index_of(lst, item):
    """
    返回 item 在 lst 中的索引位置。
    """
    return lst.index(item)

def shuffle_list(lst):
    """
    返回一个新的列表，为输入列表的随机排列。
    """
    l = list(lst)
    random.shuffle(l)
    return l

def pick_distinct(lst, k):
    """
    从列表中随机选取 k 个不重复元素，返回一个长度为 k 的新列表。
    若 k 等于列表长度，则返回一个随机排列。
    """
    if k > len(lst):
        raise ValueError("k cannot be greater than the length of the list")
    if k == len(lst):
        return shuffle_list(lst)
    return random.sample(list(lst), k)