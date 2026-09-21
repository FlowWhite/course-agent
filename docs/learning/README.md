# Course Agent 学习目录

本目录用于系统学习 `Course Agent` 主项目。

学习材料必须以项目**当前真实代码**为基础，并结合：

* `docs/architecture.md`：当前真实架构；
* `docs/current-sprint.md`：当前允许推进的开发范围；
* `docs/roadmap.md`：长期升级路线。

本目录的目标不是记录“Codex 写了什么”，而是最终让我能够：

1. 看懂项目真实执行链；
2. 解释关键技术为什么存在；
3. 理解重要架构取舍；
4. 独立定位和修改核心代码；
5. 通过测试和实验验证自己的理解；
6. 在面试中经受围绕项目的连续追问。

---

# 一、最重要的学习原则

## 1. 当前已有能力：先读代码，再学习

如果某项能力已经真实存在于仓库中：

```text
真实代码
→ 找入口
→ 跟执行链
→ 理解概念
→ 自己验证
→ 写笔记
```

不要为了学习而先重构代码。

典型内容包括：

* FastAPI；
* Router；
* Endpoint；
* JWT；
* PostgreSQL CRUD；
* 文件上传；
* 当前 async/sync 模型；
* Agent Runtime；
* Tool Calling；
* 当前 RAG；
* Vue；
* Docker。

---

## 2. 尚未实现的路线图能力：先了解问题，再实现，再深入学习

从项目开始进入架构升级阶段以后，采用：

```text
先理解当前问题
        ↓
Codex 分析并实现
        ↓
运行测试 / 验证结果
        ↓
沿新代码重建执行链
        ↓
自己完成一个小修改或测试
        ↓
深入理解原理与取舍
        ↓
写学习笔记
```

这类内容包括：

* Tool Risk Policy；
* Human Approval；
* Connection Pool；
* Hybrid Retrieval；
* Reranker；
* Agentic Retrieval；
* LangGraph Workflow；
* SSE；
* Tracing；
* Agent Evaluation。

---

## 3. 不允许“完全不知道 → Codex 写完 → 看总结”

Codex 可以承担主要工程实现，但正式写进学习笔记前，至少必须完成：

### A. 知道它解决什么问题

例如：

```text
为什么当前数据库连接方式需要 Connection Pool？
```

### B. 能沿真实代码解释执行链

例如：

```text
HTTP Request
→ Router
→ Service
→ Pool
→ Connection
→ PostgreSQL
→ return connection
```

### C. 自己完成一个小型修改或测试

例如：

* 新增一个 Tool Policy 测试；
* 修改一个 Connection Pool 配置；
* 增加一个 Retrieval Eval Case；
* 新增一种 SSE event；
* 调整一个 retrieval `top_k` 并解释结果。

---

## 4. 不确定的内容必须标记为“不知道”

如果当前代码、配置或实验无法证明某件事：

统一写成：

```text
状态：待确认
```

或者：

```text
当前无法从仓库确认
```

不要为了让笔记完整而猜测。

尤其禁止：

* 把 roadmap 中的能力写成已经实现；
* 推测第三方 SDK 内部行为；
* 推测生产环境配置；
* 推测尚未执行的测试结果；
* 把 vector → FTS fallback 写成 Hybrid Retrieval；
* 把 PostgreSQL FTS 写成 BM25；
* 把线程池任务写成后台任务。

---

# 二、整个学习路线的三个阶段模型

Course Agent 的学习过程分成三种不同模式。

```text
01–12
理解当前系统
     ↓
13
冻结并记录 Baseline
     ↓
14–27
逐阶段升级系统
     ↓
28
完整复盘
```

对应：

### 第一类

```text
现有代码 → 学习
```

### 第二类

```text
Baseline → 记录
```

### 第三类

```text
问题
→ Codex 实现
→ 测试
→ 学习
→ 自己修改
→ 笔记
```

---

# 三、第一阶段：理解当前已经运行的应用

## 01–08：后端基础执行链

这些能力已经存在。

**不要为了学习它们先修改架构。**

