import os
import logging
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
import json
import sys

# Make sure llm_engines is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def vqa_eval(
    model_name: str,
    vlm_engine: str,
    data: List[Dict[str, Any]] = None,
    images: Dict[str, str] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Visual Question Answering evaluation for renderable outputs.
    
    Args:
        model_name: Name of the VLM model
        vlm_engine: Engine for VLM evaluation
        additional_args: Additional arguments to pass to the VLM
        data: List of tasks to evaluate
        images: Dictionary mapping task_id to image paths
        
    Returns:
        List of evaluated tasks with VQA scores
    """
    # Handle default parameters
    if data is None:
        data = []
    if images is None:
        images = {}
        
    try:
        from llm_engines import LLMEngine
    except ImportError:
        logging.error("LLMEngine not found. VQA evaluation not available.")
        for item in data:
            item["VQA_score"] = 0.0
            item["VQAeval"] = ["NONE"]
        return data
    
    logging.info(f"Running VQA evaluation with model {model_name} on {len(data)} tasks")
    
    llm = LLMEngine()
    
    try:
        llm.load_model(
            model_name=model_name,
            engine=vlm_engine,
            use_cache=False,
            **kwargs
        )
    except Exception as e:
        logging.error(f"Failed to load VLM model: {e}")
        for item in data:
            item["VQA_score"] = 0.0
            item["VQAeval"] = ["FAILURE: Model loading error"]
        return data
    
    # Ensure debug images directory exists
    os.makedirs("debug_images", exist_ok=True)
    
    output_data = []
    counter = 0
    for item in data:
        counter += 1
        print(f"Evaluating VQA task {counter} of {len(data)}")
        
        task_id = item.get("task_id")
        img_file = images.get(task_id)

        # Load image if available
        if img_file and os.path.exists(img_file):
            try:
                with Image.open(img_file) as img:
                    image = img.convert("RGB")
                
                # Save a copy for debugging
                debug_image_path = f"debug_images/{task_id}.png"
                image.save(debug_image_path)
                logging.info(f"Saved debug image for task_id {task_id}")
            except Exception as e:
                logging.error(f"Failed to load image for {task_id}: {e}")
                image = None
        else:
            image = None 
            
        # If image is not available, skip VQA
        if image is None:
            item["VQA_score"] = 0.0
            item["render_score"] = item.get("render_score", 0.0)
            item["VQAeval"] = []
            output_data.append(item)
            continue
        
        # Run VQA evaluation in a single call with JSON output
        vqa_questions = item.get("VQA", [])
        total_questions = len(vqa_questions)
        if total_questions == 0:
            item["VQA_score"] = 0.0
            item["VQAeval"] = []
            output_data.append(item)
            continue

        # Build the question-answer list for the prompt
        qa_list = ""
        for idx, vqa in enumerate(vqa_questions, 1):
            qa_list += f"{idx}. Question: {vqa['question']} Expected Answer: {vqa['answer']}\n"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are given an image and a list of question-answer pairs. "
                            "For each pair, verify if the image content supports the expected answer based on the corresponding question. "
                            "If the image is fully white, then you should always output false"
                            "Base your judgment solely on the visual content of the provided image, and the question. Do not imagine anything. "
                            "Do not use any external information or common-sense reasoning beyond what is visible. "
                            "Respond with a JSON object mapping each question number to true or false (e.g., {\"1\": true, \"2\": false}). "
                            "If the image is unclear or does not contain enough information to answer, use null for that question. "
                            "Here are the question-answer pairs:\n"
                            f"{qa_list}"
                        )
                    },
                    {
                        "type": "image",
                        "image": image
                    }
                ]
            }
        ]

        try:
            response = llm.call_model(model_name, messages, temperature=0.0, max_tokens=None)
            parsed = json.loads(response)
            evaluations = [parsed.get(str(idx)) for idx in range(1, total_questions + 1)]
            true_count = sum(1 for ans in evaluations if ans is True)
        except Exception as e:
            logging.error(f"VQA evaluation failed for {task_id}: {e}")
            evaluations = [None] * total_questions
            true_count = 0

        item["VQA_score"] = true_count / total_questions
        item["VQAeval"] = evaluations
        output_data.append(item)
    
    logging.info(f"VQA evaluation completed for {len(output_data)} tasks")
    return output_data