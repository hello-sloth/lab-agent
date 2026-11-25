from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent # 后端项目的根路径

class Settings(BaseSettings):
    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_HOURS: int = 24

    # 七牛云配置
    QINIU_ACCESS_KEY: str
    QINIU_SECRET_KEY: str
    QINIU_BUCKET_NAME: str
    QINIU_DOMAIN: str  # 例如 "cdn.yourdomain.com"，不要带 http://

    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str

    # Milvus 向量库配置
    MILVUS_URL: str
    MILVUS_TOKEN: str
    MILVUS_DB: str   # 留空使用 default 数据库

    # 嵌入模型配置（硅基流动 OpenAI 兼容接口）
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DIM: int = 1024

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()



MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip",
}