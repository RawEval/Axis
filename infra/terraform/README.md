# Terraform — AWS multi-region (Phase 2+)

Placeholder. Migration target once Phase 1 validates product-market fit.

Planned stack:
- ECS Fargate (per service)
- RDS Postgres (ap-south-1 primary, eu-west-1 replica for EU users)
- ElastiCache Redis
- Managed Qdrant Cloud or self-hosted on EKS
- Neo4j Aura Enterprise
- R2 for snapshots (not AWS — keep egress free)
- CloudFront + Route53
