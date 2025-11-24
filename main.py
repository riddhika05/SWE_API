from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uuid
import random
# Add at top:
from f3_fitness_evaluation import router as f3_router
from f4_coverage_execution import router as f4_router
from tarantula_fault_localization import tara
# After app creation:

from models import (
    SourceCodeInput, CFGOutput, CFGNode, CFGEdge, 
    GAConfigInput, EvolveInput, PopulationOutput, Chromosome
)
from database import stored_cfgs, active_populations
from cfg_parser import analyze_cpp_code
import genetic_engine as engine

app = FastAPI(title="Automated Test Case Generator")
# Add CORS from integration branch at the top:

app.include_router(f3_router)
app.include_router(f4_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://swe-nu.vercel.app", "https://swe-nu.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Returns a simple status message for health checks and CORS tests."""
    return {"status": "ok", "message": "API is running"}
# --- F1 ENDPOINT: PARSE CODE ---
@app.post("/analysis/generate-cfg", response_model=CFGOutput, status_code=status.HTTP_201_CREATED, tags=["F1"])
async def generate_cfg(data: SourceCodeInput):
    if not data.source_code.strip():
        raise HTTPException(status_code=400, detail="Source code empty")

    try:
        # 1. Run Logic (cfg_parser.py)
        result = analyze_cpp_code(data.source_code)
        
        # 2. Map Logic result to API Models
        final_nodes = [CFGNode(**n) for n in result["nodes"]]
        final_edges = [CFGEdge(**e) for e in result["edges"]]
        
        # Calculate Complexity (Count decision points)
        decision_points = ["If", "Loop", "Switch"]
        complexity = len([n for n in final_nodes if any(d in n.code_snippet for d in decision_points)]) + 1

        output = CFGOutput(
            cfg_id=str(uuid.uuid4()),
            total_nodes=len(final_nodes),
            nodes=final_nodes,
            edges=final_edges,
            complexity=complexity,
            required_inputs=result["params"] # This is sent to F2
        )
        
        # 3. Save to DB
        stored_cfgs[output.cfg_id] = output
        return output

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- F2 ENDPOINT: INITIALIZE POPULATION ---
@app.post("/ga/initialize", response_model=PopulationOutput, status_code=status.HTTP_201_CREATED, tags=["F2"])
async def initialize_population(config: GAConfigInput):
    if config.cfg_id not in stored_cfgs:
        raise HTTPException(status_code=404, detail="CFG not found")
    
    # 1. Get the required inputs detected by F1
    cfg_data = stored_cfgs[config.cfg_id]
    required_params = cfg_data.required_inputs # e.g. ['int', 'int']

    # 2. Create Random Population (genetic_engine.py)
    individuals = []
    for _ in range(config.population_size):
        genes = [engine.generate_random_gene(p_type) for p_type in required_params]
        # FIXED: Used 'Chromosome' instead of 'TestCaseChromosome'
        individuals.append(Chromosome(id=str(uuid.uuid4())[:8], genes=genes))

    output = PopulationOutput(
        generation_id=0,
        status="Initialized",
        population_count=len(individuals),
        individuals=individuals
    )
    
    active_populations[config.cfg_id] = output
    return output


# --- F2 ENDPOINT: EVOLVE POPULATION ---
@app.post("/ga/evolve", response_model=PopulationOutput, tags=["F2"])
async def evolve_population(data: EvolveInput):
    if data.cfg_id not in active_populations:
        raise HTTPException(status_code=404, detail="Population not found")
    
    current_output = active_populations[data.cfg_id]
    population = current_output.individuals

    # 1. Evaluate Fitness
    for ind in population:
        ind.fitness_score = engine.calculate_fitness_mock(ind)
    
    # Sort by best fitness
    population.sort(key=lambda x: x.fitness_score, reverse=True)

    # 2. Create Next Generation
    next_gen = []
    # Elitism: Keep top 2
    next_gen.extend(population[:2])

    while len(next_gen) < len(population):
        p1 = engine.tournament_selection(population)
        p2 = engine.tournament_selection(population)
        
        if random.random() < data.crossover_rate:
            child = engine.crossover(p1, p2)
        else:
            child = p1
            child.id = str(uuid.uuid4())[:8]
        
        engine.mutate(child, data.mutation_rate)
        next_gen.append(child)

    new_gen_id = current_output.generation_id + 1
    output = PopulationOutput(
        generation_id=new_gen_id,
        status=f"Evolved Gen {new_gen_id}",
        population_count=len(next_gen),
        individuals=next_gen
    )

    active_populations[data.cfg_id] = output
    return output