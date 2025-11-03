from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.routes import healthcheck
from api.routes import upload
from api.routes import subtitle
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return {"users": users}


app = FastAPI(
    title="SVSP FastAPI Service",
    description="Semantic Video Summarization Pipeline Backend API documentation",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # FE dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(healthcheck.router)
app.include_router(upload.router)
app.include_router(subtitle.router)



@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello World"}