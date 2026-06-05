# Resolution Ambiguity Taxonomy And Manual-Label Workflow

## 1. Status

- WP: WP55 (resolution ambiguity taxonomy and manual-label workflow on branch)
- Package class: docs-tests-research-taxonomy-manual-label-workflow
- Package size class: L
- Runtime impact: NO_RUNTIME_CHANGE
- Source impact: NO_SRC_CHANGE
- Tooling impact: NO_TOOL_IMPLEMENTATION
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_RUNTIME_NETWORK
- Trading impact: NO_TRADING_EXECUTION
- Hermes impact: NO_HERMES_INSTALL_OR_RUNTIME
- Agent runtime impact: NO_AGENT_RUNTIME
- Docs/schema/tests only: YES
- No parser: YES — no automated resolution-rule parser is added in WP55
- No automated extraction: YES — no automated ambiguity extraction is added in WP55
- No feature extraction: YES — feature extraction from ambiguity labels is deferred
- No scorer integration: YES — scorer integration is deferred to a future approved WP
- No CLI/export/report: YES — no CLI, export, or report writer is added in WP55
- No LLM/provider: YES — no LLM or Hermes provider is used
- No network: YES — all workflow steps are local/offline/read-only
- No credentials: YES — no API keys, wallets, or private keys

## 2. Purpose

This document defines the resolution-rule ambiguity taxonomy and manual-label
workflow for human research data quality in the polymarket-strategy-lab project.

It answers:
- What categories of ambiguity exist in Polymarket resolution rules?
- What status values and severity tiers are allowed for review labels?
- What fields does a future manual label record require?
- How should a human reviewer perform the manual labeling workflow?
- When may future WPs consume ambiguity labels in feature extraction?

This is not a trading system, alpha system, or execution system. All ambiguity
labels are research-data-quality metadata for future human review only.

## 3. Non-Signal Boundary

Resolution-rule ambiguity labels are **research-data-quality metadata only**.

They do not imply and must never be used to imply:

- profitability
- expected return
- entry or exit
- position size
- leverage
- tradability
- execution confidence
- fill probability
- order size or slippage model
- trade recommendation
- paper trade authorization
- live trade authorization

Labels must use only safe research-data-quality framing:

- `resolution_ambiguity_review`
- `manual_review_required`
- `research_data_quality`
- `resolution_clarity`
- `source_hierarchy_clarity`
- `cutoff_clarity`
- `evidence_traceability`
- `human_research_triage_only`
- `ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED`

Any label, field, comment, or annotation that implies a market should be traded,
entered, exited, or sized based on its ambiguity classification is forbidden.

## 4. Taxonomy Categories

The following taxonomy categories define distinct types of resolution-rule
ambiguity that a human reviewer may observe in a local Polymarket market record.

Categories are not mutually exclusive. A single market may receive multiple
category labels when the reviewer observes multiple distinct ambiguity types.

### 4.1 `missing_resolution_source`

The market record contains no identifiable resolution source. No URL, authority,
publication, or reference is named as the source that will determine the outcome.
The reviewer cannot determine who or what will call the resolution.

### 4.2 `unclear_source_hierarchy`

Multiple possible resolution sources exist but no hierarchy or priority order
is stated. It is unclear which source takes precedence if sources disagree.

### 4.3 `cutoff_time_ambiguity`

The resolution cutoff time is vague, unstated, or inconsistent with other
fields. The market may resolve based on data at an unclear point in time.

### 4.4 `timezone_ambiguity`

A cutoff time is stated but the timezone is not specified or is ambiguous.
Different interpretations of the timezone would produce different resolution
outcomes.

### 4.5 `title_rules_mismatch`

The market title and the detailed resolution rules describe different events,
conditions, or thresholds. A reviewer following only the title would reach a
different conclusion than one following the detailed rules.

### 4.6 `entity_definition_ambiguity`

The entity that the market is about is not clearly defined. The entity's
boundaries, scope, legal status, or membership are ambiguous in a way that
affects resolution.

### 4.7 `event_definition_ambiguity`

The event that would trigger resolution is not clearly defined. It is unclear
what specific occurrence or observation constitutes the event.

