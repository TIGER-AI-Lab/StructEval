import fire
import os
from inference import run_inference
from render import process_json_file
import json
import asyncio

class StructEvalCLI:
    
    def __init__(self):
        pass
        
    
    def inference(
        self,
        llm_model_name: str,
        llm_engine: str,
        input_path: str,
        output_path: str,
        **kwargs #temperatures, top_k, decoding parameters
    ):

        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        queries = [
            f"{item['query']}\n\nIMPORTANT: Only output the executable code. You must not include any other things, such as explanations, comments, or markdown (```, **, #), or any formatting hints etc. You must start the code with <code> and end the code with </code> tags" 
            for item in data
        ]   
            
        task_ids = [item["task_id"] for item in data] 

        useVisualRendering = [item["useVisualRendering"] for item in data] 

        generations = run_inference(llm_model_name, llm_engine, queries)

        output_data = [{"task_id": tid, "useVisualRendering": render, "query": q, "generation": gen} for tid, render, q, gen in zip(task_ids, useVisualRendering, queries, generations)]

        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(output_data, out_file, indent=2)

    
    def evaluate(
        self,
        vlm_model_name: str,
        input_path: str,
        img_output_path: str,
        **kwargs
    ):
        print(f"Evaluating model with vlm_model_name: {vlm_model_name}")
        print(f"Additional arguments: {kwargs}")

        #need rendering?
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        #render/compiler and take screenshots
        asyncio.run(process_json_file(input_path, img_output_path))

        #pass VQA into VLMs 
        
        
        
def main():
    fire.Fire(StructEvalCLI)

if __name__ == "__main__":
    main()