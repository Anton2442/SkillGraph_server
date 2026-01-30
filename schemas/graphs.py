from pydantic import BaseModel
from schemas.skills import SkillResponse


class GraphResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None = None

    class Config:
        from_attributes = True


class SubgraphResponse(BaseModel):
    id: int
    title: str | None = None

    class Config:
        from_attributes = True


class GraphNodeResponse(BaseModel):
    id: int
    node_type: str

    position_x: int
    position_y: int

    skill: SkillResponse | None = None
    subgraph: SubgraphResponse | None = None

    status: str
    progress: int

    class Config:
        from_attributes = True
    

class GraphEdgeResponse(BaseModel):
    id: int
    from_node_id: int
    to_node_id: int
    relation_type: str

    class Config:
        from_attributes = True


class GraphFullResponse(BaseModel):
    graph: GraphResponse
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]