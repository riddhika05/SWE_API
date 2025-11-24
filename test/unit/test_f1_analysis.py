from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to sys.path so we can import 'main'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_generate_cfg_valid_cpp():
    """
    F1 Check: Does it correctly parse a C++ function and detect inputs?
    """
    payload = {
        "filename": "math_test.cpp",
        "source_code": "int multiply(int a, int b) { return a * b; }"
    }
    
    response = client.post("/analysis/generate-cfg", json=payload)
    
    # 1. Check API Status
    assert response.status_code == 201
    
    # 2. Check JSON Structure
    data = response.json()
    assert "cfg_id" in data
    assert "nodes" in data
    assert "edges" in data
    
    # 3. Check Parameter Detection (Critical for F1 -> F2 link)
    # The code has 2 'int' parameters.
    assert data["required_inputs"] == ["int", "int"]

def test_generate_cfg_complexity_calc():
    """
    F1 Check: Does it calculate Cyclomatic Complexity correctly?
    """
    # A function with one 'if' has complexity 2 (1 base + 1 branch)
    payload = {
        "filename": "logic.cpp",
        "source_code": "void check(int x) { if(x > 0) return; }"
    }
    
    response = client.post("/analysis/generate-cfg", json=payload)
    data = response.json()
    
    assert data["complexity"] == 2

def test_reject_empty_code():
    """
    F1 Check: Error handling.
    """
    payload = {
        "filename": "empty.cpp",
        "source_code": "   "
    }
    response = client.post("/analysis/generate-cfg", json=payload)
    assert response.status_code == 400