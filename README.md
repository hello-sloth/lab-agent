# Lab Agent · 实验室预约智能体

> 一句话预约实验室和设备，告别繁琐的点击与提交流程。

面向高校/企业实验室场景的 AI Agent 全栈项目：把传统「实验室 + 设备 + 预约审批」管理系统和 LangGraph ReAct Agent 结合在一起。你可以在对话框里说 *"明天下午三点帮我约化学实验室的离心机"*，Agent 会自己查日期、找实验室、列设备、复述要素、等你确认，再落一张待审核的预约单；规则类问题（开放时间、安全规范、设备使用）由 Milvus RAG 检索知识库回答，而不是让模型凭空编。

技术栈：**FastAPI + LangGraph + Milvus + 七牛云 + 硅基流动（Embedding & DeepSeek）+ Vue3 + Element Plus**

---

## 目录

- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [工作原理](#工作原理)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 一览](#api-一览)
- [数据模型](#数据模型)
- [对话示例](#对话示例)
- [设计要点与已知限制](#设计要点与已知限制)
- [参与贡献](#参与贡献)

---

## 核心特性

| 能力 | 说明 |
| --- | --- |
| 💬 对话式预约 | 自然语言 → `get_today` 换算日期 → `list_open_labs` / `list_lab_equipments` 定位 ID → 复述要素等你确认 → `create_lab_reservation` 落库 |
| 📚 RAG 知识库 | `backend/data/kb/*.md` 向量化后存入 Milvus，规则/开放时间/安全规范类问题走检索，答案可溯源到具体文档 |
| 🌊 流式体验 | SSE 逐字输出 + `tool_start` / `tool_end` 过程可视化，前端能看到「正在检索实验室知识库…」这类真实步骤 |
| 🛡 先确认后执行 | System Prompt 强约束：未听到「确认」不允许提交预约；缺 `lab_id` / `equipment_id` 必须先查再写，不许瞎编 |
| ✅ 预约审批闭环 | 预约状态 `0 待审核 / 1 已通过 / 2 已拒绝 / 3 已取消`，管理员审核页 + 我的预约页，学生可取消 |
| 🔐 认证与鉴权 | JWT（`Authorization: Bearer`）+ `student` / `admin` 两种角色，`get_current_admin` 保护管理类接口 |
| 🖼 对象存储 | 头像/封面/附件直传七牛云（流式上传，不落临时文件），支持 11 种扩展名、单文件 100MB |
| 🧩 传统后台仍在 | 实验室、设备、用户、预约的 CRUD 接口齐全，Agent 只是叠加在同一套业务服务之上的新入口 |

## 技术栈

**后端**

| 分类 | 选型 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn，统一响应体 `{code, message, data}` 与全局异常处理器 |
| Agent 编排 | LangGraph `StateGraph(MessagesState)`，`agent ⇄ tools` 两节点 ReAct 环 + `tools_condition` 路由 |
| 模型接入 | `langchain-openai` 的 `ChatOpenAI`（`temperature=0`，`streaming=True`）+ OpenAI SDK 兼容 Embeddings |
| 向量数据库 | Milvus（`pymilvus.MilvusClient`），集合 `lab_kb`，`FLOAT_VECTOR(1024)` + `AUTOINDEX` / L2 |
| 关系数据库 | PostgreSQL + SQLAlchemy 2.0（`Mapped` / `mapped_column` 声明式模型），启动时 `create_all` 建表 |
| 对象存储 | 七牛云 `qiniu.put_stream_v2` |
| 鉴权 | PyJWT（HS256）+ bcrypt 密码哈希 |
| 依赖管理 | `uv`（`pyproject.toml`，已配置清华 PyPI 镜像），Python ≥ 3.14 |

**前端**

| 分类 | 选型 |
| --- | --- |
| 框架 | Vue 3（`<script setup>`）+ Vite |
| UI | Element Plus + `@element-plus/icons-vue` |
| 路由 | vue-router，`beforeEach` 做 token 守卫 |
| 请求 | Axios 封装（自动带 JWT、统一处理 401）；AI 对话单独用 `fetch` + `ReadableStream` 解析 SSE |
| Markdown | `marked` 渲染 + `dompurify` 消毒 |

## 项目结构

```text
lab-agent/
├── backend/
│   ├── app/
│   │   ├── api/               # 路由层：auth / user / lab / equipment / reservation / files / ai
│   │   ├── common/            # BusinessException、统一 Response / PageResponse
│   │   ├── dependencies/      # get_current_user / get_current_admin
│   │   ├── models/            # SQLAlchemy：users / labs / equipments / reservations
│   │   ├── schemas/           # Pydantic 请求与响应模型
│   │   ├── services/
│   │   │   ├── agent_service.py   # LangGraph 图构建、System Prompt、SSE 事件流
│   │   │   ├── agent_tools.py     # 5 个 Agent 工具（绑定 db 与当前用户）
│   │   │   ├── kb_service.py      # Milvus 连接、惰性建索引、向量检索
│   │   │   ├── lab_service.py / equipment_service.py / reservation_service.py
│   │   │   └── auth_service.py / user_service.py
│   │   ├── utils/             # jwt 签发校验、密码哈希
│   │   ├── config.py          # pydantic-settings 读 .env
│   │   ├── database.py        # engine / SessionLocal / Base
│   │   └── main.py            # FastAPI 装配：CORS、路由、异常处理
│   ├── data/kb/               # 知识库原始文档：开放时间.md / 安全规范.md / 设备使用.md
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── api/               # 按业务域拆分的请求封装，ai.js 负责 SSE
    │   ├── views/             # AIChat、LabList、Equipment、MyReservation、AuditReservation…
    │   ├── components/ReserveDialog.vue
    │   ├── layouts/Layout.vue
    │   ├── router/  utils/  assets/
    │   └── vite.config.js     # dev 端口 3000，/api 代理到 127.0.0.1:8000
```

## 工作原理

### 1. 对话式预约（ReAct）

```text
Vue AIChat.vue ── fetch POST /api/ai/chat/stream (JWT) ──► api/ai.py
                                                             │
                                                   agent_service.stream_agent
                                                             │
                          ┌──────────────────────────────────┴───────────┐
                          │  StateGraph: START → agent ──tools_condition─┤
                          │      ▲                        │              │
                          │      └──── tools (ToolNode) ◄─┘              │
                          └──────────────────────────────────┬───────────┘
                                                             │
              ┌──────────────┬───────────────┬───────────────┼──────────────┐
              ▼              ▼               ▼               ▼              ▼
        search_lab_docs  list_open_labs  list_lab_   create_lab_       get_today
              │                             equipments  reservation
              ▼                                  │          │
        kb_service.search (Milvus)               ▼          ▼
                                            lab_service  reservation_service
                                                        （冲突校验 + 落库）
```

- `build_tools(db, current_user)` 在每次请求里现场构造工具闭包，把数据库会话和当前用户绑进工具，**模型无法伪造他人身份**。
- LangGraph 事件（`on_tool_start` / `on_tool_end` / `on_chat_model_stream`）被翻译成 `status` / `tool_start` / `tool_end` / `token` / `done` / `error` 六种 SSE 事件，工具结果只给前端 200 字预览，完整内容仍在图内给模型看。
- `recursion_limit=10` 兜住 `agent ⇄ tools` 空转。

### 2. RAG 检索链路

```text
data/kb/*.md ──(首次检索时惰性触发)──► 整篇读取 ──► 硅基流动 bge-large-zh-v1.5 (1024d)
                                                        │
                                                        ▼
                                          Milvus collection: lab_kb
                                          {id, vector, text, source}  AUTOINDEX/L2
                                                        │
用户提问 ──► 模型决定调用 search_lab_docs ──► 同一模型编码 query ──► top5 相似
                                                        │
                        score = 1 / (1 + L2_distance)，丢弃 < 0.5，取前 2 篇拼接
                                                        │
                                                        ▼
                                          ToolMessage 回给 agent 组织答案
```

## 快速开始

### 依赖准备

| 服务 | 用途 | 备注 |
| --- | --- | --- |
| PostgreSQL | 业务数据 | 驱动为 psycopg 3；建一个空库即可，表由后端自动创建 |
| Milvus | 向量库 | `standalone` 单机部署即可，需暴露 gRPC 端口（默认 `19530`） |
| 硅基流动 API Key | Embedding + 对话模型 | OpenAI 兼容端点 `https://api.siliconflow.cn/v1` |
| 七牛云 Bucket | 头像/附件 | 需要绑定的访问域名 |
| Python ≥ 3.14 / `uv` | 后端 | |
| Node 22.18+ 或 24.12+ | 前端 | |

### 后端

```bash
cd backend

# 1) 新建配置文件（切勿把真实密钥提交进仓库）
cat > .env <<'EOF'
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db>?sslmode=disable
JWT_SECRET_KEY=<换成一串随机长字符>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

QINIU_ACCESS_KEY=<AK>
QINIU_SECRET_KEY=<SK>
QINIU_BUCKET_NAME=<bucket>
QINIU_DOMAIN=<cdn.yourdomain.com>   # 不要带 http://

LLM_API_KEY=<硅基流动 API Key>
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V3

MILVUS_URL=http://<milvus-host>:19530
MILVUS_TOKEN=<user>:<password>
MILVUS_DB=default

EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_DIM=1024
EOF

# 2) 安装依赖并启动
uv sync
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

首次对话触发检索时，后端会自动创建集合 `lab_kb` 并把 `data/kb/*.md` 全部向量化插入，**无需单独的建索引脚本**。

### 前端

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000，/api 已代理到 127.0.0.1:8000
```

登录后左侧菜单进入 **AI 助手**（路由 `/manager/ai-chat`）即可开始对话。管理员账号（`role=admin`）额外拥有用户管理、实验室/设备维护与预约审核页面。

## 配置说明

所有配置通过 `backend/.env` 注入（`app/config.py` 用 `pydantic-settings` 读取，缺字段直接启动失败，便于 early fail）：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | SQLAlchemy 连接串，本项目用 `postgresql+psycopg` 生态的 `postgresql://` |
| `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_EXPIRE_HOURS` | ✅ / HS256 / 24 | Token 载荷只有 `{user_id, exp}`，角色每次从库里取，改权限不必等 Token 过期 |
| `QINIU_*` | ✅ | 上传走 `uploads/<毫秒时间戳_随机>.ext`，返回 `https://<QINIU_DOMAIN>/<key>` |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | ✅ | 同一个 Key 同时用于对话与 Embedding |
| `MILVUS_URL` / `MILVUS_TOKEN` / `MILVUS_DB` | ✅ | `MILVUS_URL` 是 gRPC 地址，不是浏览器里的 REST 地址 |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | 1024 | **改维度必须先删除集合 `lab_kb`**，否则插入即报错 |

知识库本身：目录 `backend/data/kb`（硬编码常量）与集合名 `lab_kb`，想加文档直接把 `.md` 丢进去即可，但需按[已知限制](#设计要点与已知限制)第 2 条重建索引。

## API 一览

统一前缀 `/api`，除 `auth` 与 `files` 外的接口均需 `Authorization: Bearer <token>`；`/api/user/list`、`/api/reservation/{id}/audit` 以及实验室/设备/用户的写操作额外要求 `role=admin`（`get_current_admin`）。响应体统一为 `{code, message, data}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/login` `/api/auth/register` | 登录返回 `{token, user}` / 注册（角色固定 `student`） |
| GET PUT | `/api/user/me` | 个人信息读写 |
| PUT | `/api/user/password` | 修改密码（bcrypt 校验旧密码） |
| GET POST PUT DELETE | `/api/user/list` `/api/user` `/api/user/{id}` | 用户管理，`admin` 专属 |
| GET | `/api/lab/list` `/api/lab/{id}` | 实验室分页/关键词查询，支持按 `status` 过滤开放中的实验室 |
| POST PUT DELETE | `/api/lab` `/api/lab/{id}` | 实验室维护 |
| GET | `/api/equipment/list` | 设备分页查询，`lab_id` 与 `keywords` 均可选 |
| POST PUT DELETE | `/api/equipment` `/api/equipment/{id}` | 设备维护 |
| POST | `/api/reservation` | 提交预约，服务端做时间/状态/时段冲突校验 |
| GET | `/api/reservation/list` | 学生只见自己的记录，管理员见全部；支持按 `status` 过滤 |
| PUT | `/api/reservation/{id}/cancel` | 仅本人、且状态为 `待审核` 时可取消 |
| PUT | `/api/reservation/{id}/audit` | 审核，`status` 只接受 `1` 通过 / `2` 拒绝，且必须处于待审核 |
| POST | `/api/files/upload` | multipart 上传到七牛云 |
| POST | `/api/ai/chat/stream` | **SSE 流式对话**，请求体 `{messages: [{role, content}]}` |

`/api/ai/chat/stream` 的事件类型：

```text
data: {"type":"status","message":"正在思考…"}
data: {"type":"tool_start","name":"search_lab_docs","label":"检索实验室知识库"}
data: {"type":"tool_end","name":"search_lab_docs","label":"检索实验室知识库","preview":"[开放时间.md] …"}
data: {"type":"token","content":"计算机实验室"}
data: {"type":"done"}
data: {"type":"error","message":"…"}   # 流已开始，错误也只能用事件返回
```

## 数据模型

`Base.metadata.create_all` 在启动时建表，公共字段 `id / create_time / update_time` 由基类提供。

| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `users` | `username` `password` `name` `role` `email` `phone` `avatar` `status` | `role`: `student` / `admin`；`status`: 0 禁用 1 正常 |
| `labs` | `name` `location` `capacity` `open_time` `close_time` `description` `img` `status` | `status`: 0 关闭 1 开放，决定能否被预约 |
| `equipments` | `lab_id` `name` `spec` `quantity` `description` `img` `status` | `status`: 0 维修 1 正常 |
| `reservations` | `user_id` `lab_id` `equipment_id?` `date` `start_time` `end_time` `remark` `status` | `equipment_id` 为空表示只约实验室；`status`: 0 待审 1 通过 2 拒绝 3 取消 |

预约服务端校验（`reservation_service.create_reservation`）：不能约过去日期/过去时间、结束必须晚于开始、必须落在实验室 `open_time~close_time` 内、实验室或设备状态异常则拒绝、同实验室（或同设备）同时段已有 `待审核/已通过` 记录则提示「该时段已预约」。

## 对话示例

```text
🧑 明天下午三点到五点，帮我约化学实验室那台离心机
🤖 [get_today → 2026-11-26] [list_open_labs("化学") → ID 4]
   [list_lab_equipments(4, "离心机") → ID 9，数量 3]
   请确认：化学实验室（ID 4）· 离心机（ID 9）· 2026-11-26 15:00-17:00，确认预约吗？
🧑 确认
🤖 [create_lab_reservation] 预约已提交，状态为待审核，管理员通过后即可使用。

🧑 实验室几点开门？
🤖 [search_lab_docs → 命中 开放时间.md] 计算机实验室周一至周五 08:00-21:00，周末 09:00-17:00…

🧑 用化学实验室需要注意什么？
🤖 [search_lab_docs → 命中 安全规范.md] 需穿实验服、佩戴护目镜，废液分类回收…
```

## 设计要点与已知限制

以下内容对二次开发或部署排障很有用，均为当前实现的真实边界。

1. **检索阈值偏紧**。`score = 1/(1+L2)` 且 `score < 0.5` 的命中会被丢弃（等价于余弦相似度 ≥ 0.5）。实测 `开放时间` 0.556、`你们几点开放` 0.511——换个问法就可能落空，工具于是返回「没有检索到相关的资料」。建议阈值降到 0.35 左右，或改用 `COSINE` / `IP` 度量并按相似度设阈，同时把 `top_k=2` 参数化。
2. **索引只在集合为空时构建**。集合非空就直接返回，因此**新增或修改 `data/kb/*.md` 不会自动生效**，需要删掉集合重建：
   ```python
   from pymilvus import MilvusClient
   MilvusClient(uri=MILVUS_URL, token=MILVUS_TOKEN, db_name=MILVUS_DB).drop_collection("lab_kb")
   ```
3. **一篇文章 = 一条向量**，没有 chunking。整篇 md 直接 embedding，文档越长、主题越杂，相似度越低；建议把知识库拆成「一文件一主题」的小文档。
4. **Milvus gRPC 不走 HTTP 代理**。若后端进程环境里有 `HTTP_PROXY` / `HTTPS_PROXY`（Clash、公司代理、某些 IDE 注入），gRPC 会被转发到代理导致 `Fail connecting to server`，而 REST 探测看起来一切正常——极易误判成"知识库没数据"。启动前加一句即可：
   ```bash
   export no_proxy=<milvus-host>,localhost,127.0.0.1
   ```
5. **工具异常被转成 JSON 给模型**。`agent_tools` 里 `except Exception` 会把堆栈信息压成 `{"ok": false, "error": "..."}`，前端只显示 200 字预览，模型则回答"知识库连不上"。排障请看后端日志，建议后续接入 `logging` 并把外部服务异常显式暴露。
6. **多轮上下文有限**。前端只回传 `role/content`，`ToolMessage` 不进历史，跨轮追问会重新检索一遍；如需长会话记忆可接入 LangGraph checkpointer。
7. **CORS 与端口**。`main.py` 白名单写的是 `5173`，而 Vite 实际配置为 `3000`；开发时因为走 `/api` 反向代理不受影响，若前端独立域名部署需同步修改。
8. **上传接口未鉴权**。`/api/files/upload` 没有 `Depends(get_current_user)`，任何人拿到域名就能占用你的七牛云存储额度；二次开发时建议补上鉴权、频率限制与 Content-Type 校验。
9. **过期预约自动失效逻辑尚未挂载**。`reservation_service.run_expire_scan()` 会把已过时间的待审核单置为取消，但 `main.py` 里没有 lifespan 或定时任务注册它——需要的话在启动事件里 `asyncio.create_task(run_expire_scan())`。
10. **遗留依赖**。`pyproject.toml` 里的 `chromadb`、`sentence-transformers` 是向量库从 Chroma 迁到 Milvus 之前的依赖，当前代码未使用，可按需清理。
11. **自动建表适合开发**。`Base.metadata.create_all` 不会处理字段变更，正式环境建议换成 Alembic 迁移。

## 参与贡献

Issues 和 PR 都欢迎。比较值得做的方向：知识库切片 + 重排、检索参数外置为配置、给 Agent 增加 checkpointer 与会话持久化、预约冲突检测覆盖设备数量、前端展示检索来源链接。

提交前请确认：
- 不要把 `.env` 或任何真实密钥写进代码与文档；若历史上已误提交，请立即轮换密钥并清理 Git 历史。
- 后端 `uv run uvicorn app.main:app --reload` 自测通过，且至少跑通一条完整对话预约链路和一条知识库问答。

---

如果这个项目对你在学 LangGraph / RAG 落地有帮助，欢迎点个 Star ⭐。
