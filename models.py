from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskStatus(str, Enum):
    TODO = "todo"
    DONE = "done"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DocumentParseStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LearningPlanStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LearningPlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CourseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    teacher: str
    todo_count: int = Field(ge=0)


class TaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    course_id: str
    course_name: str
    title: str
    deadline: date
    status: TaskStatus
    priority: TaskPriority
    description: str


class TaskCreate(BaseModel):
    """新增任务时写入数据库的参数。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    deadline: date
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority
    description: str = Field(min_length=1)


class TaskUpdate(BaseModel):
    """修改任务普通字段时的参数，不允许修改任务 ID 或所属课程。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1)
    deadline: date | None = None
    priority: TaskPriority | None = None
    description: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_has_changes(self) -> "TaskUpdate":
        """确保更新请求至少提供一个实际要修改的字段。"""
        if all(
            value is None
            for value in (
                self.title,
                self.deadline,
                self.priority,
                self.description,
            )
        ):
            raise ValueError("至少提供一个需要修改的任务字段")
        return self


class TaskStatusUpdate(BaseModel):
    """切换任务完成状态时的参数。"""

    model_config = ConfigDict(extra="forbid")

    status: TaskStatus


class CourseFileRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    course_id: str
    original_filename: str
    file_type: str
    file_size: int = Field(gt=0)
    sha256: str
    parse_status: DocumentParseStatus
    parse_error: str | None = None
    extracted_char_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    created_at: datetime


class DocumentSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    file_name: str
    page: int | None = None
    content: str
    relevance: float = Field(ge=0)


class PlanSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    file_name: str
    page: int | None = None
    excerpt: str = Field(min_length=1, max_length=1_400)


class GeneratedPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1_200)
    estimated_minutes: int = Field(ge=5, le=480)
    deliverable: str = Field(min_length=1, max_length=500)
    acceptance_criteria: str = Field(min_length=1, max_length=700)


class TaskPlanDraft(BaseModel):
    """The constrained output generated before a user starts a learning plan."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal: str = Field(min_length=1, max_length=500)
    prerequisite_knowledge: list[str] = Field(max_length=12)
    steps: list[GeneratedPlanStep] = Field(min_length=1, max_length=12)


class LearningPlanStepRecord(GeneratedPlanStep):
    model_config = ConfigDict(extra="forbid")

    id: str
    position: int = Field(gt=0)
    status: LearningPlanStepStatus
    completed_at: datetime | None = None


class LearningPlanRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task_id: str
    course_id: str
    task_title: str
    deadline: date
    goal: str
    prerequisite_knowledge: list[str]
    sources: list[PlanSource]
    status: LearningPlanStatus
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    paused_at: datetime | None = None
    resumed_at: datetime | None = None
    completed_at: datetime | None = None
    steps: list[LearningPlanStepRecord]


class TaskRiskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    course_id: str
    course_name: str
    title: str
    deadline: date
    risk_level: RiskLevel
    score: int = Field(ge=0)
    days_remaining: int
    reasons: list[str]
    recommended_priority: TaskPriority
    sources: list[PlanSource]


class ToolResponse(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None
