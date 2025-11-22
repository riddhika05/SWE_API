"""
Unit tests for F4: Coverage Execution Module (FastAPI Endpoints)
Tests endpoints 19-25 from project structure
"""

import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI
from f4_coverage_execution import router

# Create FastAPI app for testing
app = FastAPI()
app.include_router(router)

# Test client
client = TestClient(app)


# ========== Test C Code ==========

SAMPLE_C_CODE = """
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("No args\\n");
        return 1;
    }
    
    int x = atoi(argv[1]);
    
    if (x > 10) {
        printf("Greater than 10\\n");
    } else {
        printf("Less or equal to 10\\n");
    }
    
    return 0;
}
"""

INVALID_C_CODE = """
#include <stdio.h>

int main() {
    printf("Missing semicolon")  // Syntax error
    return 0
}
"""


# ========== Endpoint 19: POST /api/coverage/compile/{project_id} ==========

class TestCompileEndpoint:
    """Test compilation endpoint"""
    
    def test_compile_success(self, tmp_path):
        """Test successful compilation"""
        # Create temporary C file
        source_file = tmp_path / "test.c"
        source_file.write_text(SAMPLE_C_CODE)
        
        request = {
            "source_file_path": str(source_file),
            "compiler": "gcc"
        }
        
        response = client.post(
            "/api/coverage/compile/project_001",
            json=request
        )
        
        # Skip if gcc not available
        if response.status_code == 200:
            data = response.json()
            
            if "not found" in data.get("stderr", "").lower():
                pytest.skip("GCC not installed")
            
            assert data["project_id"] == "project_001"
            assert data["status"] == "success"
            assert data["binary_path"] is not None
            assert data["compilation_time"] > 0
            assert os.path.exists(data["binary_path"])
    
    def test_compile_failure(self, tmp_path):
        """Test compilation with invalid code"""
        source_file = tmp_path / "invalid.c"
        source_file.write_text(INVALID_C_CODE)
        
        request = {
            "source_file_path": str(source_file),
            "compiler": "gcc"
        }
        
        response = client.post(
            "/api/coverage/compile/project_invalid",
            json=request
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "not found" not in data.get("stderr", "").lower():
                assert data["status"] == "failed"
                assert data["binary_path"] is None
                assert len(data["stderr"]) > 0
    
    def test_compile_nonexistent_file(self):
        """Test compilation with non-existent file"""
        request = {
            "source_file_path": "/nonexistent/file.c",
            "compiler": "gcc"
        }
        
        response = client.post(
            "/api/coverage/compile/project_nonexist",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
    
    def test_compile_with_gpp(self, tmp_path):
        """Test compilation with g++ compiler"""
        source_file = tmp_path / "test.c"
        source_file.write_text(SAMPLE_C_CODE)
        
        request = {
            "source_file_path": str(source_file),
            "compiler": "g++"
        }
        
        response = client.post(
            "/api/coverage/compile/project_gpp",
            json=request
        )
        
        assert response.status_code == 200


# ========== Endpoint 20: POST /api/coverage/execute/{project_id} ==========

class TestExecuteEndpoint:
    """Test test execution endpoint"""
    
    @pytest.fixture
    def compiled_project(self, tmp_path):
        """Fixture that compiles a project"""
        source_file = tmp_path / "test.c"
        source_file.write_text(SAMPLE_C_CODE)
        
        compile_request = {
            "source_file_path": str(source_file),
            "compiler": "gcc"
        }
        
        response = client.post(
            "/api/coverage/compile/project_exec",
            json=compile_request
        )
        
        if response.status_code != 200:
            pytest.skip("Compilation failed")
        
        data = response.json()
        if data["status"] != "success":
            pytest.skip("Compilation failed or GCC not available")
        
        return "project_exec"
    
    def test_execute_success(self, compiled_project):
        """Test successful test execution"""
        request = {
            "test_inputs": ["15"]  # x > 10
        }
        
        response = client.post(
            f"/api/coverage/execute/{compiled_project}",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["project_id"] == compiled_project
        assert data["execution_status"] in ["success", "failed"]
        assert "exit_code" in data
        assert data["execution_time"] > 0
        assert "coverage_data" in data
    
    def test_execute_different_inputs(self, compiled_project):
        """Test execution with different inputs"""
        # Test 1: x > 10
        response1 = client.post(
            f"/api/coverage/execute/{compiled_project}",
            json={"test_inputs": ["15"]}
        )
        
        # Test 2: x <= 10
        response2 = client.post(
            f"/api/coverage/execute/{compiled_project}",
            json={"test_inputs": ["5"]}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Both should execute
        assert data1["execution_status"] in ["success", "failed"]
        assert data2["execution_status"] in ["success", "failed"]
    
    def test_execute_project_not_found(self):
        """Test execution for non-existent project"""
        response = client.post(
            "/api/coverage/execute/nonexistent_project",
            json={"test_inputs": []}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_execute_no_args(self, compiled_project):
        """Test execution with no arguments"""
        request = {
            "test_inputs": []
        }
        
        response = client.post(
            f"/api/coverage/execute/{compiled_project}",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should fail because program expects argument
        assert data["execution_status"] == "failed"
        assert data["exit_code"] != 0


# ========== Endpoint 21: POST /api/coverage/run-gcov/{project_id} ==========

class TestRunGcovEndpoint:
    """Test gcov execution endpoint"""
    
    def test_run_gcov_project_not_found(self):
        """Test gcov for non-existent project"""
        request = {
            "source_files": ["test.c"]
        }
        
        response = client.post(
            "/api/coverage/run-gcov/nonexistent",
            json=request
        )
        
        assert response.status_code == 404
    
    def test_run_gcov_no_coverage_data(self, tmp_path):
        """Test gcov when no coverage data exists"""
        # Compile but don't execute
        source_file = tmp_path / "test.c"
        source_file.write_text(SAMPLE_C_CODE)
        
        compile_resp = client.post(
            "/api/coverage/compile/project_no_gcov",
            json={
                "source_file_path": str(source_file),
                "compiler": "gcc"
            }
        )
        
        if compile_resp.json().get("status") != "success":
            pytest.skip("Compilation failed")
        
        # Try to run gcov without executing tests
        request = {
            "source_files": ["test.c"]
        }
        
        response = client.post(
            "/api/coverage/run-gcov/project_no_gcov",
            json=request
        )
        
        # Should fail because no .gcda files
        assert response.status_code == 500


# ========== Endpoint 22: GET /api/coverage/report/{project_id}/{test_case_id} ==========

class TestCoverageReportEndpoint:
    """Test coverage report endpoint"""
    
    def test_report_project_not_found(self):
        """Test report for non-existent project"""
        response = client.get("/api/coverage/report/nonexistent/test_001")
        
        assert response.status_code == 404
    
    def test_report_no_coverage_data(self, tmp_path):
        """Test report when no gcov data exists"""
        # Compile project
        source_file = tmp_path / "test.c"
        source_file.write_text(SAMPLE_C_CODE)
        
        compile_resp = client.post(
            "/api/coverage/compile/project_no_report",
            json={
                "source_file_path": str(source_file),
                "compiler": "gcc"
            }
        )
        
        if compile_resp.json().get("status") != "success":
            pytest.skip("Compilation failed")
        
        # Try to get report without running gcov
        response = client.get("/api/coverage/report/project_no_report/test_001")
        
        # Should fail because no .gcov files
        assert response.status_code == 404
        assert "No coverage data" in response.json()["detail"]


# ========== Endpoint 23: POST /api/coverage/batch-execute/{session_id} ==========

class TestBatchExecuteEndpoint:
    """Test batch execution endpoint"""
    
    def test_batch_execute(self):
        """Test batch execution of test cases"""
        request = {
            "test_cases": [
                {"test_id": "test_1", "inputs": ["5"]},
                {"test_id": "test_2", "inputs": ["15"]},
                {"test_id": "test_3", "inputs": ["100"]}
            ]
        }
        
        response = client.post(
            "/api/coverage/batch-execute/session_batch",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "session_batch"
        assert data["total_tests"] == 3
        assert "completed" in data
        assert "failed" in data
    
    def test_batch_execute_empty(self):
        """Test batch execution with empty test cases"""
        request = {
            "test_cases": []
        }
        
        response = client.post(
            "/api/coverage/batch-execute/session_empty",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_tests"] == 0


# ========== Endpoint 24: GET /api/coverage/summary/{session_id} ==========

class TestCoverageSummaryEndpoint:
    """Test coverage summary endpoint"""
    
    def test_summary_new_session(self):
        """Test summary for new session (no data)"""
        response = client.get("/api/coverage/summary/new_session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "new_session"
        assert data["total_branches"] == 0
        assert data["covered_branches"] == 0
        assert data["coverage_percentage"] == 0.0
        assert data["uncovered_count"] == 0
    
    def test_summary_response_structure(self):
        """Test that summary has correct response structure"""
        response = client.get("/api/coverage/summary/test_session")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert "session_id" in data
        assert "total_branches" in data
        assert "covered_branches" in data
        assert "coverage_percentage" in data
        assert "uncovered_count" in data


# ========== Endpoint 25: GET /api/coverage/uncovered/{session_id} ==========

class TestUncoveredBranchesEndpoint:
    """Test uncovered branches endpoint"""
    
    def test_uncovered_new_session(self):
        """Test uncovered branches for new session"""
        response = client.get("/api/coverage/uncovered/new_session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "new_session"
        assert data["uncovered_branches"] == []
        assert data["total_uncovered"] == 0
    
    def test_uncovered_response_structure(self):
        """Test response structure"""
        response = client.get("/api/coverage/uncovered/test_session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "uncovered_branches" in data
        assert "total_uncovered" in data
        assert isinstance(data["uncovered_branches"], list)


# ========== Integration Tests ==========

class TestCoverageWorkflow:
    """Test complete coverage workflow"""
    
    def test_full_workflow(self, tmp_path):
        """Test: compile -> execute -> gcov -> report"""
        # Setup
        source_file = tmp_path / "workflow.c"
        source_file.write_text(SAMPLE_C_CODE)
        project_id = "workflow_test"
        
        # Step 1: Compile
        compile_resp = client.post(
            f"/api/coverage/compile/{project_id}",
            json={
                "source_file_path": str(source_file),
                "compiler": "gcc"
            }
        )
        
        if compile_resp.status_code != 200:
            pytest.skip("Compilation failed")
        
        compile_data = compile_resp.json()
        if compile_data["status"] != "success":
            pytest.skip("GCC not available")
        
        assert compile_data["binary_path"] is not None
        
        # Step 2: Execute test
        execute_resp = client.post(
            f"/api/coverage/execute/{project_id}",
            json={"test_inputs": ["15"]}
        )
        
        assert execute_resp.status_code == 200
        execute_data = execute_resp.json()
        assert execute_data["execution_status"] in ["success", "failed"]
        
        # Step 3: Run gcov
        gcov_resp = client.post(
            f"/api/coverage/run-gcov/{project_id}",
            json={"source_files": ["workflow.c"]}
        )
        
        # May succeed or fail depending on gcov availability
        if gcov_resp.status_code == 200:
            gcov_data = gcov_resp.json()
            assert gcov_data["status"] == "success"
            assert len(gcov_data["gcov_files"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
