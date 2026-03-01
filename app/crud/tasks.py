from sqlalchemy.ext.asyncio import AsyncSession

from .base import CRUDBase
from app.models.tasks import Task, StatusEnum
from app.schemas.tasks import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):

    async def update_status(
        self,
        session: AsyncSession,
        task_id: int,
        status: StatusEnum
    ) -> Task:
        task: Task = self.get(task_id)
        task.status = status
        session.add(task)
        session.commit()
        session.refresh(task)
        return task


task_crud = CRUDTask(Task)
