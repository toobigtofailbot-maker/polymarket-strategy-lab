# Hermes Candidate-Review Assisted Research Current Provider/Model, Privacy, Retention, Cost, And Endpoint Research With Candidate Shortlist

## Purpose

This WP147 record performs a bounded, current, public, first-party-documentation
review of remote model configurations that could be considered in a later
controlled Hermes-assisted experiment. It records evidence and a fail-closed
eligibility decision. It does not force a shortlist, choose a production provider, create an account or
credential, install or invoke Hermes, call a model, activate an endpoint, spend
money, persist model data, or change any trading or runtime surface.

WP147 research status:
COMPLETE

Candidate pool posture:
CURRENT_AUTHORITATIVE_FIRST_PARTY_RESEARCH_ONLY

Provider decision:
NO_PROVIDER_SELECTED_EVIDENCE_INSUFFICIENT

## Position After WP146

Merged WP146 accepted the corrected WP145 local one-case harness only as
bounded test-control evidence, closed that local phase, and left remote
readiness blocked by missing current provider/model, privacy, retention, cost,
endpoint, credential, sandbox, and evidence decisions. WP147 supplies the
current research and a fail-closed no-shortlist decision. It supplies none of the remote
implementation or operator approvals that WP146 said were still missing.

## Authority And Non-Authority

Authority is limited to public research, this documentation record, its
Markdown-only regression, stable status, and exact repo-truth reconciliation.
The Centralized Boundary Group Reference in `docs/ai/codex/PROTECTED_PATHS.md`
remains binding.

Provider/model activation: NOT AUTHORIZED

Provider/model call: NOT AUTHORIZED

Hermes installation/invocation: NOT AUTHORIZED

Provider account creation: NOT AUTHORIZED

Credential creation/use: NOT AUTHORIZED

Network endpoint activation: NOT AUTHORIZED

Experiment spending: NOT AUTHORIZED

Raw input/output persistence: NOT AUTHORIZED

Paper/live/execution authority: FORBIDDEN

## Repository Inputs Reviewed

The review used the current agent/work-package controls; project status,
repo-truth, protected paths, evidence, validation, and drafting rules; the
WP95-WP98 Hermes foundation; the complete WP141-WP146 experiment chain; the
unchanged 20-case WP142 fixture; the WP143 caps and privacy requirements; the
WP144 controller/endpoint contract; the final WP145 bounded local harness; and
the merged WP146 closeout. Research artifacts have no execution authority.

The WP142 fixture is 49,497 bytes, contains 20 cases, and has a maximum compact
serialized case length of 2,279 characters. Those measured repository facts
inform token estimates but do not expose or transmit fixture content.

## Research Method

Research began without a provider selection. A current catalog scan produced
four exact remote configurations, which were pre-screened for public model
identity, no-training posture, standard retention no longer than 30 days,
tool-free stateless use, endpoint restriction feasibility, and budget fit.
Three configurations received deep review; only configurations with PASS on
every mandatory criterion could be shortlisted. Missing evidence remained
`EVIDENCE_INSUFFICIENT` and could not be converted into PASS.

The OpenAI official-documents MCP described by the local documentation skill
was not callable in this environment, and installing/configuring it was outside
WP147 authority. The allowed fallback was therefore restricted to current
official OpenAI web properties. All other provider and Hermes claims likewise
use public first-party properties. Search-result snippets were discovery aids
only and are not cited as evidence.

Facts are sourced; calculations and compatibility conclusions explicitly
marked `ANALYST_INFERENCE` are derived from those facts and the merged WP143
controller contract. No provider account, login-only setting, model response,
SDK, or endpoint was used.

## Research Cut-Off And Freshness

Research cut-off:
2026-07-22T23:49:02Z

Pricing, model, endpoint, lifecycle, privacy, retention, security, region,
subprocessor, error, limit, credential, and Hermes pages were accessed on
2026-07-22 UTC. Current pages may change after the cutoff; WP148 must re-check
all time-sensitive facts before making any evidence-resolution or configuration decision.
Undated pages are labeled `UNDATED_CURRENT_PAGE` rather than assigned invented
dates.

## Source Hierarchy

Tier 1 is an official provider API/model/legal/privacy/security document or the
official Hermes repository documentation and is mandatory for gates. Tier 2 is
an official provider help document and may support operational interpretation.
Tier 3 material may provide context only and cannot make a candidate eligible.
Every gating citation below is Tier 1 unless a row explicitly says otherwise;
the Tier 2 OpenAI key-permission page only supplements the official API/admin
surface and is not used for privacy eligibility.

## Source Registry

Each record contains every field required by the WP147 freshness contract.

