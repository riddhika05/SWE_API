import clang.cindex
from typing import Dict, Any

# --- WINDOWS USERS UNCOMMENT THIS IF LLVM IS NOT FOUND ---
# clang.cindex.Config.set_library_path(r'C:\Program Files\LLVM\bin')

def analyze_cpp_code(source_code: str) -> Dict[str, Any]:
    """
    Parses C++ code using LibClang.
    Returns: nodes, edges, and detected parameters.
    """
    index = clang.cindex.Index.create()
    # We use a virtual file 'temp.cpp'
    args = ['-std=c++11']
    unsaved_files = [('temp.cpp', source_code)]
    
    try:
        tu = index.parse('temp.cpp', args=args, unsaved_files=unsaved_files)
    except Exception as e:
        raise Exception(f"Clang Error: {e}")

    nodes = []
    edges = []
    params = []

    # Mapping Clang Cursors to readable names
    control_cursors = {
        clang.cindex.CursorKind.IF_STMT: "If Statement",
        clang.cindex.CursorKind.FOR_STMT: "For Loop",
        clang.cindex.CursorKind.WHILE_STMT: "While Loop",
        clang.cindex.CursorKind.SWITCH_STMT: "Switch Case",
        clang.cindex.CursorKind.RETURN_STMT: "Return",
        clang.cindex.CursorKind.FUNCTION_DECL: "Function Entry",
        clang.cindex.CursorKind.VAR_DECL: "Variable Decl"
    }

    node_counter = 1

    def walk_ast(cursor, parent_id=None):
        nonlocal node_counter
        current_id = None

        # LOGIC 1: Detect Function Arguments (Required for F2)
        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            for child in cursor.get_children():
                if child.kind == clang.cindex.CursorKind.PARM_DECL:
                    # Capture the type (e.g., "int")
                    params.append(child.type.spelling)

        # LOGIC 2: Build Control Flow Graph (Required for F1)
        if cursor.kind in control_cursors:
            current_id = node_counter
            node_counter += 1
            
            nodes.append({
                "node_id": current_id,
                "code_snippet": control_cursors[cursor.kind],
                "is_entry": cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL,
                "is_exit": cursor.kind == clang.cindex.CursorKind.RETURN_STMT
            })
            
            if parent_id is not None:
                edges.append({
                    "source_node_id": parent_id,
                    "target_node_id": current_id,
                    "label": "next"
                })
        
        # Helper to pass the correct parent ID down the tree
        next_parent = current_id if current_id is not None else parent_id
        
        for child in cursor.get_children():
            walk_ast(child, next_parent)

    walk_ast(tu.cursor)
    
    return {"nodes": nodes, "edges": edges, "params": params}