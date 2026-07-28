# Course Agent

[![Course Agent CI](https://github.com/FlowWhite/course-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/FlowWhite/course-agent/actions/workflows/ci.yml)

Course Agent 是一个面向课程任务执行的学习工作台。它把课程资料、任务截止日期与学习计划结合起来，提供**有来源、可解释、需确认**的学习辅助，而不是直接替用户修改任务。

## 界面展示

![Course Agent 登录页](docs/images/login-page.png)

> 公开展示仅使用不含课程内容的界面图。请勿将真实课程文件、账号信息或模型密钥用于截图、issue 或日志。

## 核心能力

- 课程任务管理：注册、登录、JWT 鉴权、任务增删改查与状态切换。
- 课程资料检索：支持 PDF、DOCX、TXT、Markdown；后端本地解析并按用户、课程隔离保存。
- 资料增强 Agent：仅检索当前课程资料与任务，回答时提供文件名与页码等来源信息。
- 截止日期风险雷达：以确定性规则计算剩余天数、优先级、计划工作量、计划冲突与资料要求的风险。
- 可确认学习计划：先生成草案，再由用户确认启动；计划不会自动修改任务状态。
- 作业要求评估：在任务详情上传 PDF、DOCX、TXT 或 Markdown 作业，由课程 Agent 结合任务要求与相关课程资料给出逐项检查和补充建议。
- 任务拆解安全边界：所有任务修改仍需要用户确认；上传资料只是参考文本，不能改变 Agent 的工具权限或确认规则。

## 架构

```mermaid
flowchart LR
    U["用户"] --> W["Vue 前端"]
    W --> A["FastAPI API"]
    A --> P[("PostgreSQL")]
    A --> F["Docker 挂载的课程文件"]
    A --> X["本地解析与全文检索"]
    X --> D["DeepSeek V4 Flash"]
    D --> A
```

原始 PDF 不会直接发送给模型：后端先提取文本、按页/段分块并保存检索来源；只有与当前问题有关的片段会作为课程参考提供给 Agent。

## 隐私与安全

- 原始课程文件保存在 Docker 挂载目录，并按用户和课程保存；`.env`、运行数据库、日志和上传资料均被 Git 忽略。
- 原始 PDF 不会直接发送给模型，但 Agent 回答时会向已配置的模型提供相关文本片段。请仅上传获准处理的课程资料。
- 作业评估文件仅在本次请求的临时目录中解析；模型接收提取的有限文本、当前任务和相关资料片段，评估结果不会修改或保存作业文件。
- 公开部署时必须使用强随机的 `JWT_SECRET_KEY` 和数据库密码；不要提交或在 issue、截图、日志中粘贴任何密钥。

## 技术栈

- 后端：Python、FastAPI、OpenAI Agents SDK、DeepSeek V4 Flash
- 前端：Vue 3、Vite
- 数据与部署：PostgreSQL、Docker Compose
- 文档解析：pypdf、python-docx

## 项目结构

```text
.
├─ backend/
│  ├─ src/course_agent/
│  │  ├─ main.py                # FastAPI 装配、中间件与生命周期
│  │  ├─ api/
│  │  │  ├─ dependencies.py     # JWT 鉴权等共享依赖
│  │  │  ├─ schemas.py          # HTTP 请求模型
│  │  │  └─ routers/            # 认证、任务、资料、计划、风险与 Agent 路由
│  │  └─ ...                    # Agent、服务、数据库与领域模型
│  └─ tests/                    # 后端与 API 契约测试
├─ server.py / app.py           # 旧启动命令的兼容入口
├─ postgres/                    # PostgreSQL 初始化 SQL
├─ scripts/                     # Docker 启动、迁移与演示数据脚本
│  ├─ migrations/
│  └─ legacy/sqlite/
├─ docs/images/                 # README 展示图片
└─ web/                         # Vue 3 前端
   ├─ src/components/           # 认证、课程、任务、资料、风险与 Agent 视觉组件
   └─ src/composables/          # 课程工作台状态、API 调用与交互逻辑
```

## 本地启动

### 1. 配置环境变量

复制示例文件并填写本机的真实配置：

```powershell
Copy-Item .env.example .env
```

至少设置 `DEEPSEEK_API_KEY`、`POSTGRES_PASSWORD` 和 `JWT_SECRET_KEY`。`.env` 已被 Git 忽略，不能提交到仓库。

本地直接运行后端时，先以 editable mode 安装包：

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

### 2. 启动服务

```powershell
docker compose up --build
```

启动后访问：

- 前端：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8000/health>

`docker-compose.yml` 将 PostgreSQL 仅绑定到本机 `127.0.0.1`，供本地开发使用。部署到公网时，不要将数据库端口暴露到互联网；应通过内部网络、访问控制和备份策略管理数据库。

> 如果本机已经存在旧版 PostgreSQL 数据卷，`postgres/init.sql` 不会自动重新执行。升级到用户隔离版本前，请先备份数据库，再人工检查并执行 `scripts/migrations/001_user_scope.sql`，为所有旧课程和任务指定明确的 `user_id`。旧版 SQLite 迁移脚本还需要设置 `LEGACY_OWNER_USER_ID`，避免把历史数据无意间分配给错误用户。不要使用 `docker compose down -v` 代替迁移，它会删除本地 PostgreSQL 数据卷。

新注册用户默认只能看到属于自己的课程和任务；如果课程列表为空，需要由课程创建/导入流程为该用户建立课程，不能直接依赖另一用户的演示数据。

### 3. 创建公开演示账号（可选）

仓库提供一组脱敏的“计算机网络”合成演示数据，包含课程、实验任务和一份 Markdown 课程资料。它不会在应用启动时自动写入数据库，只有显式执行下面的命令才会创建：

```powershell
docker compose up -d --build
docker compose exec backend python /app/scripts/seed_demo_data.py --yes
```

默认演示账号为 `demo`，密码为 `course-agent-demo`。如果使用 Docker 覆盖账号信息，请把变量显式传给容器，例如 `docker compose exec -e DEMO_USERNAME=my-demo -e DEMO_PASSWORD=another-demo-password backend python /app/scripts/seed_demo_data.py --yes`。该账号和密码仅用于本地/作品集演示，禁止用于生产环境；演示资料是合成内容，不包含原始课程 PDF。

## 开发验证

后端基础测试不需要真实数据库、课程文件或模型密钥：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m compileall -q backend/src
```

前端构建验证：

```powershell
Set-Location web
npm.cmd ci
npm.cmd run build
```

## GitHub 发布安全清单

提交前务必检查暂存区：

```powershell
git status --short
git check-ignore -v .env data/sessions.db logs/agent.log .playwright-mcp
git diff --cached --name-only
```

可以提交源代码、`postgres/init.sql`、Docker 配置、启动脚本、`.env.example`、测试、CI 和本文档。禁止提交真实 `.env`、上传的课程资料、运行数据库、会话库、日志或浏览器自动化状态。

将仓库设为 **Public** 前，请先确认没有敏感内容，并使用脱敏课程资料和演示账号进行公开展示。

## 开源协作

本项目以 [MIT License](LICENSE) 发布，欢迎通过 issue 或 Pull Request 提交改进。

- `main` 分支要求通过 Pull Request 合并，并通过后端与前端构建检查。
- GitHub 已启用 Dependabot 安全更新、依赖漏洞告警、Secret scanning 和 Push protection。
- 安全问题请遵循 [SECURITY.md](SECURITY.md) 中的私密报告流程，不要公开披露可利用细节。

## 当前边界与路线图

当前版本刻意不引入向量数据库、OCR、LangGraph、多 Agent、MCP 或自动修改任务的工作流。

下一阶段重点：

1. 保存每日可用学习时间并生成按天排程；
2. 支持教师自定义作业验收量表与评分权重；
3. 在现有 CI 基础上补充 PostgreSQL 集成测试；
4. 最后再评估日历提醒、课程偏好记忆与小组协作。
