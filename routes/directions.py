from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.deps import get_current_user
from models import Direction
from schemas.directions import DirectionResponse

router = APIRouter(prefix="/directions", tags=["directions"])


@router.get(
    "/",
    response_model=list[DirectionResponse],
    responses={
        200: {"description": "List of directions"}
    }
)
async def get_directions(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    result = await db.execute(select(Direction))
    return result.scalars().all()


@router.get(
    "/{slug}",
    response_model=DirectionResponse,
    responses={
        404: {"description": "Direction not found"}
    }
)
async def get_direction(
    slug: str,
    db: AsyncSession = Depends(get_db), 
    user=Depends(get_current_user)
):
    result = await db.execute(
        select(Direction).where(Direction.slug == slug)
    )

    direction = result.scalar_one_or_none()

    if not direction:
        raise HTTPException(404, "Direction not found")

    return direction