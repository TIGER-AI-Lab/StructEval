import logging
from typing import Dict, List, Any, Optional
from .eval_utils import raw_output_eval

def evaluate_nontext_to_renderable(
    items: List[Dict[str, Any]],
    images: Dict[str, str],
    vlm_model_name: Optional[str] = None,
    vlm_engine: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate tasks with non-text input and renderable output.
    This is similar to text→renderable, but may involve different VQA criteria.
    
    Args:
        items: List of tasks to evaluate
        images: Dictionary of task_id to image paths
        vlm_model_name: Name of VLM to use for visual evaluation
        vlm_engine: Engine for VLM evaluation
    
    Returns:
        Evaluated tasks with scores
    """
    logging.info(f"Evaluating {len(items)} non-text→renderable tasks")
    
    # Apply raw output evaluation
    for item in items:
        raw_output_eval(item)
    
    # If VLM is provided, run VQA evaluation on images
    if vlm_model_name and vlm_engine:
        from eval_vqa import vqa_eval
        items = vqa_eval(vlm_model_name, vlm_engine, items, images)
    else:
        # If no VLM, set VQA score to None
        for item in items:
            item["VQA_score"] = None
            item["VQAeval"] = []
    
    return items 