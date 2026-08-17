# -*- coding: utf-8 -*-
"""複数ファイルを1コミットでpushする（Vercelのデプロイが1回で済む）
使い方: GH_TOKEN=... python3 tools/deploy.py "コミットメッセージ" file1 file2 ...
パスはリポジトリルートからの相対パスで指定する。"""
import base64
import json
import os
import sys
import urllib.request

REPO = "taka-a1111/trip-plan"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(path, method="GET", data=None):
    token = os.environ["GH_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "trip-plan-deploy",
                 **({"Content-Type": "application/json"} if data else {})},
        data=json.dumps(data).encode() if data else None)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def deploy(message, files):
    ref = api(f"/repos/{REPO}/git/ref/heads/main")
    base_commit = ref["object"]["sha"]
    base_tree = api(f"/repos/{REPO}/git/commits/{base_commit}")["tree"]["sha"]
    tree_items = []
    for f in files:
        content = open(os.path.join(ROOT, f), "rb").read()
        blob = api(f"/repos/{REPO}/git/blobs", "POST",
                   {"content": base64.b64encode(content).decode(), "encoding": "base64"})
        tree_items.append({"path": f, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("blob:", f)
    tree = api(f"/repos/{REPO}/git/trees", "POST", {"base_tree": base_tree, "tree": tree_items})
    commit = api(f"/repos/{REPO}/git/commits", "POST",
                 {"message": message, "tree": tree["sha"], "parents": [base_commit]})
    api(f"/repos/{REPO}/git/refs/heads/main", "PATCH", {"sha": commit["sha"]})
    print("commit:", commit["sha"][:12], "->", message)


if __name__ == "__main__":
    deploy(sys.argv[1], sys.argv[2:])