| 编号 | 笔记                             | 核心问题                                | 学习模式  |
| -- | ------------------------------ | ----------------------------------- | ----- |
| 01 | FastAPI——从 Python 函数到 HTTP API | Python 函数如何成为 HTTP API？             | 读现有代码 |
| 02 | Router——API 的业务拆分与路由注册         | Request 如何找到 Router？                | 读现有代码 |
| 03 | Endpoint——请求参数、依赖注入与错误处理       | Path、Body、Dependency 如何进入 Endpoint？ | 读现有代码 |
| 04 | 鉴权——注册、登录、JWT 与用户隔离            | 系统如何识别用户并隔离数据？                      | 读现有代码 |
| 05 | 任务查询——从 Endpoint 到 PostgreSQL  | CRUD 如何真正执行到数据库？                    | 读现有代码 |
| 06 | PostgreSQL——表关系、约束、索引与参数化 SQL  | 数据如何建模、约束和查询？                       | 读现有代码 |
| 07 | 课程资料——文件上传、文档解析与文本分块           | UploadFile 如何变成 chunk？              | 读现有代码 |
| 08 | 同步与异步——请求如何执行                  | async、同步阻塞、线程池分别是什么？                | 读现有代码 |

---

## 第一阶段完成标准

不看笔记，能够讲清：

```text
Vue
→ HTTP
→ FastAPI
→ Middleware / Dependency
→ JWT 当前用户
→ Router
→ Service / Data Service
→ psycopg
→ PostgreSQL
→ Response
→ Vue
```

并能够回答：

* `async def` 为什么不代表里面所有操作都是异步？
* FastAPI 为什么能运行同步 Endpoint？
* Pydantic Schema 和数据库表是什么关系？
* JWT 为什么不是数据库 Session？
* SQL 参数化为什么能够降低 SQL Injection 风险？

---

# 四、第二阶段：补全当前已经存在但尚未系统学习的核心链路

09–12 依然属于：

> **先学习现有真实代码。**

不要等未来重构。

---

## 09 Agent Runtime 与 Tool Calling

重点代码：

```text
agent_runtime.py
tools.py
api/routers/chat.py
```

必须掌握：

```text
POST /api/v1/chat
→ JWT
→ course ownership
→ ContextVar
→ Agent
→ SQLiteSession
→ Runner.run_sync
→ DeepSeek
→ Tool Call
→ Service
→ PostgreSQL / Retrieval
→ Tool Result
→ LLM
→ Final Answer
```

重点理解：

* Agent 在哪里创建；
* Runner 是什么；
* Model 与 Runner 的职责区别；
* Tool schema 从哪里来；
* LLM 是否真正执行 Python 函数；
* Tool 为什么能获得当前 `user_id`；
* ContextVar 解决什么问题；
* SQLiteSession 保存的是什么；
* Conversation Memory 和业务 State 有什么区别。

### 当前未知内容

第三方 `SQLiteSession` 内部：

* 数据库 schema；
* 压缩策略；
* 清理策略；
* 连接管理；

如果没有继续阅读 SDK 源码：

```text
状态：当前无法从仓库确认
```

不要猜。

---

# 五、10 当前 RAG：先理解第一代实现

第十篇不重复第七篇已经讲过的上传、文件校验、文档解析和文本分块。

本篇从 `document_chunks` 已经保存以后开始，沿代码继续学习：

```text
document_chunks
→ search_vector / embedding
→ 词法检索 / 向量检索
→ 检索路径选择
→ Agent、计划和评估使用检索结果
```

本篇采用“基线 + 当前扩展”的写法，而不是复制成两篇相互重复的笔记。

这里的“基线”表示当前代码中可以单独工作的词法检索路径，不表示仓库历史上一定先存在一个完全没有 Embedding 的版本。项目历史顺序只有在 Git 历史能够证明时才能这样描述。

真实代码：

```text
course_material_service.py
embedding_service.py
document_parser.py
postgres/init.sql
```

当前代码中的检索能力分成三层：

### 1. 词法检索基线

```text
document_chunks.content
→ to_tsvector('simple', content)
→ search_vector
→ PostgreSQL 全文排名和 ILIKE 匹配
```

它适合精确术语、标识符和关键词，不依赖 Embedding Provider，也不要求独立向量数据库。

### 2. 当前已经实现的语义检索扩展

```text
chunk.content
→ Embedding
→ document_chunks.embedding
→ pgvector cosine search
→ HNSW index
```

当前 `search_course_documents_data()` 的实际策略是：

```text
有可用向量并且向量检索有结果
→ 直接返回向量结果

没有可用向量、Provider 失败或向量无结果
→ 回退到 PostgreSQL 全文检索
```

