# Course Agent 项目结构重构可行性调研笔记

调研日期：2026-07-26
调研目标：评估将当前 Course Agent 从根目录平铺脚本重构为适合 GitHub 展示和长期维护的分层单仓库结构的可行性、风险与迁移路径。

## 关键问题

1. 当前模块依赖、Docker、启动脚本、测试和 GitHub CI 对文件路径的耦合程度如何？
2. FastAPI、Vue 和 Python 官方推荐的组织方式能否在不改变产品功能的前提下逐步采用？
3. 哪些迁移可一次完成，哪些必须分阶段执行并保持回滚能力？

## 发现

### 当前仓库证据

- 后端活跃模块仍平铺在仓库根目录；`server.py` 约 30 KB，聚合了认证、课程资料、任务、学习计划、风险雷达与聊天接口。
- `App.vue` 约 71 KB、3318 行，单文件同时管理认证、课程、任务、资料上传、风险、计划与 Agent 聊天状态和 UI。
- 后端模块目前通过根目录绝对导入互相引用；Dockerfile 通过 `COPY *.py ./` 复制源码，启动命令为 `uvicorn server:app`。Windows 启动脚本、README 和 CI 也引用这些路径。
- 测试使用根目录导入，例如 `from document_parser import ...`，因此一次性移动目录会同时影响容器、测试、开发启动和文档。

### 官方结构建议

- FastAPI 官方建议将大应用组织为 Python 包，使用 `APIRouter` 将不同领域路由拆入子模块，再由主应用集中 `include_router()`。
- PyPA 说明 `src/` 布局把可导入代码和仓库配置隔离，可避免开发目录意外进入 import path；代价是开发/测试需要 editable install 或明确 `PYTHONPATH`。
- Vue 官方将单文件组件作为模块化基础；复杂前端宜将页面、可复用组件、API 客户端和 composables 按功能拆开，而不是保留单一巨型根组件。

### 可行性判断

可行性：高。当前 API、数据库和 Agent 已按服务概念分出多个模块，拆分主要是导入路径、路由装配和前端状态抽取，不需要替换 FastAPI、Vue、Docker、PostgreSQL 或 DeepSeek。

主要风险：中等。风险集中在导入路径、Docker 构建上下文、`uvicorn` 入口、测试导入和 Windows 脚本；应通过分阶段 PR、兼容入口和每阶段 CI 降低风险。

### 建议目标结构

```text
.
├─ backend/
│  ├─ src/course_agent/
│  │  ├─ main.py
│  │  ├─ api/routers/
│  │  ├─ services/
│  │  ├─ agent/
│  │  ├─ db/
│  │  ├─ schemas/
│  │  ├─ parsers/
│  │  └─ core/
│  └─ tests/
├─ frontend/
│  └─ src/{features,components,composables,services,assets}/
├─ infra/{docker,postgres}/
├─ scripts/{dev,migrations,legacy}/
├─ docs/
├─ compose.yaml
└─ pyproject.toml
```

### 分阶段迁移建议

1. 先建立 Python 包和 `pyproject.toml`，保留一个兼容 `server.py` 入口；CI 改为 editable install，确保 import 路径可测试。
2. 将 FastAPI 路由按 `auth`、`courses`、`tasks`、`materials`、`plans`、`insights`、`chat` 拆为 `APIRouter`；保持 URL 和响应模型不变。
3. 将服务、数据库、Agent、解析器与模型移动到领域子包；每次迁移一类模块并运行单元测试与容器健康检查。
4. 将 `App.vue` 拆为 feature modules（auth、dashboard、tasks、materials、plans、chat、risk）与共享 composables/API client；先抽 API client 和状态，再拆 UI。
5. 最后调整 Docker、Compose、启动脚本、README 与 CI，移除兼容入口，并补 PostgreSQL 集成与浏览器端到端测试。

### 不建议

- 不建议在本次重构同时换用 LangGraph、向量数据库、状态管理库或微服务；这会把“结构整理”扩大为“产品重写”。
- 不建议直接移动所有文件后再集中修复；应保持每一个 PR 可启动、可测试、可回滚。

## 来源列表

| 来源 | URL | 日期 | 可信度 |
|---|---|---|---|
| FastAPI Bigger Applications | https://fastapi.tiangolo.com/tutorial/bigger-applications/ | 2026-07-26 | 高 |
| PyPA src layout vs flat layout | https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ | 2026-07-26 | 高 |
| Vue SFC glossary | https://vuejs.org/glossary/ | 2026-07-26 | 高 |

## 调研结论

应执行结构重构，但作为独立的“架构演进”工作流：先建立可安装后端包与兼容入口，再拆 API 和前端 feature。预估为 4 至 6 个小 PR；核心功能 API 不变，因此可保持用户数据和现有 Docker 数据卷不迁移。
