import json

def split_by_rendering(input_file, renderable_file):
    # Load JSON list from file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Partition based on the "rendering" field
    renderable = [entry for entry in data if entry.get("output_type") == "Angular"]

    # Write to output files
    with open(renderable_file, 'w') as f:
        json.dump(renderable, f, indent=2)


split_by_rendering(
    input_file="dataset/renderable.json",
    renderable_file="angular.json"
)
