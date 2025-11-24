from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from genetic_engine import crossover, mutate, Chromosome 

client = TestClient(app)

# --- API INTEGRATION TESTS ---

def test_ga_lifecycle_flow():
    """
    F2 Check: Full flow from creating a graph to evolving a population.
    """
    # 1. Setup: Create a CFG first (F2 needs a CFG ID)
    cfg_payload = {
        "filename": "loop.cpp",
        "source_code": "void loop(int n) { while(n < 10) n++; }"
    }
    response_cfg = client.post("/analysis/generate-cfg", json=cfg_payload)
    cfg_id = response_cfg.json()["cfg_id"]
    
    # 2. Test Initialization
    init_payload = {
        "cfg_id": cfg_id,
        "population_size": 10
    }
    response_init = client.post("/ga/initialize", json=init_payload)
    
    assert response_init.status_code == 201
    init_data = response_init.json()
    
    assert init_data["generation_id"] == 0
    assert init_data["population_count"] == 10
    # 'void loop(int n)' has 1 input, so genes length should be 1
    assert len(init_data["individuals"][0]["genes"]) == 1

    # 3. Test Evolution
    evolve_payload = {
        "cfg_id": cfg_id,
        "mutation_rate": 0.1,
        "crossover_rate": 0.8
    }
    response_evolve = client.post("/ga/evolve", json=evolve_payload)
    
    assert response_evolve.status_code == 200
    evolve_data = response_evolve.json()
    
    assert evolve_data["generation_id"] == 1
    assert evolve_data["population_count"] == 10


# --- UNIT TESTS (ALGORITHM LOGIC) ---

def test_crossover_logic():
    """
    F2 Check: Does the math for mixing genes work?
    """
    # Parent 1: [0, 0, 0, 0]
    p1 = Chromosome(id="p1", genes=[0, 0, 0, 0])
    # Parent 2: [1, 1, 1, 1]
    p2 = Chromosome(id="p2", genes=[1, 1, 1, 1])
    
    child = crossover(p1, p2)
    
    # Child must have same length
    assert len(child.genes) == 4
    
def test_mutation_logic():
    """
    F2 Check: Does mutation actually change values?
    """
    ind = Chromosome(id="test", genes=[50, 50, 50])
    
    # Force mutation with rate 1.0 (100% chance)
    mutate(ind, rate=1.0)
    
    # Values should have changed
    assert ind.genes != [50, 50, 50]