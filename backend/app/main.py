from fastapi import FastAPI, HTTPException
from fastapi.exceptions import ValidationException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR
from app.database import engine, Base
from app.models.user import User
from app.api import api

from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers={"*"},
)
app.include_router(api)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底，必须放在最后注册
app.add_exception_handler(Exception, global_exception_handler)

# 挂载静态的文件目录
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
@app.get("/")
async def root():
    return {"message": "Hello World"}