因此当前实现是“向量优先 + FTS fallback”，不是两路同时召回并融合的 Hybrid Retrieval。

### 3. RAG 应用连接

```text
用户问题
→ search_course_documents_data()
→ DocumentSearchResult
→ Agent Tool / 学习计划 / 作业评估
→ LLM 使用检索到的 chunk 生成结果
```

需要区分：

```text
TSVECTOR
  → 词法检索机制

Embedding + pgvector
  → 语义检索机制

检索结果交给 LLM 作为上下文
  → RAG 应用链
```

必须明确：

```text
当前不是 Hybrid Retrieval。
```

因为两路结果没有同时召回并融合。

也必须明确：

```text
PostgreSQL FTS != BM25
```

除非未来项目真正实现 BM25。

---

## 本篇范围和拆分

第七篇已经覆盖了文件上传、文档解析、文本分块和 `document_chunks` 的初步保存流程。

因此第十篇不再重复展开上传接口，而是从已经保存的 chunk 开始，拆成四个学习单元。每个单元都采用：

```text
阅读真实代码
→ 做一个小实验
→ 观察输入、输出和状态
→ 回到代码解释原因
→ 回答项目自测题
```

### 10A：chunk 的两种检索表示

重点代码：

```text
course_material_service.py
  replace_document_chunks_data()

postgres/init.sql
  document_chunks.content
  document_chunks.search_vector
  document_chunks.embedding

embedding_service.py
  embed_texts()
```

需要理解：

```text
content
  → 原始文本

search_vector
  → PostgreSQL 词法检索表示

embedding
  → 语义检索使用的 1024 维向量
```

完成标准：

* 能解释 `search_vector` 和 `embedding` 的区别；
* 能说明为什么解析成功后 Embedding 仍可能是 `not_indexed`；
* 能说明 GIN 索引和 HNSW 索引分别服务什么检索路径。

### 10B：Embedding 索引生命周期

重点代码：

```text
course_material_service.py
  index_course_file_embeddings_data()
  _set_embedding_indexing_data()
  _get_owned_chunks_for_embedding()
  _save_file_embeddings_data()

api/routers/files.py
  POST /files/{file_id}/index
```

需要理解：

```text
not_indexed
  → indexing
  → ready / failed
```

完成标准：

* 能沿代码解释每个状态如何变化；
* 能说明 Provider 失败后为什么解析文本仍然可以保留；
* 能解释为什么支持向量索引重试；
* 能区分线程池中的索引工作和脱离 HTTP 请求的后台任务。

### 10C：一次查询如何选择检索路径

重点代码：

```text
course_material_service.py
  search_course_documents_data()
  _search_course_documents_by_vector()
  _search_course_documents_by_full_text()
```

需要理解：

```text
检查当前课程是否有 ready 向量
  ↓
尝试向量检索
  ↓
有结果则直接返回
  ↓
没有结果或 Provider 失败
  ↓
PostgreSQL 全文检索回退
```

完成标准：

* 能预测不同文件状态下的实际执行路径；
* 能解释 `MIN_VECTOR_RELEVANCE` 的作用；
* 能说明为什么当前实现是 Vector-first + FTS fallback；
* 能说明为什么当前实现不是 Hybrid Retrieval，也不是 BM25。

### 10D：检索结果如何进入业务功能

重点代码：

```text
tools.py
  search_course_documents()

agent_runtime.py
  当前请求的资料来源收集

api/routers/tasks.py
  学习计划和作业评估中的资料检索

learning_insight_service.py
  截止日期风险中的相关资料

web/src/components/AgentChatDrawer.vue
  聊天来源展示
```

需要理解：

```text
DocumentSearchResult
  → ToolResponse
  → PlanSource
  → Agent / 学习计划 / 作业评估 / 前端 sources
```

完成标准：

* 能区分 `DocumentSearchResult`、`ToolResponse` 和 `PlanSource`；
* 能说明检索结果如何进入 Agent 和其他业务功能；
* 能说明当前 sources 为什么还不是严格的 Citation System；
* 能指出当前引用系统没有实现事实级绑定和引用正确性评估。

### 第十篇的小实验安排

第十篇不要求一开始连接真实 Embedding Provider。优先使用 fake client、mock、临时文本和受控输入，观察当前代码的分支和状态。

建议至少完成两个实验：

