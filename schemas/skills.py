from pydantic import BaseModel


class SkillResource(BaseModel):
    url: str
    type: str

    class Config:
        from_attributes = True


class SkillResponse(BaseModel):
    id: int
    title: str
    description: str | None = None

    resources: list[SkillResource] = []

    class Config:
        from_attributes = True


class AnswerResponse(BaseModel):
    id: int
    text: str

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    type: str
    text: str
    code_snippet: str | None = None

    answers: list[AnswerResponse]

    class Config:
        from_attributes = True


class SubmitAttemptRequest(BaseModel):
    answers: list[int]


class TestResultResponse(BaseModel):
    attempt_id: int
    score: int
    is_passed: bool