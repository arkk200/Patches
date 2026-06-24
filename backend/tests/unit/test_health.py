from fastapi.testclient import TestClient


class TestHealth:
    def test_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_post_not_allowed(self, client: TestClient) -> None:
        response = client.post("/health")
        assert response.status_code == 405