```text
source_id: HERMES-001
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES, ANT-SONNET-MESSAGES
evidence_category: Hermes compatibility, provider interface, credential location
publisher: NousResearch
document_title: AI Providers
canonical_url: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Hermes documents direct openai-api, native Anthropic, Google/Gemini, and OpenAI-compatible providers; custom endpoints implement v1/chat/completions; credentials are configured outside prompts.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Official repository documentation; no install or invocation performed.
---
source_id: HERMES-002
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES, ANT-SONNET-MESSAGES
evidence_category: API mode and endpoint compatibility
publisher: NousResearch
document_title: Building a Model Provider Plugin
canonical_url: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/model-provider-plugin.md
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Hermes recognizes codex_responses, anthropic_messages, and chat_completions; api.openai.com auto-detects codex_responses.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Compatibility evidence only; future configuration remains prohibited.
---
source_id: HERMES-003
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES, ANT-SONNET-MESSAGES
evidence_category: timeout control
publisher: NousResearch
document_title: Configuration
canonical_url: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Provider-wide and model-specific request timeouts are supported for OpenAI-wire and native Anthropic transports.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: WP143 lower 180-second request limit remains controlling.
---
source_id: OAI-001
candidate_id: OAI-SOL-RESPONSES
evidence_category: identity, availability, limits, endpoint, pricing, lifecycle
publisher: OpenAI
document_title: GPT-5.6 Sol Model
canonical_url: https://developers.openai.com/api/docs/models/gpt-5.6-sol
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Exact model ID gpt-5.6-sol, Responses support, 128k provider max output, 1.05M context, $5/M input and $30/M output, snapshots, and account-tier rate limits.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: The WP143 50k/8k limits are lower and remain controlling.
---
source_id: OAI-002
candidate_id: OAI-LUNA-RESPONSES
evidence_category: identity, availability, limits, endpoint, pricing, lifecycle
publisher: OpenAI
document_title: GPT-5.6 Luna Model
canonical_url: https://developers.openai.com/api/docs/models/gpt-5.6-luna
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Exact model ID gpt-5.6-luna, Responses support, 128k provider max output, 1.05M context, $1/M input and $6/M output, snapshots, and account-tier rate limits.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: The WP143 50k/8k limits are lower and remain controlling.
---
source_id: OAI-003
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: API data use, retention, state, ZDR, region
publisher: OpenAI
document_title: Data controls in the OpenAI platform
canonical_url: https://developers.openai.com/api/docs/guides/your-data
accessed_at_utc: 2026-07-22T23:49:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: API data is not used for training; Responses abuse-monitoring retention is up to 30 days with documented exceptions; store=false prevents Responses application-state creation but does not prove deletion of abuse-monitoring content; ZDR or MAM requires approval and is not standard-account posture; data-residency controls and limitations are documented.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Refreshed for PR147-FU1. No ZDR or MAM eligibility is assumed. No public per-experiment operator-verifiable abuse-log deletion mechanism is documented for the standard posture; safety/legal exceptions are material limitations.
---
source_id: OAI-004
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: request shape, optional tools, state, output cap, usage
publisher: OpenAI
document_title: Migrate to the Responses API
canonical_url: https://developers.openai.com/api/docs/guides/migrate-to-responses
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Responses requests can be stateless with store false, accept bounded text input, omit tools, cap output, and return response/usage metadata.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: No hosted tool, conversation object, file, background mode, or MCP is in the candidate configuration.
---
source_id: OAI-005
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: errors and request traceability
publisher: OpenAI
document_title: Error codes
canonical_url: https://developers.openai.com/api/docs/guides/error-codes
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: HTTP/API error categories and request identifiers are documented for deterministic retry/stop handling.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: WP143 permits only bounded retry behavior.
---
source_id: OAI-006
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: rate limits
publisher: OpenAI
document_title: Rate limits
canonical_url: https://developers.openai.com/api/docs/guides/rate-limits
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Limits are organization/project/model and usage-tier dependent; response headers and 429 behavior support bounded control.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Actual account limits remain an operator verification gate, not an assumed value.
---
source_id: OAI-007
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: key lifecycle and least privilege
publisher: OpenAI
document_title: Assign API Key Permissions
canonical_url: https://help.openai.com/en/articles/8867743-assign-api-key-permissions
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_2
claim_supported: Project keys can be restricted per endpoint and edited or revoked through platform settings.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Operational supplement only; future operator must verify exact project and revocation controls.
---
source_id: OAI-008
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: jurisdiction, deletion, security, incident handling
publisher: OpenAI
document_title: OpenAI Data Processing Addendum
canonical_url: https://cdn.openai.com/pdf/openai-data-processing-addendum.pdf
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: 2026-01-01
source_tier: TIER_1
claim_supported: API processing, transfers, deletion obligations, technical/organizational security measures, subprocessors, and breach notification are documented.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Contract applicability must be confirmed by the operator before any future use.
---
source_id: OAI-009
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: subprocessors and processing locations
publisher: OpenAI
document_title: OpenAI Sub-processor list
canonical_url: https://openai.com/policies/sub-processor-list/
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: 2026-07-09
source_tier: TIER_1
claim_supported: Current API subprocessors, purposes, and processing locations are publicly listed.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Global processing exposure remains a material limitation unless later residency controls are approved and verified.
---
source_id: OAI-010
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: service-account key creation, project scope, replacement, revocation, operator verification
publisher: OpenAI
document_title: Service Accounts API Reference
canonical_url: https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/projects/subresources/service_accounts
accessed_at_utc: 2026-07-22T23:49:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: The project-scoped API supports creating service accounts and additional service-account API keys, retrieving/listing service accounts, deleting the service account, and returning a deletion response with a deleted boolean; creation, replacement, and service-account deletion are directly observable, but the page does not document deletion of one service-account key.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Feasibility evidence only. No service account or key was created, listed, retrieved, replaced, or deleted.
---
source_id: OAI-011
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: project key inventory, project scope, key deletion, operator verification
publisher: OpenAI
document_title: Project API Keys API Reference
canonical_url: https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/projects/subresources/api_keys
accessed_at_utc: 2026-07-22T23:49:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Project API keys can be listed and retrieved with owner and effective project-access fields; user-owned project keys can be deleted through the documented endpoint with a deleted boolean response; service-account keys carry a project role.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: The Tier 2 OAI-007 page supplements endpoint-level UI interpretation only. OAI-011 documents deletion of user-owned project keys and explicitly distinguishes service-account-owned keys; it does not complete the exact service-account-key revocation chain.
---
source_id: OAI-012
candidate_id: OAI-SOL-RESPONSES, OAI-LUNA-RESPONSES
evidence_category: project-bound roles and least-privilege permission sets
publisher: OpenAI
document_title: Roles API Reference
canonical_url: https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/roles
accessed_at_utc: 2026-07-22T23:49:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: The administration API supports project-bound custom roles with explicit permission arrays and returns the configured permissions, allowing a future operator to define and verify least-privilege project administration independently of model input.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Role feasibility evidence only; no role, permission assignment, account, or key was created or modified.
---
source_id: ANT-001
candidate_id: ANT-SONNET-MESSAGES
evidence_category: identity, availability, version, pricing, context, output
publisher: Anthropic
document_title: Models overview
canonical_url: https://platform.claude.com/docs/en/about-claude/models/overview
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Exact pinned ID claude-sonnet-5, general Claude API availability, 1M context, 128k output, and $3/M input and $15/M output (with temporary introductory pricing separately disclosed).
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Cost calculations use the non-promotional $3/$15 rates.
---
source_id: ANT-002
candidate_id: ANT-SONNET-MESSAGES
evidence_category: endpoint, headers, request shape, output cap
publisher: Anthropic
document_title: Get started with Claude
canonical_url: https://platform.claude.com/docs/en/get-started
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: POST https://api.anthropic.com/v1/messages uses content-type, x-api-key, anthropic-version, exact model, messages, and max_tokens.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: No call was made.
---
source_id: ANT-003
candidate_id: ANT-SONNET-MESSAGES
evidence_category: no training and commercial API terms
publisher: Anthropic
document_title: Commercial Terms of Service
canonical_url: https://www.anthropic.com/legal/commercial-terms
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Anthropic may not train models on commercial-service customer content; DPA and destruction-request obligations are incorporated.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Consumer terms were not substituted.
---
source_id: ANT-004
candidate_id: ANT-SONNET-MESSAGES
evidence_category: retention and automatic deletion
publisher: Anthropic
document_title: How long do you store my organization's data?
canonical_url: https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Anthropic API inputs/outputs are normally auto-deleted within 30 days; policy, legal, feedback, and covered-model exceptions are disclosed.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Normal retention passes the <=30-day gate; exception risk is material.
---
source_id: ANT-005
candidate_id: ANT-SONNET-MESSAGES
evidence_category: regions and operator-verifiable geography
publisher: Anthropic
document_title: Data residency
canonical_url: https://platform.claude.com/docs/en/manage-claude/data-residency
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: inference_geo supports global or US-only inference, reports the used geo in usage, and applies a 1.1x US-only price multiplier.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Candidate costing uses the conservative 1.1x US-only multiplier.
---
source_id: ANT-006
candidate_id: ANT-SONNET-MESSAGES
evidence_category: stateless API, optional tools/memory, ZDR
publisher: Anthropic
document_title: API and data retention
canonical_url: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Messages is ZDR-eligible; hosted/stateful features have distinct retention; tools and memory are not mandatory for plain Messages use.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: No ZDR eligibility is assumed and all optional tools are excluded.
---
source_id: ANT-007
candidate_id: ANT-SONNET-MESSAGES
evidence_category: errors, request ID, rate limits, usage
publisher: Anthropic
document_title: Claude API errors and rate limits
canonical_url: https://platform.claude.com/docs/en/api/errors
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Error shapes, request-id, transient status classes, account-tier limits, retry-after, and token limit headers are documented.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Account-specific current limits require later operator verification.
---
source_id: ANT-008
candidate_id: ANT-SONNET-MESSAGES
evidence_category: credential scoping, revocation, usage/cost reporting
publisher: Anthropic
document_title: Workspaces
canonical_url: https://platform.claude.com/docs/en/manage-claude/workspaces
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Keys are workspace-scoped; workspace archival revokes keys; limits, usage, and cost can be tracked by workspace.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: No account or key was created.
---
source_id: ANT-009
candidate_id: ANT-SONNET-MESSAGES
evidence_category: model lifecycle
publisher: Anthropic
document_title: Model deprecations
canonical_url: https://platform.claude.com/docs/en/about-claude/model-deprecations
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Active, legacy, deprecated, and retired states are defined with at least 60 days notice for public model retirement.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: claude-sonnet-5 was current and not listed as deprecated at cutoff.
---
source_id: ANT-010
candidate_id: ANT-SONNET-MESSAGES
evidence_category: subprocessors and security
publisher: Anthropic
document_title: Anthropic Trust Center and Data Processing Addendum references
canonical_url: https://trust.anthropic.com/
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Security/compliance portal exists, but the bounded public review did not yield a current accessible subprocessor record with entity, purpose, and processing-location detail.
direct_or_inferred: DIRECT
freshness_status: EVIDENCE_INSUFFICIENT
notes: Login/dynamic portal content cannot satisfy the mandatory public-subprocessor gate.
---
source_id: GGL-001
candidate_id: GGL-FLASH-DEVELOPER
evidence_category: preliminary model and API availability
publisher: Google
document_title: Gemini API models and rate limits
canonical_url: https://ai.google.dev/gemini-api/docs/rate-limits
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Gemini 3.5 Flash appears in the current developer API catalog and account-dependent rate-limit documentation.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: Preliminary screening only.
---
source_id: GGL-002
candidate_id: GGL-FLASH-DEVELOPER
evidence_category: preliminary pricing and data handling
publisher: Google
document_title: Gemini API billing
canonical_url: https://ai.google.dev/gemini-api/docs/billing
accessed_at_utc: 2026-07-22T21:55:02Z
document_effective_date_or_last_updated: UNDATED_CURRENT_PAGE
source_tier: TIER_1
claim_supported: Paid-tier prompts/responses are not used to improve Google products; billing and account tier prerequisites are documented.
direct_or_inferred: DIRECT
freshness_status: CURRENT_AT_CUTOFF
notes: A public operator-verifiable deletion control for the exact Developer API configuration was not found in the bounded screen.
```

