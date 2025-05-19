import json

def split_by_rendering(input_file, renderable_file):
    # Load JSON list from file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Partition based on the "rendering" field
    renderable = [entry for entry in data if entry.get("rendering") is True]
    non_renderable = [entry for entry in data if entry.get("rendering") is False]

    # Write to output files
    with open(renderable_file, 'w') as f:
        json.dump(renderable, f, indent=2)


    print(f"✅ Renderable: {len(renderable)} items saved to {renderable_file}")

split_by_rendering(
    input_file="dataset/1615Dataset.json",
    renderable_file="renderableData.json"
)



