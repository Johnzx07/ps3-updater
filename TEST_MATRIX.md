# TEST_MATRIX.md

# Test Matrix

This file defines verification coverage expected for the project.

Populate concrete rows from verified project behavior and acceptance criteria.

## Completion-Critical Tests

| Area | Test | Required Before Completion? | Command / Method | Last Verified Result |
|---|---|---:|---|---|
| Syntax / Build | `ps3_updater.py` compiles | Yes | `python -m py_compile ps3_updater.py` | PASS (exit 0, 2026-09-09) |
| Core workflow | GUI end-to-end: search → ordered rows → live progress → bar fills to max → ✓ done ×N → "Done. N update(s)" announcement; error branches (`no updates`, `error:`); stop mid-download (✗ row, pump survives) | Yes | `python gui_selftest.py` | PASS (exit 0, 2026-09-09 — after UI pass) |
| Error handling | `read_games_yml()`: flat + nested formats, name derivation, missing-file error, empty file | Yes | `python test_games_yml.py` | PASS (exit 0, 2026-09-09 — after UI pass) |
| Regression coverage | Core logic (lines 1–321: config, lookup, parser, SHA-1, download, plan) and CLI byte-identical to pre-UI snapshot; `--help` runs | Yes | line-diff vs pre-change snapshot + `python ps3_updater.py --help` | PASS (exit 0, 2026-09-09) |

## User-Facing Workflow Tests

| Workflow | Happy Path | Error Path | Cancellation / Recovery | Notes |
|---|---:|---:|---:|---|
| Single serial search → download in order | ✓ (gui_selftest phase 2, faked network) | ✓ (`no updates`, `error:` rows — phase 4) | ✓ (Stop mid-download — phase 5) | Deterministic; downloads to temp dir |
| Library scan (games.yml) | Parser covered by test_games_yml.py | Missing file → error dialog path in GUI | n/a | Scan→search_many wiring exercised via same queue contract |

## Platform / Environment Matrix

| Platform / Environment | Supported? | Verified? | Notes |
|---|---:|---:|---|
| Windows 10/11 + Python 3.9+ (tkinter, requests, PyYAML) | Yes | Partially | GUI self-test executed on this Windows host; clean-machine install not re-verified in this pass |

## Dependency / Setup Tests

| Check | Required? | Method | Result |
|---|---:|---|---|
| Documented install command succeeds in a clean environment | Before release | `python -m pip install requests PyYAML` (README) | Not re-run in this pass (deps already present); no dependency changes made |
| Required dependencies match manifests | Yes | requirements.txt vs imports (`requests`, `yaml`) | PASS — unchanged by UI pass, both still the only third-party imports |

## Network / External-Service Tests

Deterministic tests should not depend entirely on external services.

| Service | Deterministic/Faked Test | Optional Real Smoke Test | Notes |
|---|---:|---:|---|
| Sony PSN update endpoints (`a0.ww.np.dl.playstation.net`, CDN) | ✓ gui_selftest fakes `fetch_updates`/`download_pkg`; core logic unchanged and byte-identical to the previously verified state | Optional: `python ps3_updater.py --cli BLUS30675 -o PS3Updates` | Live smoke not re-run in this pass (no core changes) |

## Release Verification

Before release, verify as applicable:

- [ ] compile/build passes
- [ ] automated tests pass
- [ ] GUI/runtime smoke test passes
- [ ] core user workflow passes
- [ ] failure paths pass
- [ ] clean installation is verified or limitation is documented
- [ ] dependency manifests match implementation
- [ ] documentation matches final behavior
- [ ] release artifacts were generated from the final intended source state
- [ ] final artifacts were tested

## Rule

Do not replace deterministic automated tests with live network tests.

Do not report a test as PASS unless it was actually executed or the evidence explicitly supports the claim.
