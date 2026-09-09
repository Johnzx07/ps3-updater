# Contributing

This is a small personal project. Contributions are welcome but kept simple on
purpose — there is no formal process, CI pipeline, or branch-protection setup.

## How to contribute

1. Fork the repository and make your change on a feature branch.
2. Keep changes focused: this app intentionally does one thing (find + download
   PSN title updates for RPCS3 games). Avoid redesigns or scope creep.
3. Run the checks below before opening a pull request.

## Checks to run locally

```bat
python -m py_compile ps3_updater.py gui_selftest.py test_games_yml.py
python gui_selftest.py
python test_games_yml.py
```

- `gui_selftest.py` exercises the GUI logic headlessly (no display needed).
- `test_games_yml.py` is a deterministic parser test using throwaway temp dirs —
  it never touches a real RPCS3 install.

## Style

- Match the existing code: plain Python, no framework, stdlib + `requests` +
  PyYAML only. Do not add new third-party dependencies without strong reason.
- Keep user-facing messages clear and actionable (the launcher and error paths
  are designed so a non-expert can fix problems from the text alone).

## What we will not merge

- Changes that alter working download/progress behavior without a concrete bug.
- New dependencies, build systems, or packaging tooling for this small script.
- Anything requiring an account, login, or network service beyond Sony's public
  PSN update endpoints.
