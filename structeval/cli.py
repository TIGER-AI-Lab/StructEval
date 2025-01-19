import fire
import os

class StructEvalCLI:
    
    def __init__(self):
        pass
        
    
    def inference(
        self,
        input_path: str,
        output_path: str,
        **kwargs
    ):
        print(f"Training model with input_path: {input_path} and output_path: {output_path}")
        print(f"Additional arguments: {kwargs}")
    
    def eval(
        self,
        vlm_model_name: str,
        **kwargs
    ):
        print(f"Evaluating model with vlm_model_name: {vlm_model_name}")
        print(f"Additional arguments: {kwargs}")
        
        
        
def main():
    fire.Fire(StructEvalCLI)

if __name__ == "__main__":
    main()