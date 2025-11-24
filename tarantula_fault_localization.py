from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

class LineCoverage(BaseModel):
    line_number: int
    tests_executed: List[str]

class FaultLocalizationRequest(BaseModel):
    coverage_data: List[LineCoverage]
    test_results: Dict[str, str] 


def tarantula_score(failed, passed, total_failed, total_passed):
    if failed == 0 and passed == 0:
        return 0.0

    failed_ratio = failed / total_failed if total_failed > 0 else 0
    passed_ratio = passed / total_passed if total_passed > 0 else 0

    denom = failed_ratio + passed_ratio
    if denom == 0:
        return 0.0

    return failed_ratio / denom

@app.post("/fault-localization/tarantula")
def apply_tarantula(request: FaultLocalizationRequest):

    # Count totals for Tarantula percentage calculation
    total_failed = sum(1 for status in request.test_results.values() if status == "fail")
    total_passed = sum(1 for status in request.test_results.values() if status == "pass")

    suspicious_lines = []

    for entry in request.coverage_data:
        failed_count = 0
        passed_count = 0

        # Count how many passing and failing tests executed this line
        for test in entry.tests_executed:
            if test not in request.test_results:
                continue

            if request.test_results[test] == "fail":
                failed_count += 1
            elif request.test_results[test] == "pass":
                passed_count += 1

        # Apply Tarantula formula
        score = tarantula_score(
            failed_count,
            passed_count,
            total_failed,
            total_passed
        )

        suspicious_lines.append({
            "line_number": entry.line_number,
            "failed_count": failed_count,
            "passed_count": passed_count,
            "suspiciousness": round(score, 4)
        })

   

    return {
        "suspiciousness_scores": suspicious_lines, 
        "total_failed_tests": total_failed,
        "total_passed_tests": total_passed
    }

