# Customs-Bond 後端工程
# 技術棧：Python 3.10+ / FastAPI / PostgreSQL(Supabase) / IMAP+SMTP
# 啟動前先裝依賴：pip install -r requirements.txt

name: customs-bond-backend
description: Customs-Bond 內部業務管理系統後端
version: 1.0.0

環境變數（放 .env，勿提交到 git）:
  SUPABASE_URL=https://xlcyumbyqcwedqwpspzs.supabase.co
  SUPABASE_ANON_KEY=sb_publishable_FlQqq0Zg6PgO_bJ9FuLGWw_MdgpYpe5
  GITHUB_TOKEN=ghp_你的token
  GITHUB_REPO=uscrm26/bcd
  GIT_LOCAL_WORKDIR=/tmp/bond-dashboard
  MAIL_PASSWORD=123456
  ADMIN_USER=廖駿賢
  JWT_SECRET=請換成隨機長字串
