"""Frontend contracts for Today/Verdict trust states."""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text(encoding="utf-8")


def _extract_function(name):
    start = HTML.index(f"function {name}(") if f"function {name}(" in HTML else HTML.index(f"async function {name}(")
    depth = 0
    i = start
    while i < len(HTML):
        c = HTML[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return HTML[start : i + 1]
        i += 1
    raise ValueError(f"Could not extract {name}")


def _extract_last_function(name):
    markers = (f"function {name}(", f"async function {name}(")
    start = max(HTML.rfind(marker) for marker in markers)
    if start < 0:
        raise ValueError(f"Could not extract {name}")
    depth = 0
    i = start
    while i < len(HTML):
        c = HTML[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return HTML[start : i + 1]
        i += 1
    raise ValueError(f"Could not extract {name}")


def test_today_scout_success_is_gated_on_server_confirmation():
    block = _extract_function("_todayV2ArmScout")
    assert "await dvFetch('/api/automation/settings'" in block
    assert "await dvFetch('/api/today/scout-alert'" in block
    assert "settingsOk&&alertOk" in block
    assert "Today Scout not armed" in block
    assert "goal_horizon" in block
    assert "pace_goal:paceGoal" in block
    assert "period_goal:periodGoal" in block
    assert "goal:s.goal" not in block


def test_today_protect_alert_is_gated_on_server_confirmation():
    block = _extract_function("_todayV2ProtectSummary")
    assert "await dvFetch('/api/today/scout-alert'" in block
    assert "ok=!!(resp && (resp.status==='ok'||resp.status==='deduped'))" in block
    assert "server alert was not confirmed" in block
    assert "goal_horizon" in block


def test_today_target_found_alert_is_horizon_aware_and_server_confirmed():
    block = _extract_function("_todayV2MaybeScoutAlert")
    assert "horizonLbl" in block
    assert "today\\'s pace toward the '+horizonLbl+' target" in block
    assert "await dvFetch('/api/today/scout-alert'" in block
    assert "goal_horizon" in block
    assert "goal:paceGoal" in block
    assert "pace_goal:paceGoal" in block
    assert "period_goal:periodGoal" in block
    assert "goal:(targetPath.paceGoal||c.profitGoal||0)" not in block
    assert "server alert was not confirmed" in block
    assert "weekly target" not in block


def test_today_target_path_preserves_pace_and_period_goals_explicitly():
    target_path = _extract_function("_todayV2TargetPath")
    select_plan = _extract_last_function("_todaySelectPlan")
    scout_panel = _extract_function("_todayV2ScoutPanel")

    assert "parseFloat(_pace.todayTarget)||goal" not in target_path
    assert "_rawPaceGoal=parseFloat(_pace.todayTarget)" in target_path
    assert "_periodGoal=(isFinite(_rawPeriodGoal)&&_rawPeriodGoal>0)?_rawPeriodGoal:goal" in target_path
    assert "_paceGoal=isFinite(_rawPaceGoal)?_rawPaceGoal:_periodGoal" in target_path
    assert "usesPaceSlice:_usesPaceSlice" in target_path
    assert "periodGoal:_periodGoal" in target_path
    assert "paceCopy:_paceCopy" in target_path

    assert "parseFloat(pace.todayTarget)||parseFloat(cfg.profitGoal)||0" not in select_plan
    assert "goal=isFinite(rawGoal)?rawGoal:(isFinite(cfgGoal)?cfgGoal:0)" in select_plan

    assert "targetPath.paceCopy" in scout_panel
    assert "Today pace path found" in scout_panel
    assert "basket covers the '+_spHorizonLow+' target" not in scout_panel


def test_today_scan_partial_failure_is_visible():
    block = _extract_function("_todayBuildPlan")
    assert "_runScanBase(groups" in block
    assert "_jFail=(res&&res.errors&&res.errors.length)||0" in block
    assert "catch(e){ _jFail++; }" in block
    assert "Partial scan - " in HTML
    assert "Today scan degraded" in HTML


def test_verdict_auto_review_sends_timeframe_direction_and_date():
    block = _extract_function("_vAutoReviewAI")
    assert "timeframe: sig.tf || '4h'" in block
    assert "direction: action" in block
    assert "date: verdictDate" in block


def test_portfolio_std_is_not_multiplied_by_100_in_frontend():
    assert "parseFloat(varData.portfolio_std).toFixed(2)" in HTML
    assert "${parseFloat(portStd).toFixed(2)}%" in HTML
    assert "(parseFloat(portStd)*100)" not in HTML


def test_today_risk_and_target_mutations_persist_config():
    preset = _extract_function("_todaySetRiskPreset")
    target = _extract_function("_todaySetProfitGoal")
    assert "if(typeof _todaySaveCfg==='function') _todaySaveCfg();" in preset
    assert "if(typeof _todaySaveCfg==='function') _todaySaveCfg();" in target

    idx = 0
    hits = 0
    while True:
      try:
        idx = HTML.index("function _todaySetGlobalRisk(", idx)
      except ValueError:
        break
      end = HTML.index("\n}", idx) + 2
      block = HTML[idx:end]
      assert "if(typeof _todaySaveCfg==='function') _todaySaveCfg();" in block
      hits += 1
      idx = end
    assert hits >= 2
