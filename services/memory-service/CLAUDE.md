# CLAUDE.md — services/memory-service

Three-tier memory per user. Spec §6.4.

## Tiers

| Tier | Store | What it is |
|---|---|---|
| **Episodic** | Redis (hot) + Qdrant (cold) | Specific past interactions (agent actions, corrections, surfaces) |
| **Semantic** | Neo4j | Entities — people, projects, preferences, relationships |
| **Procedural** | Postgres `users.settings` | How the user likes things done (trust level, output format, brief time) |

## Retrieval

Hybrid scoring:
- Vector similarity (Qdrant) for episodic content
- Graph traversal (Neo4j) for semantic connections
- Recency weighting (decay over 90 days)
- Relationship weighting (how central is the entity to the user's world)

## Decay

Episodic memories older than 90 days are compressed into semantic summaries unless explicitly pinned by the user. Compression runs as a nightly Celery job.

## Layout

```
app/
├── main.py
├── config.py
├── graph/
│   ├── client.py       Neo4j driver
│   └── queries.py      Cypher queries for entity extraction and traversal
├── vector/
│   ├── client.py       Qdrant client
│   └── embed.py        Voyage or Anthropic embeddings
├── tiers/
│   ├── episodic.py
│   ├── semantic.py
│   └── procedural.py
└── routes/
    ├── health.py
    ├── retrieve.py     POST /retrieve (tier?, query, limit)
    └── write.py        POST /episodic, PUT /semantic, PATCH /procedural
```

## Don't

- Don't cross user namespaces. Each user has their own Qdrant collection and Neo4j label prefix.
- Don't store tokens or credentials in memory. That's connector-manager's job.
- Don't use the same embedding model across updates — keep it configurable.
