"""客戶路由：CRUD + 時間線 + 待辦 + 附件"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from .. import supabase_client as db

router = APIRouter()


class CustomerIn(BaseModel):
    customer_no: str
    company_full_name: str
    entity_type: str = "CA-LLC"
    sos_file_no: Optional[str] = None
    ein: Optional[str] = None
    member_fullname: Optional[str] = None
    member_ssn: Optional[str] = None
    member_dob: Optional[str] = None
    member_dl_expire: Optional[str] = None
    member_photo_url: Optional[str] = None
    business_status: str = "new_lead"


@router.get("")
def list_customers(q: str = ""):
    if q:
        return db.select("customer", query=f"company_full_name=ilike.*{q}*")
    return db.select("customer", order="customer_no.asc")


@router.get("/{cid}")
def get_customer(cid: int):
    rows = db.select("customer", query=f"id=eq.{cid}")
    if not rows:
        raise HTTPException(404, "客戶不存在")
    c = rows[0]
    c["timeline"] = db.select("customer_timeline", query=f"customer_id=eq.{cid}", order="created_at.desc")
    c["todos"] = db.select("customer_todo", query=f"customer_id=eq.{cid}")
    c["documents"] = db.select("customer_document", query=f"customer_id=eq.{cid}")
    c["finance"] = db.select("customer_finance", query=f"customer_id=eq.{cid}")
    c["quotes"] = db.select("quote_record", query=f"customer_id=eq.{cid}")
    return c


@router.post("")
def create_customer(body: CustomerIn):
    row = db.insert("customer", body.dict())
    db.insert("customer_timeline", {"customer_id": row[0]["id"], "event_source": "system_auto",
                                    "title": "客戶建立", "content": f"建立客戶 {body.company_full_name}"})
    return row[0]


@router.patch("/{cid}")
def update_customer(cid: int, body: CustomerIn):
    return db.update("customer", body.dict(), f"id=eq.{cid}")


@router.post("/{cid}/timeline")
def add_timeline(cid: int, title: str = Form(...), content: str = Form(""),
                 ai_zhtw: str = Form(""), ai_en: str = Form("")):
    return db.insert("customer_timeline", {
        "customer_id": cid, "event_source": "manual_note", "title": title,
        "content": content, "ai_content_zhtw": ai_zhtw or None, "ai_content_en": ai_en or None})


@router.post("/{cid}/todo")
def add_todo(cid: int, todo_title: str = Form(...), due_at: str = Form("")):
    return db.insert("customer_todo", {"customer_id": cid, "todo_title": todo_title,
                                       "due_at": due_at or None})


@router.post("/{cid}/documents")
async def upload_doc(cid: int, file: UploadFile = File(...),
                     doc_category: str = Form("other"),
                     want_github_backup: bool = Form(False),
                     note: str = Form("")):
    content = await file.read()
    path = f"data/{cid}/{file.filename}"
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    doc = db.insert("customer_document", {"customer_id": cid, "doc_category": doc_category,
                                          "file_name": file.filename, "storage_path": path,
                                          "source_type": "manual_upload",
                                          "want_github_backup": want_github_backup})[0]
    if note:
        db.insert("customer_timeline", {"customer_id": cid, "event_source": "document_upload",
                                        "title": f"上傳 {file.filename}", "content": note})
    return doc
