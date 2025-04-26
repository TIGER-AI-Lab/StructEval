import json
import logging
import re
from typing import Dict, List, Any, Union, Optional

# Import specialized evaluation modules
from .eval_text_renderable import evaluate_text_to_renderable
from .eval_text_nonrenderable import evaluate_text_to_nonrenderable
from .eval_nontext_renderable import evaluate_nontext_to_renderable
from .eval_nontext_nonrenderable import evaluate_nontext_to_nonrenderable
from .eval_utils import is_text_input, extract_code, load_structure

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def evaluate_dataset(
    data: List[Dict[str, Any]], 
    images: Dict[str, str],
    vlm_model_name: Optional[str] = None,
    vlm_engine: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Main function to evaluate all items in the dataset based on their input/output types.
    
    Args:
        data: List of task items to evaluate
        images: Dictionary mapping task_id to image paths
        vlm_model_name: Name of the VLM model to use (for renderable outputs)
        vlm_engine: Engine to use for VLM evaluation
        
    Returns:
        List of evaluated task items with scores
    """
    logging.info(f"Starting evaluation of {len(data)} tasks")
    
    # Categorize tasks by input/output types
    text_to_renderable = []
    text_to_nonrenderable = []
    nontext_to_renderable = []
    nontext_to_nonrenderable = []
    
    for item in data:
        is_renderable = item.get("useVisualRendering", False)
        has_text_input = is_text_input(item)
        
        if is_renderable and has_text_input:
            text_to_renderable.append(item)
        elif is_renderable and not has_text_input:
            nontext_to_renderable.append(item)
        elif not is_renderable and has_text_input:
            text_to_nonrenderable.append(item)
        else:
            nontext_to_nonrenderable.append(item)
    
    logging.info(f"Tasks categorized: {len(text_to_renderable)} text→renderable, "
                f"{len(text_to_nonrenderable)} text→non-renderable, "
                f"{len(nontext_to_renderable)} non-text→renderable, "
                f"{len(nontext_to_nonrenderable)} non-text→non-renderable")
    
    # Evaluate each category
    results = []
    
    # Case 1: Text input → Renderable output
    if text_to_renderable:
        results.extend(evaluate_text_to_renderable(text_to_renderable, images, vlm_model_name, vlm_engine))
    
    # Case 2: Text input → Non-renderable output
    if text_to_nonrenderable:
        results.extend(evaluate_text_to_nonrenderable(text_to_nonrenderable))
    
    # Case 3: Non-text input → Renderable output
    if nontext_to_renderable:
        results.extend(evaluate_nontext_to_renderable(nontext_to_renderable, images, vlm_model_name, vlm_engine))
    
    # Case 4: Non-text input → Non-renderable output
    if nontext_to_nonrenderable:
        results.extend(evaluate_nontext_to_nonrenderable(nontext_to_nonrenderable))
    
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
    is_renderable = item.get("useVisualRendering", False)
    has_text_input = is_text_input(item)
    
    render_score = item.get("render_score", 0)
    raw_output_score = item.get("raw_output_score", 0)
    vqa_score = item.get("VQA_score", 0) if item.get("VQA_score") is not None else 0
    structure_score = item.get("structure_score", 0)
    
    if is_renderable:
        # Cases 1 & 3: Input text/non-text, Output renderable
        # 40% render + 20% raw output + 40% VQA
        final_score = (0.4 * render_score) + (0.2 * raw_output_score) + (0.4 * vqa_score)
    else:
        if has_text_input:
            # Case 2: Input text, Output non-renderable
            # 40% render + 60% raw output
            final_score = (0.4 * render_score) + (0.6 * raw_output_score)
        else:
            # Case 4: Input non-text, Output non-renderable
            # 40% render + 20% raw output + 40% structure comparison
            final_score = (0.4 * render_score) + (0.2 * raw_output_score) + (0.4 * structure_score)
    
    item["final_eval_score"] = round(final_score, 2)

if __name__ == "__main__":
    # For testing
    import sys
    import os
    
    if len(sys.argv) != 3:
        print("Usage: python main.py <input_json_file> <output_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Get images from rendered_images directory if it exists
    images = {}
    img_dir = os.path.join(os.path.dirname(input_file), "rendered_images")
    if os.path.exists(img_dir):
        for item in data:
            task_id = item.get("task_id")
            img_path = os.path.join(img_dir, f"{task_id}.png")
            if os.path.exists(img_path):
                images[task_id] = img_path
    
    # Run evaluation
    results = evaluate_dataset(data, images)
    
    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"Evaluation completed. Results saved to {output_file}") 