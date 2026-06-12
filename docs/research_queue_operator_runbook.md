# Research Queue Operator Runbook

## Purpose

This runbook covers the safe manual use of the local research queue export
tool added in WP65. It explains what the tool does, what it does not do, how
to run it, how to read its output, and what conclusions are forbidden.

The tool turns an already-prepared WP64 research queue object (or a list of
local market context dicts) into a local morning briefing — a JSON or Markdown
file that a human can read. The human then decides what markets to research
next. The tool does not decide what to trade.

Plain analogy:

> WP64 built the analyst desk tray.
> WP65 prints the tray into a morning briefing.
> A human reads the briefing and decides what to investigate.

---

## 1. Advisory Notice

**This tool produces advisory-only output. It is not a trading signal, not an
expected return estimate, not position sizing advice, and not an execution
instruction. Human review is required before any use of the output.**

**FORBIDDEN INTERPRETATIONS: Do not interpret any field, bucket, rank, score,
flag, or section in this briefing as a trading signal, buy/sell recommendation,
expected return, position size, execution instruction, or indication of any
actionable research conclusion.**

---

## 2. Required Preconditions

Before using this tool:

1. You have a local JSON file containing either:
   - a list of prepared market context dicts (produced by the WP51–WP63
     feature extraction pipeline), or
   - an already-built `LOCAL_HUMAN_REVIEW_REPORT_V1` object (produced by
     `build_local_human_review_report` from WP64).
2. The JSON file is under an ignored local path (e.g. `local_data/`).
3. You are not relying on the tool for trading decisions.
4. You understand the non-signal boundary described in Section 10 below.

---

## 3. Example Commands

### Generate a Markdown briefing to stdout

```bash
python tools/research_queue/local_research_queue_export.py \
    --input local_data/example/research_queue_input.json \
    --format markdown
```

### Generate a JSON export to stdout

```bash
python tools/research_queue/local_research_queue_export.py \
    --input local_data/example/research_queue_input.json \
    --format json
```

### Save Markdown output to a local ignored file

```bash
python tools/research_queue/local_research_queue_export.py \
    --input local_data/example/research_queue_input.json \
    --format markdown \
    --output local_data/research_queue_exports/briefing_2026_06_11.md
```

### Override generated-at timestamp (for deterministic review)

```bash
python tools/research_queue/local_research_queue_export.py \
    --input local_data/example/research_queue_input.json \
    --format markdown \
    --generated-at-utc 2026-06-11T09:00:00+00:00
```

### Limit output to top 10 queue items

```bash
python tools/research_queue/local_research_queue_export.py \
    --input local_data/example/research_queue_input.json \
    --format markdown \
    --max-items 10
```

---

## 4. Supported Flags

| Flag | Required | Description |
|---|---|---|
| `--input <path>` | Yes | Local JSON input file path. |
| `--format json\|markdown` | No (default: json) | Output format. |
| `--output <path>` | No | Local output file. Defaults to stdout. |
| `--generated-at-utc <iso-ts>` | No | Override generated_at_utc field. |
| `--max-items <n>` | No | Cap total queue items in output. |

---

## 5. Input Expectations

The tool reads only the file you pass via `--input`. It does not scan
directories, fetch remote data, or read credentials.

Accepted input shapes:

1. **List of market context dicts** — any list of dicts produced by the WP51–
   WP63 `extract_market_research_priority_context` pipeline. The tool calls
   `build_local_human_review_report` internally to build the queue.

2. **LOCAL_HUMAN_REVIEW_REPORT_V1 object** — a dict with
   `"report_type": "LOCAL_HUMAN_REVIEW_REPORT_V1"` already built by WP64.
   The tool passes it through directly, applying any flag overrides.

The tool rejects:
- missing or unreadable files;
- non-JSON input;
- JSON that is neither a list nor a recognized report object;
- unsupported format strings;
- output paths under tracked source/test/docs directories.

---

## 6. Output Expectations

### Default (stdout)

Output is written to stdout. You can redirect it:

```bash
python tools/research_queue/local_research_queue_export.py ... > briefing.md
```

### --output flag

If `--output` is passed, the tool writes to the explicit path and prints a
confirmation line to stderr. The parent directory is created if needed.

Recommended output location (git-ignored):

```
local_data/research_queue_exports/
```

Do not pass output paths under `src/`, `tests/`, `docs/`, `tools/`, or
`.github/`. The tool rejects these with exit code 2.

---

## 7. How To Read Queue Buckets

The output groups markets into five buckets in priority order:

