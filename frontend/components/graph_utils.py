"""Graph visualization utilities.

Transforms GraphitiService search results (list of relationship dicts)
into nodes + edges for st-link-analysis (Cytoscape.js-based).
"""

from typing import Any


def relationships_to_graph(relationships: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert GraphitiService search results to st-link-analysis format.

    Input shape (from /api/graph/search):
        [{"source": "Entity A", "relationship": "connects to", "target": "Entity B"}, ...]

    Output shape (for st_link_analysis):
        {
            "nodes": [{"id": "entity-a", "label": "Entity A", "type": "entity"}, ...],
            "edges": [{"id": "e0", "source": "entity-a", "target": "entity-b", "label": "connects to"}, ...]
        }
    """
    nodes_map = {}  # label -> node dict
    edges = []

    for i, rel in enumerate(relationships):
        src = rel.get("source", "?")
        tgt = rel.get("target", "?")
        relationship = rel.get("relationship", "related")

        # Create nodes (deduplicate by label)
        src_id = _node_id(src)
        tgt_id = _node_id(tgt)

        if src_id not in nodes_map:
            nodes_map[src_id] = {"id": src_id, "label": src, "type": "entity"}
        if tgt_id not in nodes_map:
            nodes_map[tgt_id] = {"id": tgt_id, "label": tgt, "type": "entity"}

        edges.append({
            "id": f"e{i}",
            "source": src_id,
            "target": tgt_id,
            "label": relationship,
        })

    return {
        "nodes": list(nodes_map.values()),
        "edges": edges,
    }


def episodes_to_graph(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert episode list to graph format.

    Input shape (from /api/graph/episodes):
        [{"id": "uuid", "content": "...", "source": "...", "created_at": "..."}, ...]

    Output: nodes only (episodes don't have explicit edges between them).
    """
    nodes = []
    for ep in episodes:
        ep_id = ep.get("id", f"ep-{len(nodes)}")
        label = ep.get("content", "")[:50] + ("..." if len(ep.get("content", "")) > 50 else "")
        source = ep.get("source", "unknown")
        nodes.append({
            "id": ep_id,
            "label": label,
            "type": "episode",
            "source": source,
            "created_at": ep.get("created_at"),
        })
    return {"nodes": nodes, "edges": []}


def _node_id(label: str) -> str:
    """Generate a stable node ID from a label."""
    return label.lower().replace(" ", "-").replace("/", "-")[:50]
