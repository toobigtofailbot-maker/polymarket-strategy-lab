# Official Client Read-Only Sandbox

## Purpose

This directory contains WP15 dev-only tooling for evaluating whether the current official Python V2 CLOB client candidate may be useful for public read-only market data in a future work package.

The sandbox has no runtime authority. It is not imported by `src/`, strategy code, execution code, risk code, storage code, dashboards, schedulers, bot loops, backtests, paper trading, or trade proposal paths.

## Boundaries

- The official client is not a project dependency.
- `.venv-official-client/` is an ignored local sandbox environment and must not be committed.
- No credentials, private keys, wallet keys, mnemonics, API keys, passphrases, or `.env` files are read.
- No authenticated client setup is allowed.
- No signing, order placement, order cancellation, buy, sell, submit, account, balance, open-order, or trade-history behavior is allowed.
- Network access is optional and requires `--allow-network`.
- Local sandbox output is allowed only under ignored sandbox output paths and only when an output flag is passed.

## Commands

Inspect safe defaults:

```powershell
python tools/polymarket/official_client_sandbox/setup_sandbox.py --help
python tools/polymarket/official_client_sandbox/verify_sandbox.py
python tools/polymarket/official_client_sandbox/readonly_public_probe.py --help
python tools/polymarket/official_client_sandbox/readonly_public_probe.py
```

Create the ignored sandbox virtual environment:

```powershell
python tools/polymarket/official_client_sandbox/setup_sandbox.py --create
```

Install the candidate into the sandbox only, with an explicit version:

```powershell
python tools/polymarket/official_client_sandbox/setup_sandbox.py --install-package --package py-clob-client-v2 --package-version <PINNED_VERSION>
```

Verify sandbox status without installing anything:

```powershell
python tools/polymarket/official_client_sandbox/verify_sandbox.py
```

Run offline package/interface inspection from the sandbox Python only:

```powershell
.venv-official-client\Scripts\python.exe tools/polymarket/official_client_sandbox/inspect_package.py
```

Run the optional public read-only network probe:

```powershell
.venv-official-client\Scripts\python.exe tools/polymarket/official_client_sandbox/readonly_public_probe.py --allow-network --markets-limit 3
```

If the package API shape does not expose a bounded public read-only method, the probe reports the mismatch and does not force authenticated behavior.
