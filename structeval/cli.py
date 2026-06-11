from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv

from .config import (
    SplitName,
    load_model_registry,
    resolve_model_spec,
    task_filter_label,
    write_init_templates,
)
from .workflows import (
    evaluate_file,
    infer_file_async,
    load_config,
    read_json,
    render_file_async,
    run_coro,
    run_workflow_async,
    safe_model_name,
    summarize_results,
    timestamp_id,
    write_json,
)
from .model_client import env_names_with_fallbacks, get_env_with_fallback


app = typer.Typer(
    help="StructEval lightweight API evaluator.",
    no_args_is_help=True,
)
load_dotenv()


def cfg(config: dict[str, Any], key: str, value: Any, default: Any = None) -> Any:
    return value if value is not None else config.get(key, default)


def require_value(name: str, value: Any) -> Any:
    if value is None:
        raise typer.BadParameter(f"{name} is required via CLI flag or config file.")
    return value


def default_run_dir(model: str) -> Path:
    return Path("runs") / safe_model_name(model) / timestamp_id()


def config_value(
    cli_value: Any,
    config: dict[str, Any],
    key: str,
    model_defaults: dict[str, Any],
    default: Any = None,
) -> Any:
    if cli_value is not None:
        return cli_value
    if key in config:
        return config[key]
    if key in model_defaults:
        return model_defaults[key]
    return default