```text
实验一：观察 content、search_vector、embedding 和索引状态之间的关系
  → 覆盖 10A、10B、10C

实验二：追踪 DocumentSearchResult 如何转换为 PlanSource 并进入 sources
  → 覆盖 10D
```

实验设计阶段先只读分析当前代码；如果需要创建实验文件，应先确认路径和范围，不直接修改业务代码或本学习目录中的原笔记。

完成第十篇的标准不是记住所有 RAG 术语，而是能够独立回答：

* 一个 chunk 如何获得词法检索和语义检索两种表示？
* Embedding 状态为什么会从 `not_indexed` 变成 `indexing`、`ready` 或 `failed`？
* `search_course_documents_data()` 什么时候走向量路径，什么时候走全文回退？
* 为什么当前实现不是 Hybrid Retrieval？
* `DocumentSearchResult` 如何变成 `ToolResponse` 或 `PlanSource`？
* Embedding 失败后，为什么课程资料仍然可能被检索？

### Ingestion

```text
Document
→ parsing
→ chunking
→ embedding
→ vector storage
```

### Retrieval

```text
Query
→ query embedding
→ vector similarity
→ Top-K chunk
```

### Lexical fallback

```text
Query
→ PostgreSQL FTS
→ lexical match
```

### Sources

理解：

* source metadata 从哪里产生；
* 是否真正做到事实级 citation；
* 当前引用系统有什么限制。

---

# 六、11 Vue 工作台

重点：

```text
web/src/App.vue
web/src/composables/useCourseWorkspace.js
```

掌握：

```text
Vue Component
→ composable
→ requestJson()
→ fetch()
→ Authorization header
→ FastAPI
```

重点理解：

* `ref`；
* `computed`；
* props；
* emit；
* composable；
* `sessionStorage`；
* JWT 如何加入请求；
* 401 后如何处理。

不需要把全部前端代码背下来。

---

# 七、12 Docker、测试与运行拓扑

重点：

```text
docker-compose.yml
Dockerfile.backend
web/Dockerfile.frontend
backend/tests/
main.py
```

能够解释：

```text
Browser
  ↓
Nginx / Vue
  ↓
FastAPI
  ├─ PostgreSQL / pgvector
  ├─ Upload Files
  ├─ SQLiteSession
  ├─ DeepSeek
  └─ Embedding Provider
```

同时明确：

### 已测试

必须根据实际测试文件判断。

### 未测试

如果没有真实数据库 integration test：

```text
未实现
```

如果本次没有真正运行测试：

```text
测试当前是否通过：待确认
```

不要因为存在 test 文件就写“测试通过”。

---

# 八、13：架构 Baseline——开发模式的分界线

13 是整个路线中非常重要的过渡阶段。

在这一阶段：

> **原则上不新增重大业务功能。**

目标是保存“升级之前的 Course Agent”。

---

## 需要记录

### 当前 Agent

```text
Agent
→ Runner.run_sync
→ Tool Calling
```

### 当前 Tool 权限

```text
ContextVar
+
SQL ownership filtering
+
Prompt constraint
```

尚不存在：

```text
独立 Tool Risk Policy
通用 HITL Approval
```

### 当前 Retrieval

```text
Vector
→ fallback FTS
```

尚不存在：

```text
Hybrid
Reranker
Retrieval Eval
```

### 当前数据库

```text
Service
→ psycopg.connect()
→ query
→ close
```

尚不存在统一 Connection Pool。

### 当前 Chat

```text
Request
→ Runner.run_sync
→ 完整 JSON Response
```

尚不存在 SSE。

---

# 九、从 14 开始正式切换学习模式

从第 14 篇开始，原则变为：

> **先理解当前问题，再让 Codex 完成当前 Sprint 的工程实现，然后基于真实修改后的代码深入学习。**

固定执行流程：

```text
Step 1
用 15–30 分钟理解问题

Step 2
Codex 分析当前代码

Step 3
Codex 实现

Step 4
运行测试

Step 5
阅读 diff 和真实执行链

Step 6
自己完成一个小修改

Step 7
写学习笔记

Step 8
整理面试追问
```

---

# 十、14 Agent Tool 风险策略与确定性授权

## 当前问题

当前 Agent 可以：

```text
Retrieval
→ 不可信课程文档
→ LLM
→ create/update/delete Tool
```

即使 prompt 中声明：

> 文档不可信。

Prompt 仍然不是确定性权限边界。

---

## 开发前只需理解

```text
Prompt instruction
!=
Authorization
```

