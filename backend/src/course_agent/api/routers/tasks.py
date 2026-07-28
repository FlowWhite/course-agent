"""Task CRUD, planning, and non-destructive assignment-review endpoints."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from ...agent_runtime import (
    generate_task_plan_draft,
    generate_task_submission_assessment,
)
from ...app_logger import logger
from ...course_material_service import (
    MAX_UPLOAD_BYTES,
    sanitize_original_filename,
    search_course_documents_data,
)
from ...document_parser import DocumentParseError, parse_document, validate_file_signature
from ...learning_insight_service import create_learning_plan_data
from ...models import (
    PlanSource,
    TaskStatusUpdate,
    TaskSubmissionAssessmentResult,
    TaskUpdate,
    ToolResponse,
)
from ...postgres_data_service import (
    create_task_data,
    delete_task_data,
    get_task_detail_data,
    list_tasks_data,
    update_task_data,
    update_task_status_data,
)
from ..dependencies import get_current_user
from ..schemas import TaskCreateRequest, TaskDeleteRequest


router = APIRouter(prefix="/api/v1", tags=["tasks"])


MAX_SUBMISSION_ASSESSMENT_CHARS = 28_000


async def _save_submission_upload(
    uploaded_file: UploadFile,
    destination: Path,
) -> int:
    """Write one transient submission while enforcing the shared upload cap."""
    total_size = 0
    try:
        with destination.open("xb") as target:
            while chunk := await uploaded_file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="单个作业文件不能超过 20 MB。",
                    )
                target.write(chunk)
        if total_size == 0:
            raise HTTPException(status_code=400, detail="不允许上传空文件。")
        return total_size
    finally:
        await uploaded_file.close()


def _submission_excerpt(chunks) -> tuple[str, bool]:
    """Keep the model request bounded while retaining a submission's conclusion."""
    submission_text = "\n\n".join(chunk.content for chunk in chunks).strip()
    if len(submission_text) <= MAX_SUBMISSION_ASSESSMENT_CHARS:
        return submission_text, False

    head_length = 20_000
    tail_length = MAX_SUBMISSION_ASSESSMENT_CHARS - head_length
    return (
        "\n\n".join(
            [
                submission_text[:head_length],
                "[作业正文过长：中间内容未发送给评估器]",
                submission_text[-tail_length:],
            ]
        ),
        True,
    )


def _task_sources_for_assessment(user_id: int, task) -> list[PlanSource]:
    """Fetch only current-course material excerpts relevant to the task."""
    try:
        results = search_course_documents_data(
            user_id=user_id,
            course=task.course_id,
            query=task.title,
        )
    except ValueError:
        results = []
    return [
        PlanSource(
            file_id=result.file_id,
            file_name=result.file_name,
            page=result.page,
            excerpt=result.content[:1_400],
        )
        for result in results
    ]


