# 第 5 篇：任务查询——从 Endpoint 到 PostgreSQL

在第二篇中，我们已经看过任务 Router 如何找到任务接口，也看过 `list_tasks_api()` 的基本结构。

这一篇继续沿着同一个接口向下看，了解请求进入 Endpoint 以后，如何查询 PostgreSQL，并把查询结果返回给前端。

## 1. 先看任务查询接口

任务接口在 `backend/src/course_agent/api/routers/tasks.py` 中：

```python
@router.get("/tasks")
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List tasks filtered by course and completion status."""
    user_id = int(current_user["id"])
    try:
        tasks = list_tasks_data(
            user_id=user_id,
            course=course,
            status=status,
        )
        return ToolResponse(
            success=True,
            data=[task.model_dump(mode="json") for task in tasks],
        ).model_dump(mode="json")
    except ValueError as exc:
        return ToolResponse(
            success=False,
            error=str(exc),
        ).model_dump(mode="json")
    except Exception:
        return ToolResponse(
            success=False,
            error="任务数据查询失败。",
        ).model_dump(mode="json")
```

这个接口对应的请求类似：

```http
GET /api/v1/tasks?course=数据库&status=todo
Authorization: Bearer <JWT>
```

这里有三个参数，它们的来源不同。

```python
course: str = ""
```

`course` 是查询参数，来自 URL：

```text
?course=数据库
```

如果没有传 `course`，它就是空字符串，表示不按照课程筛选。

```python
status: Literal["all", "todo", "done"] = "all"
```

`status` 也是查询参数，用来筛选任务状态。它只能是下面三个值之一：

```text
all   所有任务
todo  未完成任务
done  已完成任务
```

如果客户端传入其他值，FastAPI 会在进入函数前进行校验。

```python
current_user: dict = Depends(get_current_user)
```

`current_user` 不是客户端传入的，而是通过前面学过的 JWT 依赖得到的。验证成功后大致是：

```python
{
    "id": 1,
    "username": "alice",
}
```

然后接口取出用户 ID：

```python
user_id = int(current_user["id"])
```

这一步很重要，因为后面的数据库查询必须知道“当前是谁在查询”。

## 2. Endpoint 把数据交给数据层

```python
tasks = list_tasks_data(
    user_id=user_id,
    course=course,
    status=status,
)
```

Endpoint 在这里没有自己写 SQL，而是把三个已经准备好的参数传给 `list_tasks_data()`：

```text
JWT 得到的 user_id
前端传来的 course
前端传来的 status
        ↓
list_tasks_data()
```

这样做以后，Endpoint 主要负责接收请求、获取用户身份和组织调用，数据库查询放在数据服务中完成。

## 3. 数据层先处理输入

`list_tasks_data()` 位于 `backend/src/course_agent/postgres_data_service.py`：

```python
def list_tasks_data(
    user_id: int,
    course: str,
    status: str,
) -> list[TaskRecord]:
    normalized_course = course.strip()
    normalized_status = status.strip().lower()

    if normalized_status not in {"all", "todo", "done"}:
        raise ValueError("status 只能是 all、todo 或 done。")
```

这里先对输入进行规范化处理：

```python
normalized_course = course.strip()
```

去掉课程名称前后的空格。

```python
normalized_status = status.strip().lower()
```

去掉状态前后的空格，并统一转换成小写。

虽然 Endpoint 中的 `Literal` 已经限制了状态，但数据层仍然再次检查：

```python
if normalized_status not in {"all", "todo", "done"}:
    raise ValueError("status 只能是 all、todo 或 done。")
```

这是因为数据层不一定只会被这个 Endpoint 调用，也可能被 Agent 工具或其他业务函数调用，所以数据层不能完全依赖上层校验。

## 4. 查询条件是如何生成的

数据层先建立一个查询条件列表：

```python
conditions: list[str] = ["t.user_id = %s"]
parameters: list[Any] = [user_id]
```

这里一开始就加入了：

```sql
t.user_id = %s
```

这表示无论用户有没有选择课程和状态，查询都必须限制在当前用户的数据范围内。

同时，`parameters` 保存 `%s` 对应的实际值：

```text
conditions  保存 SQL 条件
parameters  保存条件对应的参数值
```

如果用户传入了课程：

```python
if normalized_course:
    conditions.append(
        "(c.id = %s OR c.name LIKE %s)"
    )
    parameters.extend(
        [
            normalized_course,
            f"%{normalized_course}%",
        ]
    )
```

这表示课程既可以按照课程 ID 查询，也可以按照课程名称模糊查询：

```sql
(c.id = %s OR c.name LIKE %s)
```

如果用户选择的课程是“数据库”，对应的参数大致是：

```python
["数据库", "%数据库%"]
```

如果状态不是 `all`，再添加状态条件：

```python
if normalized_status != "all":
    conditions.append("t.status = %s")
    parameters.append(normalized_status)
```

例如 `status=todo` 时，会增加：

```sql
t.status = %s
```

