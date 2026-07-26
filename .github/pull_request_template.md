## Summary

Describe the problem and the focused change.

## Analytical and source boundary

Explain any effect on identity resolution, designation screening, ownership,
contextual relationships, source provenance, workflow, or analyst judgment.

## Validation

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python -m compileall -q main.py app.py src tests scripts`
- [ ] `python scripts/check_publication.py`
- [ ] Fictional demonstration run when behavior changes
- [ ] Documentation and changelog updated when claims or interfaces change

## Safety and release checks

- [ ] No credentials, `.env`, nonpublic data, generated cases, SQLite databases,
      raw OFAC downloads, or virtual environments are included
- [ ] New outputs preserve evidence, uncertainty, and human-review boundaries
- [ ] Known limitations and follow-up work are described