## Candidate Pool Construction

Preliminary pool count: 4.

| Candidate ID | Exact configuration | Intended role | Pre-screen result | Evidence |
|---|---|---|---|---|
| OAI-SOL-RESPONSES | OpenAI + Responses API + `gpt-5.6-sol` | high-capability reasoning | ADVANCE_TO_DEEP_RESEARCH | OAI-001, OAI-003, HERMES-001, HERMES-002 |
| OAI-LUNA-RESPONSES | OpenAI + Responses API + `gpt-5.6-luna` | lower-cost comparison | ADVANCE_TO_DEEP_RESEARCH | OAI-002, OAI-003, HERMES-001, HERMES-002 |
| ANT-SONNET-MESSAGES | Anthropic + Claude Messages API + `claude-sonnet-5` | cross-provider capable comparison | ADVANCE_TO_DEEP_RESEARCH | ANT-001 through ANT-010, HERMES-001 |
| GGL-FLASH-DEVELOPER | Google + Gemini Developer API + `gemini-3.5-flash` | lower-cost/latency screen | STOP_PRELIMINARY_EVIDENCE_INSUFFICIENT | GGL-001, GGL-002 |

Google was not deeply researched because the bounded official screen did not
find an operator-verifiable deletion control for this exact Developer API
configuration. Absence of evidence is not a negative claim, but it fails the
mandatory evidence pre-screen. Managed autonomous-agent offerings and
aggregators were excluded by design because they expand tools, endpoints,
subprocessors, or persistence beyond the WP143 target.

