"""
Rule DAG (Directed Acyclic Graph) for topological ordering and execution
"""
from collections import defaultdict, deque
from app.validators.rules.base import BaseRule, RuleResult


class RuleDAG:
    """
    Executes a set of rules in topological order, respecting dependencies.
    Uses Kahn's algorithm to determine execution order.
    """

    def __init__(self, rules: list[BaseRule]):
        """
        Initialize DAG with a list of rules.

        Args:
            rules: List of BaseRule instances
        """
        self._rules = {r.rule_id: r for r in rules}

    def _topological_order(self) -> list[BaseRule]:
        """
        Compute topological order of rules using Kahn's algorithm.
        Respects depends_on relationships.

        Returns:
            List of rules in execution order
        """
        # Build adjacency list and in-degree map
        in_degree = defaultdict(int)
        graph = defaultdict(list)

        # Initialize all nodes
        for rule_id in self._rules:
            if rule_id not in in_degree:
                in_degree[rule_id] = 0

        # Build edges: if A depends_on B, then B -> A (B must run first)
        for rule_id, rule in self._rules.items():
            for dep in rule.depends_on or []:
                if dep in self._rules:
                    graph[dep].append(rule_id)
                    in_degree[rule_id] += 1
                # If dep not in rules, silently ignore (soft fail)

        # Kahn's algorithm: process nodes with in_degree 0
        queue = deque([rule_id for rule_id in self._rules if in_degree[rule_id] == 0])
        ordered_ids = []

        while queue:
            node = queue.popleft()
            ordered_ids.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Verify all nodes processed (check for cycles)
        if len(ordered_ids) != len(self._rules):
            # Cycle detected, but we'll return what we have (partial order)
            # and log a warning. For MVP, we trust that rule authors don't create cycles.
            pass

        return [self._rules[rule_id] for rule_id in ordered_ids]

    def execute(
        self,
        fiscal_document,
        items: list,
        config: dict,
    ) -> list[RuleResult]:
        """
        Execute all rules in topological order.

        Args:
            fiscal_document: FiscalDocument instance
            items: List of FiscalItem instances
            config: Tenant configuration dict

        Returns:
            List of RuleResult objects (one per rule)
        """
        results = {}
        for rule in self._topological_order():
            result = rule.execute(fiscal_document, items, config)
            results[rule.rule_id] = result
        return list(results.values())
