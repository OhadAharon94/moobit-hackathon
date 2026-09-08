import json

from qera.evaluate import Evaluator
from qera.records import write_json


def test_actual_evaluation_record_serializes_mapping_proxies(tmp_path) -> None:
    evaluation = Evaluator().evaluate((0, 0, 0, 0), "nominal")
    path = write_json(tmp_path / "evaluation.json", evaluation)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["scenario"] == "nominal"
    assert payload["loads"]["('S0', 'U')"] == 4.0
    assert payload["utilization"]["('U', 'M1')"] == 8.0 / 6.0
