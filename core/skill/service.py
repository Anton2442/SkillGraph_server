from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from models import (
    Skill,
    Question,
    TestAttempt,
    UserSkill,
    SkillStatus
)


class SkillService:

    @staticmethod
    async def load_questions(db, skill_id: int):
        return (
            await db.execute(
                select(Question)
                .options(selectinload(Question.answers))
                .where(Question.skill_id == skill_id)
            )
        ).scalars().all()

    @staticmethod
    def build_answer_maps(questions):
        answer_to_question = {}
        correct_by_question = {}

        for q in questions:
            correct_by_question[q.id] = set()

            for a in q.answers:
                answer_to_question[a.id] = q.id

                if a.is_correct:
                    correct_by_question[q.id].add(a.id)

        return answer_to_question, correct_by_question

    @staticmethod
    def group_user_answers(answer_ids, answer_to_question):
        grouped = defaultdict(set)

        for aid in answer_ids:
            qid = answer_to_question.get(aid)

            if qid is None:
                raise ValueError("invalid answer")

            grouped[qid].add(aid)

        return grouped

    @staticmethod
    def calculate_score(questions, user_answers, correct_answers):
        correct = 0

        for q in questions:
            if user_answers[q.id] == correct_answers.get(q.id, set()):
                correct += 1

        total = len(questions)
        return int((correct / total) * 100) if total else 0

    @staticmethod
    def compute_status(best_score: int):
        if best_score == 100:
            return SkillStatus.mastered
        if best_score >= 70:
            return SkillStatus.completed
        if best_score > 0:
            return SkillStatus.available
        return SkillStatus.locked

    @staticmethod
    async def get_best_score(db, user_id: int, skill_id: int):
        return (
            await db.scalar(
                select(func.max(TestAttempt.score))
                .where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.skill_id == skill_id
                )
            )
        ) or 0

    @staticmethod
    async def save_attempt(db, user_id: int, skill_id: int, score: int, is_passed: bool):
        attempt = TestAttempt(
            user_id=user_id,
            skill_id=skill_id,
            score=score,
            is_passed=is_passed,
        )

        if is_passed:
            attempt.completed_at = func.now()

        db.add(attempt)
        await db.flush()
        return attempt

    @staticmethod
    async def update_user_skill(db, user_id: int, skill_id: int, new_status: SkillStatus):
        us = await db.scalar(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id
            )
        )

        now = func.now()

        if us:
            us.status = new_status

            if new_status in (SkillStatus.completed, SkillStatus.mastered) and not us.completed_at:
                us.completed_at = now

            if not us.unlocked_at:
                us.unlocked_at = now

        else:
            db.add(UserSkill(
                user_id=user_id,
                skill_id=skill_id,
                status=new_status,
                unlocked_at=now,
                completed_at=now if new_status in (SkillStatus.completed, SkillStatus.mastered) else None,
            ))

    @staticmethod
    async def submit_attempt(db, user_id: int, skill_id: int, answers):
        questions = await SkillService.load_questions(db, skill_id)

        if not questions:
            raise ValueError("no questions")

        answer_to_question, correct_by_question = SkillService.build_answer_maps(questions)

        user_answers = SkillService.group_user_answers(answers, answer_to_question)

        score = SkillService.calculate_score(
            questions,
            user_answers,
            correct_by_question
        )

        is_passed = score >= 70

        attempt = await SkillService.save_attempt(
            db,
            user_id,
            skill_id,
            score,
            is_passed
        )

        best_score = await SkillService.get_best_score(db, user_id, skill_id)

        status = SkillService.compute_status(best_score)

        await SkillService.update_user_skill(
            db,
            user_id,
            skill_id,
            status
        )

        await db.commit()

        return {
            "attempt_id": attempt.id,
            "score": score,
            "is_passed": is_passed
        }