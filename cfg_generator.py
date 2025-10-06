from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class CFGNode(BaseModel):
    id: int
    lines: List[str]
    type: str
    label: Optional[str] = None

class CFGEdge(BaseModel):
    from_node: int
    to_node: int
    label: str
    color: str

def generate_cfg_from_ir(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes = []
    edges = []

    node_id = 0

    def next_id():
        nonlocal node_id
        nid = node_id
        node_id += 1
        return nid

    # Create nodes from blocks
    for block in blocks:
        if block["type"] == "decision":
            nodes.append(CFGNode(id=next_id(), lines=[block["condition"]], type="decision", label=block["condition"]))
        else:
            nodes.append(CFGNode(id=next_id(), lines=block.get("lines", []), type="statement"))

    # Add entry and exit nodes
    entry_node = CFGNode(id=next_id(), lines=[], type="entry", label="START")
    exit_node = CFGNode(id=next_id(), lines=[], type="exit", label="EXIT")
    nodes.insert(0, entry_node)
    nodes.append(exit_node)

    # Build edges
    for i in range(len(nodes) - 1):
        current = nodes[i]
        next_node = nodes[i + 1]
        if current.type == "decision":
            edges.append(CFGEdge(from_node=current.id, to_node=next_node.id, label="True", color="#22c55e"))
            if i + 2 < len(nodes):
                edges.append(CFGEdge(from_node=current.id, to_node=nodes[i + 2].id, label="False", color="#ef4444"))
        else:
            edges.append(CFGEdge(from_node=current.id, to_node=next_node.id, label="", color="#6b7280"))

    return {
        "nodes": [node.dict() for node in nodes],
        "edges": [edge.dict() for edge in edges]
    }
