def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "healthy"
    assert body["database"] == "connected"
