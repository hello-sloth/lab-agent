import os.path
import uuid
from pathlib import Path
import time

from fastapi import APIRouter, UploadFile, File
from qiniu import Auth, put_stream_v2

from app.schemas.file import FileResponse

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, settings

router = APIRouter(prefix="/files", tags=["文件管理"])

q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)

# 七牛云上的统一目录前缀
UPLOAD_PREFIX = "uploads/"
@router.post("/upload")
def upload(file: UploadFile = File(...)):
    """文件上传的接口"""
    if not file.filename:
        raise BusinessException(message="文件名不能为空")

    # 原始的文件名 用户头像.jpg
    original_name = os.path.basename(file.filename)
    # 文件后缀 .jpg
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessException(message=f"不支持的文件后缀: {ext}")
    # 文件大小校验
    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessException(
            message=f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    # 生成唯一文件名，并拼接 uploads/ 前缀作为七牛云的 key
    unique_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"
    key = f"{UPLOAD_PREFIX}{unique_name}"

    # 生成上传 Token
    token = q.upload_token(settings.QINIU_BUCKET_NAME, key, 3600)
    # 直接将 UploadFile 的流交给七牛云，无需临时文件
    file.file.seek(0)

    ret, info = put_stream_v2(token, key, file.file, original_name, file.size, version='v2')

    if info.status_code != 200 or not ret or ret.get("key") != key:
        error_body = getattr(info, "text_body", "") or str(info)
        raise BusinessException(message=f"七牛云上传失败: {error_body}")

    # 访问 URL 也带上 uploads/ 前缀
    url = f"https://{settings.QINIU_DOMAIN}/{key}"

    return Response.success(
        data=FileResponse(
            original_name=original_name,
            disk_name=key,      # 返回完整的 key（含 uploads/ 前缀）
            size=file.size,
            url=url,
        )
    )



