#!/usr/bin/env python3
"""把 Supabase mail_messages 裡所有 sent 郵件批量 APPEND 到 IMAP Sent 資料夾"""
import imaplib, json, os, socket, urllib.request, email
from email.message import EmailMessage
socket.setdefaulttimeout(20)

SB_URL = "https://xlcyumbyqcwedqwpspzs.supabase.co"
SB_KEY = "sb_publishable_FlQqq0Zg6PgO_bJ9FuLGWw_MdgpYpe5"
HOST = "mail.pony-it.com"
PORT = 993
PWD = os.environ.get("MAIL_PWD", "123456")

# 1. 拿全部 sent 郵件
req = urllib.request.Request(
    f"{SB_URL}/rest/v1/mail_messages?select=id,from_identity,to_addr,subject,body,sent_at&status=eq.sent&order=id.asc",
    headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
)
rows = json.loads(urllib.request.urlopen(req, timeout=15).read())
print(f"From Supabase: {len(rows)} sent emails to backfill")

# 按 from_identity 分組
by_sender = {}
for r in rows:
    sender = r['from_identity']
    by_sender.setdefault(sender, []).append(r)

total_appended = 0
total_skipped = 0

for sender, emails in by_sender.items():
    print(f"\n--- {sender}: {len(emails)} emails ---")
    try:
        M = imaplib.IMAP4_SSL(HOST, PORT, timeout=15)
        M.login(sender, PWD)
        
        # 找 Sent 資料夾
        typ, folders = M.list()
        sent_folder = None
        for f in folders:
            fn = f.decode() if isinstance(f, bytes) else str(f)
            if 'sent' in fn.lower():
                parts = fn.split(' "/" ')
                sent_folder = parts[-1].strip('"') if len(parts) > 1 else fn.strip('"')
                break
        
        if not sent_folder:
            print(f"  No Sent folder, skipping")
            M.logout()
            continue
        
        # 先看 Sent 裡已有多少
        M.select(sent_folder, readonly=True)
        typ, data = M.search(None, "ALL")
        existing_ids = data[0].split() if data and data[0] else []
        existing_count = len(existing_ids)
        print(f"  Sent folder currently has {existing_count} emails")
        
        # APPEND 每封
        for e in emails:
            msg = EmailMessage()
            msg['From'] = sender
            msg['To'] = e['to_addr']
            msg['Subject'] = e.get('subject', '(no subject)')
            msg['Date'] = e.get('sent_at', '')
            msg.set_content(e.get('body', ''))
            
            try:
                M.append(sent_folder, '\\Seen', None, msg.as_bytes())
                total_appended += 1
            except Exception as append_err:
                print(f"  Append failed id={e['id']}: {append_err}")
                total_skipped += 1
        
        M.logout()
        print(f"  Appended {len(emails)} emails to {sent_folder}")
    except Exception as ex:
        print(f"  ERROR: {ex}")
        total_skipped += len(emails)

print(f"\n=== BACKFILL DONE: appended={total_appended}, skipped={total_skipped} ===")
