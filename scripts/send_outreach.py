#!/usr/bin/env python3
# 23:00 单发开发信 runner：逐封单发、无Cc/Bcc、随机间隔40-90秒，两邮箱分组。
# 由定时任务触发时在仓库根目录执行：python3 scripts/send_outreach.py
import smtplib, ssl, json, time, random, os, sys
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

HOST="mail.pony-it.com"; PORT=587; PWD="123456"
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT=os.path.join(ROOT,"docs/outreach/outreach_draft.json")
LOG=os.path.join(ROOT,"docs/outreach/send_log.json")

def send_one(user,to,subject,body,name=None):
    msg=MIMEText(body,"plain","utf-8")
    msg["Subject"]=subject
    msg["From"]=formataddr((name or "",user))
    msg["To"]=to
    msg["Date"]=formatdate(localtime=True)
    ctx=ssl.create_default_context()
    with smtplib.SMTP(HOST,PORT,timeout=30) as s:
        s.ehlo(); s.starttls(context=ctx); s.ehlo()
        s.login(user,PWD)
        s.sendmail(user,[to],msg.as_string())

def main():
    d=json.load(open(DRAFT,encoding="utf-8"))
    log=[]
    for grp in ["pebblehome","nervaqon"]:
        cfg=d[grp]; user=cfg["from"]; name=cfg.get("signature","").split("\n")[0]
        for i,m in enumerate(cfg["mails"]):
            rec={"group":grp,"to":m["to"],"company":m.get("company"),"subject":m["subject"]}
            try:
                send_one(user,m["to"],m["subject"],m["body"],name=name)
                rec["status"]="sent"
                print("SENT",grp,i+1,m["to"],"|",m["subject"])
            except Exception as e:
                rec["status"]="failed"; rec["error"]=str(e)
                print("FAIL",grp,i+1,m["to"],e)
            log.append(rec)
            json.dump(log,open(LOG,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
            if i!=len(cfg["mails"])-1:
                time.sleep(random.randint(40,90))
    sent=sum(1 for r in log if r["status"]=="sent")
    print(f"DONE sent={sent}/{len(log)}")

if __name__=="__main__":
    main()
