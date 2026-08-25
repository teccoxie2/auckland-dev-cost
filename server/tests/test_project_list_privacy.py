from fastapi.testclient import TestClient

from app.main import app
from app.store import create_project, reset_engine


def test_http_project_list_stays_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'projects.sqlite'}")
    reset_engine()
    create_project("55 Nelson Street, Howick", {"options": []}, "ready")
    client = TestClient(app)
    response = client.get("/projects")
    assert response.status_code == 200
    assert response.json() == {"projects": []}
    assert "no-store" in response.headers.get("cache-control", "")
