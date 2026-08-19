"""Tests for GET /api/v1/taxonomy (production-hardening phase). Proves the endpoint is the live
source of truth for the controlled venture-positioning taxonomy — i.e. that a taxonomy change is
reflected in the API response without editing anything outside app.ml.positioning_taxonomy.
"""

from app.ml.positioning_taxonomy import POSITIONING_TAXONOMY, TAXONOMY_VERSION


def test_taxonomy_endpoint_exposes_active_version_and_all_domains(client):
    response = client.get("/api/v1/taxonomy")
    assert response.status_code == 200
    body = response.json()

    assert body["taxonomy_version"] == TAXONOMY_VERSION
    returned_ids = {d["id"] for d in body["domains"]}
    assert returned_ids == set(POSITIONING_TAXONOMY.keys())


def test_taxonomy_domains_carry_label_description_and_sectors(client):
    body = client.get("/api/v1/taxonomy").json()
    by_id = {d["id"]: d for d in body["domains"]}

    smart_facilities = by_id["Smart Facilities Technology"]
    assert smart_facilities["label"] == "Smart Facilities Technology"
    assert smart_facilities["description"]
    assert {"Campuses", "Hotels"}.issubset(set(smart_facilities["deployment_sectors"]))


def test_allowed_secondary_domains_matches_full_domain_list(client):
    body = client.get("/api/v1/taxonomy").json()
    domain_ids = {d["id"] for d in body["domains"]}
    assert set(body["allowed_secondary_domains"]) == domain_ids


def test_taxonomy_change_is_reflected_without_editing_any_frontend_constant(monkeypatch, client):
    """Simulates a taxonomy revision: add a brand-new domain to the live taxonomy dict at runtime
    and confirm the API immediately reflects it — proving the endpoint (and therefore the frontend
    that consumes it) never needs a hardcoded, duplicated domain list to stay in sync.
    """
    from app.ml.positioning_taxonomy import DomainSpec, POSITIONING_TAXONOMY as taxonomy_dict

    new_spec = DomainSpec(
        name="Synthetic Test Domain",
        specificity_rank=99,
        keywords={"synthetic": 1.0, "test": 1.0},
    )
    monkeypatch.setitem(taxonomy_dict, "Synthetic Test Domain", new_spec)

    body = client.get("/api/v1/taxonomy").json()
    ids = {d["id"] for d in body["domains"]}
    assert "Synthetic Test Domain" in ids
    assert "Synthetic Test Domain" in body["allowed_secondary_domains"]
