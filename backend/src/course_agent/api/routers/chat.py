"""Course-scoped Agent conversation endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from agents.exceptions import MaxTurnsExceeded, ModelBehaviorError

from ...agent_runtime import (
    create_course_agent,
    create_session,
    reset_current_agent_course_id,
    reset_current_agent_user_id,
    run_agent_message,
    set_current_agent_course_id,
    set_current_agent_user_id,
)
from ...app_logger import logger
from ...models import ToolResponse
from ...postgres_data_service import list_courses_data
from ..dependencies import get_current_user
from ..schemas import ChatRequest


router = APIRouter(prefix="/api/v1", tags=["agent"])
_course_agents: dict[str, object] = {}


def get_runtime_agent(course_id: str, course_name: str):
    """Create and reuse an isolated Agent configuration per course."""
    agent = _course_agents.get(course_id)
    if agent is None:
        agent = create_course_agent(course_id=course_id, course_name=course_name)
        _course_agents[course_id] = agent
    return agent


@router.post("/chat")
def chat_api(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Run the Agent constrained to the currently selected course."""
    user_id = int(current_user["id"])
    course_id = request.course_id.strip()
    course = next(
        (
            item
            for item in list_courses_data(user_id=user_id)
            if item.id == course_id
        ),
        None,
    )
    if course is None:
        raise HTTPException(status_code=404, detail="没有找到当前课程。")
    user_token = set_current_agent_user_id(user_id)
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
        logger.exception("课程 Agent 对话处理失败：course_id=%s", course_id)
        return ToolResponse(
            success=False,
            error="Agent 对话处理失败。",
        ).model_dump(mode="json")
    finally:
        reset_current_agent_course_id(course_token)
        reset_current_agent_user_id(user_token)