## Hermes Compatibility Evidence

Official Hermes documentation lists direct OpenAI API and native Anthropic as
provider families. Its provider runtime identifies `api.openai.com` as
`codex_responses`, supports `anthropic_messages`, and permits provider/model
timeouts. Therefore:

| Candidate | Interface | Compatibility classification | Evidence |
|---|---|---|---|
| OAI-SOL-RESPONSES | `codex_responses` at direct OpenAI API | PASS_CODEX_RESPONSES | HERMES-001, HERMES-002, HERMES-003 |
| OAI-LUNA-RESPONSES | `codex_responses` at direct OpenAI API | PASS_CODEX_RESPONSES | HERMES-001, HERMES-002, HERMES-003 |
| ANT-SONNET-MESSAGES | native `anthropic_messages` | PASS | HERMES-001, HERMES-002, HERMES-003 |

This is interface feasibility only. It does not prove a local installed Hermes
version, configured provider, auxiliary-client behavior, credential, or actual
request. A WP148 decision must pin the exact Hermes version and prohibit
fallbacks before any later implementation could be considered.

## Mandatory Eligibility Criteria

Allowed gate states are `PASS`, `FAIL`, `EVIDENCE_INSUFFICIENT`, and
`NOT_APPLICABLE`. Every mandatory gate must be PASS to shortlist. Preferred ZDR
may be unavailable only when normal API retention is documented at no more
than 30 days and every mandatory privacy gate passes. Consumer policy is never
API evidence. Alias, price, benchmark reputation, or provider familiarity
cannot compensate for a failed or unknown gate.

The mandatory categories are exact identity; public availability; API/model
lifecycle; API no-training; retention; deletion; jurisdiction; subprocessors;
security and incident evidence; exact endpoint/redirect control; optional-only
hosted tools and memory; no repository connection; request identity; token and
cost reporting; output cap; timeout; errors; rate limits; key lifecycle; secret
isolation; synthetic-data and WP133 compatibility; Hermes compatibility;
pricing; per-call/total/daily budgets; and caveat disclosure.

Negative-test matrix: REQUIRED for the hardened test-only matrix parser. The
existing focused regression proves Tier-2-only mandatory support fails; Tier 2
may supplement but not replace Tier 1; inference-only support fails;
request-manifest verification cannot prove provider-side deletion; one
mandatory `EVIDENCE_INSUFFICIENT` removes eligibility; candidate-ID aliases are
rejected; and canonical cost values must agree across evidence surfaces.

## Remote Candidate Evidence

Deep research count: 3.

`OAI-SOL-RESPONSES` is OpenAI + Responses API + exact model identifier
`gpt-5.6-sol`. It is the high-capability role. The request is restricted to
plain synthetic text, `store=false`, no conversation, no file, no background
mode, no hosted tool, no MCP, no web/search, no memory, and an 8,000-token
controller cap. Exact candidate evidence: OAI-001 through OAI-012 and
HERMES-001 through HERMES-003.

`OAI-LUNA-RESPONSES` is OpenAI + Responses API + exact model identifier
`gpt-5.6-luna`. It is the lower-cost comparison role under the identical
stateless/no-tool request posture. Exact candidate evidence: OAI-002 through
OAI-012 and HERMES-001 through HERMES-003.

`ANT-SONNET-MESSAGES` is Anthropic + Claude Messages API + exact pinned model
identifier `claude-sonnet-5`. It supports a plain, bounded, tool-free Messages
request and passes the reviewed functional, privacy, region, lifecycle, and
budget gates, but the bounded public review did not obtain either the mandatory
current public subprocessor record or an accessible detailed security-program
and incident-notification record. Exact candidate evidence: ANT-001 through
ANT-010 and HERMES-001 through HERMES-003.

## Privacy, Training, Retention, And Deletion

OpenAI's API endpoint table marks Responses data as not used for training,
records default abuse-monitoring retention up to 30 days, and permits
`store=false` so the candidate creates no Responses application-state record.
The request manifest can verify only the request shape and prevention of that
application-state creation. It cannot verify deletion of provider-side
abuse-monitoring content. OAI-003 documents automatic provider retention,
legal/safety exceptions, and approval-dependent ZDR/MAM, but no public
per-experiment operator-verifiable deletion method for the evaluated standard
account posture. OAI-008's contractual deletion obligations do not create a
per-request verification mechanism. The mandatory deletion gate is therefore
`EVIDENCE_INSUFFICIENT` for both OpenAI configurations.

