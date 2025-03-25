import os
from datasets import load_dataset
from smart_open import open as smart_open
from itertools import islice
from collections import defaultdict
from huggingface_hub import login

# Login to Hugging Face
login("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")


# Define targets
file_targets = {
    "Markdown": 50,
    "HTML": 45,
    "React": 45,
    "Vue": 40,
    "Angular": 35,
    "CSV": 50,
    "JSON": 45,
    "XML": 40,
    "YAML": 25,
    "TOML": 5
}

# GitHub-safe permissive licenses
allowed_licenses = {"mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "isc"}

# Extensions for saving
file_extensions = {
    "Markdown": "md",
    "HTML": "html",
    "React": "js",
    "Vue": "vue",
    "Angular": "ts",
    "CSV": "csv",
    "JSON": "json",
    "XML": "xml",
    "YAML": "yaml",
    "TOML": "toml"
}

# Prepare folders
base_dir = "corpus"
os.makedirs(base_dir, exist_ok=True)
for code_type in file_targets:
    os.makedirs(os.path.join(base_dir, code_type), exist_ok=True)

# Load streaming dataset
print("📡 Connecting to The Stack v2 (streaming)...")
dataset = load_dataset("bigcode/the-stack-v2", split="train", streaming=True)

# Track collected files
collected = defaultdict(list)
sample_count = 0

# Helper to fetch from S3
def fetch_blob(blob_id, encoding="utf-8"):
    url = f"s3://softwareheritage/content/{blob_id}"
    try:
        with smart_open(url, "rb") as f:
            return f.read().decode(encoding, errors="ignore")
    except Exception as e:
        print(f"[Error] Failed to fetch {blob_id}: {e}")
        return None

# Start collecting
print("🚀 Starting collection...")
for sample in dataset:
    sample_count += 1
    if sample_count % 1000 == 0:
        print(f"🔍 Scanned {sample_count} samples...")

    lang = sample.get("language", "")
    license_type = sample.get("license_type", "")
    detected_licenses = [l.lower() for l in (sample.get("detected_licenses") or [])]
    blob_id = sample["blob_id"]
    encoding = sample.get("src_encoding", "utf-8")

    # Filter: must be permissive and have allowed license
    if license_type != "permissive":
        continue

    if not any(l in allowed_licenses for l in detected_licenses):
        continue

    # Match direct languages
    if lang in file_targets and len(collected[lang]) < file_targets[lang]:
        content = fetch_blob(blob_id, encoding)
        if content:
            collected[lang].append(content)
            print(f"✅ Collected {lang}: {len(collected[lang])}/{file_targets[lang]}")

    # Match React (JavaScript containing "react")
    if lang == "JavaScript" and len(collected["React"]) < file_targets["React"]:
        content = fetch_blob(blob_id, encoding)
        if content and "react" in content.lower():
            collected["React"].append(content)
            print(f"✅ Collected React: {len(collected['React'])}/{file_targets['React']}")

    # Match Angular (TypeScript containing "angular")
    if lang == "TypeScript" and len(collected["Angular"]) < file_targets["Angular"]:
        content = fetch_blob(blob_id, encoding)
        if content and "angular" in content.lower():
            collected["Angular"].append(content)
            print(f"✅ Collected Angular: {len(collected['Angular'])}/{file_targets['Angular']}")

    # Check if all targets are met
    if all(len(collected[k]) >= file_targets[k] for k in file_targets):
        print("\n🎉 All target files collected!")
        break

# Save files
print("\n💾 Saving files...")
for code_type, files in collected.items():
    ext = file_extensions[code_type]
    for i, content in enumerate(files):
        path = os.path.join(base_dir, code_type, f"{code_type.lower()}_{i}.{ext}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

print("✅ Done! Files saved to 'corpus/' folder.")