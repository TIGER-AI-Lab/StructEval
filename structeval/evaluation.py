from dotenv import load_dotenv
import os
from llm_engines import LLMEngine
import torch
from PIL import Image

#openai, claude, gemini, open source model using vllm in llm_engine

#use batch inference

def vqa_eval(
        model_name: str,
        vlm_engine: str,
        data: list[dict],
        images: dict[str, str]
    ):
    
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
            continue
            
        debug_image_path = f"debug_images/{task_id}.png"
        os.makedirs("debug_images", exist_ok=True)
        image.save(debug_image_path)

        print(f"Saved debug image for task_id {task_id} at {debug_image_path}")
        
        evaluations = []
        
        for vqa in item.get("VQAmetric", []):
            question = vqa["question"]
            answer = vqa["answer"]
            
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
