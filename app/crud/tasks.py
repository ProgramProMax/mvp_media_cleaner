from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tasks import StatusEnum, Task
from app.schemas.tasks import TaskCreate, TaskUpdate
from .base import CRUDBase


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):

    async def update_status(
        self,
        session: AsyncSession,
        task_id: int,
        status: StatusEnum
    ) -> Task:
        task: Task = await self.get(session, task_id)
        task.status = status.value
        session.add(task)
        session.commit()
        session.refresh(task)
        return task

    async def update_by_id(
        self,
        session: AsyncSession,
        task_id: int,
        obj_in: TaskUpdate
    ) -> Task:
        task: Task = await self.get(session, task_id)
        return await self.update(session, task, obj_in)


task_crud = CRUDTask(Task)
