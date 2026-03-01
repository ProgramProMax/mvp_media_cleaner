from fastapi import APIRouter

router = APIRouter(tags=["tasks"])


@router.post("/")
async def create_task():
    return {
        'test': 'test'
    }
