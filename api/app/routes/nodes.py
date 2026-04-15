"""Graph-query endpoints for the Explore UI."""

from fastapi import APIRouter, HTTPException, Query

from app.db import fetch_node, fetch_neighbors

router = APIRouter(tags=["query"])


# Register /neighbors before the bare /nodes/{id} so the more specific
# path matches first (node ids contain colons but not slashes).


@router.get("/nodes/{node_id}/neighbors")
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(1, ge=1, le=1),
    edge_types: list[str] | None = Query(None),
):
    """Fetch a node plus its one-hop inbound and outbound neighbors."""
    subgraph = await fetch_neighbors(node_id, edge_types=edge_types)
    if subgraph is None:
        raise HTTPException(status_code=404, detail="Not found")
    return subgraph


@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """Fetch one node by its stable id."""
    node = await fetch_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Not found")
    return node
