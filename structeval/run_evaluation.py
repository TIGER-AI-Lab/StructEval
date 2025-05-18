import os
import logging
from cli import StructEvalCLI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_evaluation_only(infer_output, img_output_path, eval_output_path, non_renderable_output_dir):
    cli = StructEvalCLI()
    engine = "openai"
    model_name = "gpt-4.1-mini"

    logger.info("Running evaluation...")
    cli.evaluate(
        vlm_model_name=model_name,
        vlm_engine=engine,
        input_path=infer_output,
        output_path=eval_output_path,
        img_path=img_output_path,
        non_renderable_output_dir=non_renderable_output_dir
    )

if __name__ == "__main__":
    base_output_dir = "experiment_results"

    models = [
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "Qwen/Qwen2.5-7B",
        "Qwen/Qwen3-4B",
        "microsoft/Phi-3-mini-128k-instruct",
        "microsoft/Phi-4-mini-instruct",
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1-mini",
        "o1-mini",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]

    for model in models:
        model_id = model.split("/")[-1]
        output_dir = os.path.join(base_output_dir, model_id)

        infer_output = os.path.join(output_dir, "inference_nonrenderable.json")
        img_output_path = os.path.join(output_dir, "rendered_images")
        non_renderable_output_path = os.path.join(output_dir, "non_renderable_files")
        eval_output_path = os.path.join(output_dir, "evaluate_nonrenderable.json")

        print(f"Now evaluating model: {model}")
        run_evaluation_only(infer_output, img_output_path, eval_output_path, non_renderable_output_path)