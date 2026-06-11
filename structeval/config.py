from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Literal

import yaml


SplitName = Literal["full", "renderable", "nonrenderable"]

FORMAT_NAMES = {
    "angular": "Angular",
    "canvas": "Canvas",
    "csv": "CSV",
    "html": "HTML",
    "json": "JSON",
    "latex": "Latex",
    "markdown": "Markdown",
    "matplotlib": "Matplotlib",
    "mermaid": "Mermaid",
    "react": "React",
    "svg": "SVG",
    "t": "Text",
    "text": "Text",
    "tikz": "Tikz",
    "toml": "TOML",
    "typst": "Typst",
    "vega": "Vega",
    "vue": "Vue",
    "xml": "XML",
    "yaml": "YAML",
}

FORMAT_LABELS = {
    "text": "T",
    "latex": "LaTeX",
    "tikz": "TikZ",
}


CONFIG_TEMPLATE = """dataset: dataset/StructEval_dataset.json
output_dir: runs/deepseek-v4-pro
model: deepseek-v4-pro
judge_model: gpt-4.1-mini
split: full
concurrency: 8
render_concurrency: 1
temperature: 0.0
judge_temperature: 0.0
max_tokens: null
timeout: null
max_retries: 2
"""


MODELS_TEMPLATE = """models:
  deepseek-v4-pro:
    model: deepseek/deepseek-v4-pro
    api_key_env: DEEPSEEK_API_KEY

  gpt-4.1-mini:
    model: openai/gpt-4.1-mini
    api_key_env: OPENAI_API_KEY

  claude-sonnet-4:
    model: anthropic/claude-sonnet-4
    api_key_env: ANTHROPIC_API_KEY

  openrouter-gpt-4.1-mini:
    model: openrouter/openai/gpt-4.1-mini
    api_key_env: OPENROUTER_API_KEY
"""


@dataclass
class ModelSpec:
    name: str
    model: str
    api_base: str | None = None
    api_key_env: str | None = None
    litellm_params: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)


def load_model_registry(path: str | Path | None = None) -> dict[str, ModelSpec]:
    registry_path = Path(path or "models/models.yaml")
    if not registry_path.exists():
        return {}
    loaded = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    raw_models = loaded.get("models", loaded)
    if not isinstance(raw_models, dict):
        raise ValueError(f"Model registry must contain a mapping: {registry_path}")

    registry: dict[str, ModelSpec] = {}
    for alias, raw_spec in raw_models.items():
        if isinstance(raw_spec, str):
            spec = {"model": raw_spec}
        elif isinstance(raw_spec, dict):
            spec = dict(raw_spec)
        else:
            raise ValueError(f"Invalid model registry entry for {alias!r}")

        model = spec.pop("model", alias)
        api_base = spec.pop("api_base", None)
        api_key_env = spec.pop("api_key_env", None)
        litellm_params = spec.pop("litellm_params", {}) or {}
        defaults = spec.pop("defaults", {}) or {}
        defaults.update(spec)
        registry[alias] = ModelSpec(
            name=str(alias),
            model=str(model),
            api_base=api_base,
            api_key_env=api_key_env,
            litellm_params=litellm_params,
            defaults=defaults,
        )
    return registry


def resolve_model_spec(
    model_name: str,
    registry: dict[str, ModelSpec] | None = None,
) -> ModelSpec:
    registry = registry or {}
    return registry.get(model_name) or ModelSpec(name=model_name, model=model_name)


def filter_by_split(data: list[dict[str, Any]], split: str = "full") -> list[dict[str, Any]]:
    if split == "full":
        return data
    if split == "renderable":
        return [item for item in data if item.get("rendering", False)]
    if split == "nonrenderable":
        return [item for item in data if not item.get("rendering", False)]
    raise ValueError("split must be one of: full, renderable, nonrenderable")


def normalize_format_name(value: str) -> str:
    normalized = re.sub(r"[\s_-]+", "", value.strip().lower())
    return FORMAT_NAMES.get(normalized, value.strip())


def format_label(value: str) -> str:
    normalized = re.sub(r"[\s_-]+", "", value.strip().lower())
    return FORMAT_LABELS.get(normalized, FORMAT_NAMES.get(normalized, value.strip()))


def parse_task_filter(task: str | None) -> tuple[str, str] | None:
    if task is None:
        return None
    task = task.strip()
    if not task or task.lower() in {"all", "full"}:
        return None

    arrow_normalized = re.sub(r"\s*(?:→|⇒|->|=>)\s*", "->", task)
    parts = arrow_normalized.split("->")
    if len(parts) == 1:
        parts = re.split(r"\s+to\s+", task, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) == 1:
        return "Text", normalize_format_name(parts[0])
    if len(parts) == 2:
        return normalize_format_name(parts[0]), normalize_format_name(parts[1])
    raise ValueError("task must look like 'svg', 'T->SVG', or 'Text to SVG'")


def task_filter_label(task: str | None) -> str:
    parsed = parse_task_filter(task)
    if parsed is None:
        return "full"
    source, target = parsed
    return f"{format_label(source)}->{format_label(target)}"


def filter_by_task(data: list[dict[str, Any]], task: str | None) -> list[dict[str, Any]]:
    parsed = parse_task_filter(task)
    if parsed is None:
        return data
    source, target = parsed

    def same_format(left: Any, right: str) -> bool:
        return normalize_format_name(str(left)) == normalize_format_name(right)

    return [
        item
        for item in data
        if same_format(item.get("input_type", ""), source)
        and same_format(item.get("output_type", ""), target)
    ]


def write_init_templates(
    *,
    config_path: str | Path = "structeval.yaml",
    models_path: str | Path = "models/models.yaml",
    force: bool = False,
) -> list[Path]:
    written: list[Path] = []
    targets = [
        (Path(config_path), CONFIG_TEMPLATE),
        (Path(models_path), MODELS_TEMPLATE),
    ]
    for path, content in targets:
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
