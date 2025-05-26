from dotenv import load_dotenv
import os
from llm_engines import LLMEngine
import torch

def run_inference(model_name: str, llm_engine: str, queries: list[str], **kwargs):
    """Using llm_engines to run inference."""
    
    llm = LLMEngine()

    llm.load_model(
        model_name=model_name, 
        engine=llm_engine,
        num_workers=1, 
        num_gpu_per_worker=1,
        use_cache=False,
        **kwargs
    )   

    responses = llm.batch_call_model(model_name, queries,num_proc=32, timeout=None,  disable_batch_api=True, temperature=1.0, max_tokens=None)
    return responses
    
    