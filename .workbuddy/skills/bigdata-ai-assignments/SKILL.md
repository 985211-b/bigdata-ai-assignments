---
name: bigdata-ai-assignments
description: 大数据 & AI 课程作业仓库（bigdata-ai-assignments）的作业完成与提交工作流。当需要在本仓库中新建/修改作业脚本或 Notebook、按课程作业截图搭建文件、运行 py 或 ipynb、把代码提交并推送到 GitHub 远程仓库时使用。包含目录与命名约定、Python 3.12 运行方式、无 Jupyter CLI 时执行 Notebook、以及 git push 被网络阻断时改用 GitHub API 镜像提交的完整流程。
agent_created: true
---

# 课程作业仓库工作流

## Overview

本 skill 面向 `bigdata-ai-assignments` 这一个仓库，把"按课程截图做作业 → 本地运行验证 → 推送到 GitHub"整条链路固定下来。仓库位于 WorkBuddy 工作区根目录，远端为 `https://github.com/985211-b/bigdata-ai-assignments`。

## 仓库约定

### 目录结构

```
bigdata-ai-assignments/
├── scripts/                  # 作业正文，第 N 次作业 = NN.py + NN.ipynb
├── notebooks/                # 临时实验 Notebook
├── data/  docs/  assignments/  concept-learning-materials/
├── README.md  requirements.txt  .gitignore  LICENSE
└── .workbuddy/               # 已 gitignore，不入库
```

### 命名与内容约定

- 第 N 次作业统一写作 `scripts/NN.py`、`scripts/NN.ipynb`（两位数，如 `01.py`）。
- 脚本顶部写中文文档字符串，注明运行命令与预期输出。
- 输出的提示语沿用课程给出的文案（如 `print('我也会写程序啦！')`），不要自创，便于与课程示例逐字比对。
- `.py` 与 `.ipynb` 内容保持一致：`.py` 给命令行运行，`.ipynb` 给逐格演示。
- 新增依赖写入 `requirements.txt`，不要只装在本地。
- 提交信息用 `feat: 课程作业 NN —— <一句话>` 的格式，正文用 `-` 列出改动文件。

## 环境

- 解释器统一用 **Python 3.12**：`py -3.12`。本机默认 `py` 已指向 3.14，务必显式指定版本。
- pip 已配置清华源（`%APPDATA%\pip\pip.ini`），装包直接 `py -3.12 -m pip install <pkg>`。
- Windows 终端中文乱码时，先设 `PYTHONIOENCODING=utf-8`。

## 工作流 A：新增 .py 作业并运行

1. 按课程截图确认文件名与预期输出文案。
2. 创建 `scripts/NN.py`，顶部写清运行命令与预期输出。
3. 在仓库根目录运行验证：

```bash
cd <仓库根目录>
PYTHONIOENCODING=utf-8 py -3.12 scripts/NN.py
```

4. 把实际输出与课程截图逐字比对，不一致先修脚本。

## 工作流 B：新增 / 更新 Notebook 并运行

本机**没有** `jupyter` CLI，必须用 skill 自带脚本原地执行，执行后输出会写回 `.ipynb`：

```bash
PYTHONIOENCODING=utf-8 py -3.12 \
  .workbuddy/skills/bigdata-ai-assignments/scripts/run_notebook.py scripts/NN.ipynb
```

脚本内部用 `nbclient` + `nbformat`：

```python
nb = nbformat.read(p, as_version=4)
NotebookClient(nb, timeout=300, kernel_name="python3").execute()
nbformat.write(nb, p)      # 会自动补全 cell id
nbformat.validate(nb)
```

要点：

- 必须在仓库根目录运行，kernel 的工作目录即当前目录。
- 新建 `.ipynb` 时手写 JSON 也要是 nbformat 4.5 结构（`cells` / `metadata.kernelspec` / `nbformat`），cell 缺 `id` 会被 `nbformat.write` 自动补上。
- 日志里 zmq Proactor 与 "Kernel running over TCP without encryption" 是无害警告，可忽略。
- 需要 `ipykernel`、`nbclient`，已在 `requirements.txt` 中声明。

## 工作流 C：提交并推送到 GitHub

### 前置：本地提交

```bash
git add -A
git commit -m "feat: 课程作业 NN —— <一句话>"
```

配置已是 `core.autocrlf=false`、`core.eol=lf`，不要改动。

### push 被阻断时的替代方案（本网络环境必用）

本网络对 github.com **上传方向不通**：`git push` 会静默挂起到超时（90~120s），但下载方向正常（`git fetch`、`git ls-remote` 可用）。因此改用 GitHub API 在云端重建同一提交：

```bash
PAT=$(sed -n 's|https://[^:]*:\([^@]*\)@github.com|\1|p' ~/.git-credentials)
GH_PAT="$PAT" PYTHONIOENCODING=utf-8 py -3.12 \
  .workbuddy/skills/bigdata-ai-assignments/scripts/sync_github_api.py
```

脚本做什么（幂等，可重复运行）：

1. 从 `git remote get-url origin` 解析仓库名；远端已与本地 HEAD 一致则直接退出。
2. `git ls-tree -r HEAD` 逐文件 `POST /git/blobs`，断言 blob SHA 与本地一致。
3. `POST /git/trees` 建整棵树，断言 tree SHA 一致。
4. 以远端 main 顶端为 parent，用本地 HEAD 的 author/committer/date/message `POST /git/commits` —— 结果 SHA 与本地完全相同。
5. `PATCH /git/refs/heads/main`，再把本地 `refs/remotes/origin/main` 对齐。

已知坑（脚本已处理，排查时留意）：

- 空仓库调 Git Data API 返回 **409**，需先用 Contents API `PUT contents/README.md` 激活。
- Contents API 的 `content` 字段**必须传 base64**，纯文本会 422。
- 本机 `git update-ref` 偶发静默失败（退出码 0 但引用未写入），必须 `rev-parse` 校验并直写 `.git/refs/...` 兜底。
- 脚本只镜像 HEAD 单个提交；若有多个未推送提交会被压平，故建议**一次作业一次提交**。
- 缺失远端父对象时用 `git fetch --refetch origin main` 补齐（fetch 方向可用）。

### 验证

```bash
git status -sb          # 应显示 up to date with 'origin/main'
git log --oneline --decorate
```

再用 API 核对远端提交与文件树：

```bash
curl -s -H "Authorization: token $PAT" \
  https://api.github.com/repos/985211-b/bigdata-ai-assignments/commits | head -40
```

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `python` 跑出来的版本不是 3.12 | 本机有三套解释器，改回 `py -3.12` |
| 脚本输出中文乱码 | 设 `PYTHONIOENCODING=utf-8` |
| `git push` 卡住无输出 | 正常，走上文 API 方案 |
| Notebook 打开看不到输出 | 用 `run_notebook.py` 执行一次，输出会写回文件 |
| 装包后 import 不到 | 确认包装在 `py -3.12` 同一解释器下 |

## 资源

- `scripts/run_notebook.py` —— 原地执行 `.ipynb` 并写回输出。
- `scripts/sync_github_api.py` —— push 被阻断时用 GitHub API 镜像本地 HEAD 提交。
