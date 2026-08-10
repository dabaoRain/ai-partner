# 应用入口：组装中间件与路由
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, health, sessions

app = FastAPI(title="AI Partner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