知道问题即可。

不要先学大量 Agent Security 理论。

---

## Codex 实现方向

预计需要建立：

```text
Tool
→ Risk Policy
→ Authorization
→ Approval Decision
→ Execute
```

风险等级可考虑：

```text
READ
WRITE
DESTRUCTIVE
```

真实设计以当前 Sprint 和实际代码为准。

---

## 实现后学习

必须沿真实代码找到：

* Risk Policy 在哪里；
* Tool 如何声明风险；
* ownership 在哪里校验；
* approval 在哪里发生；
* prompt injection 为什么不能突破 policy；
* LLM 与 deterministic code 的职责边界。

### 自己至少完成

例如：

* 新增一个 Tool policy case；
* 为现有 Tool 调整 risk level；
* 增加一个 unauthorized-action 测试。

---

# 十一、15 阻塞 I/O、线程池与执行边界

## 当前问题

真实项目存在：

```text
async Endpoint
→ sync psycopg
→ sync filesystem
→ PDF/DOCX parser
```

可能阻塞 event loop。

---

## Codex 修改以后重点学习

比较：

### Before

```text
Event Loop
→ blocking operation
→ 其他协程无法及时运行
```

### After

具体实现必须根据真实代码描述，例如：

```text
Event Loop
→ thread pool
→ sync parser
```

如果最终采用其他方式，则笔记跟随实际实现。

---

## 必须理解

* native async I/O；
* blocking I/O；
* CPU-bound；
* thread pool；
* background task；
* 为什么这些概念不能混为一谈。

---

# 十二、16 PostgreSQL Connection、Transaction 与删除安全

这是一个非常适合：

> **先改代码，再系统学习**

的主题。

---

## 当前问题

当前数据库模式主要是：

```text
service function
→ psycopg.connect()
→ SQL
→ connection close
```

并且任务删除存在：

```text
delete one task
→ full database backup
```

的不合理行为。

---

## 修改以后重点学习

### Connection Pool

```text
Application
→ Pool
→ acquire connection
→ SQL
→ return connection
```

理解：

* Pool 在哪里创建；
* 生命周期；
* acquire；
* return；
* pool size；
* pool exhausted；
* connection 和 transaction 的关系。

### Transaction

理解：

```text
BEGIN
→ SQL
→ COMMIT
```

和：

```text
BEGIN
→ error
→ ROLLBACK
```

### 删除安全

根据最终实现学习：

* soft delete；
* audit log；
* scoped backup；

实际采用哪一种就学习哪一种。

不要在笔记里描述最终没有采用的方案。

---

# 十三、17 文件解析资源限制

当前已有：

* 文件类型检查；
* 文件签名；
* 20 MB size limit；
* DOCX 资源限制。

需要进一步处理 PDF。

修改后学习：

* page budget；
* text budget；
* timeout；
* failure state；
* CPU / memory risk；
* 为什么“文件小”不代表解析成本一定低。

---

# 十四、18 安全回归与后端 Baseline Test

从这里开始要建立一个重要思想：

```text
我认为修好了
```

不等于：

```text
系统证明修好了
```

重点增加：

* authorization test；
* cross-user isolation；
* destructive action；
* Tool Policy；
* parser limit；
* connection behavior；
* regression case。

---

# 十五、19–20 后端可靠性

这两个阶段仍然采用：

```text
Codex 实现
→ 测试
→ 学习
→ 小修改
→ 笔记
```

---

## 19 Versioned Migration / Error Model / Logging

学习：

* migration 为什么存在；
* init.sql 为什么不能永远承担 migration；
* schema version；
* error model；
* structured logging。

如果最终没有使用 Alembic：

不要写：

```text
项目使用 Alembic
```

只能记录真实实现。

---

## 20 Integration Test / Limits / Timeout / Readiness

重点：

* PostgreSQL integration test；
* input limit；
* message limit；
* session lifecycle；
* Provider timeout；
* retry boundary；
* readiness；
* liveness。

---

# 十六、21 开始进入“实验驱动学习”

从 Retrieval Evaluation 开始，学习方式再次升级。

不是：

```text
Codex 写
→ 看代码
```

而是：

```text
问题
→ Baseline
→ Hypothesis
→ Implementation
→ Experiment
→ Metrics
→ Analysis
→ Decision
```

---

# 十七、21 Retrieval Evaluation Baseline

在实现 Hybrid 之前：

