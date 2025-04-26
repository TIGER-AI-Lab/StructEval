import logging
from typing import Dict, List, Any
from .eval_utils import raw_output_eval, extract_code, load_structure, calculate_structure_similarity

def evaluate_nontext_to_nonrenderable(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluate tasks with non-text input and non-renderable output.
    This involves comparing input and output structures for similarity.
    
    Args:
        items: List of tasks to evaluate
        
    Returns:
        Evaluated tasks with scores
    """
    logging.info(f"Evaluating {len(items)} non-text→non-renderable tasks")
    
    for item in items:
        # First apply raw output evaluation
        raw_output_eval(item)
        
        # Set VQA score to None (non-renderable)
        item["VQA_score"] = None
        
        # Extract code from input and output
        query = item.get("query", "")
        generation = item.get("generation", "")
        
        input_code = extract_code(query)
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
        
        # Parse input and output structures
        input_struct, input_confidence = load_structure(input_code, output_type)
        output_struct, output_confidence = load_structure(output_code, output_type)
        
        # Store structure info for debugging
        item["input_structure_type"] = type(input_struct).__name__
        item["output_structure_type"] = type(output_struct).__name__
        item["input_confidence"] = input_confidence
        item["output_confidence"] = output_confidence
        
        # Calculate structure similarity if both parsed successfully
        structure_score = 0.0
        if input_confidence >= 0.5 and output_confidence >= 0.5:
            structure_score = calculate_structure_similarity(input_struct, output_struct)
        
        # Store scores
        item["structure_score"] = structure_score
        
        # Set render score based on output parsing confidence
        item["render_score"] = output_confidence
    
    return items 