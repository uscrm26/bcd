#!/usr/bin/env python3
import imaplib, email, os, re
from email.header import decode_header

SERVER = "mail.pony-it.com"
PORT = 993
PASSWORD = os.environ.get("MAIL_PWD", "")

def decode_str(s):
    if not s: return ""
    parts = decode_header(s)
    result = ""
    for data, charset in parts:
        if isinstance(data, bytes):
            result += data.decode(charset or "utf-8", errors="replace")
        else:
            result += data
    return result

addr = "enriqueajrendon@l3harristechnologies.live"
M = imaplib.IMAP4_SSL(SERVER, PORT)
M.login(addr, PASSWORD)
M.select("INBOX")
typ, data = M.search(None, "ALL")
ids = data[0].split()
# 只取最後兩封
for eid in ids[-2:]:
    typ, msg_data = M.fetch(eid, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"START_MAIL")
    print(f"From: {decode_str(msg.get('From',''))}")
    print(f"Subject: {decode_str(msg.get('Subject',''))}")
    print(f"Date: {msg.get('Date','')}")
    # 抓純文字
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not part.get_filename():
                try:
                    payload = part.get_payload(decode=True)
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
                except: pass
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html" and not part.get_filename():
                    try:
                        h = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                        body = re.sub(r"<[^>]+>", " ", h)
                        break
                    except: pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        except: body = str(msg.get_payload())
    print(f"BODY_START")
    print(body[:3000])
    print(f"BODY_END")
    print(f"END_MAIL")
M.logout()
