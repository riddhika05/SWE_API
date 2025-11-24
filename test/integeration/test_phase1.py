import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_f1_cfg_generation():
    response = client.post("/analysis/generate-cfg", json={
        "filename": "test.cpp",
        "source_code": "int add(int a, int b) { return a + b; }"
    })
    assert response.status_code == 201
    assert "cfg_id" in response.json()
    assert response.json()["required_inputs"] == ["int", "int"]

def test_f2_ga_initialization():
    # First create CFG
    cfg_resp = client.post("/analysis/generate-cfg", json={
        "filename": "test.cpp",
        "source_code": "int add(int a, int b) { return a + b; }"
    })
    cfg_id = cfg_resp.json()["cfg_id"]
    
    # Initialize GA
    response = client.post("/ga/initialize", json={
        "cfg_id": cfg_id,
        "population_size": 20
    })
    assert response.status_code == 201
    assert response.json()["population_count"] == 20

def test_cors_enabled():
    response = client.get("/", headers={"Origin": "https://swe-nu.vercel.app"})
    assert response.status_code == 200