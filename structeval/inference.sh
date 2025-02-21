export CUDA_VISIBLE_DEVICES=2

export HF_TOKEN="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"

python cli.py inference \
    --llm_model_name "meta-llama/Meta-Llama-3-8B-Instruct" \
    --llm_engine "sglang" \
    --input_path "HTML_cleaned_output.json" \
    --output_path "HTMLoutputInference.json"