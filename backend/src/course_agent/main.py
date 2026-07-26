import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import (
    Depends,
    File,
    Form,
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from .auth_service import (
    UserAlreadyExistsError,
    authenticate_user_data,
    create_user_data,
)
from .auth_security import (
    create_access_token,
    decode_access_token,
)
from .rate_limit import InMemoryRateLimiter
from .app_logger import logger
from .course_material_service import (
    MAX_UPLOAD_BYTES,
    calculate_sha256,
    create_course_file_data,
    create_storage_name,
    delete_course_file_data,
    get_course_file_data,
    get_owned_file_storage_data,
    list_course_files_data,
    replace_document_chunks_data,
    search_course_documents_data,
    sanitize_original_filename,
    set_course_file_parse_failed_data,
    set_course_file_parsing_data,
    storage_path_for,
)
from .document_parser import DocumentParseError, parse_document, validate_file_signature
from .learning_insight_service import (
    complete_learning_plan_step_data,
    confirm_learning_plan_data,
    create_learning_plan_data,
    get_learning_plan_data,
    list_learning_plans_data,
    list_task_risks_data,
    pause_learning_plan_data,
    resume_learning_plan_data,
)

from .postgres_data_service import (
    create_task_data,
    delete_task_data,
    get_task_detail_data,
    list_courses_data,
    list_tasks_data,
    update_task_data,
    update_task_status_data,
)
from .postgres_database import ensure_application_schema
from .models import (
    PlanSource,
    TaskStatusUpdate,
    TaskPriority,
    TaskUpdate,
    ToolResponse,
)
from agents.exceptions import (
    MaxTurnsExceeded,
    ModelBehaviorError,
)

from .agent_runtime import (
    create_course_agent,
    create_session,
    generate_task_plan_draft,
    reset_current_agent_course_id,
    reset_current_agent_user_id,
    run_agent_message,
    set_current_agent_course_id,
    set_current_agent_user_id,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_application_schema()
    yield


app = FastAPI(
    title="Course Agent API",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
       "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)
rate_limiter = InMemoryRateLimiter(
    max_requests=int(
        os.getenv(
            "RATE_LIMIT_MAX_REQUESTS",
            "60",
        )
    ),
    window_seconds=int(
        os.getenv(
            "RATE_LIMIT_WINDOW_SECONDS",
            "60",
        )
    ),
)


@app.middleware("http")
async def rate_limit_middleware(
    request: Request,
    call_next,
):
    """
    按客户端 IP 和请求路径进行限流。
    """
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    rate_limit_key = (
        f"{client_ip}:{request.url.path}"
    )

    allowed, retry_after = rate_limiter.check(
        rate_limit_key
    )

    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(retry_after),
            },
            content={
                "success": False,
                "data": None,
                "error": (
                    "请求过于频繁，请稍后再试"
                ),
            },
        )

    return await call_next(request)


def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """
    从 Authorization: Bearer <token>
    中解析当前用户。
    """
    try:
        return decode_access_token(token)

    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={
                "WWW-Authenticate": "Bearer"
            },
        ) from exc
@app.middleware("http")
async def add_utf8_charset(
    request: Request,
    call_next,
):
    """为 JSON 响应明确声明 UTF-8 编码。"""
    response = await call_next(request)

    content_type = response.headers.get(
        "content-type",
        "",
    )

    if (
        content_type.startswith("application/json")
        and "charset=" not in content_type.lower()
    ):
        response.headers["content-type"] = (
            f"{content_type}; charset=utf-8"
        )

    return response
class TaskCreateRequest(BaseModel):
    """API 新增任务请求。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    task_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    title: str = Field(min_length=1)
    deadline: date
    priority: TaskPriority
    description: str = Field(min_length=1)
class TaskDeleteRequest(BaseModel):
    """API 删除任务请求。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    confirmation: str = Field(min_length=1)


class FileDeleteRequest(BaseModel):
    """Explicit confirmation required before removing an uploaded source file."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    confirmation: str = Field(min_length=1)
class LoginRequest(BaseModel):
    """用户登录请求。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str = Field(
        min_length=3,
        max_length=100,
    )
    password: str = Field(
        min_length=1,
    )


