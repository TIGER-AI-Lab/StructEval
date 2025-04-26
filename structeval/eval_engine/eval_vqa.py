import os
import logging
from typing import Dict, List, Any
from PIL import Image
import torch
import sys

# Make sure llm_engines is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def vqa_eval(
    model_name: str,
    vlm_engine: str,
    data: List[Dict[str, Any]],
    images: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Visual Question Answering evaluation for renderable outputs.
    
    Args:
        model_name: Name of the VLM model
        vlm_engine: Engine for VLM evaluation
        data: List of tasks to evaluate
        images: Dictionary mapping task_id to image paths
        
    Returns:
        List of evaluated tasks with VQA scores
    """
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
    
    # Set up model-specific configuration
    additional_args = ["--chat-template=llama_3_vision"]
    additional_args.extend(["--limit-mm-per-prompt", "image=2", "--max-model-len", "4096"])
    
    try:
        llm.load_model(
            model_name=model_name,
            engine=vlm_engine,
            use_cache=False,
            additional_args=additional_args
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
    
    for item in data:
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
        
        # Run VQA evaluation
        evaluations = []
        for vqa in item.get("VQAmetric", []):
            question = vqa["question"]
            answer = vqa["answer"]
            
            # Prepare message with image
            messages_with_image = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Determine whether the provided image satisfies the given answer to the question. 
                                        Your task is to verify if the visual content of the image aligns with the expected answer. 
                                        Respond strictly with either 'True' or 'False' ONLY.

                                        Question: {question}
                                        Expected Answer: {answer}

                                        Respond with either 'True' or 'False' ONLY
                                        
                                        If you cannot see the image, respond with 'NONE' """
                        },
                        {
                            "type": "image",
                            "image": image
                        }
                    ]
                }
            ]
            
            try:
                response = llm.call_model(model_name, 
                                         messages_with_image, 
                                         temperature=0.0, 
                                         max_tokens=None)
                evaluations.append(response)
            except Exception as e:
                logging.error(f"VQA evaluation failed for {task_id}: {e}")
                evaluations.append("ERROR")

        # Normalize and filter valid responses
        valid_responses = [resp.strip().lower() for resp in evaluations if resp.strip().lower() in ["true", "false"]]

        # Calculate VQA score
        item["VQA_score"] = valid_responses.count("true") / len(valid_responses) if valid_responses else 0.0
        item["VQAeval"] = evaluations
        output_data.append(item)
    
    logging.info(f"VQA evaluation completed for {len(output_data)} tasks")
    return output_data 