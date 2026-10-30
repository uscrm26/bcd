"""認證路由：登入 + JWT，基於既有 Supabase accounts 表"""
import datetime
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import config
from .. import supabase_client as db

router = APIRouter()


class LoginReq(BaseModel):
    username: str
    password: str


def create_token(account: dict) -> str:
    payload = {"sub": str(account["id"]), "username": account["display_name"],
               "role": account["role"], "exp": datetime.datetime.utcnow() +
               datetime.timedelta(hours=config.JWT_EXPIRE_HOURS)}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


@router.post("/login")
def login(req: LoginReq):
    # accounts 表以 display_name + pin 為登入依據
    users = db.select("accounts", query=f"display_name=eq.{req.username},active=eq.true")
    if not users:
        raise HTTPException(401, "帳號或密碼錯誤")
    u = users[0]
    if str(u.get("pin")) != str(req.password):
        raise HTTPException(401, "帳號或密碼錯誤")
    return {"token": create_token(u), "user": {
        "id": u["id"], "username": u["display_name"], "display_name": u["display_name"],
        "role": u.get("role", "operator")}}


@router.get("/me")
def me(auth: str = None):
    if not auth:
        raise HTTPException(401, "未登入")
    token = auth.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登入已過期")
    return {"id": payload["sub"], "username": payload["username"], "role": payload["role"]}
