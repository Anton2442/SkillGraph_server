from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from core.database import get_db
from models import Graph, GraphNode, GraphEdge, Skill, UserSkill, TestAttempt
from schemas.graphs import (
    GraphResponse,
    GraphNodeResponse,
    GraphEdgeResponse,
    GraphFullResponse,
)

from core.deps import get_current_user
from core.graph.service import GraphService


router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.get(
    "/{graph_id}",
    response_model=GraphResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Graph not found"},
    },
)
async def get_graph(
    graph_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    graph = await db.scalar(select(Graph).where(Graph.id == graph_id))

    if not graph:
        raise HTTPException(404, "Graph not found")

    return graph


@router.get(
    "/{graph_id}/nodes",
    response_model=list[GraphNodeResponse],
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Graph not found"},
    },
)
@router.get(
    "/{graph_id}/nodes",
    response_model=list[GraphNodeResponse],
)
async def get_graph_nodes(
    graph_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    # check graph exists
    graph = await db.scalar(select(Graph.id).where(Graph.id == graph_id))
    if not graph:
        raise HTTPException(404, "Graph not found")

    # load nodes with relations
    nodes = (
        await db.execute(
            select(GraphNode)
            .options(
                selectinload(GraphNode.skill)
                .selectinload(Skill.resources),
                selectinload(GraphNode.subgraph),
            )
            .where(GraphNode.graph_id == graph_id)
        )
    ).scalars().all()

    skill_ids = [n.skill_id for n in nodes if n.skill_id]

    # user skill states
    user_skills = (
        await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.id,
                UserSkill.skill_id.in_(skill_ids)
            )
        )
    ).scalars().all()

    # test attempts
    attempts = (
        await db.execute(
            select(TestAttempt).where(
                TestAttempt.user_id == user.id,
                TestAttempt.skill_id.in_(skill_ids)
            )
        )
    ).scalars().all()

    us_map = {u.skill_id: u for u in user_skills}

    # max score per skill
    progress = {}
    for a in attempts:
        progress[a.skill_id] = max(progress.get(a.skill_id, 0), a.score or 0)

    # build response
    return [
        {
            "id": n.id,
            "node_type": n.node_type,
            "position_x": n.position_x,
            "position_y": n.position_y,
            "skill_id": n.skill_id,
            "subgraph_id": n.subgraph_id,
            "skill": n.skill,
            "subgraph": n.subgraph,
            "status": (us_map[n.skill_id].status if n.skill_id in us_map else "locked") if n.skill_id else "available",
            "progress": progress.get(n.skill_id, 0) if n.skill_id else 0,
        }
        for n in nodes
    ]


@router.get(
    "/{graph_id}/edges",
    response_model=list[GraphEdgeResponse],
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Graph not found"},
    },
)
async def get_graph_edges(
    graph_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    graph = await db.scalar(select(Graph.id).where(Graph.id == graph_id))

    if not graph:
        raise HTTPException(404, "Graph not found")

    result = await db.execute(
        select(GraphEdge).where(GraphEdge.graph_id == graph_id)
    )
    edges = result.scalars().all()

    return edges


@router.get(
    "/{graph_id}/full",
    response_model=GraphFullResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Graph not found"},
    },
)
@router.get("/{graph_id}/full", response_model=GraphFullResponse)
async def get_graph_full(
    graph_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await GraphService.build_full_graph(db, user, graph_id)

    if not result:
        raise HTTPException(404, "Graph not found")

    return result


@router.post(
    "/init-user-skills",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Graph not found"},
    },
)
async def init_user_skills(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await GraphService.init_user_skills(db, user.id)

    return {"good": 200}