| Required deletion fact | OpenAI standard Responses posture | Gate effect |
|---|---|---|
| `application_state_creation_prevented` | `store=false`; request manifest verifies the field | PROVEN, but narrower than provider deletion |
| `abuse_monitoring_retention` | Up to 30 days by default, with documented legal/safety exceptions | PROVEN |
| `provider_side_deletion_method` | Automatic policy expiry; no public experiment-specific deletion action for abuse-monitoring content | EVIDENCE_INSUFFICIENT |
| `operator_verification_method` | No public mechanism proving that retained abuse-monitoring content for the experiment was deleted | EVIDENCE_INSUFFICIENT |
| `ZDR_or_MAM_eligibility` | Prior approval and additional requirements; not assumed | NOT ESTABLISHED FOR CANDIDATE |
| `exceptions` | Legal, service-protection, Eyes Off, Safety Retention, and image/file safety exceptions are documented | MATERIAL |

Anthropic commercial terms prohibit training on customer content and the API
retention page states normal automatic input/output deletion within 30 days.
Messages is ZDR-eligible, but eligibility is not assumed. The documented
policy/safety/legal exceptions are material, and the bounded public evidence
does not provide per-experiment operator verification of the automatic
provider-side deletion. The mandatory deletion gate is therefore also
`EVIDENCE_INSUFFICIENT`. ANT-003, ANT-004, and ANT-006 support these facts.

No candidate permits raw repo data, live market/account data, feedback
submission, files, persistent conversations, or raw local persistence. The
input remains the synthetic WP142 cases only.

## Jurisdiction, Subprocessors, And Security

OpenAI documents global processing locations and named API subprocessors,
security measures, incident response/breach notice, contractual deletion, and
conditional data-residency options. The shortlist does not assume enterprise
residency or ZDR. Any future operator must accept the documented global
exposure or prove an eligible configured residency control. Evidence: OAI-003,
OAI-008, OAI-009.

Anthropic documents per-request `inference_geo` and response reporting for US
or global inference, commercial confidentiality obligations, and a Trust
Center. The bounded public review did not obtain a current public subprocessor
record containing the entity/purpose/location detail required by WP147 or an
accessible detailed security-program and incident-notification record.
`ANT-010` is therefore `EVIDENCE_INSUFFICIENT` on both mandatory rows, making
the exact configuration not shortlistable even though other strengths remain.

## API, Model Version, Errors, Limits, And Observability

OpenAI model pages identify exact model IDs and current endpoint support. The
pages present the IDs in their snapshots sections; the unsuffixed `gpt-5.6`
alias is not used. Responses expose usage for reproducible token-cost
calculation, and OpenAI documents request IDs, error classes, 429/rate-limit
behavior, and account-tier limits. Account limits are not assumed. The future
controller must record sanitized provider request ID, model ID, token counts,
status class, latency, and calculated cost only.

Anthropic says `claude-sonnet-5` is a pinned snapshot rather than an evergreen
pointer, documents a lifecycle with at least 60-day public-retirement notice,
returns request IDs and token usage, provides account-dependent limits and
rate headers, and supports `max_tokens`. Introductory pricing is time-limited,
so conservative calculations use the higher standard price.

Provider context/output capacities never replace WP143 caps: 50,000 input
tokens maximum, 8,000 output tokens maximum, 180 seconds per request, 300
seconds per case, one concurrent request, and bounded retries.

## Endpoint And Network Restriction Feasibility

| Candidate | Sole future permitted host/path | Redirect posture | Feasibility | Evidence |
|---|---|---|---|---|
| OAI-SOL-RESPONSES | `https://api.openai.com/v1/responses` | Controller must disable redirects and fail any 3xx or host/path change; documentation requires no redirect | PASS | OAI-001, OAI-004, HERMES-002; redirect control is ANALYST_INFERENCE from WP143 |
| OAI-LUNA-RESPONSES | `https://api.openai.com/v1/responses` | Same exact fail-closed rule | PASS | OAI-002, OAI-004, HERMES-002; redirect control is ANALYST_INFERENCE from WP143 |
| ANT-SONNET-MESSAGES | `https://api.anthropic.com/v1/messages` | Same exact fail-closed rule | PASS | ANT-002, HERMES-002; redirect control is ANALYST_INFERENCE from WP143 |

DNS/TLS and the one exact provider host are unavoidable future network
dependencies. Documentation, status, telemetry, file, model-discovery,
fallback, hosted-tool, and secondary provider hosts are denied. A redirect is
never followed; it is a terminal endpoint-policy failure. Research browsing
hosts are not runtime allowlist candidates. No endpoint was activated or
called in WP147.

## Credential And Key-Lifecycle Evidence

OpenAI's Tier 1 administration references document project-scoped service
account and project-key creation/inventory, additional service-account keys for
replacement, project-bound roles with explicit permission sets, deletion of a
service account or user-owned project key, and deletion responses containing a
`deleted` boolean. They do not directly establish the complete exact chain for
one proposed service-account credential: endpoint-level key restriction is
described only by Tier 2 OAI-007, and the Tier 1 project-key deletion reference
distinguishes service-account-owned keys rather than documenting deletion of
one such key. OAI-010 through OAI-012 are material Tier 1 partial evidence;
OAI-007 may supplement but cannot cure the remaining gap. The OpenAI mandatory
key-lifecycle gate is therefore `EVIDENCE_INSUFFICIENT`.
Anthropic supports workspace-scoped keys, separate limits, usage/cost
reporting, and revocation by key removal or workspace archival. The future
secret must be operator-created outside the repo, injected only into the
transport process, never placed in prompts/model context/logs/artifacts, and
revoked after the experiment. A project/workspace must be dedicated to the
experiment with no file, tool, admin, or unrelated endpoint permission.

These are feasibility findings, not existing credentials. Provider account
creation and credential creation/use remain unauthorized. Account-specific key
scope and revocation must be manually verified in WP148 before any later
implementation package.

## Pricing And Cost Model

No-cache standard rates are used; cache discounts, batches, promotions, and
free tiers are assumed to be zero. Formula:

`call_cost = input_tokens / 1,000,000 * input_rate + output_tokens / 1,000,000 * output_rate`

