import os, json, time, urllib.parse

AK = os.environ["QINIU_AK"]
SK = os.environ["QINIU_SK"]
BUCKET = os.environ.get("QINIU_BUCKET", "ucrm-files")
HOST = "tnsayp74s.hn-bkt.clouddn.com"
BODY = os.environ.get("ISSUE_BODY", "")

from qiniu import Auth
q = Auth(AK, SK)

# 解析 body：优先 JSON，兼容裸 key 行
meta = None
keys = []
try:
    parsed = json.loads(BODY)
    if isinstance(parsed, dict):
        meta = parsed
        k = parsed.get("key")
        if k:
            keys.append(k)
    elif isinstance(parsed, list):
        keys = [x for x in parsed if isinstance(x, str)]
except Exception:
    for line in BODY.splitlines():
        line = line.strip()
        if line and not line.startswith("{"):
            keys.append(line)

if not keys:
    print("沒有可簽名的 key，body:", BODY[:200])
    raise SystemExit(0)

# 合并签名
try:
    with open("qiniu_map.json", encoding="utf-8") as f:
        m = json.load(f)
except Exception:
    m = {}

deadline = int(time.time()) + 30 * 24 * 3600
added = []
for k in keys:
    if k in m:
        continue
    base = "http://" + HOST + "/" + urllib.parse.quote(k)
    m[k] = q.private_download_url(base, expires=deadline)
    added.append(k)

with open("qiniu_map.json", "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False)
print(f"補簽名 {len(added)} 個 key，map 總數 {len(m)}")

# 若带客户编号，同步写 files.json
if meta and meta.get("no"):
    no = str(meta["no"])
    name = meta.get("name", os.path.basename(meta.get("key", "file")))
    key = meta.get("key", "")
    try:
        with open("files.json", encoding="utf-8") as f:
            files = json.load(f)
    except Exception:
        files = {}
    arr = files.get(no, [])
    if not any(x.get("path") == urllib.parse.quote(key) for x in arr):
        ext = os.path.splitext(name)[1].lower()
        ftype = "image" if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif") else ("pdf" if ext == ".pdf" else ("text" if ext == ".txt" else "file"))
        arr.insert(0, {"name": name, "path": urllib.parse.quote(key), "type": ftype})
        files[no] = arr
        with open("files.json", "w", encoding="utf-8") as f:
            json.dump(files, f, ensure_ascii=False)
        print(f"files.json 已加入 #{no} / {name}")
