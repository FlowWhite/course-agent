# 第 8 篇：同步与异步——请求如何执行

上一部分我们沿着课程资料上传接口，看到了文件如何从前端进入 FastAPI，经过校验、解析和文本分块，最后保存到 PostgreSQL。

这一部分继续看请求进入系统以后是怎样执行的。项目中同时出现了普通的 `def`、`async def`、`await` 和 `run_in_threadpool`。它们并不是同一个概念，不能只看到函数前面有 `async` 就认为里面的所有操作都是异步的。

所以这一篇先从 Python 的同步和异步开始，再回到当前项目，沿着前端请求、FastAPI 接口、PostgreSQL 查询和 Agent 模型调用看一遍。

## 1. 什么是同步执行

同步代码的执行顺序比较直观：调用一个函数，等这个函数返回以后，再执行下一行。

~~~python
import time


def task(name):
    print(f"{name} 开始")
    time.sleep(2)
    print(f"{name} 完成")


task("任务 A")
task("任务 B")
~~~

执行过程是：

~~~text
任务 A 开始
等待 2 秒
任务 A 完成
任务 B 开始
等待 2 秒
任务 B 完成
~~~

这里调用 `task("任务 B")` 之前，必须先等 `task("任务 A")` 完成。两个任务加起来大约需要 4 秒。

`time.sleep(2)` 期间，当前线程会停在这里，不能继续执行后面的 Python 代码。这个等待可能来自很多地方，例如等待磁盘、数据库、HTTP 服务或模型返回。

同步不一定是错误。普通脚本、简单的数据处理，或者本身不需要同时处理很多请求时，同步代码通常更容易理解。需要注意的是：如果一个负责处理很多请求的线程长时间停在同步等待上，就会影响其他请求。

## 2. 什么是异步执行

Python 使用 `async def` 定义协程函数。它和普通函数有一个明显区别：调用协程函数时，通常先得到一个协程对象，而不是函数最终返回的结果。

~~~python
import asyncio


async def task(name):
    print(f"{name} 开始")
    await asyncio.sleep(2)
    print(f"{name} 完成")


result = task("任务 A")
print(result)
~~~

上面的 `result` 是一个协程对象。函数体要等它被 `await`，或者被注册为任务以后，才会真正执行。

在普通 Python 脚本中，可以使用 `asyncio.run` 运行一个最外层协程：

~~~python
asyncio.run(task("任务 A"))
~~~

如果当前已经在另一个异步函数中，就可以直接 `await`：

~~~python
async def main():
    await task("任务 A")
~~~

这几步可以表示为：

~~~text
调用 async def
  ↓
得到协程对象
  ↓
await 或 create_task
  ↓
协程开始运行
~~~

### 2.1 await 做了什么

下面这一句是异步代码里最重要的部分：

~~~python
await asyncio.sleep(2)
~~~

它不是简单地让整个程序停两秒，而是当前协程在这里等待，并把执行机会交回事件循环。

~~~text
当前协程暂时停下
  ↓
事件循环查看其他可以执行的协程
  ↓
其他协程继续运行
  ↓
等待条件满足后，当前协程恢复
~~~

事件循环可以看成一个任务调度器。某个协程在等待网络或文件结果时，事件循环可以去处理另一个已经准备好继续执行的协程。

但是事件循环不会凭空打断一段正在运行的同步代码。例如：

~~~python
async def handler():
    time.sleep(5)
~~~

这个函数虽然使用了 `async def`，但 `time.sleep(5)` 没有 `await`，所以执行期间仍然会占住当前事件循环。看到 `async def` 以后，还要继续看函数体中具体在哪些地方使用了 `await`。

### 2.2 await 不等于并发

下面的代码仍然是顺序执行：

~~~python
async def main():
    await task("A")
    await task("B")
~~~

它的意思是先等待 A 完成，再开始 B。

如果希望两个任务都开始运行，可以使用 `asyncio.gather`：

~~~python
async def main():
    await asyncio.gather(
        task("A"),
        task("B"),
    )
~~~

执行过程更接近：

~~~text
A 开始
B 开始
A、B 在等待时交替让出执行权
A 完成
B 完成
~~~

如果两个任务都只是等待两秒，总时间通常接近两秒，而不是四秒。但这只说明它们的等待过程可以交错进行，并不代表所有代码都会因为使用异步而自动变快。

## 3. 异步函数中遇到同步工作怎么办

