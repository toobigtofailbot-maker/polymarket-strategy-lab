# tools/polymarket

Manual read-only development tools for Polymarket public data access.

## Contents

- `readonly_smoke_test.py` — Optional manual smoke test for the read-only public adapter.

## Important

These tools are for manual use only. They are not run by automated tests. They require explicit `--allow-network` to make any network call. They perform GET-only requests to public endpoints. They use no credentials.

## Usage

```
python tools/polymarket/readonly_smoke_test.py --help
python tools/polymarket/readonly_smoke_test.py --allow-network --markets-limit 3
```

Without `--allow-network` the script exits immediately with no network calls.
