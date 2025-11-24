from fastapi.testclient import TestClient
from main import app
import pytest

# Initialize the test client
client = TestClient(app)

@pytest.mark.integration
def test_f5_tarantula():
    """
    Tests the F5 Tarantula endpoint integration.
    Verifies that the API calculates suspiciousness scores correctly.
    
    Test Case:
    Total Passed (P) = 1 (t1)
    Total Failed (F) = 1 (t2)
    
    Line 10: Executed by t1 (Pass), t2 (Fail). Passed_count=1, Failed_count=1.
             Score = (1/1) / (1/1 + 1/1) = 1 / 2 = 0.5
    
    Line 20: Executed by t2 (Fail) only. Passed_count=0, Failed_count=1.
             Score = (1/1) / (1/1 + 0/1) = 1 / 1 = 1.0
             
    Expectation: Line 20 (Score 1.0) > Line 10 (Score 0.5)
    """
    response = client.post("/api/tarantula/fault-localization/tarantula", json={
        "coverage_data": [
            {"line_number": 10, "tests_executed": ["t1", "t2"]},
            {"line_number": 20, "tests_executed": ["t2"]}
        ],
        "test_results": {"t1": "pass", "t2": "fail"}
    })
    
    assert response.status_code == 200
    scores = response.json()["suspiciousness_scores"]
    
    # Use next() to safely find the scores by line number
    line_20 = next(s for s in scores if s["line_number"] == 20)
    line_10 = next(s for s in scores if s["line_number"] == 10)
    
    # Assert line 20 (1.0) is greater than line 10 (0.5)
    assert line_20["suspiciousness"] > line_10["suspiciousness"]
    assert line_20["suspiciousness"] == 1.0
    assert line_10["suspiciousness"] == 0.5


@pytest.mark.integration
def test_f6_report():
    """
    Tests the F6 Report Generation endpoint integration.
    Verifies that the API accepts the F5 output format and produces a report structure.
    
    NOTE: This mock test cannot verify the actual code snippet reading 
    since 'test_file.py' doesn't exist, but it checks the API handles the request 
    and transforms the data correctly.
    """
    response = client.post("/api/fault-localization/report", json={
        "suspiciousness_scores": [
            {"line_number": 5, "suspiciousness": 0.8}
        ],
        "default_file_name": "test_file.py"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "fault_localization_report" in data
    assert isinstance(data["fault_localization_report"], list)
    assert len(data["fault_localization_report"]) == 1
    
    # Check that the report structure is correct
    report_item = data["fault_localization_report"][0]
    assert report_item["line_number"] == 5
    assert report_item["suspiciousness"] == 0.8
    # Code snippet should indicate file not found, as it's a mock file
    assert "code" in report_item
    assert report_item["code"] == "<File not found>"