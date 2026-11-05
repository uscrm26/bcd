#!/usr/bin/env python3
import imaplib, json, os, socket
from email import policy
from email.parser import BytesParser
socket.setdefaulttimeout(20)

ROOT = os.path.dirname(os.path.abspath(__file__))
MB = json.load(open(os.path.join(ROOT, "mailboxes.json"), encoding="utf-8"))
HOST = MB["server"]["host"]; PORT = MB["server"]["imap_port"]
PWD = os.environ.get("MAIL_PWD", "123456")

total = 0
for box in MB["mailboxes"]:
    addr, client = box["email"], box["client"]
    try:
        M = imaplib.IMAP4_SSL(HOST, PORT, timeout=15)
        M.login(addr, PWD)
        typ, folders = M.list()
        folder_names = []
        for f in folders:
            if f:
                fname = f.decode() if isinstance(f, bytes) else str(f)
                folder_names.append(fname)

        sent_folder = None
        for fn in folder_names:
            if 'sent' in fn.lower():
                parts = fn.split(' "/" ')
                sent_folder = parts[-1].strip('"') if len(parts) > 1 else fn.strip('"')
                break

        if not sent_folder:
            print(f"\n{client}: no Sent folder. Folders: {[f.split(' "/" ')[-1].strip(chr(34)) for f in folder_names[:8]]}")
            M.logout()
            continue

        M.select(sent_folder, readonly=True)
        typ, data = M.search(None, "ALL")
        ids = data[0].split() if data and data[0] else []
        count = len(ids)
        total += count

        recent = []
        for i in ids[-8:]:
            typ, msgd = M.fetch(i, "(BODY.PEEK[HEADER.FIELDS (SUBJECT TO DATE)])")
            if msgd and msgd[0]:
                msg = BytesParser(policy=policy.default).parsebytes(msgd[0][1])
                subj = str(msg.get("Subject",""))[:55]
                date = str(msg.get("Date",""))[:28]
                recent.append(f"    {date} | {subj}")

        print(f"\n{client} ({addr}): {count} sent emails")
        for r in recent:
            print(r)
        M.logout()
    except Exception as e:
        print(f"\n{client}: ERROR - {e}")

print(f"\n=== TOTAL SENT: {total} ===")
