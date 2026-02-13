import uuid

from sqlalchemy import func, text, select
from models import TestAttempt, User, UserSkill, SkillStatus


class AuthService:

    @staticmethod
    async def create_email_token(db, user_id: int):
        token = str(uuid.uuid4())

        await db.execute(
            text("""
                INSERT INTO email_verification_tokens (user_id, token)
                VALUES (:user_id, :token)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    token = EXCLUDED.token,
                    expires_at = now() + interval '24 hours'
            """),
            {"user_id": user_id, "token": token}
        )

        await db.commit()

        return token

    @staticmethod
    async def verify_email(db, token: str):
        result = await db.execute(
            text("""
                SELECT user_id
                FROM email_verification_tokens
                WHERE token = :token
                AND expires_at > now()
            """),
            {"token": token}
        )

        row = result.first()

        # if no token found or expired
        if not row:
            return False

        user_id = row[0]

        await db.execute(
            text("""
                UPDATE users
                SET is_email_verified = true
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        )

        # delete token after success
        await db.execute(
            text("""
                DELETE FROM email_verification_tokens
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )

        await db.commit()

        return True
    
    @staticmethod
    async def get_profile(db, user_id: int):
        result = await db.execute(
            select(
                User.username,
                User.avatar_url,
                User.email_verified
            ).where(User.id == user_id)
        )

        user = result.first()

        skills_count = await AuthService._get_skills_count(db, user_id)
        tests_stats = await AuthService._get_tests_stats(db, user_id)

        return {
            "username": user.username,
            "email_verified": user.email_verified,
            "avatar": user.avatar_url,
            "skills": skills_count,
            **tests_stats,
        }

    @staticmethod
    async def _get_skills_count(db, user_id: int):
        result = await db.scalar(
            select(func.count())
            .select_from(UserSkill)
            .where(UserSkill.user_id == user_id,
                   UserSkill.status != SkillStatus.available,
                   UserSkill.status != SkillStatus.locked)
        )

        return result or 0

    @staticmethod
    async def _get_tests_stats(db, user_id: int):
        total_tests = await db.scalar(
            select(func.count())
            .select_from(TestAttempt)
            .where(TestAttempt.user_id == user_id)
        )

        best_scores_subquery = (
            select(
                TestAttempt.skill_id,
                func.max(TestAttempt.score).label("best_score")
            )
            .where(TestAttempt.user_id == user_id)
            .group_by(TestAttempt.skill_id)
            .subquery()
        )

        avg_score = await db.scalar(
            select(func.avg(best_scores_subquery.c.best_score))
        )

        return {
            "total_tests": total_tests or 0,
            "average_score": round(avg_score or 0)
        }