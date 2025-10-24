from fastapi import FastAPI
from app.middleware.cors import addCORS
from app.middleware.session import addSession
from app.middleware.static import AddStaticFileServing
from app.api.router import addRouter

application = FastAPI(
    title="SVSP FastAPI Service",
    description="Semantic Video Summarization Pipeline Backend API documentation",
    version="1.0.0"
)

addCORS(application)
addSession(application)
AddStaticFileServing(application)
addRouter(application)


@application.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}
