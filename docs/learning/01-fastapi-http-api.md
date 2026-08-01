# 第 1 篇：FastAPI——从 Python 函数到 HTTP API

项目入口见 [main.py](../../backend/src/course_agent/main.py)。

## 1. 为什么需要 HTTP API

我们知道一个 Python 函数可以实现特定的功能：

```python
def health_check():
    return {"status": "ok"}
```

这个函数只能被同一个 Python 程序内部调用：

```python
result = health_check()
```

但是浏览器、Vue 前端或其他程序无法直接调用它。为了让外部程序通过网络访问这个能力，我们需要把函数暴露为 HTTP API。

## 2. FastAPI 如何把函数变成接口

下面是一个最小 FastAPI 示例：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }
```

这段代码建立了这样的对应关系：

```text
GET /health  →  health_check()
```

`app = FastAPI()` 中的 `app` 是整个 FastAPI 应用对象，所有路由、中间件和启动逻辑，最后都挂在这个对象上。

`@app.get("/health")` 表示当收到 `/health` 请求时，就执行下面的函数。其中 `GET` 是 HTTP 方法，`/health` 是 URL 路径，`health_check()` 是真正执行的 Python 函数。

## 3. 项目中的真实实现

项目中的健康检查接口位于 [main.py](../../backend/src/course_agent/main.py)：

```python
@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {
        "success": True,
        "data": {
            "service": "course-agent",
            "status": "ok",
        },
        "error": None,
    }
```

与最小示例相比，项目代码多了 `tags=["system"]`，用于分类 API 文档；返回值也使用了 `success/data/error` 结构，方便前端统一处理成功和失败。

## 4. HTTP 方法与任务接口

常见的 HTTP 方法有：

```text
GET       查询
POST      创建
PATCH     部分修改
DELETE    删除
```

所以项目中的任务接口会使用：

```text
GET    /api/v1/tasks
POST   /api/v1/tasks
PATCH  /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}
```

这些方法通常可以对应 CRUD，但 CRUD 只是对业务操作的概括，不是说每个 HTTP 方法都严格只对应一种数据库操作。例如 `POST` 也可能用于触发一次评估或生成计划。

## 5. 一次请求如何流动

当客户端访问：

```text
GET /health
```

后端大致经历以下过程：

```text
浏览器或监控系统
  → FastAPI 查找匹配路由
  → 执行 health_check()
  → Python 字典
  → 转换为 JSON 响应
  → 返回客户端
```

当我们使用 `GET /health` 时，会返回：

```json
{
  "success": true,
  "data": {
    "service": "course-agent",
    "status": "ok"
  },
  "error": null
}
```

所以，FastAPI 主要帮我们完成：

```text
HTTP 请求
  → 路由匹配
  → Python 函数调用
  → Python 返回值
  → HTTP JSON 响应
```

## 6. 统一响应结构

大多数业务接口返回的数据格式是项目自己定义的。这样前端对于不同内容的数据可以统一处理：

```json
{
  "success": true,
  "data": "业务数据",
  "error": null
}
```

业务处理失败时可以统一为：

```json
{
  "success": false,
  "data": null,
  "error": "任务数据查询失败。"
}
```

统一结构降低了前端处理不同接口的复杂度，但它不是全部响应的强制协议。当前项目中，参数校验错误由 FastAPI 返回 422，鉴权依赖会返回 401，部分接口通过 `HTTPException` 返回 404 或 400；这些响应通常使用 FastAPI 的 `detail` 字段。限流中间件返回的 429 和多数业务接口仍使用 `success/data/error` 结构。前端因此同时处理 HTTP 状态码、`error` 和 `detail`。

## 7. `/health` 解决什么问题

健康检查接口只回答一个问题：

```text
FastAPI 进程目前能否接收请求并返回响应？
```

它不负责验证：

- PostgreSQL 是否可用；
- DeepSeek 是否可用；
- 课程数据是否存在；
- Agent 是否能正常调用工具。

因此，`/health` 返回成功，只能说明 API 进程本身可以响应，不能证明整个业务链路都正常。

## 8. 这一层解决了什么问题

加入 FastAPI API 后，系统获得了：

```text
Python 函数
  ↓
HTTP 地址
  ↓
浏览器、Vue、其他程序可以调用
```

但现在仍然有很多问题没有解决：

- 数据从哪里来？
- 谁可以访问？
- 如何保存任务？
- 如何处理多个接口？
- 如何和前端交互？

这些问题会在后面的层次中逐步加入。

下一篇：[Router：如何把 API 按业务领域拆分](02-router-modules-registration.md)
