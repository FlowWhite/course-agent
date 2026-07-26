"""Course listing endpoints."""

from fastapi import APIRouter, Depends

from ...models import ToolResponse
from ...postgres_data_service import list_courses_data
from ..dependencies import get_current_user


router = APIRouter(prefix="/api/v1", tags=["courses"])


@router.get("/courses")
def list_courses_api(current_user: dict = Depends(get_current_user)) -> dict:
    """Return all courses and their unfinished-task counts."""
    try:
        courses = list_courses_data(user_id=int(current_user["id"]))
        return ToolResponse(
            success=True,
            data=[course.model_dump(mode="json") for course in courses],
        ).model_dump(mode="json")
    except Exception:
        return ToolResponse(
            success=False,
            error="课程数据查询失败。",
        ).model_dump(mode="json")
