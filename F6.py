from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os # Import os for potential file path manipulation

# 1. Define the router instance for F6
router = APIRouter(
    tags=["Fault Localization Report"],
    prefix="/fault-localization" # This prefix will be combined with the one in main.py (/api)
)

# 2. Define Pydantic Models
class SuspiciousLine(BaseModel):
    # Note: Use os.path.normpath to ensure path is correctly handled on different systems
    file_name: str
    line_number: int
    suspiciousness: float

class ReportRequest(BaseModel):
    # This allows direct input (if Tarantula was run elsewhere)
    suspicious_lines: Optional[List[SuspiciousLine]] = None
    # This allows raw F5 output (suspiciousness_scores) to be passed
    suspiciousness_scores: Optional[List[Dict[str, Any]]] = None
    # Default file name is required for F5 output that doesn't specify file names
    default_file_name: Optional[str] = "tarantula_fault_localization.py" 

# 3. Define the Endpoint using the router
@router.post("/report")
def generate_fault_report(request: ReportRequest):
    """
    Generate a fault localization report.
    Automatically transforms F5 output if needed.
    Reads code lines from source files based on suspiciousness scores.
    """

    # --- Step 1: Normalize all input into a List of SuspiciousLine objects ---
    suspicious_lines = request.suspicious_lines or []
    if request.suspiciousness_scores:
        for item in request.suspiciousness_scores:
            # Create a SuspiciousLine object from the raw score data
            suspicious_lines.append(SuspiciousLine(
                file_name=request.default_file_name,
                line_number=item["line_number"],
                suspiciousness=item["suspiciousness"]
            ))

    # --- Step 2: Read Code Lines and Build Report ---
    report = []
    
    # Store lines read to avoid reading the same file multiple times
    file_cache: Dict[str, List[str]] = {}
    
    for item in suspicious_lines:
        code_line = ""
        
        # Determine the file to read (use os.path.normpath for safety)
        file_path = os.path.normpath(item.file_name)
        
        try:
            # Check cache first
            if file_path not in file_cache:
                with open(file_path, "r") as f:
                    file_cache[file_path] = f.readlines()
            
            lines = file_cache[file_path]
            
            # Check line number range
            if 0 < item.line_number <= len(lines):
                # Read the line (Python lists are 0-indexed, line numbers are 1-indexed)
                code_line = lines[item.line_number - 1].rstrip()
            else:
                code_line = "<Line number out of range>"
                
        except FileNotFoundError:
            code_line = "<File not found>"
        except Exception as e:
            # Catch other potential file reading errors
            code_line = f"<Error reading file: {e}>"

        report.append({
            "file_name": item.file_name,
            "line_number": item.line_number,
            "code": code_line,
            "suspiciousness": round(item.suspiciousness, 4)
        })

    # --- Step 3: Sort and Return ---
    # Sort the final report by suspiciousness descending
    report.sort(key=lambda x: x["suspiciousness"], reverse=True)
    
    return {"fault_localization_report": report}