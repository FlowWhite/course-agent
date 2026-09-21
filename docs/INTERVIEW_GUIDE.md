# Course Agent 面试导读

> 面向后端 / 全栈岗位的代码导读与面试复习手册。
>
> 学习方式：先追踪真实业务链路，再补充框架概念；每个主题都要能回答“代码在哪里、数据怎么走、为什么这样设计、有什么取舍”。

## 0. 先记住项目是什么

Course Agent 是一个“课程任务与资料管理 + 课程专属 Agent”的全栈应用。它把课程、任务截止日期、课程资料和学习计划放在同一个工作台中，并要求 Agent 的建议有来源、可解释、需要确认。

项目当前的核心边界：

- Agent 可以查询任务、检索资料、生成风险和计划建议。
- Agent 不应绕过用户确认直接修改任务。
- 所有业务数据都必须同时按用户和课程隔离。
- 原始 PDF 先在后端提取文字，模型只接收相关文本片段。
- 当前刻意不引入向量数据库、OCR、LangGraph、MCP 或多 Agent。

核心链路：

```text
Vue 工作台
  → FastAPI 路由与 JWT 依赖
  → PostgreSQL / 文件存储 / 文档解析
  → 课程 Agent 与受限工具
  → DeepSeek OpenAI 兼容接口
  → ToolResponse 返回 Vue 状态
```

## 1. 技术栈地图

| 层次 | 项目技术 | 需要掌握的面试概念 |
| --- | --- | --- |
| 后端 API | Python、FastAPI、Pydantic | 路由、依赖注入、请求校验、异常和状态码 |
| 鉴权 | JWT、密码哈希、`get_current_user` | Bearer Token、身份和权限边界 |
| 数据库 | PostgreSQL 16、SQL、全文检索 | 外键、索引、事务、用户隔离、GIN / `tsvector` |
| AI | OpenAI Agents SDK、DeepSeek V4 Flash | Agent、工具调用、上下文、模型错误、提示注入 |
| 文件 | `pypdf`、`python-docx`、TXT / Markdown | 文件签名、大小限制、临时目录、文本分块 |
| 前端 | Vue 3、Vite、原生 `fetch` | `ref`、`computed`、Composable、组件通信、状态同步 |
| 部署 | Docker Compose、Dockerfile | 服务、端口、网络、环境变量、数据卷、健康检查 |
| 验证 | `unittest`、API 契约测试、CI | 单元测试、边界测试、构建和回归验证 |

建议的代码入口：

- [README.md](../README.md)：产品边界、启动命令和安全约束。
- [main.py](../backend/src/course_agent/main.py)：FastAPI 装配、中间件和路由注册。
- [agent_runtime.py](../backend/src/course_agent/agent_runtime.py)：模型配置、Agent、会话和用户/课程上下文。
- [postgres_data_service.py](../backend/src/course_agent/postgres_data_service.py)：课程和任务 SQL 数据访问。
- [tools.py](../backend/src/course_agent/tools.py)：Agent 能调用的受限工具。
- [useCourseWorkspace.js](../web/src/composables/useCourseWorkspace.js)：前端 API 和工作台状态。

## 2. 如何高效阅读这个项目

不要从第一个文件开始逐行阅读。每次学习固定完成四步：

1. **先说问题**：这个模块解决什么用户问题？
2. **再画调用链**：入口、校验、服务、数据库或模型、返回值分别在哪里？
3. **最后看取舍**：为什么现在这样做？替代方案是什么？安全边界在哪里？
4. **用面试语言复述**：用 30 秒和 2 分钟各讲一次。

每个模块只需要记住三类内容：

- 一个入口函数或组件；
- 一条完整数据流；
- 两个设计理由和一个局限。

## 3. 第 1 周：启动流程与 FastAPI

### 3.1 启动与路由装配

阅读 [main.py](../backend/src/course_agent/main.py) 的顺序：

