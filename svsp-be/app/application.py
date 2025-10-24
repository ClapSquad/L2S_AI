from fastapi import FastAPI
from app.api.health import healthcheck
from app.api.file import upload
from app.api.auth import register, login, logout, me
from app.middleware.cors import addCORS
from app.middleware.session import addSession
from app.middleware.static import AddStaticFileServing

application = FastAPI(
    title="SVSP FastAPI Service",
    description="Semantic Video Summarization Pipeline Backend API documentation",
    version="1.0.0"
)

addCORS(application)
addSession(application)
AddStaticFileServing(application)

application.include_router(healthcheck.router)
application.include_router(upload.router)

application.include_router(register.router)
application.include_router(login.router)
application.include_router(logout.router)
application.include_router(me.router)


@application.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}
