#!/bin/bash

# Array of model names (directories in experiment_results)
models=(
  "gemini-1.5-pro"
  "Qwen3-4B"
  "gpt-4o-mini"
  "gpt-4.1-mini"
  "Phi-3-mini-128k-instruct"
  "Llama-3.1-8B-Instruct"
  "Phi-4-mini-instruct"
  "Meta-Llama-3-8B-Instruct"
  "gemini-2.0-flash"
  "Qwen2.5-7B"
  "gpt-4o"
  "o1-mini"
)

echo "========================================================"
echo "           RENDER PROGRESS REPORT                       "
echo "========================================================"

# Check if processes are running
echo -e "\nCHECKING RUNNING PROCESSES:"
total_running=0
for model in "${models[@]}"; do
  pid=$(ps aux | grep "python -m cli render.*$model" | grep -v grep | awk '{print $2}')
  if [ -n "$pid" ]; then
    echo "✅ $model (PID: $pid) is running"
    ((total_running++))
  else
    echo "❌ $model is not running"
  fi
done

echo -e "\nTotal running processes: $total_running out of ${#models[@]}"

# Check image output
echo -e "\nCHECKING GENERATED IMAGES:"
for model in "${models[@]}"; do
  img_count=$(find "experiment_results/$model/rendered_images" -type f | wc -l)
  echo "$model: $img_count images generated"
done

# Check recent log activity
echo -e "\nRECENT LOG ACTIVITY:"
for model in "${models[@]}"; do
  echo -e "\n--- $model ---"
  if [ -f "render_logs/${model}_render.log" ]; then
    tail -5 "render_logs/${model}_render.log"
  else
    echo "No log file found"
  fi
done

echo -e "\n========================================================" 