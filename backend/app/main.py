from fastapi import FastAPI

from app.database import engine, Base
from app.models.user import User
from app.api.auth import router as auth_router
from app.api.user import router as user_router
Base.metadata.create_all(bind=engine)
app = FastAPI()

app.include_router(auth_router)
app.include_router(user_router)
@app.get("/")
async def root():
    return {"message": "Hello World"}
