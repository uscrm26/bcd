"""IMAP 收信 + SMTP 外發服務"""
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from .. import config


def _decode(s):
    if not s:
        return ""
    out = []
    for part, enc in decode_header(s):
        out.append(part.decode(enc or "utf-8", "ignore") if isinstance(part, bytes) else part)
    return "".join(out)


class MailService:
    def __init__(self, email_address, password=None):
        self.email = email_address
        self.password = password or config.MAIL_PASSWORD

    # ---------- IMAP 收信 ----------
    def fetch_unseen(self):
        m = imaplib.IMAP4_SSL(config.MAIL_IMAP_HOST, config.MAIL_IMAP_PORT)
        m.login(self.email, self.password)
        m.select("INBOX")
        _, data = m.search(None, "UNSEEN")
        results = []
        for num in data[0].split():
            _, msg = m.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg[0][1])
            body = self._extract_body(msg)
            results.append({
                "from_addr": _decode(msg.get("From")),
                "from_name": _decode(msg.get("From")),
                "to_addr": self.email,
                "subject": _decode(msg.get("Subject")),
                "body_text": body,
                "receive_at": msg.get("Date"),
                "raw_message_id": msg.get("Message-ID") or f"{self.email}-{num}",
            })
        m.logout()
        return results

    @staticmethod
    def _extract_body(msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", "ignore")
                    except Exception:
                        continue
        else:
            try:
                return msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8", "ignore")
            except Exception:
                return msg.get_payload()
        return ""

    # ---------- SMTP 外發 ----------
    def send(self, to_addr, subject, body, note=None):
        msg = MIMEMultipart()
        msg["From"] = self.email
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        final_body = body
        if note:
            final_body = body + f"\n\n---\n附件註記: {note}"
        msg.attach(MIMEText(final_body, "plain", "utf-8"))
        with smtplib.SMTP(config.MAIL_SMTP_HOST, config.MAIL_SMTP_PORT) as s:
            s.starttls()
            s.login(self.email, self.password)
            s.send_message(msg)
        return True
