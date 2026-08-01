# 第 6 篇：PostgreSQL——表关系、约束、索引与参数化 SQL
## 1. 用户、课程、任务三张核心表
```sql
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    teacher TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    deadline DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('todo', 'done')),
    priority TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    description TEXT NOT NULL
);
```

`postgres/init.sql` 中首先定义这三张核心表：用户、课程和任务。它们的关系是:
一个用户可以有多门课程
一个用户可以有多个任务
一门课程可以有多个任务
## 2. 表中的约束
每一个表都有一个主键，如users中的
```sql
id BIGSERIAL PRIMARY KEY
```
这里的bigserial指的是使用序列自动生成递增的数字，big指的是可以容纳更大的数目，primary key就说明id是主键，用来唯一标识一条数据。
```sql
username TEXT NOT NULL UNIQUE
```
表示username必须有值，而且不能重复
下面courses表中的
```sql
user_id BIGINT NOT NULL REFERENCES users(id)
```
表示courses.user_id必须对应users.id中已经存在的用户，这就是外键，外键通常用于一对多的场景，因为主键不能重复而对应的外键可以重复。
在下面的tasks表中的
```sql
course_id TEXT NOT NULL REFERENCES courses(id)
```
也是外键，表示任务必须属于一门已经存在的课程。
```sql
status TEXT NOT NULL CHECK (status IN ('todo', 'done'))
```
则限定了状态，如果插入其他值数据库会拒绝。
## 3. 为什么任务表中同时保存 user_id 和 course_id
任务表中有两个重要字段：
```text
user_id
course_id
```
这样查询任务时，可以直接使用：
```sql
WHERE t.user_id = %s
```
保证用户只能查询自己的任务。
虽然课程本身也有 user_id，但任务中再次保存 user_id，可以让用户隔离条件更加直接，也方便按用户查询。在查询时，项目还会检查任务和课程属于同一个用户：
```sql
JOIN courses AS c
    ON t.course_id = c.id
    AND t.user_id = c.user_id
```
此时若只写：
```sql
ON t.course_id = c.id
```
就只会检查课程 ID 是否匹配，没有进一步确认任务和课程是否属于同一个用户。
## 4. 任务查询中的 JOIN
第五篇中看过的这部分SQL：
```sql
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
WHERE t.user_id = %s
ORDER BY t.deadline ASC
```
有两个表：
```text
tasks AS t
courses AS c
```
所以后面就可以使用类似 `t.title` 这种数据。
任务表中只有course_id，没有课程名称。所以通过
```sql
JOIN courses AS c
```
就能查询出课程名称，最终返回的数据中就会同时有：
```json
{
  "course_id": "db",
  "course_name": "数据库",
  "title": "完成实验"
}
```
## 5. 外键删除规则
```sql
user_id BIGINT NOT NULL
    REFERENCES users(id)
    ON DELETE CASCADE
```
里面ON DELETE CASCADE表示：
```text
删除用户
  ↓
自动删除这个用户的课程
  ↓
自动删除这个用户的任务
```
这样做可以避免数据库中留下没有所属对象的孤立数据。但是它也有风险：删除用户或课程时会连带删除数据，所以实际项目中需要谨慎处理删除操作。
## 6. 索引
项目中定义了这些索引：
```sql
CREATE INDEX IF NOT EXISTS idx_tasks_course_id
    ON tasks(course_id);

CREATE INDEX IF NOT EXISTS idx_courses_user_id
    ON courses(user_id);

CREATE INDEX IF NOT EXISTS idx_tasks_user_course
    ON tasks(user_id, course_id);

CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks(status);
```
索引就像目录，如果没有索引，数据库就会对每一行检查符合条件的数据。而有了索引，数据库可能会先按照索引缩小候选数据范围，再进行筛选，最后读取记录。是否使用索引，最终由数据库的查询优化器决定。
```sql
WHERE t.user_id = %s
```
就可以使用和 user_id 相关的索引。
```sql
WHERE t.user_id = %s
  AND t.course_id = %s
```
就可以使用
```sql
CREATE INDEX idx_tasks_user_course
    ON tasks(user_id, course_id);
```
创建的联合索引，顺序表示了它更适合先按照user_id，再按照course_id查询。
如果只按照course_id查询，因为缺少前面的user_id，通常不能充分使用这个联合索引。
索引并不是越多越好，因为它也会：
占用磁盘空间；
增加插入和修改成本；
需要数据库额外维护。
所以索引应该根据真实查询来设计。

可以使用EXPLAIN查看PostgreSQL最终选择了什么查询方式：
```sql
EXPLAIN
SELECT *
FROM tasks
WHERE user_id = 1;
```
如果结果中出现Index Scan或Bitmap Index Scan，说明查询使用了索引；如果出现Seq Scan，说明PostgreSQL选择了全表扫描。
## 7. SQL 参数为什么不直接拼接
项目的数据层使用：
```python
cursor.execute(
    sql,
    parameters,
)
```
例如：
```python
conditions = ["t.user_id = %s"]
parameters = [user_id]
```
最终的：
```sql
WHERE t.user_id = %s
```
实际的user_id通过parameters传入，而不是直接拼接到SQL字符串中。
如果这样写：
```python
sql = f"SELECT * FROM tasks WHERE user_id = {user_id}"
```
就会使用户输入直接进入SQL，可能产生SQL注入。
虽然当前项目中的user_id来自已经验证的JWT，但其他用户输入也应该统一使用参数化查询。
## 8. 数据库记录和 Python 对象的区别
查询结束后，项目会执行：
```python
rows = cursor.fetchall()

return [
    TaskRecord.model_validate(row)
    for row in rows
]
```
这里面数据库负责保存数据，TaskRecord 负责在 Python 中表示数据，两者不是一个东西。
最后Endpoint再把TaskRecord对象转换成JSON：
```python
data=[
    task.model_dump(mode="json")
    for task in tasks
]
```
## 9. 从Endpoint到PostgreSQL的完整过程
```text
Vue 请求任务
  ↓
FastAPI Endpoint 接收 course、status
  ↓
get_current_user() 验证 JWT
  ↓
得到 user_id
  ↓
调用 list_tasks_data()
  ↓
清理和检查输入
  ↓
构造 conditions 和 parameters
  ↓
执行 SQL
  ↓
JOIN tasks 和 courses
  ↓
使用 user_id 限制数据
  ↓
返回数据库记录
  ↓
转换成 TaskRecord
  ↓
转换成 JSON
  ↓
Vue 显示任务
```
PostgreSQL 不只是保存数据，还通过主键、外键、检查约束和索引保证数据关系、数据合法性以及查询效率。

## 10. 当前 schema 的后续扩展

本篇先聚焦任务查询所需的三张核心表；当前项目的 `postgres/init.sql` 还定义了以下表和索引：

```text
course_files
  保存按 user_id、course_id 隔离的原始资料元数据、解析状态和向量索引状态。

document_chunks
  保存资料解析后的文本块、页码、PostgreSQL 全文检索向量和可选 Embedding。

learning_plans / learning_plan_steps
  保存用户确认前后的学习计划及其步骤状态。
```

资料检索直接使用 PostgreSQL 的 pgvector，而不是额外部署一个独立向量数据库：

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- document_chunks 中保存固定 1024 维向量
embedding VECTOR(1024)

-- 只为已生成向量的文本块建立余弦距离 HNSW 索引
CREATE INDEX idx_document_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;
```

因此，任务查询仍主要使用本篇介绍的关系和 B-tree 索引；课程资料问答则会优先按向量检索，在向量服务未配置或不可用时回退到全文检索。
