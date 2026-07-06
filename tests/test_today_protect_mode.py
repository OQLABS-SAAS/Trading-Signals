import app as dvapp


def test_today_scout_alert_accepts_protect_mode(monkeypatch):
    sent = {}

    def fake_telegram(message):
        sent["telegram"] = message
        return True

    def fake_push(user_id, ntype, title, body, data=None):
        sent["push"] = {
            "user_id": user_id,
            "ntype": ntype,
            "title": title,
            "body": body,
            "data": data or {},
        }

    monkeypatch.setattr(dvapp, "send_telegram", fake_telegram)
    monkeypatch.setattr(dvapp, "_push_notification", fake_push)

    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"

    resp = client.post(
        "/api/today/scout-alert",
        json={"kind": "protect", "goal": 500, "profit": 520, "eta": "protect mode", "trades": 2},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["title"] == "Today protect mode active"
    assert "pausing new Today entries" in data["body"]
    assert "Protect Alert: target already reached" in sent["telegram"]
    assert "What this means:" in sent["telegram"]
    assert "Status:\nPROTECTING - no new entries" in sent["telegram"]
    assert "Next step:" in sent["telegram"]
    assert sent["push"]["ntype"] == "today_scout"
    assert sent["push"]["data"]["kind"] == "protect"


def test_today_scout_alert_uses_review_template_for_covered_path(monkeypatch):
    sent = {}

    monkeypatch.setattr(dvapp, "send_telegram", lambda message: sent.setdefault("telegram", message) or True)
    monkeypatch.setattr(dvapp, "_push_notification", lambda *args, **kwargs: None)

    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"

    resp = client.post(
        "/api/today/scout-alert",
        json={
            "kind": "covered",
            "goal_horizon": "weekly",
            "goal": 100,
            "profit": 293.15,
            "risk": 143.8,
            "eta": "~3h",
            "trades": 2,
        },
    )

    assert resp.status_code == 200
    msg = sent["telegram"]
    assert "Scout Alert: 2 candidate trades found" in msg
    assert "What this means:" in msg
    assert "DotVerse found 2 possible trades that could exceed this week's $100.00 target if they work as planned." in msg
    assert "Summary:" in msg
    assert "• Trades: 2" in msg
    assert "• Goal: $100.00" in msg
    assert "• Potential upside: +$293.15" in msg
    assert "• Planned risk: -$143.80" in msg
    assert "• Sizing rule: every $1,000 account equity = 0.01 lot" in msg
    assert "• ETA: ~3h" in msg
    assert "• Reason: scout detected a target path" in msg
    assert "Status:\nSUGGESTED - not yet executed" in msg
    assert "Next step:\nReview the symbols, entries, stop losses, take-profit levels, and position sizing before entering." in msg


def test_today_automation_summary_counts_enabled_flags_not_reasons():
    result = dvapp._recommend_automations_from_signal(
        {
            "trade_type": "swing",
            "confidence": 82,
            "confidence_label": "CONFIRMED",
            "signal": "SELL",
            "bull_count": 8,
            "bear_count": 26,
            "atr": 1,
            "entry": 576,
            "htf_bias": "BEARISH",
            "rsi": 27,
            "target": "tp3",
        }
    )

    assert all(result[k] is True for k in ("be", "trail", "macro", "inval", "sent", "tp1", "tp2", "weekend"))
    assert "DotVerse activated 8 automations" in result["explanation"]