异步比较适合等待 I/O，例如等待 HTTP 响应、异步数据库查询、上传文件内容或定时器。

如果异步函数内部直接执行很慢的同步工作，事件循环仍然可能被占住：

~~~python
def slow_work():
    time.sleep(5)
    return "完成"


async def main():
    result = slow_work()
    print(result)
~~~

这里的 `slow_work()` 没有被异步处理。`main` 执行到这一句以后，会一直等 `slow_work` 返回。

可以把同步函数交给线程池：

~~~python
from fastapi.concurrency import run_in_threadpool


async def main():
    result = await run_in_threadpool(slow_work)
    print(result)
~~~

这时执行关系是：

~~~text
slow_work 在工作线程中执行
  ↓
run_in_threadpool 返回一个可等待对象
  ↓
await 等待工作线程完成
  ↓
当前协程恢复并继续执行
~~~

线程池的作用是把同步工作从当前异步执行线程中移开，让事件循环有机会处理其他协程。但是这里仍然有一个容易混淆的地方：

~~~text
线程池隔离
  ≠
后台任务
~~~

`await run_in_threadpool(...)` 返回之前，当前 HTTP 请求仍然在等待。因此客户端还是要等这个线程池工作完成以后，才能收到响应。它只是改变了同步函数在哪个线程执行，并没有把任务放到 HTTP 请求结束以后。

## 4. 前端是在哪里等待请求的

先看前端的统一请求函数。它位于：

~~~text
web/src/composables/useCourseWorkspace.js
~~~

核心代码如下：

~~~javascript
async function requestJson(
  path,
  options = {},
  fallback = "请求失败",
) {
  let response

  try {
    const requestOptions = {
      ...options,
      headers: buildRequestHeaders(options.headers),
    }

    response = await fetch(
      ${API_BASE_URL}${path},
      requestOptions,
    )
  } catch (exception) {
    throw new Error(
      "无法连接到 API 服务，请确认 FastAPI 正在运行。"
    )
  }

  const result = await response.json().catch(() => null)

  if (response.status === 401) {
    clearAccessToken()
    throw new Error("登录已失效，请重新登录")
  }

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        result,
        ${fallback}（HTTP ${response.status}）,
      )
    )
  }

  if (result?.success === false) {
    throw new Error(getErrorMessage(result, fallback))
  }

  return result?.data ?? result
}
~~~

这里有两个主要的 `await`：

~~~text
await fetch(...)
  ↓
等待 FastAPI 返回 HTTP 响应

await response.json()
  ↓
等待响应体转换成 JavaScript 对象
~~~

`buildRequestHeaders` 还会把访问令牌放进请求头，所以前端等待的请求通常已经包含了 JWT。

工作台加载某门课程时，还会使用 `Promise.all`：

~~~javascript
await Promise.all([
  loadTasks(selectedCourseId.value),
  loadCourseFiles(selectedCourseId.value),
  loadRisks(selectedCourseId.value),
])
~~~

这表示前端同时发起任务、课程资料和风险请求，并等待它们全部完成。这里的并发只说明前端没有逐个等待这三个请求，不能据此判断后端的三个 Endpoint 都是 `async def`。

接下来选一个后端接口，看看请求进入 FastAPI 后真正怎样执行。

## 5. 任务查询：同步 Endpoint 和同步 PostgreSQL

任务接口位于：

~~~text
backend/src/course_agent/api/routers/tasks.py
~~~

入口函数是：

~~~python
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
~~~

这里的函数声明是普通的 `def`，不是 `async def`。请求从前端到返回的过程可以表示为：

~~~text
Vue 调用 requestJson()
  ↓
await fetch("/api/v1/tasks")
  ↓
FastAPI 找到 list_tasks_api()
  ↓
普通 def Endpoint 在 FastAPI 的线程池中执行
  ↓
list_tasks_data()
  ↓
同步 psycopg 查询 PostgreSQL
  ↓
TaskRecord 转成 JSON
  ↓
前端继续执行
~~~

### 5.1 JWT 在这条链路中的位置

函数参数中的：

~~~python
current_user: dict = Depends(get_current_user)
~~~

不是客户端在查询参数中传入的普通字段。FastAPI 会先执行依赖函数，依赖函数从请求头中读取 JWT 并验证，成功后才把当前用户传给 Endpoint。

然后 Endpoint 从 JWT 对应的用户信息中取出：

~~~python
user_id = int(current_user["id"])
~~~

这个用户 ID 会继续传给数据层，而不是使用客户端自己提交的 user_id。因此这里的鉴权边界是：

