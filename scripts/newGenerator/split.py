import json
import os
from math import ceil

def split_json_file(input_path, k, output_prefix="convert_split"):
    # Load original data
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    chunk_size = ceil(total / k)

    print(f"Splitting {total} items into {k} files (≈{chunk_size} per file)")

    for i in range(k):
        chunk = data[i * chunk_size : (i + 1) * chunk_size]
        output_path = f"{output_prefix}_{i+1:02d}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=4, ensure_ascii=False)
        print(f"✅ Wrote {len(chunk)} items to {output_path}")

# Example usage
split_json_file("label_studio_ready.json", k=15)