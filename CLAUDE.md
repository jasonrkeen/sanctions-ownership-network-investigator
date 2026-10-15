> This file mirrors `.github/copilot-instructions.md`; keep both in sync when either changes.

# CLAUDE.md — Sanctions Ownership Network Investigator

## Purpose
Source-backed sanctions screening and corporate ownership network investigation MVP.

## Tech stack
- Python; dependencies in `requirements.txt`
- Imports observed: `reportlab`, `streamlit`

## Folder structure
- `.github/` (5 files)
- `data/` (5 files)
- `docs/` (16 files)
- `outputs/` (1 files)
- `scripts/` (4 files)
- `sql/` (1 files)
- `src/` (17 files)
- `tests/` (12 files)
- `.env.example`
- `CHANGELOG.md`
- `CITATION.cff`
- `CONTRIBUTING.md`
- `Dockerfile`
- `README.md`
- `SECURITY.md`
- `app.py`
- `docker-compose.yml`
- `main.py`
- `pyproject.toml`
- `requirements.txt`

## Setup, run, test
Commands documented in README.md (referenced files exist):
```bash
python main.py --mode sample --query "Harbor Meridian Trading LLC"
python -m venv .venv
python -m pip install --upgrade pip
pip install -e ".[dashboard,pdf]"
streamlit run app.py
python main.py --mode live --query "ENTITY NAME"
python main.py --mode live --skip-download --query "ENTITY NAME"
python main.py --mode live --gleif-enrich --query "JPMorgan Chase & Co."
python main.py --mode live --gleif-enrich --country US --query "ENTITY NAME"
python main.py --mode live --gleif-enrich --gleif-lei "LEI_HERE" --query "ENTITY NAME"
```
- Tests: 12 Python test file(s) under `tests/`; framework appears to be pytest. Add/update tests with any logic change.
- CI workflows exist in `.github/workflows/`; keep them passing.

## Conventions observed
- Functions use type hints; keep annotating new code.
- Uses `dataclasses` for structured config/results.
- Config lives in: `docker-compose.yml`, `pyproject.toml`; avoid hardcoding parameters elsewhere.
- Credentials/API keys come from environment variables (see `.env.example`); never hardcode them.
- Raw data (`data/raw/`) is gitignored; download/fetch it via the pipeline, do not commit it.
- Public data sources referenced: SEC, OFAC.
- Write paths relative to the repo root (no absolute local paths).

## Output artifacts
- Generated outputs go to `outputs/`.
- A PDF report is produced with `reportlab`; keep it in sync with model changes.
- Streamlit dashboard: `app.py` (run with `streamlit run <file>`).

## Guardrails
- Never commit secrets, API keys, tokens, or `.env` files.
- Do not commit large raw datasets or binaries; keep data fetched or documented with its source.
- Keep analysis source-backed: cite data sources and assumptions; label scenario/forecast outputs as model estimates, not facts.
- Preserve reproducibility: no unseeded randomness, no hidden manual steps.
