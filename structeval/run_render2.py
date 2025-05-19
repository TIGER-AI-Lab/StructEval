import os
import logging
import json
import asyncio
from render_engine.main import process_json_file as render_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def render(input_path: str, img_output_path: str, non_renderable_output_dir: str):
    """
    Render the generated code to images using the comprehensive render engine.
    Supports multiple output formats based on task type code.
    """
    os.makedirs(img_output_path, exist_ok=True)
    os.makedirs(non_renderable_output_dir, exist_ok=True)

    # Get metadata about renderable tasks
    with open(input_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    total_tasks = len(tasks)
    renderable_tasks = sum(1 for task in tasks if task.get("rendering", False))

    # Count by output type
    type_codes = {}
    for task in tasks:
        if task.get("rendering", False):
            task_id = task.get("task_id", "000000")
            if len(task_id) >= 4:
                type_code = task_id[2:4]
                type_codes[type_code] = type_codes.get(type_code, 0) + 1

    print(
        f"Found {renderable_tasks} renderable tasks out of {total_tasks} total tasks."
    )

    # Process rendering
    await render_task(input_path, img_output_path, non_renderable_output_dir)


async def run_render(infer_output, img_output_path, non_renderable_output_dir):
    os.makedirs(img_output_path, exist_ok=True)

    logger.info(f"Rendering from {infer_output}...")
    await render(
        input_path=infer_output,
        img_output_path=img_output_path,
        non_renderable_output_dir=non_renderable_output_dir,
    )


if __name__ == "__main__":
    base_output_dir = "experiment_results"

    models = [
        #"meta-llama/Meta-Llama-3-8B-Instruct",
        #"meta-llama/Llama-3.1-8B-Instruct",
        # "Qwen/Qwen2.5-7B",
        #"Qwen/Qwen3-4B"
        #"microsoft/Phi-3-mini-128k-instruct",
        # "microsoft/Phi-4-mini-instruct",
        "gpt-4o-mini",
        # "gpt-4o",
        # "gpt-4.1-mini",
        # "o1-mini",
        # "gemini-2.0-flash",
        # "gemini-1.5-pro"
    ]

    for model in models:
        model_id = model.split("/")[-1]
        output_dir = os.path.join(base_output_dir, model_id)
        infer_output = os.path.join(output_dir, "toml.json")
        img_output_path = os.path.join(output_dir, "toml_rendered")
        non_renderable_output_dir = os.path.join(output_dir, "non_renderable_files")
        asyncio.run(
            run_render(infer_output, img_output_path, non_renderable_output_dir)
        )
