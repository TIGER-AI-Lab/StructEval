import fire
import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from inference import run_inference
from render import process_json_file, get_rendering_metadata
from evaluation import vqa_eval, raw_output_eval

class StructEvalCLI:
    
    def __init__(self):
        pass
    
    def inference(
        self,
        llm_model_name: str,
        llm_engine: str,
        input_path: str,
        output_path: str,
        **kwargs
    ):
        """Run inference on the input dataset using the specified LLM."""
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        queries = [
            f"{item['query']}\n\nIMPORTANT: Only output the executable code. You must not include any other things, such as explanations, comments, or markdown (```, **, #), or any formatting hints etc. You must start the code with <code> and end the code with </code> tags" 
            for item in data
        ]   

        generations = run_inference(llm_model_name, llm_engine, queries, **kwargs)

        output_data = []
        for item, generation in zip(data, generations):
            item["generation"] = generation  
            output_data.append(item)
        
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(output_data, out_file, indent=2)
            
        return output_path
    
    async def render(
        self,
        input_path: str,
        img_output_path: str
    ):
        """
        Render the generated code to images using the comprehensive render engine.
        Supports multiple output formats based on task type code.
        """
        os.makedirs(img_output_path, exist_ok=True)
        
        # Get metadata about renderable tasks
        metadata = await get_rendering_metadata(input_path)
        print(f"Found {metadata['renderable_tasks']} renderable tasks out of {metadata['total_tasks']} total tasks.")
        
        # Process rendering
        await process_json_file(input_path, img_output_path)
        
        return img_output_path
    
    def evaluate(
        self,
        vlm_model_name: str,
        vlm_engine: str,
        input_path: str,
        output_path: str,
        img_path: str,
        **kwargs
    ):
        """
        Evaluate the generated code using different strategies based on input/output types:
        
        1. Input: text, Output: renderable - Raw output metric + VQA on screenshots
        2. Input: text, Output: non-renderable - Dictionary validation + key checking
        3. Input: non-text, Output: renderable - Same as case 1
        4. Input: non-text, Output: non-renderable - Structure comparison with partial scoring
        """
        print(f"Evaluating model with vlm_model_name: {vlm_model_name}")

        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        images = {item["task_id"]: f"{img_path}/{item['task_id']}.png" 
                 for item in data if os.path.exists(f"{img_path}/{item['task_id']}.png")}
        
        # Use the comprehensive evaluation function that handles all scenarios
        from evaluation import comprehensive_eval
        evaluation_results = comprehensive_eval(data, images, vlm_model_name, vlm_engine)
        
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(evaluation_results, out_file, indent=2)
            
        # Print summary statistics
        total_tasks = len(evaluation_results)
        avg_score = sum(item.get("final_eval_score", 0) for item in evaluation_results) / total_tasks if total_tasks > 0 else 0
        
        print("\n=== EVALUATION SUMMARY ===")
        print(f"Total tasks evaluated: {total_tasks}")
        print(f"Average score: {avg_score:.2f}")
        
        # Summarize by input/output types
        renderable = [i for i in evaluation_results if i.get("useVisualRendering", False)]
        non_renderable = [i for i in evaluation_results if not i.get("useVisualRendering", False)]
        
        print(f"Renderable tasks: {len(renderable)}, Avg score: {sum(i.get('final_eval_score', 0) for i in renderable) / len(renderable) if renderable else 0:.2f}")
        print(f"Non-renderable tasks: {len(non_renderable)}, Avg score: {sum(i.get('final_eval_score', 0) for i in non_renderable) / len(non_renderable) if non_renderable else 0:.2f}")
        
        return output_path
    
    async def run_pipeline(
        self,
        input_path: str,
        llm_model_name: str,
        llm_engine: str,
        vlm_model_name: str,
        vlm_engine: str,
        output_dir: str = "outputs",
        inference_only: bool = False,
        skip_inference: bool = False,
        inference_output_path: Optional[str] = None,
        **kwargs
    ):
        """
        Run the complete StructEval pipeline: inference → rendering → evaluation
        
        Args:
            input_path: Path to the input dataset
            llm_model_name: Name of the LLM to use for inference
            llm_engine: Engine to use for running the LLM
            vlm_model_name: Name of the VLM to use for evaluation
            vlm_engine: Engine to use for running the VLM
            output_dir: Directory to save outputs
            inference_only: Only run inference, skip rendering and evaluation
            skip_inference: Skip inference, use existing inference output
            inference_output_path: Path to existing inference output (required if skip_inference=True)
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Define output paths
        infer_output = inference_output_path or os.path.join(output_dir, "inference_output.json")
        img_output_path = os.path.join(output_dir, "rendered_images")
        eval_output_path = os.path.join(output_dir, "evaluation_results.json")
        
        # Step 1: Inference (optional skip)
        if not skip_inference:
            print(f"Running inference with {llm_model_name} on {llm_engine}...")
            infer_output = self.inference(
                llm_model_name=llm_model_name,
                llm_engine=llm_engine,
                input_path=input_path,
                output_path=infer_output,
                **kwargs
            )
            print(f"Inference completed. Output saved to {infer_output}")
        else:
            if not inference_output_path or not os.path.exists(inference_output_path):
                raise ValueError("inference_output_path must be provided and exist when skip_inference=True")
            print(f"Skipping inference, using existing output: {infer_output}")
        
        if inference_only:
            print("Inference-only mode, skipping rendering and evaluation.")
            return infer_output
        
        # Step 2: Rendering
        print(f"Rendering generated code to {img_output_path}...")
        img_output_path = await self.render(
            input_path=infer_output,
            img_output_path=img_output_path
        )
        print(f"Rendering completed. Images saved to {img_output_path}")
        
        # Step 3: Evaluation
        print(f"Evaluating with {vlm_model_name} on {vlm_engine}...")
        eval_output = self.evaluate(
            vlm_model_name=vlm_model_name,
            vlm_engine=vlm_engine,
            input_path=infer_output,
            output_path=eval_output_path,
            img_path=img_output_path,
            **kwargs
        )
        print(f"Evaluation completed. Results saved to {eval_output}")
        
        # Print summary statistics
        with open(eval_output, "r", encoding="utf-8") as f:
            results = json.load(f)
        
        total_tasks = len(results)
        avg_score = sum(item.get("final_eval_score", 0) for item in results) / total_tasks if total_tasks > 0 else 0
        
        print("\n=== EVALUATION SUMMARY ===")
        print(f"Total tasks evaluated: {total_tasks}")
        print(f"Average score: {avg_score:.2f}")
        
        return {
            "inference_output": infer_output,
            "images_output": img_output_path,
            "evaluation_output": eval_output,
            "avg_score": avg_score
        }

def main():
    def async_to_sync(async_func):
        def wrapper(*args, **kwargs):
            return asyncio.run(async_func(*args, **kwargs))
        return wrapper
    
    StructEvalCLI.run_pipeline = async_to_sync(StructEvalCLI.run_pipeline)
    StructEvalCLI.render = async_to_sync(StructEvalCLI.render)
    
    fire.Fire(StructEvalCLI)

if __name__ == "__main__":
    main()