~~~text
请求头中的 JWT
  ↓
get_current_user()
  ↓
current_user["id"]
  ↓
list_tasks_data(user_id=...)
~~~

### 5.2 数据层是同步数据库调用

`list_tasks_data` 位于：

~~~text
backend/src/course_agent/postgres_data_service.py
~~~

它的返回类型是：

~~~python
def list_tasks_data(
    user_id: int,
    course: str,
    status: str,
) -> list[TaskRecord]:
~~~

函数先整理课程和状态，然后生成查询条件：

~~~python
conditions: list[str] = ["t.user_id = %s"]
parameters: list[Any] = [user_id]

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
~~~

这里默认就有 t.user_id = %s，说明查询不是把所有用户的任务取出来以后再在 Python 中筛选。课程和状态条件也会加入 SQL。

真正访问 PostgreSQL 的部分是同步调用：

~~~python
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
~~~

这里的连接、游标、execute 和 fetchall 都是同步 psycopg 的使用方式。用户提供的课程名称、状态和用户 ID 会放入 parameters，不是直接拼接进 SQL 值中；where_clause 只由代码中固定的条件片段组成。

最后，数据层把数据库行转换成 TaskRecord 列表，Endpoint 再使用 model_dump(mode="json") 生成可以返回给前端的 JSON。

因此，这条接口的执行方式是：

~~~text
普通 def Endpoint
  +
同步数据库调用
  +
FastAPI 提供的线程池
~~~

这也是为什么不能只根据前端的 await fetch 判断后端接口的类型。

## 6. 文件上传：一个 async def 中混合了多种执行方式

课程资料上传入口位于：

~~~text
backend/src/course_agent/api/routers/files.py
~~~

入口函数声明为：

~~~python
@router.post("/files", status_code=201)
async def upload_course_file_api(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
~~~

从函数签名看它是异步 Endpoint，但看函数体以后会发现，里面同时有异步读取、同步校验、同步数据库操作、同步解析和线程池索引。

上传接口的关键顺序是：

~~~python
original_filename, file_type = sanitize_original_filename(file.filename)
storage_filename = create_storage_name(file_type)
final_path = storage_path_for(user_id, storage_filename)
file_size = await _save_upload_to_storage(file, final_path)
validate_file_signature(final_path, file_type)
course_file = create_course_file_data(...)
set_course_file_parsing_data(user_id, course_file.id)

parsed_chunks = parse_document(final_path, file_type)
course_file = replace_document_chunks_data(...)

course_file = await run_in_threadpool(
    index_course_file_embeddings_data,
    user_id=user_id,
    file_id=course_file.id,
)
~~~

下面逐个看这些调用。

### 6.1 上传文件的读取使用 await

`_save_upload_to_storage` 中的代码是：

~~~python
async def _save_upload_to_storage(
    uploaded_file: UploadFile,
    destination: Path,
) -> int:
    temporary_path = destination.with_name(
        f".{destination.name}.uploading"
    )
    total_size = 0
    try:
        with temporary_path.open("xb") as target:
            while chunk := await uploaded_file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="单个课程文件不能超过 20 MB。",
                    )
                target.write(chunk)
        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="不允许上传空文件。",
            )
        temporary_path.replace(destination)
        return total_size
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await uploaded_file.close()
~~~

这里真正出现 await 的地方是：

~~~python
await uploaded_file.read(1024 * 1024)
await uploaded_file.close()
~~~

读取时每次最多取 1 MB，循环直到文件结束。文件内容写入临时文件以后，成功时再使用 temporary_path.replace(destination) 替换成正式文件。

但：

~~~python
target.write(chunk)
~~~

仍然是同步的磁盘写入。也就是说，从当前路由的代码看，这一段不能简单说成“整个文件保存都是异步的”，更准确的说法是：

~~~text
使用 await 读取 UploadFile
  +
同步写入临时文件
  +
await 关闭上传对象
~~~

### 6.2 文件校验、哈希、解析和数据库操作是同步调用

上传文件写入磁盘以后，接口会直接调用：

~~~python
validate_file_signature(final_path, file_type)
calculate_sha256(final_path)
create_course_file_data(...)
set_course_file_parsing_data(user_id, course_file.id)
parse_document(final_path, file_type)
replace_document_chunks_data(...)
~~~

这些函数的调用处没有 await：

~~~text
validate_file_signature
  → 同步读取文件头并检查格式

