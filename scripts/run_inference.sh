#!/bin/bash
export CUDA_VISIBLE_DEVICES=5
export HF_TOKEN=""
export OPENAI_API_KEY=""
export GEMINI_API_KEY=""

# Simple script to run inference for multiple models
INPUT_PATH="nonrenderable_new.json"
BASE_OUTPUT_DIR="experiment_results"

# List of models to run
#  "meta-llama/Meta-Llama-3-8B-Instruct"
# "Qwen/Qwen2.5-7B"
# "microsoft/Phi-3-mini-128k-instruct"
#  "microsoft/Phi-3-mini-128k-instruct"
#  "microsoft/Phi-4-mini-instruct"
#  "meta-llama/Llama-3.1-8B-Instruct"
# "Qwen/Qwen3-4B"
#"Qwen/Qwen3-4B-Base" problematic answers, because it's base model
#  "gpt-4o-mini"
#  "gpt-4.1-mini"
 # "o1-mini"
MODELS=(
  #"gemini-1.5-pro"
  #"microsoft/Phi-3-mini-128k-instruct"
  #"microsoft/Phi-4-mini-instruct"
  #"meta-llama/Meta-Llama-3-8B-Instruct"
  #"Qwen/Qwen2.5-7B"
  #"meta-llama/Llama-3.1-8B-Instruct"
  #"Qwen/Qwen3-4B"
  #gpt-4.1-mini
  "gpt-4o"
)

# Run each model in a separate process
for MODEL in "${MODELS[@]}"; do
  MODEL_ID=$(basename "$MODEL")
  OUTPUT_DIR="${BASE_OUTPUT_DIR}/${MODEL_ID}"
  
  echo "========================================"
  echo "Running inference for model: $MODEL"
  echo "Output directory: $OUTPUT_DIR"
  echo "========================================"
  
  # Create a simple Python script for this model only
  python -c "
from cli import StructEvalCLI
import os

os.makedirs('${OUTPUT_DIR}', exist_ok=True)
cli = StructEvalCLI()
cli.inference(
    llm_model_name='${MODEL}',
    llm_engine='vllm',
    input_path='${INPUT_PATH}',
    output_path='${OUTPUT_DIR}/inference_nonrenderable.json',
    **{
       'additional_args': ['--gpu-memory-utilization', '0.7', '--max-model-len', '4096', '--max-num-batched-tokens', '4096', '--max-num-seqs', '64', '--tensor-parallel-size', '1']
    }
)
"


  # Wait a moment to ensure resources are freed
  sleep 30
  
  echo "Completed model: $MODEL_ID"
  echo ""
done

echo "All models completed!"