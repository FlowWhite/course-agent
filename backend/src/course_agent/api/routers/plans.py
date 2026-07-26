"""Learning-plan lifecycle endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from ...learning_insight_service import (
    complete_learning_plan_step_data,
    confirm_learning_plan_data,
    get_learning_plan_data,
    list_learning_plans_data,
    pause_learning_plan_data,
    resume_learning_plan_data,
)
from ...models import ToolResponse
from ..dependencies import get_current_user


router = APIRouter(prefix="/api/v1", tags=["learning plans"])


@router.get("/plans")
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


@router.get("/plans/{plan_id}")
def get_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    plan = get_learning_plan_data(int(current_user["id"]), plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="没有找到学习计划。")
    return ToolResponse(success=True, data=plan.model_dump(mode="json")).model_dump(
        mode="json"
    )


@router.post("/plans/{plan_id}/confirm")
def confirm_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = confirm_learning_plan_data(int(current_user["id"]), plan_id)
        return ToolResponse(success=True, data=plan.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/pause")
def pause_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = pause_learning_plan_data(int(current_user["id"]), plan_id)
        return ToolResponse(success=True, data=plan.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/resume")
def resume_learning_plan_api(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        plan = resume_learning_plan_data(int(current_user["id"]), plan_id)
        return ToolResponse(success=True, data=plan.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/steps/{step_id}/complete")
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
        return ToolResponse(success=True, data=plan.model_dump(mode="json")).model_dump(
            mode="json"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
