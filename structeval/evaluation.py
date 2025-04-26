from dotenv import load_dotenv
import os
from llm_engines import LLMEngine
import torch
from PIL import Image
import re
import json
import yaml
import io
import csv
import logging
import asyncio
from typing import Dict, List, Any, Optional

# Import the evaluation engine
from eval_engine import evaluate_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

#openai, claude, gemini, open source model using vllm in llm_engine

#use batch inference

def vqa_eval(
        model_name: str,
        vlm_engine: str,
        data: list[dict],
        images: dict[str, str]
    ):
    """
    Legacy VQA evaluation function.
    Use comprehensive_eval instead for new code.
    """
    llm = LLMEngine()
    
    additional_args = []
    additional_args=["--chat-template=llama_3_vision"]
    additional_args=["--limit-mm-per-prompt", "image=2", "--max-model-len", "4096"]
    llm.load_model(
        model_name=model_name,
        engine=vlm_engine,
        use_cache=False,
        additional_args=additional_args
    )
    
    output_data = []
    
    for item in data:
        task_id = item.get("task_id")
        img_file = images.get(task_id)

        if img_file and os.path.exists(img_file):
            with Image.open(img_file) as img:
                image = img.convert("RGB")
        else:
            image = None 
            item["VQA_score"] = 0.0
            item["render_score"] = 0.0
            item["VQAeval"] = []
            output_data.append(item)
            continue
            
        debug_image_path = f"debug_images/{task_id}.png"
        os.makedirs("debug_images", exist_ok=True)
        image.save(debug_image_path)

        print(f"Saved debug image for task_id {task_id} at {debug_image_path}")
        
        evaluations = []
        
        for vqa in item.get("VQAmetric", []):
            question = vqa["question"]
            answer = vqa["answer"]
            
            #Use CoT before outputting True or False, step by step
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
            #print(image==None)
            response = llm.call_model(model_name, 
                                      messages_with_image, 
                                      temperature=0.0, 
                                      max_tokens=None)
            evaluations.append(response)

        # Normalize and filter valid responses
        valid_responses = [resp.strip().lower() for resp in evaluations if resp.strip().lower() in ["true", "false"]]

        # Count "true" values and compute the score
        item["VQA_score"] = valid_responses.count("true") / len(valid_responses) if valid_responses else 0.0

        
        item["VQAeval"] = evaluations
        #item["VQA_score"] = evaluations.count("True") / len(evaluations) if evaluations else 0.0
        output_data.append(item)
    
    return output_data


def raw_output_eval(data: list[dict]):
    """
    Legacy raw output evaluation function.
    Use comprehensive_eval instead for new code.
    """
    for item in data:
        generation = item.get("generation", "").lower()
        raw_output_metric = item.get("raw_output_metric", [])
        
        evaluation_results = []
        
        for keyword in raw_output_metric:
            keyword_lower = keyword.lower()
            if keyword_lower in generation:
                evaluation_results.append("True")
            else:
                evaluation_results.append("False")
        
        item["raw_output_eval"] = evaluation_results
        item["raw_output_score"] = evaluation_results.count("True") / len(evaluation_results) if evaluation_results else 0.0
    
    return data

def comprehensive_eval(
    data: List[Dict[str, Any]], 
    images: Dict[str, str],
    vlm_model_name: Optional[str] = None,
    vlm_engine: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Comprehensive evaluation that handles four different scenarios:
    1. Input: text, Output: renderable - Raw output metric + VQA on screenshots
    2. Input: text, Output: non-renderable - Dictionary validation + key checking
    3. Input: non-text, Output: renderable - Same as case 1
    4. Input: non-text, Output: non-renderable - Structure comparison with partial scoring
    
    Args:
        data: List of task items to evaluate
        images: Dictionary mapping task_id to image paths
        vlm_model_name: Optional name of VLM for visual evaluation
        vlm_engine: Optional engine for VLM evaluation
        
    Returns:
        List of evaluated tasks with scores
    """
    logging.info(f"Starting comprehensive evaluation of {len(data)} tasks")
    
    # Delegate to the evaluation engine
    evaluated_data = evaluate_dataset(data, images, vlm_model_name, vlm_engine)
    
    logging.info(f"Evaluation completed for {len(evaluated_data)} tasks")
    return evaluated_data

def _is_text_input(item):
    """Determine if the input is text-based or structured data"""
    query = item.get("query", "")
    # Simple heuristic: if the query contains code tags, it's likely not plain text
    return "<code>" not in query

def _extract_code(text):
    """Extract code between <code> tags"""
    match = re.search(r"<code>(.*?)</code>", text, re.DOTALL)
    return match.group(1) if match else text

def _validate_non_renderable_output(item):
    """Validate non-renderable outputs (JSON, YAML, etc.) by checking keys"""
    generation = item.get("generation", "")
    output_code = _extract_code(generation)
    
    # Try to parse the output into a structure
    output_struct = _parse_to_structure(output_code)
    
    # Check if parsing was successful
    item["validation_success"] = output_struct is not None
    
    # If we have raw_output_metric, check if those keys exist in the structure
    if output_struct and isinstance(output_struct, dict):
        raw_output_metric = item.get("raw_output_metric", [])
        
        key_found_count = 0
        for key in raw_output_metric:
            if key in output_struct:
                key_found_count += 1
        
        # Calculate a score based on found keys
        key_score = key_found_count / len(raw_output_metric) if raw_output_metric else 0
        item["key_validation_score"] = key_score
    else:
        item["key_validation_score"] = 0
    
    return item

def _parse_to_structure(code):
    """
    Try to parse code into a structure (dict, list, etc.)
    Returns the parsed structure or None if parsing fails
    """
    # First try JSON
    try:
        return json.loads(code)
    except:
        pass
    
    # Then try YAML
    try:
        return yaml.safe_load(code)
    except:
        pass
    
    # Try CSV
    try:
        rows = list(csv.reader(io.StringIO(code.strip())))
        if rows and len(rows) >= 2:
            return rows
    except:
        pass
    
    # If all parsing fails, return None
    return None

def _compare_structures(input_code, output_code):
    """
    Compare two code structures and assign partial score
    Returns a score between 0 and 1 based on structural similarity
    """
    # Try to parse both as structured data
    input_struct = _parse_to_structure(input_code)
    output_struct = _parse_to_structure(output_code)
    
    if not input_struct or not output_struct:
        return 0.0
    
    # Calculate similarity score
    return _calculate_structure_similarity(input_struct, output_struct)

def _calculate_structure_similarity(struct1, struct2):
    """
    Calculate structural similarity between two structures
    Returns a score between 0 and 1
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
            _calculate_structure_similarity(struct1[k], struct2[k])
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
            _calculate_structure_similarity(struct1[i], struct2[i])
            for i in range(min_len)
        ]
        element_similarity = sum(element_similarities) / min_len
        
        # Combine length and element similarities
        return 0.5 * len_ratio + 0.5 * element_similarity
        
    else:
        # For primitive types, direct comparison
        return 1.0 if struct1 == struct2 else 0.0
