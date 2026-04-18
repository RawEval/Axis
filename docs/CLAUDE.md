# CLAUDE.md — docs/

- `axis_full_spec.docx` — **the** canonical spec. v1.0, 2025, RawEval Inc.
- `architecture/` — system diagrams, service interactions, data flow
- `api/` — OpenAPI snapshots
- `runbooks/` — on-call, local dev, incident response, deploy

## Spec-first

Every architectural decision should be justified against a spec section. When the code and the spec disagree, the spec wins — unless the user explicitly says otherwise and we log the deviation here.

## Updating docs

- When you add a new service, write or update its section in `architecture/overview.md`.
- When you add a new cross-service flow, add or update a diagram in `architecture/`.
- When you change the data model, update `architecture/overview.md` AND the SQL init file.
- When you hit a weird production issue, write a runbook in `runbooks/`.

## Don't

- Don't duplicate content between docs and CLAUDE.md files. CLAUDE.md = how Claude Code should work. docs/ = how humans understand the system.
- Don't commit large binary assets here. Put them in R2 and link.