class RegisterRequest(BaseModel):
    """用户注册请求。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str = Field(
        min_length=3,
        max_length=100,
    )
    password: str = Field(
        min_length=8,
    )
@app.get("/health")
def health_check() -> dict:
    """检查 API 服务是否正常运行。"""
    return {
        "success": True,
        "data": {
            "service": "course-agent",
            "status": "ok",
        },
        "error": None,
    }
@app.post("/api/v1/auth/login")
def login_api(
    request: LoginRequest,
) -> dict:
    """
    验证用户身份并返回访问令牌。
    """
    try:
        user = authenticate_user_data(
            username=request.username,
            password=request.password,
        )

        if user is None:
            return JSONResponse(
                status_code=401,
                content=ToolResponse(
                    success=False,
                    error="用户名或密码错误",
                ).model_dump(mode="json"),
            )

        access_token = create_access_token(
            user_id=user["id"],
            username=user["username"],
        )

        return ToolResponse(
            success=True,
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": user,
            },
        ).model_dump(mode="json")

    except Exception:
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="登录处理失败",
            ).model_dump(mode="json"),
        )


@app.post(
    "/api/v1/auth/register",
    status_code=201,
)
def register_api(
    request: RegisterRequest,
) -> dict:
    """
    创建用户账户。
    """
    try:
        user = create_user_data(
            username=request.username,
            password=request.password,
        )

        return ToolResponse(
            success=True,
            data={
                "user": user,
                "message": "注册成功，请登录",
            },
        ).model_dump(mode="json")

    except UserAlreadyExistsError as exc:
        return JSONResponse(
            status_code=409,
            content=ToolResponse(
                success=False,
                error=str(exc),
            ).model_dump(mode="json"),
        )

    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=ToolResponse(
                success=False,
                error=str(exc),
            ).model_dump(mode="json"),
        )

    except Exception:
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="注册处理失败",
            ).model_dump(mode="json"),
        )
async def _save_upload_to_storage(
    uploaded_file: UploadFile,
    destination: Path,
) -> int:
    """Stream an upload to a new temporary file, enforcing the size limit."""
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


@app.post("/api/v1/files", status_code=201)
async def upload_course_file_api(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Persist a user-scoped source file and synchronously parse it locally."""
    user_id = int(current_user["id"])
    original_filename = ""
    final_path: Path | None = None
    metadata_created = False

    try:
        original_filename, file_type = sanitize_original_filename(file.filename)
        storage_filename = create_storage_name(file_type)
        final_path = storage_path_for(user_id, storage_filename)
        file_size = await _save_upload_to_storage(file, final_path)
        validate_file_signature(final_path, file_type)

        course_file = create_course_file_data(
            user_id=user_id,
            course_id=course_id.strip(),
            original_filename=original_filename,
            storage_filename=storage_filename,
            file_type=file_type,
            file_size=file_size,
            file_sha256=calculate_sha256(final_path),
        )
        metadata_created = True
        set_course_file_parsing_data(user_id, course_file.id)

        try:
            parsed_chunks = parse_document(final_path, file_type)
            course_file = replace_document_chunks_data(
                user_id=user_id,
                file_id=course_file.id,
                chunks=parsed_chunks,
            )
        except DocumentParseError as exc:
            course_file = set_course_file_parse_failed_data(
                user_id=user_id,
                file_id=course_file.id,
                error=str(exc),
            )
        except Exception:
            logger.exception("课程文件解析失败：file_id=%s", course_file.id)
            course_file = set_course_file_parse_failed_data(
                user_id=user_id,
                file_id=course_file.id,
                error="文件解析失败，请检查文件是否损坏。",
            )

        return ToolResponse(
            success=True,
            data=course_file.model_dump(mode="json"),
        ).model_dump(mode="json")

    except HTTPException:
        raise
    except ValueError as exc:
        if final_path is not None and not metadata_created:
            final_path.unlink(missing_ok=True)
        return JSONResponse(
            status_code=400,
            content=ToolResponse(
                success=False,
                error=str(exc),
            ).model_dump(mode="json"),
        )
    except Exception:
        logger.exception("课程文件上传失败：filename=%r", original_filename)
        if final_path is not None and not metadata_created:
            final_path.unlink(missing_ok=True)
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="课程文件上传失败。",
            ).model_dump(mode="json"),
        )


