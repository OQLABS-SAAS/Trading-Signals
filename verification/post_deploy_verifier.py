#!/usr/bin/env python3
"""DotVerse post-deploy verifier.

This is not a trading bot and it does not place orders. It verifies the public
bundle and public endpoints, then labels anything requiring login, MT5, or
the trader's click as blocked instead of pretending it passed.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_BASE_URL = "https://dot-verse.up.railway.app"
DEFAULT_BUNDLE_PATH = "static/index-v2-prototype.html"
DEFAULT_SW_PATH = "sw.js"
MAX_RESPONSE_BYTES = 6_000_000


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    evidence: str
    severity: str = "required"


@dataclass(frozen=True)
class TextCheck:
    name: str
    needles: tuple[str, ...]
    evidence: str
    severity: str = "required"


BUNDLE_CHECKS: tuple[TextCheck, ...] = (
    TextCheck(
        name="today_horizon_selector",
        needles=("todayHorizon", "_todaySetHorizon", ">Daily<", ">Weekly<", ">Monthly<"),
        evidence="Today exposes daily, weekly, and monthly profit horizons.",
    ),
    TextCheck(
        name="main_alerts_telegram_feed",
        needles=("async function showAlerts(", "tgScanFeed", "Telegram Signals", "dvLoadScanAlerts"),
        evidence="Main Alerts tab renders the Telegram scan feed and loader.",
    ),
    TextCheck(
        name="basket_totals_engine",
        needles=("_dvBasketTotals", "totalCashIn", "totalRisk", "totalProfitTarget", "totalPositionValue"),
        evidence="Canonical multi-leg basket totals function is present.",
    ),
    TextCheck(
        name="ladder_entry_completeness",
        needles=("Scale-out plan", "Entry", "Cash in", "controls", "lots"),
        evidence="Ladder UI contains entry, cash-in, controlled value, and lot language.",
    ),
    TextCheck(
        name="plain_mt5_status_language",
        needles=("account details syncing", "MT5 CONNECTED", "SYNCING"),
        evidence="Human MT5 sync wording is present in the bundle.",
    ),
    TextCheck(
        name="retcode_translation_surface",
        needles=("status_message", "_dvHumanizeError", "o.status === 'failed'"),
        evidence="Act/order UI has a display path for broker retcode instructions.",
    ),
    TextCheck(
        name="real_pnl_chart_contract",
        needles=("/api/performance/pnl", "No closed trades yet"),
        evidence="P&L chart reads real closed-trade data and has an honest empty state.",
    ),
    TextCheck(
        name="real_stress_test_contract",
        needles=("/api/mt5/state", "open positions", "Stress test"),
        evidence="Risk stress-test surface is wired to real MT5 state language.",
    ),
    TextCheck(
        name="no_bare_mt5_unknown",
        needles=("MT5 UNKNOWN",),
        evidence="Bare 'MT5 UNKNOWN' wording must not render.",
    ),
)


BLOCKED_CHECKS: tuple[CheckResult, ...] = (
    CheckResult(
        name="mt5_order_fill",
        status="blocked",
        evidence="Requires the trader's MT5 terminal/account to accept trading; broker retcode 10017 is external.",
        severity="blocked",
    ),
    CheckResult(
        name="ea_self_diagnosis_live_banner",
        status="blocked",
        evidence="Requires the trader to recompile and reattach the updated DotVerse_EA.ex5.",
        severity="blocked",
    ),
    CheckResult(
        name="authenticated_money_path_walk",
        status="blocked",
        evidence="Requires an authenticated browser session and an explicit non-irreversible test scope.",
        severity="blocked",
    ),
)


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def url_for(base_url: str, path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{normalize_base_url(base_url)}{clean_path}"


def fetch_text(url: str, timeout: float, max_bytes: int = MAX_RESPONSE_BYTES) -> tuple[int, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "Connection": "close",
            "User-Agent": "DotVerse-Post-Deploy-Verifier/1.0",
        },
    )
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes + 1).decode("utf-8", errors="replace")
            if len(body.encode("utf-8", errors="replace")) > max_bytes:
                return resp.getcode(), body[:max_bytes], f"response exceeded {max_bytes} bytes; truncated"
            return resp.getcode(), body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body, str(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, "", str(exc)
    finally:
        socket.setdefaulttimeout(old_timeout)


def load_local_text(path: Path) -> tuple[int, str, str]:
    try:
        return 200, path.read_text(encoding="utf-8"), ""
    except OSError as exc:
        return 0, "", str(exc)


def evaluate_text_checks(source: str, checks: Iterable[TextCheck]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check in checks:
        if check.name.startswith("no_"):
            present = [needle for needle in check.needles if needle in source]
            if present:
                results.append(
                    CheckResult(
                        check.name,
                        "fail",
                        f"Forbidden marker(s) present: {', '.join(present)}",
                        check.severity,
                    )
                )
            else:
                results.append(CheckResult(check.name, "pass", check.evidence, check.severity))
            continue

        missing = [needle for needle in check.needles if needle not in source]
        if missing:
            results.append(
                CheckResult(
                    check.name,
                    "fail",
                    f"Missing marker(s): {', '.join(missing)}",
                    check.severity,
                )
            )
        else:
            results.append(CheckResult(check.name, "pass", check.evidence, check.severity))
    return results


def extract_cache_version(sw_text: str) -> str | None:
    match = re.search(r"CACHE_VER\s*=\s*['\"]([^'\"]+)['\"]", sw_text)
    return match.group(1) if match else None


def evaluate_health(base_url: str, timeout: float) -> CheckResult:
    status, text, error = fetch_text(url_for(base_url, "/health"), timeout)
    if status != 200:
        detail = error or text[:160] or "no response body"
        return CheckResult("health_endpoint", "fail", f"/health returned {status}: {detail}")
    return CheckResult("health_endpoint", "pass", "/health returned HTTP 200.")


def evaluate_auth_check(base_url: str, timeout: float) -> CheckResult:
    status, text, error = fetch_text(url_for(base_url, "/api/auth-check"), timeout)
    if status == 200:
        return CheckResult("auth_check_endpoint", "pass", "/api/auth-check returned HTTP 200.")
    if status in {401, 403}:
        return CheckResult(
            "auth_check_endpoint",
            "warn",
            f"/api/auth-check returned {status}; logged-out state is reachable but not authenticated.",
            "optional",
        )
    detail = error or text[:160] or "no response body"
    return CheckResult("auth_check_endpoint", "fail", f"/api/auth-check returned {status}: {detail}")


def evaluate_scan_alerts(base_url: str, timeout: float) -> CheckResult:
    status, text, error = fetch_text(url_for(base_url, "/api/scan-alerts"), timeout)
    if status == 200:
        try:
            payload = json.loads(text or "{}")
        except json.JSONDecodeError:
            return CheckResult("scan_alerts_endpoint", "fail", "/api/scan-alerts did not return JSON.")
        if isinstance(payload, dict):
            sample = json.dumps(payload, sort_keys=True)[:240]
            return CheckResult("scan_alerts_endpoint", "pass", f"/api/scan-alerts JSON ok: {sample}")
        return CheckResult("scan_alerts_endpoint", "fail", "/api/scan-alerts returned non-object JSON.")
    if status in {401, 403}:
        return CheckResult(
            "scan_alerts_endpoint",
            "warn",
            f"/api/scan-alerts returned {status}; feed render is verified from bundle, data needs login/live user.",
            "optional",
        )
    detail = error or text[:160] or "no response body"
    return CheckResult("scan_alerts_endpoint", "fail", f"/api/scan-alerts returned {status}: {detail}")


def evaluate_service_worker(
    *,
    source_name: str,
    sw_text: str,
    expected_cache: str | None,
) -> CheckResult:
    cache_version = extract_cache_version(sw_text)
    if not cache_version:
        return CheckResult("service_worker_cache", "fail", f"No CACHE_VER found in {source_name}.")
    if expected_cache and cache_version != expected_cache:
        return CheckResult(
            "service_worker_cache",
            "fail",
            f"{source_name} CACHE_VER={cache_version}, expected {expected_cache}.",
        )
    return CheckResult("service_worker_cache", "pass", f"{source_name} CACHE_VER={cache_version}.")


def summarize(results: Sequence[CheckResult]) -> str:
    failures = sum(1 for result in results if result.status == "fail")
    warnings = sum(1 for result in results if result.status == "warn")
    blocked = sum(1 for result in results if result.status == "blocked")
    passed = sum(1 for result in results if result.status == "pass")
    if failures:
        overall = "fail"
    else:
        overall = "pass_with_blockers" if blocked or warnings else "pass"
    return f"{overall}: {passed} pass, {failures} fail, {warnings} warn, {blocked} blocked"


def build_report(
    *,
    base_url: str,
    bundle_source: str,
    bundle_text: str,
    sw_source: str,
    sw_text: str,
    expected_cache: str | None,
    timeout: float,
    include_live_endpoints: bool,
) -> dict[str, object]:
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results: list[CheckResult] = []
    results.extend(evaluate_text_checks(bundle_text, BUNDLE_CHECKS))
    results.append(
        evaluate_service_worker(
            source_name=sw_source,
            sw_text=sw_text,
            expected_cache=expected_cache,
        )
    )
    if include_live_endpoints:
        results.append(evaluate_health(base_url, timeout))
        results.append(evaluate_auth_check(base_url, timeout))
        results.append(evaluate_scan_alerts(base_url, timeout))
    else:
        results.append(
            CheckResult(
                "live_endpoint_probe",
                "warn",
                "Skipped because --local-bundle was used without --probe-live.",
                "optional",
            )
        )
    results.extend(BLOCKED_CHECKS)
    return {
        "name": "post_deploy_verifier",
        "started_at": started,
        "base_url": normalize_base_url(base_url),
        "bundle_source": bundle_source,
        "service_worker_source": sw_source,
        "summary": summarize(results),
        "results": [asdict(result) for result in results],
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify DotVerse bundle and public live checks.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--bundle-path", default=DEFAULT_BUNDLE_PATH)
    parser.add_argument("--sw-path", default=DEFAULT_SW_PATH)
    parser.add_argument("--local-bundle", type=Path, help="Read HTML from disk instead of base-url.")
    parser.add_argument("--local-sw", type=Path, help="Read service worker from disk instead of base-url.")
    parser.add_argument("--probe-live", action="store_true", help="Probe live endpoints even with local files.")
    parser.add_argument("--no-endpoints", action="store_true", help="Skip public endpoint probes.")
    parser.add_argument("--expected-cache", help="Expected service-worker CACHE_VER, e.g. dv-v20.")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    base_url = normalize_base_url(args.base_url)

    if args.local_bundle:
        bundle_status, bundle_text, bundle_error = load_local_text(args.local_bundle)
        bundle_source = str(args.local_bundle)
    else:
        bundle_source = url_for(base_url, args.bundle_path)
        bundle_status, bundle_text, bundle_error = fetch_text(bundle_source, args.timeout)

    if args.local_sw:
        sw_status, sw_text, sw_error = load_local_text(args.local_sw)
        sw_source = str(args.local_sw)
    else:
        sw_source = url_for(base_url, args.sw_path)
        sw_status, sw_text, sw_error = fetch_text(sw_source, args.timeout)

    bootstrap_failures: list[CheckResult] = []
    if bundle_status != 200:
        bootstrap_failures.append(
            CheckResult("bundle_fetch", "fail", f"{bundle_source} returned {bundle_status}: {bundle_error}")
        )
    if sw_status != 200:
        bootstrap_failures.append(
            CheckResult("service_worker_fetch", "fail", f"{sw_source} returned {sw_status}: {sw_error}")
        )

    if bootstrap_failures:
        report = {
            "name": "post_deploy_verifier",
            "base_url": base_url,
            "summary": summarize(bootstrap_failures),
            "results": [asdict(result) for result in bootstrap_failures],
        }
    else:
        report = build_report(
            base_url=base_url,
            bundle_source=bundle_source,
            bundle_text=bundle_text,
            sw_source=sw_source,
            sw_text=sw_text,
            expected_cache=args.expected_cache,
            timeout=args.timeout,
            include_live_endpoints=((not args.local_bundle) or args.probe_live) and not args.no_endpoints,
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["summary"])
        for item in report["results"]:
            print(f"[{item['status']}] {item['name']}: {item['evidence']}")

    return 1 if any(item["status"] == "fail" for item in report["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
