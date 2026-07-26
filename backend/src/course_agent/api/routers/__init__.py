"""Feature routers exposed by the Course Agent API."""

from .auth import router as auth_router
from .chat import router as chat_router
from .courses import router as courses_router
from .files import router as files_router
from .insights import router as insights_router
from .plans import router as plans_router
from .tasks import router as tasks_router

__all__ = [
    "auth_router",
    "chat_router",
    "courses_router",
    "files_router",
    "insights_router",
    "plans_router",
    "tasks_router",
]
