# Negative Test Matrix Policy

Status: `WORKFLOW_GOVERNANCE_MANDATORY`

Applies to: all WPs that add or modify validators, parsers, schema validators, scorers, contract enforcement, forbidden-field scanners, boundary guards, evidence guards, or semantic wording filters.

---

## Purpose

Prevent semantic validation gaps like those seen in WP49 and WP56. When a validator or guard is added, the test suite must include a matrix of negative cases proving the validator correctly rejects invalid inputs — not only that it accepts valid ones.

---

## Scope

This policy applies when a WP adds or modifies:

- Validators
- Parsers
- Schema validators
- Scorers
- Contract enforcement logic
- Forbidden-field scanners
- Boundary guards
- Evidence guards (local or GitHub-aware)
- Semantic wording filters

---

## Required Negative-Test Matrix Categories

Before `Ready for review: YES`, WPs in scope must cover:

1. Missing required field
2. Null value where field is required
3. Wrong type (e.g., string where integer expected)
4. Empty string / empty list / empty dict where invalid
5. Stale or future timestamp (if timestamps are validated)
6. Forbidden field name
7. Forbidden wording (e.g., trade-like, credential-like, strategy-like terms)
8. Credential-like token (e.g., fake API key pattern)
9. Trade-like or strategy-like wording where forbidden
10. Boundary crossing term (e.g., execution/live-trading terms in advisory-only context)
11. Malformed input (truncated, wrong encoding, wrong format)
12. Duplicate or conflicting input
13. Edge spelling variants (common typos of forbidden terms)
14. Case-insensitive variant (e.g., `FORBIDDEN` vs `forbidden`)
15. Safe allowed wording (must not be over-blocked — at least one positive case per wording rule)

Not all categories apply to every WP. Inapplicable categories must be identified and explained.

---

## PR Body Requirements

The PR body must state:

```
Negative test matrix required: YES / NO
```

If YES, list the categories covered.

If NO, explain why the matrix is not applicable (e.g., no validator/scorer/parser added or modified).

---

## Enforcement

- A validator/scorer/parser/schema-validator WP must not be marked `Ready for review: YES` if the applicable negative-test matrix is missing.
- The matrix must be tested in code, not only described in docs.
- The reviewer must confirm the matrix is present and covers the applicable categories before approving.

---

## Cross-References

- `docs/work_package_template.md`
- `docs/ai/codex/WP_BUNDLING_POLICY.md`
- `docs/ai/codex/PR_REVIEW_CHECKLIST.md`
- `.github/pull_request_template.md`
- `docs/testing_requirements.md`
