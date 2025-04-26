import logging
from typing import Dict, List, Any
from .eval_utils import raw_output_eval, extract_code, load_structure

def evaluate_text_to_nonrenderable(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluate tasks with text input and non-renderable output.
    For these tasks, we validate the output structure and check specified keys.
    
    Args:
        items: List of tasks to evaluate
        
    Returns:
        Evaluated tasks with scores
    """
    logging.info(f"Evaluating {len(items)} text→non-renderable tasks")
    
    for item in items:
        # First apply raw output evaluation
        raw_output_eval(item)
        
        # Set VQA score to None (non-renderable)
        item["VQA_score"] = None
        
        # Extract and parse the output
        generation = item.get("generation", "")
        output_code = extract_code(generation)
        
        # Determine output type from task_id if available
        output_type = ""
        task_id = item.get("task_id", "")
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
            output_type = type_mapping.get(type_code, "")
        
        # Try to load the structure
        structure, confidence = load_structure(output_code, output_type)
        
        # Store structure info for debugging
        item["structure_type"] = type(structure).__name__
        item["structure_confidence"] = confidence
        
        # Verify key validation if structure is a dictionary
        key_validation_score = 0.0
        if isinstance(structure, dict):
            raw_output_metric = item.get("raw_output_metric", [])
            if raw_output_metric:
                # Count matches
                matches = sum(1 for key in raw_output_metric if key in structure)
                key_validation_score = matches / len(raw_output_metric)
        
        item["key_validation_score"] = key_validation_score
        
        # Calculate combined structure validation score
        # 50% from parsing confidence, 50% from key validation
        structure_validation_score = 0.5 * confidence + 0.5 * key_validation_score
        
        # Store as render score since it represents the structural quality
        item["render_score"] = structure_validation_score
    
    return items 