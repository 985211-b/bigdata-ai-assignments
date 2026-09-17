# bigdata-ai-assignments

大数据 & AI 课程作业仓库。

## 目录结构

```
bigdata-ai-assignments/
├── assignments/              # 作业提交区（按周次/章节归档）
├── concept-learning-materials/  # 概念学习资料
├── data/                     # 数据集（原始数据 + 处理后数据）
├── docs/                     # 文档、笔记
├── notebooks/                # 实验用 Notebook
├── scripts/                  # 可直接运行的脚本
│   ├── 01.py                 # 作业①：创建 .py 文件并运行
│   └── 01.ipynb              # 作业②：创建 Notebook 并运行
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## 课程作业

### ① 创建 .py 文件并运行

文件：`scripts/01.py`

```bash
py scripts/01.py
```

预期输出：

```
我也会写程序啦！
```

### ② 创建 .ipynb 并运行

文件：`scripts/01.ipynb`

在 VS Code 中打开该文件，选择 Python 3.12 内核，点击顶部的「运行全部」即可。

## 开发环境

| 项目 | 版本 / 说明 |
| --- | --- |
| Python | 3.12.10 |
| 包管理 | pip（已配置清华 TUNA 镜像源） |

安装依赖：

```bash
py -3.12 -m pip install -r requirements.txt
```

## 提交说明

只提交源码与文档，**不要**提交虚拟环境、缓存文件和原始大数据集（已在 `.gitignore` 中排除）。

```bash
git add .
git commit -m "feat: 完成作业 01 创建 py 与 ipynb"
git push
```