必须先测：

```text
FTS
vs
Vector
```

建立 query dataset。

覆盖：

* exact term；
* semantic question；
* cross-chunk；
* ambiguous query；
* no-answer query。

记录：

* relevant chunk；
* expected source；
* query type。

---

## 指标

至少理解：

```text
Recall@K
MRR
NDCG
Latency
```

不要只会公式。

必须能解释：

> 为什么这个指标适合当前问题？

---

# 十八、22 Hybrid Retrieval + Reranking

只有 21 完成以后才进入。

候选结构：

```text
Query
 ├─ Lexical
 └─ Vector
      ↓
Candidate Fusion
      ↓
Reranker
      ↓
Context
```

实际可能使用：

```text
RRF
```

但必须由最终实现决定。

---

## 必须保存比较结果

例如：

| Strategy        | Recall@5 | MRR | Latency |
| --------------- | -------: | --: | ------: |
| FTS             |      待实验 | 待实验 |     待实验 |
| Vector          |      待实验 | 待实验 |     待实验 |
| Hybrid          |      待实验 | 待实验 |     待实验 |
| Hybrid + Rerank |      待实验 | 待实验 |     待实验 |

实验没运行之前：

```text
不得填写假数字。
```

---

# 十九、23 Context Router

目标不是：

> 所有问题都去 RAG。

而是判断：

```text
Query
│
├─ SQL
├─ Lexical
├─ Semantic / Hybrid
└─ Long Context
```

例如：

```text
“数据库作业几点截止？”
→ SQL
```

```text
“讲义中 SERIALIZABLE 出现在哪里？”
→ Lexical
```

```text
“解释 MVCC 和隔离级别的关系。”
→ Semantic / Hybrid
```

需要建立 Routing Evaluation。

---

# 二十、24 Agentic Retrieval

只有：

```text
Retrieval Evaluation
+
Hybrid
+
Routing
```

稳定以后再进入。

目标结构：

```text
Question
→ Retrieve
→ Evidence Check
→ sufficient?
   ├─ yes → Answer
   └─ no
       ↓
     Rewrite
       ↓
     Retrieve Again
```

---

## 必须存在系统预算

例如：

* max retrieval rounds；
* max tool calls；
* token budget；
* document budget；
* no-new-evidence stop condition。

不能让 LLM 无限决定是否继续搜索。

---

# 二十一、25 Stateful Workflow + HITL

只有真正需要：

* State；
* Branch；
* Loop；
* Checkpoint；
* Interrupt；
* Resume；

时再引入 LangGraph。

推荐学习计划 Workflow：

```text
Load Tasks
→ Get User Constraints
→ Generate Plan
→ Deterministic Validation
→ Conflict?
   ├─ yes → Replan
   └─ no
        ↓
     Human Approval
        ↓
     Write DB
```

普通 Chat 不为了“用了 LangGraph”而迁移。

---

# 二十二、26 Agent Event Stream / SSE

当前系统是：

```text
Request
→ Agent 完成
→ JSON Response
```

目标可能变为：

```text
agent_start
retrieval_start
retrieval_result
tool_call
tool_result
approval_required
token_delta
final_answer
error
```

实现以后学习：

* SSE；
* HTTP streaming；
* browser consumption；
* disconnect；
* cancellation；
* error protocol。

---

# 二十三、27 Tracing + Agent/RAG Evaluation

这里开始真正进入 Agent Engineering。

Tracing 至少需要关注：

```text
LLM
Retrieval
Reranker
Tool
Approval
Error
```

Metrics 可能包括：

```text
Latency
Token
Cost
Tool Calls
Retrieval Rounds
Fallback
Errors
```

---

## Agent Eval

覆盖：

* Tool Selection Accuracy；
* Argument Accuracy；
* Task Success；
* Unauthorized Action；
* Retrieval quality；
* Citation correctness；
* latency；
* cost。

实际指标以最终系统为准。

---

# 二十四、28 完整架构复盘

最后停止增加大功能。

需要能够从用户输入开始完整讲：

```text
Frontend
↓
HTTP / SSE
↓
FastAPI
↓
Auth
↓
Agent / Workflow
↓
Context Router
↓
SQL / Retrieval
↓
Tool Policy
↓
Human Approval
↓
PostgreSQL
↓
Tracing
↓
Evaluation
```

如果某项最终没有实现：

就不要画进最终架构。

---

