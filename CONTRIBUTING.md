# Contributing

Thank you for helping improve the Sanctions Ownership Network Investigator.
Contributions should preserve the project's evidence-first design and clear
boundary between system output, analyst judgment, and legal determinations.

## Development setup

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[all,dev]"
```

Run the validation suite before opening a pull request:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py app.py src tests scripts
python scripts\check_publication.py
python main.py --mode sample --query "Harbor Meridian Trading LLC"
```

## Contribution standards

- Add or update tests for behavior changes.
- Retain source references, evidence fields, and uncertainty in analytical
  outputs.
- Do not convert fuzzy scores into probability claims.
- Keep GLEIF accounting-consolidation relationships separate from percentage
  ownership.
- Keep analyst reviews and workflow changes append-only.
- Use fictional or public, authoritative data in tests and examples.
- Do not commit `.env`, credentials, downloaded OFAC files, generated case
  outputs, SQLite databases, or virtual environments.
- Update the model card, methodology, data dictionary, and changelog when a
  change affects their claims.

## Pull requests

Describe the analytical problem, implementation, evidence or source boundary,
tests performed, and known limitations. Small, reviewable pull requests are
preferred.

Run the clean release builder when changing packaging:

```powershell
python scripts\build_release.py
```

## Reporting security concerns

Do not place credentials, sensitive case data, or exploit details in a public
issue. Follow [SECURITY.md](SECURITY.md) instead.
