"""FastAPI 主程式入口"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .services import scheduler
from .routes import customers, misc_routes, auth

app = FastAPI(title="Customs-Bond 後端", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(customers.router, prefix="/api/customers")
app.include_router(misc_routes.mailboxes_router, prefix="/api/mailboxes")
app.include_router(misc_routes.queue_router, prefix="/api/queue")
app.include_router(misc_routes.github_router, prefix="/api/github")
app.include_router(misc_routes.finance_router, prefix="/api/finance")
app.include_router(misc_routes.archives_router, prefix="/api/archives")


@app.on_event("startup")
async def startup():
    _sched = scheduler.start_scheduler()
    _sched.start()


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "customs-bond-backend"}
