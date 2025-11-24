import random
import uuid
from typing import List
from models import Chromosome

def generate_random_gene(param_type: str):
    """
    Generates a random gene based on the expected C++ type.
    """
    if "int" in param_type:
        return random.randint(-100, 100)
    elif "float" in param_type or "double" in param_type:
        return round(random.uniform(-100.0, 100.0), 2)
    elif "bool" in param_type:
        return random.choice([0, 1])
    return 0 

def calculate_fitness_mock(chromosome: Chromosome) -> float:
    """
    MOCK Fitness: Returns a random score.
    TODO: Replace with real 'gcov' coverage analysis later.
    """
    return round(random.uniform(0.1, 0.9), 2)

def tournament_selection(population: List[Chromosome]) -> Chromosome:
    """
    Selects the best individual from a random subgroup (Tournament Size = 3).
    """
    k = 3
    competitors = random.sample(population, k=min(k, len(population)))
    return max(competitors, key=lambda c: c.fitness_score)

def crossover(p1: Chromosome, p2: Chromosome) -> Chromosome:
    """
    Single-Point Crossover: Combines half of P1 with half of P2.
    """
    if len(p1.genes) < 2:
        return p1 # Cannot crossover a single gene, just return parent
    
    point = random.randint(1, len(p1.genes) - 1)
    new_genes = p1.genes[:point] + p2.genes[point:]
    
    return Chromosome(
        id=str(uuid.uuid4())[:8],
        genes=new_genes,
        fitness_score=0.0
    )

def mutate(chromosome: Chromosome, rate: float):
    """
    Randomly modifies genes to maintain diversity.
    Now supports INT and FLOAT mutations.
    """
    for i in range(len(chromosome.genes)):
        if random.random() < rate:
            val = chromosome.genes[i]
            
            # Mutate Integers (e.g. 5 -> 8)
            if isinstance(val, int) and not isinstance(val, bool):
                chromosome.genes[i] += random.randint(-5, 5)
                
            # Mutate Floats (e.g. 5.5 -> 5.7)
            elif isinstance(val, float):
                chromosome.genes[i] = round(val + random.uniform(-5.0, 5.0), 2)
                
            # Mutate Booleans (Flip 0 -> 1)
            elif isinstance(val, bool) or val in [0, 1]: 
                 # In Python bool is int subclass, so explicit check helps
                 chromosome.genes[i] = 1 - val