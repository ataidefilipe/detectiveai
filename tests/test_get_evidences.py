def test_list_session_evidences(client):
    resp = client.get("/sessions/1/evidences")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) > 0
    assert "is_mandatory" in data[0]
