import json

# === CONFIGURATION ===
INPUT_FILE = "conversion_generated_cases.json"
OUTPUT_FILE = "label_studio_ready.json"

# === LOAD GENERATED CASES ===
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    cases = json.load(f)

formatted_data = []

for case in cases:
    task_id = case["task_id"]

    # --- DATA FIELD ---
    data = {
        "query": case.get("query", ""),
        "feature_requirements": case.get("feature_requirements",""),
        "task_id": task_id,
        "task_name": case.get("task_name", ""),
        "input_type": case.get("input_type", ""),
        "output_type": case.get("output_type", ""),
        "query_example": case.get("query_example", ""),
        "VQA_questions": list(case.get("VQA", {}).keys()),
        "VQA_answers": list(case.get("VQA", {}).values()),
        "raw_output_metric": case.get("raw_output_metric", [])
    }

    # --- PREDICTIONS FIELD ---
    results = []

    # Query Output
    results.append({
        "id": f"{task_id}_q",
        "type": "textarea",
        "value": {
            "text": [case.get("query", "")]
        },
        "to_name": "query",
        "from_name": "queryAnswer"
    })

    # Raw Output Metric
    results.append({
        "id": f"{task_id}_r",
        "type": "textarea",
        "value": {
            "text": case.get("raw_output_metric", [])
        },
        "to_name": "raw_output_metric",
        "from_name": "raw_output_answer"
    })

    # Visual Rendering Flag
    if case.get("rendering", False):
        results.append({
            "id": f"{task_id}_v",
            "type": "choices",
            "value": {
                "choices": ["Use Visual Rendering"]
            },
            "to_name": "visual_rendering",
            "from_name": "shouldUseVisualRendering"
        })

    # VQA Questions
    vqa_qs = list(case.get("VQA", {}).keys())
    vqa_as = list(case.get("VQA", {}).values())

    if vqa_qs:
        results.append({
            "id": f"{task_id}_vq",
            "type": "textarea",
            "value": {
                "text": vqa_qs
            },
            "to_name": "VQA_questions",
            "from_name": "question"
        })

    if vqa_as:
        results.append({
            "id": f"{task_id}_va",
            "type": "textarea",
            "value": {
                "text": vqa_as
            },
            "to_name": "VQA_answers",
            "from_name": "desiredAnswer"
        })

    formatted_data.append({
        "data": data,
        "predictions": [{
            "result": results
        }]
    })

# === SAVE OUTPUT ===
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(formatted_data, f, indent=4, ensure_ascii=False)

print(f"✅ Saved {len(formatted_data)} items to {OUTPUT_FILE}")