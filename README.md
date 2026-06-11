# StructEval

StructEval evaluates language models on structured output generation and
conversion tasks. This refactor is API-first: inference and VQA judging go
through LiteLLM, local GPU inference backends are not required, and the CLI is
designed around one main workflow.

Supported model providers include OpenAI, OpenRouter, DeepSeek, Anthropic/Claude,
Azure OpenAI, and other OpenAI-compatible endpoints supported by LiteLLM.

## What This Repo Does

- Runs model inference over the StructEval dataset.
- Renders visual/code outputs such as HTML, React, Vue, Angular, SVG, Mermaid,
  Matplotlib, LaTeX/TikZ, Typst, Vega, Markdown, and Canvas.
- Extracts and validates non-renderable structured outputs such as JSON, YAML,
  CSV, TOML, and XML.
- Evaluates rendered outputs with a vision judge model.
- Writes reproducible `inference.json`, `evaluation.json`, `summary.json`, and
  `run.json` artifacts.

The public CLI is:

```bash
structeval init
structeval run
structeval reproduce
structeval evaluate
structeval summary
structeval doctor
```

Advanced debug commands `infer` and `render` remain available, but are hidden
from the primary help output.

## Install

Use `uv` for local development:

```bash
uv sync --extra render --extra test
uv run playwright install chromium
```

For API-only use without local rendering:

```bash
uv sync
```

Check the environment:

```bash
uv run structeval doctor --render
```

Optional system dependencies are needed only for the corresponding renderers:

| Dependency | Used By |
| --- | --- |
| Node.js and npm | Angular, Vue, browser render helpers |
| Playwright Chromium | HTML, SVG, React, Vue, Angular, Mermaid, Vega, Canvas |
| TeX or Tectonic, plus poppler | LaTeX and TikZ |
| Typst and ImageMagick | Typst |

Rendering executes model-generated code locally. Run evaluations in an isolated
environment if the model output is untrusted.

## Quick Start

Create config and model-registry templates:

```bash
uv run structeval init
```

This writes:

```text
structeval.yaml
models/models.yaml
```

Run a two-task smoke test:

```bash
uv run structeval run \
  --dataset dataset/StructEval_dataset.json \
  --model openrouter-gpt-4.1-mini \
  --judge-model openrouter-gpt-4.1-mini \
  --limit 2
```

Run the full benchmark from config:

```bash
uv run structeval run --config structeval.yaml
```

Run only one benchmark side:

```bash
uv run structeval run \
  --dataset dataset/StructEval_dataset.json \
  --model openrouter-gpt-4.1-mini \
  --judge-model openrouter-gpt-4.1-mini \
  --split renderable

uv run structeval run \
  --dataset dataset/StructEval_dataset.json \
  --model openrouter-gpt-4.1-mini \
  --judge-model openrouter-gpt-4.1-mini \
  --split nonrenderable
```

`--split` supports `full`, `renderable`, and `nonrenderable`. `--limit` is
applied after filtering.

## API Keys And Models

StructEval uses LiteLLM model strings. You can pass them directly:

```bash
uv run structeval run \
  --dataset dataset/StructEval_dataset.json \
  --model openai/gpt-4.1-mini \
  --judge-model openai/gpt-4.1-mini
```

Or use aliases from `models/models.yaml`:

```yaml
models:
  gpt-4.1-mini:
    model: openai/gpt-4.1-mini
    api_key_env: OPENAI_API_KEY

  openrouter-gpt-4.1-mini:
    model: openrouter/openai/gpt-4.1-mini
    api_key_env: OPENROUTER_API_KEY

  deepseek-v4-pro:
    model: deepseek/deepseek-v4-pro
    api_key_env: DEEPSEEK_API_KEY

  claude-sonnet-4:
    model: anthropic/claude-sonnet-4
    api_key_env: ANTHROPIC_API_KEY
```

Common environment variables:

```bash
export OPENAI_API_KEY=...
export OPENROUTER_API_KEY=...
export DEEPSEEK_API_KEY=...
export ANTHROPIC_API_KEY=...
```

For OpenRouter, `OPEN_ROUTER_API_KEY` is also accepted as a fallback for
`OPENROUTER_API_KEY`.

Provider-specific LiteLLM parameters can be placed in the registry:

```yaml
models:
  my-openai-compatible-model:
    model: openai/my-model
    api_base: http://localhost:8000/v1
    api_key_env: MY_API_KEY
    litellm_params:
      extra_headers:
        X-Example: value
```

CLI flags override `structeval.yaml`, and `structeval.yaml` overrides model
registry defaults.

## Config

Minimal config:

```yaml
dataset: dataset/StructEval_dataset.json
output_dir: runs/gpt-4.1-mini
model: openrouter-gpt-4.1-mini
judge_model: openrouter-gpt-4.1-mini
split: full
concurrency: 8
render_concurrency: 4
temperature: 0.0
judge_temperature: 0.0
max_tokens: null
timeout: null
max_retries: 2
```

Optional advanced config:

```yaml
models_path: models/models.yaml
api_base: null
api_key_env: null
judge_api_base: null
judge_api_key_env: null
litellm_params: {}
judge_litellm_params: {}
```

Run it:

```bash
uv run structeval run --config structeval.yaml
```

If `--output-dir` is omitted, `run` writes to:

```text
runs/<safe-model-name>/<utc-timestamp>/
```