Expected planning case uses 8,000 input and 2,000 output tokens. Absolute
stress uses WP143's 50,000 input and 8,000 output. Reasoning tokens, if billed
as output, must fit inside the 8,000 output cap. The full 49,497-byte fixture is
never sent as one call; the measured 2,279-character maximum case plus prompt
and schema overhead supports the deliberately conservative 8,000-token
expected input estimate. Actual provider token usage would control accounting.

| Candidate | Conservative rates per 1M | Expected call | Absolute stress call | Evidence |
|---|---:|---:|---:|---|
| OAI-SOL-RESPONSES | $5 input / $30 output | `(8k*5 + 2k*30)/1M = $0.100` | `(50k*5 + 8k*30)/1M = $0.490` | OAI-001 |
| OAI-LUNA-RESPONSES | $1 input / $6 output | `(8k*1 + 2k*6)/1M = $0.020` | `(50k*1 + 8k*6)/1M = $0.098` | OAI-002 |
| ANT-SONNET-MESSAGES | $3.30 input / $16.50 output (standard $3/$15 with 1.1x US geo) | `(8k*3.3 + 2k*16.5)/1M = $0.0594` | `(50k*3.3 + 8k*16.5)/1M = $0.297` | ANT-001, ANT-005 |

Canonical Anthropic geo-adjusted values:

- `expected_us_geo_cost: USD 0.0594`
- `stress_us_geo_cost: USD 0.2970`

These are reproducible projections, not invoices or spending authority. Taxes,
minimum deposits, currency conversion, provider-side rounding, failed-request
billing, and price changes are not included and require operator verification.

## WP143 Budget Compatibility

For a non-executable two-OpenAI comparison envelope retained only for cost
reproducibility, the 120-call primary scenario allocates 60 calls to each
configuration. Expected cost is `60*$0.100 + 60*$0.020 = $7.20`; absolute
stress cost is `60*$0.490 + 60*$0.098 = $35.28`.

The hypothetical hard 140-call envelope allocates at most 70 calls to each configuration.
Absolute stress cost is `70*$0.490 + 70*$0.098 = $41.16`, below USD 100. A
seven-day schedule of at most 20 calls/day, ten per candidate, has absolute
stress cost `10*$0.490 + 10*$0.098 = $5.88/day`, below USD 25. Each absolute
stress call is below USD 2. Concurrency remains 1. Primary calls remain 120,
retry calls remain 20, and total calls remain 140.

| WP143 cap | Preserved value | Result |
|---|---:|---|
| Cases | 20 | PASS |
| Repeats per candidate/case | 3 | PASS |
| Primary calls | 120 | PASS |
| Retry calls | 20 | PASS |
| Total calls | 140 | PASS |
| Input tokens/call | 50,000 maximum | PASS |
| Output tokens/call | 8,000 maximum | PASS |
| Request timeout | 180 seconds | PASS |
| Case timeout | 300 seconds | PASS |
| Concurrent calls | 1 | PASS |
| Single call spend | USD 2 maximum | PASS |
| Daily spend | USD 25 maximum | PASS |
| Total spend | USD 100 maximum | PASS |
| Automatic top-up | FORBIDDEN | PASS |

Experiment spending: NOT AUTHORIZED

## Optional Local Baseline

Local baseline decision:
DEFERRED_HARDWARE_EVIDENCE_MISSING

Repository/current-context evidence does not establish CPU model/instruction
set, physical RAM and available RAM, GPU vendor/model, GPU VRAM, usable local
storage, driver/runtime support, or sustained thermal/power constraints.
Operating-system context alone is insufficient. No runtime, model, license,
quantization, throughput, or fit is inferred, and no model was downloaded or
executed.

Local baseline evaluated: NO

## Candidate Eligibility Matrix

The following matrix covers every mandatory gate. `ZDR` is preferred and does
not compensate for any mandatory failure. Every candidate cell cites existing
registry IDs. A mandatory PASS requires at least one directly relevant Tier 1,
DIRECT, current source; Tier 2 and analyst inference may supplement but never
replace that source. A source marked `EVIDENCE_INSUFFICIENT` cannot support a
PASS. The focused regression maps every citation back to this registry and
derives eligibility and shortlist counts from the mandatory rows.

