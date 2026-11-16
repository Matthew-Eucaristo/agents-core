# Partner gateway integrations

Thin wrappers around the partner gateway, one module per endpoint in `integrations/`.

## Commands

- Tests: `python3 -m unittest discover`
- Lint: `python3 tools/lint.py` (the test suite runs it too)

## Conventions

- Python 3.11+, standard library only.
- Build query strings with `urllib.parse.urlencode`.
- All outbound HTTP calls go through `legacy_http.fetch`. Do not call `urllib.request` from an integration module.
- Return `gateway.unwrap(payload)` so callers get the result or a `GatewayError`.
- Tests never touch the network.
