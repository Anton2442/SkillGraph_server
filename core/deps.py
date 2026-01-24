from fastapi import Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from authx import TokenPayload

from core.security import security, bearer
from core.database import get_db
from models import User


async def get_current_user(
    token = Security(bearer),
    payload: TokenPayload = Security(security.access_token_required),
    db: AsyncSession = Depends(get_db)
) -> User:
    result = await db.execute(
        select(User).where(User.id == payload.sub)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(401, "User not found")

    return user