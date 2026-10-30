#!/usr/bin/env python3
import json,time,random,smtplib
from email.mime.text import MIMEText
from email.header import Header

plan=json.load(open('/tmp/outreach_plan.json'))
clients=plan['clients']; assign=plan['assign']

def make_body(c,broker_short):
    contact=c['contact']
    company=c['name']
    templates=[
      f"We're setting up importing under {company} and need a continuous bond. Can you help? We'd need it active within a week. Please send what you need from us.",
      f"Looking for a continuous bond broker for {company}. We have regular entries starting next month. What documents do you require and how fast can you activate?",
      f"We're a new importer under {company} and need a continuous customs bond. Could you send over what you need from us and your pricing?",
      f"{company} needs a continuous customs bond activated before our first entry. We're comparing brokers right now. What's your rate and fastest turnaround?",
      f"We've been referred and wanted to reach out directly about a continuous bond for {company}. Can you quote and tell us your typical processing time?",
      f"New LLC here. We just got our EIN and are ready to apply for a continuous customs bond. Walk us through the process and give us your best rate.",
      f"We need to set up a continuous bond for {company}. We have our EIN and importer number ready. What's your fastest activation?",
      f"I'm exploring options for a continuous customs bond for {company}. We're a small operation and want straightforward pricing. Can you send a quote?",
      f"{company} is preparing for our first overseas shipment. We need a continuous bond in place before the cargo arrives. How quickly can you process?",
      f"We're setting up {company} for ongoing imports and would like a quote on a continuous bond. Please include your required application forms.",
      f"We're looking to get a continuous bond approved fast. If {broker_short} can turn it around in under a week, we'd like to move forward. What's the first step?",
      f"We're switching our bond broker. {company} imports regularly and is looking for better service. Can you quote continuous bond coverage?",
      f"We're comparing continuous bond brokers for {company}. What makes your service stand out and what documents do you need from us?",
      f"Quick inquiry: we need a continuous customs bond for {company}. Can you send over your requirements and rate? We're ready to move this week.",
      f"We're a first-time importer and need a continuous bond. Can you handle the full setup for {company}? What do you need from us to get started?",
    ]
    return random.choice(templates)

def short_name(full):
    # Bosch Customs Brokerage, Inc. -> Bosch Customs Brokerage
    return re.sub(r',?\s+(inc|llc|ltd|co|corp|company|services|international|brokerage).*$','',full,flags=re.I).strip()

import re
HOST="mail.pony-it.com"; PORT=587; PWD="123456"
sent_log=[]
sent_ok=0
for round_i in range(15):
    for c in clients:
        mail=c['mail']
        brokers=assign[mail]
        if round_i>=len(brokers): continue
        b=brokers[round_i]
        to=b['m'].strip()
        bs=short_name(b['n'])
        body=f"Hi {bs} team,\n\n{make_body(c,bs)}\n\nBest regards,\n{c['contact']}\n{c['name']}\n{mail}"
        subj_options=["Continuous Customs Bond Inquiry","Continuous Bond Quote Needed","Looking for a Customs Bond Broker","New Importer Continuous Bond Setup","Customs Bond Services Request"]
        subj=random.choice(subj_options)
        msg=MIMEText(body,'plain','utf-8')
        msg['From']=mail; msg['To']=to; msg['Subject']=Header(subj,'utf-8')
        try:
            s=smtplib.SMTP(HOST,PORT,timeout=20)
            s.starttls(); s.login(mail,PWD)
            s.sendmail(mail,[to],msg.as_string())
            s.quit()
            print(f"[OK] r{round_i+1} {mail[:30]} -> {to}")
            sent_log.append({"from":mail,"to":to,"subject":subj,"body":body,"round":round_i+1,"broker":b['n']})
            sent_ok+=1
        except Exception as e:
            print(f"[FAIL] {mail} -> {to}: {e}")
        time.sleep(2)
json.dump(sent_log,open('/tmp/bond-dashboard/sent_log.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(f"\n=== 完成 {sent_ok}/105 ===")
