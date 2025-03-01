import fire
import os
from inference import run_inference
from render import process_json_file
from evaluation import vqa_eval, raw_output_eval
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

        generations = run_inference(llm_model_name, llm_engine, queries)

        output_data = []
        for item, generation in zip(data, generations):
            item["generation"] = generation  
            output_data.append(item)
        
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(output_data, out_file, indent=2)

    
    def evaluate(
        self,
        vlm_model_name: str,
        vlm_engine: str,
        input_path: str,
        output_path: str,
        img_path: str,
        **kwargs
    ):
        print(f"Evaluating model with vlm_model_name: {vlm_model_name}")
        print(f"Additional arguments: {kwargs}")

        #need rendering?
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        #render/compiler and take screenshots
        asyncio.run(process_json_file(input_path, img_path))

        #pass VQA and screenshots to VLMs 
        # prepare image dictionary

        images = {item["task_id"]: f"{img_path}/{item['task_id']}.png" 
          for item in data if os.path.exists(f"{img_path}/{item['task_id']}.png")}
        
        #Run raw output metric evaluation
        raw_output_evaluations = raw_output_eval(data)


        # Pass VQA and screenshots to VLMs
        vqa_evaluations = vqa_eval(vlm_model_name, vlm_engine=vlm_engine, data=raw_output_evaluations, images=images)

        # Compute final scores
        for item in vqa_evaluations:
            render_score = item.get("render_score", 0)  # 40%
            raw_output_score = item.get("raw_output_score", 0)  # 20%
            vqa_score = item.get("VQA_score", 0)  # 40%
            
            final_score = (0.4 * render_score) + (0.2 * raw_output_score) + (0.4 * vqa_score)
            item["final_eval_score"] = round(final_score, 2)
        
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(vqa_evaluations, out_file, indent=2)

        
def main():
    fire.Fire(StructEvalCLI)

if __name__ == "__main__":
    main()