@router.get("/tasks")
def list_tasks_api(
    course: str = "",
    status: Literal["all", "todo", "done"] = "all",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List tasks filtered by course and completion status."""
    user_id = int(current_user["id"])
    try:
        tasks = list_tasks_data(user_id=user_id, course=course, status=status)
        return ToolResponse(
            success=True,
            data=[task.model_dump(mode="json") for task in tasks],
        ).model_dump(mode="json")
    except ValueError as exc:
        return ToolResponse(success=False, error=str(exc)).model_dump(mode="json")
    except Exception:
        return ToolResponse(success=False, error="任务数据查询失败。").model_dump(mode="json")


@router.get("/tasks/{task_id}")
def get_task_detail_api(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return task detail by task ID."""
    user_id = int(current_user["id"])
    try:
        task = get_task_detail_data(user_id=user_id, task_id=task_id)
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
        return ToolResponse(success=False, error="任务详情查询失败。").model_dump(mode="json")


@router.post("/tasks")
def create_task_api(
    request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a task."""
    user_id = int(current_user["id"])
    try:
        task = create_task_data(
            user_id=user_id,
            task_id=request.task_id,
            course=request.course,
            title=request.title,
            deadline=request.deadline.isoformat(),
            priority=request.priority.value,
            description=request.description,
        )
        return ToolResponse(success=True, data=task.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        return ToolResponse(success=False, error=str(exc)).model_dump(mode="json")
    except Exception:
        return ToolResponse(success=False, error="新增任务失败。").model_dump(mode="json")


@router.patch("/tasks/{task_id}")
def update_task_api(
    task_id: str,
    request: TaskUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update ordinary task fields."""
    user_id = int(current_user["id"])
    try:
        task = update_task_data(
            user_id=user_id,
            task_id=task_id,
            title=request.title,
            deadline=request.deadline.isoformat() if request.deadline is not None else None,
            priority=request.priority.value if request.priority is not None else None,
            description=request.description,
        )
        return ToolResponse(success=True, data=task.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        return ToolResponse(success=False, error=str(exc)).model_dump(mode="json")
    except Exception:
        return ToolResponse(success=False, error="修改任务失败。").model_dump(mode="json")


@router.patch("/tasks/{task_id}/status")
def update_task_status_api(
    task_id: str,
    request: TaskStatusUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update task completion status."""
    user_id = int(current_user["id"])
    try:
        task = update_task_status_data(
            user_id=user_id,
            task_id=task_id,
            status=request.status.value,
        )
        return ToolResponse(success=True, data=task.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        return ToolResponse(success=False, error=str(exc)).model_dump(mode="json")
    except Exception:
        return ToolResponse(success=False, error="修改任务状态失败。").model_dump(mode="json")


@router.delete("/tasks/{task_id}")
def delete_task_api(
    task_id: str,
    request: TaskDeleteRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Delete a task after explicit user confirmation."""
    user_id = int(current_user["id"])
    normalized_task_id = task_id.strip()
    expected_confirmation = f"确认删除任务 {normalized_task_id}"
    if request.confirmation != expected_confirmation:
        return ToolResponse(
            success=False,
            error=f"删除操作未确认。请准确输入：{expected_confirmation}",
        ).model_dump(mode="json")
    try:
        task = delete_task_data(user_id=user_id, task_id=normalized_task_id)
        return ToolResponse(
            success=True,
            data={
                "deleted_task": task.model_dump(mode="json"),
                "message": "任务已删除。",
            },
        ).model_dump(mode="json")
    except ValueError as exc:
        return ToolResponse(success=False, error=str(exc)).model_dump(mode="json")
    except Exception:
        return ToolResponse(success=False, error="删除任务失败。").model_dump(mode="json")


@router.post("/tasks/{task_id}/plan", status_code=201)
def create_task_plan_api(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a saved, awaiting-confirmation learning-plan draft."""
    user_id = int(current_user["id"])
    task = get_task_detail_data(user_id=user_id, task_id=task_id)
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
        return ToolResponse(success=True, data=plan.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=ToolResponse(success=False, error=str(exc)).model_dump(mode="json"),
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


@router.post("/tasks/{task_id}/assessment")
async def assess_task_submission_api(
    task_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Assess a temporary uploaded submission against one owned task."""
    user_id = int(current_user["id"])
    task = get_task_detail_data(user_id=user_id, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="没有找到要评估的任务。")

    original_filename = ""
    try:
        original_filename, file_type = sanitize_original_filename(file.filename)
        with TemporaryDirectory(prefix="course-agent-submission-") as directory:
            submission_path = Path(directory) / f"submission.{file_type}"
            await _save_submission_upload(file, submission_path)
            validate_file_signature(submission_path, file_type)
            chunks = parse_document(submission_path, file_type)
            submission_text, submission_truncated = _submission_excerpt(chunks)

        sources = _task_sources_for_assessment(user_id, task)
    except HTTPException:
        raise
    except (DocumentParseError, ValueError) as exc:
        return JSONResponse(
            status_code=400,
            content=ToolResponse(success=False, error=str(exc)).model_dump(mode="json"),
        )
    except Exception:
        logger.exception("作业文件读取失败：task_id=%s", task_id)
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="作业文件读取失败，请检查文件后重试。",
            ).model_dump(mode="json"),
        )

    try:
        assessment = await run_in_threadpool(
            generate_task_submission_assessment,
            task=task.model_dump(mode="json"),
            submission_text=submission_text,
            sources=[source.model_dump(mode="json") for source in sources],
        )
        result = TaskSubmissionAssessmentResult(
            **assessment.model_dump(mode="json"),
            file_name=original_filename,
            submission_truncated=submission_truncated,
            sources=sources,
        )
        return ToolResponse(success=True, data=result.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except Exception:
        logger.exception("作业评估失败：task_id=%s", task_id)
        return JSONResponse(
            status_code=502,
            content=ToolResponse(
                success=False,
                error="作业评估暂时不可用，请稍后重试。",
            ).model_dump(mode="json"),
        )
