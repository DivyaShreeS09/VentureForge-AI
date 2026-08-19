def test_create_startup_success(client):
    response = client.post(
        "/api/v1/startups",
        json={
            "name": "PayFlux",
            "description": "A payments platform that lets small businesses settle cross-border payments in seconds.",
            "funding_answers": {"problem_clarity": 2},
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "PayFlux"
    assert "id" in body


def test_create_startup_missing_name_returns_422(client):
    response = client.post(
        "/api/v1/startups",
        json={"name": "", "description": "A sufficiently long description of the startup idea."},
    )
    assert response.status_code == 422


def test_create_startup_description_too_short_returns_422(client):
    response = client.post("/api/v1/startups", json={"name": "Nova", "description": "short"})
    assert response.status_code == 422


def test_get_startup_not_found_returns_404(client):
    response = client.get("/api/v1/startups/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_startup_after_create(client):
    created = client.post(
        "/api/v1/startups",
        json={"name": "Nova", "description": "A subscription analytics dashboard for retail teams."},
    ).json()
    response = client.get(f"/api/v1/startups/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
