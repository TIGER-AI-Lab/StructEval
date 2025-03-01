export CUDA_VISIBLE_DEVICES=4

export HF_TOKEN="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"

python cli.py evaluate \
    --vlm_model_name "microsoft/Phi-3.5-vision-instruct" \
    --vlm_engine "vllm" \
    --input_path "HTMLoutputInference.json" \
    --output_path "HTMLevaluations.json" \
    --img_path "screenshots/"