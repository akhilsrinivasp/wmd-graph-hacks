"""FalkorDB connection helper."""
import os
from functools import lru_cache

from falkordb import FalkorDB

GRAPH_NAME = os.getenv("COMPOUNDER_GRAPH", "compounder")


@lru_cache(maxsize=1)
def _client() -> FalkorDB:
    url = os.getenv("FALKORDB_URL")  # e.g. redis://user:pass@host:port for FalkorDB Cloud
    if url:
        return FalkorDB.from_url(url)
    return FalkorDB(
        host=os.getenv("FALKORDB_HOST", "localhost"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        username=os.getenv("FALKORDB_USERNAME") or None,
        password=os.getenv("FALKORDB_PASSWORD") or None,
    )


def graph():
    return _client().select_graph(GRAPH_NAME)


def run(query: str, params: dict | None = None) -> list[dict]:
    """Run a Cypher query and return rows as dicts keyed by column name."""
    res = graph().query(query, params or {})
    cols = [h[1] if isinstance(h, (list, tuple)) else h for h in res.header]
    cols = [c.decode() if isinstance(c, bytes) else c for c in cols]
    return [dict(zip(cols, row)) for row in res.result_set]
