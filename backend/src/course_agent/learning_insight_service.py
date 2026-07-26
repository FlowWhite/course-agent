"""Persistent learning plans and deterministic deadline-risk calculations."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .course_material_service import search_course_documents_data
from .models import (
    LearningPlanRecord,
    LearningPlanStatus,
    LearningPlanStepRecord,
    LearningPlanStepStatus,
    PlanSource,
    RiskLevel,
    TaskPlanDraft,
    TaskPriority,
    TaskRiskRecord,
)
from .postgres_data_service import get_task_detail_data
from .postgres_database import get_postgres_connection


def _get_connection():
    connection = get_postgres_connection()
    connection.row_factory = dict_row
    return connection


def _sources_from_search_results(results) -> list[PlanSource]:
    return [
        PlanSource(
            file_id=result.file_id,
            file_name=result.file_name,
            page=result.page,
            excerpt=result.content[:1_400],
        )
        for result in results[:6]
    ]


def create_learning_plan_data(
    *,
    user_id: int,
    task_id: str,
    draft: TaskPlanDraft,
    sources: list[PlanSource],
) -> LearningPlanRecord:
    task = get_task_detail_data(user_id=user_id, task_id=task_id)
    if task is None:
        raise ValueError("没有找到要生成计划的任务。")
    if task.status.value == "done":
        raise ValueError("已完成任务无需生成新的学习计划。")

    plan_id = uuid4().hex
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO learning_plans (
                    id, user_id, task_id, course_id, goal,
                    prerequisite_knowledge, sources, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    plan_id,
                    user_id,
                    task.id,
                    task.course_id,
                    draft.goal,
                    Jsonb(draft.prerequisite_knowledge),
                    Jsonb([
                        source.model_dump(mode="json")
                        for source in sources
                    ]),
                    LearningPlanStatus.AWAITING_CONFIRMATION.value,
                ),
            )

            for position, step in enumerate(draft.steps, start=1):
                cursor.execute(
                    """
                    INSERT INTO learning_plan_steps (
                        id, plan_id, position, title, description,
                        estimated_minutes, deliverable, acceptance_criteria,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4().hex,
                        plan_id,
                        position,
                        step.title,
                        step.description,
                        step.estimated_minutes,
                        step.deliverable,
                        step.acceptance_criteria,
                        LearningPlanStepStatus.PENDING.value,
                    ),
                )

            plan = _fetch_plan_by_cursor(cursor, user_id, plan_id)

    if plan is None:
        raise RuntimeError("学习计划已创建，但无法读取。")
    return plan


def _fetch_plan_by_cursor(
    cursor,
    user_id: int,
    plan_id: str,
) -> LearningPlanRecord | None:
    cursor.execute(
        """
        SELECT
            p.id,
            p.task_id,
            p.course_id,
            t.title AS task_title,
            t.deadline,
            p.goal,
            p.prerequisite_knowledge,
            p.sources,
            p.status,
            p.created_at,
            p.updated_at,
            p.confirmed_at,
            p.paused_at,
            p.resumed_at,
            p.completed_at
        FROM learning_plans AS p
        JOIN tasks AS t
            ON t.id = p.task_id
        WHERE p.id = %s AND p.user_id = %s
        """,
        (plan_id, user_id),
    )
    plan_row = cursor.fetchone()
    if plan_row is None:
        return None

    cursor.execute(
        """
        SELECT
            id, position, title, description, estimated_minutes,
            deliverable, acceptance_criteria, status, completed_at
        FROM learning_plan_steps
        WHERE plan_id = %s
        ORDER BY position
        """,
        (plan_id,),
    )
    steps = [
        LearningPlanStepRecord.model_validate(row)
        for row in cursor.fetchall()
    ]
    data = dict(plan_row)
    data["steps"] = steps
    return LearningPlanRecord.model_validate(data)


def get_learning_plan_data(
    user_id: int,
    plan_id: str,
) -> LearningPlanRecord | None:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            return _fetch_plan_by_cursor(cursor, user_id, plan_id)


def list_learning_plans_data(
    user_id: int,
    task_id: str | None = None,
) -> list[LearningPlanRecord]:
    parameters: list[Any] = [user_id]
    where = "WHERE user_id = %s"
    if task_id and task_id.strip():
        where += " AND task_id = %s"
        parameters.append(task_id.strip())

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id
                FROM learning_plans
                {where}
                ORDER BY created_at DESC
                """,
                parameters,
            )
            plan_ids = [str(row["id"]) for row in cursor.fetchall()]
            return [
                plan
                for plan_id in plan_ids
                if (plan := _fetch_plan_by_cursor(cursor, user_id, plan_id)) is not None
            ]


def confirm_learning_plan_data(
    user_id: int,
    plan_id: str,
) -> LearningPlanRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            _require_plan_status(
                cursor,
                user_id,
                plan_id,
                LearningPlanStatus.AWAITING_CONFIRMATION,
            )
            cursor.execute(
                """
                UPDATE learning_plans
                SET
                    status = %s,
                    confirmed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (LearningPlanStatus.ACTIVE.value, plan_id, user_id),
            )
            _start_next_pending_step(cursor, plan_id)
            plan = _fetch_plan_by_cursor(cursor, user_id, plan_id)

    if plan is None:
        raise RuntimeError("学习计划已确认，但无法读取。")
    return plan


