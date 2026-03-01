from fastapi.routing import APIRouter

from .task import router as task_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(
    task_router, prefix="/tasks", tags=["tasks"]
)
