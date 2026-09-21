# Course Agent · Codex 交接文档

> 更新时间：2026-07-28（Asia/Shanghai）
> 交接原则：本次仅梳理现状；业务功能开发已暂停。
> 工作目录：`D:\project\course-agent`

## 1. 项目目标与技术栈

Course Agent 是一个面向课程任务执行的学习工作台。它把课程资料、任务截止日期与学习计划结合，为用户提供有来源、可解释且需要确认的学习辅助；Agent 不应自行修改任务。

- 后端：Python、FastAPI、OpenAI Agents SDK
- 模型：DeepSeek V4 Flash（通过项目根目录 `.env` 配置）
- 前端：Vue 3、Vite
- 数据库：PostgreSQL 16
- 部署与本地运行：Docker Compose
- 文档解析：pypdf、python-docx；支持 PDF、DOCX、TXT、Markdown

当前版本明确**不引入**向量数据库、OCR、LangGraph、MCP、多 Agent 或自动修改任务的工作流。

## 2. 已完成的功能

### 账户、课程与任务

- 用户注册、登录、JWT 鉴权与按用户隔离的数据访问。
- 课程与任务的增删改查、任务完成状态切换、优先级和截止日期管理。
- 任务列表筛选顺序为：`待完成`、`已完成`、`全部`。
- 任务详情面板使用更大展示区域；编辑、删除入口位于详情右上角。

### 课程资料与课程专属 Agent

- 课程资料按“用户 + 课程”隔离保存；原始文件保存在 Docker 挂载的 `data/` 下。
- 后端解析文件文本并写入 PostgreSQL；`document_chunks.search_vector` 使用 PostgreSQL 全文检索。
- PDF 不直接发送给模型；只将与当前问题相关的提取片段传给模型，并在回答中提供资料来源。
- 每门课程有独立的 Agent 上下文：只能查询当前课程的任务与资料。
- Agent 的任务修改仍必须经用户确认。

### 风险、计划与作业评估

- 截止日期风险雷达：按剩余天数、优先级、计划工作量、计划冲突和资料要求计算风险。
- 学习计划：先生成草案，用户确认后才激活；不会自动修改任务状态。
- 已移除前端的“暂停 / 恢复计划”操作按钮。数据库和后端仍保留计划状态字段及相关路由，是否重新启用需单独产品决策。
- 作业要求评估：在任务详情底部上传 PDF、DOCX、TXT 或 Markdown；课程 Agent 结合任务描述和相关课程资料生成逐项检查与补充建议。
  - 提交的作业文件只在本次请求的临时目录解析，不保存至数据库或课程资料目录。
  - 评估结果不修改任务，也不持久化为历史记录。

### 作品集、文档与工程化

- 公开的合成“计算机网络”演示数据及演示账号种子脚本。
- README 已包含登录页、工作台/任务详情截图、启动说明、隐私提示与开源协作说明。
- 使用 MIT License、CI、Dependabot、Secret scanning / Push protection 相关仓库配置。

## 3. 尚未完成或需要后续决策的事项

按 README 的路线图，建议后续处理：

1. 保存用户每日可用学习时间，并生成按天排程。
2. 支持教师自定义作业验收量表与评分权重。
3. 补充真实 PostgreSQL 集成测试（现有测试以单元与 API 契约测试为主）。
4. 再评估日历提醒、课程偏好记忆和小组协作。

另外需要明确设计再实现的事项：

- 是否恢复学习计划“暂停 / 恢复”交互，以及恢复后如何体现执行闭环。
- 是否需要保存作业评估历史、评分版本和附件；当前设计刻意不保存。
- 是否把 Agent 错误同时输出到容器标准输出，减少仅从 `logs/agent.log` 排障的成本。
- PR #15（工作台截图文档）仍是 Draft，需在 GitHub 标记为 Ready for review 并合并到 `main`。

## 4. 最近一轮修改过的关键文件

### 作业要求评估（已通过 PR #14 合并）

- `backend/src/course_agent/models.py`：作业评估的输入、逐项要求检查与结果模型。
- `backend/src/course_agent/agent_runtime.py`：调用 DeepSeek 生成评估、解析与校验结果；也包含学习计划时长下限的归一化逻辑。
- `backend/src/course_agent/api/routers/tasks.py`：`POST /api/v1/tasks/{task_id}/assessment`，含临时文件、安全解析、大小与类型限制。
- `backend/tests/test_task_submission_assessment.py`：作业评估测试。
- `backend/tests/test_api_route_contract.py`：路由契约覆盖。
- `web/src/components/TaskList.vue`：任务筛选标签顺序。
- `web/src/components/TaskDetailPanel.vue`：详情右上角编辑/删除、移除计划暂停/恢复按钮、作业评估 UI。
- `web/src/composables/useCourseWorkspace.js`：作业评估请求、加载状态、错误状态与计划确认动作。
- `web/src/App.vue`：相关布局和视觉样式。

