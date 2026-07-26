# Release checklist

## Automated build

Always build the distributable archive with:

```powershell
python scripts\build_release.py
```

Do not use File Explorer's **Send to compressed folder** on the working
directory. That operation can include machine-specific environments and ignored
runtime data.

## Required validation

Run these commands from the project root:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py app.py src tests scripts
python scripts\check_publication.py
python main.py --mode sample --query "Harbor Meridian Trading LLC"
python scripts\build_release.py
```

## Archive requirements

The release ZIP must:

- Open without CRC errors
- Contain one top-level project directory
- Include source, tests, documentation, sample data, schemas, and configuration
  templates
- Retain `data/raw/ofac/.gitkeep` and `outputs/.gitkeep`
- Exclude all virtual environments
- Exclude `__pycache__`, `*.pyc`, and `*.egg-info`
- Exclude `.env` and local credentials
- Exclude downloaded OFAC data
- Exclude generated outputs and SQLite databases
- Exclude temporary rendering files and nested ZIP archives
- Include changelog, citation metadata, contribution and security policies,
  versioned release notes, and GitHub collaboration templates
- Pass the publication audit with synchronized project, package, citation, and
  model-card versions

## Local data preservation

Before replacing a working project folder, separately back up any live
investigations that must be retained:

```powershell
Copy-Item outputs outputs_backup -Recurse
```

Downloaded OFAC files and generated cases are intentionally not portable
release assets. Copying a release over the existing project without deleting
the project folder preserves them; a full folder replacement requires the
backup above.

## GitHub check

Before committing:

```powershell
git status --short
```

Confirm that no `.venv*`, `.env`, raw OFAC file, generated report, SQLite
database, package metadata, or ZIP archive appears in the staged changes.
