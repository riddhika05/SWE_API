"""
F3: Fitness Evaluation Module - FastAPI Endpoints
Implements endpoints 15-18 from project structure

SRS Requirements (Section 3.2.3):
- Calculate fitness score based on branch coverage
- Higher fitness for test cases covering new branches
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

# Router for F3 endpoints
router = APIRouter(prefix="/api/fitness", tags=["F3: Fitness Evaluation"])

# In-memory storage (replace with database in production)
session_data = {}


# ========== Pydantic Models ==========

class TestCaseInput(BaseModel):
    """Test case with executed branches"""
    test_id: str
    inputs: List[str]
    executed_branches: List[str] = Field(default_factory=list)


class FitnessScoreResult(BaseModel):
    """Fitness score for a test case"""
    test_id: str
    fitness_score: float
    branches_covered: int
    coverage_percentage: float
    rank: Optional[int] = None


class EvaluateRequest(BaseModel):
    """Request for fitness evaluation"""
    test_cases: List[TestCaseInput]
    total_branches: int = Field(gt=0)


class EvaluateResponse(BaseModel):
    """Response with fitness results"""
    session_id: str
    results: List[FitnessScoreResult]
    summary: Dict[str, float]


class ScoresResponse(BaseModel):
    """Response for fitness scores"""
    session_id: str
    scores: List[FitnessScoreResult]
    total_test_cases: int


class BestTestCasesResponse(BaseModel):
    """Response for best test cases"""
    session_id: str
    best_test_cases: List[TestCaseInput]
    fitness_scores: List[FitnessScoreResult]
    top_n: int


class SingleFitnessRequest(BaseModel):
    """Request for single fitness calculation"""
    test_case: TestCaseInput
    total_branches: int


class SingleFitnessResponse(BaseModel):
    """Response for single fitness"""
    project_id: str
    test_case_id: str
    fitness_score: float
    branches_covered: int


# ========== Core Functions (Internal) ==========

def calculate_fitness(test_case: TestCaseInput, total_branches: int) -> FitnessScoreResult:
    """
    Calculate fitness score based on branch coverage
    Fitness = branches_covered / total_branches
    """
    branches_covered = len(test_case.executed_branches)
    fitness_score = branches_covered / total_branches if total_branches > 0 else 0.0
    coverage_percentage = fitness_score * 100
    
    return FitnessScoreResult(
        test_id=test_case.test_id,
        fitness_score=round(fitness_score, 4),
        branches_covered=branches_covered,
        coverage_percentage=round(coverage_percentage, 2)
    )


def evaluate_branch_coverage(test_cases: List[TestCaseInput]) -> set:
    """Count unique covered branches across population"""
    all_branches = set()
    for tc in test_cases:
        all_branches.update(tc.executed_branches)
    return all_branches


def assign_fitness_scores(
    test_cases: List[TestCaseInput],
    total_branches: int
) -> List[FitnessScoreResult]:
    """Batch fitness calculation for population"""
    results = [calculate_fitness(tc, total_branches) for tc in test_cases]
    # Sort by fitness (descending) and assign ranks
    results.sort(key=lambda x: x.fitness_score, reverse=True)
    for rank, result in enumerate(results, start=1):
        result.rank = rank
    return results


def normalize_fitness(scores: List[FitnessScoreResult]) -> Dict[str, float]:
    """Calculate summary statistics"""
    if not scores:
        return {
            "average_fitness": 0.0,
            "max_fitness": 0.0,
            "min_fitness": 0.0
        }
    
    fitness_values = [s.fitness_score for s in scores]
    return {
        "average_fitness": round(sum(fitness_values) / len(fitness_values), 4),
        "max_fitness": round(max(fitness_values), 4),
        "min_fitness": round(min(fitness_values), 4)
    }


# ========== API Endpoints ==========

@router.post("/evaluate/{session_id}", response_model=EvaluateResponse)
async def evaluate_fitness(session_id: str, request: EvaluateRequest):
    """
    Endpoint 15: POST /api/fitness/evaluate/{session_id}
    
    Evaluate fitness for all test cases in the population.
    Fitness based on branch coverage - higher scores for more branches covered.
    """
    try:
        # Calculate fitness for all test cases
        results = assign_fitness_scores(request.test_cases, request.total_branches)
        
        # Calculate summary statistics
        summary = normalize_fitness(results)
        
        # Track unique branches covered
        unique_branches = evaluate_branch_coverage(request.test_cases)
        summary["unique_branches_covered"] = len(unique_branches)
        summary["population_coverage_percentage"] = round(
            len(unique_branches) / request.total_branches * 100, 2
        ) if request.total_branches > 0 else 0.0
        
        # Store in session
        session_data[session_id] = {
            "test_cases": request.test_cases,
            "results": results,
            "total_branches": request.total_branches,
            "timestamp": datetime.now().isoformat()
        }
        
        return EvaluateResponse(
            session_id=session_id,
            results=results,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fitness evaluation error: {str(e)}")


@router.get("/scores/{session_id}", response_model=ScoresResponse)
async def get_fitness_scores(session_id: str):
    """
    Endpoint 16: GET /api/fitness/scores/{session_id}
    
    Get fitness scores for current population.
    Returns list of test cases with fitness values.
    """
    if session_id not in session_data:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    data = session_data[session_id]
    
    return ScoresResponse(
        session_id=session_id,
        scores=data["results"],
        total_test_cases=len(data["results"])
    )


@router.get("/best/{session_id}", response_model=BestTestCasesResponse)
async def get_best_test_cases(
    session_id: str,
    top_n: int = Query(default=1, ge=1, description="Number of top test cases")
):
    """
    Endpoint 17: GET /api/fitness/best/{session_id}
    
    Get best test case(s) by fitness.
    Returns top N test cases sorted by fitness score.
    """
    if session_id not in session_data:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    data = session_data[session_id]
    results = data["results"][:top_n]  # Already sorted by fitness
    
    # Get corresponding test cases
    test_case_map = {tc.test_id: tc for tc in data["test_cases"]}
    best_cases = [test_case_map[r.test_id] for r in results if r.test_id in test_case_map]
    
    return BestTestCasesResponse(
        session_id=session_id,
        best_test_cases=best_cases,
        fitness_scores=results,
        top_n=top_n
    )


@router.post("/calculate/{project_id}/{test_case_id}", response_model=SingleFitnessResponse)
async def calculate_single_fitness(
    project_id: str,
    test_case_id: str,
    request: SingleFitnessRequest
):
    """
    Endpoint 18: POST /api/fitness/calculate/{project_id}/{test_case_id}
    
    Calculate fitness for single test case.
    Returns fitness score and branches covered.
    """
    try:
        result = calculate_fitness(request.test_case, request.total_branches)
        
        return SingleFitnessResponse(
            project_id=project_id,
            test_case_id=test_case_id,
            fitness_score=result.fitness_score,
            branches_covered=result.branches_covered
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fitness calculation error: {str(e)}")


# For standalone testing
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI(title="F3 Fitness Evaluation API")
    app.include_router(router)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
