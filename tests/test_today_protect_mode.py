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
    assert "Today protect mode active" in sent["telegram"]
    assert sent["push"]["ntype"] == "today_scout"
    assert sent["push"]["data"]["kind"] == "protect"


def test_today_scout_alert_uses_requested_goal_horizon(monkeypatch):
    sent = {}

    monkeypatch.setattr(dvapp, "send_telegram", lambda message: sent.setdefault("telegram", message))
    monkeypatch.setattr(
        dvapp,
        "_push_notification",
        lambda user_id, ntype, title, body, data=None: sent.setdefault("push", {"body": body, "data": data or {}}),
    )

    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"

    resp = client.post(
        "/api/today/scout-alert",
        json={"kind": "armed", "goal_horizon": "monthly", "goal": 2500, "profit": 100, "eta": "15 min scan"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "monthly target" in data["body"]
    assert "weekly target" not in data["body"]
    assert sent["push"]["data"]["goal_horizon"] == "monthly"


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