### 4.8 `measurement_definition_ambiguity`

A numerical threshold, measurement method, or data source for measurement is
not clearly defined. Different measurement approaches would produce different
resolution outcomes.

### 4.9 `outcome_mapping_ambiguity`

The mapping from real-world outcomes to YES/NO (or other token outcomes) is
not clearly defined. Edge cases exist where the mapping is unclear.

### 4.10 `source_conflict`

Two or more sources that could be used for resolution are likely to disagree
on the outcome. The rules do not clearly specify how to handle this conflict.

### 4.11 `finality_or_revision_ambiguity`

It is unclear whether the resolution source will be considered final immediately
or whether a revision, appeal, correction, or recount could change the outcome
after initial publication.

### 4.12 `duplicate_or_overlap_risk`

The market appears to overlap significantly with another market or may represent
a duplicate with slightly different wording. Resolution of one may or may not
imply resolution of the other.

### 4.13 `insufficient_local_evidence`

The local snapshot or export data does not contain enough information to
assess the ambiguity level with confidence. More data would be needed to
form a reliable label.

### 4.14 `other_manual_review_issue`

The ambiguity does not fit any of the above categories but the reviewer
believes the market warrants closer human attention. A free-text note in
`evidence_notes` is required when this category is used.

## 5. Review Status Values

The following status values define the outcome of a human resolution-rule
review. Only these values are allowed in the `review_status` field of a
manual label.

| Status | Meaning |
|---|---|
| `NOT_REVIEWED` | No human review has been performed for this market |
| `REVIEWED_CLEAR` | Reviewed; resolution rules appear clear and unambiguous |
| `REVIEWED_LOW_AMBIGUITY` | Reviewed; minor ambiguity present but unlikely to affect resolution |
| `REVIEWED_MEDIUM_AMBIGUITY` | Reviewed; meaningful ambiguity present; human attention recommended before any downstream use |
| `REVIEWED_HIGH_AMBIGUITY` | Reviewed; significant ambiguity present; strong human caution required |
| `INSUFFICIENT_LOCAL_EVIDENCE` | Reviewed; insufficient local snapshot or export data to form a confident label |

**Forbidden status values:** any status that implies a market is tradeable,
untradeable, attractive, or an opportunity. Review status is about data quality
only.

## 6. Severity And Confidence Separation

### 6.1 Ambiguity Severity

Ambiguity severity describes how serious the observed ambiguity is in the
reviewer's judgment.

| Severity | Meaning |
|---|---|
| `NONE` | No ambiguity observed |
| `LOW` | Minor ambiguity unlikely to affect resolution outcome |
| `MEDIUM` | Meaningful ambiguity that could affect resolution under some conditions |
| `HIGH` | Serious ambiguity likely to affect resolution or create disputes |
| `UNKNOWN` | Severity cannot be assessed from available local evidence |

### 6.2 Reviewer Confidence

Reviewer confidence describes the reviewer's confidence in the accuracy and
completeness of the label they assigned — not confidence in any market outcome.

| Confidence | Meaning |
|---|---|
| `LOW` | The reviewer is not confident the label is accurate; limited local evidence |
| `MEDIUM` | The reviewer has moderate confidence in the label |
| `HIGH` | The reviewer has high confidence the label accurately reflects the local evidence |

**Important separation:** `reviewer_confidence` is confidence in the label
quality, not confidence in any trading outcome, market resolution, or research
priority. A `HIGH` reviewer confidence does not mean the market is well-defined,
well-understood, or suitable for any downstream use.

## 7. Manual Label Schema

