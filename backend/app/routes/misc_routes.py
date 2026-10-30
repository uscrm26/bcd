"""信箱、佇列、GitHub、財務、歸檔路由"""
from fastapi import APIRouter, HTTPException, Body
from .. import supabase_client as db
from ..services.mail import MailService
from ..services.github import GitHubService
from .. import config

# ===== 信箱 =====
mailboxes_router = APIRouter()


@mailboxes_router.get("")
def list_mailboxes():
    return db.select("mailbox")


@mailboxes_router.post("")
def add_mailbox(body: dict):
    return db.insert("mailbox", body)


@mailboxes_router.post("/{mid}/test")
def test_mailbox(mid: int):
    box = db.select("mailbox", query=f"id=eq.{mid}")
    if not box:
        raise HTTPException(404, "信箱不存在")
    try:
        ms = MailService(box[0]["email_address"], box[0].get("password_encrypted") or config.MAIL_PASSWORD)
        ms.fetch_unseen()
        db.update("mailbox", {"last_test_result": "success", "last_test_at": None}, f"id=eq.{mid}")
        return {"ok": True, "result": "success"}
    except Exception as e:
        db.update("mailbox", {"last_test_result": f"fail:{e}"}, f"id=eq.{mid}")
        return {"ok": False, "result": str(e)}


# ===== 佇列 =====
queue_router = APIRouter()


@queue_router.get("")
def list_queue(status: str = ""):
    if status:
        return db.select("mail_messages", query=f"status=eq.{status}")
    return db.select("mail_messages", order="created_at.desc")


@queue_router.post("")
def enqueue(body: dict):
    return db.insert("mail_messages", {**body, "status": "pending_send"})


@queue_router.post("/{mid}/retry")
def retry(mid: int):
    return db.update("mail_messages", {"status": "pending_send", "note": "手動重試"},
                     f"id=eq.{mid}")


# ===== GitHub =====
github_router = APIRouter()


@github_router.get("/config")
def get_cfg():
    rows = db.select("github_sync_config")
    return rows[0] if rows else {}


@github_router.post("/backup")
def full_backup():
    g = GitHubService()
    data = {"mailboxes": {"mailboxes": [{"email": b["email_address"], "client": b["display_name"]}
                                        for b in db.select("mailbox")]},
            "notes": db.select("sync_note"), "emails": db.select("email_inbound")}
    ok, err = g.export_json_backup(data)
    return {"ok": ok, "error": err}


# ===== 財務 =====
finance_router = APIRouter()


@finance_router.get("/{cid}")
def list_finance(cid: int):
    return {"finance": db.select("customer_finance", query=f"customer_id=eq.{cid}"),
            "quotes": db.select("quote_record", query=f"customer_id=eq.{cid}")}


@finance_router.post("/{cid}")
def add_finance(cid: int, body: dict = Body(...)):
    return db.insert("customer_finance", {"customer_id": cid, **body})


@finance_router.post("/{cid}/quotes")
def add_quote(cid: int, body: dict = Body(...)):
    return db.insert("quote_record", {"customer_id": cid, **body})


# ===== 歸檔包 =====
archives_router = APIRouter()


@archives_router.post("/{cid}/generate")
def generate_archive(cid: int):
    c = db.select("customer", query=f"id=eq.{cid}")
    if not c:
        raise HTTPException(404, "客戶不存在")
    timeline = db.select("customer_timeline", query=f"customer_id=eq.{cid}")
    todos = db.select("customer_todo", query=f"customer_id=eq.{cid}")
    docs = db.select("customer_document", query=f"customer_id=eq.{cid}")
    path, name = build_archive_local(c[0], timeline, todos, docs)
    rec = db.insert("customer_archive_record", {"customer_id": cid, "archive_file_name": name,
                                                "local_storage_path": path, "status": "completed",
                                                "completed_at": None})[0]
    return rec


def build_archive_local(c, tl, td, d):
    from ..services.github import build_archive
    return build_archive(c, tl, td, d, "data/archives")
