# Railway — Phase 1 hosting

Axis ships Phase 1 on Railway for speed of iteration. Each service deploys from
its own Dockerfile. Attach Postgres, Redis via Railway plugins. Qdrant and Neo4j
run as custom services (Docker images).

Migrate to AWS multi-region for Phase 2+ scale.
