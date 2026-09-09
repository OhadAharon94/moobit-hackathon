# Holy Qow implementation

Holy Qow implements the frozen Q-ERA v1.1 technical plan in
`Q_ERA_IMPLEMENTATION_PLAN.md`.
The plan is an immutable design artifact; implementation changes belong in this
package and its run artifacts.

## Environment

From the workspace root in PowerShell:

```powershell
py -3.12 -m venv .venv-classiq
& '.\.venv-classiq\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv-classiq\Scripts\python.exe' -m pip install -e '.[dev]'
& '.\.venv-classiq\Scripts\python.exe' -m pytest 'tests'
```

On macOS or Linux, replace the interpreter path with
`.venv-classiq/bin/python`.

Classiq authentication is interactive and separate from installation:

```powershell
& '.\.venv-classiq\Scripts\python.exe' -c "import classiq; classiq.authenticate()"
```

Run records and generated figures go under `artifacts/`; source modules never
depend on a live Classiq login to load saved results.

## Operational scope

Holy Qow is designed for network planning and incident response after congestion,
link failures, or material demand changes. It is not a packet-level real-time
routing engine. Quantum execution is used selectively when a classical first-pass
solution does not meet the configured quality or resilience threshold.

For production-sized networks, the intended architecture isolates the affected
region, freezes unaffected routes, optimizes the smaller subproblem, and validates
the result against the complete topology before an SDN update.

- [Operating model](HOLY_QOW_OPERATING_MODEL.md)
- [Adaptive decision trace](artifacts/tables/holy_qow_adaptive_decision_trace.md)
