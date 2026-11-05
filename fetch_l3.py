#!/usr/bin/env python3
import imaplib, email, os
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

def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
                except: pass
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        import re
                        h = payload.decode(charset, errors="replace")
                        body = re.sub(r"<[^>]+>", " ", h)
                        break
                    except: pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
        except: body = str(msg.get_payload())
    return body.strip()

# L3Harris 最近5封全部列出
addr = "enriqueajrendon@l3harristechnologies.live"
M = imaplib.IMAP4_SSL(SERVER, PORT)
M.login(addr, PASSWORD)
M.select("INBOX")
typ, data = M.search(None, "ALL")
ids = data[0].split()
recent = ids[-5:]
for eid in recent:
    typ, msg_data = M.fetch(eid, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"\n{'='*60}")
    print(f"From: {decode_str(msg.get('From',''))}")
    print(f"Subject: {decode_str(msg.get('Subject',''))}")
    print(f"Date: {msg.get('Date','')}")
    body = get_body(msg)
    print(f"Body:\n{body[:3000]}")
    for part in msg.walk():
        fn = part.get_filename()
        if fn:
            print(f"ATTACHMENT: {decode_str(fn)}")
M.logout()