calculate_sha256
  → 同步读取文件并计算哈希

create_course_file_data
  → 使用同步 psycopg 保存 course_files 元数据

parse_document
  → 同步解析 PDF、DOCX、TXT 或 Markdown

replace_document_chunks_data
  → 使用同步 psycopg 替换 document_chunks
~~~

所以，虽然上传 Endpoint 是 async def，这些同步函数在它们执行期间仍然会占用当前执行线程。

这一点和前面的任务查询有区别：任务查询整个 Endpoint 是普通 def，FastAPI 会把整个函数放到线程池；上传 Endpoint 的函数体是异步函数，其中这些直接调用的同步工作不会因为外层写了 async 就自动进入线程池。

### 6.3 Embedding 使用线程池，但请求仍然等待

解析成功以后，当前代码执行：

~~~python
course_file = await run_in_threadpool(
    index_course_file_embeddings_data,
    user_id=user_id,
    file_id=course_file.id,
)
~~~

index_course_file_embeddings_data 内部仍然是同步工作，包括读取文本块、调用 Embedding 客户端、写入 PostgreSQL 向量和更新索引状态。

这里使用线程池，是为了不要让这段同步工作直接占住异步 Endpoint 的执行线程。可是外层写了 await，所以 HTTP 请求要等索引函数返回以后才能返回：

~~~text
上传请求
  ↓
解析文本并保存全文检索数据
  ↓
等待线程池中的 Embedding 索引
  ↓
返回文件状态
~~~

因此这不是“上传完成以后后台慢慢建立索引”，而是“索引工作在线程池中执行，但上传请求等待它结束”。

## 7. 作业评估和 Agent 聊天

### 7.1 作业评估：文件读取和模型评估分别处理

作业评估接口位于：

~~~text
backend/src/course_agent/api/routers/tasks.py
~~~

入口函数是：

