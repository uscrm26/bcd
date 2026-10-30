#!/usr/bin/env python3
# 每小時 IMAP 巡查：逐戶連 mail.pony-it.com:993，拉新信，去重寫入 emails.json。
# 由定時任務觸發：python3 scripts/imap_patrol.py
import imaplib, json, os, re, sys, datetime, socket
from email import policy
from email.parser import BytesParser
socket.setdefaulttimeout(20)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MB = json.load(open(os.path.join(ROOT, "mailboxes.json"), encoding="utf-8"))
HOST = MB["server"]["host"]; PORT = MB["server"]["imap_port"]; PWD = "123456"
EMAILS_PATH = os.path.join(ROOT, "emails.json")
emails = json.load(open(EMAILS_PATH, encoding="utf-8"))

def fingerprint(m):
    return re.sub(r"\s+", "", (str(m.get("from") or "")+"|"+str(m.get("subject") or "")+"|"+str(m.get("date") or ""))).lower()

seen = {fingerprint(e) for e in emails}

def body_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try: return part.get_content().strip()
                except Exception: pass
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                try:
                    h = part.get_content()
                    return re.sub(r"<[^>]+>", " ", h)[:2000]
                except Exception: pass
        return ""
    try: return msg.get_content().strip()
    except Exception: return ""

new_count = 0
report = []
for box in MB["mailboxes"]:
    addr, client = box["email"], box["client"]
    rec = {"client": client, "ok": False, "new": 0, "err": ""}
    try:
        M = imaplib.IMAP4_SSL(HOST, PORT, timeout=15)
        M.login(addr, PWD)
        M.select("INBOX", readonly=True)
        typ, data = M.search(None, "UNSEEN")
        ids = data[0].split() if data and data[0] else []
        new_here = []
        for i in ids[-15:]:
            typ, msgd = M.fetch(i, "(BODY.PEEK[])")
            if not msgd or not msgd[0]: continue
            msg = BytesParser(policy=policy.default).parsebytes(msgd[0][1])
            rec_mail = {
                "client": client,
                "from": str(msg.get("From","")),
                "subject": str(msg.get("Subject","(無標題)")),
                "date": str(msg.get("Date","")),
                "body": body_text(msg)[:4000],
                "read": False
            }
            fp = fingerprint(rec_mail)
            if fp in seen: continue
            seen.add(fp)
            emails.append(rec_mail)
            new_here.append(rec_mail)
        M.logout()
        rec["ok"] = True
        rec["new"] = len(new_here)
        new_count += len(new_here)
        for nm in new_here:
            print(f"[NEW] {client} | {nm['from']} | {nm['subject']} | {nm['date']}")
    except Exception as e:
        rec["err"] = str(e)[:120]
        print(f"[FAIL] {client} {addr}: {rec['err']}")
    report.append(rec)

# ===== AI 自動分析新信，寫入時間線 =====
import urllib.request
AI_KEY = os.environ.get("OPENROUTER_KEY","")
DATA_PATH = os.path.join(ROOT,"dbboard","data.json")
if AI_KEY and os.path.exists(DATA_PATH):
    try:
        data = json.load(open(DATA_PATH,encoding="utf-8"))
        tls = data.get("timeline",{})
        for nm in new_here:
            prompt = "Summarize this email in one short Chinese sentence and what action is needed.\nFrom: "+nm["from"]+"\nSubject: "+nm["subject"]+"\nBody: "+nm["body"][:600]
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                    data=json.dumps({"model":"google/gemma-4-31b-it:free","messages":[{"role":"user","content":prompt}]}).encode(),
                    headers={"Authorization":"Bearer "+AI_KEY,"Content-Type":"application/json"})
                r = json.loads(urllib.request.urlopen(req,timeout=20).read())
                summary = r["choices"][0]["message"]["content"].strip()
            except Exception as e:
                summary = nm["subject"]
            tls.setdefault(nm["client"],[]).append({"e":"email","src":nm["from"],"tt":nm["subject"],"tm":datetime.datetime.now().strftime("%m/%d %H:%M"),"tx":summary})
            print(f"[AI] {nm['client']}: {summary[:80]}")
        data["timeline"] = tls
        json.dump(data,open(DATA_PATH,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    except Exception as e:
        print(f"[AI SKIP] {e}")

json.dump(emails, open(EMAILS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
ok = sum(1 for r in report if r["ok"])
print(f"[SUMMARY] 連線 {ok}/{len(report)}，新信 {new_count} 封")
for r in report:
    print(f"  - {r['client']}: {'ok' if r['ok'] else 'FAIL '+r['err']}, new={r['new']}")
