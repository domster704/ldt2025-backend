from fastapi import APIRouter

router = APIRouter()


@router.get("/backup")
async def backup() -> bool:
    return True