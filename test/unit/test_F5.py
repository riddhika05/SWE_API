import sys
import os
# Ensure imports from parent directory work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI # Needed to create a temporary app for the router
from tarantula_fault_localization import router # Correctly import the router

# --- FIX: Create a temporary app to host the router for testing ---
temp_app = FastAPI()
temp_app.include_router(router)
client = TestClient(temp_app)
# -----------------------------------------------------------------

# -----------------
# Test 1: Basic Normal Case
# -----------------
def test_f5_basic():
    payload = {
        "coverage_data": [
            {"line_number": 10, "tests_executed": ["t1", "t2", "t3"]},
            {"line_number": 20, "tests_executed": ["t2"]},
            {"line_number": 30, "tests_executed": ["t1", "t3"]}
        ],
        "test_results": {"t1": "fail", "t2": "pass", "t3": "fail"}
    }

    response = client.post("/tarantula/fault-localization/tarantula", json=payload) # Note the prefix in the URL
    assert response.status_code == 200

    data = response.json()
    assert len(data["suspiciousness_scores"]) == 3


# -----------------
# Test 2: No failing tests
# -----------------
def test_f5_no_failed_tests():
    payload = {
        "coverage_data": [
            {"line_number": 10, "tests_executed": ["t1", "t2"]}
        ],
        "test_results": {"t1": "pass", "t2": "pass"}
    }

    response = client.post("/tarantula/fault-localization/tarantula", json=payload) # Note the prefix
    assert response.status_code == 200
    data = response.json()

    assert data["total_failed_tests"] == 0
    assert data["suspiciousness_scores"][0]["suspiciousness"] == 0.0


# -----------------
# Test 3: No passing tests
# -----------------
def test_f5_no_passed_tests():
    payload = {
        "coverage_data": [
            {"line_number": 10, "tests_executed": ["t1", "t2"]}
        ],
        "test_results": {"t1": "fail", "t2": "fail"}
    }

    response = client.post("/tarantula/fault-localization/tarantula", json=payload) # Note the prefix
    assert response.status_code == 200
    data = response.json()

    assert data["total_passed_tests"] == 0
    assert data["suspiciousness_scores"][0]["suspiciousness"] == 1.0


# -----------------
# Test 4: Line executed by no tests
# -----------------
def test_f5_line_no_test_execution():
    payload = {
        "coverage_data": [
            {"line_number": 10, "tests_executed": []}
        ],
        "test_results": {"t1": "pass", "t2": "fail"}
    }

    response = client.post("/tarantula/fault-localization/tarantula", json=payload) # Note the prefix
    data = response.json()

    assert data["suspiciousness_scores"][0]["suspiciousness"] == 0.0


# -----------------
# Test 5: Test name in coverage not in test_results
# -----------------
def test_f5_unknown_testname():
    payload = {
        "coverage_data": [
            {"line_number": 10, "tests_executed": ["x1", "x2"]}
        ],
        "test_results": {"t1": "pass"}
    }

    response = client.post("/tarantula/fault-localization/tarantula", json=payload) # Note the prefix
    data = response.json()

    assert data["suspiciousness_scores"][0]["failed_count"] == 0
    assert data["suspiciousness_scores"][0]["passed_count"] == 0