# Agent Exchange Request

Target:
Human

Sender:
Codex

Created at:
2026-09-01T00:05:00Z

Status:
NEEDS_HUMAN_APPROVAL

Objective:
Enable a real Databento online cost preflight after a separate contract/stype decision, without writing API keys to repo files or approving any data purchase.

Scope:
- `tools/preflight_databento_gc_vendor.py`
- `configs/data/databento-gc-vendor-preflight.yaml`
- `schemas/databento_gc_vendor_preflight.schema.json`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`

Required inputs:
- First decide which Databento symbol mode should be used for GC cost preflight: dated raw symbol, parent futures, or continuous front month.
- Set `DATABENTO_API_KEY` in the local shell environment only.
- Do not put the API key in `.env`, markdown files, YAML files, logs, screenshots, or `agent-exchange/`.

Contracts:
- The preflight may call Databento metadata/symbology/get_cost only after the contract/stype decision exists.
- The preflight must not download market data.
- The preflight must not approve spend.
- The output is a blocked planning report, not an order-flow/options source decision.

Non-negotiables:
- no API key in repo files
- no Databento data download or purchase
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:
- After selecting contract/stype mode and setting the environment variable, ask Codex to run the online cost preflight with the decision file.
- Codex will inspect the redacted output and decide whether to request new human decisions for order-flow/options.

Verification commands:
- `python tools/preflight_databento_gc_vendor.py --online-cost-estimate`
- `python tools/validate_phase21.py`

Out of scope:
- Do not paste the API key into chat again.
- Do not approve `ORDER_FLOW_SOURCE_DECISION` or `OPTIONS_SOURCE_DECISION` from this request.
- Do not approve MBO purchase.

Notes:
PowerShell setup example for the current terminal only:

1. Choose one mode from `configs/data/databento-gc-contract-stype-decision-template.yaml`.
2. Set the key in the current terminal only:

```powershell
$env:DATABENTO_API_KEY = "<your-key-here>"
```

3. Ask Codex to create/validate the selected decision file before the online call.

The key must be provided by the human locally; Codex will not reuse keys pasted in chat.
