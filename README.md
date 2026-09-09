# Holy Qow implementation

Holy Qow implements the frozen Q-ERA v1.1 technical plan in
`Q_ERA_IMPLEMENTATION_PLAN.md`.
The plan is an immutable design artifact; implementation changes belong in this
package and its run artifacts.

## Environment

From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv-classiq
& '.\.venv-classiq\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv-classiq\Scripts\python.exe' -m pip install -e '.[dev]'
& '.\.venv-classiq\Scripts\python.exe' -m pytest 'tests'
```

From the repository root on macOS or Linux:

```bash
python3.12 -m venv .venv-classiq
./.venv-classiq/bin/python -m pip install --upgrade pip
./.venv-classiq/bin/python -m pip install -e '.[dev]'
./.venv-classiq/bin/python -m pytest tests
```

Classiq authentication is interactive and separate from installation:

```powershell
& '.\.venv-classiq\Scripts\python.exe' -c "import classiq; classiq.authenticate()"
```

Run records and generated figures go under `artifacts/`; source modules never
depend on a live Classiq login to load saved results.

## Operational scope

Holy Qow is designed for network-planning experiments and incident-response
decision support after congestion or material demand changes. It is not a
packet-level real-time routing engine. The experimental orchestration wrapper can
invoke a quantum candidate when a classical first pass misses a configured
resilience threshold, but keeps the valid classical candidate unless the quantum
candidate is valid and scores better under the frozen comparison rule.

Regional decomposition and SDN integration are proposed future architecture, not
features demonstrated by this repository. The current evidence favors static
multi-environment classical routing; selective quantum escalation has not shown a
route-quality advantage and is disabled unless explicitly configured by a caller.

- [Operating model](HOLY_QOW_OPERATING_MODEL.md)
- [Adaptive decision trace](artifacts/tables/holy_qow_adaptive_decision_trace.md)
