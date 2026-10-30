"""應用配置"""
import os
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xlcyumbyqcwedqwpspzs.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_FlQqq0Zg6PgO_bJ9FuLGWw_MdgpYpe5")

MAIL_IMAP_HOST = os.getenv("MAIL_IMAP_HOST", "mail.pony-it.com")
MAIL_IMAP_PORT = int(os.getenv("MAIL_IMAP_PORT", "993"))
MAIL_SMTP_HOST = os.getenv("MAIL_SMTP_HOST", "mail.pony-it.com")
MAIL_SMTP_PORT = int(os.getenv("MAIL_SMTP_PORT", "587"))
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "123456")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "uscrm26/bcd")
GIT_LOCAL_WORKDIR = os.getenv("GIT_LOCAL_WORKDIR", "/tmp/bond-dashboard")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-to-random")
JWT_EXPIRE_HOURS = 24
