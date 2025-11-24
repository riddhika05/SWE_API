from fastapi.testclient import TestClient
from main import app
import pytest
import os
# Initialize the test client
client = TestClient(app)

def test_f3_fitness_evaluation():
    """
    Tests the API endpoint for calculating fitness scores of generated test cases.
    It expects a higher score for the test case that covers more branches.
    """
    response = client.post("/api/fitness/evaluate/test_session", json={
        "test_cases": [
            {"test_id": "tc1", "inputs": ["5"], "executed_branches": ["L1", "L2"]},
            {"test_id": "tc2", "inputs": ["0"], "executed_branches": ["L1"]}
        ],
        "total_branches": 3
    })
    
    assert response.status_code == 200
    results = response.json().get("results")
    assert results is not None
    
    # Assert that tc1 (2 branches covered) has a higher fitness score than tc2 (1 branch covered)
    # This validates the fitness calculation logic (e.g., branch coverage divided by total branches)
    assert results[0]["fitness_score"] > results[1]["fitness_score"]
    assert results[0]["test_id"] == "tc1"
    assert results[1]["test_id"] == "tc2"


# Note: The test_f4_compilation requires the 'g++' compiler to be available 
# in the environment where pytest is run.
#@pytest.mark.skipif(not os.getenv("COMPILER_PATH"), reason="Skipping F4 compilation test; g++ not configured/found.")
def test_f4_compilation():
    """
    Tests the API endpoint for compiling source code for coverage analysis.
    This creates a temporary file and attempts compilation via the API.
    """
    import tempfile
    import os
    
    # 1. Create a temporary C++ source file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write("int main() { return 0; }")
        source = f.name
        
    try:
        # 2. Call the API to compile the temporary file
        response = client.post("/api/coverage/compile/test_proj", json={
            "source_file_path": source,
            "compiler": "g++"
        })
        
        # 3. Assert the API call succeeded (status 200 means the API request was handled, 
        # but actual compilation success depends on the backend)
        assert response.status_code == 200
        
        # Additional checks could be added here, like asserting the compiled output path exists.
        
    finally:
        # 4. Clean up the temporary file
        os.remove(source)