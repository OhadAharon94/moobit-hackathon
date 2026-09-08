# Q-ERA implementation

This directory implements the frozen v1.1 plan in `Q_ERA_IMPLEMENTATION_PLAN.md`.
The plan is an immutable design artifact; implementation changes belong in this
package and its run artifacts.

## Environment

From the workspace root in PowerShell:

```powershell
& '.\.venv-classiq\Scripts\python.exe' -m pip install -e '.\implementation[dev]'
& '.\.venv-classiq\Scripts\python.exe' -m pytest '.\implementation\tests'
```

Classiq authentication is interactive and separate from installation:

```powershell
& '.\.venv-classiq\Scripts\python.exe' -c "import classiq; classiq.authenticate()"
```

Run records and generated figures go under `artifacts/`; source modules never
depend on a live Classiq login to load saved results.