@app.get("/api/v1/files")
def list_course_files_api(
    course_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        files = list_course_files_data(
            user_id=int(current_user["id"]),
            course_id=course_id,
        )
        return ToolResponse(
            success=True,
            data=[file.model_dump(mode="json") for file in files],
        ).model_dump(mode="json")
    except Exception:
        logger.exception("课程文件列表读取失败")
        return ToolResponse(
            success=False,
            error="课程文件列表读取失败。",
        ).model_dump(mode="json")


@app.get("/api/v1/files/{file_id}")
def get_course_file_api(
    file_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    course_file = get_course_file_data(
        int(current_user["id"]),
        file_id,
    )
    if course_file is None:
        raise HTTPException(status_code=404, detail="没有找到课程文件。")
    return ToolResponse(
        success=True,
        data=course_file.model_dump(mode="json"),
    ).model_dump(mode="json")


@app.delete("/api/v1/files/{file_id}")
def delete_course_file_api(
    file_id: str,
    request: FileDeleteRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    normalized_file_id = file_id.strip()
    expected_confirmation = f"确认删除文件 {normalized_file_id}"
    if request.confirmation != expected_confirmation:
        raise HTTPException(
            status_code=400,
            detail=f"删除操作未确认，请准确输入：{expected_confirmation}",
        )

    user_id = int(current_user["id"])
    owned_file = get_owned_file_storage_data(user_id, normalized_file_id)
    if owned_file is None:
        raise HTTPException(status_code=404, detail="没有找到课程文件。")

    course_file, storage_filename = owned_file
    storage_path = storage_path_for(user_id, storage_filename)
    try:
        storage_path.unlink(missing_ok=True)
        deleted_file = delete_course_file_data(user_id, normalized_file_id)
    except Exception as exc:
        logger.exception("课程文件删除失败：file_id=%s", normalized_file_id)
        raise HTTPException(
            status_code=500,
            detail="课程文件删除失败。",
        ) from exc

    return ToolResponse(
        success=True,
        data={
            "deleted_file": deleted_file.model_dump(mode="json"),
            "message": "课程文件已删除。",
        },
    ).model_dump(mode="json")


@app.get("/api/v1/courses")
def list_courses_api(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """返回所有课程及未完成任务数量。"""
    try:
        courses = list_courses_data()

        return ToolResponse(
            success=True,
            data=[
                course.model_dump(mode="json")
                for course in courses
            ],
        ).model_dump(mode="json")

    except Exception:
        return ToolResponse(
            success=False,
            error="课程数据查询失败。",
        ).model_dump(mode="json")
@app.get("/api/v1/tasks")
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """按课程和状态查询任务。"""
    try:
        tasks = list_tasks_data(
            course=course,
            status=status,
        )

        return ToolResponse(
            success=True,
            data=[
                task.model_dump(mode="json")
                for task in tasks
            ],
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
@app.get("/api/v1/tasks/{task_id}")
def get_task_detail_api(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """根据任务 ID 查询任务详情。"""
    try:
        task = get_task_detail_data(task_id)

        if task is None:
            return ToolResponse(
                success=False,
                error=f"没有找到任务：{task_id}",
            ).model_dump(mode="json")

        return ToolResponse(
            success=True,
            data=task.model_dump(mode="json"),
        ).model_dump(mode="json")

    except Exception:
        return ToolResponse(
            success=False,
            error="任务详情查询失败。",
        ).model_dump(mode="json")
@app.post("/api/v1/tasks")
def create_task_api(
    request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """通过 API 新增任务。"""
    try:
        task = create_task_data(
            task_id=request.task_id,
            course=request.course,
            title=request.title,
            deadline=request.deadline.isoformat(),
            priority=request.priority.value,
            description=request.description,
        )

        return ToolResponse(
            success=True,
            data=task.model_dump(mode="json"),
        ).model_dump(mode="json")

    except ValueError as exc:
        return ToolResponse(
            success=False,
            error=str(exc),
        ).model_dump(mode="json")

    except Exception:
        return ToolResponse(
            success=False,
            error="新增任务失败。",
        ).model_dump(mode="json")
@app.patch("/api/v1/tasks/{task_id}")
def update_task_api(
    task_id: str,
    request: TaskUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """通过 API 修改任务普通字段。"""
    try:
        task = update_task_data(
            task_id=task_id,
            title=request.title,
            deadline=(
                request.deadline.isoformat()
                if request.deadline is not None
                else None
            ),
            priority=(
                request.priority.value
                if request.priority is not None
                else None
            ),
            description=request.description,
        )

        return ToolResponse(
            success=True,
            data=task.model_dump(mode="json"),
        ).model_dump(mode="json")

    except ValueError as exc:
        return ToolResponse(
            success=False,
            error=str(exc),
        ).model_dump(mode="json")

    except Exception:
        return ToolResponse(
            success=False,
            error="修改任务失败。",
        ).model_dump(mode="json")
@app.patch("/api/v1/tasks/{task_id}/status")
def update_task_status_api(
    task_id: str,
    request: TaskStatusUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """通过 API 修改任务完成状态。"""
    try:
        task = update_task_status_data(
            task_id=task_id,
            status=request.status.value,
        )

        return ToolResponse(
            success=True,
            data=task.model_dump(mode="json"),
        ).model_dump(mode="json")

    except ValueError as exc:
        return ToolResponse(
            success=False,
            error=str(exc),
        ).model_dump(mode="json")

    except Exception:
        return ToolResponse(
            success=False,
            error="修改任务状态失败。",
        ).model_dump(mode="json")
@app.delete("/api/v1/tasks/{task_id}")
def delete_task_api(
    task_id: str,
    request: TaskDeleteRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """通过 API 删除任务。"""
    normalized_task_id = task_id.strip()

    expected_confirmation = (
        f"确认删除任务 {normalized_task_id}"
    )

    if request.confirmation != expected_confirmation:
        return ToolResponse(
            success=False,
            error=(
                "删除操作未确认。请准确输入："
                f"{expected_confirmation}"
            ),
        ).model_dump(mode="json")

    try:
        task = delete_task_data(
            normalized_task_id,
        )

        return ToolResponse(
            success=True,
            data={
                "deleted_task": task.model_dump(
                    mode="json"
                ),
                "message": "任务已删除。",
            },
        ).model_dump(mode="json")

    except ValueError as exc:
        return ToolResponse(
            success=False,
            error=str(exc),
        ).model_dump(mode="json")

    except Exception:
        return ToolResponse(
            success=False,
            error="删除任务失败。",
        ).model_dump(mode="json")
@app.post("/api/v1/tasks/{task_id}/plan", status_code=201)
def create_task_plan_api(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a saved, awaiting-confirmation learning-plan draft."""
    user_id = int(current_user["id"])
    task = get_task_detail_data(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="没有找到要拆解的任务。")

    try:
        try:
            results = search_course_documents_data(
                user_id=user_id,
                course=task.course_id,
                query=task.title,
            )
        except ValueError:
            results = []

        sources = [
            PlanSource(
                file_id=result.file_id,
                file_name=result.file_name,
                page=result.page,
                excerpt=result.content[:1_400],
            )
            for result in results
        ]
        draft = generate_task_plan_draft(
            task=task.model_dump(mode="json"),
            sources=[source.model_dump(mode="json") for source in sources],
        )
        plan = create_learning_plan_data(
            user_id=user_id,
            task_id=task.id,
            draft=draft,
            sources=sources,
        )
        return ToolResponse(
            success=True,
            data=plan.model_dump(mode="json"),
        ).model_dump(mode="json")
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=ToolResponse(
                success=False,
                error=str(exc),
            ).model_dump(mode="json"),
        )
    except Exception:
        logger.exception("学习计划草案生成失败：task_id=%s", task_id)
        return JSONResponse(
            status_code=502,
            content=ToolResponse(
                success=False,
                error="学习计划草案生成失败，请稍后重试。",
            ).model_dump(mode="json"),
        )


@app.get("/api/v1/plans")
def list_learning_plans_api(
    task_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    plans = list_learning_plans_data(
        user_id=int(current_user["id"]),
        task_id=task_id,
    )
    return ToolResponse(
        success=True,
        data=[plan.model_dump(mode="json") for plan in plans],
    ).model_dump(mode="json")


@app.get("/api/v1/plans/{plan_id}")
def get_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    plan = get_learning_plan_data(int(current_user["id"]), plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="没有找到学习计划。")
    return ToolResponse(
        success=True,
        data=plan.model_dump(mode="json"),
    ).model_dump(mode="json")


@app.post("/api/v1/plans/{plan_id}/confirm")
def confirm_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = confirm_learning_plan_data(
            int(current_user["id"]),
            plan_id,
        )
        return ToolResponse(
            success=True,
            data=plan.model_dump(mode="json"),
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/plans/{plan_id}/pause")
def pause_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = pause_learning_plan_data(
            int(current_user["id"]),
            plan_id,
        )
        return ToolResponse(
            success=True,
            data=plan.model_dump(mode="json"),
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/plans/{plan_id}/resume")
def resume_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = resume_learning_plan_data(
            int(current_user["id"]),
            plan_id,
        )
        return ToolResponse(
            success=True,
            data=plan.model_dump(mode="json"),
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/plans/{plan_id}/steps/{step_id}/complete")
def complete_learning_plan_step_api(
    plan_id: str,
    step_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = complete_learning_plan_step_data(
            user_id=int(current_user["id"]),
            plan_id=plan_id,
            step_id=step_id,
        )
        return ToolResponse(
            success=True,
            data=plan.model_dump(mode="json"),
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/insights/risks")
def list_deadline_risks_api(
    course_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        risks = list_task_risks_data(
            user_id=int(current_user["id"]),
            course_id=course_id,
        )
        return ToolResponse(
            success=True,
            data=[risk.model_dump(mode="json") for risk in risks],
        ).model_dump(mode="json")
    except Exception:
        logger.exception("截止日期风险计算失败")
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="截止日期风险计算失败。",
            ).model_dump(mode="json"),
        )


class ChatRequest(BaseModel):
    """Agent 对话请求。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    session_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


_course_agents: dict[str, object] = {}


def get_runtime_agent(
    course_id: str,
    course_name: str,
):
    """按课程创建并复用各自独立的 Agent 配置。"""
    agent = _course_agents.get(course_id)

    if agent is None:
        agent = create_course_agent(
            course_id=course_id,
            course_name=course_name,
        )
        _course_agents[course_id] = agent

    return agent


@app.post("/api/v1/chat")
def chat_api(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """通过 API 调用当前课程专属的 Agent。"""
    course_id = request.course_id.strip()
    course = next(
        (
            item
            for item in list_courses_data()
            if item.id == course_id
        ),
        None,
    )
    if course is None:
        raise HTTPException(status_code=404, detail="没有找到当前课程。")

    user_token = set_current_agent_user_id(int(current_user["id"]))
    course_token = set_current_agent_course_id(course.id)
    try:
        agent = get_runtime_agent(course.id, course.name)
        session = create_session(
            f"user-{current_user['id']}-course-{course.id}-{request.session_id}"
        )

        result = run_agent_message(
            agent=agent,
            user_input=request.message,
            session=session,
        )

        return ToolResponse(
            success=True,
            data={
                "session_id": request.session_id,
                "course_id": course.id,
                "reply": result.final_output,
            },
        ).model_dump(mode="json")

    except MaxTurnsExceeded:
        return ToolResponse(
            success=False,
            error="Agent 超过最大执行轮数。",
        ).model_dump(mode="json")

    except ModelBehaviorError:
        return ToolResponse(
            success=False,
            error="Agent 返回了无效的工具调用。",
        ).model_dump(mode="json")

    except Exception:
        logger.exception(
            "课程 Agent 对话处理失败：course_id=%s",
            course_id,
        )
        return ToolResponse(
            success=False,
            error="Agent 对话处理失败。",
        ).model_dump(mode="json")
    finally:
        reset_current_agent_course_id(course_token)
        reset_current_agent_user_id(user_token)
