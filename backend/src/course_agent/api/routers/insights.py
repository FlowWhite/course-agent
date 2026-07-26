"""Deadline-risk insight endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...app_logger import logger
from ...learning_insight_service import list_task_risks_data
from ...models import ToolResponse
from ..dependencies import get_current_user


router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("/risks")
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
