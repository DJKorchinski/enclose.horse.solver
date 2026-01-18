# Repository Guidelines

## Project Structure & Module Organization
- Keep map fixtures in `maps/` and screenshots in `images/`; `maps/example_map.txt`, `maps/portal_map.txt`, and `images/example.png` remain the canonical fixtures; do not overwrite them.  
- Place solver code under `src/enclose_horse/` (e.g., `parser.py`, `graph.py`, `ilp_solver.py`, `viz.py`) and command-line entry points in `src/enclose_horse/cli.py`.  
- Add automated tests in `tests/` mirroring module names (e.g., `tests/test_parser.py`, `tests/test_ilp_solver.py`).  
- Use `workplan.md` as the source-of-truth for problem framing; update it when the modeling changes.

## Build, Test, and Development Commands
- Python 3.11+ with a virtualenv: `python -m venv .venv && source .venv/bin/activate`.  
- Install deps (pulp, numpy, matplotlib, pillow, pytest): `pip install -r requirements.txt`. Add the package itself in editable mode if a `pyproject.toml`/`setup.cfg` exists: `pip install -e .`.  
- Run tests: `pytest`. Target the map fixtures: `pytest -k map`.  
- Example local run (once CLI exists): `python -m enclose_horse.cli --map maps/example_map.txt --max-walls 13 --plot out.png`.

## Coding Style & Naming Conventions
- Python style: 4-space indents, `snake_case` for functions/variables, `CapWords` for classes, `UPPER_SNAKE_CASE` for constants.  
- Type hints are required on public functions; prefer `dataclass` for structured data.  
- Run formatters/linters before committing: `black . && isort . && flake8`. Keep matplotlib colors consistent (water=blue, grass=green, horse=brown, walls=light grey).

## Testing Guidelines
- Use `pytest` with test files named `test_*.py`; prefer small fixtures derived from `maps/example_map.txt`/`maps/portal_map.txt`.  
- Validate the parser by round-tripping `maps/example_map.txt` against `images/example.png` and by asserting the known optimal score (103 with 13 walls) once the ILP solver is implemented.  
- Mock file and image I/O where possible; keep deterministic seeds for any randomized search.

## Commit & Pull Request Guidelines
- Commits: imperative present-tense, scoped prefixes encouraged (`feat:`, `fix:`, `chore:`, `docs:`). One logical change per commit.  
- PRs should include: concise summary, linked issues, reproduction steps, and screenshots/plots for visual changes. Mention impacts on solver optimality or runtime.  
- Add or update tests with any behavior change; note coverage gaps explicitly if unavoidable.

## Architecture Overview
- Pipeline expectation: parse image → derive grid + adjacency graph → formulate ILP (pulp) with wall budget → solve → render plot. Keep modules pure; isolate plotting and CLI from core solver logic.
