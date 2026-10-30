"""GitHub 備份 + 客戶歸檔包服務"""
import os
import json
import subprocess
import zipfile
import datetime
from .. import config


def _git(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


class GitHubService:
    def __init__(self, workdir=None):
        self.workdir = workdir or config.GIT_LOCAL_WORKDIR
        self._ensure_clone()

    def _ensure_clone(self):
        if not os.path.isdir(os.path.join(self.workdir, ".git")):
            url = f"https://{config.GITHUB_TOKEN}@github.com/{config.GITHUB_REPO}.git"
            _git(["git", "clone", url, self.workdir], os.path.dirname(self.workdir))
            _git(["git", "config", "user.email", "kevinyama@local"], self.workdir)
            _git(["git", "config", "user.name", "kevinyama"], self.workdir)

    def export_json_backup(self, data: dict):
        """把 DB 導出為 mailboxes.json / notes.json / emails.json 並 push"""
        self._ensure_clone()
        _git(["git", "pull", "origin", "main"], self.workdir)
        for name, payload in data.items():
            path = os.path.join(self.workdir, f"{name}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        _git(["git", "add", "-A"], self.workdir)
        _git(["git", "commit", "-m", f"定時備份 {datetime.datetime.now():%Y-%m-%d %H:%M}"], self.workdir)
        r = _git(["git", "push", "origin", "main"], self.workdir)
        return r.returncode == 0, r.stderr

    def sync_file(self, local_path, repo_relative_path):
        """把單檔複製到工作副本並 push"""
        self._ensure_clone()
        _git(["git", "pull", "origin", "main"], self.workdir)
        dest = os.path.join(self.workdir, repo_relative_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["cp", local_path, dest], check=True)
        _git(["git", "add", "-A"], self.workdir)
        _git(["git", "commit", "-m", f"上傳 {os.path.basename(repo_relative_path)}"], self.workdir)
        r = _git(["git", "push", "origin", "main"], self.workdir)
        return r.returncode == 0, r.stderr


def build_archive(customer: dict, timeline: list, todos: list, documents: list, out_dir: str):
    """生成客戶完整 ZIP 歸檔包，內含檔案索引清單"""
    cust_no = customer.get("customer_no", "unknown")
    fname = f"{cust_no}-{customer.get('company_full_name', '')}-full-archive.zip"
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in fname)
    zpath = os.path.join(out_dir, safe)
    index_rows = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        # 摘要 md
        summary = f"# {customer.get('company_full_name')}\n\n"
        summary += f"客戶編號: {cust_no}\n法人: {customer.get('member_fullname')}\nEIN: {customer.get('ein')}\n"
        summary += f"狀態: {customer.get('business_status')}\n"
        z.writestr("00-客戶資訊摘要.md", summary)
        # 時間線 csv
        tl_csv = "時間,來源,標題,內容\n"
        for t in timeline:
            tl_csv += f"{t.get('created_at','')},{t.get('event_source','')},{t.get('title','')},{t.get('content','')}\n"
        z.writestr("02-時間線紀錄.csv", tl_csv)
        # 待辦 csv
        td_csv = "標題,截止,狀態\n"
        for t in todos:
            td_csv += f"{t.get('todo_title','')},{t.get('due_at','')},{'完成' if t.get('is_completed') else '未完成'}\n"
        z.writestr("03-待辦清單.csv", td_csv)
        # 附件
        for i, d in enumerate(documents, 1):
            ap = d.get("storage_path")
            if ap and os.path.exists(ap):
                z.write(ap, f"attachments/{d.get('file_name','file')}")
                index_rows.append([i, d.get("file_name"), d.get("source_type"), d.get("upload_at")])
        # 檔案索引清單
        idx = "|序號|檔案名稱|來源|上傳時間|\n|---|---|---|---|\n"
        for r_ in index_rows:
            idx += f"|{r_[0]}|{r_[1]}|{r_[2]}|{r_[3]}|\n"
        z.writestr("_檔案索引清單.md", idx)
    return zpath, safe
