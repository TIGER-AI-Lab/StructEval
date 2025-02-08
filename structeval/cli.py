import fire
import os
from inference import run_inference
import json

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
            f"{item['query']}\n\nIMPORTANT: Only output the executable code. Do NOT include any other things, such as explanations, comments, or markdown (```, **, #), or any formatting hints etc." 
            for item in data
        ]   

        #define tags to represent output components : <code> </code>
            
        task_ids = [item["task_id"] for item in data] 

        generations = run_inference(llm_model_name, llm_engine, queries)

        
        output_data = [{"task_id": tid, "query": q, "generation": gen} for tid, q, gen in zip(task_ids, queries, generations)]

       
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(output_data, out_file, indent=2)

    
    def eval(
        self,
        vlm_model_name: str,
        **kwargs
    ):
        print(f"Evaluating model with vlm_model_name: {vlm_model_name}")
        print(f"Additional arguments: {kwargs}")
        
        
        
def main():
    fire.Fire(StructEvalCLI)

if __name__ == "__main__":
    main()