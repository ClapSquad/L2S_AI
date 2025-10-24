from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from app.api.health import healthcheck
from app.api.file import upload
from app.api.auth import register, login, logout, me
from app.config.environments import SECRET_KEY, SESSION_EXPIRE_TIME
import os

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

BASE_DIR = (
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )

    )
)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
application.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@application.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}
