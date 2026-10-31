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

# ===== AI 自動三點解讀新信，寫回 emails.json 並寫入時間線 =====
import urllib.request
ARK_KEY = os.environ.get("ARK_KEY","")
AI_KEY = ARK_KEY or os.environ.get("OPENROUTER_KEY","")
USE_ARK = bool(ARK_KEY)
DATA_PATH = os.path.join(ROOT,"dbboard","data.json")
SENT_PATH = os.path.join(ROOT,"sent_log.json")
AI_SYS = "你是美國海關 continuous Customs Bond 業務的資深顧問。基於提供的客戶檔案與完整往來郵件歷史，對本次新收到的郵件做綜合分析。用繁體中文，分三段：\n【前後文定位】把新郵件放回整條往來線，說明進展到哪、雙方交換過什麼、卡在哪。\n【對方來意與訴求】這封信具體要什麼、拒絕什麼、要補什麼。\n【建議下一步】結合客戶檔案，給出具體可執行的回覆與準備事項。不用客套。"

def build_ctx(nm, data, all_emails, sent):
    cname = nm.get("client","")
    lines=[]
    cust = next((c for c in data.get("customers",[]) if c.get("name","")==cname or c.get("name","").startswith(cname)), None)
    if cust:
        lines.append("【客戶檔案】")
        lines.append(f"公司：{cust.get('name','')}｜法人：{cust.get('member','')}｜EIN：{cust.get('ein','—')}｜狀態：{cust.get('status','')}｜信箱：{cust.get('mail','—')}")
    else:
        lines.append(f"【客戶檔案】系統未建檔，客戶：{cname}")
    recv=[e for e in all_emails if e.get("client","")==cname]
    if recv:
        lines.append("【歷史收件】")
        for x in recv[-10:]:
            lines.append(f"- [{x.get('date','')}] {x.get('from','')}｜{x.get('subject','')}")
    broker_dom=(nm.get("from","").split("@")[1] or "").lower()
    cust_mail=(cust or {}).get("mail","")
    rel_sent=[s for s in sent if broker_dom and (s.get("to","").split("@")[1] or "").lower()==broker_dom] or [s for s in sent if cust_mail and s.get("from","").lower()==cust_mail.lower()]
    if rel_sent:
        lines.append("【我方過去寄出】")
        for s in rel_sent[-8:]:
            lines.append(f"- to: {s.get('to','')}｜{s.get('subject','')}｜{(s.get('body','') or '')[:150]}")
    return "\n".join(lines)

if AI_KEY and os.path.exists(DATA_PATH):
    try:
        data = json.load(open(DATA_PATH,encoding="utf-8"))
        tls = data.get("timeline",{})
        sent = json.load(open(SENT_PATH,encoding="utf-8")) if os.path.exists(SENT_PATH) else []
        for nm in new_here:
            ctx = build_ctx(nm, data, emails, sent)
            prompt = ctx + "\n\n【本次新郵件】\n寄件人："+nm["from"]+"\n主旨："+nm["subject"]+"\n正文：\n"+nm["body"][:1800]
            try:
                if USE_ARK:
                    ep="https://ark.cn-beijing.volces.com/api/v3/chat/completions"; mdl=os.environ.get("ARK_MODEL","doubao-pro-32k")
                else:
                    ep="https://openrouter.ai/api/v1/chat/completions"; mdl="google/gemma-4-31b-it:free"
                req = urllib.request.Request(ep,
                    data=json.dumps({"model":mdl,"messages":[{"role":"system","content":AI_SYS},{"role":"user","content":prompt}]}).encode(),
                    headers={"Authorization":"Bearer "+AI_KEY,"Content-Type":"application/json"})
                r = json.loads(urllib.request.urlopen(req,timeout=40).read())
                interp = r["choices"][0]["message"]["content"].strip()
            except Exception as e:
                interp = ""
                print(f"[AI FAIL] {nm['client']}: {e}")
            if interp:
                nm["auto_interp"] = interp
                tl_tx = interp.split("\n")[0].strip("【】 ")
                if len(tl_tx) > 80: tl_tx = tl_tx[:80] + "…"
            else:
                tl_tx = nm["subject"]
            tls.setdefault(nm["client"],[]).append({"e":"email","src":nm["from"],"tt":nm["subject"],"tm":datetime.datetime.now().strftime("%m/%d %H:%M"),"tx":tl_tx})
            print(f"[AI] {nm['client']}: {tl_tx[:80]}")
        data["timeline"] = tls
        json.dump(data,open(DATA_PATH,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    except Exception as e:
        print(f"[AI SKIP] {e}")
elif not AI_KEY:
    print("[AI SKIP] 未設定 ARK_KEY / OPENROUTER_KEY，新信僅入檔未解讀")

json.dump(emails, open(EMAILS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
ok = sum(1 for r in report if r["ok"])
print(f"[SUMMARY] 連線 {ok}/{len(report)}，新信 {new_count} 封")
for r in report:
    print(f"  - {r['client']}: {'ok' if r['ok'] else 'FAIL '+r['err']}, new={r['new']}")
