from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from parser import parse_c_code
from cfg_generator import generate_cfg_from_ir
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend URL(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class CodeInput(BaseModel):
    c_code: str

@app.post("/generate-cfg", response_model=Dict[str, Any])
async def generate_cfg_endpoint(code_input: CodeInput):
    try:
        parsed_blocks = parse_c_code(code_input.c_code)
        cfg = generate_cfg_from_ir(parsed_blocks)
        return cfg
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



