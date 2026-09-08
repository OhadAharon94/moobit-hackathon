# Q-ERA implementation — corrected setup

This is the versioned setup companion for the frozen v1.1 scientific plan. It
corrects invocation paths without changing the original Markdown artifact.

## Repository-root setup

Use these commands when the current directory contains `pyproject.toml`, `qera/`,
and `tests/`.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv-classiq
& '.\.venv-classiq\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv-classiq\Scripts\python.exe' -m pip install -e '.[dev]'
& '.\.venv-classiq\Scripts\python.exe' -m pytest 'tests'
```

### macOS/Linux

```bash
python3.12 -m venv .venv-classiq
source .venv-classiq/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest tests
```

## Wrapper-workspace layout

In a workspace where the repository content is under `implementation/`, first
enter that directory and then use the repository-root commands:

```powershell
Set-Location '.\implementation'
```

Classiq authentication remains a separate interactive step:

```powershell
& '.\.venv-classiq\Scripts\python.exe' -c "import classiq; classiq.authenticate()"
```

New synthesis manifests cryptographically bind each `.qprog` to its objective,
weights, energy scaling, depth, and source/config provenance. Legacy unbound
circuits must be re-synthesized before a new execution; saved raw samples remain
readable and unchanged.
