
from openai import OpenAI
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType

from app.config import BASE_DIR, settings

KB_DIR = BASE_DIR / "data" / "kb"

COLLECTION_NAME = "lab_kb"
EMBED_BATCH_SIZE = 16

_milvus_client = None
_openai_client = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.LLM_API_KEY:
            raise RuntimeError("请设置 LLM_API_KEY 环境变量")
        _openai_client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    return _openai_client

def _embed_texts(texts: list[str]) -> list[list[float]]:
    """调用硅基流动的 OpenAI 兼容嵌入接口，批量生成向量"""
    client = _get_openai_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]
        # 硅基流动非 Qwen 模型不要传 dimensions 参数，BAAI/bge-large-zh-v1.5 默认 1024 维
        resp = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
        vectors.extend(item.embedding for item in resp.data)

    mismatch = next((v for v in vectors if len(v) != settings.EMBEDDING_DIM), None)
    if mismatch is not None:
        raise RuntimeError(
            f"{settings.EMBEDDING_MODEL} 返回 {len(mismatch)} 维向量，"
            f"与 EMBEDDING_DIM={settings.EMBEDDING_DIM} 不一致，"
            f"请修改 .env 后删除 Milvus 集合 {COLLECTION_NAME} 重建"
        )
    return vectors

def _get_milvus_client() -> MilvusClient:
    global _milvus_client
    if _milvus_client is None:
        if not settings.MILVUS_URL:
            raise RuntimeError("请设置 MILVUS_URL 环境变量")
        kwargs = {"uri": settings.MILVUS_URL}
        if settings.MILVUS_TOKEN:
            kwargs["token"] = settings.MILVUS_TOKEN
        if settings.MILVUS_DB:
            kwargs["db_name"] = settings.MILVUS_DB
        _milvus_client = MilvusClient(**kwargs)
    return _milvus_client

def _build_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=512),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
    ]
    return CollectionSchema(fields=fields)

def _init_collection_if_empty(client: MilvusClient):
    """如果集合不存在或为空，则从 KB_DIR 加载 .md 文件、生成向量并插入 Milvus"""
    if not client.has_collection(COLLECTION_NAME):
        schema = _build_schema()
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="L2",  # 保持与原 1/(1+dist) 的 score 转换逻辑兼容
        )
        client.create_collection(
            collection_name=COLLECTION_NAME,
            schema=schema,
            index_params=index_params,
        )
        client.load_collection(COLLECTION_NAME)
    else:
        client.load_collection(COLLECTION_NAME)
        stats = client.get_collection_stats(COLLECTION_NAME)
        if stats.get("row_count", 0) > 0:
            return

    # 集合为空，加载知识库
    paths = sorted(KB_DIR.glob("*.md"))
    docs, ids, sources = [], [], []
    for path in paths:
        text = path.read_text(encoding="UTF-8").strip()
        if not text:
            continue
        docs.append(text)
        ids.append(path.stem)
        sources.append(path.name)

    if not docs:
        return

    vectors = _embed_texts(docs)
    data = [
        {"id": ids[i], "vector": vectors[i], "text": docs[i], "source": sources[i]}
        for i in range(len(docs))
    ]
    client.insert(collection_name=COLLECTION_NAME, data=data)

def get_collection():
    """兼容原函数名，返回 (MilvusClient, collection_name)"""
    client = _get_milvus_client()
    _init_collection_if_empty(client)
    return client, COLLECTION_NAME


def search(query: str) -> str:
    """根据关键字检索 Milvus，返回拼接后的文档字符串"""
    client, collection_name = get_collection()

    stats = client.get_collection_stats(collection_name)
    if stats.get("row_count", 0) == 0:
        return ""

    query_vector = _embed_texts([query])[0]
    limit = min(5, stats.get("row_count", 5))

    hits = client.search(
        collection_name=collection_name,
        data=[query_vector],
        limit=limit,
        output_fields=["text", "source"],
        search_params={"metric_type": "L2"},
    )

    score_parts = []
    for hit in (hits[0] if hits else []):
        dist = hit["distance"]
        # 沿用原逻辑：1/(1+dist)，越接近 1 越相关
        score = 1 / (1 + dist)
        if score < 0.5:
            continue
        entity = hit.get("entity", {})
        name = entity.get("source") or ""
        content = entity.get("text") or ""
        score_parts.append({"score": score, "content": f"[{name}]\n{content}"})

    score_parts.sort(key=lambda x: x["score"], reverse=True)
    final_parts = [item["content"] for item in score_parts[:2]]
    return "\n\n".join(final_parts)