"""Neo4j graph store: source of truth for chunk text, entities, typed
relationships, and provenance.

Schema
------
(:Document {id, title, source})
(:ParentChunk {id, doc_id, index, text})
(:ChildChunk  {id, doc_id, parent_id, index, text})
(:Entity {name, type})

(:ParentChunk)-[:PART_OF]->(:Document)
(:ChildChunk)-[:CHILD_OF]->(:ParentChunk)
(:Entity)-[:MENTIONED_IN]->(:ChildChunk)                  # provenance to child
(:Entity)-[<TYPE> {source_child_id, source_parent_id}]->(:Entity)  # typed edge

Typed edges use real Neo4j relationship types (ACQUIRED, FOUNDED, ...) created
dynamically via APOC, so the graph is queryable with idiomatic Cypher.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

from neo4j import GraphDatabase

from ..config import settings
from ..models.schemas import GraphEdge, GraphNode, SubgraphResponse, Triple


class GraphStore:
    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #
    def ensure_constraints(self) -> None:
        stmts = [
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT parent_id IF NOT EXISTS FOR (p:ParentChunk) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT child_id IF NOT EXISTS FOR (c:ChildChunk) REQUIRE c.id IS UNIQUE",
        ]
        with self._driver.session() as session:
            for stmt in stmts:
                session.run(stmt)

    # ------------------------------------------------------------------ #
    # Writes (ingestion)
    # ------------------------------------------------------------------ #
    def write_hierarchy(
        self,
        doc_id: str,
        title: str,
        source: Optional[str],
        parents: List[dict],
        children: List[dict],
    ) -> None:
        """Persist Document, ParentChunk and ChildChunk nodes + structure edges."""
        with self._driver.session() as session:
            session.run(
                "MERGE (d:Document {id: $id}) SET d.title = $title, d.source = $source",
                id=doc_id, title=title, source=source,
            )
            session.run(
                """
                UNWIND $parents AS p
                MERGE (pc:ParentChunk {id: p.id})
                SET pc.doc_id = $doc_id, pc.index = p.index, pc.text = p.text
                WITH pc
                MATCH (d:Document {id: $doc_id})
                MERGE (pc)-[:PART_OF]->(d)
                """,
                parents=parents, doc_id=doc_id,
            )
            session.run(
                """
                UNWIND $children AS c
                MERGE (cc:ChildChunk {id: c.id})
                SET cc.doc_id = $doc_id, cc.parent_id = c.parent_id,
                    cc.index = c.index, cc.text = c.text
                WITH cc, c
                MATCH (pc:ParentChunk {id: c.parent_id})
                MERGE (cc)-[:CHILD_OF]->(pc)
                """,
                children=children, doc_id=doc_id,
            )

    def write_entities(self, entities: List[dict]) -> None:
        if not entities:
            return
        with self._driver.session() as session:
            session.run(
                """
                UNWIND $entities AS e
                MERGE (n:Entity {name: e.name})
                SET n.type = coalesce(e.type, n.type, 'Unknown')
                """,
                entities=entities,
            )

    def write_mentions(self, mentions: List[dict]) -> None:
        """mentions: [{entity, child_id}] -> provenance edges to child chunks."""
        if not mentions:
            return
        with self._driver.session() as session:
            session.run(
                """
                UNWIND $mentions AS m
                MATCH (e:Entity {name: m.entity})
                MATCH (c:ChildChunk {id: m.child_id})
                MERGE (e)-[:MENTIONED_IN]->(c)
                """,
                mentions=mentions,
            )

    def write_relationships(self, rels: List[dict]) -> None:
        """rels: [{source, target, type, source_child_id, source_parent_id}]."""
        if not rels:
            return
        with self._driver.session() as session:
            session.run(
                """
                UNWIND $rels AS rel
                MATCH (a:Entity {name: rel.source})
                MATCH (b:Entity {name: rel.target})
                CALL apoc.merge.relationship(
                    a, rel.type, {},
                    {source_child_id: rel.source_child_id, source_parent_id: rel.source_parent_id},
                    b
                ) YIELD rel AS r
                RETURN count(r)
                """,
                rels=rels,
            )

    # ------------------------------------------------------------------ #
    # Reads (retrieval)
    # ------------------------------------------------------------------ #
    def get_parents(self, parent_ids: List[str]) -> Dict[str, dict]:
        if not parent_ids:
            return {}
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (pc:ParentChunk)-[:PART_OF]->(d:Document)
                WHERE pc.id IN $ids
                RETURN pc.id AS parent_id, pc.doc_id AS doc_id, pc.text AS text, d.title AS title
                """,
                ids=parent_ids,
            )
            return {r["parent_id"]: dict(r) for r in result}

    def entities_for_children(self, child_ids: List[str]) -> List[str]:
        if not child_ids:
            return []
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)-[:MENTIONED_IN]->(c:ChildChunk)
                WHERE c.id IN $ids
                RETURN DISTINCT e.name AS name
                """,
                ids=child_ids,
            )
            return [r["name"] for r in result]

    def expand_subgraph(self, entity_names: List[str], hops: int) -> SubgraphResponse:
        """N-hop traversal over Entity-Entity typed edges from seed entities."""
        if not entity_names:
            return SubgraphResponse()
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity) WHERE e.name IN $names
                WITH collect(e) AS starts
                CALL apoc.path.subgraphAll(starts, {maxLevel: $hops, labelFilter: '+Entity'})
                YIELD nodes, relationships
                RETURN
                  [n IN nodes | {id: n.name, label: n.name, type: coalesce(n.type,'Unknown')}] AS nodes,
                  [r IN relationships | {
                      id: toString(id(r)),
                      source: startNode(r).name,
                      target: endNode(r).name,
                      type: type(r),
                      properties: properties(r)
                  }] AS edges
                """,
                names=entity_names, hops=hops,
            )
            record = result.single()
            if not record:
                return SubgraphResponse()
            return self._to_subgraph(record["nodes"], record["edges"])

    def subgraph_by_entity(self, entity: Optional[str], hops: int, limit: int) -> SubgraphResponse:
        """Public graph endpoint: subgraph around a named entity, or a capped
        slice of the whole graph if no entity is given."""
        with self._driver.session() as session:
            if entity:
                result = session.run(
                    """
                    MATCH (e:Entity) WHERE toLower(e.name) CONTAINS toLower($entity)
                    WITH collect(e) AS starts
                    CALL apoc.path.subgraphAll(starts, {maxLevel: $hops, labelFilter: '+Entity'})
                    YIELD nodes, relationships
                    RETURN
                      [n IN nodes | {id: n.name, label: n.name, type: coalesce(n.type,'Unknown')}] AS nodes,
                      [r IN relationships | {
                          id: toString(id(r)), source: startNode(r).name,
                          target: endNode(r).name, type: type(r), properties: properties(r)
                      }] AS edges
                    """,
                    entity=entity, hops=hops,
                )
                record = result.single()
                if not record:
                    return SubgraphResponse()
                return self._to_subgraph(record["nodes"], record["edges"])

            # Whole-graph slice (capped).
            result = session.run(
                """
                MATCH (a:Entity)-[r]->(b:Entity)
                RETURN a.name AS s, a.type AS st, b.name AS t, b.type AS tt,
                       type(r) AS rtype, toString(id(r)) AS rid, properties(r) AS props
                LIMIT $limit
                """,
                limit=limit,
            )
            nodes: Dict[str, dict] = {}
            edges: List[dict] = []
            for r in result:
                nodes.setdefault(r["s"], {"id": r["s"], "label": r["s"], "type": r["st"] or "Unknown"})
                nodes.setdefault(r["t"], {"id": r["t"], "label": r["t"], "type": r["tt"] or "Unknown"})
                edges.append({
                    "id": r["rid"], "source": r["s"], "target": r["t"],
                    "type": r["rtype"], "properties": dict(r["props"] or {}),
                })
            return self._to_subgraph(list(nodes.values()), edges)

    @staticmethod
    def _to_subgraph(nodes: List[dict], edges: List[dict]) -> SubgraphResponse:
        return SubgraphResponse(
            nodes=[GraphNode(**n) for n in nodes],
            edges=[GraphEdge(**e) for e in edges],
        )

    @staticmethod
    def triples_from_subgraph(sub: SubgraphResponse) -> List[Triple]:
        return [
            Triple(
                source=e.source, type=e.type, target=e.target,
                source_child_id=e.properties.get("source_child_id"),
                source_parent_id=e.properties.get("source_parent_id"),
            )
            for e in sub.edges
        ]

    def stats(self) -> dict:
        with self._driver.session() as session:
            rec = session.run(
                """
                OPTIONAL MATCH (d:Document) WITH count(d) AS docs
                OPTIONAL MATCH (p:ParentChunk) WITH docs, count(p) AS parents
                OPTIONAL MATCH (c:ChildChunk) WITH docs, parents, count(c) AS children
                OPTIONAL MATCH (e:Entity) WITH docs, parents, children, count(e) AS entities
                OPTIONAL MATCH (:Entity)-[r]->(:Entity)
                RETURN docs, parents, children, entities, count(r) AS relationships
                """
            ).single()
            return dict(rec) if rec else {}


@lru_cache
def get_graph_store() -> GraphStore:
    return GraphStore()
