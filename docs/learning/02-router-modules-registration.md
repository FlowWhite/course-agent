# 第 2 篇：Router——API 的业务拆分与路由注册

## 1. 为什么需要 Router

在真实的项目中，通常不会只有一个网络接口。当遇到复杂的、含有多个网络接口的情况时，为了避免都写在一个 `main` 文件中导致混乱，我们需要 Router 路由。

## 2. Router 是什么

Router 可以理解为一组相关 HTTP 接口的集合。例如在 `task.py` 文件的相关位置，我们可以看见：

```python
router = APIRouter(
    prefix="/api/v1",
    tags=["tasks"],
)
```

`prefix` 前缀会加在 HTTP 路径前。例如 `/task` 就是 `/api/v1/task`；`tags` 则是 `/docs` 打开 FastAPI 文档时使用的分类位置。

## 3. Router 和 App 的关系

这一结构和 `app` 很像：

```python
app = FastAPI()
router = APIRouter()
```

它们的关系就是 Router 包含在 App 中，就像公司和部门。

在 `main` 中最后有：

```python
for router in (
    auth_router,
    courses_router,
    tasks_router,
    files_router,
    plans_router,
    insights_router,
    chat_router,
):
    app.include_router(router)
```

这里就把不同的 Router 注册到 App 中了。

## 4. 以 Task Router 中的一个接口为例

```python
@router.get("/tasks")
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
) -> dict:
    ...
```

`course: str = ""` 是查询参数。若网页传来：

```text
GET /api/v1/tasks?course=computer-network
```

那么 `course` 就是 `"computer-network"`。

`status: Literal[...]` 限制了状态只能是后面的几种。如果客户端传入其他值，FastAPI 会进行参数校验。

`current_user: dict = Depends(get_current_user)` 是 FastAPI 通过依赖注入自动提供的当前用户。

请求链路如下：

```text
GET /api/v1/tasks
  → 解析 course 和 status
  → 执行 get_current_user()
  → 验证 JWT
  → 得到 current_user
  → 执行 list_tasks_api()
```

## 5. Router 的三个重要功能

Router 有三个重要功能：

1. 按照业务分组，便于开发者快速找到代码；
2. 使用 `prefix` 统一路径前缀，不同文件中的 Router 可以设置不同的前缀，这样业务逻辑统一，不需要每个接口重复写路径；
3. 进行统一的文档分类，例如 `tags=["tasks"]` 说明 FastAPI 自动生成的 `/docs` 页面会按照 tags 分类接口。

## 6. 一个请求经过 Router 的过程

```text
浏览器
  ↓
GET /api/v1/tasks?status=todo
  ↓
FastAPI 匹配 tasks_router
  ↓
匹配 @router.get("/tasks")
  ↓
解析 status 参数
  ↓
执行 get_current_user()
  ↓
验证 JWT
  ↓
执行 list_tasks_api()
  ↓
调用 list_tasks_data()
  ↓
返回 JSON
```

Router 在这里主要负责“找到正确的入口”。