1. `lifespan()` 启动时调用 `ensure_application_schema()`，保证应用表结构已准备好。
2. `FastAPI(...)` 创建应用，并配置 CORS。
3. `rate_limit_middleware()` 按客户端 IP 和请求路径限流，健康检查排除在外。
4. `add_utf8_charset()` 给 JSON 响应补充 UTF-8 声明。
5. 通过 `app.include_router(...)` 注册认证、课程、任务、文件、计划、风险和聊天路由。
6. `GET /health` 只返回服务可用状态，不依赖业务数据。

面试表达：

> `main.py` 只负责应用级装配，把跨切面逻辑放在中间件和生命周期中，把业务接口拆到 router。这样入口文件不会混入任务 SQL 或 Agent 业务细节，后续测试和维护更容易。

### 3.2 登录链路

真实链路：

```text
POST /api/v1/auth/login
  → LoginRequest 校验
  → authenticate_user_data()
  → create_access_token(user_id, username)
  → { access_token, token_type, user }
  → Vue 保存到 sessionStorage
```

关键代码：

- [auth.py](../backend/src/course_agent/api/routers/auth.py)：`login_api()`、`register_api()`。
- [schemas.py](../backend/src/course_agent/api/schemas.py)：`LoginRequest`、`RegisterRequest`。
- [dependencies.py](../backend/src/course_agent/api/dependencies.py)：`get_current_user()`。
- [auth_security.py](../backend/src/course_agent/auth_security.py)：token 和密码安全逻辑。

必须理解的区别：

- **认证（Authentication）**：你是谁，由 JWT 证明。
- **授权（Authorization）**：你能访问哪些课程和任务，由查询中的 `user_id`、`course_id` 约束保证。

### 3.3 任务 API 链路

任务路由位于 [tasks.py](../backend/src/course_agent/api/routers/tasks.py)：

| API | 函数 | 用途 |
| --- | --- | --- |
| `GET /api/v1/tasks` | `list_tasks_api()` | 按课程和 `all/todo/done` 筛选 |
| `GET /api/v1/tasks/{task_id}` | `get_task_detail_api()` | 查询任务详情 |
| `POST /api/v1/tasks` | `create_task_api()` | 新建任务 |
| `PATCH /api/v1/tasks/{task_id}` | `update_task_api()` | 修改普通字段 |
| `PATCH /api/v1/tasks/{task_id}/status` | `update_task_status_api()` | 修改完成状态 |
| `DELETE /api/v1/tasks/{task_id}` | `delete_task_api()` | 必须携带准确确认文本 |
| `POST /api/v1/tasks/{task_id}/assessment` | `assess_task_submission_api()` | 临时解析作业并评估 |

典型查询结构：

```python
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = int(current_user["id"])
    tasks = list_tasks_data(user_id=user_id, course=course, status=status)
    return ToolResponse(success=True, data=[...])
```

面试时要指出：路由层负责 HTTP 参数、鉴权和响应；`postgres_data_service.py` 负责 SQL；模型层负责结构化数据。分层可以降低耦合，但需要维护多个对象和调用边界。

## 4. 第 1 周：PostgreSQL 与用户隔离

### 4.1 数据模型

数据库定义在 [postgres/init.sql](../postgres/init.sql)：

```text
users
  └─ courses(user_id)
       ├─ tasks(user_id, course_id)
       ├─ course_files(user_id, course_id)
       │    └─ document_chunks(file_id, search_vector)
       └─ learning_plans(user_id, course_id)
            └─ learning_plan_steps(plan_id)
```

`tasks` 同时保存 `user_id` 和 `course_id`。这不是重复无意义字段，而是让查询可以同时表达“属于谁”和“属于哪门课”，并防止跨用户、跨课程访问。

主要索引：

- `idx_tasks_user_course(user_id, course_id)`：常见工作台筛选。
- `idx_tasks_status(status)`：按完成状态查询。
- `idx_document_chunks_search_vector`：PostgreSQL GIN 全文检索。

### 4.2 数据访问规则

在 [postgres_data_service.py](../backend/src/course_agent/postgres_data_service.py) 中，列表和详情查询都先构造用户条件，例如：

```sql
WHERE t.user_id = %s
  AND t.course_id = %s
```

面试回答要强调：不能只在前端隐藏其他课程，也不能只校验 `course_id`。前端是不可信边界，真正的隔离必须在后端查询和写入层再次执行。

