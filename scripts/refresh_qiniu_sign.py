import os, json, time, urllib.parse
from qiniu import Auth, BucketManager

AK = os.environ["QINIU_AK"]
SK = os.environ["QINIU_SK"]
BUCKET = os.environ.get("QINIU_BUCKET", "ucrm-files")
HOST = "tnsayp74s.hn-bkt.clouddn.com"

q = Auth(AK, SK)
bm = BucketManager(q)

keys = []
marker = ""
while True:
    res = bm.list(BUCKET, limit=1000, marker=marker)
    data = res[0] if isinstance(res, tuple) else res
    if not data:
        print("list 返回空:", res)
        break
    items = data.get("items", [])
    keys.extend([it["key"] for it in items])
    marker = data.get("marker")
    if not marker:
        break

deadline = int(time.time()) + 30 * 24 * 3600
m = {}
for k in keys:
    base = "http://" + HOST + "/" + urllib.parse.quote(k)
    m[k] = q.private_download_url(base, expires=deadline)

with open("qiniu_map.json", "w") as f:
    json.dump(m, f, ensure_ascii=False)

print(f"已生成 {len(m)} 条签名链接，有效期 30 天")
