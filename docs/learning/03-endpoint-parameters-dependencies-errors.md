# 第 3 篇：Endpoint——请求参数、依赖注入与错误处理

上一部分我们知道 Router 会找到正确的 Endpoint。这一部分我们来了解一下数据如何进入 Endpoint 函数。

## 1. Endpoint 的参数来源

```python
@router.get("/tasks")
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
) -> dict:
    ...
```

FastAPI 主要有四种参数来源：

```text
查询参数
路径参数
请求体
依赖注入
```

## 2. 查询参数

如果网页请求：

```text
GET /api/v1/tasks?course=computer-network&status=todo
```

FastAPI 会自动转换成：

```python
course = "computer-network"
status = "todo"
```

`course: str = ""` 表示 `course` 的类型是字符串，默认值是空字符串。如果没有提供 `course`，它的值就是空字符串。

`status: Literal["all", "todo", "done"] = "all"` 表示限定参数范围。如果请求提供的参数不合法，FastAPI 会在进入函数之前进行校验，不会执行 `list_tasks_api()` 的函数体。

要注意，在 Endpoint 函数拿到参数之前，FastAPI 已经进行了这样的检查。

## 3. 路径参数

```python
@router.get("/tasks/{task_id}")
def get_task_detail_api(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    ...
```

如果请求：

```text
GET /api/v1/tasks/os-lab-1
```

那么 `os-lab-1` 就被传给了 `task_id`。

查询参数和路径参数的区别在于：

```text
查询参数：用于筛选、排序、分页
路径参数：用于定位某个具体资源
```

## 4. 请求体参数

```python
@router.post("/tasks")
def create_task_api(
    request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    ...
```

网页发送：

```text
POST /api/v1/tasks
Content-Type: application/json
```

请求体是：

```json
{
  "task_id": "os-lab-1",
  "course": "操作系统",
  "title": "完成实验一",
  "deadline": "2026-07-30",
  "priority": "high",
  "description": "完成实验报告"
}
```

这样的请求体格式由 `TaskCreateRequest` 类来定义，值就被传给了 `request`。

这里的 `TaskCreateRequest` 是 Pydantic 模型。Pydantic 模型是带有固定结构、类型校验和转换能力的数据对象，通常更适合表达结构固定的数据。

```text
JSON 请求体
  → Pydantic 模型
  → 类型和字段校验
  → 进入 Endpoint
```

## 5. 依赖注入参数

注意这一行：

```python
current_user: dict = Depends(get_current_user)
```

`Depends(get_current_user)` 的意思是执行这个 Endpoint 之前，先执行 `get_current_user()`。

这时网页会传这种信息：

```text
Authorization: Bearer <token>
```

依赖注入就是声明需要 `current_user`，然后由 FastAPI 准备一个 `current_user`。

这个过程把：

```python
token = request.headers["Authorization"]
user = decode_access_token(token)
```

的验证过程放到了依赖函数里面。因此登录校验逻辑可以被多个接口复用，每个接口都可以共享同一个用户验证逻辑。

## 6. Endpoint 的执行过程

对于：

```python
@router.get("/tasks")
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
):
    ...
```

完整过程是：

```text
1. FastAPI 根据 HTTP 方法和路径匹配 Endpoint
2. 从 URL 读取 course
3. 从 URL 读取 status
4. 检查 status 是否是 all/todo/done
5. 执行 get_current_user()
6. 验证 JWT
7. 准备 current_user
8. 调用 list_tasks_api()
```

## 7. 不同的错误类型

### 1. 参数错误

例如：

```text
GET /api/v1/tasks?status=finished
```

`status` 不符合 `Literal` 限制。这种错误发生在 Endpoint 执行之前，通常会返回参数校验错误。

### 2. 身份错误

例如：

```text
Authorization: Bearer invalid-token
```

这会导致 `get_current_user()` 解码失败。这种错误也发生在 Endpoint 执行之前。

### 3. 业务或数据库错误

如果参数和身份都正确，函数已经开始执行，但数据库连接失败，这才属于 Endpoint 内部或数据访问层的错误。

## 8. 完整请求链路

```text
GET /api/v1/tasks?course=computer-network&status=todo
  ↓
Router 匹配 /tasks
  ↓
读取 course
  ↓
读取并校验 status
  ↓
Depends(get_current_user)
  ↓
验证 JWT
  ↓
得到 current_user
  ↓
执行 list_tasks_api()
  ↓
把参数传给下一层
```

Endpoint 的主要作用是：

```text
接收 HTTP 世界的数据
  → 转换成 Python 参数
  → 确保基本合法
  → 传给后续业务逻辑
```

所以 Endpoint 不是简单的“普通函数”，它是一个由 FastAPI 自动准备参数、执行依赖并调用的 HTTP 处理函数。
