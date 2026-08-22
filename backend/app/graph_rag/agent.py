"""LangGraph multi-hop retrieval agent.

Flow:  retrieve  ->  link_entities  ->  traverse_graph  ->  (decide) -> ...
                          ^-----------------------------------------|

Each iteration performs vector retrieval, links matched child chunks to their
graph entities, and expands an N-hop subgraph. The `decide` edge loops for up to
`max_iterations`, re-seeding the next vector search with entities newly
discovered in the graph. That gives genuine multi-hop behaviour: hop 1 finds
entities from the query, hop 2 pulls in passages about their graph neighbours.

The graph assembles grounded context, citations and a subgraph; token-by-token
generation is streamed separately by the chat router from the context this
produces.
"""
from __future__ import annotations

from typing import Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from ..config import settings
from ..models.schemas import ParentCitation, RetrievalResult, SubgraphResponse, Triple
from ..stores.graph_store import get_graph_store
from .retrieval import build_citations, build_context, expand_to_parents, vector_search


class GraphState(TypedDict, total=False):
    base_query: str
    search_query: str
    top_k: int
    hops: int
    max_iterations: int
    iteration: int
    seen_child_ids: List[str]
    all_hits: List[dict]
    seed_entities: List[str]
    subgraph: SubgraphResponse


def _retrieve(state: GraphState) -> GraphState:
    hits = vector_search(state["search_query"], state["top_k"])
    seen = set(state.get("seen_child_ids", []))
    fresh = [h for h in hits if h.get("child_id") not in seen]
    for h in fresh:
        seen.add(h.get("child_id"))
    return {
        "all_hits": state.get("all_hits", []) + fresh,
        "seen_child_ids": list(seen),
    }


def _link_entities(state: GraphState) -> GraphState:
    gstore = get_graph_store()
    child_ids = [h.get("child_id") for h in state.get("all_hits", []) if h.get("child_id")]
    entities = gstore.entities_for_children(child_ids)
    merged = list(dict.fromkeys(state.get("seed_entities", []) + entities))
    return {"seed_entities": merged}


def _traverse_graph(state: GraphState) -> GraphState:
    gstore = get_graph_store()
    sub = gstore.expand_subgraph(state.get("seed_entities", []), state["hops"])
    return {"subgraph": sub}


def _decide(state: GraphState) -> str:
    """Loop for another hop, or finish."""
    iteration = state.get("iteration", 0) + 1
    if iteration >= state.get("max_iterations", 1):
        return "finish"
    # Only worth another hop if the graph gave us neighbours to explore.
    if not state.get("subgraph") or not state["subgraph"].nodes:
        return "finish"
    return "continue"


def _next_hop(state: GraphState) -> GraphState:
    """Re-seed the next vector search with discovered graph entities."""
    iteration = state.get("iteration", 0) + 1
    node_labels = [n.label for n in state["subgraph"].nodes][:5]
    search_query = ", ".join(node_labels) if node_labels else state["base_query"]
    return {"iteration": iteration, "search_query": search_query}


def build_agent():
    g = StateGraph(GraphState)
    g.add_node("retrieve", _retrieve)
    g.add_node("link_entities", _link_entities)
    g.add_node("traverse_graph", _traverse_graph)
    g.add_node("next_hop", _next_hop)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "link_entities")
    g.add_edge("link_entities", "traverse_graph")
    g.add_conditional_edges(
        "traverse_graph",
        _decide,
        {"continue": "next_hop", "finish": END},
    )
    g.add_edge("next_hop", "retrieve")
    return g.compile()


_AGENT = None


def _get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = build_agent()
    return _AGENT


def run_retrieval(query: str, top_k: int | None = None, max_hops: int | None = None) -> RetrievalResult:
    """Run the multi-hop retrieval graph and assemble grounded context."""
    top_k = top_k or settings.top_k
    hops = max_hops or settings.max_hops

    initial: GraphState = {
        "base_query": query,
        "search_query": query,
        "top_k": top_k,
        "hops": hops,
        "max_iterations": settings.max_iterations,
        "iteration": 0,
        "seen_child_ids": [],
        "all_hits": [],
        "seed_entities": [],
        "subgraph": SubgraphResponse(),
    }

    # recursion_limit guards the loop; each hop adds a few super-steps.
    final: GraphState = _get_agent().invoke(initial, {"recursion_limit": 25})

    parent_ids, best_score, matched = expand_to_parents(final.get("all_hits", []))
    parent_ids = parent_ids[: max(top_k, 6)]
    citations: List[ParentCitation] = build_citations(parent_ids, best_score, matched)

    subgraph: SubgraphResponse = final.get("subgraph", SubgraphResponse())
    triples: List[Triple] = get_graph_store().triples_from_subgraph(subgraph)
    context = build_context(citations, triples)

    return RetrievalResult(
        context=context,
        parents=citations,
        triples=triples,
        subgraph=subgraph,
        seed_entities=final.get("seed_entities", []),
    )
