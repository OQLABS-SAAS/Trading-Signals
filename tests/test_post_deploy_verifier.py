import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import verification.post_deploy_verifier as verifier


def _passing_bundle_text():
    return """
    async function showAlerts() { tgScanFeed; Telegram Signals; dvLoadScanAlerts(); }
    todayHorizon _todaySetHorizon >Daily< >Weekly< >Monthly<
    _dvBasketTotals totalCashIn totalRisk totalProfitTarget totalPositionValue
    Scale-out plan Entry Cash in controls lots
    account details syncing MT5 CONNECTED SYNCING
    status_message _dvHumanizeError o.status === 'failed'
    /api/performance/pnl No closed trades yet
    /api/mt5/state open positions Stress test
    """


def test_bundle_checks_pass_with_required_markers():
    results = verifier.evaluate_text_checks(_passing_bundle_text(), verifier.BUNDLE_CHECKS)
    assert {result.status for result in results} == {"pass"}


def test_bundle_checks_fail_when_marker_missing():
    results = verifier.evaluate_text_checks("todayHorizon", verifier.BUNDLE_CHECKS)
    failures = [result for result in results if result.status == "fail"]
    assert failures
    assert any(result.name == "today_horizon_selector" for result in failures)


def test_forbidden_mt5_unknown_marker_fails():
    text = _passing_bundle_text() + "MT5 UNKNOWN"
    results = verifier.evaluate_text_checks(text, verifier.BUNDLE_CHECKS)
    result = next(item for item in results if item.name == "no_bare_mt5_unknown")
    assert result.status == "fail"


def test_extract_cache_version():
    assert verifier.extract_cache_version("const CACHE_VER = 'dv-v20';") == "dv-v20"
    assert verifier.extract_cache_version('const CACHE_VER = "dv-v21";') == "dv-v21"


def test_service_worker_expected_cache_mismatch_fails():
    result = verifier.evaluate_service_worker(
        source_name="sw.js",
        sw_text="const CACHE_VER = 'dv-v20';",
        expected_cache="dv-v21",
    )
    assert result.status == "fail"
    assert "expected dv-v21" in result.evidence


def test_report_labels_mt5_and_auth_paths_as_blocked():
    report = verifier.build_report(
        base_url="https://example.test",
        bundle_source="local-html",
        bundle_text=_passing_bundle_text(),
        sw_source="local-sw",
        sw_text="const CACHE_VER = 'dv-v20';",
        expected_cache="dv-v20",
        timeout=1,
        include_live_endpoints=False,
    )
    statuses = {item["name"]: item["status"] for item in report["results"]}
    assert statuses["mt5_order_fill"] == "blocked"
    assert statuses["authenticated_money_path_walk"] == "blocked"
    assert statuses["live_endpoint_probe"] == "warn"
    assert report["summary"].startswith("pass_with_blockers")


def test_cli_json_local_bundle(tmp_path, capsys):
    bundle = tmp_path / "index.html"
    sw = tmp_path / "sw.js"
    bundle.write_text(_passing_bundle_text())
    sw.write_text("const CACHE_VER = 'dv-v20';")

    code = verifier.main(
        [
            "--local-bundle",
            str(bundle),
            "--local-sw",
            str(sw),
            "--expected-cache",
            "dv-v20",
            "--json",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["name"] == "post_deploy_verifier"
    assert out["summary"].startswith("pass_with_blockers")


def test_current_local_bundle_passes_core_markers():
    bundle = Path("static/index-v2-prototype.html").read_text(encoding="utf-8")
    results = verifier.evaluate_text_checks(bundle, verifier.BUNDLE_CHECKS)
    assert not [result for result in results if result.status == "fail"]