def pause_learning_plan_data(
    user_id: int,
    plan_id: str,
) -> LearningPlanRecord:
    return _set_plan_status(
        user_id=user_id,
        plan_id=plan_id,
        required_status=LearningPlanStatus.ACTIVE,
        next_status=LearningPlanStatus.PAUSED,
        timestamp_column="paused_at",
    )


def resume_learning_plan_data(
    user_id: int,
    plan_id: str,
) -> LearningPlanRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            _require_plan_status(
                cursor,
                user_id,
                plan_id,
                LearningPlanStatus.PAUSED,
            )
            cursor.execute(
                """
                UPDATE learning_plans
                SET
                    status = %s,
                    resumed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (LearningPlanStatus.ACTIVE.value, plan_id, user_id),
            )
            _start_next_pending_step(cursor, plan_id)
            plan = _fetch_plan_by_cursor(cursor, user_id, plan_id)

    if plan is None:
        raise RuntimeError("学习计划已恢复，但无法读取。")
    return plan


def _set_plan_status(
    *,
    user_id: int,
    plan_id: str,
    required_status: LearningPlanStatus,
    next_status: LearningPlanStatus,
    timestamp_column: str,
) -> LearningPlanRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            _require_plan_status(cursor, user_id, plan_id, required_status)
            cursor.execute(
                f"""
                UPDATE learning_plans
                SET
                    status = %s,
                    {timestamp_column} = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (next_status.value, plan_id, user_id),
            )
            plan = _fetch_plan_by_cursor(cursor, user_id, plan_id)

    if plan is None:
        raise RuntimeError("学习计划状态已更新，但无法读取。")
    return plan


