"""統一 schema 轉換器：把 SQL 建表語句自動對照到前端欄位命名。
本檔案用於文件化欄位對照，實際業務讀寫由 supabase_client 直接依欄位名操作。
"""
# 前端欄位名 ↔ 資料庫欄位名對照（命名統一用資料庫欄位名，無需轉換）
FIELD_ALIASES = {
    "customer_no": "customer_no",
    "company_full_name": "company_full_name",
    "member_fullname": "member_fullname",
    "member_photo_url": "member_photo_url",
    "business_status": "business_status",
    "ein": "ein",
    "member_dl_expire": "member_dl_expire",
}
