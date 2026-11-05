#!/usr/bin/env python3
"""Deep audit: list ALL folders and count emails in each, for every mailbox."""
import imaplib, os, json

SERVER = "mail.pony-it.com"
PORT = 993
PASSWORD = os.environ.get("MAIL_PWD", "")

MAILBOXES = [
    "kashayisisramonaodom@immunora-bio.com",
    "horaciolsanchez@olivewareinc.com",
    "christopherhodge@pebblehomeinc.com",
    "jaliarthomas@sagewareinc.com",
    "christianjgpunzalan@nervaqon.live",
    "amjadbahmad@home-depot.live",
    "allysonbrennafankuchen@honeywellinternational.live",
    "jessicakeyates@huntingtoningallsindustries.live",
    "amerdaujok@jeld-wenholding.live",
    "ahmedmohamedali@kervalonix.live",
    "amantahiradam@kontoorbrands.live",
    "enriqueajrendon@l3harristechnologies.live",
    "adisushimelismulatu@laureateeducation.live",
    "jennieannmyers@leidosholdings.live",
    "coreymheaward@lennar.live",
]

for addr in MAILBOXES:
    name = addr.split("@")[0][:12]
    try:
        M = imaplib.IMAP4_SSL(SERVER, PORT)
        M.login(addr, PASSWORD)
        typ, folders = M.list()
        print(f"\n=== {addr} ===")
        for f in folders:
            fname = f.decode().split('"/"')[-1].strip().strip('"')
            M.select(fname, readonly=True)
            typ, data = M.search(None, "ALL")
            count = len(data[0].split())
            print(f"  {fname:30s}: {count:4d} emails")
        M.logout()
    except Exception as e:
        print(f"\n{addr}: ERROR - {e}")
