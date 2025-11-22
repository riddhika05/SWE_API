import pytest
from fastapi.testclient import TestClient
from SWE_API.F6 import app
import os

client = TestClient(app)

# Helper: create a temporary source file
TEST_FILE = "sample.c"
TEST_LINES = [
    "int main() {",
    "   int a = 10;",
    "   return a;",
    "}"
]

def setup_module(module):
    # create file before tests run
    with open(TEST_FILE, "w") as f:
        f.write("\n".join(TEST_LINES))

def teardown_module(module):
    # delete file after tests finish
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

# -----------------
# Test 1: Basic valid report
# -----------------
def test_f6_basic():
    payload = {
        "suspiciousness_scores": [
            {"line_number": 2, "suspiciousness": 0.75}
        ],
        "default_file_name": TEST_FILE
    }

    response = client.post("/fault-localization/report", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["fault_localization_report"][0]["code"] == TEST_LINES[1]


# -----------------
# Test 2: File not found
# -----------------
def test_f6_file_not_found():
    payload = {
        "suspiciousness_scores": [
            {"line_number": 3, "suspiciousness": 1.0}
        ],
        "default_file_name": "does_not_exist.c"
    }

    response = client.post("/fault-localization/report", json=payload)
    data = response.json()

    assert data["fault_localization_report"][0]["code"] == "<File not found>"


# -----------------
# Test 3: Line out of range
# -----------------
def test_f6_line_out_of_range():
    payload = {
        "suspiciousness_scores": [
            {"line_number": 99, "suspiciousness": 0.5}
        ],
        "default_file_name": TEST_FILE
    }

    response = client.post("/fault-localization/report", json=payload)
    data = response.json()

    assert data["fault_localization_report"][0]["code"] == "<Line number out of range>"


# -----------------
# Test 4: Already transformed suspicious_lines
# -----------------
def test_f6_suspicious_lines_direct_input():
    payload = {
        "suspicious_lines": [
            {"file_name": TEST_FILE, "line_number": 1, "suspiciousness": 0.8}
        ]
    }

    response = client.post("/fault-localization/report", json=payload)
    data = response.json()

    assert data["fault_localization_report"][0]["code"] == TEST_LINES[0]


# -----------------
# Test 5: Sorting correctness
# -----------------
def test_f6_sorting():
    payload = {
        "suspiciousness_scores": [
            {"line_number": 1, "suspiciousness": 0.1},
            {"line_number": 2, "suspiciousness": 0.9},
            {"line_number": 3, "suspiciousness": 0.5}
        ],
        "default_file_name": TEST_FILE
    }

    response = client.post("/fault-localization/report", json=payload)
    data = response.json()["fault_localization_report"]

    assert data[0]["suspiciousness"] == 0.9
    assert data[1]["suspiciousness"] == 0.5
    assert data[2]["suspiciousness"] == 0.1
