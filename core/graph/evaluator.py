from collections import defaultdict, deque
from models import SkillStatus


class GraphEvaluator:
    def __init__(self, nodes, edges, user_skill_status: dict):
        self.nodes = {n.id: n for n in nodes}
        self.user_skill_status = user_skill_status
        self.edges = edges

        # graph_id -> nodes
        self.nodes_by_graph = defaultdict(list)
        for n in nodes:
            self.nodes_by_graph[n.graph_id].append(n)

        # node_id -> prerequisite groups
        self.prereq_groups = self._build_prerequisite_groups(edges)

    def get_node_status(self, node_id: int) -> SkillStatus:
        node = self.nodes[node_id]

        if node.node_type == "skill":
            return self._eval_skill(node)

        return self._eval_subgraph(node)

    def _eval_skill(self, node) -> SkillStatus:
        # DB state is source of truth
        status = self.user_skill_status.get(node.skill_id)

        if status in (SkillStatus.completed, SkillStatus.mastered):
            return status

        if status == SkillStatus.available:
            return SkillStatus.available

        # fallback to graph rules
        if self._check_groups_satisfied(node.id):
            return SkillStatus.available

        return SkillStatus.locked

    def _eval_subgraph(self, node) -> SkillStatus:
        # check own prerequisites
        if not self._check_groups_satisfied(node.id):
            return SkillStatus.locked

        # subgraph must be opened by at least one entry node
        if not self._is_subgraph_open(node.subgraph_id):
            return SkillStatus.locked

        children = self.nodes_by_graph.get(node.subgraph_id, [])

        # empty graph is considered completed
        if not children:
            return SkillStatus.mastered

        statuses = [self.get_node_status(c.id) for c in children]

        return self._aggregate(statuses)

    def _is_subgraph_open(self, graph_id: int) -> bool:
        # OR logic: any entry node can unlock subgraph
        for n in self.nodes.values():
            if n.subgraph_id == graph_id:
                if self._check_groups_satisfied(n.id):
                    return True
        return False

    def _build_prerequisite_groups(self, edges):
        # build alternative connectivity graph
        alt_graph = defaultdict(set)

        for e in edges:
            if e.relation_type == "alternative":
                alt_graph[e.from_node_id].add(e.to_node_id)
                alt_graph[e.to_node_id].add(e.from_node_id)

        # find connected components (OR groups)
        visited = set()
        components = []

        for node in alt_graph:
            if node in visited:
                continue

            comp = set()
            queue = deque([node])

            while queue:
                cur = queue.popleft()
                if cur in visited:
                    continue

                visited.add(cur)
                comp.add(cur)

                for nei in alt_graph[cur]:
                    if nei not in visited:
                        queue.append(nei)

            components.append(comp)

        # map node -> component
        comp_map = {}
        for comp in components:
            for n in comp:
                comp_map[n] = comp

        # build prerequisite groups per node
        prereq_map = defaultdict(list)

        for e in edges:
            if e.relation_type != "prerequisite":
                continue

            src = e.from_node_id
            dst = e.to_node_id

            group = comp_map.get(src, {src})
            prereq_map[dst].append(group)

        # deduplicate groups
        result = {}

        for dst, groups in prereq_map.items():
            unique = []
            seen = set()

            for g in groups:
                key = tuple(sorted(g))
                if key in seen:
                    continue
                seen.add(key)
                unique.append(list(g))

            result[dst] = unique

        return result

    def _check_groups_satisfied(self, node_id: int) -> bool:
        # AND of OR-groups
        groups = self.prereq_groups.get(node_id, [])

        for group in groups:
            ok = False

            for n in group:
                status = self.get_node_status(n)

                if status in (SkillStatus.completed, SkillStatus.mastered):
                    ok = True
                    break

            if not ok:
                return False

        return True

    def _aggregate(self, statuses):
        total = len(statuses)

        # empty subgraph is completed
        if total == 0:
            return SkillStatus.mastered

        mastered = sum(s == SkillStatus.mastered for s in statuses)
        completed = sum(
            s in (SkillStatus.completed, SkillStatus.mastered)
            for s in statuses
        )

        if mastered == total:
            return SkillStatus.mastered

        if completed / total >= 0.7:
            return SkillStatus.completed

        return SkillStatus.available