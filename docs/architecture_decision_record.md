# Architecture Decision Record

This file records planning-level architecture decisions that are repo truth only
after the approving work package merges. It does not grant implementation
authority beyond the active work package scope.

## WP61 Direction Lock-In - User-Approved Execution Path

Status: WP61_MERGED (PR #62; merge commit fa84711471fcd81a9f6a447584d0e5dd92e4f4c4)

Scope: planning constraints and research-data metadata only. There is no database, dashboard, runtime, deployment, scheduler, or execution implementation in WP61.

### Database Direction

Decision: SQLite first for local research snapshots, paper-trading state,
positions, orders, PnL, local reports, and early bot state.

Postgres deferred until multi-process, hosted runtime, larger data volume, team
access, or production reliability needs justify it.

Implementation constraints:
- No database implementation in WP61.
- Future schemas should be written in a migration-friendly way where practical.
- No Postgres dependency may be added until explicitly approved.

### Dashboard Direction

Decision: Streamlit first for fast internal operator/research dashboard.
Grafana later for runtime metrics and operations monitoring. Next.js only if productizing
or if a polished user-facing dashboard becomes necessary.

Implementation constraints:
- No dashboard implementation in WP61.
- The Streamlit choice does not imply immediate dependency addition.

### Runtime Direction

Decision: local development first. Cheap VPS later for a controlled live pilot.
Avoid serverless for live runtime because durable state and predictable process
behavior matter.

Implementation constraints:
- No VPS, deployment, scheduler, bot loop, or hosted-runtime implementation in
  WP61.

### Strategy Direction

Decision: rules-based + research-score-driven strategy first.

LLM may be used only as read-only analyst/proposal layer. There is no autonomous LLM execution authority.

Implementation constraints:
- Human review remains required.
- Advisory-only semantics remain binding.
- Live execution remains forbidden unless a future explicit authorization updates
  repo truth.

### Execution Ladder

Decision: lock this phased ladder:

```text
research-only -> paper -> dry-run -> manual live approval -> restricted live
research-only → paper → dry-run → manual live approval → restricted live
```

Skipping phases requires explicit future approval. Live trading authorization is
still absent. Credentials remain forbidden until an approved future work package.

### Remaining Research Before Live

These are future research or investigation topics only. They are candidates for
Agent Mode / deep research before any execution or live phase:

- Polymarket API/CLOB execution architecture.
- Legal, terms, jurisdiction, and access review.
- Prediction-market strategy realism.
- Paper trading realism requirements.
- Hosting and runtime architecture.

WP61 implements none of these topics.
