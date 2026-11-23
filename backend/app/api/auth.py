from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.schemas.user import UserResponse
from app.services import auth_service
from app.utils.jwt import create_access_token
from app.utils.password import verify_password

router = APIRouter(prefix="/auth", tags=["权限验证"])

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.login(db, data)
    return Response.success(message="登录成功", data=result)

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    auth_service.register(db, data)
    return Response.success(message="注册成功")