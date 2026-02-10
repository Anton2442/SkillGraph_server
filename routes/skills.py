from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.deps import get_current_user
from core.skill.service import SkillService
from models import Skill
from schemas.skills import QuestionResponse, SubmitAttemptRequest, TestResultResponse

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get(
    "/{skill_id}/questions",
    response_model=list[QuestionResponse],
    responses={
        200: {"description": "List of questions for the skill"},
        404: {"description": "Skill not found"},
        403: {"description": "Email not verified"}
    }
)
async def get_skill_questions(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if not user.email_verified:
        raise HTTPException(403, "Email not verified")

    skill = await db.scalar(
        select(Skill).where(Skill.id == skill_id)
    )

    if not skill:
        raise HTTPException(404, "Skill not found")

    result = await SkillService.load_questions(db, skill_id)

    return result


@router.post(
    "/{skill_id}/attempt",
    response_model=TestResultResponse,
    responses={
        200: {"description": "Test attempt result"},
        404: {"description": "Skill not found"},
        403: {"description": "Email not verified"},
        400: {"description": "Invalid request data"},
    }
)
async def submit_attempt(
    skill_id: int,
    data: SubmitAttemptRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if not user.email_verified:
        raise HTTPException(403, "Email not verified")

    skill = await db.scalar(
        select(Skill).where(Skill.id == skill_id)
    )

    if not skill:
        raise HTTPException(404, "Skill not found")

    try:
        return await SkillService.submit_attempt(
            db=db,
            user_id=user.id,
            skill_id=skill_id,
            answers=data.answers
        )

    except ValueError as e:
        raise HTTPException(400, str(e))