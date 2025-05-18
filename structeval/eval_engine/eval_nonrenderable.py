import logging
import os
import json
from typing import Dict, List, Any
from .eval_utils import load_file_structure, determine_output_type, path_exists

def evaluate_nonrenderable(items: List[Dict[str, Any]], saved_files_dir: str) -> List[Dict[str, Any]]:
    """
    Evaluate tasks with non-renderable output, regardless of input type.
    This function saves the extracted code to files and then uses path validation
    to check if the paths in raw_output_metric exist in the output structure.
    
    Args:
        items: List of tasks to evaluate
        output_dir: Directory to save extracted files
        
    Returns:
        Evaluated tasks with scores
    """
    logging.info(f"Evaluating {len(items)} non-renderable tasks")
    
    # Create output directory if it doesn't exist
    #os.makedirs(saved_files_dir, exist_ok=True)
    counter = 0
    for item in items:
        counter += 1
        print(f"Evaluating non-renderable task {counter} of {len(items)}")

        # Set VQA score to None (non-renderable)
        item["VQA_score"] = None
        item["key_validation_score"] = 0

        if item.get("render_score") == 0:
            item["key_validation_score"] = 0
            continue
        
        # Get task ID and determine output type
        task_id = item.get("task_id", "unknown")
        output_type = determine_output_type(task_id)
        
        file_path = item.get("output_file", None)
        if file_path is None:
            item["key_validation_score"] = 0
            break

        structure, parsed_success = load_file_structure(file_path, output_type.lower())

        if parsed_success == 0:
            item["key_validation_score"] = 0
            continue

        raw_output_metric = item.get("raw_output_metric", [])

        if len(raw_output_metric) > 0:
            for path in raw_output_metric:
                if path_exists(structure, path):
                    item["key_validation_score"] += 1
        
        # Aggregate key validation score
        item["key_validation_score"] = item["key_validation_score"] / len(raw_output_metric)

    return items 