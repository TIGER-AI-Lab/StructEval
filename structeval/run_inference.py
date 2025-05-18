import os
import logging
import torch
import gc
from cli import StructEvalCLI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_inference(input_file, output_dir, llm_model_name):

    torch.cuda.empty_cache()
    gc.collect()


    os.makedirs(output_dir, exist_ok=True)
    infer_output = os.path.join(output_dir, "inference_output.json")

    cli = StructEvalCLI()
    llm_engine = "vllm"

    logger.info(f"Running inference for model {llm_model_name}...")
    cli.inference(
        llm_model_name=llm_model_name,
        llm_engine=llm_engine,
        input_path=input_file,
        output_path=infer_output
    )

if __name__ == "__main__":
    input_path = "../scripts/NewCleanedDataset.json"
    base_output_dir = "experiment_results"

    models = [
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "Qwen/Qwen1.5-7B-Chat",
        "Qwen/Qwen1.5-14B-Chat",
        "Qwen/Qwen2.5-7B",
        "Qwen/Qwen3-4B-Base",
        "microsoft/Phi-3-mini-128k-instruct",
        "microsoft/Phi-4-mini-instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
    ]

    for model in models:
        model_id = model.split("/")[-1]
        output_dir = os.path.join(base_output_dir, model_id)
        run_inference(input_path, output_dir, model)