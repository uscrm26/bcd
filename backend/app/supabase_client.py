"""Supabase REST 客戶端（純 REST，無需 SDK）"""
import httpx
from . import config

_HEADERS = {
    "apikey": config.SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {config.SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
}

BASE = f"{config.SUPABASE_URL}/rest/v1"


def _url(table: str) -> str:
    return f"{BASE}/{table}"


def select(table: str, query: str = "", order: str = None, limit: int = 1000):
    params = {"select": "*"}
    if query:
        params["or"] = f"({query})" if query.startswith("and") else query
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)
    r = httpx.get(_url(table), headers=_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def insert(table: str, payload: dict):
    r = httpx.post(_url(table), headers=_HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def update(table: str, payload: dict, query: str):
    """query 如 'id=eq.123'"""
    r = httpx.patch(_url(table), headers=_HEADERS, json=payload,
                    params=parse_query(query), timeout=30)
    r.raise_for_status()
    return r.json()


def parse_query(q: str) -> dict:
    """把 'col=eq.val&col2=eq.val2' 拆成 params"""
    out = {}
    for part in q.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def delete(table: str, query: str):
    r = httpx.delete(_url(table), headers=_HEADERS,
                     params=parse_query(query), timeout=30)
    r.raise_for_status()
    return True