### 4.3 资料全文检索

`document_chunks` 保存：

- 文件 ID；
- 文本内容；
- 页码或来源位置；
- PostgreSQL `tsvector` 检索向量。

项目选择 PostgreSQL 全文检索，而不是向量数据库，原因是当前需求主要是本地课程资料的关键词/文本检索，系统复杂度和部署成本更低。局限是语义相似度检索能力不如 embedding + 向量数据库。

## 5. 第 2 周：文件解析与资料增强

### 5.1 课程资料上传链路

真实链路：

```text
POST /api/v1/files
  → sanitize_original_filename()
  → 流式写入临时上传文件
  → 20 MB 大小限制
  → validate_file_signature()
  → create_course_file_data()
  → parse_document()
  → replace_document_chunks_data()
```

关键文件：

- [files.py](../backend/src/course_agent/api/routers/files.py)：上传、删除和元数据接口。
- [document_parser.py](../backend/src/course_agent/document_parser.py)：PDF、DOCX、文本解析与分块。
- [course_material_service.py](../backend/src/course_agent/course_material_service.py)：文件存储、哈希和检索。

为什么同时检查扩展名和文件签名？扩展名由用户提供，不能证明内容类型；签名检查可以阻止明显的类型伪装。文件大小限制和分块则控制内存、数据库和模型请求的成本。

### 5.2 作业评估的临时文件边界

`assess_task_submission_api()` 与课程资料上传不同：

- 作业文件写入 `TemporaryDirectory`；
- 解析后只保留有限文本；
- 文本过长时保留头尾，中间内容用标记替代；
- 评估结果只返回本次请求，不保存作业附件和历史记录。

面试表达：

> 课程资料是可重复检索的用户资产，需要保存元数据和解析分块；作业提交是一次性的评估输入，当前只需要短期处理，因此采用临时目录可以降低隐私、保留期限和清理策略的复杂度。

## 6. 第 2 周：Agent、工具与安全边界

### 6.1 模型配置

在 [agent_runtime.py](../backend/src/course_agent/agent_runtime.py) 中：

1. `load_project_env()` 从项目根目录读取本地 `.env`。
2. `configure_model()` 创建 `AsyncOpenAI`，`base_url` 指向 DeepSeek。
3. Agents SDK 使用 `chat_completions` 模式。
4. `use_for_tracing=False` 并关闭 tracing，避免 DeepSeek key 被当成 OpenAI tracing 凭据。
5. `create_course_agent()` 创建绑定课程名称和课程 ID 的 Agent。

这是“OpenAI 兼容协议”而不是“使用 OpenAI 模型”：SDK 使用相同的客户端协议，实际请求地址和密钥由 DeepSeek 配置决定。

### 6.2 用户与课程上下文

聊天路由 [chat.py](../backend/src/course_agent/api/routers/chat.py) 的关键步骤：

```text
校验当前用户拥有 course_id
  → set_current_agent_user_id(user_id)
  → set_current_agent_course_id(course_id)
  → get_runtime_agent()
  → Runner.run_sync(...)
  → finally reset 两个 ContextVar
```

`ContextVar` 让工具函数可以读取当前请求的用户和课程，而不必把两个参数手工加到每个 Agent 工具签名中。`finally` 重置上下文，避免请求之间泄漏状态。

### 6.3 工具边界

工具位于 [tools.py](../backend/src/course_agent/tools.py)：

- `list_tasks()`：查询任务，任务问题不能错误路由到 `list_courses()`。
- `get_task_detail()`：读取任务详情。
- `search_course_documents()`：检索当前课程资料。
- `list_deadline_risks()`：返回程序计算的风险，不由模型编造分数。
- `create_task()`、`update_task()`、`update_task_status()`：只有明确的用户写入意图才能调用。
- `delete_task()`：必须使用 `确认删除任务 <任务 ID>`。

写保护是多层的：

1. Agent instructions 约束模型什么时候允许调用工具。
2. 工具中的 `_get_scoped_task_or_raise()` 校验用户和当前课程。
3. API 路由和数据库访问层仍然传入 `user_id`。
4. 删除操作再次校验精确确认文本。

