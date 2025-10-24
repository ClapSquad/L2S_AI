from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from app.api.health import healthcheck
from app.api.file import upload
from app.api.auth import register, login, logout, me
from app.config.environments import SECRET_KEY, SESSION_EXPIRE_TIME

application = FastAPI(
    title="SVSP FastAPI Service",
    description="Semantic Video Summarization Pipeline Backend API documentation",
    version="1.0.0"
)

application.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # FE dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

application.add_middleware(SessionMiddleware,
                           secret_key=SECRET_KEY,
                           max_age=SESSION_EXPIRE_TIME)

application.include_router(healthcheck.router)
application.include_router(upload.router)

application.include_router(register.router)
application.include_router(login.router)
application.include_router(logout.router)
application.include_router(me.router)


@application.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}