def _require_plan_status(
    cursor,
    user_id: int,
    plan_id: str,
    expected_status: LearningPlanStatus,
) -> None:
    cursor.execute(
        """
        SELECT status
        FROM learning_plans
        WHERE id = %s AND user_id = %s
        """,
        (plan_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("没有找到可操作的学习计划。")
    if row["status"] != expected_status.value:
        raise ValueError("学习计划当前状态不允许此操作。")


def _start_next_pending_step(cursor, plan_id: str) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM learning_plan_steps
        WHERE plan_id = %s AND status = %s
        """,
        (plan_id, LearningPlanStepStatus.IN_PROGRESS.value),
    )
    if cursor.fetchone() is not None:
        return

    cursor.execute(
        """
        UPDATE learning_plan_steps
        SET status = %s
        WHERE id = (
            SELECT id
            FROM learning_plan_steps
            WHERE plan_id = %s AND status = %s
            ORDER BY position
            LIMIT 1
        )
        """,
        (
            LearningPlanStepStatus.IN_PROGRESS.value,
            plan_id,
            LearningPlanStepStatus.PENDING.value,
        ),
    )


def complete_learning_plan_step_data(
    *,
    user_id: int,
    plan_id: str,
    step_id: str,
) -> LearningPlanRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            _require_plan_status(
                cursor,
                user_id,
                plan_id,
                LearningPlanStatus.ACTIVE,
            )
            cursor.execute(
                """
                UPDATE learning_plan_steps
                SET
                    status = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE
                    id = %s
                    AND plan_id = %s
                    AND status IN (%s, %s)
                """,
                (
                    LearningPlanStepStatus.COMPLETED.value,
                    step_id,
                    plan_id,
                    LearningPlanStepStatus.PENDING.value,
                    LearningPlanStepStatus.IN_PROGRESS.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("没有找到可完成的学习步骤。")

            _start_next_pending_step(cursor, plan_id)
            cursor.execute(
                """
                SELECT 1
                FROM learning_plan_steps
                WHERE plan_id = %s AND status != %s
                """,
                (plan_id, LearningPlanStepStatus.COMPLETED.value),
            )
            all_completed = cursor.fetchone() is None
            if all_completed:
                cursor.execute(
                    """
                    UPDATE learning_plans
                    SET
                        status = %s,
                        completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                    """,
                    (LearningPlanStatus.COMPLETED.value, plan_id, user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE learning_plans
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                    """,
                    (plan_id, user_id),
                )
            plan = _fetch_plan_by_cursor(cursor, user_id, plan_id)

    if plan is None:
        raise RuntimeError("学习步骤已完成，但无法读取计划。")
    return plan


def list_task_risks_data(
    *,
    user_id: int,
    course_id: str | None = None,
) -> list[TaskRiskRecord]:
    parameters: list[Any] = [user_id]
    where_clause = "WHERE t.user_id = %s AND t.status = 'todo'"
    if course_id and course_id.strip():
        where_clause += " AND t.course_id = %s"
        parameters.append(course_id.strip())

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    t.id,
                    t.course_id,
                    c.name AS course_name,
                    t.title,
                    t.deadline,
                    t.priority
                FROM tasks AS t
                JOIN courses AS c
                    ON c.id = t.course_id
                    AND c.user_id = t.user_id
                {where_clause}
                ORDER BY t.deadline ASC
                """,
                parameters,
            )
            task_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    p.task_id,
                    t.deadline,
                    COALESCE(SUM(s.estimated_minutes) FILTER (
                        WHERE s.status != 'completed'
                    ), 0) AS remaining_minutes
                FROM learning_plans AS p
                JOIN tasks AS t
                    ON t.id = p.task_id
                    AND t.user_id = p.user_id
                LEFT JOIN learning_plan_steps AS s
                    ON s.plan_id = p.id
                WHERE p.user_id = %s AND p.status = 'active'
                GROUP BY p.task_id, t.deadline
                """,
                (user_id,),
            )
            active_plans = cursor.fetchall()

    plan_minutes = {
        str(row["task_id"]): int(row["remaining_minutes"])
        for row in active_plans
    }
    active_deadlines = [row["deadline"] for row in active_plans]

    risks: list[TaskRiskRecord] = []
    today = date.today()
    for task in task_rows:
        deadline = task["deadline"]
        days_remaining = (deadline - today).days
        score, reasons = _base_risk_score(
            days_remaining=days_remaining,
            priority=task["priority"],
        )

        remaining_minutes = plan_minutes.get(str(task["id"]), 0)
        if remaining_minutes:
            capacity_minutes = max(days_remaining, 1) * 120
            if remaining_minutes > capacity_minutes:
                score += 2
                reasons.append(
                    f"当前学习计划还需约 {remaining_minutes} 分钟，时间余量偏紧"
                )

        overlapping_plans = sum(
            1
            for other_deadline in active_deadlines
            if other_deadline != deadline
            and abs((other_deadline - deadline).days) <= 3
        )
        if overlapping_plans:
            score += 2
            reasons.append("附近截止日期已有进行中的学习计划，可能存在时间冲突")

        sources = _relevant_material_sources(
            user_id=user_id,
            course_id=str(task["course_id"]),
            task_title=str(task["title"]),
        )
        if sources and any(
            marker in source.excerpt
            for source in sources
            for marker in ("提交", "必须", "要求", "验收", "报告")
        ):
            score += 1
            reasons.append("关联课程资料包含提交或验收要求，需预留核对时间")

        risk_level = _risk_level_from_score(score)
        recommended_priority = (
            TaskPriority.HIGH
            if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
            else TaskPriority.MEDIUM
            if risk_level == RiskLevel.MEDIUM
            else TaskPriority(task["priority"])
        )
        risks.append(
            TaskRiskRecord(
                task_id=str(task["id"]),
                course_id=str(task["course_id"]),
                course_name=str(task["course_name"]),
                title=str(task["title"]),
                deadline=deadline,
                risk_level=risk_level,
                score=score,
                days_remaining=days_remaining,
                reasons=reasons,
                recommended_priority=recommended_priority,
                sources=sources,
            )
        )

    severity_order = {
        RiskLevel.CRITICAL: 0,
        RiskLevel.HIGH: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3,
    }
    return sorted(
        risks,
        key=lambda risk: (
            severity_order[risk.risk_level],
            risk.deadline,
            -risk.score,
        ),
    )


def _base_risk_score(
    *,
    days_remaining: int,
    priority: str,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if days_remaining < 0:
        score += 12
        reasons.append(f"已逾期 {-days_remaining} 天")
    elif days_remaining == 0:
        score += 10
        reasons.append("截止日期就是今天")
    elif days_remaining <= 1:
        score += 8
        reasons.append("距离截止日期不足两天")
    elif days_remaining <= 3:
        score += 6
        reasons.append("距离截止日期不足四天")
    elif days_remaining <= 7:
        score += 3
        reasons.append("截止日期在一周内")

    if priority == TaskPriority.HIGH.value:
        score += 3
        reasons.append("任务优先级为高")
    elif priority == TaskPriority.MEDIUM.value:
        score += 1
        reasons.append("任务优先级为中")

    if not reasons:
        reasons.append("当前截止日期和优先级处于可控范围")
    return score, reasons


def _risk_level_from_score(score: int) -> RiskLevel:
    if score >= 10:
        return RiskLevel.CRITICAL
    if score >= 7:
        return RiskLevel.HIGH
    if score >= 4:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _relevant_material_sources(
    *,
    user_id: int,
    course_id: str,
    task_title: str,
) -> list[PlanSource]:
    try:
        results = search_course_documents_data(
            user_id=user_id,
            course=course_id,
            query=task_title,
            limit=2,
        )
    except Exception:
        # Risk calculation remains available when there are no documents yet
        # or a non-critical document-search failure occurs.
        return []
    return _sources_from_search_results(results)