## 5. 多个条件如何合成 WHERE

```python
where_clause = ""

if conditions:
    where_clause = (
        "WHERE " + " AND ".join(conditions)
    )
```

如果请求是：

```http
GET /api/v1/tasks?course=数据库&status=todo
```

那么 `conditions` 大致是：

```python
[
    "t.user_id = %s",
    "(c.id = %s OR c.name LIKE %s)",
    "t.status = %s",
]
```

最后会生成：

```sql
WHERE t.user_id = %s
  AND (c.id = %s OR c.name LIKE %s)
  AND t.status = %s
```

这里使用 `conditions` 列表的好处是，可以根据请求中有没有筛选条件来决定是否增加 SQL 条件，不需要为每一种查询情况单独写一条 SQL。

## 6. SQL 查询任务和课程

```python
with _get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                t.id,
                t.course_id,
                c.name AS course_name,
                t.title,
                t.deadline,
                t.status,
                t.priority,
                t.description
            FROM tasks AS t
            JOIN courses AS c
                ON t.course_id = c.id
                AND t.user_id = c.user_id
            {where_clause}
            ORDER BY t.deadline ASC
            """,
            parameters,
        )

        rows = cursor.fetchall()
```

这里查询了两张表：

```text
tasks    任务表
courses  课程表
```

通过下面这部分连接它们：

```sql
JOIN courses AS c
    ON t.course_id = c.id
    AND t.user_id = c.user_id
```

`t.course_id = c.id` 表示任务属于哪门课程。

`t.user_id = c.user_id` 进一步保证任务和课程属于同一个用户，避免把不同用户的数据连接在一起。

查询结果按照截止时间排序：

```sql
ORDER BY t.deadline ASC
```

这样前端拿到的任务会按照截止时间从早到晚排列。

这里虽然使用了 f-string 放入 `where_clause`，但 `where_clause` 的内容只来自代码中预先写好的 SQL 条件，用户输入没有直接拼进 SQL。用户输入的课程和状态仍然通过 `parameters` 传入：

```python
cursor.execute(sql, parameters)
```

这样可以避免 SQL 注入。

## 7. 数据库结果如何变成任务对象

查询完成以后：

```python
rows = cursor.fetchall()
```

`rows` 是数据库返回的多行记录。数据层会把每一行转换成 `TaskRecord`：

```python
return [
    TaskRecord.model_validate(row)
    for row in rows
]
```

这一步相当于：

```text
数据库的一行数据
  ↓
TaskRecord.model_validate()
  ↓
项目中的任务对象
```

所以 `list_tasks_data()` 返回的不是原始 SQL 结果，而是：

```python
list[TaskRecord]
```

## 8. Endpoint 如何返回给前端

数据层返回任务对象后，回到 `list_tasks_api()`：

```python
return ToolResponse(
    success=True,
    data=[task.model_dump(mode="json") for task in tasks],
).model_dump(mode="json")
```

这里做了两次转换：

```text
TaskRecord 对象
  ↓
task.model_dump(mode="json")
  ↓
每个任务变成字典
  ↓
ToolResponse.model_dump(mode="json")
  ↓
整个响应变成 JSON
```

前端最终得到类似这样的结果：

```json
{
  "success": true,
  "data": [
    {
      "id": "task-001",
      "course_id": "db",
      "course_name": "数据库",
      "title": "完成实验",
      "deadline": "2026-08-10",
      "status": "todo",
      "priority": "high",
      "description": "完成第三章实验"
    }
  ]
}
```

## 9. 查询失败时如何处理

Endpoint 中有两种错误处理：

```python
except ValueError as exc:
    return ToolResponse(
        success=False,
        error=str(exc),
    ).model_dump(mode="json")
```

这一类通常是用户输入或业务条件错误，例如状态不合法。接口会把具体错误返回给前端。

另一类是其他没有预料到的异常：

```python
except Exception:
    return ToolResponse(
        success=False,
        error="任务数据查询失败。",
    ).model_dump(mode="json")
```

这里不会把数据库内部错误直接返回给用户，而是返回一个比较统一的错误信息。

## 10. 一条完整请求链路

```text
Vue 发起请求
  ↓
GET /api/v1/tasks?course=数据库&status=todo
  ↓
FastAPI 解析 course 和 status
  ↓
get_current_user() 验证 JWT
  ↓
得到 current_user
  ↓
取出 user_id
  ↓
调用 list_tasks_data()
  ↓
规范化查询条件
  ↓
构造 conditions 和 parameters
  ↓
执行 PostgreSQL 查询
  ↓
返回 rows
  ↓
转换成 TaskRecord
  ↓
转换成 JSON
  ↓
Vue 更新任务列表
```

这一部分和第二篇的关系是：

```text
第二篇：Router 找到任务接口
第五篇：任务接口继续访问数据层和数据库
```

所以任务 Endpoint 的作用不是直接完成所有事情，而是连接请求、身份信息、数据服务和响应结果。
