from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from structeval.model_client import LiteLLMClient, LiteLLMSettings, image_to_data_url


def build_vqa_prompt(vqa_questions: list[dict[str, Any]]) -> str:
    qa_list = ""
    for idx, vqa in enumerate(vqa_questions, 1):
        qa_list += (
            f"{idx}. Question: {vqa['question']} "
            f"Expected Answer: {vqa['answer']}\n"
        )
    return (
        "You are given an image and a list of question-answer pairs. "
        "For each pair, verify if the image content supports the expected answer "
        "based on the corresponding question. If the image is fully white, then "
        "you should always output false. Base your judgment solely on the visual "
        "content of the provided image, and the question. Do not imagine anything. "
        "Do not use any external information or common-sense reasoning beyond "
        "what is visible. Respond with a JSON object mapping each question number "
        "to true or false (e.g., {\"1\": true, \"2\": false}). If the image is "
        "unclear or does not contain enough information to answer, use null for "
        "that question. Here are the question-answer pairs:\n"
        f"{qa_list}"
    )


def parse_vqa_response(response: str) -> dict[str, Any]:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


async def vqa_eval_async(
    model_name: str,
    vlm_engine: str | None = None,
    data: list[dict[str, Any]] | None = None,
    images: dict[str, str] | None = None,
    **kwargs
) -> list[dict[str, Any]]:
    """
    Visual Question Answering evaluation for renderable outputs.
    
    Args:
        model_name: Name of the VLM model
        vlm_engine: Engine for VLM evaluation
        additional_args: Additional arguments to pass to the VLM
        data: List of tasks to evaluate
        images: Dictionary mapping task_id to image paths
        
    Returns:
        List of evaluated tasks with VQA scores
    """
    # Handle default parameters
    if data is None:
        data = []
    if images is None:
        images = {}
        
    logging.info(f"Running VQA evaluation with model {model_name} on {len(data)} tasks")

    client = LiteLLMClient(
        LiteLLMSettings(
            model=model_name,
            temperature=kwargs.get("temperature", 0.0),
            max_tokens=kwargs.get("max_tokens"),
            timeout=kwargs.get("timeout"),
            max_retries=kwargs.get("max_retries", 2),
            api_base=kwargs.get("api_base"),
            api_key_env=kwargs.get("api_key_env"),
            litellm_params=kwargs.get("litellm_params") or {},
        )
    )

    concurrency = max(1, int(kwargs.get("concurrency", 4)))
    semaphore = asyncio.Semaphore(concurrency)
    output_data: list[dict[str, Any] | None] = [None] * len(data)

    async def evaluate_one(index: int, item: dict[str, Any]) -> None:
        task_id = item.get("task_id")
        img_file = images.get(task_id)

        if not img_file or not os.path.exists(img_file):
            item["VQA_score"] = 0.0
            item["render_score"] = item.get("render_score", 0.0)
            item["VQAeval"] = []
            output_data[index] = item
            return

        vqa_questions = item.get("VQA", [])
        total_questions = len(vqa_questions)
        if total_questions == 0:
            item["VQA_score"] = 0.0
            item["VQAeval"] = []
            output_data[index] = item
            return

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_vqa_prompt(vqa_questions)},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_to_data_url(img_file)},
                    },
                ],
            }
        ]

        try:
            async with semaphore:
                response = await client.complete(messages, temperature=kwargs.get("temperature", 0.0))
            parsed = parse_vqa_response(response)
            evaluations = [parsed.get(str(idx)) for idx in range(1, total_questions + 1)]
            true_count = sum(1 for ans in evaluations if ans is True)
        except Exception as e:
            logging.error(f"VQA evaluation failed for {task_id}: {e}")
            evaluations = [None] * total_questions
            true_count = 0

        item["VQA_score"] = true_count / total_questions
        item["VQAeval"] = evaluations
        output_data[index] = item

    await asyncio.gather(*(evaluate_one(index, item) for index, item in enumerate(data)))
    
    logging.info(f"VQA evaluation completed for {len(data)} tasks")
    return [item for item in output_data if item is not None]


def vqa_eval(
    model_name: str,
    vlm_engine: str | None = None,
    data: list[dict[str, Any]] | None = None,
    images: dict[str, str] | None = None,
    **kwargs,
) -> list[dict[str, Any]]:
    return asyncio.run(vqa_eval_async(model_name, vlm_engine, data, images, **kwargs))
