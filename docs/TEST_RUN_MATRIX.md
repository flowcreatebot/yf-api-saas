# Test Run Matrix

This project now supports marker-driven test lanes to make quality gates explicit and auditable.

## Markers

Defined in `pytest.ini`:

- `unit` — fast deterministic logic tests
- `integration` — API/service integration tests
- `e2e` — end-to-end product flows
- `deployed` — deployed-environment verification checks
- `billing` — checkout/webhook/subscription related tests
- `critical` — must-pass customer-critical flows

## Matrix runner

Use:

```bash
./scripts/run_test_matrix.sh
```

Environment knobs:

- `PYTHON_BIN` (default: `python3`)
- `RUN_DEPLOYED=1` to include deployed critical lane (`tests/test_deployed_smoke.py`)

The script writes evidence reports:

- timestamped: `reports/test_matrix_YYYY-MM-DD_HH-MM-SS.txt`
- latest pointer: `reports/latest_test_matrix.txt`

## Lanes

1. `critical-integration`
   - `-m "integration and critical and not deployed"`
2. `billing-integration`
   - `-m "integration and billing and not deployed"`
3. `critical-deployed` (optional)
   - `-m "deployed and critical" tests/test_deployed_smoke.py`

## CI wiring

GitHub Actions `test` job runs the non-deployed matrix each push/PR and uploads `reports/latest_test_matrix.txt` as `test-matrix-report` artifact.
