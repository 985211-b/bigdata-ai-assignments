# -*- coding: utf-8 -*-
"""
我的第一个 Python 脚本
运行方式（在本文件所在目录打开终端）：
    py hello.py          使用 Python 3.12
    python hello.py      使用 PATH 中默认的 Python
"""

import platform
import sys
from datetime import datetime

# 1. 最简单的输出
print("Hello, Python!")

# 2. 看看当前用的是哪个 Python
print("-" * 40)
print(f"Python 版本 : {platform.python_version()}")
print(f"解释器路径   : {sys.executable}")

# 3. 一点点计算：打印乘法表的一行
print("-" * 40)
n = 7
print(f"{n} 的乘法表：", end="")
for i in range(1, 6):
    print(f"{n}x{i}={n * i}", end="  ")
print()

# 4. 一个函数 + 列表推导式
def square(x):
    return x * x


numbers = [1, 2, 3, 4, 5]
print(f"{numbers} 的平方：{list(map(square, numbers))}")
print(f"其中的偶数：{[x for x in numbers if x % 2 == 0]}")

# 5. 运行时间戳
now = datetime.now()
print("-" * 40)
print(f"脚本运行时间：{now:%Y-%m-%d %H:%M:%S}")
print("运行成功，没有报错。")
