#!/usr/bin/env python3
"""Fetch specific unread emails from Immunora, Home Depot, L3Harris"""
import imaplib, email, os, json
from email.header import decode_header

SERVER = "mail.pony-it.com"
PORT = 993
PASSWORD = os.environ.get("MAIL_PWD", "")

MAILBOXES = [
    ("Immunora", "kashayisisramonaodom@immunora-bio.com"),
    ("Home Depot", "amjadbahmad@home-depot.live"),
    ("L3Harris", "enriqueajrendon@l3harristechnologies.live"),
]

def decode_str(s):
    if not s:
        return ""
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
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
                except:
                    pass
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
                    except:
                        pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
        except:
            body = str(msg.get_payload())
    return body.strip()

for name, addr in MAILBOXES:
    print(f"\n{'='*60}")
    print(f"=== {name} ({addr}) ===")
    print(f"{'='*60}")
    try:
        m = imaplib.IMAP4_SSL(SERVER, PORT)
        m.login(addr, PASSWORD)
        m.select("INBOX")
        # 搜未讀
        typ, data = m.search(None, "UNSEEN")
        ids = data[0].split()
        print(f"Unseen: {len(ids)}")
        for eid in ids:
            typ, msg_data = m.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            print(f"\n  From: {decode_str(msg.get('From',''))}")
            print(f"  To: {decode_str(msg.get('To',''))}")
            print(f"  Subject: {decode_str(msg.get('Subject',''))}")
            print(f"  Date: {msg.get('Date','')}")
            body = get_body(msg)
            print(f"  Body:\n{body[:2000]}")
            # 附件
            for part in msg.walk():
                fn = part.get_filename()
                if fn:
                    print(f"  Attachment: {decode_str(fn)} ({part.get('Content-Type','')})")
        m.logout()
    except Exception as e:
        print(f"  ERROR: {e}")

# 也看 L3Harris 最近所有郵件
print(f"\n{'='*60}")
print(f"=== L3Harris recent inbox ===")
print(f"{'='*60}")
try:
    m = imaplib.IMAP4_SSL(SERVER, PORT)
    m.login("enriqueajrendon@l3harristechnologies.live", PASSWORD)
    m.select("INBOX")
    typ, data = m.search(None, "ALL")
    ids = data[0].split()
    recent = ids[-5:] if len(ids) > 5 else ids
    for eid in recent:
        typ, msg_data = m.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        print(f"\n  From: {decode_str(msg.get('From',''))}")
        print(f"  Subject: {decode_str(msg.get('Subject',''))}")
        print(f"  Date: {msg.get('Date','')}")
    m.logout()
except Exception as e:
    print(f"  ERROR: {e}")
