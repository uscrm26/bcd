#!/usr/bin/env python3
"""Backfill all Sent emails from 15 mailboxes into Supabase mail_messages."""
import imaplib, email, os, json, time, urllib.request
from email.header import decode_header
from email.utils import parsedate_to_datetime

SERVER = "mail.pony-it.com"
PORT = 993
PASSWORD = os.environ.get("MAIL_PWD", "")

SB_URL = "https://xlcyumbyqcwedqwpspzs.supabase.co"
SB_KEY = "sb_publishable_FlQqq0Zg6PgO_bJ9FuLGWw_MdgpYpe5"

MAILBOXES = [
    ("kashayisisramonaodom@immunora-bio.com", "Immunora"),
    ("horaciolsanchez@olivewareinc.com", "Oliveware"),
    ("christopherhodge@pebblehomeinc.com", "Pebblehome"),
    ("jaliarthomas@sagewareinc.com", "Sageware"),
    ("christianjgpunzalan@nervaqon.live", "Nervaqon"),
    ("amjadbahmad@home-depot.live", "Home Depot"),
    ("allysonbrennafankuchen@honeywellinternational.live", "Honeywell"),
    ("jessicakeyates@huntingtoningallsindustries.live", "Huntington"),
    ("amerdaujok@jeld-wenholding.live", "JELD-WEN"),
    ("ahmedmohamedali@kervalonix.live", "Kervalonix"),
    ("amantahiradam@kontoorbrands.live", "Kontoor"),
    ("enriqueajrendon@l3harristechnologies.live", "L3Harris"),
    ("adisushimelismulatu@laureateeducation.live", "Laureate"),
    ("jennieannmyers@leidosholdings.live", "Leidos"),
    ("coreymheaward@lennar.live", "Lennar"),
]

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
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    payload = part.get_payload(decode=True)
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
                except: pass
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html" and not part.get_filename():
                    try:
                        import re
                        h = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                        body = re.sub(r"<[^>]+>", " ", h)
                        break
                    except: pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        except: body = str(msg.get_payload())
    return body.strip()[:4000]

# 先查 Supabase 已有的 from+to+subject 組合，避免重複
req = urllib.request.Request(
    f"{SB_URL}/rest/v1/mail_messages?select=from_identity,to_addr,subject",
    headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
)
existing = json.loads(urllib.request.urlopen(req, timeout=15).read())
existing_keys = set()
for e in existing:
    key = (e['from_identity'].lower(), e['to_addr'].lower(), e['subject'][:80].lower())
    existing_keys.add(key)
print(f"Existing records in Supabase: {len(existing_keys)}")

total_new = 0
total_skip = 0

for addr, name in MAILBOXES:
    try:
        M = imaplib.IMAP4_SSL(SERVER, PORT)
        M.login(addr, PASSWORD)
        M.select("Sent")
        typ, data = M.search(None, "ALL")
        ids = data[0].split()
        print(f"\n{name}: {len(ids)} emails in Sent")
        
        new_count = 0
        for eid in ids:
            typ, msg_data = M.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            
            to_addr = decode_str(msg.get("To", "")).strip()
            # 提取 email 地址
            import re
            to_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', to_addr)
            if not to_match: continue
            to_addr = to_match.group(0).lower()
            
            subject = decode_str(msg.get("Subject", "")).strip()
            date_str = msg.get("Date", "")
            
            # 解析時間
            sent_at = None
            try:
                dt = parsedate_to_datetime(date_str)
                sent_at = dt.isoformat()
            except: pass
            
            body = get_body(msg)
            
            # 跳過自己發給自己的
            if to_addr == addr.lower(): continue
            
            key = (addr.lower(), to_addr, subject[:80].lower())
            if key in existing_keys:
                total_skip += 1
                continue
            
            # 插入 Supabase
            record = {
                "from_identity": addr,
                "to_addr": to_addr,
                "subject": subject,
                "body": body,
                "status": "sent",
                "client_name": name,
                "sender_account": "kevinyama",
                "sent_at": sent_at,
                "note": "Backfilled from IMAP Sent"
            }
            
            try:
                req2 = urllib.request.Request(
                    f"{SB_URL}/rest/v1/mail_messages",
                    data=json.dumps(record).encode(),
                    headers={
                        "apikey": SB_KEY,
                        "Authorization": f"Bearer {SB_KEY}",
                        "Content-Type": "application/json"
                    },
                    method="POST"
                )
                urllib.request.urlopen(req2, timeout=10)
                existing_keys.add(key)
                new_count += 1
                total_new += 1
            except Exception as e:
                print(f"  Error inserting: {e}")
            
            time.sleep(0.2)
        
        print(f"  New: {new_count}, skipped existing: {len(ids)-new_count}")
        M.logout()
    except Exception as e:
        print(f"{name}: ERROR - {e}")

print(f"\n=== DONE ===")
print(f"Total new records: {total_new}")
print(f"Total skipped (already in Supabase): {total_skip}")
