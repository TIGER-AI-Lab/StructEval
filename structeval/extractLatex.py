import os
import json

def extract_latex_tikz_objects(root_dir):

    for model_name in os.listdir(root_dir):
        model_dir = os.path.join(root_dir, model_name)
        if os.path.isdir(model_dir):
            file_path = os.path.join(model_dir, 'inference_output.json')
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            filtered = [obj for obj in data if obj.get("output_type") in ("Angular")]
                            if filtered:
                                output_path = os.path.join(model_dir, 'inference_latex.json')
                                with open(output_path, 'w', encoding='utf-8') as out_f:
                                    json.dump(filtered, out_f, indent=2)
                        else:
                            print(f"Warning: Expected a list in {file_path}, but got {type(data)}")
                    except json.JSONDecodeError:
                        print(f"Invalid JSON in file: {file_path}")

# Example usage
results = extract_latex_tikz_objects("experiment_results")