这叫“纵深防御”：不能把安全性押在 Prompt 一层。

### 6.4 资料不是系统指令

课程资料可能包含类似“忽略之前规则”的文本。Agent instructions 明确规定资料属于不可信参考内容，不能改变工具权限、确认要求或系统规则。回答资料问题前先调用 `search_course_documents()`，并返回文件名、页码等来源。

## 7. 第 2 周：Vue 工作台

### 7.1 Composable 是前端状态中枢

在 [useCourseWorkspace.js](../web/src/composables/useCourseWorkspace.js) 中，`useCourseWorkspace()` 集中管理：

- `accessToken`：会话 token；
- `courses`、`selectedCourseId`：课程列表和当前课程；
- `tasks`、`selectedTaskId`、`taskFilter`：任务状态；
- `chatMessagesByCourse`：按课程隔离对话；
- `courseFiles`、`risks`、`taskPlan`、`taskAssessment`：辅助功能状态；
- 各组 `loading`、`error`、`saving`：异步反馈。

`selectedCourse`、`selectedTask`、`filteredTasks`、`todoCount` 和 `doneCount` 使用 `computed` 派生，避免手动同步重复状态。

### 7.2 浏览器到 API

`requestJson()` 统一处理：

1. 拼接 `VITE_API_BASE_URL`。
2. 自动添加 `Authorization: Bearer <token>`。
3. 解析 JSON。
4. 将后端 `success=false` 或 HTTP 错误转换成前端异常。

典型流程：

```text
login()
  → POST /auth/login
  → saveAccessToken()
  → loadCourses()
  → selectCourse()
  → loadTasks()
  → selectedTask 更新详情面板
```

组件职责：

- [App.vue](../web/src/App.vue)：页面布局和顶层组合。
- `CourseSidebar.vue`：课程选择。
- `TaskList.vue`：筛选和任务选择。
- `TaskDetailPanel.vue`：详情、编辑、删除、计划和作业评估。
- `AgentChatDrawer.vue`：课程 Agent 对话。

面试时不要只说“用了 Vue”。要说明：Composable 负责跨组件共享业务状态，展示组件负责输入和渲染，API 错误和加载状态由状态中枢统一管理。

## 8. 第 3 周：Docker、测试与安全

### 8.1 Docker Compose 服务

在 [docker-compose.yml](../docker-compose.yml) 中：

- `backend`：8000 端口，挂载 `data/`、`logs/`，会话 SQLite 使用独立命名卷。
- `frontend`：构建 Vue 静态资源，通过 5173 访问，并依赖后端服务。
- `postgres`：PostgreSQL 16，数据库端口只绑定到本机 `127.0.0.1`。
- `postgres_data`：持久化数据库数据。
- `agent_session_data`：避免 Windows 绑定目录上的 SQLite WAL 文件锁问题。

`depends_on` 只表达启动顺序，不等价于应用已经准备好；数据库还通过 `pg_isready` healthcheck 表示健康状态。

### 8.2 现有验证命令

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -m compileall -q backend\src

Set-Location web
npm.cmd ci
npm.cmd run build
```

测试重点：

- `test_api_route_contract.py`：路由存在性和契约。
- `test_agent_tool_context.py`：Agent 工具上下文和课程隔离。
- `test_document_parser.py`：文件类型、解析和分块。
- `test_task_submission_assessment.py`：作业评估输入边界。
- `test_rate_limit.py`：限流行为。
- `test_task_plan_draft_validation.py`：计划步骤时长范围。

### 8.3 安全与运维追问

面试回答要覆盖：

- `.env`、数据库、上传文件和日志不能提交 Git。
- JWT secret 和数据库密码必须使用强随机值。
- 不用 `docker compose down -v` 代替数据库迁移，因为会删除数据卷。
- Agent 错误要结合 `logs/agent.log`，不能仅凭聊天接口 200 判断成功。
- 用户隔离必须同时存在于路由、服务和 SQL 层。

## 9. 三条必须会讲的业务链路

### 链路 A：登录后加载任务

```text
AuthScreen
  → useCourseWorkspace.login()
  → POST /api/v1/auth/login
  → auth_service.authenticate_user_data()
  → auth_security.create_access_token()
  → sessionStorage
  → loadCourses()
  → selectCourse()
  → GET /api/v1/tasks?course=...
  → list_tasks_data(user_id, course, status)
  → PostgreSQL
  → TaskList.vue
