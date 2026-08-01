# 第 7 篇：课程资料——文件上传、文档解析与文本分块

这一部分牵扯的文件和函数比较多，所以先从完整链路开始，再逐步拆解每一个部分。

本篇主要涉及四个位置：

~~~text
files.py
  接收上传请求，组织完整流程

course_material_service.py
  保存文件元数据和文本块

document_parser.py
  按文件类型提取文字并分块

postgres/init.sql
  定义 course_files 和 document_chunks 表
~~~

## 1. 文件上传的完整链路

~~~text
前端选择课程和文件
  ↓
发送 multipart/form-data
  ↓
JWT 验证用户
  ↓
检查文件名和类型
  ↓
生成安全的存储文件名
  ↓
按块保存到临时文件
  ↓
检查文件大小和文件签名
  ↓
保存 course_files 元数据
  ↓
解析 PDF、DOCX、TXT 或 MD
  ↓
切分成多个文本块
  ↓
保存 document_chunks
  ↓
更新文件解析状态
  ↓
返回文件信息
~~~

下面按照这条链路，从上传接口开始。

## 2. 上传请求如何进入系统

先让我们看一下files.py中的上传接口

~~~python
@router.post("/files", status_code=201)
async def upload_course_file_api(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
~~~

### 2.1 文件上传和普通 JSON 请求不同

普通的接口通常接受一个json格式的请求体，如：

~~~json
{
  "title": "完成实验"
}
~~~

但是如果文件直接放在普通JSON中，就会是这样：

~~~json
{
    "filename": "test.pdf",
    "content": "101010101..."
}
~~~

但是这样非常不合理，这样内存占用过大，不方便流式上传，严重依赖传输稳定性，非常原始。所以我们在传输的时候使用multipart/form-data格式

### 2.2 multipart/form-data是什么

可以简单理解成一个请求里面包含多个不同类型的数据块。

例如上传课程资料的请求：

~~~http
POST /api/v1/files
Content-Type: multipart/form-data
~~~

这里的请求体就类似于

~~~text
course_id：
数据库课程

file：
<PDF二进制内容>
~~~

所以后端可以分别接受:

~~~python
course_id: str = Form(...)
~~~

和

~~~python
file: UploadFile = File(...)
~~~

form和file是fastapi中的格式，就是告诉框架这是multipart表单中的对应部分。

### 2.3 Form(...)具体是什么

~~~python
course_id: str = Form(...)
~~~

其中str说明这个值最终希望变成Python字符串。

Form(...)告诉框架从multipart/form-data中寻找数据。

### 2.4 File(...)具体是什么

~~~python
file: UploadFile = File(...)
~~~

其中File(...)含义如Form(...)。

而UploadFile则是fastapi对“上传文件”的封装，它不会直接把整个文件内容读入 Python 内存，而是提供一个文件对象，让你可以按需读取、保存和处理文件。

如果不使用UploadFile，fastapi会把上传的文件直接转换成bytes形式，很可能造成内存压力过大，所以文件上传不能简单等同于普通字符串。

### 2.5 UploadFile 的设计

UploadFile含有的常见属性：

~~~text
filename
content_type
还有最重要的file，这是真正的文件对象
~~~

### 2.6 文件之外的信息传输

请求体multipart/form-data里面含有文件和课程ID信息，而JWT这种信息会在请求头中。所以一次请求实际上有两个部分：

~~~text
HTTP 请求

Header:
    Authorization: Bearer xxx

Body:
    multipart/form-data
        course_id=db001
        file=test.pdf
~~~

fastapi会分别对两者进行处理，因此我们的鉴权部分和文件传输并不冲突。

请求进入接口后，下一步就是确定当前用户、文件名和保存位置。

## 3. 文件保存前的准备

### 3.1 获取当前用户

首先获取当前用户：

~~~python
user_id = int(current_user["id"])
~~~

后面文件保存路径和数据库记录都会使用user_id，保证用户只能访问自己的文件。

~~~python
original_filename = ""
final_path: Path | None = None
metadata_created = False
~~~

这里的final_path记录最终保存路径，metadata_created记录文件元数据是否已经写入数据库。后面发生异常时，程序会根据它们判断是否需要删除已经写入磁盘、但还没有对应数据库记录的文件。

### 3.2 原始文件名和存储文件名

从这一部分能看出来，创建了两个文件名：

~~~text
original_filename
  用户上传时看到的文件名

storage_filename
  后端真正保存时使用的文件名
~~~

例如：

~~~text
用户上传：
数据库实验报告.pdf

后端保存：
a8f6c1....pdf
~~~

这样做的好处:

- 原始文件名可以展示给用户；
- 存储文件名不会因为重名而覆盖；
- 不直接使用用户提供的路径；
- 文件可以按用户分目录保存。

~~~python
original_filename, file_type = sanitize_original_filename(file.filename)
storage_filename = create_storage_name(file_type)
final_path = storage_path_for(user_id, storage_filename)
~~~

这三句为传输文件做准备，先用sanitize_original_filename检查扩展名，只允许特定格式的文件写入，然后使用create_storage_name创建后端文件名，最后storage_path_for保存地址

准备好保存位置后，就可以把上传内容真正写入磁盘。

## 4. 文件如何写入磁盘

~~~python
file_size = await _save_upload_to_storage(file, final_path)
~~~

这一句首先使用了_save_upload_to_storage，使用同一文件的方法：

~~~python
async def _save_upload_to_storage(
    uploaded_file: UploadFile,
    destination: Path,
) -> int:
    """Stream an upload to temporary storage while enforcing the size limit."""
    temporary_path = destination.with_name(f".{destination.name}.uploading")
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
            raise HTTPException(status_code=400, detail="不允许上传空文件。")
        temporary_path.replace(destination)
        return total_size
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await uploaded_file.close()
~~~

### 4.1 为什么需要分块读取

如果在原函数中直接使用：

~~~python
content = await uploaded_file.read()
with open("xxx.pdf", "wb") as f:
    f.write(content)
~~~

这种简单的写法会一次性将文件加载到内存中，造成服务器负载过大。因此使用了分块读取:

~~~python
while chunk := await uploaded_file.read(1024 * 1024):
~~~

这种写法是Python的赋值表达式，等价于:

~~~python
while True:
    chunk = await uploaded_file.read(1024 * 1024)
    if not chunk:
        break
~~~

这样会每次读取1MB的文件，直到读取结束。

### 4.2 临时文件

~~~python
temporary_path = destination.with_name(
    f".{destination.name}.uploading"
)
~~~

这里声明了一个临时文件，先在内存中生成它的临时路径，此时磁盘中还不存在临时文件。一直到：

~~~python
with temporary_path.open("xb") as target:
~~~

其中x指的是以“独占创建”方式打开，如果同名临时文件已经存在，就直接报错，不会覆盖原文件。b指的是二进制方式写入。此时临时文件已经创建，但是还不存在主要内容。

~~~python
while chunk := await uploaded_file.read(1024 * 1024):
    total_size += len(chunk)
    if total_size > MAX_UPLOAD_BYTES:
        raise HTTPException(...)
    target.write(chunk)
~~~

这里的

~~~python
target.write(chunk)
~~~

就是写入临时文件，因为前面已经open as target了。此时文件正在写入，而正式文件还不存在。

文件写完并且确认不为空后：

~~~python
temporary_path.replace(destination)
~~~

会把

~~~text
.abc123.pdf.uploading
~~~

这样的临时路径替换成

~~~text
abc123.pdf
~~~

这样临时文件就变成了正式文件。因此成功后，磁盘上通常不会同时存在两个文件。如果临时路径和正式路径位于同一个文件系统中，这种重命名通常具有原子性：其他代码要么看不到正式文件，要么看到完整的正式文件，不容易看到只写了一半的状态。

~~~python
except Exception:
    temporary_path.unlink(missing_ok=True)
    raise
~~~

如果中途发生问题，如：

- 文件超过 20 MB；
- 网络连接中断；
- 磁盘写入失败；
- 文件为空；
- 其他异常；

就会执行

~~~python
temporary_path.unlink(missing_ok=True)
~~~

删除临时文件。missing_ok=True表示：即使临时文件已经不存在，也不要因为删除失败再产生一个新的异常。raise会继续把原来的异常向上抛出，让接口返回相应错误。这样磁盘中不会长期留下一个不完整的 PDF。

文件写入完成后，还不能只凭扩展名判断它确实是对应格式。

## 5. 检查文件签名

让我们回到upload_course_file_api中，下一句

~~~python
validate_file_signature(final_path, file_type)
~~~

会检查文件类型是否与文件扩展名匹配。

~~~python
def validate_file_signature(path: Path, file_type: str) -> None:
    """Reject common extension spoofing before a parser opens the file."""
    if file_type == "pdf":
        with path.open("rb") as uploaded_file:
            header = uploaded_file.read(1_024)

        if b"%PDF-" not in header:
            raise DocumentParseError("PDF 文件头无效，文件可能不是 PDF。")

    elif file_type == "docx":
        if not zipfile.is_zipfile(path):
            raise DocumentParseError("DOCX 文件格式无效，文件可能已损坏或被伪装。")

        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            uncompressed_size = sum(
                entry.file_size
                for entry in archive.infolist()
            )
            document_info = (
                archive.getinfo("word/document.xml")
                if "word/document.xml" in names
                else None
            )

            if document_info is None:
                raise DocumentParseError("DOCX 缺少正文内容。")

            if (
                uncompressed_size > MAX_DOCX_UNCOMPRESSED_BYTES
                or document_info.file_size > MAX_DOCX_DOCUMENT_XML_BYTES
            ):
                raise DocumentParseError("DOCX 解压后的内容过大，已拒绝解析。")
~~~

对于pdf，就判断"%PDF-"是否在header里面；对于docx，由于docx本质是一个zip，那么就检查zipfile.is_zipfile(path)，查找是否有word/document.xml。

验证通过后，原始文件已经安全地保存在磁盘中，接下来需要在数据库中记录它的信息和处理状态。

## 6. 文件元数据和解析状态

### 6.1 文件元数据如何保存到数据库

回到upload_course_file_api，下面是：

~~~python
course_file = create_course_file_data(
    user_id=user_id,
    course_id=course_id.strip(),
    original_filename=original_filename,
    storage_filename=storage_filename,
    file_type=file_type,
    file_size=file_size,
    file_sha256=calculate_sha256(final_path),
)
~~~

这里保存的是文件的元数据，如：

~~~text
文件 ID
用户 ID
课程 ID
原始文件名
存储文件名
文件类型
文件大小
SHA-256
解析状态
~~~

文件正文仍然保存在磁盘中。

### 6.2 解析状态如何变化

上面的create_course_file_data：

~~~python
def create_course_file_data(
    *,
    user_id: int,
    course_id: str,
    original_filename: str,
    storage_filename: str,
    file_type: str,
    file_size: int,
    file_sha256: str,
) -> CourseFileRecord:
    file_id = uuid4().hex

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            _assert_course_exists(cursor, user_id, course_id)
            cursor.execute(
                """
                INSERT INTO course_files (
                    id, user_id, course_id, original_filename,
                    storage_filename, file_type, file_size, sha256,
                    parse_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    file_id,
                    user_id,
                    course_id,
                    original_filename,
                    storage_filename,
                    file_type,
                    file_size,
                    file_sha256,
                    DocumentParseStatus.PENDING.value,
                ),
            )
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

    if fetched is None:
        raise RuntimeError("文件元数据已写入，但无法读取。")
    return fetched[0]
~~~

可以看到里面的数据库操作：

~~~python
DocumentParseStatus.PENDING.value
~~~

初始化了文件的状态为pending，但这只是一个比较短暂的状态，表示文件已经写入，但是尚未开始解析。

回到upload_course_file_api中，接下来的

~~~python
set_course_file_parsing_data(user_id, course_file.id)
~~~

则将状态变成了parsing。接着：

~~~python
try:
    parsed_chunks = parse_document(final_path, file_type)
    course_file = replace_document_chunks_data(
        user_id=user_id,
        file_id=course_file.id,
        chunks=parsed_chunks,
    )
~~~

到这里，文件状态和真实处理过程已经连接起来，下面开始看文件如何变成可以保存和检索的文字。

## 7. 文件解析

第一句使用了parse_document：

~~~python
def parse_document(path: Path, file_type: str) -> list[ParsedChunk]:
    """Extract text locally and split it into searchable, source-aware chunks."""
    validate_file_signature(path, file_type)

    if file_type == "pdf":
        sections = _extract_pdf(path)
    elif file_type == "docx":
        sections = _extract_docx(path)
    elif file_type in {"txt", "md"}:
        sections = [_extract_text_file(path)]
    else:
        raise DocumentParseError("不支持的文件类型。")

    chunks: list[ParsedChunk] = []
    for section in sections:
        for content in _split_text(section.content):
            chunks.append(
                ParsedChunk(
                    content=content,
                    page_number=section.page_number,
                )
            )

    if not chunks:
        raise DocumentParseError(
            "无法从文件中提取可检索文字；扫描版 PDF 暂不支持 OCR。"
        )

    return chunks
~~~

这里通过判断使用不同的方法，不同格式使用不同解析方式：

~~~text
PDF
  → 按页提取文字

DOCX
  → 提取段落和表格

TXT / Markdown
  → 按编码读取文字
~~~

### 7.1 以 PDF 为例

例如对于pdf使用_extract_pdf：

~~~python
def _extract_pdf(path: Path) -> list[ExtractedSection]:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pypdf exposes several parser-specific errors.
        raise DocumentParseError("PDF 已损坏或无法读取。") from exc

    sections: list[ExtractedSection] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            content = _normalize_text(page.extract_text() or "")
        except Exception as exc:
            raise DocumentParseError(
                f"PDF 第 {page_number} 页无法提取文字。"
            ) from exc

        if content:
            sections.append(
                ExtractedSection(
                    content=content,
                    page_number=page_number,
                )
            )
    return sections
~~~

其中

~~~python
reader = PdfReader(str(path))
~~~

这一步使用了pypdf库，将path对象转换为字符串路径，使用PdfReader打开PDF。如果 PDF 损坏或无法读取：

~~~python
raise DocumentParseError("PDF 已损坏或无法读取。")
~~~

这个异常会被上层上传路由捕获，然后把文件状态改成failed。

~~~python
for page_number, page in enumerate(reader.pages, start=1):
~~~

说明采用了逐页读取。

~~~python
content = _normalize_text(page.extract_text() or "")
~~~

执行过程是:

~~~text
page.extract_text()
→ 取出当前页文字
→ 如果返回 None，就使用空字符串
→ 调用 _normalize_text() 清理格式
~~~

_normalize_text()会处理：

~~~text
删除空字符
统一换行符
压缩多余空格
压缩连续空行
~~~

最后

~~~python
sections.append(
    ExtractedSection(
        content=content,
        page_number=page_number,
    )
)
~~~

这一步后返回的就不是最终的ParsedChunk，而是按页面整理的ExtractedSection。

整体过程是：

~~~text
PDF
  ↓
_extract_pdf()
  ↓
ExtractedSection（按页）
  ↓
_split_text()
  ↓
ParsedChunk（按检索长度）
  ↓
document_chunks
~~~

由这一过程可知，它主要支持本身包含文字层的PDF。如果只有图片，就会在上层：

~~~python
if not chunks:
    raise DocumentParseError(
        "无法从文件中提取可检索文字；扫描版 PDF 暂不支持 OCR。"
    )
~~~

### 7.2 从 ExtractedSection 到 ParsedChunk

~~~python
for section in sections:
    for content in _split_text(section.content):
        chunks.append(
            ParsedChunk(
                content=content,
                page_number=section.page_number,
            )
        )
~~~

这是解析之后的操作，过程是：

~~~text
整份 PDF 文字
  ↓
按页提取
  ↓
清理空格和换行
  ↓
切成多个文本块
  ↓
保存每个文本块
~~~

因为后面检索时，不需要把整本 PDF 都交给模型，而是只找到相关的文本块。

得到ParsedChunk之后，还需要将它们持久化到数据库。

## 8. 文本块如何保存

解析完成后，下一步：

~~~python
course_file = replace_document_chunks_data(
    user_id=user_id,
    file_id=course_file.id,
    chunks=parsed_chunks,
)
~~~

这里调用了replace_document_chunks_data。这个函数的主要任务是：

删除这个文件旧的文本分块，保存本次解析得到的新分块，并更新文件状态。

~~~python
def replace_document_chunks_data(
    *,
    user_id: int,
    file_id: str,
    chunks: Iterable[ParsedChunk],
) -> CourseFileRecord:
~~~

输入有三个：

~~~text
user_id
当前用户，用来做权限隔离

file_id
当前课程文件的 ID

chunks
解析后的文本分块
~~~

chunks 中的每个元素是：

~~~python
ParsedChunk(
    content="一段文字",
    page_number=1
)
~~~

它的类型是：

~~~python
Iterable[ParsedChunk]
~~~

意思是它可以是列表，也可以是其他可遍历对象。

~~~python
prepared_chunks = list(chunks)
if not prepared_chunks:
    raise ValueError("没有可保存的解析文本。")
~~~

这里首先把chunks转成列表，然后检索是否为空

~~~python
with _get_connection() as connection:
    with connection.cursor() as cursor:
        fetched = _fetch_file_by_cursor(cursor, user_id, file_id)
        if fetched is None:
            raise ValueError("没有找到可操作的文件。")

        cursor.execute(
            "DELETE FROM document_chunks WHERE file_id = %s",
            (file_id,),
        )

        for chunk_index, chunk in enumerate(prepared_chunks):
            cursor.execute(
                """
                INSERT INTO document_chunks (
                    id, file_id, page_number, chunk_index, content, search_vector
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    to_tsvector('simple', %s)
                )
                """,
                (
                    uuid4().hex,
                    file_id,
                    chunk.page_number,
                    chunk_index,
                    chunk.content,
                    chunk.content,
                ),
            )

        extracted_char_count = sum(
            len(chunk.content)
            for chunk in prepared_chunks
        )
        cursor.execute(
            """
            UPDATE course_files
            SET
                parse_status = %s,
                parse_error = NULL,
                embedding_status = %s,
                embedding_error = NULL,
                embedding_model = NULL,
                embedding_dimension = NULL,
                embedded_at = NULL,
                extracted_char_count = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (
                DocumentParseStatus.PARSED.value,
                DocumentEmbeddingStatus.NOT_INDEXED.value,
                extracted_char_count,
                file_id,
                user_id,
            ),
        )
        fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

if fetched is None:
    raise RuntimeError("解析内容已保存，但无法读取文件。")
return fetched[0]
~~~

### 8.1 数据库连接和用户隔离

首先我们看到：

~~~python
with _get_connection() as connection:
    with connection.cursor() as cursor:
~~~

这里创建数据库连接connection，数据库游标cursor，后面是一个完整的数据库操作，确保失败一起回滚。

~~~python
fetched = _fetch_file_by_cursor(cursor, user_id, file_id)
if fetched is None:
    raise ValueError("没有找到可操作的文件。")
~~~

这里同时传入user_id和file_id，确认文件存在和属于当前用户，做了用户隔离。

### 8.2 删除旧 chunks，再插入新 chunks

~~~python
cursor.execute(
    "DELETE FROM document_chunks WHERE file_id = %s",
    (file_id,),
)
~~~

这里先删除该文件旧的chunks，再写入本次解析得到的新chunks，采用整批替换，防止重复检索，embedding和索引混乱的问题。

下面

~~~python
for chunk_index, chunk in enumerate(prepared_chunks):
~~~

中enumerate给每个chunk分配顺序号，然后执行插入操作

插入时的to_tsvector('simple', chunk.content)会根据文本生成search_vector，供PostgreSQL全文检索使用。它和后面的Embedding向量不是同一个东西。

### 8.3 统计文字长度

~~~python
extracted_char_count = sum(
    len(chunk.content)
    for chunk in prepared_chunks
)
~~~

这段代码统计所有分块的文字长度，记录了字符数。

### 8.4 更新文件状态

然后：

~~~sql
UPDATE course_files
SET
    parse_status = 'parsed',
    parse_error = NULL,
    embedding_status = 'not_indexed',
    embedding_error = NULL,
    embedding_model = NULL,
    embedding_dimension = NULL,
    embedded_at = NULL,
    extracted_char_count = ...
~~~

更新course_files数据库。这个时候解析状态变成了parsed，重置了embedding状态

因为文本块已经重新生成，旧Embedding对应的是旧文本，所以必须将Embedding状态重置，等待后续重新建立向量索引。

最后:

~~~python
fetched = _fetch_file_by_cursor(cursor, user_id, file_id)
if fetched is None:
    raise RuntimeError("解析内容已保存，但无法读取文件。")
return fetched[0]
~~~

重新查询文件，返回最新的CourseFileRecord。

这一个函数可以这样理解;

~~~text
确认文件归属
→ 删除旧 chunks
→ 插入新 chunks
→ 生成全文检索数据
→ 更新解析和向量状态
→ 返回最新文件信息
~~~

## 9. 这一部分和 RAG 的连接

到了这里，原始文件已经变成了保存在document_chunks中的文本块。后续的Embedding和检索会继续使用这些文本块，但属于下一部分的内容。

回到开头的完整链路，可以把这一篇压缩成：

~~~text
HTTP上传请求
→ 安全保存原始文件
→ 保存文件元数据和状态
→ 按文件类型提取文字
→ 切分并保存文本块
→ 为后续 RAG 准备数据
~~~
