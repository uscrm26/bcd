# 資料庫完整結構：PostgreSQL，相容 Supabase
# 繼承 B2 全部既有表，追加財務、管理員帳戶管理相關表

-- ========== 既有業務表 ==========

-- i18n_text 系統UI介面翻譯字典
CREATE TABLE IF NOT EXISTS i18n_text (
  id bigserial PRIMARY KEY,
  key text NOT NULL UNIQUE,
  lang_zh_tw text NOT NULL,
  lang_en text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- admin_user 管理員帳號
CREATE TABLE IF NOT EXISTS admin_user (
  id bigserial PRIMARY KEY,
  username text NOT NULL UNIQUE,
  display_name text NOT NULL,
  password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('super_admin','operator')),
  ui_prefer_lang text NOT NULL DEFAULT 'zh_tw' CHECK (ui_prefer_lang IN ('zh_tw','en','zh_cn')),
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  last_login timestamptz NULL
);

-- mailbox 信箱帳號配置
CREATE TABLE IF NOT EXISTS mailbox (
  id bigserial PRIMARY KEY,
  display_name text NOT NULL,
  email_address text NOT NULL UNIQUE,
  imap_host text NOT NULL,
  imap_port integer NOT NULL DEFAULT 993,
  imap_ssl boolean DEFAULT true,
  smtp_host text NOT NULL,
  smtp_port integer NOT NULL DEFAULT 587,
  smtp_starttls boolean DEFAULT true,
  password_encrypted text NOT NULL,
  is_enabled boolean DEFAULT true,
  last_test_at timestamptz NULL,
  last_test_result text NULL,
  remark text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- schedule_config 定時任務排程
CREATE TABLE IF NOT EXISTS schedule_config (
  id bigserial PRIMARY KEY,
  dense_window_start time NOT NULL DEFAULT '22:00',
  dense_window_end time NOT NULL DEFAULT '03:00',
  dense_interval_min integer NOT NULL DEFAULT 60,
  idle_interval_min integer NOT NULL DEFAULT 180,
  daily_reminder_enable boolean DEFAULT true,
  daily_reminder_trigger_time time NOT NULL DEFAULT '10:00',
  day_cutoff_hour integer DEFAULT 5,
  enable_traditional_to_simplified boolean DEFAULT true,
  updated_at timestamptz DEFAULT now()
);

-- customer 客戶主檔案
CREATE TABLE IF NOT EXISTS customer (
  id bigserial PRIMARY KEY,
  customer_no text NOT NULL UNIQUE,
  company_full_name text NOT NULL,
  entity_type text NOT NULL,
  sos_file_no text NULL,
  ein text NULL,
  register_date date NULL,
  approve_date date NULL,
  physical_address text NULL,
  mailing_address text NULL,
  est_12month_fob numeric(14,2) NULL,
  has_antidumping boolean DEFAULT false,
  member_fullname text NULL,
  member_ssn text NULL,
  member_dob date NULL,
  member_residence_address text NULL,
  member_dl_number text NULL,
  member_dl_expire date NULL,
  member_marital text CHECK(member_marital IN ('single','married_joint','married_not_joint')) NULL,
  member_photo_url text NULL,
  business_status text NOT NULL DEFAULT 'new_lead',
  remark text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 客戶與信箱多對多
CREATE TABLE IF NOT EXISTS customer_mailbox_rel (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  mailbox_id bigint REFERENCES mailbox(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(customer_id, mailbox_id)
);

-- HTS 編碼一對多
CREATE TABLE IF NOT EXISTS hts_item (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  hts_code text NOT NULL,
  product_desc text NULL,
  origin_country text NULL,
  created_at timestamptz DEFAULT now()
);

-- inbound 收件郵件
CREATE TABLE IF NOT EXISTS email_inbound (
  id bigserial PRIMARY KEY,
  mailbox_id bigint REFERENCES mailbox(id),
  from_addr text NOT NULL,
  from_name text NULL,
  to_addr text NOT NULL,
  subject text NULL,
  body_text text NULL,
  body_html text NULL,
  receive_at timestamptz NOT NULL,
  customer_id bigint REFERENCES customer(id) ON DELETE SET NULL,
  is_unread boolean DEFAULT true,
  ai_business_type text NULL,
  raw_message_id text UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- 郵件附件
CREATE TABLE IF NOT EXISTS email_attachment (
  id bigserial PRIMARY KEY,
  email_inbound_id bigint REFERENCES email_inbound(id) ON DELETE CASCADE,
  file_name text NOT NULL,
  storage_path text NOT NULL,
  file_size bigint,
  mime_type text,
  created_at timestamptz DEFAULT now()
);

-- mail_messages 外發郵件佇列
CREATE TABLE IF NOT EXISTS mail_messages (
  id bigserial PRIMARY KEY,
  from_identity text NOT NULL,
  to_addr text NOT NULL,
  subject text NULL,
  ai_content_zhtw text NULL,
  ai_content_en text NULL,
  body text NOT NULL,
  note text NULL,
  status text NOT NULL CHECK(status IN ('pending_send','sent','failed')),
  created_at timestamptz DEFAULT now(),
  sent_at timestamptz NULL,
  relate_customer_id bigint REFERENCES customer(id) ON DELETE SET NULL
);

-- 客戶時間線
CREATE TABLE IF NOT EXISTS customer_timeline (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  event_source text NOT NULL CHECK(event_source IN ('email_inbound','manual_note','system_auto','document_upload','email_outbound')),
  title text NOT NULL,
  content text NULL,
  ai_content_zhtw text NULL,
  ai_content_en text NULL,
  email_inbound_id bigint REFERENCES email_inbound(id) ON DELETE SET NULL,
  mail_message_id bigint REFERENCES mail_messages(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now()
);

-- 客戶待辦
CREATE TABLE IF NOT EXISTS customer_todo (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  todo_title text NOT NULL,
  due_at timestamptz NULL,
  is_completed boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz NULL
);

-- 客戶附件文件庫
CREATE TABLE IF NOT EXISTS customer_document (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  doc_category text CHECK(doc_category IN ('ein','article','id_card','bond_application','financial_statement','broker_attachment','other')),
  file_name text NOT NULL,
  storage_path text NOT NULL,
  source_type text CHECK(source_type IN ('mail_attachment','manual_upload')),
  email_attachment_id bigint REFERENCES email_attachment(id) ON DELETE SET NULL,
  want_github_backup boolean DEFAULT false,
  upload_at timestamptz DEFAULT now()
);

-- sync_note 待同步備註
CREATE TABLE IF NOT EXISTS sync_note (
  id bigserial PRIMARY KEY,
  content text NOT NULL,
  synced boolean DEFAULT false,
  relate_customer_id bigint REFERENCES customer(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  synced_at timestamptz NULL
);

-- task_run_log 巡檢日誌
CREATE TABLE IF NOT EXISTS task_run_log (
  id bigserial PRIMARY KEY,
  run_type text CHECK(run_type IN ('schedule_auto','manual_trigger')),
  run_start timestamptz NOT NULL,
  mailbox_list text[] NOT NULL,
  new_email_count integer NOT NULL DEFAULT 0,
  outbound_total integer NOT NULL DEFAULT 0,
  outbound_success integer NOT NULL DEFAULT 0,
  outbound_failed integer NOT NULL DEFAULT 0,
  error_summary text NULL,
  created_at timestamptz DEFAULT now()
);

-- system_notification 系統通知
CREATE TABLE IF NOT EXISTS system_notification (
  id bigserial PRIMARY KEY,
  notify_type text NOT NULL,
  title text NOT NULL,
  content text NULL,
  relate_customer_id bigint REFERENCES customer(id) ON DELETE SET NULL,
  relate_email_id bigint REFERENCES email_inbound(id) ON DELETE SET NULL,
  is_read boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

-- ai_form_cache AI 表單生成暫存
CREATE TABLE IF NOT EXISTS ai_form_cache (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  form_type text NOT NULL CHECK(form_type IN ('personal_financial','bond_application')),
  ai_content_zhtw text NULL,
  ai_content_en text NULL,
  form_json text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- ========== GitHub 備份表 ==========
CREATE TABLE IF NOT EXISTS github_sync_config (
  id bigserial PRIMARY KEY,
  repo_path text NOT NULL DEFAULT 'uscrm26/bcd',
  auto_json_backup_enable boolean DEFAULT false,
  auto_json_backup_interval_min integer DEFAULT 240,
  git_local_workdir text NOT NULL,
  last_full_json_sync_at timestamptz NULL,
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS github_file_sync_record (
  id bigserial PRIMARY KEY,
  customer_document_id bigint REFERENCES customer_document(id) ON DELETE CASCADE,
  customer_id bigint REFERENCES customer(id) ON DELETE SET NULL,
  local_storage_path text NOT NULL,
  github_repo_relative_path text NOT NULL,
  sync_status text NOT NULL CHECK(sync_status IN ('not_sync','synced','sync_failed')),
  last_sync_at timestamptz NULL,
  last_commit_hash text NULL,
  error_msg text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS github_sync_log (
  id bigserial PRIMARY KEY,
  trigger_source text NOT NULL CHECK(trigger_source IN ('manual','schedule','file_upload')),
  action_desc text NOT NULL,
  commit_sha text NULL,
  is_success boolean NOT NULL,
  error_detail text NULL,
  created_at timestamptz DEFAULT now()
);

-- ========== 歸檔包表 ==========
CREATE TABLE IF NOT EXISTS customer_archive_record (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  archive_file_name text NOT NULL,
  local_storage_path text NOT NULL,
  include_basic_info boolean DEFAULT true,
  include_timeline boolean DEFAULT true,
  include_todo boolean DEFAULT true,
  include_attachments boolean DEFAULT true,
  want_github_backup boolean DEFAULT false,
  github_sync_record_id bigint REFERENCES github_file_sync_record(id) ON DELETE SET NULL,
  generated_by_admin_user_id bigint REFERENCES admin_user(id),
  status text NOT NULL CHECK(status IN ('generating','completed','failed')),
  error_msg text NULL,
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz NULL
);

-- ========== 新增：財務與費用模組 ==========
-- 客戶費用 / 收款記錄：Bond 保費、申請費、付款狀態
CREATE TABLE IF NOT EXISTS customer_finance (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  finance_type text NOT NULL CHECK(finance_type IN ('bond_premium','application_fee','other')),
  description text NULL,
  amount numeric(14,2) NOT NULL,
  currency text NOT NULL DEFAULT 'USD',
  invoice_no text NULL,
  due_at date NULL,
  payment_status text NOT NULL DEFAULT 'unpaid' CHECK(payment_status IN ('unpaid','partial','paid')),
  paid_amount numeric(14,2) NOT NULL DEFAULT 0,
  paid_at timestamptz NULL,
  payment_method text NULL,
  ai_content_zhtw text NULL,
  ai_content_en text NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 報價記錄：Broker 給的報價
CREATE TABLE IF NOT EXISTS quote_record (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  broker_name text NULL,
  bond_type text NULL,
  quote_amount numeric(14,2) NULL,
  currency text NOT NULL DEFAULT 'USD',
  quote_date date NULL,
  valid_until date NULL,
  status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','declined','expired')),
  note text NULL,
  email_inbound_id bigint REFERENCES email_inbound(id) ON DELETE SET NULL,
  ai_content_zhtw text NULL,
  ai_content_en text NULL,
  created_at timestamptz DEFAULT now()
);

-- 客戶權限：指定客戶給哪個管理員/操作員負責
CREATE TABLE IF NOT EXISTS customer_ownership (
  id bigserial PRIMARY KEY,
  customer_id bigint REFERENCES customer(id) ON DELETE CASCADE,
  admin_user_id bigint REFERENCES admin_user(id) ON DELETE CASCADE,
  is_owner boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  UNIQUE(customer_id, admin_user_id)
);
