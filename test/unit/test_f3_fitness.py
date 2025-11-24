"""
Unit tests for F3: Fitness Evaluation Module (FastAPI Endpoints)
Tests endpoints 15-18 from project structure
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from f3_fitness_evaluation import router

# Create FastAPI app for testing
app = FastAPI()
app.include_router(router)

# Test client
client = TestClient(app)


# ========== Test Data ==========

SAMPLE_EVALUATE_REQUEST = {
    "test_cases": [
        {
            "test_id": "test_001",
            "inputs": ["10", "20"],
            "executed_branches": ["b1", "b2", "b3"]
        },
        {
            "test_id": "test_002",
            "inputs": ["5"],
            "executed_branches": ["b1", "b4"]
        },
        {
            "test_id": "test_003",
            "inputs": ["100"],
            "executed_branches": ["b1", "b2", "b3", "b5", "b6"]
        }
    ],
    "total_branches": 10
}


# ========== Endpoint 15: POST /api/fitness/evaluate/{session_id} ==========

class TestEvaluateFitness:
    """Test fitness evaluation endpoint"""
    
    def test_evaluate_fitness_success(self):
        """Test successful fitness evaluation"""
        response = client.post(
            "/api/fitness/evaluate/session_001",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "results" in data
        assert "summary" in data
        assert data["session_id"] == "session_001"
        
        # Verify results
        assert len(data["results"]) == 3
        
        # Check that test_003 has highest fitness (5 branches / 10 total = 0.5)
        assert data["results"][0]["test_id"] == "test_003"
        assert data["results"][0]["fitness_score"] == 0.5
        assert data["results"][0]["rank"] == 1
        assert data["results"][0]["branches_covered"] == 5
        
        # Verify sorting (descending by fitness)
        fitness_scores = [r["fitness_score"] for r in data["results"]]
        assert fitness_scores == sorted(fitness_scores, reverse=True)
        
        # Verify summary statistics
        summary = data["summary"]
        assert "average_fitness" in summary
        assert "max_fitness" in summary
        assert "min_fitness" in summary
        assert "unique_branches_covered" in summary
        assert summary["max_fitness"] == 0.5
        assert summary["unique_branches_covered"] == 6  # b1,b2,b3,b4,b5,b6
    
    def test_evaluate_fitness_empty_population(self):
        """Test fitness evaluation with empty population"""
        request = {
            "test_cases": [],
            "total_branches": 10
        }
        
        response = client.post(
            "/api/fitness/evaluate/session_empty",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 0
        assert data["summary"]["average_fitness"] == 0.0
        assert data["summary"]["max_fitness"] == 0.0
    
    def test_evaluate_fitness_zero_coverage(self):
        """Test with test cases that cover no branches"""
        request = {
            "test_cases": [
                {
                    "test_id": "test_zero",
                    "inputs": [],
                    "executed_branches": []
                }
            ],
            "total_branches": 10
        }
        
        response = client.post(
            "/api/fitness/evaluate/session_zero",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["results"][0]["fitness_score"] == 0.0
        assert data["results"][0]["branches_covered"] == 0
        assert data["results"][0]["coverage_percentage"] == 0.0
    
    def test_evaluate_fitness_full_coverage(self):
        """Test with 100% branch coverage"""
        request = {
            "test_cases": [
                {
                    "test_id": "test_full",
                    "inputs": ["data"],
                    "executed_branches": [f"b{i}" for i in range(5)]
                }
            ],
            "total_branches": 5
        }
        
        response = client.post(
            "/api/fitness/evaluate/session_full",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["results"][0]["fitness_score"] == 1.0
        assert data["results"][0]["coverage_percentage"] == 100.0
    
    def test_evaluate_fitness_invalid_request(self):
        """Test with invalid request (missing required fields)"""
        response = client.post(
            "/api/fitness/evaluate/session_invalid",
            json={"test_cases": []}  # Missing total_branches
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_evaluate_fitness_negative_total_branches(self):
        """Test with invalid total_branches value"""
        request = {
            "test_cases": [],
            "total_branches": -5  # Invalid
        }
        
        response = client.post(
            "/api/fitness/evaluate/session_neg",
            json=request
        )
        
        assert response.status_code == 422  # Validation error


# ========== Endpoint 16: GET /api/fitness/scores/{session_id} ==========

class TestGetFitnessScores:
    """Test get fitness scores endpoint"""
    
    def test_get_scores_success(self):
        """Test retrieving fitness scores for existing session"""
        # First, create a session by evaluating fitness
        client.post(
            "/api/fitness/evaluate/session_scores",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        # Now retrieve scores
        response = client.get("/api/fitness/scores/session_scores")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "session_scores"
        assert len(data["scores"]) == 3
        assert data["total_test_cases"] == 3
        
        # Verify scores are sorted
        scores = [s["fitness_score"] for s in data["scores"]]
        assert scores == sorted(scores, reverse=True)
    
    def test_get_scores_session_not_found(self):
        """Test retrieving scores for non-existent session"""
        response = client.get("/api/fitness/scores/nonexistent_session")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_scores_has_ranks(self):
        """Test that scores include rank information"""
        # Create session
        client.post(
            "/api/fitness/evaluate/session_ranks",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        # Get scores
        response = client.get("/api/fitness/scores/session_ranks")
        data = response.json()
        
        # Verify all results have ranks
        for score in data["scores"]:
            assert "rank" in score
            assert score["rank"] is not None
        
        # Verify ranks are sequential
        ranks = [s["rank"] for s in data["scores"]]
        assert ranks == list(range(1, len(ranks) + 1))


# ========== Endpoint 17: GET /api/fitness/best/{session_id} ==========

class TestGetBestTestCases:
    """Test get best test cases endpoint"""
    
    def test_get_best_default(self):
        """Test getting best test case (default top_n=1)"""
        # Setup session
        client.post(
            "/api/fitness/evaluate/session_best",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        # Get best test case
        response = client.get("/api/fitness/best/session_best")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "session_best"
        assert data["top_n"] == 1
        assert len(data["best_test_cases"]) == 1
        assert len(data["fitness_scores"]) == 1
        
        # Should be test_003 (highest fitness)
        assert data["best_test_cases"][0]["test_id"] == "test_003"
        assert data["fitness_scores"][0]["rank"] == 1
    
    def test_get_best_top_n(self):
        """Test getting top N best test cases"""
        # Setup session
        client.post(
            "/api/fitness/evaluate/session_top_n",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        # Get top 2
        response = client.get("/api/fitness/best/session_top_n?top_n=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["top_n"] == 2
        assert len(data["best_test_cases"]) == 2
        assert len(data["fitness_scores"]) == 2
        
        # Verify they're the top 2
        assert data["fitness_scores"][0]["rank"] == 1
        assert data["fitness_scores"][1]["rank"] == 2
    
    def test_get_best_all(self):
        """Test getting all test cases as best"""
        # Setup session
        client.post(
            "/api/fitness/evaluate/session_all",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        # Get all (top_n=10, more than we have)
        response = client.get("/api/fitness/best/session_all?top_n=10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return all 3
        assert len(data["best_test_cases"]) == 3
    
    def test_get_best_session_not_found(self):
        """Test getting best for non-existent session"""
        response = client.get("/api/fitness/best/nonexistent?top_n=1")
        
        assert response.status_code == 404
    
    def test_get_best_invalid_top_n(self):
        """Test with invalid top_n parameter"""
        # Setup session
        client.post(
            "/api/fitness/evaluate/session_invalid_n",
            json=SAMPLE_EVALUATE_REQUEST
        )
        
        # top_n must be >= 1
        response = client.get("/api/fitness/best/session_invalid_n?top_n=0")
        
        assert response.status_code == 422  # Validation error


# ========== Endpoint 18: POST /api/fitness/calculate/{project_id}/{test_case_id} ==========

class TestCalculateSingleFitness:
    """Test single fitness calculation endpoint"""
    
    def test_calculate_single_success(self):
        """Test calculating fitness for single test case"""
        request = {
            "test_case": {
                "test_id": "single_test",
                "inputs": ["42"],
                "executed_branches": ["b1", "b2", "b3", "b4"]
            },
            "total_branches": 20
        }
        
        response = client.post(
            "/api/fitness/calculate/project_001/single_test",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["project_id"] == "project_001"
        assert data["test_case_id"] == "single_test"
        assert data["fitness_score"] == 0.2  # 4/20
        assert data["branches_covered"] == 4
    
    def test_calculate_single_zero_coverage(self):
        """Test single test case with no coverage"""
        request = {
            "test_case": {
                "test_id": "zero_test",
                "inputs": [],
                "executed_branches": []
            },
            "total_branches": 10
        }
        
        response = client.post(
            "/api/fitness/calculate/project_002/zero_test",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["fitness_score"] == 0.0
        assert data["branches_covered"] == 0
    
    def test_calculate_single_full_coverage(self):
        """Test single test case with 100% coverage"""
        request = {
            "test_case": {
                "test_id": "full_test",
                "inputs": ["data"],
                "executed_branches": [f"b{i}" for i in range(10)]
            },
            "total_branches": 10
        }
        
        response = client.post(
            "/api/fitness/calculate/project_003/full_test",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["fitness_score"] == 1.0
        assert data["branches_covered"] == 10
    
    def test_calculate_single_invalid_request(self):
        """Test with invalid request"""
        response = client.post(
            "/api/fitness/calculate/project_004/test",
            json={}  # Missing required fields
        )
        
        assert response.status_code == 422


# ========== Integration Tests ==========

class TestFitnessWorkflow:
    """Test complete fitness evaluation workflow"""
    
    def test_full_workflow(self):
        """Test complete workflow: evaluate -> get scores -> get best"""
        session_id = "workflow_test"
        
        # Step 1: Evaluate fitness
        eval_response = client.post(
            f"/api/fitness/evaluate/{session_id}",
            json=SAMPLE_EVALUATE_REQUEST
        )
        assert eval_response.status_code == 200
        eval_data = eval_response.json()
        
        # Step 2: Get scores
        scores_response = client.get(f"/api/fitness/scores/{session_id}")
        assert scores_response.status_code == 200
        scores_data = scores_response.json()
        
        # Step 3: Get best test cases
        best_response = client.get(f"/api/fitness/best/{session_id}?top_n=2")
        assert best_response.status_code == 200
        best_data = best_response.json()
        
        # Verify consistency
        assert len(scores_data["scores"]) == len(eval_data["results"])
        assert best_data["best_test_cases"][0]["test_id"] == eval_data["results"][0]["test_id"]
        assert best_data["fitness_scores"][0]["fitness_score"] == eval_data["results"][0]["fitness_score"]
    
    def test_multiple_evaluations_same_session(self):
        """Test re-evaluating fitness for same session (should update)"""
        session_id = "multi_eval"
        
        # First evaluation
        first_response = client.post(
            f"/api/fitness/evaluate/{session_id}",
            json=SAMPLE_EVALUATE_REQUEST
        )
        assert first_response.status_code == 200
        
        # Second evaluation with different data
        new_request = {
            "test_cases": [
                {
                    "test_id": "new_test",
                    "inputs": ["x"],
                    "executed_branches": ["b1", "b2", "b3", "b4", "b5", "b6", "b7"]
                }
            ],
            "total_branches": 10
        }
        
        second_response = client.post(
            f"/api/fitness/evaluate/{session_id}",
            json=new_request
        )
        assert second_response.status_code == 200
        
        # Get scores - should reflect second evaluation
        scores_response = client.get(f"/api/fitness/scores/{session_id}")
        scores_data = scores_response.json()
        
        assert len(scores_data["scores"]) == 1
        assert scores_data["scores"][0]["test_id"] == "new_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
