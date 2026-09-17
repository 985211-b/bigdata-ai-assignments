#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原地执行 Jupyter Notebook（.ipynb）并把输出写回文件。

无需 jupyter / nbconvert CLI，仅依赖 nbclient + nbformat。

用法:
    py -3.12 run_notebook.py scripts/01.ipynb
    py -3.12 run_notebook.py scripts/01.ipynb --timeout 600

注意:
    - 必须在仓库根目录下运行，kernel 的工作目录即当前目录。
    - 执行成功后会打印每个代码单元格的输出摘要，便于核对。
"""
import os
import sys

import nbformat
from nbclient import NotebookClient


def summarize(nb):
    """打印代码单元格的输入与输出摘要。"""
    for i, cell in enumerate(nb.cells, 1):
        if cell.cell_type != "code":
            continue
        src = "".join(cell.source).strip().replace("\n", " ")
        print("  [cell %d] %s" % (i, src[:70]))
        outs = cell.get("outputs") or []
        if not outs:
            print("           -> (无输出)")
            continue
        for o in outs:
            if o.get("output_type") == "stream":
                text = "".join(o.get("text", "")).strip()
            elif o.get("output_type") in ("execute_result", "display_data"):
                text = "".join(o.get("data", {}).get("text/plain", [])).strip()
            elif o.get("output_type") == "error":
                text = "%s: %s" % (o.get("ename"), o.get("evalue"))
            else:
                continue
            print("           -> %s" % text.replace("\n", " | ")[:100])


def main(argv):
    if not argv:
        print(__doc__)
        return 1

    path = argv[0]
    timeout = 300
    if "--timeout" in argv:
        timeout = int(argv[argv.index("--timeout") + 1])

    if not os.path.isfile(path):
        print("找不到文件: %s" % path)
        return 1

    nb = nbformat.read(path, as_version=4)
    print("执行 %s (超时 %ds) ..." % (path, timeout))
    NotebookClient(nb, timeout=timeout, kernel_name="python3").execute()

    # nbformat.write 会顺带补全缺失的 cell id，避免 MissingIDFieldWarning
    nbformat.write(nb, path)
    nbformat.validate(nb)

    print("已写回输出:")
    summarize(nb)
    code_cells = sum(1 for c in nb.cells if c.cell_type == "code")
    print("完成: %d 个代码单元格，nbformat %d.%d"
          % (code_cells, nb.nbformat, nb.nbformat_minor))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
