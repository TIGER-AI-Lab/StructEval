import json
from deepdiff import DeepDiff

def normalize_key(key: str) -> str:
    return key.lower().replace(" ", "")

def extract_keys(d):
    if isinstance(d, dict):
        return {normalize_key(k): extract_keys(v) for k, v in d.items()}
    return None  # Ignore values, only structure matters

def json_eval(data: list[dict], expected_keys: dict):

    output_data = []

    for item in data:
        task_id = item.get("task_id", "unknown")

        # Extract only the structure (keys) of the actual JSON, with normalized keys
        actual_keys = extract_keys(item)

        # Compare expected vs actual keys (ignoring case and spaces)
        diff = DeepDiff(extract_keys(expected_keys), actual_keys, ignore_order=True)

        # Identify missing and extra keys (normalize them)
        missing_keys = [normalize_key(key) for key in diff.get("dictionary_item_removed", [])]
        extra_keys = [normalize_key(key) for key in diff.get("dictionary_item_added", [])]

        # Score calculation
        total_expected_keys = len(set(extract_keys(expected_keys).keys())) 
        correct_keys = total_expected_keys - len(missing_keys)  

        score = correct_keys / total_expected_keys if total_expected_keys > 0 else 0.0

        item["JSON_Score"] = round(score, 2)
        item["Missing_Keys"] = missing_keys if missing_keys else []
        item["Extra_Keys"] = extra_keys if extra_keys else []

        output_data.append(item)

    return output_data


if __name__ == "__main__":
    expected_structure = {
        "person": {
            "name": None,
            "age": None
        },
        "favorites": {
            "colors": None,
            "numbers": None
        }
    }


    json_data = [
        {
            "task_id": "1",
            "Person ": { 
                " Name": "Alice", 
            },
            "Favorites": { 
                " Colors": ["red", "green", "blue"],
                "Numbers": [10, 20, 30]
            },
            "extra_field": "unexpected"
        },
        {
            "task_id": "2",
            "person": {"name": "Bob", "age": 25}, 
            "favorites": {"colors": ["blue"], "numbers": [5, 15]},
        }
    ]

    results = json_eval(json_data, expected_structure)

    with open("json_evaluation_results.json", "w") as f:
        json.dump(results, f, indent=4)

    for result in results:
        print(json.dumps(result, indent=4))