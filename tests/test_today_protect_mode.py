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