| Bucket | Meaning |
|---|---|
| **REVIEW_FIRST** | Acceptable data quality, highest research priority score. Human review recommended next. |
| **MANUAL_SOURCE_REVIEW_REQUIRED** | Resolution ambiguity or source hierarchy requires manual human source review before any use. |
| **REVIEW_LATER** | Lower research priority score or data warnings, but not blocked. Review after REVIEW_FIRST. |
| **DATA_QUALITY_BLOCKED** | Failing data quality, stale input requiring recapture, missing critical data, or absent provenance. Requires data recapture before human review. |
| **DEPRIORITIZED** | Insufficient metadata for meaningful human review at this time. |

Bucket assignment is advisory-only. The bucket does not tell you which market
is worth researching for investment purposes. It tells you which markets have
better data quality and metadata completeness for human research triage.

---

## 8. What The Output Does Not Mean

The output does not mean:

- Any market is worth buying or selling.
- Any market has a predictable outcome.
- Any market has an exploitable price discrepancy.
- Any score represents expected profit or return.
- Any `REVIEW_FIRST` market should be acted on immediately.
- Any flag or warning implies a definite data problem in the original source.

The output is a human research triage aid. It helps a human decide what to
look at next. All conclusions require human review and independent verification.

---

## 9. Safe Manual Review Workflow

1. Run the export command with your local input.
2. Read the Queue Summary section to understand the distribution.
3. Check Global Warnings for any data-quality issues.
4. Start with `REVIEW_FIRST` markets. Review the `review_reasons` and
   `blocking_or_caution_flags` for each. Investigate the underlying data
   manually.
5. Review `MANUAL_SOURCE_REVIEW_REQUIRED` markets for source and resolution
   ambiguity issues.
6. Skip `DATA_QUALITY_BLOCKED` markets until data recapture is complete.
7. Record any conclusions in a separate approved work package.
8. Do not act on any market based solely on its queue position or score.

---

## 10. Non-Signal Boundary

This tool enforces the same non-signal boundary as WP64.

The following are explicitly forbidden as output interpretations:

- trading signal;
- expected return;
- position sizing;
- buy or sell recommendation;
- execution instruction;
- entry or exit point;
- price edge or arbitrage indication;
- fill probability or slippage estimate.

The tool output is for human research triage only. ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED.

---

## 11. Forbidden Interpretations

Do not use this tool output to:

- justify a trade or position;
- configure a bot or automated strategy;
- claim a market has a research edge or predictable outcome;
- produce a paper or live trading signal;
- train or evaluate a machine learning model without further review;
- replace independent human judgment on market data quality.

---

## 12. Troubleshooting

### Exit code 1

Input validation failure. Check:
- Does the `--input` file exist?
- Is it valid JSON?
- Is it a list or a `LOCAL_HUMAN_REVIEW_REPORT_V1` dict?
- Is `--format` one of `json` or `markdown`?
- Is `--generated-at-utc` a valid ISO timestamp?

### Exit code 2

Unsafe output path. Check:
- Does `--output` point outside tracked directories?
- Use `local_data/research_queue_exports/` instead.

### Empty queue sections

If all markets end up in `DATA_QUALITY_BLOCKED` or `DEPRIORITIZED`, your input
data likely has quality gate failures or missing metadata. Recapture snapshots
or update metadata before running the export again.

---

## 13. What This Tool Does Not Do

This tool does not:

- fetch data from any network endpoint;
- read credentials, `.env` files, or wallet files;
- schedule itself to run automatically;
- write to a database or dashboard;
- push notifications or messages;
- integrate with any advisory consumer or bot runtime;
- add a trading strategy or signal;
- modify scores or weights from the WP49 scorer;
- create or modify any tracked source, test, or docs file.

The tool is local/offline/read-only/manual/explicit only.

---

## 14. No Network / No Credentials / No Scheduler / No Trading

- **Network**: no network access. The tool reads only the local file you provide.
- **Credentials**: no credentials, API keys, private keys, or `.env` files are
  read, required, or supported.
- **Scheduler**: no scheduler, daemon, cron, or bot loop. You invoke the tool
  manually each time you need a briefing.
- **Trading**: the tool produces no trading signals, executes no orders, and
  has no paper or live trading behavior.

---

## 15. Related Docs

- `src/data_layer/market_research_priority_review_queue.py` — WP64 in-memory
  queue and report builder (produces the objects this tool consumes).
- `docs/market_research_priority_scoring_layer.md` — scoring layer design and
  status.
- `docs/market_research_priority_scoring_output_contract.md` — output contract.
- `docs/research_data_foundation_direction.md` — research data direction lock.
- `tools/research_queue/local_research_queue_export.py` — this tool's source.
- `tests/tools/research_queue/test_local_research_queue_export.py` — focused
  tests.
