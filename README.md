# StructEval

StructEval is a framework for evaluating language models on structured outputs, supporting rendering and evaluation of generated code.

## Installation

### Installation with conda

```bash
# Create and activate the conda environment from the environment.yml file
conda create -n structeval python=3.12
conda activate structeval

# Install all required packages(required)
pip install -r requirements.txt

# Separately install the llm-engines(required for inference)
pip install git+https://github.com/jdf-prog/LLM-Engines.git

# Install playwright browsers (required for rendering)
playwright install

# You could also install the package in development mode(optional)
pip install -e .
```

### System Dependencies(Optional to read)

The following system packages will be installed automatically through conda:
- `ghostscript` and `poppler`: Required for PDF processing
- `nodejs`: Required for Playwright
- `graphviz`: Required for visualization
- `imagemagick`: Required for image processing

If you encounter any issues with system dependencies, you can install them manually using your system's package manager:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ghostscript poppler-utils nodejs graphviz imagemagick

# CentOS/RHEL
sudo yum install ghostscript poppler nodejs graphviz ImageMagick

# macOS
brew install ghostscript poppler node graphviz imagemagick
```

## CLI Usage

StructEval provides a command-line interface for running inference, rendering, and evaluation.

### Basic Commands

```bash
# Run inference
python -m structeval.cli inference \
    --llm_model_name "model_name" \
    --llm_engine "engine_name" \
    --input_path "path/to/input.json" \
    --output_path "path/to/output.json"

# Render outputs
python -m structeval.cli render \
    --input_path "path/to/inference_output.json" \
    --img_output_path "path/to/rendered_images" \
    --non_renderable_output_dir "path/to/non_renderable_files"

# Run evaluation
python -m structeval.cli evaluate \
    --vlm_model_name "model_name" \
    --vlm_engine "engine_name" \
    --input_path "path/to/inference_output.json" \
    --output_path "path/to/evaluation_output.json" \
    --img_path "path/to/rendered_images" \
    --non_renderable_output_dir "path/to/non_renderable_files"
```

### Command Parameters

#### Inference
- `--llm_model_name`: Name of the language model (e.g., "meta-llama/Llama-3.1-8B-Instruct", "gpt-4.1-mini")
- `--llm_engine`: Engine for running inference (e.g., "vllm", "openai")
- `--input_path`: Path to the input dataset JSON file
- `--output_path`: Path to save inference results

#### Render
- `--input_path`: Path to the inference output JSON
- `--img_output_path`: Directory to save rendered images
- `--non_renderable_output_dir`: Directory to save non-renderable outputs

#### Evaluate
- `--vlm_model_name`: Name of the vision language model for evaluation (e.g., "gpt-4.1-mini")
- `--vlm_engine`: Engine for evaluation (e.g., "openai")
- `--input_path`: Path to the inference output JSON
- `--output_path`: Path to save evaluation results
- `--img_path`: Path to the directory containing rendered images
- `--non_renderable_output_dir`: Directory containing non-renderable outputs

## Helper Scripts

The repository includes helper scripts for running full experiments:

### run_inference.py
Run inference across multiple models:

```bash
python -m structeval.run_inference
```

### run_render.py
Render outputs from inference results:

```bash
python -m structeval.run_render
```

### run_evaluation.py
Evaluate rendered outputs:

```bash
python -m structeval.run_evaluation
```

These scripts can be configured by editing the model lists and file paths within them.

## Input Format

The input JSON should be an array of task objects with the following structure:

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
    "raw_output_metric": [
      "novel.title",
      "novel.author.name",
      "novel.characters[0].name"
    ],
    "rendering": false
  }
]
```

### Input Fields:
- `task_id`: Unique identifier for the task
- `query`: The prompt sent to the model
- `task_name`: Name of the task (e.g., "Text to JSON", "Text to Angular")
- `input_type`: Type of input (e.g., "Text")
- `output_type`: Expected output format (e.g., "JSON", "Angular")
- `VQA`: Array of visual question-answer pairs for evaluating renderable outputs
- `raw_output_metric`: Keys or elements to check in the output
- `rendering`: Boolean indicating if the output should be rendered visually

## Output Format

### Inference Output
The inference process adds a `generation` field to each task in the input:

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
    "raw_output_metric": [...],
    "rendering": false,
    "generation": "```json\n{\n  \"novel\": {\n    \"title\": \"The Obsidian Labyrinth\",\n    \"author\": {\n      \"name\": \"Anya Petrova\",\n      \"birth_year\": 1978\n    },\n    ...\n  }\n}\n```"
  }
]
```

### Evaluation Output
The evaluation result contains additional scoring fields:

```json
[
  {
    "task_id": "000500",
    "query": "Please output JSON code:\n\nTask:\n...",
    "feature_requirements": "",
    "task_name": "Text to JSON",
    "input_type": "Text",
    "output_type": "JSON",
    "VQA": [],
    "raw_output_metric": [...],
    "rendering": false,
    "generation": "...",
    "output_file": "experiment_results/model-name/non_renderable_files/000500.json",
    "render_score": 1,
    "VQA_score": null,
    "key_validation_score": 1.0,
    "final_eval_score": 1.0
  }
]
```

### Evaluation Fields:
- `output_file`: Path to the rendered output or extracted JSON file
- `render_score`: Score indicating if the output was rendered successfully (0 or 1)
- `VQA_score`: Score from visual question-answering evaluation (for renderable outputs)
- `key_validation_score`: Score from validating expected keys in JSON output (for non-renderable outputs)
- `raw_output_eval`: Array of boolean values indicating whether each raw output metric was satisfied
- `raw_output_score`: Score from the raw output evaluation
- `final_eval_score`: Overall evaluation score between 0 and 1