### README 截图（已推送，待 PR #15 合并）

- `docs/images/workspace-task-detail.png`：公开演示用工作台截图。
- `README.md`：插入截图并明确使用虚构演示课程和任务。

本交接文件本身为本次唯一新增文件：`docs/CODEX_HANDOFF.md`。

## 5. 当前数据库、后端、前端与 API 结构

### 数据库

数据库初始化定义在 `postgres/init.sql`：

| 表 | 用途 |
| --- | --- |
| `users` | 用户、密码哈希、启用状态 |
| `courses` | 课程；以 `user_id` 归属用户 |
| `tasks` | 任务；以 `user_id` 和 `course_id` 双重关联 |
| `course_files` | 上传资料的元数据、解析状态、文件哈希 |
| `document_chunks` | 资料分段、页码与 PostgreSQL 全文检索向量 |
| `learning_plans` | 计划草案、确认、激活、暂停等生命周期状态 |
| `learning_plan_steps` | 计划步骤、预计时长、交付物与完成状态 |

`backend/src/course_agent/postgres_database.py` 中的 `ensure_application_schema()` 会在 FastAPI 生命周期启动时执行兼容性建表/升级检查。已有 Docker PostgreSQL 数据卷不会重新执行 `postgres/init.sql`；旧数据升级必须先备份，再审阅并执行 `scripts/migrations/001_user_scope.sql`。

### 后端

后端包根目录：`backend/src/course_agent/`。

- `main.py`：FastAPI 装配、CORS、限流、中间件、生命周期和路由注册；健康检查为 `GET /health`。
- `api/dependencies.py`：JWT 等共享依赖。
- `api/schemas.py`：HTTP 请求/响应模型。
- `api/routers/`：`auth.py`、`courses.py`、`tasks.py`、`files.py`、`plans.py`、`insights.py`、`chat.py`。
- `agent_runtime.py`：DeepSeek/Agents SDK 运行时、课程上下文、计划草案与作业评估。
- `tools.py`：供 Agent 调用的受限工具；任务类查询必须使用 `list_tasks`，并通过相对导入读取当前用户/课程上下文。
- `app_logger.py`：Agent 排障日志，通常写到挂载的 `logs/agent.log`。

### 前端

前端目录：`web/`。

- `src/App.vue`：整体工作台布局与页面级状态绑定。
- `src/components/`：认证、课程侧栏、任务清单、任务详情、资料、风险雷达、学习计划、Agent 面板等组件。
- `src/composables/useCourseWorkspace.js`：课程工作台状态、API 调用、计划确认、作业评估等交互逻辑。

### API 概览

所有业务接口在 `/api/v1` 下，由各路由模块注册。主要分组：

| 分组 | 路由模块 | 典型用途 |
| --- | --- | --- |
| 认证 | `auth.py` | 注册、登录、当前用户 |
| 课程 | `courses.py` | 当前用户课程列表与课程操作 |
| 任务 | `tasks.py` | 任务 CRUD、状态、作业评估 |
| 资料 | `files.py` | 上传、解析状态、全文检索资料 |
| 计划 | `plans.py` | 草案、确认和计划读取 |
| 风险 | `insights.py` | 截止日期风险与建议 |
| Agent | `chat.py` | 当前课程限定的对话 |

作业评估接口：`POST /api/v1/tasks/{task_id}/assessment`。它会接受一个支持类型的上传文件，解析有限文本并返回评估；不要把它当作文件存储接口。

## 6. 运行、构建与测试命令

在 PowerShell 中先进入项目根目录：

```powershell
Set-Location D:\project\course-agent
```

首次配置：

```powershell
Copy-Item .env.example .env
# 在 .env 中填写 DEEPSEEK_API_KEY、POSTGRES_PASSWORD、JWT_SECRET_KEY
```

Docker 启动、状态与日志：

```powershell
docker compose up -d --build
docker compose ps
docker compose logs backend --tail 200
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/health`

创建合成演示数据（仅在项目根目录执行）：

```powershell
docker compose exec backend python /app/scripts/seed_demo_data.py --yes
```

默认本地演示账号：`demo` / `course-agent-demo`。仅用于演示，不可用于生产。

