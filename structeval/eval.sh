export CUDA_VISIBLE_DEVICES=2

export HF_TOKEN="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"

python cli.py evaluate \
    --vlm_model_name "meta-llama/Meta-Llama-3-8B-Instruct" \
    --input_path "HTMLoutputInference.json" \
    --img_output_path "screenshots/"