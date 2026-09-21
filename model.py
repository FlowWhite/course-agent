from pydantic import BaseModel


class Course(BaseModel):
    id: str
    name: str
    teacher: str


class Task(BaseModel):
    id: str
    course_id: str
    title: str
    deadline: str
    status: str
    priority: str
    description: str