| Mandatory gate | OAI-SOL-RESPONSES | OAI-LUNA-RESPONSES | ANT-SONNET-MESSAGES |
|---|---|---|---|
| Exact identity | PASS (OAI-001) | PASS (OAI-002) | PASS (ANT-001) |
| Public availability/prerequisites | PASS (OAI-001) | PASS (OAI-002) | PASS (ANT-001, ANT-002) |
| Version/lifecycle/deprecation | PASS (OAI-001) | PASS (OAI-002) | PASS (ANT-001, ANT-009) |
| API no-training | PASS (OAI-003) | PASS (OAI-003) | PASS (ANT-003) |
| Default/configurable retention <=30 days | PASS (OAI-003) | PASS (OAI-003) | PASS (ANT-004, ANT-006) |
| ZDR availability (preferred) | PASS, approval required/not assumed (OAI-003) | PASS, approval required/not assumed (OAI-003) | PASS, agreement required/not assumed (ANT-006) |
| Deletion/operator-verifiable control | EVIDENCE_INSUFFICIENT, store=false proves application-state prevention but no operator-verifiable abuse-log deletion (OAI-003, OAI-008) | EVIDENCE_INSUFFICIENT, same unresolved provider-side deletion proof (OAI-003, OAI-008) | EVIDENCE_INSUFFICIENT, automatic policy deletion lacks per-experiment operator verification (ANT-004, ANT-006) |
| Jurisdiction/region evidence | PASS, global locations and conditional residency disclosed (OAI-003, OAI-009) | PASS, global locations and conditional residency disclosed (OAI-003, OAI-009) | PASS, US/global request and response evidence (ANT-005) |
| Current public subprocessors | PASS (OAI-009) | PASS (OAI-009) | EVIDENCE_INSUFFICIENT (ANT-010) |
| Security/incident evidence | PASS (OAI-008) | PASS (OAI-008) | EVIDENCE_INSUFFICIENT (ANT-003, ANT-010) |
| Exact host/path and redirects | PASS (OAI-001, OAI-004, HERMES-002; ANALYST_INFERENCE supplements direct endpoint evidence) | PASS (OAI-002, OAI-004, HERMES-002; ANALYST_INFERENCE supplements direct endpoint evidence) | PASS (ANT-002, HERMES-002; ANALYST_INFERENCE supplements direct endpoint evidence) |
| Hosted tools not mandatory | PASS (OAI-004) | PASS (OAI-004) | PASS (ANT-002, ANT-006) |
| Persistent hosted memory not mandatory | PASS (OAI-003, OAI-004) | PASS (OAI-003, OAI-004) | PASS (ANT-006) |
| Repository connection not required | PASS (OAI-004) | PASS (OAI-004) | PASS (ANT-002) |
| Request identity | PASS (OAI-005) | PASS (OAI-005) | PASS (ANT-007) |
| Usage reporting | PASS (OAI-004) | PASS (OAI-004) | PASS (ANT-005, ANT-008) |
| Reproducible cost reporting | PASS (OAI-001, OAI-004) | PASS (OAI-002, OAI-004) | PASS (ANT-001, ANT-008) |
| Configurable output cap | PASS (OAI-001, OAI-004) | PASS (OAI-002, OAI-004) | PASS (ANT-001, ANT-002) |
| Controller timeout compatibility | PASS (HERMES-003) | PASS (HERMES-003) | PASS (HERMES-003) |
| Documented errors/transients | PASS (OAI-005) | PASS (OAI-005) | PASS (ANT-007) |
| Rate-limit behavior | PASS, account value later verified (OAI-001, OAI-006) | PASS, account value later verified (OAI-002, OAI-006) | PASS, account value later verified (ANT-007, ANT-008) |
| Key create/scope/rotate/revoke | EVIDENCE_INSUFFICIENT, Tier 1 partial chain plus Tier 2 endpoint restriction cannot prove exact service-account-key revocation (OAI-007, OAI-010, OAI-011, OAI-012) | EVIDENCE_INSUFFICIENT, same incomplete exact credential chain (OAI-007, OAI-010, OAI-011, OAI-012) | PASS (ANT-008) |
| Secret isolation from model context | PASS (HERMES-001, OAI-010, OAI-012; ANALYST_INFERENCE supplements direct configuration evidence) | PASS (HERMES-001, OAI-010, OAI-012; ANALYST_INFERENCE supplements direct configuration evidence) | PASS (HERMES-001, ANT-008; ANALYST_INFERENCE supplements direct configuration evidence) |
| Synthetic WP142 input/no tools | PASS (OAI-004 plus repository input) | PASS (OAI-004 plus repository input) | PASS (ANT-002, ANT-006 plus repository input) |
| WP133 bounded plain/structured output | PASS (OAI-001, OAI-004) | PASS (OAI-002, OAI-004) | PASS (ANT-001, ANT-002) |
| Hermes compatibility | PASS (HERMES-001 through HERMES-003) | PASS (HERMES-001 through HERMES-003) | PASS (HERMES-001 through HERMES-003) |
| Current input/output pricing | PASS (OAI-001) | PASS (OAI-002) | PASS (ANT-001, ANT-005) |
| Per-call <=USD2 | PASS, $0.490 stress (OAI-001) | PASS, $0.098 stress (OAI-002) | PASS, $0.297 stress (ANT-001, ANT-005) |
| Total <=USD100 | PASS, shortlist plan jointly $41.16 stress (OAI-001, OAI-002) | PASS, shortlist plan jointly $41.16 stress (OAI-001, OAI-002) | PASS, standalone projection within cap (ANT-001, ANT-005) |
| Daily executable <=USD25 | PASS, joint 20-call day $5.88 stress (OAI-001, OAI-002) | PASS, joint 20-call day $5.88 stress (OAI-001, OAI-002) | PASS, standalone 20-call day $5.94 stress (ANT-001, ANT-005) |
| Material caveats disclosed | PASS (OAI-003, OAI-006, OAI-008, OAI-009) | PASS (OAI-003, OAI-006, OAI-008, OAI-009) | PASS (ANT-004, ANT-005, ANT-006, ANT-007, ANT-008, ANT-009) |

Candidate classifications:

- OAI-SOL-RESPONSES: `NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT` because provider-side deletion/operator verification and the exact Tier 1 key-lifecycle chain remain unresolved.
- OAI-LUNA-RESPONSES: `NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT` because provider-side deletion/operator verification and the exact Tier 1 key-lifecycle chain remain unresolved.
- ANT-SONNET-MESSAGES: `NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT` because deletion/operator verification, public subprocessors, and detailed security/incident evidence remain unresolved.

`EVIDENCE_INSUFFICIENT` never acts as PASS.

## Eligible Candidate Comparison

No deeply researched configuration passes every mandatory row, so there is no
eligible-candidate comparison and no tie to break. The cost and capability
research remains useful evidence, but it cannot compensate for unresolved
deletion/operator-verification gates.

## Candidate Shortlist

Candidate shortlist decision:
EVIDENCE_INSUFFICIENT_NO_SHORTLIST

Remote configurations researched deeply: 3

Remote configurations eligible: 0

Remote configurations shortlisted: 0

No candidate entry is emitted. `EVIDENCE_INSUFFICIENT_NO_SHORTLIST` is a valid
complete WP147 outcome and is not a provider-negative claim, production
selection, activation decision, or trading recommendation.

## Candidate-Specific Blockers