def merged_litellm_params(
    config_params: dict[str, Any] | None,
    model_params: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(model_params or {})
    merged.update(config_params or {})
    return merged


@app.command("init")
def init_command(
    config_path: Path = typer.Option(Path("structeval.yaml"), "--config-path", help="Config template path."),
    models_path: Path = typer.Option(Path("models/models.yaml"), "--models-path", help="Model registry template path."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
) -> None:
    """Create config and model registry templates."""
    written = write_init_templates(
        config_path=config_path,
        models_path=models_path,
        force=force,
    )
    if written:
        for path in written:
            typer.echo(f"Wrote {path}")
    else:
        typer.echo("Templates already exist. Use --force to overwrite them.")


@app.command(hidden=True)
def infer(
    dataset: Path | None = typer.Option(None, "--dataset", help="Input dataset JSON."),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model name."),
    output_path: Path | None = typer.Option(None, "--output-path", "-o", help="Inference JSON output."),
    config: Path | None = typer.Option(None, "--config", "-c", help="YAML/JSON config."),
    concurrency: int | None = typer.Option(None, "--concurrency", help="Concurrent API requests."),
    temperature: float | None = typer.Option(None, "--temperature", help="Generation temperature."),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Maximum output tokens."),
    timeout: float | None = typer.Option(None, "--timeout", help="Per-request timeout seconds."),
    max_retries: int | None = typer.Option(None, "--max-retries", help="Retries per request."),
    api_base: str | None = typer.Option(None, "--api-base", help="OpenAI-compatible API base."),
    api_key_env: str | None = typer.Option(None, "--api-key-env", help="Environment variable containing API key."),
    split: SplitName | None = typer.Option(None, "--split", help="Dataset split to run."),
    limit: int | None = typer.Option(None, "--limit", help="Limit number of tasks."),
) -> None:
    """Run model inference and write generations."""
    conf = load_config(config)
    registry = load_model_registry(conf.get("models_path"))
    requested_model = require_value("model", cfg(conf, "model", model))
    model_spec = resolve_model_spec(requested_model, registry)
    dataset = Path(require_value("dataset", cfg(conf, "dataset", dataset)))
    output_path = Path(
        cfg(conf, "output_path", output_path, default_run_dir(requested_model) / "inference.json")
    )

    run_coro(
        infer_file_async(
            dataset=dataset,
            output_path=output_path,
            model=model_spec.model,
            concurrency=config_value(concurrency, conf, "concurrency", model_spec.defaults, 8),
            temperature=config_value(temperature, conf, "temperature", model_spec.defaults, 0.0),
            max_tokens=config_value(max_tokens, conf, "max_tokens", model_spec.defaults),
            timeout=config_value(timeout, conf, "timeout", model_spec.defaults),
            max_retries=config_value(max_retries, conf, "max_retries", model_spec.defaults, 2),
            api_base=config_value(api_base, conf, "api_base", model_spec.defaults, model_spec.api_base),
            api_key_env=config_value(api_key_env, conf, "api_key_env", model_spec.defaults, model_spec.api_key_env),
            litellm_params=merged_litellm_params(conf.get("litellm_params"), model_spec.litellm_params),
            split=cfg(conf, "split", split, "full"),
            limit=cfg(conf, "limit", limit),
        )
    )
    typer.echo(f"Wrote inference output: {output_path}")


@app.command(hidden=True)
def render(
    input_path: Path = typer.Option(..., "--input-path", help="Inference JSON to render."),
    img_output_path: Path | None = typer.Option(None, "--img-output-path", help="Directory for rendered images."),
    non_renderable_output_dir: Path | None = typer.Option(
        None,
        "--non-renderable-output-dir",
        help="Directory for extracted non-renderable files.",
    ),
    render_concurrency: int = typer.Option(1, "--render-concurrency", help="Concurrent local render jobs."),
) -> None:
    """Render generated outputs and update the inference JSON in place."""
    run_dir = input_path.parent
    img_output_path = img_output_path or run_dir / "images"
    non_renderable_output_dir = non_renderable_output_dir or run_dir / "non_renderable_format_files"
    run_coro(
        render_file_async(
            input_path=input_path,
            img_output_path=img_output_path,
            non_renderable_output_dir=non_renderable_output_dir,
            render_concurrency=render_concurrency,
        )
    )
    typer.echo(f"Updated rendered metadata in: {input_path}")


@app.command()
def evaluate(
    input_path: Path = typer.Option(..., "--input-path", help="Rendered inference JSON."),
    output_path: Path | None = typer.Option(None, "--output-path", "-o", help="Evaluation JSON output."),
    img_path: Path | None = typer.Option(None, "--img-path", help="Directory containing rendered images."),
    non_renderable_output_dir: Path | None = typer.Option(
        None,
        "--non-renderable-output-dir",
        help="Directory containing extracted non-renderable files.",
    ),
    judge_model: str | None = typer.Option(None, "--judge-model", help="LiteLLM vision judge model."),
    config: Path | None = typer.Option(None, "--config", "-c", help="YAML/JSON config."),
    concurrency: int | None = typer.Option(None, "--concurrency", help="Concurrent judge requests."),
    judge_temperature: float | None = typer.Option(None, "--judge-temperature", help="Judge temperature."),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Maximum judge output tokens."),
    timeout: float | None = typer.Option(None, "--timeout", help="Per-request timeout seconds."),
    max_retries: int | None = typer.Option(None, "--max-retries", help="Retries per request."),
    api_base: str | None = typer.Option(None, "--api-base", help="Judge API base."),
    api_key_env: str | None = typer.Option(None, "--api-key-env", help="Judge API key environment variable."),
) -> None:
    """Evaluate rendered outputs and write score files."""
    conf = load_config(config)
    registry = load_model_registry(conf.get("models_path"))
    judge_model_name = cfg(conf, "judge_model", judge_model)
    judge_spec = resolve_model_spec(judge_model_name, registry) if judge_model_name else None
    run_dir = input_path.parent
    output_path = output_path or run_dir / "evaluation.json"
    summary_path = run_dir / "summary.json"
    img_path = img_path or run_dir / "images"
    non_renderable_output_dir = (
        non_renderable_output_dir or run_dir / "non_renderable_format_files"
    )

    evaluate_file(
        input_path=input_path,
        output_path=output_path,
        img_path=img_path,
        non_renderable_output_dir=non_renderable_output_dir,
        judge_model=judge_spec.model if judge_spec else None,
        concurrency=config_value(
            concurrency,
            conf,
            "concurrency",
            judge_spec.defaults if judge_spec else {},
            4,
        ),
        judge_temperature=config_value(
            judge_temperature,
            conf,
            "judge_temperature",
            judge_spec.defaults if judge_spec else {},
            0.0,
        ),
        max_tokens=config_value(max_tokens, conf, "max_tokens", judge_spec.defaults if judge_spec else {}),
        timeout=config_value(timeout, conf, "timeout", judge_spec.defaults if judge_spec else {}),
        max_retries=config_value(max_retries, conf, "max_retries", judge_spec.defaults if judge_spec else {}, 2),
        api_base=config_value(
            api_base,
            conf,
            "judge_api_base",
            judge_spec.defaults if judge_spec else {},
            judge_spec.api_base if judge_spec else conf.get("api_base"),
        ),
        api_key_env=config_value(
            api_key_env,
            conf,
            "judge_api_key_env",
            judge_spec.defaults if judge_spec else {},
            judge_spec.api_key_env if judge_spec else None,
        ),
        litellm_params=merged_litellm_params(
            conf.get("judge_litellm_params"),
            judge_spec.litellm_params if judge_spec else {},
        ),
        summary_path=summary_path,
    )
    typer.echo(f"Wrote evaluation output: {output_path}")
    typer.echo(f"Wrote summary output: {summary_path}")


@app.command()
def run(
    dataset: Path | None = typer.Option(None, "--dataset", help="Input dataset JSON."),
    model: str | None = typer.Option(None, "--model", help="LiteLLM model name."),
    judge_model: str | None = typer.Option(None, "--judge-model", help="LiteLLM vision judge model."),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Run output directory."),
    config: Path | None = typer.Option(None, "--config", "-c", help="YAML/JSON config."),
    concurrency: int | None = typer.Option(None, "--concurrency", help="Concurrent API requests."),
    render_concurrency: int | None = typer.Option(None, "--render-concurrency", help="Concurrent local render jobs."),
    temperature: float | None = typer.Option(None, "--temperature", help="Generation temperature."),
    judge_temperature: float | None = typer.Option(None, "--judge-temperature", help="Judge temperature."),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Maximum output tokens."),
    timeout: float | None = typer.Option(None, "--timeout", help="Per-request timeout seconds."),
    max_retries: int | None = typer.Option(None, "--max-retries", help="Retries per request."),
    api_base: str | None = typer.Option(None, "--api-base", help="Inference API base."),
    api_key_env: str | None = typer.Option(None, "--api-key-env", help="Inference API key env variable."),
    judge_api_base: str | None = typer.Option(None, "--judge-api-base", help="Judge API base."),
    judge_api_key_env: str | None = typer.Option(None, "--judge-api-key-env", help="Judge API key env variable."),
    split: SplitName | None = typer.Option(None, "--split", help="Dataset split to run."),
    limit: int | None = typer.Option(None, "--limit", help="Limit number of tasks."),
) -> None:
    """Run inference, rendering, evaluation, and summary generation."""
    conf = load_config(config)
    registry = load_model_registry(conf.get("models_path"))
    requested_model = require_value("model", cfg(conf, "model", model))
    model_spec = resolve_model_spec(requested_model, registry)
    judge_model_name = cfg(conf, "judge_model", judge_model)
    judge_spec = resolve_model_spec(judge_model_name, registry) if judge_model_name else None
    dataset = Path(require_value("dataset", cfg(conf, "dataset", dataset)))
    output_dir = Path(cfg(conf, "output_dir", output_dir, default_run_dir(requested_model)))

    paths = run_coro(
        run_workflow_async(
            dataset=dataset,
            output_dir=output_dir,
            model=model_spec.model,
            judge_model=judge_spec.model if judge_spec else None,
            concurrency=config_value(concurrency, conf, "concurrency", model_spec.defaults, 8),
            render_concurrency=config_value(
                render_concurrency,
                conf,
                "render_concurrency",
                model_spec.defaults,
                1,
            ),
            temperature=config_value(temperature, conf, "temperature", model_spec.defaults, 0.0),
            judge_temperature=config_value(
                judge_temperature,
                conf,
                "judge_temperature",
                judge_spec.defaults if judge_spec else {},
                0.0,
            ),
            max_tokens=config_value(max_tokens, conf, "max_tokens", model_spec.defaults),
            timeout=config_value(timeout, conf, "timeout", model_spec.defaults),
            max_retries=config_value(max_retries, conf, "max_retries", model_spec.defaults, 2),
            api_base=config_value(api_base, conf, "api_base", model_spec.defaults, model_spec.api_base),
            api_key_env=config_value(api_key_env, conf, "api_key_env", model_spec.defaults, model_spec.api_key_env),
            litellm_params=merged_litellm_params(conf.get("litellm_params"), model_spec.litellm_params),
            judge_api_base=config_value(
                judge_api_base,
                conf,
                "judge_api_base",
                judge_spec.defaults if judge_spec else {},
                judge_spec.api_base if judge_spec else conf.get("api_base"),
            ),
            judge_api_key_env=config_value(
                judge_api_key_env,
                conf,
                "judge_api_key_env",
                judge_spec.defaults if judge_spec else {},
                judge_spec.api_key_env if judge_spec else None,
            ),
            judge_litellm_params=merged_litellm_params(
                conf.get("judge_litellm_params"),
                judge_spec.litellm_params if judge_spec else {},
            ),
            split=cfg(conf, "split", split, "full"),
            limit=cfg(conf, "limit", limit),
        )
    )
    typer.echo("Run complete.")
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")


@app.command()
def reproduce(
    dataset: Path | None = typer.Option(None, "--dataset", help="Input dataset JSON."),
    model: str | None = typer.Option(None, "--model", help="Model alias or LiteLLM model name."),
    task: str | None = typer.Option(None, "--task", help="Paper subtask, e.g. svg, T->SVG, JSON->YAML. Omit for full."),
    judge_model: str | None = typer.Option(None, "--judge-model", help="VQA judge model."),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Run output directory."),
    config: Path | None = typer.Option(None, "--config", "-c", help="YAML/JSON config."),
    concurrency: int | None = typer.Option(None, "--concurrency", help="Concurrent API requests."),
    render_concurrency: int | None = typer.Option(None, "--render-concurrency", help="Concurrent local render jobs."),
    timeout: float | None = typer.Option(None, "--timeout", help="Per-request timeout seconds."),
    max_retries: int | None = typer.Option(None, "--max-retries", help="Retries per request."),
    api_base: str | None = typer.Option(None, "--api-base", help="Inference API base."),
    api_key_env: str | None = typer.Option(None, "--api-key-env", help="Inference API key env variable."),
    judge_api_base: str | None = typer.Option(None, "--judge-api-base", help="Judge API base."),
    judge_api_key_env: str | None = typer.Option(None, "--judge-api-key-env", help="Judge API key env variable."),
    limit: int | None = typer.Option(None, "--limit", help="Limit number of tasks after task filtering."),
) -> None:
    """Run a paper-style subtask reproduction with StructEval settings."""
    conf = load_config(config)
    registry = load_model_registry(conf.get("models_path"))
    requested_model = require_value("model", cfg(conf, "model", model))
    requested_task = cfg(conf, "task", task)
    model_spec = resolve_model_spec(requested_model, registry)

    judge_model_name = cfg(conf, "judge_model", judge_model)
    if judge_model_name is None:
        model_identity = f"{requested_model} {model_spec.model}".lower()
        judge_model_name = requested_model if "gpt-4.1-mini" in model_identity else "gpt-4.1-mini"
    judge_spec = resolve_model_spec(judge_model_name, registry)

    dataset = Path(cfg(conf, "dataset", dataset, Path("dataset/StructEval_dataset.json")))
    task_label = task_filter_label(requested_task)
    default_output_dir = (
        Path("runs")
        / "reproduce"
        / safe_model_name(requested_model)
        / safe_model_name(task_label)
        / timestamp_id()
    )
    output_dir = Path(cfg(conf, "output_dir", output_dir, default_output_dir))

    resolved_api_base = config_value(api_base, conf, "api_base", model_spec.defaults, model_spec.api_base)
    resolved_api_key_env = config_value(
        api_key_env,
        conf,
        "api_key_env",
        model_spec.defaults,
        model_spec.api_key_env,
    )
    judge_is_same_model = judge_model_name == requested_model or judge_spec.model == model_spec.model
    resolved_judge_api_base = config_value(
        judge_api_base,
        conf,
        "judge_api_base",
        judge_spec.defaults,
        judge_spec.api_base or (resolved_api_base if judge_is_same_model else conf.get("api_base")),
    )
    resolved_judge_api_key_env = config_value(
        judge_api_key_env,
        conf,
        "judge_api_key_env",
        judge_spec.defaults,
        judge_spec.api_key_env or (resolved_api_key_env if judge_is_same_model else None),
    )

    paths = run_coro(
        run_workflow_async(
            dataset=dataset,
            output_dir=output_dir,
            model=model_spec.model,
            judge_model=judge_spec.model,
            concurrency=config_value(concurrency, conf, "concurrency", model_spec.defaults, 32),
            render_concurrency=config_value(
                render_concurrency,
                conf,
                "render_concurrency",
                model_spec.defaults,
                4,
            ),
            temperature=0.0,
            judge_temperature=0.0,
            max_tokens=None,
            timeout=config_value(timeout, conf, "timeout", model_spec.defaults),
            max_retries=config_value(max_retries, conf, "max_retries", model_spec.defaults, 2),
            api_base=resolved_api_base,
            api_key_env=resolved_api_key_env,
            litellm_params=merged_litellm_params(conf.get("litellm_params"), model_spec.litellm_params),
            judge_api_base=resolved_judge_api_base,
            judge_api_key_env=resolved_judge_api_key_env,
            judge_litellm_params=merged_litellm_params(
                conf.get("judge_litellm_params"),
                judge_spec.litellm_params,
            ),
            split="full",
            task=requested_task,
            limit=limit,
        )
    )
    typer.echo("Reproduce run complete.")
    typer.echo(f"task: {task_label}")
    typer.echo("paper settings: temperature=0.0, judge_temperature=0.0, max_tokens=unlimited")
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")


@app.command()
def summary(
    input_path: Path = typer.Option(..., "--input-path", help="Evaluation JSON input."),
    output_path: Path | None = typer.Option(None, "--output-path", "-o", help="Summary JSON output."),
) -> None:
    """Summarize an evaluation JSON file."""
    results = read_json(input_path)
    summary_data = summarize_results(results)
    if output_path is not None:
        write_json(output_path, summary_data)
        typer.echo(f"Wrote summary output: {output_path}")
    else:
        typer.echo(json.dumps(summary_data, indent=2, ensure_ascii=False))


@app.command()
def doctor(
    render: bool = typer.Option(False, "--render", help="Also check render dependencies."),
    api_key_env: str | None = typer.Option(None, "--api-key-env", help="Required API key env var."),
) -> None:
    """Check local dependencies and common API key environment variables."""
    checks: list[tuple[str, bool, str]] = []

    checks.append(("litellm package", importlib.util.find_spec("litellm") is not None, "pip install litellm"))
    checks.append(("typer package", importlib.util.find_spec("typer") is not None, "pip install typer"))

    env_names = [api_key_env] if api_key_env else [
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    for env_name in env_names:
        if env_name:
            accepted_names = env_names_with_fallbacks(env_name)
            label = " or ".join(accepted_names)
            checks.append((label, bool(get_env_with_fallback(env_name)), f"export {env_name}=..."))

    if render:
        checks.extend(
            [
                ("playwright package", importlib.util.find_spec("playwright") is not None, "uv sync --extra render"),
                ("node", shutil.which("node") is not None, "install node"),
                ("npm", shutil.which("npm") is not None, "install npm"),
                ("pdflatex or tectonic", bool(shutil.which("pdflatex") or shutil.which("tectonic")), "install TeX"),
                ("typst", shutil.which("typst") is not None, "install typst"),
                ("magick or convert", bool(shutil.which("magick") or shutil.which("convert")), "install ImageMagick"),
            ]
        )

    failed = False
    for name, ok, hint in checks:
        status = "OK" if ok else "MISSING"
        typer.echo(f"{status:7} {name}")
        if not ok:
            failed = True
            typer.echo(f"        {hint}")

    if failed:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
