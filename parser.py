from typing import List, Dict, Any

def parse_c_code(code: str) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in code.split('\n') if line.strip() and not line.strip().startswith('//') and line.strip() not in ['{', '}']]
    blocks = []
    current_block = {"type": "statement", "lines": []}

    for line in lines:
        if line.startswith('if'):
            if current_block["lines"]:
                blocks.append(current_block)
            condition = line[line.find('(')+1:line.find(')')]
            blocks.append({"type": "decision", "condition": condition})
            current_block = {"type": "statement", "lines": []}
        elif line.startswith('} else if'):
            if current_block["lines"]:
                blocks.append(current_block)
            condition = line[line.find('(')+1:line.find(')')]
            blocks.append({"type": "decision", "condition": condition})
            current_block = {"type": "statement", "lines": []}
        elif line.startswith('} else'):
            if current_block["lines"]:
                blocks.append(current_block)
            blocks.append({"type": "statement", "lines": ["else"]})
            current_block = {"type": "statement", "lines": []}
        else:
            current_block["lines"].append(line)

    if current_block["lines"]:
        blocks.append(current_block)

    return blocks
