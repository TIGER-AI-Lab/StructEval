from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .config import filter_by_split, filter_by_task, task_filter_label
from .eval_engine.main import evaluate_dataset
from .inference import run_inference_async


def load_config(config_path: str | Path | None) -> dict[str, Any]:
    if config_path is None:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        loaded = json.loads(text)
    else:
        loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a mapping/object at the top level.")
    return loaded


def safe_model_name(model: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-")
    return safe or "model"


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, data: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    return output_path


async def infer_file_async(
    *,
    dataset: str | Path,
    output_path: str | Path,
    model: str,
    concurrency: int = 8,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float | None = None,
    max_retries: int = 2,
    api_base: str | None = None,
    api_key_env: str | None = None,
    litellm_params: dict[str, Any] | None = None,
    split: str = "full",
    task: str | None = None,
    limit: int | None = None,
) -> Path:
    data = read_json(dataset)
    data = filter_by_split(data, split)
    data = filter_by_task(data, task)
    if task is not None and not data:
        raise ValueError(f"No dataset items matched task filter: {task}")
    if limit is not None:
        data = data[:limit]
    queries = [item["query"] for item in data]
    generations = await run_inference_async(
        model,
        queries,
        concurrency=concurrency,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        api_base=api_base,
        api_key_env=api_key_env,
        litellm_params=litellm_params or {},
    )

    for item, generation in zip(data, generations):
        item["generation"] = generation

    return write_json(output_path, data)


async def render_file_async(
    *,
    input_path: str | Path,
    img_output_path: str | Path,
    non_renderable_output_dir: str | Path,
    render_concurrency: int = 1,
) -> Path:
    from .render_engine.main import process_json_file

    Path(img_output_path).mkdir(parents=True, exist_ok=True)
    Path(non_renderable_output_dir).mkdir(parents=True, exist_ok=True)
    await process_json_file(
        str(input_path),
        str(img_output_path),
        str(non_renderable_output_dir),
        render_concurrency=render_concurrency,
    )
    return Path(input_path)


def image_map(data: list[dict[str, Any]], img_path: str | Path) -> dict[str, str]:
    image_dir = Path(img_path)
    return {
        item["task_id"]: str(image_dir / f"{item['task_id']}.png")
        for item in data
        if (image_dir / f"{item['task_id']}.png").exists()
    }


def evaluate_file(
    *,
    input_path: str | Path,
    output_path: str | Path,
    img_path: str | Path,
    non_renderable_output_dir: str | Path,
    judge_model: str | None = None,
    concurrency: int = 4,
    judge_temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float | None = None,
    max_retries: int = 2,
    api_base: str | None = None,
    api_key_env: str | None = None,
    litellm_params: dict[str, Any] | None = None,
    summary_path: str | Path | None = None,
) -> Path:
    data = read_json(input_path)
    results = evaluate_dataset(
        data,
        image_map(data, img_path),
        judge_model,
        None,
        non_renderable_dir=str(non_renderable_output_dir),
        concurrency=concurrency,
        temperature=judge_temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        api_base=api_base,
        api_key_env=api_key_env,
        litellm_params=litellm_params or {},
    )
    output = write_json(output_path, results)
    if summary_path is not None:
        write_json(summary_path, summarize_results(results))
    return output


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    def group_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        count = len(items)
        if count == 0:
            return {"count": 0, "average_final_eval_score": 0.0}
        return {
            "count": count,
            "average_final_eval_score": round(
                sum(item.get("final_eval_score", 0) for item in items) / count, 4
            ),
            "average_render_score": round(
                sum(item.get("render_score", 0) for item in items) / count, 4
            ),
        }

    renderable = [item for item in results if item.get("rendering", False)]
    non_renderable = [item for item in results if not item.get("rendering", False)]
    output_types = sorted({item.get("output_type", "unknown") for item in results})
    return {
        "all": group_summary(results),
        "renderable": group_summary(renderable),
        "non_renderable": group_summary(non_renderable),
        "by_output_type": {
            output_type: group_summary(
                [item for item in results if item.get("output_type", "unknown") == output_type]
            )
            for output_type in output_types
        },
    }


async def run_workflow_async(
    *,
    dataset: str | Path,
    output_dir: str | Path,
    model: str,
    judge_model: str | None,
    concurrency: int = 8,
    temperature: float = 0.0,
    judge_temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float | None = None,
    max_retries: int = 2,
    api_base: str | None = None,
    api_key_env: str | None = None,
    litellm_params: dict[str, Any] | None = None,
    judge_api_base: str | None = None,
    judge_api_key_env: str | None = None,
    judge_litellm_params: dict[str, Any] | None = None,
    split: str = "full",
    task: str | None = None,
    limit: int | None = None,
    render_concurrency: int = 1,
) -> dict[str, str]:
    run_dir = Path(output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    inference_path = run_dir / "inference.json"
    images_path = run_dir / "images"
    non_renderable_path = run_dir / "non_renderable_format_files"
    evaluation_path = run_dir / "evaluation.json"
    summary_path = run_dir / "summary.json"
    metadata_path = run_dir / "run.json"

    await infer_file_async(
        dataset=dataset,
        output_path=inference_path,
        model=model,
        concurrency=concurrency,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        api_base=api_base,
        api_key_env=api_key_env,
        litellm_params=litellm_params or {},
        split=split,
        task=task,
        limit=limit,
    )
    await render_file_async(
        input_path=inference_path,
        img_output_path=images_path,
        non_renderable_output_dir=non_renderable_path,
        render_concurrency=render_concurrency,
    )
    await asyncio.to_thread(
        evaluate_file,
        input_path=inference_path,
        output_path=evaluation_path,
        img_path=images_path,
        non_renderable_output_dir=non_renderable_path,
        judge_model=judge_model,
        concurrency=concurrency,
        judge_temperature=judge_temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        api_base=judge_api_base,
        api_key_env=judge_api_key_env,
        litellm_params=judge_litellm_params or {},
        summary_path=summary_path,
    )
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset),
        "model": model,
        "judge_model": judge_model,
        "split": split,
        "task": task,
        "task_label": task_filter_label(task),
        "limit": limit,
        "paths": {
            "inference": str(inference_path),
            "images": str(images_path),
            "non_renderable": str(non_renderable_path),
            "evaluation": str(evaluation_path),
            "summary": str(summary_path),
        },
        "settings": {
            "concurrency": concurrency,
            "render_concurrency": render_concurrency,
            "temperature": temperature,
            "judge_temperature": judge_temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            "api_base": api_base,
            "api_key_env": api_key_env,
            "judge_api_base": judge_api_base,
            "judge_api_key_env": judge_api_key_env,
        },
    }
    write_json(metadata_path, metadata)

    return {
        "inference": str(inference_path),
        "images": str(images_path),
        "non_renderable": str(non_renderable_path),
        "evaluation": str(evaluation_path),
        "summary": str(summary_path),
        "metadata": str(metadata_path),
    }


def run_coro(coro: Any) -> Any:
    return asyncio.run(coro)