~~~python
@router.post("/tasks/{task_id}/assessment")
async def assess_task_submission_api(
    task_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
~~~

它的主要代码顺序如下：

~~~python
user_id = int(current_user["id"])
task = get_task_detail_data(
    user_id=user_id,
    task_id=task_id,
)

await _save_submission_upload(file, submission_path)
validate_file_signature(submission_path, file_type)
chunks = parse_document(submission_path, file_type)
submission_text, submission_truncated = _submission_excerpt(chunks)

sources = _task_sources_for_assessment(user_id, task)

assessment = await run_in_threadpool(
    generate_task_submission_assessment,
    task=task.model_dump(mode="json"),
    submission_text=submission_text,
    sources=[source.model_dump(mode="json") for source in sources],
)
~~~

可以看到：

~~~text
get_task_detail_data()
  → 同步查询当前用户拥有的任务

await _save_submission_upload()
  → 等待作业文件读取完成

validate_file_signature()
parse_document()
  → 同步校验和解析临时文件

_task_sources_for_assessment()
  → 根据任务和课程资料准备检索来源

await run_in_threadpool(...)
  → 在线程池中执行同步模型评估
~~~

最后一个线程池函数是 generate_task_submission_assessment。它在 agent_runtime.py 中使用 Runner.run_sync 调用模型，并对返回结果进行解析和字段校验。把它放入线程池以后，模型调用不会直接占住异步 Endpoint 的执行线程，但当前 HTTP 请求仍然会等待评估结果。

这条请求实际连接了：

~~~text
前端上传作业
  ↓
FastAPI 验证 JWT 和任务归属
  ↓
同步读取任务、课程资料和解析后的作业正文
  ↓
线程池中的 Runner.run_sync()
  ↓
生成并校验评估结果
  ↓
返回作业评估 JSON
~~~

### 7.2 Agent 聊天：普通 def 加 Runner.run_sync

聊天接口位于：

~~~text
backend/src/course_agent/api/routers/chat.py
~~~

它是普通同步函数：

~~~python
@router.post("/chat")
def chat_api(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
~~~

函数先使用 JWT 得到用户 ID，再调用：

~~~python
course = next(
    (
        item
        for item in list_courses_data(user_id=user_id)
        if item.id == course_id
    ),
    None,
)
~~~

这一步不是直接相信前端传来的课程 ID，而是从当前用户拥有的课程中查找。找不到就返回错误，避免用户使用别人的课程作为 Agent 上下文。

找到课程以后，代码会设置当前 Agent 的用户和课程上下文：

~~~python
user_token = set_current_agent_user_id(user_id)
course_token = set_current_agent_course_id(course.id)
source_token = set_current_agent_document_sources()
~~~

然后创建课程 Agent 和会话，运行一次消息：

~~~python
result = run_agent_message(
    agent=agent,
    user_input=request.message,
    session=session,
)
~~~

run_agent_message 最终调用：

~~~python
return Runner.run_sync(
    agent,
    user_input,
    max_turns=6,
    session=session,
)
~~~

所以聊天请求的链路是：

~~~text
Vue await fetch("/api/v1/chat")
  ↓
普通 def chat_api
  ↓
FastAPI 线程池
  ↓
查询当前用户的课程
  ↓
设置用户和课程上下文
  ↓
Runner.run_sync()
  ↓
等待 Agent 得到 final_output
  ↓
返回完整 reply 和 sources
~~~

当前聊天不是流式响应。前端会等待整个 HTTP 响应，直到 Agent 的完整结果生成以后才显示返回值。

另外，chat_api 使用 finally 重置了用户、课程和资料来源上下文：

~~~python
finally:
    reset_current_agent_document_sources(source_token)
    reset_current_agent_course_id(course_token)
    reset_current_agent_user_id(user_token)
~~~

这部分属于请求级的安全边界。Agent 配置可以按课程复用，但当前用户 ID、课程 ID 和资料来源不会一直留在后续请求中。

## 8. 把当前项目的执行方式放在一起看

现在可以把几条主要链路放在一起：

~~~text
任务查询：
def Endpoint
  → 同步 list_tasks_data()
  → 同步 psycopg 查询 PostgreSQL
  → FastAPI 线程池

课程上传：
async def Endpoint
  → await 文件读取
  → 同步校验、哈希、解析和数据库写入
  → await 线程池中的 Embedding 索引

作业评估：
async def Endpoint
  → 同步查询任务
  → await 读取作业文件
  → 同步解析和检索资料
  → await 线程池中的模型评估

Agent 聊天：
def Endpoint
  → FastAPI 线程池
  → Runner.run_sync()
  → 等待完整模型结果
~~~

因此当前项目不是“全部同步”，也不是“全部异步”。更准确的描述是：

~~~text
普通 def Endpoint
  → 由 FastAPI 放入线程池

async def Endpoint
  → 在 await 处让出执行机会
  → 直接调用的同步函数仍然同步执行

run_in_threadpool(...)
  → 把指定的同步工作移到线程池
  → 但 await 仍然让当前 HTTP 请求等待
~~~

## 9. 当前已实现、后续计划和暂未实现

### 9.1 当前已经实现

当前代码已经实现了：

~~~text
前端 await fetch()
  → 等待后端 HTTP 响应

FastAPI 中同时使用 def 和 async def
  → 根据 Endpoint 声明方式执行

上传文件按块读取
  → 使用 await uploaded_file.read(...)

Embedding 和作业评估
  → 使用 run_in_threadpool 隔离同步工作

Agent 聊天
  → 使用 Runner.run_sync() 返回完整结果
~~~

当前的 CORS、HTTP 中间件和内存限流也已经写在 backend/src/course_agent/main.py 中，只是本篇先不展开它们的执行顺序。

### 9.2 学习目录中的后续安排

中间件、CORS 和限流会在第 12 篇单独讲解，Redis 分布式限流安排在第 14 篇。它们是学习目录中的后续内容，不是第 08 篇缺少的代码。

### 9.3 当前尚未实现

从当前代码来看，还没有：

- 异步 PostgreSQL 驱动；当前数据层使用同步 psycopg；
- 脱离当前 HTTP 请求的后台任务队列；当前线程池调用仍然需要被 Endpoint 等待；
- Agent 聊天的流式响应；当前返回的是完整的 final_output；
- Redis 分布式限流；当前 main.py 使用的是进程内的 InMemoryRateLimiter。

这一篇先停在“一个请求如何被同步、异步和线程池共同执行”这里。

## 10. 自测问题

1. 为什么前端使用 await fetch，不能直接推出后端接口一定是 async def？

2. list_tasks_api 为什么是同步函数，但仍然可以使用同步的 psycopg？

3. upload_course_file_api 中，哪些操作真正使用了 await，哪些操作仍然是同步调用？

4. await run_in_threadpool(...) 为什么不是后台任务？

5. 当前 /api/v1/chat 为什么属于“同步 Endpoint + 同步 Agent”，而不是流式异步聊天？

请先回答这些问题，再继续第 09 篇。
