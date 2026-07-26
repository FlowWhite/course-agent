"""Request schemas owned by the HTTP API layer."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from ..models import TaskPriority


class RequestSchema(BaseModel):
    """Reject unexpected input and normalize surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskCreateRequest(RequestSchema):
    """API request for creating a task."""

    task_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    title: str = Field(min_length=1)
    deadline: date
    priority: TaskPriority
    description: str = Field(min_length=1)


class TaskDeleteRequest(RequestSchema):
    """Explicit confirmation required before removing a task."""

    confirmation: str = Field(min_length=1)


class FileDeleteRequest(RequestSchema):
    """Explicit confirmation required before removing a source file."""

    confirmation: str = Field(min_length=1)


class LoginRequest(RequestSchema):
    """User login request."""

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1)


class RegisterRequest(RequestSchema):
    """User registration request."""

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)


class ChatRequest(RequestSchema):
    """Course-scoped Agent conversation request."""

    session_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
