import requests

BASE_URL = "http://localhost:8000"

def validate_f1():
    print("Testing F1 (CFG Generation)...")
    response = requests.post(f"{BASE_URL}/analysis/generate-cfg", json={
        "filename": "test.cpp",
        "source_code": "int add(int a, int b) { return a + b; }"
    })
    assert response.status_code == 201
    print("✓ F1 works")
    return response.json()["cfg_id"]

def validate_f2(cfg_id):
    print("Testing F2 (Genetic Algorithm)...")
    response = requests.post(f"{BASE_URL}/ga/initialize", json={
        "cfg_id": cfg_id,
        "population_size": 10
    })
    assert response.status_code == 201
    print("✓ F2 works")

def validate_f3():
    print("Testing F3 (Fitness)...")
    response = requests.post(f"{BASE_URL}/api/fitness/evaluate/validation", json={
        "test_cases": [{"test_id": "t1", "inputs": [], "executed_branches": ["L1"]}],
        "total_branches": 2
    })
    assert response.status_code == 200
    print("✓ F3 works")

def validate_f5():
    print("Testing F5 (Tarantula)...")
    # --- FIX APPLIED HERE: Using the correct full path ---
    # The path is /api + /tarantula + /fault-localization/tarantula
    response = requests.post(f"{BASE_URL}/api/tarantula/fault-localization/tarantula", json={
        "coverage_data": [{"line_number": 1, "tests_executed": ["t1"]}],
        "test_results": {"t1": "pass"}
    })
    assert response.status_code == 200
    print("✓ F5 works")

if __name__ == "__main__":
    cfg_id = validate_f1()
    validate_f2(cfg_id)
    validate_f3()
    validate_f5()
    print("\n✅ All systems operational!")