```

回答重点：认证和授权是两层；课程切换会改变后续任务和 Agent 的范围。

### 链路 B：课程资料增强问答

```text
用户在 AgentChatDrawer 提问
  → POST /api/v1/chat
  → 校验用户拥有课程
  → 设置 ContextVar(user_id, course_id)
  → Runner.run_sync()
  → search_course_documents()
  → PostgreSQL 全文检索 document_chunks
  → 返回文件名 / 页码 / 片段
  → DeepSeek 生成带来源回答
  → reset ContextVar
```

回答重点：这是“检索后生成”，当前检索实现是 PostgreSQL 全文检索，不是向量数据库。

### 链路 C：作业要求评估

```text
TaskDetailPanel 上传作业
  → POST /api/v1/tasks/{task_id}/assessment
  → 校验任务归属
  → TemporaryDirectory 写入临时文件
  → 文件签名和 20 MB 限制
  → parse_document()
  → 截断过长文本
  → 当前课程资料检索
  → generate_task_submission_assessment()
  → 返回评估，不保存附件、不修改任务
```

回答重点：输入临时化、文本有界、资料和任务都限定在当前用户课程内。

## 10. 面试问题与回答模板

### FastAPI / 后端

1. **为什么用依赖注入获取当前用户？**

   `get_current_user` 统一解析 Bearer JWT，路由只接收可信的用户对象，避免每个接口重复写 token 解析逻辑。

2. **FastAPI 路由和数据服务为什么分开？**

   路由处理 HTTP、鉴权和序列化；数据服务处理 SQL 和领域数据，减少协议层与存储层耦合。

3. **`ToolResponse` 的作用是什么？**

   统一成功、数据和错误字段，让前端和 Agent 工具都能稳定解析；真正的 HTTP 错误仍通过状态码表达。

4. **如何避免跨用户访问任务？**

   从 JWT 得到 `user_id`，并把它传入每个查询和写入函数；SQL 的 `WHERE` 和更新条件同时限制用户和资源 ID。

5. **为什么删除任务需要确认文本？**

   删除不可逆，先展示详情，再要求用户输入包含任务 ID 的精确确认，降低 Agent 误删和歧义操作风险。

### PostgreSQL / 文件

6. **为什么任务同时保存 `user_id` 和 `course_id`？**

   `user_id` 保证租户隔离，`course_id` 保证课程范围；联合索引也能优化工作台常用查询。

7. **为什么用 PostgreSQL 全文检索而不是向量数据库？**

   当前需求是本地课程资料检索，全文检索部署简单、可解释且能返回页码；代价是语义召回能力有限。

8. **为什么文件要检查签名？**

   文件名和扩展名可以伪造，签名检查能确认内容类型；再配合大小限制和临时文件控制资源和风险。

9. **为什么作业文件不保存？**

   当前功能只需要一次评估，临时解析减少附件保留、隐私合规和删除策略的复杂度。

10. **数据库初始化 SQL 会在每次启动时执行吗？**

    Docker 初始化脚本只对新数据卷生效；已有卷升级必须备份并执行审阅过的迁移，不能用删除卷解决。

### Agent / AI 安全

11. **DeepSeek 如何接入 Agents SDK？**

    通过 `AsyncOpenAI` 的 OpenAI 兼容接口设置 DeepSeek `base_url` 和专用 key，再让 Agents SDK 使用 chat completions；同时禁用 tracing。

12. **Agent 如何知道当前用户和课程？**

    聊天路由先验证课程归属，再用 `ContextVar` 设置用户和课程上下文；工具从上下文读取范围，并在 `finally` 中重置。

13. **为什么不能只靠 Prompt 防止 Agent 误操作？**

    模型输出不是真正的安全边界；工具、路由和 SQL 还要重复校验用户、课程、任务和删除确认。

14. **资料中的提示注入如何处理？**

    资料被定义为不可信参考数据；查询资料时只把相关片段作为上下文，不能让资料改变工具权限或系统规则。

15. **Agent 返回 200 但用户看到查询失败，如何排查？**

    先看 `logs/agent.log`，再确认容器实际源码、Agent 工具上下文和模型调用错误；HTTP 200 只代表聊天端点完成了响应。

### Vue / 工程化

16. **为什么使用 Composable？**

    `useCourseWorkspace` 集中管理课程工作台的异步请求和状态，多个组件共享同一份状态，避免把业务逻辑散落在页面中。

17. **`ref` 和 `computed` 分别解决什么问题？**

    `ref` 保存可变状态，`computed` 从已有状态派生筛选列表、选中任务和数量，避免重复手动同步。

18. **Docker 的数据卷有什么作用？**

    数据卷让数据库和 Agent 会话在容器重建后仍可保留；代码更新时重建镜像，数据不应通过删除卷来“修复”。

19. **为什么要同时做单元测试、契约测试和构建？**

    单元测试验证局部逻辑，契约测试验证接口形状，构建验证依赖和打包链路；三者覆盖不同失败面。

20. **这个项目最重要的设计取舍是什么？**

    优先选择可解释、可确认、易部署的方案：PostgreSQL 全文检索代替向量库，课程级 Agent 代替多 Agent，用户确认代替自动修改任务。

## 11. 2 分钟项目介绍模板

> Course Agent 是一个 Vue 3 + FastAPI + PostgreSQL 的课程学习工作台。用户可以管理课程任务、上传课程资料、查看截止日期风险，并和限定在当前课程内的 Agent 对话。后端通过 JWT 实现身份认证，通过 `user_id` 和 `course_id` 在路由、服务和 SQL 层做数据隔离。课程资料先由后端解析和分块，再使用 PostgreSQL 全文检索取出相关片段，DeepSeek 只接收与问题相关的文本并给出带来源回答。Agent 可以生成建议和计划草案，但任务修改必须经过用户确认。系统使用 Docker Compose 运行 PostgreSQL、FastAPI 和 Vue，并通过单元测试、API 契约测试和构建检查保证基线质量。

## 12. 学习与验收清单

### 第 1 周

- [ ] 能解释 `main.py` 的生命周期、中间件和路由注册。
- [ ] 能从登录 API 追到 JWT 和 `get_current_user`。
- [ ] 能从任务 API 追到 `list_tasks_data()` 和 SQL。
- [ ] 能说明认证和授权的区别。
- [ ] 能解释 `user_id`、`course_id` 和联合索引的作用。

### 第 2 周

- [ ] 能画出课程文件上传、解析和全文检索链路。
- [ ] 能解释 `ContextVar` 如何限制 Agent 范围。
- [ ] 能说明 Agent 工具为什么需要多层安全校验。
- [ ] 能解释资料提示注入和删除确认边界。
- [ ] 能从 `useCourseWorkspace` 说明课程、任务和聊天状态如何联动。

### 第 3 周

- [ ] 能解释三个 Compose 服务、两个数据卷和健康检查。
- [ ] 能运行后端测试、编译检查和前端构建。
- [ ] 能根据日志判断问题属于 API、数据库、解析器还是 Agent。
- [ ] 能完成 2 分钟项目介绍。
- [ ] 能回答上面的 20 个问题，并为至少 5 个问题补充项目取舍。

## 13. 推荐学习顺序

```text
README / 架构
  → main.py / auth.py / dependencies.py
  → tasks.py / postgres_data_service.py / init.sql
  → files.py / document_parser.py / course_material_service.py
  → chat.py / agent_runtime.py / tools.py
  → useCourseWorkspace.js / App.vue / 任务组件
  → docker-compose.yml / tests / migrations
  → 模拟面试与项目介绍
```

每读完一组文件，立刻用自己的话回答三个问题：

1. 请求从哪里进入？
2. 哪一层真正保证了正确性和安全？
3. 如果这一层失败，我会看什么错误、日志或测试？
