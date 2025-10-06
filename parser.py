from typing import List, Dict, Any
import re

def parse_c_code(code: str) -> List[Dict[str, Any]]:
    # Preprocess code: remove comments and excessive whitespace
    code = re.sub(r'//.*', '', code)   # Remove single line comments
    code = re.sub(r'\s+', ' ', code)   # Normalize whitespace

    blocks = []
    current_block = {"type": "statement", "lines": []}

    # Tokenize code by splitting on ';' and braces to separate statements and blocks
    # This tokenizer is simplistic — a full parser is more complex
    tokens = re.split(r'([{};])', code)

    buffer = ''
    i = 0
    while i < len(tokens):
        token = tokens[i].strip()
        if token == '':
            i += 1
            continue
        if token == '{' or token == '}':
            # flush buffer as statement block if nonempty
            if buffer.strip():
                blocks.extend(process_code_fragment(buffer.strip()))
                buffer = ''
            i += 1
            continue
        elif token == ';':
            buffer += ';'
            blocks.extend(process_code_fragment(buffer.strip()))
            buffer = ''
            i += 1
            continue
        else:
            buffer += token + ' '
            i += 1

    # flush trailing buffer
    if buffer.strip():
        blocks.extend(process_code_fragment(buffer.strip()))

    return blocks

def process_code_fragment(fragment: str) -> List[Dict[str, Any]]:
    """
    Recursive processing to split fragment into statement and decision blocks,
    detecting if-else constructs inline.
    """
    blocks = []

    fragment = fragment.strip()
    # Regex to detect if statement and condition
    if_match = re.match(r'if\s*\((.*?)\)\s*(.*)', fragment, re.DOTALL)
    if if_match:
        condition = if_match.group(1).strip()
        rest = if_match.group(2).strip()

        blocks.append({"type": "decision", "condition": condition})

        # Process true branch (rest of statement/block after if condition)
        if rest.startswith('{'):
            # find matching '}'
            end_idx = find_matching_brace(rest)
            true_branch = rest[1:end_idx].strip()
            blocks.extend(parse_c_code(true_branch))
            rest = rest[end_idx+1:].strip()
        else:
            # true branch up to else or end
            # split by else if or else if present
            else_match = re.search(r'(else if|else)', rest)
            if else_match:
                true_branch = rest[:else_match.start()].strip()
                blocks.extend(parse_c_code(true_branch))
                rest = rest[else_match.start():].strip()
            else:
                blocks.extend(parse_c_code(rest))
                rest = ''

        # Process else if / else branches if present
        while rest:
            if rest.startswith('else if'):
                # Extract condition
                m = re.match(r'else if\s*\((.*?)\)\s*(.*)', rest, re.DOTALL)
                if not m:
                    break
                cond = m.group(1).strip()
                blocks.append({"type": "decision", "condition": cond})
                else_rest = m.group(2).strip()
                if else_rest.startswith('{'):
                    end_idx = find_matching_brace(else_rest)
                    else_true = else_rest[1:end_idx].strip()
                    blocks.extend(parse_c_code(else_true))
                    rest = else_rest[end_idx+1:].strip()
                else:
                    else_else_match = re.search(r'(else if|else)', else_rest)
                    if else_else_match:
                        else_true = else_rest[:else_else_match.start()].strip()
                        blocks.extend(parse_c_code(else_true))
                        rest = else_rest[else_else_match.start():].strip()
                    else:
                        blocks.extend(parse_c_code(else_rest))
                        rest = ''
            elif rest.startswith('else'):
                # else branch
                m = re.match(r'else\s*(.*)', rest, re.DOTALL)
                else_body = m.group(1).strip() if m else ''
                if else_body.startswith('{'):
                    end_idx = find_matching_brace(else_body)
                    else_code = else_body[1:end_idx].strip()
                    blocks.extend(parse_c_code(else_code))
                    rest = else_body[end_idx+1:].strip()
                else:
                    blocks.extend(parse_c_code(else_body))
                    rest = ''
            else:
                break
        return blocks
    else:
        # No if detected, treat as statement
        return [{"type": "statement", "lines": [fragment]}]

def find_matching_brace(code: str) -> int:
    """
    Finds the index of the matching closing brace } for the first opening { at code[0].
    Returns the index of the } character.
    """
    if not code.startswith('{'):
        raise ValueError("Code does not start with '{'")
    depth = 0
    for i, c in enumerate(code):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("No matching closing brace found")
