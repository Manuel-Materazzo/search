# AGENTS.md — SearXNG

## Build & Run
- Install: `make install` (creates virtualenv in `local/py3`)
- Run dev server: `make run`
- Full test suite: `make test` (yamllint, black, pyright, pylint, unit, robot, rst, shell)
- Unit tests only: `python -m nose2 -s tests/unit` (activate venv first, or `make test.unit`)
- Single test: `python -m nose2 -s tests/unit tests.unit.<module>.<Class>.<method>` (e.g. `tests.unit.test_utils.TestUtils.test_something`)
- Lint: `make test.pylint` | Format: `make format` (black + shfmt)
- Type check: `make test.pyright` (uses pyrightconfig.json)

## Architecture
- **Python 3.10+ / Flask** metasearch engine. Entry point: `searx/webapp.py`. Settings: `searx/settings.yml`.
- `searx/engines/` — one module per search engine (scraper). `searx/plugins/` — plugins. `searx/search/` — search orchestration.
- `searx/botdetection/`, `searx/limiter.py` — rate limiting. `searx/network/` — HTTP client layer. `searx/result_types/` — result models.
- Frontend: Jinja2 templates (`searx/templates/`) + static assets built via Node (`client/`). Theme: `simple`.
- Tests: `tests/unit/` (nose2), `tests/robot/` (Selenium). Data files: `searx/data/`.
- Storage: SQLite (`searx/sqlitedb.py`), optional Valkey/Redis (`searx/valkeydb.py`).

## Code Style
- Formatter: **black** (default settings). Linter: **pylint** (`.pylintrc`). Type checker: **pyright** (`pyrightconfig.json`).
- Imports: stdlib → third-party → local (`searx.*`). Use absolute imports.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes. Engine modules are lowercase with underscores.
- All files carry `# SPDX-License-Identifier: AGPL-3.0-or-later` header.
