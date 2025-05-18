import json
import logging
import re
from typing import Dict, List, Any, Union, Optional

# Import specialized evaluation modules
from .eval_renderable import evaluate_renderable
from .eval_nonrenderable import evaluate_nonrenderable

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def evaluate_dataset(
    data: List[Dict[str, Any]], 
    images: Dict[str, str],
    vlm_model_name: Optional[str] = None,
    vlm_engine: Optional[str] = None,
    output_dir: str = "output_files",
    non_renderable_dir: str = "non_renderable_format_files",
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Main function to evaluate all items in the dataset based on their input/output types.
    
    Args:
        data: List of task items to evaluate
        images: Dictionary mapping task_id to image paths
        vlm_model_name: Name of the VLM model to use (for renderable outputs)
        vlm_engine: Engine to use for VLM evaluation
        output_dir: Directory for output files
        non_renderable_dir: Directory where non-renderable files are saved by render_engine
        additional_args: Additional arguments to pass to the VLM
        
    Returns:
        List of evaluated task items with scores
    """
    
    logging.info(f"Starting evaluation of {len(data)} tasks")
    
    # Categorize tasks by output type (renderable vs non-renderable)
    renderable_items = []
    nonrenderable_items = []
    
    for item in data:
        is_renderable = item.get("rendering", False)
        
        if is_renderable:
            renderable_items.append(item)
        else:
            nonrenderable_items.append(item)
    
    logging.info(f"Tasks categorized: {len(renderable_items)} renderable items, "
                f"{len(nonrenderable_items)} non-renderable items")
    
    # Evaluate each category
    results = []
    
    # Case 1: Renderable output (both text and non-text input)
    if renderable_items:
        results.extend(evaluate_renderable(renderable_items, images, vlm_model_name, vlm_engine, **kwargs))
    
    # Case 2: Non-renderable output (both text and non-text input)
    if nonrenderable_items:
        results.extend(evaluate_nonrenderable(nonrenderable_items, non_renderable_dir))
    
    # Calculate final scores for all items
    for item in results:
        calculate_final_score(item)
    
    logging.info(f"Evaluation completed for {len(results)} tasks")
    return results

def calculate_final_score(item: Dict[str, Any]) -> None:
    """
    Calculate the final evaluation score based on item type.
    
    Args:
        item: The task item to calculate score for
    """
    is_renderable = item.get("rendering", False)
    
    render_score = item.get("render_score", 0)
    raw_output_score = item.get("raw_output_score", 0)
    vqa_score = item.get("VQA_score", 0) if item.get("VQA_score") is not None else 0
    
    if is_renderable:
        # Renderable output
        # 40% render + 20% raw output + 40% VQA
        final_score = (0.2 * render_score) + (0.1 * raw_output_score) + (0.7 * vqa_score)
    else:
        # Non-renderable output
        # 40% render (syntax validity) + 60% path validation
        key_validation_score = item.get("key_validation_score", 0)
        if (render_score == 0):
            print("zero render score")
            print(key_validation_score)
        final_score = (0.2 * render_score) + (0.8 * key_validation_score)
    
    item["final_eval_score"] = round(final_score, 2)
