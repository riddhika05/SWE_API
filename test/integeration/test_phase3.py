from fastapi.testclient import TestClient
from main import app
import pytest # Included for good practice, although not used in this specific test

# Initialize the test client for making API calls
client = TestClient(app)

# @pytest.mark.integration
def test_ga_to_fitness_workflow():
    """
    Tests the end-to-end integration workflow from CFG generation -> GA initialization 
    -> simulated test case execution data -> Fitness evaluation.
    This ensures data structures and IDs are correctly passed between F1, F2, and F3.
    """
    
    # 1. Generate CFG (F1 Integration Check)
    # The source code is simple enough to assume a predictable structure for mock data.
    cfg_resp = client.post("/analysis/generate-cfg", json={
        "filename": "test.cpp",
        "source_code": "int max(int a, int b) { if(a>b) return a; return b; }"
    })
    assert cfg_resp.status_code == 201
    cfg_id = cfg_resp.json()["cfg_id"]
    
    # 2. Initialize population (F2 Integration Check)
    pop_resp = client.post("/ga/initialize", json={
        "cfg_id": cfg_id,
        "population_size": 10
    })
    assert pop_resp.status_code == 201
    individuals = pop_resp.json()["individuals"]
    assert len(individuals) == 10
    
    # 3. Simulate execution and prepare fitness evaluation data (Mocking external execution)
    # We take the first 5 generated individuals and mock their branch coverage results.
    test_cases = [
        {
            "test_id": ind["id"],
            # Ensure inputs are correctly formatted as strings for the API payload
            "inputs": [str(g) for g in ind["genes"]], 
            # Mocking that all 5 individuals cover the same branch ('L1')
            "executed_branches": ["L1"]  
        }
        for ind in individuals[:5]
    ]
    
    # 4. Fitness evaluation (F3 Integration Check)
    # We assert total branches is 2 (e.g., 'if' and 'else' branch).
    fitness_resp = client.post("/api/fitness/evaluate/workflow_test", json={
        "test_cases": test_cases,
        "total_branches": 2
    })
    
    # Assertions
    assert fitness_resp.status_code == 200
    results = fitness_resp.json().get("results")
    assert results is not None
    assert len(results) == 5 # Ensure results are returned for all 5 submitted cases
    
    # Since all 5 test cases covered the same single branch out of 2, 
    # their fitness scores should be equal (e.g., 0.5)
    first_score = results[0]["fitness_score"]
    assert all(r["fitness_score"] == first_score for r in results)