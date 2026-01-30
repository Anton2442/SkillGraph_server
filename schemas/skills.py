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
