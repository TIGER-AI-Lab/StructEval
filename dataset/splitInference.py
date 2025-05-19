import json
import os
def split_by_rendering(input_file, renderable_file):
    # Load JSON list from file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Partition based on the "rendering" field
    renderable = [entry for entry in data if entry.get("output_type") == "SVG"]

    # Write to output files
    with open(renderable_file, 'w') as f:
        json.dump(renderable, f, indent=2)

    print(f"✅ Renderable: {len(renderable)} items saved to {renderable_file}")

#in each directory under experiment_results, run the split_by_rendering function on inference_output.json


split_by_rendering(
    input_file= "renderable.json",renderable_file= "SVG.json")