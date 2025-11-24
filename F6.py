from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app = FastAPI()

class SuspiciousLine(BaseModel):
    file_name: str
    line_number: int
    suspiciousness: float

class ReportRequest(BaseModel):
    suspicious_lines: Optional[List[SuspiciousLine]] = None
    suspiciousness_scores: Optional[List[Dict[str, Any]]] = None
    default_file_name: Optional[str] = "tarantula_fault_localization.py"  # updated default

@app.post("/fault-localization/report")
def generate_fault_report(request: ReportRequest):
    """
    Generate a fault localization report.
    Automatically transforms F5 output if needed.
    Uses 'tarantula_fault_localization.py' as default file.
    """

    # Transform F5 output into F6 format if needed
    suspicious_lines = request.suspicious_lines or []
    if request.suspiciousness_scores:
        for item in request.suspiciousness_scores:
            suspicious_lines.append(SuspiciousLine(
                file_name=request.default_file_name,
                line_number=item["line_number"],
                suspiciousness=item["suspiciousness"]
            ))

    report = []
    for item in suspicious_lines:
        code_line = ""
        try:
            with open(item.file_name, "r") as f:
                lines = f.readlines()
                if 0 < item.line_number <= len(lines):
                    code_line = lines[item.line_number - 1].rstrip()
                else:
                    code_line = "<Line number out of range>"
        except FileNotFoundError:
            code_line = "<File not found>"
        except Exception as e:
            code_line = f"<Error reading file: {e}>"

        report.append({
            "file_name": item.file_name,
            "line_number": item.line_number,
            "code": code_line,
            "suspiciousness": round(item.suspiciousness, 4)
        })

    # Sort by suspiciousness descending
    report.sort(key=lambda x: x["suspiciousness"], reverse=True)
    return {"fault_localization_report": report}