- `ANT-SONNET-MESSAGES`: operator-verifiable provider-side deletion, current
  public subprocessor entity/purpose/location evidence, and an accessible
  detailed security-program/incident-notification record were not available in
  the bounded official review, so mandatory gates are
  `EVIDENCE_INSUFFICIENT`; it is not shortlisted.
- `GGL-FLASH-DEVELOPER`: stopped before deep research because a public
  operator-verifiable deletion control for the exact Developer API
  configuration was not found; this is evidence insufficiency, not a claim
  that deletion is impossible.
- `OAI-SOL-RESPONSES` and `OAI-LUNA-RESPONSES`: `store=false` proves only
  prevention of Responses application-state creation. The bounded Tier 1
  evidence does not expose an operator-verifiable method proving deletion of
  standard-posture abuse-monitoring content for the experiment. The exact
  Tier 1 service-account-key restriction/revocation chain is also incomplete. Both are
  `NOT_SHORTLISTABLE_EVIDENCE_INSUFFICIENT`.

## Cross-Cutting Remote-Implementation Blockers

The following remain absent and unauthorized: operator acceptance of current
terms and processing jurisdictions; account/project eligibility; exact current
rate/spend limits; approved budget; a restricted revocable key and secret
injection path; pinned Hermes install/version evidence; one-host DNS/TLS and
redirect-deny sandbox; disabled fallback/tool/memory/source access; approved
raw-output and sanitized-evidence policy; remote adapter/controller
implementation; teardown/revocation proof; and a controlled dry run.

Research cannot prove login-only account settings. A separately approved
evidence-resolution/research-refresh decision must resolve every mandatory
unknown before any candidate-selection package can be proposed. A still-later
implementation WP would remain required. One missing gate preserves `NOT_READY`.

## Readiness Decision

Remote controlled experiment readiness: NOT_READY

The research blocker from WP146 is resolved enough to record current candidate
evidence, but the mandatory matrix yields no eligible candidate and no
shortlist. No remote capability is configured or authorized. This decision
cannot be interpreted as readiness, production selection, model
quality proof, account approval, budget approval, or permission to call an API.

Next phase:
MANDATORY_EVIDENCE_RESOLUTION_AND_RESEARCH_REFRESH_DECISION

WP148 requires separate approval and is not authorized as candidate selection while the shortlist count is zero

## Promotion Gates

Before candidate selection can be proposed, a separately approved evidence
resolution package must revalidate source freshness and establish a directly
relevant Tier 1 operator-verifiable provider-side deletion posture for every
candidate it would reconsider. Only after every mandatory row passes may a
later selection package lock exact model IDs, endpoints, lower limits, privacy
controls, terms, jurisdiction, account, key, budget, and evidence decisions.
Implementation, dry run, and promotion each require later separate
authorization and evidence.

## Explicit Deferred Capabilities

Hermes install/version/invocation; provider/model selection or activation;
account; credential; secret store; endpoint allowlist; DNS/TLS sandbox; remote
adapter/client/controller; request/retry; prompt/config package; case execution;
model output; benchmark/quality result; raw or stable experiment storage;
operator billing/spend; source retrieval; production; recommendation;
probability/ranking; paper/live; execution/risk/order; and trading integration
are deferred and unauthorized. They are not WP147 defects.

## Output Surface Inventory

WP147 repository outputs are this one canonical Markdown research record, one
Markdown-only focused test, one stable status fragment, project-status and
repo-truth-index reconciliation, and the dedicated project-status/status-chain
regression update. No source, tool, fixture, workflow, dependency, lock,
configuration, credential, prompt, runtime, raw webpage, screenshot, response,
benchmark, storage, billing, paper/live, or trading artifact is created.

## Forbidden Interpretations

The following are false: familiar provider means eligible; `store=false` proves
provider-side abuse-log deletion; a request manifest verifies provider deletion;
consumer privacy is API policy; absence of retention evidence means zero; enterprise ZDR/residency
is automatically available; model alias means a pinned version; context size
is output size; advertised tools must be enabled; SDK compatibility proves
Hermes compatibility; research hosts belong on a runtime allowlist; budget cap
authorizes spending; evidence research must force a shortlist; candidate means production;
research network means product network; unknown rate means unlimited; local
hardware can be guessed; stronger catalog positioning overrides privacy; one
failed gate can be compensated; WP147 starts WP142 calls; or WP147 implements
WP148.

No provider/model is activated, selected for production, or approved for
trading.

## Future WP148 Boundary

WP148 remains separately gated and unimplemented. While WP147 has zero eligible
and zero shortlisted configurations, its revised purpose may only be a
mandatory-evidence resolution and research-refresh decision. It may not select
a provider, install Hermes, create/use credentials, call a model, implement an
adapter/sandbox, execute cases, spend, persist raw output, or trade. Candidate
selection requires a later separately approved package after a refreshed
matrix proves every mandatory gate.

## Decision

WP147 research status:
COMPLETE

Candidate shortlist decision:
EVIDENCE_INSUFFICIENT_NO_SHORTLIST

Remote controlled experiment readiness: NOT_READY

Provider/model activation: NOT AUTHORIZED

Provider/model call: NOT AUTHORIZED

Hermes installation/invocation: NOT AUTHORIZED

Provider account creation: NOT AUTHORIZED

Credential creation/use: NOT AUTHORIZED

Network endpoint activation: NOT AUTHORIZED

Experiment spending: NOT AUTHORIZED

Raw input/output persistence: NOT AUTHORIZED

Paper/live/execution authority: FORBIDDEN

## Non-Authority Statement

This research and no-shortlist decision have no execution authority. They do not modify or
authorize runtime execution, OMS, reconciliation, risk caps, bounded overlay
semantics, safe mode, configs, credentials, live-trading paths, paper trading,
orders, or market/account behavior. Deterministic validation and human review
remain controlling, and research/workbench conclusions cannot place trades or
change runtime behavior.
