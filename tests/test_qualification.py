import json

from mneme.hosts import FakeHost
from mneme.qualification import qualify


def test_fake_qualification_report_and_artifact():
    report = qualify(FakeHost())
    artifact = report.to_dict()
    json.dumps(artifact)
    assert artifact["qualification_version"] == "0.1"
    assert artifact["summary"]["overall"] == "pass"
    assert artifact["summary"]["structured_parse_success"] == 3
    assert "MNEME host qualification" in report.text()


def test_failure_is_reported_not_leaked():
    report = qualify(FakeHost(fail=True))
    assert report.summary["overall"] == "attention_required"
    assert any(item["status"] == "error" for item in report.tests)