# 二十五、每篇笔记统一模板

01–12：

```text
1. 本篇解决什么问题
2. 真实入口
3. 真实执行链
4. 本项目用到的核心概念
5. 当前实现
6. 当前限制
7. 我自己验证了什么
8. 3–5 个项目自测题
```

---

14 以后增加：

```text
9. 修改前是什么
10. 为什么修改
11. Codex 修改了什么
12. 新执行链
13. 测试如何证明修改有效
14. 我自己完成的小修改
15. 设计 Trade-off
16. 面试追问
```

---

21 以后再增加：

```text
17. Baseline
18. Hypothesis
19. Experiment
20. Metrics
21. Result
22. Engineering Decision
```

---

# 二十六、代码掌握程度分类

不是所有代码都需要相同深度。

## A 类：必须能沿执行链解释

包括：

* FastAPI Request；
* Authentication；
* PostgreSQL；
* async / thread pool；
* Agent Runner；
* Tool Calling；
* ContextVar；
* Retrieval；
* Connection Pool；
* Tool Policy；
* HITL；
* Agent State；
* Evaluation；
* Tracing。

要求：

```text
能找到
+
能解释
+
能修改
+
能测试
```

---

## B 类：知道职责并能修改即可

例如：

* 普通 Schema；
* 文件名处理；
* CORS；
* Dockerfile；
* Vue 普通 Component；
* SHA。

---

## C 类：不要求源码级理解

例如：

* Agents SDK Runner 内部实现；
* pgvector HNSW 源码；
* pypdf parser 内核；
* Argon2 实现；
* Uvicorn 源码。

需要知道：

```text
输入
输出
职责
边界
失败模式
```

即可。

---

# 二十七、正式写进简历的技术必须达到更高标准

任何未来写入简历的能力，至少必须满足：

```text
我能解释它为什么出现
        ↓
我能画真实执行链
        ↓
我能找到关键代码
        ↓
我能自己修改一个局部
        ↓
我能写或修改测试
        ↓
我能解释设计 Trade-off
```

不能只是：

```text
Codex 实现过
```

---

# 二十八、最终学习顺序

```text
01–08
FastAPI / Auth / PostgreSQL / File / Async
        ↓
09
Agent Runtime + Tool Calling
        ↓
10A–10D
当前 RAG：从 chunk 到检索结果
        ↓
11
Vue
        ↓
12
Docker + Tests
        ↓
13
Baseline
        ↓
==============================
从这里开始先升级代码再深入学习
==============================
        ↓
14
Tool Policy
        ↓
15
Blocking I/O
        ↓
16
Connection Pool + Transaction
        ↓
17
Parser Safety
        ↓
18
Security / Regression Test
        ↓
19–20
Backend Reliability
        ↓
==============================
从这里开始实验驱动
==============================
        ↓
21
Retrieval Evaluation
        ↓
22
Hybrid + Reranker
        ↓
23
Context Router
        ↓
24
Agentic Retrieval
        ↓
25
Stateful Workflow + HITL
        ↓
26
Agent Event Streaming
        ↓
27
Tracing + Agent Evaluation
        ↓
28
Architecture + Interview Review
```

---

# 二十九、每次开始学习前的检查

开始一篇笔记之前依次确认：

```text
1. docs/architecture.md
   ↓
当前到底实现了什么？

2. docs/current-sprint.md
   ↓
现在允许修改什么？

3. docs/roadmap.md
   ↓
这个能力最终处于哪里？

4. 当前仓库真实代码
   ↓
文档有没有过期？
```

如果：

```text
文档
!=
真实代码
```

以真实代码为准，并同步修正文档。

---

# 三十、学习完成标准

一篇笔记不是“写完 Markdown”就算完成。

最低要求：

### 当前已有能力

```text
读代码
✓
执行链
✓
概念理解
✓
自己验证
✓
项目自测
✓
```

### 新增工程能力

```text
理解问题
✓
实现完成
✓
测试通过
✓
读懂新代码
✓
自己完成小修改
✓
笔记完成
✓
面试复述
✓
```

### 实验型能力

```text
Baseline
✓
Hypothesis
✓
Implementation
✓
Experiment
✓
Metrics
✓
Analysis
✓
Engineering Decision
✓
```

最终目标不是：

> “我看过 Course Agent。”

而是：

> **我能够把 Course Agent 当作自己真正理解和能够维护的工程系统。**
