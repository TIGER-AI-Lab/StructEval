import re
import json
import yaml
import csv
import io
import logging
import os
import xmltodict
import toml
from typing import Dict, List, Any, Union, Optional, Tuple


def determine_output_type(task_id: str) -> str:
    """
    Determine output type from task_id.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Output format type (json, yaml, csv, toml, xml)
    """
    if len(task_id) >= 4:
        type_code = task_id[2:4]
        # Map type code to output type
        type_mapping = {
            "05": "json",
            "18": "yaml",
            "02": "csv",
            "10": "toml",
            "17": "xml"
        }
        return type_mapping.get(type_code, "")
    return ""

def load_file_structure(file_path: str, format_type: str) -> Tuple[Any, int]:
    """
    Load and parse structure directly from a file.
    
    Args:
        file_path: Path to the file to load
        format_type: Format type to use (json, yaml, csv, toml, xml)
        
    Returns:
        (parsed_obj, success)
    """
    if not os.path.exists(file_path):
        return None, 0
    
    try:
        if format_type == "json":
            with open(file_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return result, 1
        elif format_type == "yaml":
            with open(file_path, 'r', encoding='utf-8') as f:
                result = yaml.safe_load(f)
            return result, 1
        elif format_type == "toml":
            with open(file_path, 'r', encoding='utf-8') as f:
                result = toml.load(f)
            return result, 1
        elif format_type == "xml":
            with open(file_path, 'r', encoding='utf-8') as f:
                result = xmltodict.parse(f.read())
            return result, 1
        elif format_type == "csv":
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return {"csv_headers": reader.fieldnames, "csv_rows": list(reader)}, 1
        else:
            raise ValueError("Unsupported file format.")
        
    except Exception as e:
        logging.error(f"Error loading file {file_path}: {str(e)}")
        return None, 0

# Path checking functions from check_paths.py
def tokenize_path(path: str) -> List[str]:
    """
    Tokenize a dot-notation path, handling back-ticks and array indices.
    
    Args:
        path: The path string (e.g. "users.0.name" or "users[0].name")
        
    Returns:
        List of path tokens
    """
    # Special‑case: treat CSV header paths as a single token
    if path.startswith("csv::"):
        return [path]
        
    tokens, buf, in_bt = [], "", False
    i, n = 0, len(path)

    while i < n:
        ch = path[i]

        # Toggle back-tick state
        if ch == "`":
            in_bt = not in_bt
            i += 1
            continue

        # Dot delimiter (when not inside back-ticks)
        if ch == "." and not in_bt:
            if buf:
                tokens.append(buf)
                buf = ""
            i += 1
            continue

        # Bracket "[index]" treated as separate token
        if ch == "[" and not in_bt:
            if buf:
                tokens.append(buf)
                buf = ""
            j = path.find("]", i)
            if j == -1:
                raise ValueError(f"Unclosed '[' in path: {path}")
            tokens.append(path[i : j + 1])  # e.g. "[0]"
            i = j + 1
            continue

        # Regular character
        buf += ch
        i += 1

    if buf:
        tokens.append(buf)
    return tokens

def path_exists(data: Any, path: str) -> bool:
    """
    Check if a path exists in a structured data object.
    
    Args:
        data: The structured data to check
        path: The path to check (dot notation)
        
    Returns:
        True if path exists, False otherwise
    """
    tokens = tokenize_path(path)

    def walk(node: Any, toks: List[str]) -> bool:
        if not toks:
            return True
        tok, *rest = toks

        # CSV header rule (root level only)
        if isinstance(node, dict) and "csv_headers" in node and tok.startswith("csv::"):
            header = tok[5:]
            return header in node["csv_headers"] and not rest  # must be terminal

        # Wildcard
        if tok == "*":
            if isinstance(node, list):
                return any(walk(item, rest) for item in node)
            return False

        # Fixed index [n]
        if tok.startswith("[") and tok.endswith("]"):
            try:
                idx = int(tok[1:-1])
            except ValueError:
                return False
            return (
                isinstance(node, list)
                and 0 <= idx < len(node)
                and walk(node[idx], rest)
            )

        # Dict key handling (JSON/YAML/TOML/XML)
        if isinstance(node, dict):
            # 1️⃣ Literal key match (works for "@id" too)
            if tok in node:
                return walk(node[tok], rest)

            # 2️⃣ XML attribute fallback: "@id" → "id"
            if tok.startswith("@"):
                attr = tok[1:]
                if attr in node:
                    return walk(node[attr], rest)

        return False

    return walk(data, tokens)

def raw_output_eval(item: Dict[str, Any]) -> float:
    """
    Evaluate using raw output metric (keyword matching).
    
    Args:
        item: Task item to evaluate
        
    Returns:
        Score between, 0 and 1
    """
    generation = item.get("generation", "").lower()
    raw_output_metric = item.get("raw_output_metric", [])
    
    if not raw_output_metric:
        return 0.0
    
    matches = 0
    results = []
    
    
    for keyword in raw_output_metric:
        keyword_lower = keyword.lower()
        
        # Standard keyword matching against extracted code
        if keyword_lower in generation:
            matches += 1
            results.append("True")
        else:
            results.append("False")
    
    # Store evaluation details
    item["raw_output_eval"] = results
    
    # Calculate and return score
    score = matches / len(raw_output_metric) if raw_output_metric else 0.0
    item["raw_output_score"] = score
    return score 