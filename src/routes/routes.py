from fastapi import APIRouter

router = APIRouter(prefix="/padhai")


@router.get("/")
async def get_data():
    return {
        "message": "Book retrieved successfully",
    }
