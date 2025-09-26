from fastapi import FastAPI
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.routes import healthcheck
from api.routes import upload



app = FastAPI(
    title="SVSP FastAPI Service",
    description="Semantic Video Summarization Pipeline Backend API documentation",
    version="1.0.0"
)

app.include_router(healthcheck.router)
app.include_router(upload.router)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}