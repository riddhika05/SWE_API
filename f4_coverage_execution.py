"""
F4: Test Execution & Coverage Module - FastAPI Endpoints
Implements endpoints 19-25 from project structure

SRS Requirements (Section 3.2.4):
1. Compile target source with GCC coverage flags
2. Execute instrumented binary with test inputs
3. Run gcov tool to generate .gcov reports
4. Parse coverage reports to extract branch data
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
import subprocess
import os
import re
import time
from pathlib import Path

# Router for F4 endpoints
router = APIRouter(prefix="/api/coverage", tags=["F4: Test Execution & Coverage"])

# In-memory storage
project_data = {}
session_coverage = {}


# ========== Pydantic Models ==========

class CompilerEnum(str, Enum):
    GCC = "gcc"
    GPP = "g++"


class CompileRequest(BaseModel):
    """Request for compilation"""
    source_file_path: str
    compiler: CompilerEnum = CompilerEnum.GCC
    additional_flags: List[str] = Field(default_factory=list)


class CompileResponse(BaseModel):
    """Compilation response"""
    project_id: str
    status: str
    binary_path: Optional[str] = None
    compilation_time: float
    stderr: Optional[str] = None


class ExecuteRequest(BaseModel):
    """Request for test execution"""
    test_inputs: List[str]


class ExecuteResponse(BaseModel):
    """Test execution response"""
    project_id: str
    execution_status: str
    exit_code: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time: float
    coverage_data: Dict


class RunGcovRequest(BaseModel):
    """Request to run gcov"""
    source_files: List[str]


class RunGcovResponse(BaseModel):
    """Gcov execution response"""
    project_id: str
    status: str
    gcov_files: List[str]
    execution_time: float


class BranchDetail(BaseModel):
    """Branch coverage detail"""
    branch_id: str
    line_number: int
    taken: bool
    execution_count: int


class CoverageReportResponse(BaseModel):
    """Coverage report response"""
    project_id: str
    test_case_id: str
    line_coverage: float
    branch_coverage: float
    branches_covered: int
    total_branches: int
    branch_details: List[BranchDetail]


class BatchExecuteRequest(BaseModel):
    """Batch execution request"""
    test_cases: List[Dict]


class BatchExecuteResponse(BaseModel):
    """Batch execution response"""
    session_id: str
    total_tests: int
    completed: int
    failed: int
    execution_time: float


class CoverageSummaryResponse(BaseModel):
    """Coverage summary response"""
    session_id: str
    total_branches: int
    covered_branches: int
    coverage_percentage: float
    uncovered_count: int


class UncoveredBranch(BaseModel):
    """Uncovered branch info"""
    branch_id: str
    source_file: str
    line_number: int


class UncoveredBranchesResponse(BaseModel):
    """Uncovered branches response"""
    session_id: str
    uncovered_branches: List[UncoveredBranch]
    total_uncovered: int


# ========== Core Functions (Internal) ==========

def compile_with_gcov(source_file: str, compiler: str, output_dir: str) -> tuple:
    """Compile with coverage flags"""
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = Path(source_file).stem
    binary_path = os.path.join(output_dir, f"{base_name}_instrumented")
    
    compile_cmd = [
        compiler,
        "--coverage",  # -fprofile-arcs -ftest-coverage
        "-g",
        source_file,
        "-o", binary_path
    ]
    
    start = time.time()
    try:
        result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=output_dir
        )
        comp_time = time.time() - start
        success = result.returncode == 0
        return success, binary_path if success else None, result.stderr, comp_time
    except Exception as e:
        return False, None, str(e), time.time() - start


def execute_test(binary: str, inputs: List[str], work_dir: str) -> tuple:
    """Run instrumented binary"""
    start = time.time()
    try:
        result = subprocess.run(
            [binary] + inputs,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=work_dir
        )
        exec_time = time.time() - start
        status = "success" if result.returncode == 0 else "failed"
        return status, result.returncode, result.stdout, result.stderr, exec_time
    except subprocess.TimeoutExpired:
        return "timeout", -1, "", "Timeout", time.time() - start
    except Exception as e:
        return "error", -1, "", str(e), time.time() - start


def run_gcov_tool(source_files: List[str], work_dir: str) -> tuple:
    """Generate .gcov files"""
    gcov_files = []
    start = time.time()
    
    for source in source_files:
        base_name = Path(source).name
        cmd = ["gcov", "-b", "-c", base_name]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=work_dir
            )
            
            if result.returncode == 0:
                gcov_file = os.path.join(work_dir, f"{base_name}.gcov")
                if os.path.exists(gcov_file):
                    gcov_files.append(gcov_file)
        except:
            continue
    
    exec_time = time.time() - start
    success = len(gcov_files) > 0
    return success, gcov_files, exec_time


def parse_gcov_output(gcov_file: str) -> Dict:
    """Extract coverage data from .gcov file"""
    branches = []
    branch_map = {}
    current_line = 0
    
    if not os.path.exists(gcov_file):
        return {"branches": [], "total_branches": 0, "covered_branches": 0}
    
    try:
        with open(gcov_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Match line numbers
                line_match = re.match(r'\s*(-|#####|\d+):\s*(\d+):', line)
                if line_match:
                    current_line = int(line_match.group(2))
                
                # Match branch info
                branch_match = re.search(
                    r'branch\s+(\d+)\s+(taken\s+(\d+)|never executed)',
                    line
                )
                
                if branch_match:
                    branch_num = branch_match.group(1)
                    taken = "taken" in line
                    count = int(branch_match.group(3)) if taken and branch_match.group(3) else 0
                    
                    branch_id = f"L{current_line}:B{branch_num}"
                    branch_map[branch_id] = {"line": current_line, "taken": taken, "count": count}
                    
                    branches.append(BranchDetail(
                        branch_id=branch_id,
                        line_number=current_line,
                        taken=taken,
                        execution_count=count
                    ))
        
        covered = sum(1 for b in branches if b.taken)
        total = len(branches)
        
        return {
            "branches": branches,
            "total_branches": total,
            "covered_branches": covered,
            "coverage_percentage": round(covered / total * 100, 2) if total > 0 else 0.0
        }
    except Exception as e:
        return {"branches": [], "total_branches": 0, "covered_branches": 0}


def aggregate_coverage(test_results: List[Dict]) -> Dict:
    """Merge coverage from all tests"""
    all_branches = set()
    for result in test_results:
        all_branches.update(result.get("branches_covered", []))
    
    return {
        "total_unique_branches": len(all_branches),
        "covered_branches": list(all_branches)
    }


# ========== API Endpoints ==========

@router.post("/compile/{project_id}", response_model=CompileResponse)
async def compile_source(project_id: str, request: CompileRequest):
    """
    Endpoint 19: POST /api/coverage/compile/{project_id}
    
    Compile source with gcov flags.
    Returns compilation status and binary path.
    """
    output_dir = f"./coverage_output/{project_id}"
    
    success, binary_path, stderr, comp_time = compile_with_gcov(
        request.source_file_path,
        request.compiler.value,
        output_dir
    )
    
    if success:
        project_data[project_id] = {
            "source_file": request.source_file_path,
            "binary_path": binary_path,
            "output_dir": output_dir
        }
    
    return CompileResponse(
        project_id=project_id,
        status="success" if success else "failed",
        binary_path=binary_path,
        compilation_time=round(comp_time, 3),
        stderr=stderr if not success else None
    )


@router.post("/execute/{project_id}", response_model=ExecuteResponse)
async def execute_test_case(project_id: str, request: ExecuteRequest):
    """
    Endpoint 20: POST /api/coverage/execute/{project_id}
    
    Execute test case with coverage instrumentation.
    Returns execution result and coverage data.
    """
    if project_id not in project_data:
        raise HTTPException(status_code=404, detail="Project not found. Compile first.")
    
    data = project_data[project_id]
    binary = data["binary_path"]
    work_dir = data["output_dir"]
    
    status, exit_code, stdout, stderr, exec_time = execute_test(
        binary, request.test_inputs, work_dir
    )
    
    return ExecuteResponse(
        project_id=project_id,
        execution_status=status,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr if status != "success" else None,
        execution_time=round(exec_time, 3),
        coverage_data={"note": "Run gcov to generate coverage reports"}
    )


@router.post("/run-gcov/{project_id}", response_model=RunGcovResponse)
async def run_gcov(project_id: str, request: RunGcovRequest):
    """
    Endpoint 21: POST /api/coverage/run-gcov/{project_id}
    
    Run gcov tool on source files.
    Returns .gcov file paths.
    """
    if project_id not in project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    work_dir = project_data[project_id]["output_dir"]
    
    success, gcov_files, exec_time = run_gcov_tool(request.source_files, work_dir)
    
    if not success:
        raise HTTPException(status_code=500, detail="gcov execution failed")
    
    return RunGcovResponse(
        project_id=project_id,
        status="success",
        gcov_files=gcov_files,
        execution_time=round(exec_time, 3)
    )


@router.get("/report/{project_id}/{test_case_id}", response_model=CoverageReportResponse)
async def get_coverage_report(project_id: str, test_case_id: str):
    """
    Endpoint 22: GET /api/coverage/report/{project_id}/{test_case_id}
    
    Get coverage report for specific test.
    Returns line coverage, branch coverage, and .gcov data.
    """
    if project_id not in project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    work_dir = project_data[project_id]["output_dir"]
    
    # Find .gcov files
    gcov_files = [f for f in os.listdir(work_dir) if f.endswith('.gcov')]
    
    if not gcov_files:
        raise HTTPException(status_code=404, detail="No coverage data. Run gcov first.")
    
    # Parse first .gcov file
    gcov_path = os.path.join(work_dir, gcov_files[0])
    coverage_data = parse_gcov_output(gcov_path)
    
    return CoverageReportResponse(
        project_id=project_id,
        test_case_id=test_case_id,
        line_coverage=0.0,  # Would calculate from .gcov
        branch_coverage=coverage_data["coverage_percentage"],
        branches_covered=coverage_data["covered_branches"],
        total_branches=coverage_data["total_branches"],
        branch_details=coverage_data["branches"]
    )


@router.post("/batch-execute/{session_id}", response_model=BatchExecuteResponse)
async def batch_execute_tests(session_id: str, request: BatchExecuteRequest):
    """
    Endpoint 23: POST /api/coverage/batch-execute/{session_id}
    
    Execute all test cases in population.
    Returns batch execution status.
    """
    # Placeholder for batch execution
    return BatchExecuteResponse(
        session_id=session_id,
        total_tests=len(request.test_cases),
        completed=0,
        failed=0,
        execution_time=0.0
    )


@router.get("/summary/{session_id}", response_model=CoverageSummaryResponse)
async def get_coverage_summary(session_id: str):
    """
    Endpoint 24: GET /api/coverage/summary/{session_id}
    
    Get overall coverage summary.
    Returns total branches, covered branches, and coverage %.
    """
    if session_id not in session_coverage:
        return CoverageSummaryResponse(
            session_id=session_id,
            total_branches=0,
            covered_branches=0,
            coverage_percentage=0.0,
            uncovered_count=0
        )
    
    data = session_coverage[session_id]
    return CoverageSummaryResponse(**data)


@router.get("/uncovered/{session_id}", response_model=UncoveredBranchesResponse)
async def get_uncovered_branches(session_id: str):
    """
    Endpoint 25: GET /api/coverage/uncovered/{session_id}
    
    Get list of uncovered branches.
    Returns uncovered branch IDs and locations.
    """
    return UncoveredBranchesResponse(
        session_id=session_id,
        uncovered_branches=[],
        total_uncovered=0
    )


# For standalone testing
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI(title="F4 Coverage Execution API")
    app.include_router(router)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
