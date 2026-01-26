from pydantic import BaseModel


class DirectionResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    icon_url: str | None
    root_graph_id: int

    class Config:
        from_attributes = True