If `output_dir` is set in config, that exact directory is used.

## Reproduce A Paper Subtask

`reproduce` is the convenient path for paper-style task subsets. It defaults to:

- dataset: `dataset/StructEval_dataset.json`
- API concurrency: `32`
- render concurrency: `4`
- generation temperature: `0.0`
- judge temperature: `0.0`
- max tokens: unlimited

Examples:

```bash
uv run structeval reproduce \
  --model openrouter-gpt-4.1-mini \
  --judge-model openrouter-gpt-4.1-mini \
  --task svg

uv run structeval reproduce \
  --model openrouter-gpt-4.1-mini \
  --judge-model openrouter-gpt-4.1-mini \
  --task "JSON->YAML"

uv run structeval reproduce \
  --model openrouter-gpt-4.1-mini \
  --judge-model openrouter-gpt-4.1-mini \
  --task "HTML->Vue" \
  --render-concurrency 16
```

Task aliases:

- `svg` means `Text->SVG`.
- `T->SVG`, `Text->SVG`, and `Text to SVG` are equivalent.
- `JSON->YAML` and `JSON to YAML` are equivalent.
- Omit `--task` to run the full dataset.

Exact API generations are not guaranteed to match the paper or another provider.
For deterministic score reproduction, reuse the same saved `generation` values
and rerun render/evaluate.

## Outputs

Each run directory contains:

```text
inference.json
images/
non_renderable_format_files/
evaluation.json
summary.json
run.json
```

Important fields kept for compatibility:

- `generation`
- `parsed_code`
- `render_score`
- `raw_output_score`
- `VQA_score`
- `key_validation_score`
- `final_eval_score`

`run.json` stores metadata such as model, judge model, dataset, split, task,
paths, and concurrency settings without modifying per-sample structures.

## Rescore Existing Generations

If you already have `inference.json`, rerender and evaluate it:

```bash
uv run structeval render \
  --input-path runs/my-run/inference.json \
  --img-output-path runs/my-run/images \
  --non-renderable-output-dir runs/my-run/non_renderable_format_files \
  --render-concurrency 16

uv run structeval evaluate \
  --input-path runs/my-run/inference.json \
  --output-path runs/my-run/evaluation.json \
  --img-path runs/my-run/images \
  --non-renderable-output-dir runs/my-run/non_renderable_format_files \
  --judge-model openrouter-gpt-4.1-mini \
  --concurrency 32

uv run structeval summary \
  --input-path runs/my-run/evaluation.json \
  --output-path runs/my-run/summary.json
```

`render` is hidden from the primary CLI help because normal users should use
`run` or `reproduce`, but it is intentionally available for debugging and
rescoring workflows.

## Scoring

Renderable tasks:

```text
final_eval_score = 0.2 * render_score + 0.1 * raw_output_score + 0.7 * VQA_score
```

Non-renderable tasks:

```text
final_eval_score = 0.2 * render_score + 0.8 * key_validation_score
```

`summary.json` reports:

- all-task average
- renderable average
- non-renderable average
- average by `output_type`

## Rendering Notes

`--concurrency` controls API calls. `--render-concurrency` controls local render
jobs. Render concurrency is additionally capped per output type to avoid unstable
local failures:

- Angular, Vue, and Typst are conservative.
- HTML, SVG, Markdown, Canvas, Matplotlib, and non-renderable extraction can run
  with more parallelism.
- LaTeX/TikZ rendering depends heavily on the local TeX installation.

Recent renderer fixes make React, Vue, Angular, and TikZ execution stricter and
less likely to produce blank-page false positives. That improves correctness, but
it also means exact StructEval-V scores can differ from older local render
pipelines. To compare scores, keep the renderer version and system dependencies
fixed.

## Dataset Format

The dataset is a JSON array of tasks:

```json
[
  {
    "task_id": "000500",
    "query": "Please output JSON code:\n\nTask:\n...",
    "feature_requirements": "",
    "task_name": "Text to JSON",
    "input_type": "Text",
    "output_type": "JSON",
    "query_example": "",
    "VQA": [],
    "raw_output_metric": ["novel.title", "novel.author.name"],
    "rendering": false
  }
]
```

Renderable tasks include VQA questions. Non-renderable tasks include
`raw_output_metric` key paths used for structural validation.

## Development

Run tests:

```bash
uv run --extra test pytest -q
```

Run CLI checks:

```bash
uv run structeval --help
uv run structeval run --help
uv run python -m structeval.cli --help
```

Package import should work outside the repository root after installation:

```bash
uv run python -c "import structeval; print(structeval.__version__)"
```

## Citation

```bibtex
@misc{yang2025structeval,
  title={StructEval: Benchmarking LLMs' Capabilities to Generate Structural Outputs},
  author={Jialin Yang and Dongfu Jiang and Lipeng He and Sherman Siu and Yuxuan Zhang and Disen Liao and Zhuofeng Li and Huaye Zeng and Yiming Jia and Haozhe Wang and Benjamin Schneider and Chi Ruan and Wentao Ma and Zhiheng Lyu and Yifei Wang and Yi Lu and Quy Duc Do and Ziyan Jiang and Ping Nie and Wenhu Chen},
  year={2025},
  eprint={2505.20139},
  archivePrefix={arXiv},
  primaryClass={cs.SE},
  doi={10.48550/arXiv.2505.20139}
}
```
