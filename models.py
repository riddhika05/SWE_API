from pydantic import BaseModel, Field
from typing import List, Optional, Any

# --- F1 MODELS (Code Analysis) ---
class SourceCodeInput(BaseModel):
    filename: str = Field(..., json_schema_extra={"example": "test.cpp"})
    source_code: str = Field(..., json_schema_extra={"example": "int main() { return 0; }"})

class CFGNode(BaseModel):
    node_id: int
    code_snippet: str
    is_entry: bool = False
    is_exit: bool = False

class CFGEdge(BaseModel):
    source_node_id: int
    target_node_id: int
    label: Optional[str] = None

class CFGOutput(BaseModel):
    cfg_id: str
    total_nodes: int
    nodes: List[CFGNode]
    edges: List[CFGEdge]
    complexity: int
    required_inputs: List[str] 

# --- F2 MODELS (Genetic Algorithm) ---
class GAConfigInput(BaseModel):
    cfg_id: str
    population_size: int = Field(50, ge=10, le=1000)

class EvolveInput(BaseModel):
    cfg_id: str
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8

# RENAMED: 'TestCaseChromosome' -> 'Chromosome' to stop Pytest confusion
class Chromosome(BaseModel):
    id: str
    genes: List[Any]
    fitness_score: float = 0.0

class PopulationOutput(BaseModel):
    generation_id: int
    status: str
    population_count: int
    individuals: List[Chromosome]