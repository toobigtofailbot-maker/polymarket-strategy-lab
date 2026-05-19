# tools/polymarket

Manual read-only development tools for Polymarket public data access.

## Contents

- `readonly_smoke_test.py` — Optional manual smoke test for the read-only public adapter.
- `capture_market_snapshots.py` — Manual read-only snapshot capture tool. Writes market metadata and optional order-book snapshots to `local_data/polymarket/snapshots/`.

## Important

These tools are for manual use only. They are not run by automated tests. They require explicit `--allow-network` to make any network call. They perform GET-only requests to public endpoints. They use no credentials. They do not place, cancel, sign, or simulate orders. They have no trading authority.

No automated polling is added by any tool in this directory. Each tool runs once and exits.

Snapshot files written by `capture_market_snapshots.py` go to `local_data/polymarket/snapshots/` which is git-ignored. Snapshot files must never be committed.

Rate-limit policy for public Polymarket endpoints is not confirmed (WP8-D002 OPEN). Do not use these tools for automated or frequent scanning.

## Usage

```
python tools/polymarket/readonly_smoke_test.py --help
python tools/polymarket/readonly_smoke_test.py --allow-network --markets-limit 3
```

```
python tools/polymarket/capture_market_snapshots.py --help
python tools/polymarket/capture_market_snapshots.py --allow-network --markets-limit 3
python tools/polymarket/capture_market_snapshots.py --allow-network --markets-limit 3 --include-order-books --max-order-books 2
```

Without `--allow-network` each script exits immediately with no network calls.
