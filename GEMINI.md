# SearXNG - Privacy-respecting metasearch engine

SearXNG is a privacy-respecting, hackable metasearch engine. It aggregates results from multiple search engines without tracking or profiling users.

## Project Overview

- **Architecture:** Metasearch engine that proxies requests to various search engines (engines are defined in `searx/engines/`).
- **Backend:** Python 3 with [Flask](https://flask.palletsprojects.com/).
- **Frontend:**
  - `client/simple`: The default theme.
  - `client/modern`: A more modern, responsive theme.
  - Both themes use [Vite](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/), and [Less](https://lesscss.org/).
- **Data & Caching:** Uses [Valkey](https://valkey.io/) (formerly Redis) for caching, rate limiting, and metrics.
- **Configuration:** Main configuration is in `searx/settings.yml`.

## Building and Running

The project uses a `Makefile` that wraps a comprehensive `./manage` script.

### Prerequisites
- Python 3.x
- Node.js (for theme development)
- Valkey/Redis (optional for local dev, but recommended)

### Key Commands

- **Initial Setup:**
  ```bash
  make install
  ```
- **Run Developer Instance:**
  ```bash
  make run
  # Or directly via manage:
  ./manage webapp.run
  ```
- **Build Frontend Themes:**
  ```bash
  make themes.all
  ```
- **Clean Workspace:**
  ```bash
  make clean
  ```

## Testing and Quality Control

SearXNG maintains high code quality standards through extensive linting and testing.

### Running Tests
- **All Tests:** `make test`
- **Unit Tests:** `./manage test.unit`
- **Robot (Integration) Tests:** `./manage test.robot`
- **Shell Script Tests:** `make test.shell`

### Linting and Formatting
- **Python Linting:** `make test.pylint` and `make test.pyright` (using basedpyright)
- **Python Formatting:** `make format.python` (using [Black](https://github.com/psf/black))
- **Frontend Linting:** `make themes.lint` (using [Biome](https://biomejs.dev/) and [Stylelint](https://stylelint.io/))
- **Frontend Formatting:** `make themes.fix`
## Development Conventions

- **Tooling:** Always prefer using `./manage` or `make` for common tasks as they handle virtualenvs and environment variables correctly.
- **Python Style:** Follow PEP 8 and PEP 20. Adhere to the KISS principle (Keep It Simple, Stupid).
- **Themes:** Theme source files are in `client/[theme]/src`. Compiled assets are served from `searx/static/themes/[theme]`.
- **Engines:** New engines should be added as Python modules in `searx/engines/` and configured in `searx/settings.yml`.
- **Documentation:** Documentation is built using [Sphinx](https://www.sphinx-doc.org/). Run `make docs` to build.
- **Translations:** Managed via WebLate. Local extraction can be done with `./manage pybabel`.

## Directory Structure Highlights

- `searx/`: Core Python application logic.
- `client/`: Frontend theme source code.
- `tests/`: Unit and integration tests.
- `utils/`: Helper scripts and Makefile includes.
- `manage`: The central management script for dev tasks.
