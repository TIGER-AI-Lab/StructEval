import re
import json
import yaml
import csv
import io
import logging
from typing import Dict, List, Any, Union, Optional, Tuple

def is_text_input(item: Dict[str, Any]) -> bool:
    """
    Determine if the input is text-based or structured data.
    
    Args:
        item: Task item to check
        
    Returns:
        True if input is text, False if structured
    """
    query = item.get("query", "")
    # Simple heuristic: if the query contains code tags, it's likely not plain text
    return "<code>" not in query

def extract_code(text: str) -> str:
    """
    Extract code between <code> tags.
    
    Args:
        text: Text possibly containing code tags
        
    Returns:
        Extracted code or original text if no tags found
    """
    match = re.search(r"<code>(.*?)</code>", text, re.DOTALL)
    return match.group(1) if match else text

def load_structure(
    code: str, 
    output_type: str = ""
) -> Tuple[Any, float]:
    """
    Try to load and parse text into an appropriate data structure.
    
    Args:
        code: Text to parse
        output_type: Hint about the expected type (json, yaml, csv, etc.)
        
    Returns:
        Tuple of (parsed_data, confidence_score)
        - parsed_data is the parsed structure or None if parsing failed
        - confidence_score is a float between 0 and 1 indicating parsing success
    """
    # Normalize output type
    output_type = output_type.lower()
    
    # Try JSON format first (most common)
    try:
        result = json.loads(code)
        if isinstance(result, (dict, list)) and result:
            return result, 1.0  # Full confidence for valid, non-empty JSON
        else:
            return result, 0.5  # Lower confidence for valid but empty JSON
    except json.JSONDecodeError:
        pass
    
    # Try YAML format
    try:
        result = yaml.safe_load(code)
        if isinstance(result, (dict, list)) and result:
            return result, 0.9  # High confidence for YAML
        elif result is not None:
            return result, 0.5  # Lower confidence for simple YAML
        else:
            return None, 0.0
    except (yaml.YAMLError, AttributeError):
        pass
    
    # Try CSV format
    if output_type in ["csv", ""]:
        try:
            rows = list(csv.reader(io.StringIO(code.strip())))
            if rows and len(rows) >= 2:
                if all(len(row) > 1 for row in rows):
                    return rows, 0.9  # High confidence for multi-row multi-column CSV
                else:
                    return rows, 0.7  # Lower confidence for single-column CSV
            elif rows:
                return rows, 0.5  # Even lower for single row
        except:
            pass
    
    # Try INI/Config format
    if output_type in ["ini", "conf", "config", ""]:
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read_string(code)
            result = {s: dict(config.items(s)) for s in config.sections()}
            if result:
                return result, 0.9  # High confidence
            else:
                return {}, 0.3  # Lower confidence for empty config
        except:
            pass
    
    # Try XML format
    if output_type in ["xml", ""]:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(code)
            result = {root.tag: xml_to_dict(root)}
            return result, 0.9  # High confidence for valid XML
        except:
            pass
    
    # Try TOML format
    if output_type in ["toml", ""]:
        try:
            import toml
            result = toml.loads(code)
            return result, 0.9  # High confidence for valid TOML
        except:
            pass
    
    # For text formats that are key-value based (.env, properties)
    if output_type in ["env", "properties", ""]:
        lines = [line.strip() for line in code.split('\n') 
                if line.strip() and not line.strip().startswith('#')]
        result = {}
        
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip()
        
        if result:
            return result, 0.8  # Good confidence if we found key-value pairs
        
    # If we've reached here, we couldn't parse it as a known structure
    # Return the original text with low confidence
    return code.strip(), 0.1

def xml_to_dict(element):
    """Convert XML element to dictionary for easier comparison"""
    result = {}
    
    # Add attributes
    if element.attrib:
        result["@attributes"] = dict(element.attrib)
    
    # Add children
    for child in element:
        child_dict = xml_to_dict(child)
        
        # Handle multiple children with same tag
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_dict)
        else:
            result[child.tag] = child_dict
    
    # Add text content if no children and has text
    if not result and element.text and element.text.strip():
        return element.text.strip()
    
    return result

def calculate_structure_similarity(struct1, struct2):
    """
    Calculate structural similarity between two structures.
    Returns a score between 0 and 1 based on structural similarity.
    
    Args:
        struct1: First structure (dict, list, etc.)
        struct2: Second structure to compare
        
    Returns:
        Similarity score between 0 and 1
    """
    if type(struct1) != type(struct2):
        return 0.0
    
    if isinstance(struct1, dict):
        # For dictionaries, compare keys and recursively compare values
        keys1 = set(struct1.keys())
        keys2 = set(struct2.keys())
        
        if not keys1 and not keys2:
            return 1.0
            
        # Proportion of matching keys
        key_match_ratio = len(keys1.intersection(keys2)) / max(len(keys1), len(keys2))
        
        # Compare common keys' values
        common_keys = keys1.intersection(keys2)
        if not common_keys:
            return key_match_ratio * 0.5  # Only partial credit for key matching
        
        # Average similarity of values for common keys
        value_similarities = [
            calculate_structure_similarity(struct1[k], struct2[k])
            for k in common_keys
        ]
        value_similarity = sum(value_similarities) / len(value_similarities)
        
        # Combine key and value similarities
        return 0.5 * key_match_ratio + 0.5 * value_similarity
        
    elif isinstance(struct1, list):
        # For lists, compare lengths and elements
        if not struct1 and not struct2:
            return 1.0
            
        # Length comparison
        len_ratio = min(len(struct1), len(struct2)) / max(len(struct1), len(struct2))
        
        # Compare elements (up to the shorter list's length)
        min_len = min(len(struct1), len(struct2))
        if min_len == 0:
            return len_ratio * 0.5
        
        # Compare elements at same positions (simplified)
        element_similarities = [
            calculate_structure_similarity(struct1[i], struct2[i])
            for i in range(min_len)
        ]
        element_similarity = sum(element_similarities) / min_len
        
        # Combine length and element similarities
        return 0.5 * len_ratio + 0.5 * element_similarity
        
    else:
        # For primitive types, direct comparison
        return 1.0 if struct1 == struct2 else 0.0

def raw_output_eval(item: Dict[str, Any]) -> float:
    """
    Evaluate using raw output metric (keyword matching).
    
    Args:
        item: Task item to evaluate
        
    Returns:
        Score between 0 and 1
    """
    generation = item.get("generation", "").lower()
    raw_output_metric = item.get("raw_output_metric", [])
    
    if not raw_output_metric:
        return 0.0
    
    matches = 0
    for keyword in raw_output_metric:
        keyword_lower = keyword.lower()
        if keyword_lower in generation:
            matches += 1
    
    # Store evaluation details
    item["raw_output_eval"] = [
        "True" if keyword.lower() in generation else "False"
        for keyword in raw_output_metric
    ]
    
    # Calculate and return score
    score = matches / len(raw_output_metric) if raw_output_metric else 0.0
    item["raw_output_score"] = score
    return score

def make_json_serializable(obj):
    """
    Convert objects to JSON serializable types.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON serializable version of the object
    """
    if isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj) 