A future local/offline manual label record must include all of the following
fields. This schema is a specification only. No implementation is added in WP55.

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | YES | Schema version, e.g. `"1.0"` |
| `label_id` | string | YES | Unique identifier for this label record |
| `market_id` | string | YES | Market identifier from local snapshot |
| `question_snapshot` | string | YES | Snapshot of market question text at review time |
| `resolution_text_snapshot` | string or null | YES | Snapshot of resolution rules text at review time, or null if absent |
| `review_status` | string | YES | One of the allowed status values from Section 5 |
| `ambiguity_categories` | array of strings | YES | Zero or more taxonomy categories from Section 4 |
| `ambiguity_severity` | string | YES | One of the allowed severity values from Section 6.1 |
| `reviewer_confidence` | string | YES | One of the allowed confidence values from Section 6.2 |
| `manual_review_required` | boolean | YES | Must be `true` unless `review_status` is `REVIEWED_CLEAR` |
| `reviewed_at_utc` | string | YES | ISO-8601 UTC timestamp of the review |
| `reviewer_id_or_role` | string | YES | Reviewer identifier or role (e.g. `"human_analyst"`) |
| `source_artifact_refs` | array of strings | YES | Local snapshot or export artifact references used during review |
| `evidence_notes` | string or null | YES | Free-text notes documenting what was observed; required when `other_manual_review_issue` is used |
| `limitations` | string or null | YES | Free-text limitations of this label; e.g. snapshot may be stale |
| `advisory_label` | string | YES | Must be exactly `"ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"` |
| `forbidden_use_notice` | string | YES | Explicit statement that this label is not a trade signal, not expected return, not execution instruction |

### 7.1 Advisory Label Requirement

Every manual label record must carry:

- `advisory_label`: exactly `"ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"`
- `manual_review_required`: `true` unless `review_status` is `REVIEWED_CLEAR`

These fields must not be optional, user-suppressible, or configurable to any
other value.

### 7.2 Forbidden-Use Notice Requirement

Every manual label record must include a `forbidden_use_notice` stating:

> This label is not a trading signal, not expected return, not position sizing,
> not execution confidence, and not an execution instruction. It is research-data-quality
> metadata for human research triage only.

## 8. Source Artifact Requirements

Manual labels must reference local/offline artifacts only. Specifically:

- Labels must reference snapshot files under `local_data/polymarket/snapshots/`
  or catalog exports under `local_data/polymarket/exports/` that the reviewer
  inspected during review.
- Labels must not reference live API data, real-time feeds, or authenticated
  account data.
- Labels must not be generated by an LLM or Hermes provider. Human authorship
  is required.
- Labels must not depend on any external data source not available locally.
- If the referenced snapshot or export is stale, the reviewer must note this in
  `limitations`.
- In WP55, no external data dependency is added. Artifact references are
  placeholders for the schema; the label store implementation is deferred.

## 9. Manual Workflow

The following is the approved human workflow for creating resolution-rule
ambiguity labels. This workflow is manual, local, offline, and read-only.
No automated execution of this workflow is implemented in WP55.

### Step 1: Select Market

Select a market from a local snapshot export or catalog export. Use only
data already available in `local_data/polymarket/`.

### Step 2: Inspect Local Data

Open the local question text and resolution rules fields for the selected
market. Do not fetch live data.

### Step 3: Assign Taxonomy Categories

Review the resolution rules against the taxonomy in Section 4. Assign all
applicable categories. Assign `other_manual_review_issue` if the concern
does not fit existing categories and add a note.

### Step 4: Assign Severity And Reviewer Confidence

Assign `ambiguity_severity` from Section 6.1 based on judgment of how
seriously the ambiguity could affect resolution.

Assign `reviewer_confidence` from Section 6.2 based on how confident you
are in the label, not in the market outcome.

### Step 5: Record Evidence Notes And Limitations

Write brief `evidence_notes` describing what you observed that led to the
ambiguity classification. Note any limitations of the review (e.g. stale
snapshot, incomplete resolution text).

### Step 6: Apply Human-Review Gate

Require human review before any future downstream use of the label. Set
`manual_review_required: true` unless the review status is `REVIEWED_CLEAR`.

### Step 7: Leave Unresolved If Evidence Is Insufficient

If local evidence is insufficient to form a confident label, set:
- `review_status: INSUFFICIENT_LOCAL_EVIDENCE`
- `ambiguity_severity: UNKNOWN`
- `reviewer_confidence: LOW`

Do not attempt to infer resolution rules from sources not in local data.

## 10. Future Integration Gate

A future approved work package may consume manual ambiguity labels as inputs
to feature extraction only after the following conditions are met:

