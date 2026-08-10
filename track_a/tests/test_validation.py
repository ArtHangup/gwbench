"""The offline validation battery: the pipeline proves the DVs discriminate
between architectures by construction, before any model is involved."""

from conflict.validation import run_validation


def test_validation_passes_on_a_small_battery():
    report = run_validation(n_per_cell=2)
    assert report["checks"], "no checks ran"
    failures = {name: ok for name, ok in report["checks"].items() if not ok}
    assert not failures
    # 4 domains x 2 kinds x n x 3 architectures
    assert report["n_trials"] == 4 * 2 * 2 * 3
    assert "gwt/novel" in report["table"]


def test_validation_report_is_json_serializable():
    import json

    report = run_validation(n_per_cell=1)
    json.dumps(report)
