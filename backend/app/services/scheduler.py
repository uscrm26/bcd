"""定時排程：郵件巡查 + 外發佇列消費 + GitHub 備份"""
import asyncio
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .. import config
from .. import supabase_client as db
from .mail import MailService
from .github import GitHubService


def bjnow():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))


async def poll_emails():
    """動態讀 mailbox 表，逐箱 IMAP 收信，寫入 email_inbound + 時間線"""
    boxes = db.select("mailbox", query="is_enabled=eq.true")
    new_count = 0
    for box in boxes:
        ms = MailService(box["email_address"], box.get("password_encrypted") or config.MAIL_PASSWORD)
        try:
            mails = ms.fetch_unseen()
        except Exception as e:
            db.insert("task_run_log", {"run_type": "schedule_auto", "run_start": bjnow().isoformat(),
                                       "mailbox_list": [box["email_address"]], "new_email_count": 0,
                                       "error_summary": str(e)})
            continue
        for m in mails:
            # 去重
            exists = db.select("email_inbound", query=f"raw_message_id=eq.{m['raw_message_id']}")
            if exists:
                continue
            rec = db.insert("email_inbound", {**m, "mailbox_id": box["id"], "receive_at": bjnow().isoformat()})
            new_count += 1
            # 寫時間線
            if rec:
                cid = db.select("customer_mailbox_rel", query=f"mailbox_id=eq.{box['id']}")
                customer_id = cid[0]["customer_id"] if cid else None
                db.insert("customer_timeline", {
                    "customer_id": customer_id, "event_source": "email_inbound",
                    "title": m.get("subject", "")[:80], "content": m.get("body_text", "")[:500],
                    "email_inbound_id": rec[0]["id"],
                })
    # 記錄日誌
    db.insert("task_run_log", {"run_type": "schedule_auto", "run_start": bjnow().isoformat(),
                               "mailbox_list": [b["email_address"] for b in boxes],
                               "new_email_count": new_count})
    return new_count


async def consume_outbox():
    """消費 mail_messages 表 pending_send，SMTP 寄出並更新狀態"""
    pending = db.select("mail_messages", query="status=eq.pending_send")
    for row in pending:
        box = db.select("mailbox", query=f"email_address=eq.{row['from_identity']}")
        pwd = box[0].get("password_encrypted") or config.MAIL_PASSWORD if box else config.MAIL_PASSWORD
        try:
            ms = MailService(row["from_identity"], pwd)
            ms.send(row["to_addr"], row.get("subject", ""), row["body"], row.get("note"))
            db.update("mail_messages", {"status": "sent", "sent_at": bjnow().isoformat()},
                      f"id=eq.{row['id']}")
        except Exception as e:
            db.update("mail_messages", {"status": "failed", "note": str(e)}, f"id=eq.{row['id']}")


async def json_backup():
    g = GitHubService()
    data = {
        "mailboxes": {"mailboxes": [{"email": b["email_address"], "client": b["display_name"]}
                                    for b in db.select("mailbox")]},
        "notes": db.select("sync_note", query="synced=eq.false"),
        "emails": db.select("email_inbound"),
    }
    ok, err = g.export_json_backup(data)
    if not ok:
        db.insert("system_notification", {"notify_type": "send_failure", "title": "GitHub 備份失敗",
                                          "content": err[:500]})


def start_scheduler():
    sched = AsyncIOScheduler(timezone="Asia/Shanghai")
    cfg = db.select("schedule_config")
    if not cfg:
        cfg = db.insert("schedule_config", {}) or [{}]
    c = cfg[0]
    dense = int(c.get("dense_interval_min", 60))
    idle = int(c.get("idle_interval_min", 180))
    sched.add_job(lambda: asyncio.create_task(poll_emails()), "interval", minutes=dense,
                  id="poll_dense")
    sched.add_job(lambda: asyncio.create_task(poll_emails()), "interval", minutes=idle,
                  id="poll_idle")
    sched.add_job(lambda: asyncio.create_task(consume_outbox()), "interval", minutes=1,
                  id="outbox")
    return sched
