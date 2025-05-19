import fire
import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from inference import run_inference
from render_engine.main import process_json_file as render_task
from render_engine.render_utils import determine_output_type as get_rendering_type
from eval_engine.main import evaluate_dataset


class StructEvalCLI:

    def __init__(self):
        pass

    def inference(
        self,
        llm_model_name: str,
        llm_engine: str,
        input_path: str,
        output_path: str,
        **kwargs,
    ):
        """Run inference on the input dataset using the specified LLM."""
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        queries = [
            f"""{item['query']}
            \n\nIMPORTANT: Only output the required renderable or executable code. You must start the code with <code> and end the code with </code> (they are code block indicators, not HTML tags). No other text output (explanation, comments, etc.) are allowed.
            {"\n\n/no_think" if llm_model_name == "Qwen/Qwen3-4B" else ""}
            """
            for item in data
        ]

        if llm_model_name == "Qwen/Qwen3-4B":
            print("Qwen3-4B I'm here")

        generations = run_inference(llm_model_name, llm_engine, queries, **kwargs)

        output_data = []
        for item, generation in zip(data, generations):
            item["generation"] = generation
            output_data.append(item)

        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(output_data, out_file, indent=2)

        return output_path

    async def render(
        self, input_path: str, img_output_path: str, non_renderable_output_dir: str
    ):
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

    def evaluate(
        self,
        vlm_model_name: str,
        vlm_engine: str,
        input_path: str,
        output_path: str,
        img_path: str,
        non_renderable_output_dir: str,
        **kwargs,
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

        images = {
            item["task_id"]: f"{img_path}/{item['task_id']}.png"
            for item in data
            if os.path.exists(f"{img_path}/{item['task_id']}.png")
        }

        # Get metadata about evaluation categories
        categories = {
            "text_to_renderable": 0,
            "text_to_nonrenderable": 0,
            "nontext_to_renderable": 0,
            "nontext_to_nonrenderable": 0,
        }

        for task in data:
            is_renderable = task.get("rendering", False)
            has_text_input = task.get("input_type") == "Text"

            if is_renderable and has_text_input:
                categories["text_to_renderable"] += 1
            elif is_renderable and not has_text_input:
                categories["nontext_to_renderable"] += 1
            elif not is_renderable and has_text_input:
                categories["text_to_nonrenderable"] += 1
            else:
                categories["nontext_to_nonrenderable"] += 1

        print(f"Evaluation task categories: {categories}")

        # Use the evaluate function from eval_engine
        non_renderable_dir = os.path.join(
            os.path.dirname(img_path), "non_renderable_format_files"
        )
        evaluation_results = evaluate_dataset(
            data,
            images,
            vlm_model_name,
            vlm_engine,
            non_renderable_dir=non_renderable_dir,
            **kwargs,
        )

        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(evaluation_results, out_file, indent=2)

        # Print summary statistics
        total_tasks = len(evaluation_results)
        avg_score = (
            sum(item.get("final_eval_score", 0) for item in evaluation_results)
            / total_tasks
            if total_tasks > 0
            else 0
        )

        print("\n=== EVALUATION SUMMARY ===")
        print(f"Total tasks evaluated: {total_tasks}")
        print(f"Average score: {avg_score:.2f}")

        # Summarize by input/output types
        renderable = [i for i in evaluation_results if i.get("rendering", False)]
        non_renderable = [
            i for i in evaluation_results if not i.get("rendering", False)
        ]

        print(
            f"Renderable tasks: {len(renderable)}, Avg score: {sum(i.get('final_eval_score', 0) for i in renderable) / len(renderable) if renderable else 0:.2f}"
        )
        print(
            f"Non-renderable tasks: {len(non_renderable)}, Avg score: {sum(i.get('final_eval_score', 0) for i in non_renderable) / len(non_renderable) if non_renderable else 0:.2f}"
        )

        return output_path


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