后端验证：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -m compileall -q backend\src
```

前端依赖与构建：

```powershell
Set-Location web
npm.cmd ci
npm.cmd run build
```

更新代码后，Docker 不会因 `git pull` 自动更新运行镜像；需要回到项目根目录重建：

```powershell
docker compose up -d --build --force-recreate backend frontend
```

## 7. 已知问题、常见报错与排障入口

### Agent 回复“任务数据查询失败”，但 `/api/v1/chat` 为 200

HTTP 200 只表示对话端点正常返回；Agent 工具调用异常可能被包装为自然语言错误回复。先查看：

```powershell
Get-Content .\logs\agent.log -Tail 100
```

已修复过一个根因：`tools.py` 读取当前用户/课程上下文时必须使用包内相对导入（`from .agent_runtime import ...`），不能用顶层 `from agent_runtime import ...`。如果他人已经 `git pull` 仍报错，优先核验分支和容器实际源码，再重建后端镜像；`docker compose restart` 不会更新镜像。

```powershell
git branch --show-current
docker compose exec backend python -c "import inspect; from course_agent import tools; print(inspect.getsourcefile(tools)); print(inspect.getsource(tools._current_document_user_id))"
docker compose up -d --build --force-recreate backend
```

### 前端显示“无法连接到 API 服务”或长期等待后端

通常是 Docker Desktop / 后端容器未运行，或 8000 端口未就绪。检查：

```powershell
docker compose ps
docker compose logs backend --tail 200
Invoke-WebRequest http://127.0.0.1:8000/health
```

### 学习计划草案出现 `estimated_minutes` 小于 5 的 Pydantic 错误

新代码已在生成后将计划步骤时长限制在 5 至 480 分钟。若仍报旧错误，通常是容器仍使用旧镜像；按上面的 `--build --force-recreate backend` 更新。

### 升级后课程列表为空或出现 `user_id` 相关数据库错误

新版本按用户隔离课程和任务。旧数据卷不会自动重新执行初始化 SQL；务必先备份，再按 `scripts/migrations/001_user_scope.sql` 审核迁移并为历史数据指定正确的用户。不要以 `docker compose down -v` 代替迁移，否则会删除本地 PostgreSQL 数据卷。

### `docker compose exec ...` 报 `no configuration file provided: not found`

命令不在包含 `docker-compose.yml` 的项目根目录执行。先运行：

```powershell
Set-Location D:\project\course-agent
```

## 8. 当前 Git 状态与 diff 摘要

复核结果（2026-07-28，Asia/Shanghai）：

- 当前分支：`main`，与 `origin/main` 一致，`HEAD` 为 `6ed0036 Merge pull request #15 from FlowWhite/agent/task-detail-assessment`。
- PR #14 的作业评估功能和 PR #15 的 README 截图文档均已合并到 `main`；原 `agent/task-detail-assessment` 远端分支已删除。
- 工作区没有业务代码 diff；仅有本交接文档 `docs/CODEX_HANDOFF.md` 尚未纳入版本控制。
- 本次复核前，本文档没有执行 `git add`、`git commit` 或 `git push`；应保持为独立的 `docs: add Codex handoff` 提交，避免混入业务变更。

## 9. 推荐的下一步执行顺序

1. PR #15 已合并；为本交接文档做一次独立的 docs 提交与 PR，避免混入业务变更。
2. 在干净的 `main` 分支上执行后端测试、编译检查和前端构建，确认基线。
3. 如继续开发，先确定“每日可用时间 → 按天排程”的数据模型、交互确认点与风险规则，再写迁移和 API。
4. 为 PostgreSQL 增加集成测试，并在 CI 中提供可隔离的临时数据库。
5. 处理课程 Agent 问题时，先复现并保存 `logs/agent.log` 的实际异常，再改动工具上下文或提示词；不要仅根据前端的 200 响应判断问题已解决。

## 10. 重要约束与禁止随意修改的内容

- **绝不提交或展示真实密钥与隐私数据**：`.env`、真实课程文件、上传目录、数据库、会话库、日志、浏览器自动化状态均应保持 Git 忽略。不要把 `docker compose config` 的完整输出贴入 issue、PR、截图或日志，因为它会解析环境变量。
- **不要绕开用户确认**：Agent 可以生成解释、草案、建议和评估，但任何任务新增、编辑、删除、状态改变都必须由用户明确确认。
- **维持用户/课程隔离**：所有课程、任务、文件、全文检索、计划、Agent 工具查询必须同时按已鉴权用户和当前课程限制；不能为了方便移除 `user_id` 条件。
- **维持文件处理边界**：PDF 先在后端提取文字；不要把原始 PDF 直接提交给模型。作业评估文件当前为临时解析，不要在未设计授权、保留期限和删除策略前改为永久保存。
- **不要贸然重置 Docker 数据**：禁止把 `docker compose down -v`、`docker volume rm`、`docker system prune --volumes` 当作常规修复手段。特别是 `postgres_data` 保存本地用户数据。
- **不要回退已合并修复**：任务查询要走 `list_tasks`；工具上下文导入必须使用包内相对导入；学习计划的模型输出时长必须保持 5 分钟下限。
- **不要改动公开演示边界**：README/GitHub 截图只能使用合成数据。`demo` / `course-agent-demo` 仅是本地作品集演示账号，不能作为生产账号或默认公开凭据。
- **不要假设 `git pull` 会更新服务**：代码更新后需要重建相关 Docker 镜像；修改数据库结构前先备份并提供可审阅迁移。
- **修改文档或截图时仍要做安全检查**：确认没有用户名、真实课程、密钥、Token、绝对敏感路径或日志中的内部数据。