1. The label schema defined in Section 7 is implemented and tested in a
   separate approved WP.
2. The feature extraction WP explicitly references the label schema from WP55
   and is explicitly approved by the user.
3. The feature extraction implementation reads only approved local/offline
   label files.
4. The feature extraction output preserves the `ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED`
   label and the `manual_review_required` flag on all outputs.
5. No feature extraction output is used as a trading signal, expected return,
   or execution instruction.

**No feature extraction is implemented in WP55.**

The only action WP55 takes is to define the taxonomy, review workflow, and
label schema in documentation form so that a future WP has a clear contract
to implement against.

## 11. Invalid Examples

The following examples use forbidden trade-like semantics and must not be
used as ambiguity label wording.

### Invalid Example 1 — Trade-Like Severity Wording

```json
{
  "ambiguity_severity": "AVOID",
  "review_status": "UNTRADEABLE"
}
```

**Why invalid:** `AVOID` implies a trading recommendation. `UNTRADEABLE` implies
tradability assessment. Resolution ambiguity labels must not use trade-like
severity or status wording.

### Invalid Example 2 — Opportunity Language In Notes

```json
{
  "evidence_notes": "Resolution ambiguity creates an opportunity for mispricing exploitation.",
  "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED"
}
```

**Why invalid:** `opportunity for mispricing exploitation` implies a trading
opportunity or alpha signal. Evidence notes must not use opportunity, alpha,
edge, or trade-action language even if the advisory label is present.

### Invalid Example 3 — Forbidden Field

```json
{
  "tradability_score": 0.3,
  "execution_confidence": 0.1,
  "ambiguity_categories": ["cutoff_time_ambiguity"]
}
```

**Why invalid:** `tradability_score` and `execution_confidence` are forbidden
fields in any ambiguity label record. Resolution ambiguity is a data-quality
indicator, not a tradability or execution metric.

### Invalid Example 4 — LLM-Generated Label

```json
{
  "reviewer_id_or_role": "gpt-4o",
  "evidence_notes": "LLM assessed the resolution rules as ambiguous."
}
```

**Why invalid:** Labels must be human-authored. LLM-generated labels are
forbidden because they lack the human accountability required for research
data quality review.

## 12. Valid Examples

The following examples demonstrate safe, compliant ambiguity label wording.

### Valid Example 1 — Clear Market

```json
{
  "schema_version": "1.0",
  "label_id": "label-20260604-001",
  "market_id": "0xabc123",
  "question_snapshot": "Will candidate X win the 2026 election?",
  "resolution_text_snapshot": "Resolves YES if the Associated Press calls the race for candidate X by 2026-11-30T23:59:00Z.",
  "review_status": "REVIEWED_CLEAR",
  "ambiguity_categories": [],
  "ambiguity_severity": "NONE",
  "reviewer_confidence": "HIGH",
  "manual_review_required": false,
  "reviewed_at_utc": "2026-06-04T10:00:00Z",
  "reviewer_id_or_role": "human_analyst",
  "source_artifact_refs": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
  "evidence_notes": "Resolution source (AP), event (election call), and cutoff (2026-11-30T23:59:00Z) are all clearly stated.",
  "limitations": null,
  "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
  "forbidden_use_notice": "This label is not a trading signal, not expected return, not position sizing, not execution confidence, and not an execution instruction. It is research-data-quality metadata for human research triage only."
}
```

### Valid Example 2 — Medium Ambiguity

```json
{
  "schema_version": "1.0",
  "label_id": "label-20260604-002",
  "market_id": "0xdef456",
  "question_snapshot": "Will inflation fall below 3% by end of year?",
  "resolution_text_snapshot": "Resolves YES if CPI inflation falls below 3% as reported by official statistics.",
  "review_status": "REVIEWED_MEDIUM_AMBIGUITY",
  "ambiguity_categories": ["measurement_definition_ambiguity", "unclear_source_hierarchy"],
  "ambiguity_severity": "MEDIUM",
  "reviewer_confidence": "MEDIUM",
  "manual_review_required": true,
  "reviewed_at_utc": "2026-06-04T10:05:00Z",
  "reviewer_id_or_role": "human_analyst",
  "source_artifact_refs": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
  "evidence_notes": "Multiple CPI measures exist (headline, core, PCE). Resolution rules say 'CPI inflation' but do not specify which CPI measure or country. 'Official statistics' does not name a specific agency.",
  "limitations": "Snapshot may not contain the full resolution source text.",
  "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
  "forbidden_use_notice": "This label is not a trading signal, not expected return, not position sizing, not execution confidence, and not an execution instruction. It is research-data-quality metadata for human research triage only."
}
```

