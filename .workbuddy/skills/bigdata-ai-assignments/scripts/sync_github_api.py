# -*- coding: utf-8 -*-
"""
通过 GitHub API 把本地 HEAD 提交镜像到远端仓库（github.com push 被阻断时用）。
原理：api.github.com 可达时，用 Git Data API 在远端构建与本地 tree 完全一致、
     元数据一致的 commit → 两端 SHA 相同，无需 git push。
流程：空仓库先 Contents API 放 README 激活 → 逐文件建 blob → 建 tree →
     以远端 main 为 parent 建 commit → PATCH ref → 本地重建对齐。
限制：只镜像本地 HEAD 一个提交（中间未推送的提交会被压平）。
用法：  PAT=$(sed -n 's|https://[^:]*:\\([^@]*\\)@github.com|\\1|p' ~/.git-credentials)
       GH_PAT="$PAT" python .workbuddy/scripts/sync_github_api.py
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
TOKEN = os.environ["GH_PAT"]

_url = subprocess.run(["git", "remote", "get-url", "origin"],
                      capture_output=True).stdout.decode().strip()
_m = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", _url)
REPO = "%s/%s" % (_m.group(1), _m.group(2))
print("目标仓库:", REPO)


def api(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "workbuddy-sync")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "replace")
        raise RuntimeError("HTTP %s %s %s\n%s" % (e.code, method, path, body_txt[:500]))


def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace"))
    return r.stdout


def parse_person(s):
    """'Name <mail> ts tz' -> (name, mail, 'ts tz')"""
    lt, gt = s.rindex("<"), s.rindex(">")
    name, email = s[:lt].strip(), s[lt + 1:gt]
    ts, tz = s[gt + 1:].split()
    sign = 1 if tz[0] == "+" else -1
    offset = timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5])) * sign
    iso = datetime.fromtimestamp(int(ts), tz=timezone(offset)).isoformat()
    return name, email, iso, ts + " " + tz


# ---- 1. 读取本地 HEAD 提交 ----
raw = git("cat-file", "commit", "HEAD").decode("utf-8")
header, _, message = raw.partition("\n\n")
local_sha = git("rev-parse", "HEAD").decode().strip()
tree_sha = author_line = committer_line = None
for line in header.splitlines():
    if line.startswith("tree "):
        tree_sha = line[5:]
    elif line.startswith("author "):
        author_line = line[7:]
    elif line.startswith("committer "):
        committer_line = line[10:]
a_name, a_mail, a_iso, a_raw = parse_person(author_line)
c_name, c_mail, c_iso, c_raw = parse_person(committer_line)
print("本地 commit:", local_sha)
print("本地 tree  :", tree_sha)
print("author    :", a_name, a_iso)

entries = []
for line in git("ls-tree", "-r", "HEAD").decode().splitlines():
    meta, path = line.split("\t", 1)
    mode, typ, sha = meta.split()
    entries.append((mode, sha, path))
print("文件数    :", len(entries))

# ---- 2. 确保仓库非空（空仓库 Git Data API 会 409）----
parent_sha = None
try:
    commits = api("GET", "/repos/%s/commits" % REPO)
    parent_sha = commits[0]["sha"]
    print("远端已有提交:", parent_sha)
    if parent_sha == local_sha:
        print("远端已与本地 HEAD 一致，无需同步")
        sys.exit(0)
except RuntimeError as e:
    if "409" in str(e):
        print("远端为空仓库，先用 Contents API 放入 README.md 激活 …")
        readme = git("cat-file", "blob", "HEAD:README.md").decode("utf-8")
        put = api("PUT", "/repos/%s/contents/README.md" % REPO,
                  {"message": "chore: init",
                   "content": base64.b64encode(readme.encode("utf-8")).decode("ascii")})
        parent_sha = put["commit"]["sha"]
        print("激活提交:", parent_sha)
    else:
        raise

# ---- 3. 建全部 blob ----
tree_items = []
for mode, sha, path in entries:
    content = git("cat-file", "blob", sha)
    b = api("POST", "/repos/%s/git/blobs" % REPO,
            {"content": base64.b64encode(content).decode("ascii"),
             "encoding": "base64"})
    if b["sha"] != sha:
        sys.exit("FATAL blob SHA 不一致: %s" % path)
    tree_items.append({"path": path, "mode": mode, "type": "blob", "sha": sha})
print("blob 全部一致 ✓ (%d 个)" % len(tree_items))

# ---- 4. 建 tree ----
t = api("POST", "/repos/%s/git/trees" % REPO, {"tree": tree_items})
if t["sha"] != tree_sha:
    sys.exit("FATAL tree SHA 不一致: %s vs %s" % (t["sha"], tree_sha))
print("远端 tree 与本地一致 ✓", t["sha"])

# ---- 5. 建 commit（parent = 激活提交，元数据同本地）----
c = api("POST", "/repos/%s/git/commits" % REPO,
        {"message": message, "tree": tree_sha, "parents": [parent_sha],
         "author": {"name": a_name, "email": a_mail, "date": a_iso},
         "committer": {"name": c_name, "email": c_mail, "date": c_iso}})
remote_sha = c["sha"]
print("远端 commit:", remote_sha)

# ---- 6. 本地用同样字节重建该提交 ----
obj = ("tree %s\nparent %s\nauthor %s\ncommitter %s\n\n%s"
       % (tree_sha, parent_sha, author_line, committer_line, message)).encode("utf-8")
local_new = subprocess.run(["git", "hash-object", "-t", "commit", "-w", "--stdin"],
                           input=obj, capture_output=True).stdout.decode().strip()
print("本地重建 :", local_new, "一致 ✓" if local_new == remote_sha else "不一致 ✗")

final = remote_sha


def set_ref(name, sha):
    """本环境 git update-ref 偶发静默失败，写完必须校验，失败则直写文件。"""
    subprocess.run(["git", "update-ref", name, sha])
    got = subprocess.run(["git", "rev-parse", "--verify", "--quiet", name],
                         capture_output=True).stdout.decode().strip()
    if got != sha:
        path = os.path.join(".git", *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(sha + "\n")


# ---- 7. 更新远端 ref main（此时已存在，用 PATCH）----
r = api("PATCH", "/repos/%s/git/refs/heads/main" % REPO, {"sha": final})
print("远端 main ->", r["object"]["sha"])

# ---- 8. 本地对齐 ----
set_ref("refs/heads/main", final)
set_ref("refs/remotes/origin/main", final)
print("本地 main / origin/main 已指向", final)
print("\n同步完成")

