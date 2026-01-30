from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from models import (
    Graph, GraphNode, GraphEdge,
    Skill, UserSkill, TestAttempt,
    SkillStatus
)
from .evaluator import GraphEvaluator


class GraphService:

    @staticmethod
    async def build_full_graph(db, user, graph_id: int):
        graph, nodes, all_nodes, edges = await GraphService._load_graph_data(db, graph_id)
        if not graph:
            return None

        # collect all skills including nested graphs
        skill_ids = [n.skill_id for n in all_nodes if n.skill_id]

        user_skill_map, attempts = await GraphService._load_user_data(db, user.id, skill_ids)

        progress_map = GraphService._build_progress_map(attempts)

        evaluator = GraphEvaluator(
            nodes=all_nodes,
            edges=edges,
            user_skill_status=user_skill_map
        )

        # sync DB with computed availability
        await GraphService._sync_user_skills(db, user.id, nodes, evaluator, user_skill_map)

        result_nodes = GraphService._build_nodes_response(nodes, evaluator, progress_map)

        return {
            "graph": graph,
            "nodes": result_nodes,
            "edges": edges,
        }

    @staticmethod
    async def _load_graph_data(db, graph_id: int):
        graph = await db.scalar(select(Graph).where(Graph.id == graph_id))
        if not graph:
            return None, None, None, None

        # root nodes
        nodes = (
            await db.execute(
                select(GraphNode)
                .options(
                    selectinload(GraphNode.skill).selectinload(Skill.resources),
                    selectinload(GraphNode.subgraph),
                )
                .where(GraphNode.graph_id == graph_id)
            )
        ).scalars().all()

        all_nodes = list(nodes)

        visited_graphs = {graph_id}
        to_visit = {n.subgraph_id for n in nodes if n.subgraph_id}

        # load nested subgraphs iteratively
        while to_visit:
            current_ids = to_visit - visited_graphs
            if not current_ids:
                break

            visited_graphs.update(current_ids)

            extra = (
                await db.execute(
                    select(GraphNode)
                    .options(
                        selectinload(GraphNode.skill).selectinload(Skill.resources),
                        selectinload(GraphNode.subgraph),
                    )
                    .where(GraphNode.graph_id.in_(current_ids))
                )
            ).scalars().all()

            all_nodes.extend(extra)

            for n in extra:
                if n.subgraph_id:
                    to_visit.add(n.subgraph_id)

        # edges only for root graph
        edges = (
            await db.execute(
                select(GraphEdge)
                .where(GraphEdge.graph_id == graph_id)
            )
        ).scalars().all()

        return graph, nodes, all_nodes, edges

    @staticmethod
    async def _load_user_data(db, user_id: int, skill_ids):
        # load user skill states
        user_skills = (
            await db.execute(
                select(UserSkill).where(
                    UserSkill.user_id == user_id,
                    UserSkill.skill_id.in_(skill_ids)
                )
            )
        ).scalars().all()

        user_skill_map = {u.skill_id: u.status for u in user_skills}

        # load test attempts
        attempts = (
            await db.execute(
                select(TestAttempt).where(
                    TestAttempt.user_id == user_id,
                    TestAttempt.skill_id.in_(skill_ids)
                )
            )
        ).scalars().all()

        return user_skill_map, attempts

    @staticmethod
    def _build_progress_map(attempts):
        # max score per skill
        progress_map = {}

        for a in attempts:
            score = a.score or 0
            current = progress_map.get(a.skill_id, 0)

            if score > current:
                progress_map[a.skill_id] = score

        return progress_map

    @staticmethod
    async def _sync_user_skills(db, user_id, nodes, evaluator, user_skill_map):
        to_create = []
        to_update = []

        for n in nodes:
            if not n.skill_id:
                continue

            status = evaluator.get_node_status(n.id)
            db_status = user_skill_map.get(n.skill_id)

            # only sync locked -> available
            if status == SkillStatus.available:
                if db_status is None:
                    to_create.append(
                        UserSkill(
                            user_id=user_id,
                            skill_id=n.skill_id,
                            status=SkillStatus.available,
                            unlocked_at=func.now(timezone=True)
                        )
                    )
                elif db_status == SkillStatus.locked:
                    to_update.append(n.skill_id)

        if not to_create and not to_update:
            return

        for obj in to_create:
            db.add(obj)

        for skill_id in to_update:
            await db.execute(
                UserSkill.__table__.update()
                .where(
                    UserSkill.user_id == user_id,
                    UserSkill.skill_id == skill_id
                )
                .values(
                    status=SkillStatus.available,
                    unlocked_at=func.now(timezone=True)
                )
            )

        await db.commit()

    @staticmethod
    def _build_nodes_response(nodes, evaluator, progress_map):
        result = []

        for n in nodes:
            status = evaluator.get_node_status(n.id)

            result.append({
                "id": n.id,
                "node_type": n.node_type,
                "position_x": n.position_x,
                "position_y": n.position_y,
                "skill_id": n.skill_id,
                "subgraph_id": n.subgraph_id,
                "skill": n.skill,
                "subgraph": n.subgraph,
                "status": status.value,
                "progress": progress_map.get(n.skill_id, 0) if n.skill_id else 0,
            })

        return result

    @staticmethod
    async def init_user_skills(db, user_id: int):
        nodes = (await db.execute(select(GraphNode))).scalars().all()
        edges = (await db.execute(select(GraphEdge))).scalars().all()

        existing = (
            await db.execute(
                select(UserSkill.skill_id)
                .where(UserSkill.user_id == user_id)
            )
        ).scalars().all()

        existing = set(existing)

        # nodes that have prerequisites
        has_prereq = set()
        for e in edges:
            if e.relation_type == "prerequisite":
                has_prereq.add(e.to_node_id)

        # graphs available without prerequisites
        open_graphs = set()

        for n in nodes:
            if n.subgraph_id and n.id not in has_prereq:
                open_graphs.add(n.subgraph_id)

        for n in nodes:
            if n.id not in has_prereq:
                open_graphs.add(n.graph_id)

        for n in nodes:
            if not n.skill_id:
                continue

            if n.skill_id in existing:
                continue

            if n.id in has_prereq:
                continue

            if n.graph_id not in open_graphs:
                continue

            db.add(UserSkill(
                user_id=user_id,
                skill_id=n.skill_id,
                status=SkillStatus.available,
                unlocked_at=func.now(timezone=True)
            ))

        await db.commit()