### Valid Example 3 — Insufficient Evidence

```json
{
  "schema_version": "1.0",
  "label_id": "label-20260604-003",
  "market_id": "0xghi789",
  "question_snapshot": "Will the event occur?",
  "resolution_text_snapshot": null,
  "review_status": "INSUFFICIENT_LOCAL_EVIDENCE",
  "ambiguity_categories": ["missing_resolution_source", "insufficient_local_evidence"],
  "ambiguity_severity": "UNKNOWN",
  "reviewer_confidence": "LOW",
  "manual_review_required": true,
  "reviewed_at_utc": "2026-06-04T10:10:00Z",
  "reviewer_id_or_role": "human_analyst",
  "source_artifact_refs": ["local_data/polymarket/snapshots/manifest-20260603-001.jsonl"],
  "evidence_notes": "Local snapshot contains no resolution text and no resolution source URL. Cannot assess ambiguity without more data.",
  "limitations": "Resolution text absent from local snapshot. Label is provisional.",
  "advisory_label": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
  "forbidden_use_notice": "This label is not a trading signal, not expected return, not position sizing, not execution confidence, and not an execution instruction. It is research-data-quality metadata for human research triage only."
}
```

## 13. Deferred Items

The following items are intentionally deferred from WP55 and must not be
implemented until explicitly approved in a future work package.

### WP55-D001 — Resolution Ambiguity Labels Not Yet Consumed By Feature Extraction

Ambiguity labels defined in this document are not consumed by any feature
extraction, scorer, advisory consumer, or reporting component in WP55.

A future approved WP may implement feature extraction from local/offline
ambiguity label files only after the integration gate conditions in Section 10
are satisfied and the user explicitly approves.

### WP55-D002 — Automated Resolution-Rule Parser Remains Not Started

No automated parser for resolution rules is added in WP55. Extracting
ambiguity categories from resolution rule text automatically requires:
- A separate parser design and approval WP
- Human review of parser outputs before any downstream use
- Non-LLM parser design that does not depend on provider runtime

This item subsumes WP51-D002 and WP53-D001 for the automated parser scope.
The taxonomy and manual-label workflow address the human-review portion of
those deferred items. The automated parser portion remains not started.

### Remaining Open Deferred Items (Unchanged By WP55)

- WP49-D002: CLI/export/report writer not started
- WP49-D003: Core scorer not integrated with advisory consumer or market catalog
- WP50-D001: Implementation sequencing still requires explicit future WPs
- WP51-D003 / WP53-D002: Microstructure quality feature extraction not started
- WP51-D004: CLI/export/report writer not started
- WP52-D001: Roadmap milestone implementation gated by future WPs
- WP54-D001: GitHub-posted evidence still requires manual verification

## 14. Protected-Boundary Reaffirmation

WP55 reaffirms all existing protected boundaries unchanged:

- Live trading: DISABLED — no change
- Execution: NOT_STARTED — no change
- Credentials: NOT_USED — no change
- Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY — no change
- Agent runtime: NOT_STARTED — no change
- Agent execution authority: FORBIDDEN — no change
- Scheduler: NOT_STARTED — no change
- Bot loop: NOT_STARTED — no change
- Authenticated client: FORBIDDEN_UNTIL_APPROVED_WP — no change
- Strategy modules: no module started, no module authorized — no change
- Paper trading: NOT_STARTED — no change
- Database: NOT_STARTED — no change
- Dashboard: NOT_STARTED — no change
- LLM/provider runtime: NO_LLM_PROVIDER_RUNTIME — no change
