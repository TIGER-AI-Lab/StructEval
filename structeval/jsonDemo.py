import json
from deepdiff import DeepDiff

# Define the expected keys (no value checking, just structure)
expected_keys = {
    "person": {
        "name": None,
        "age": None  # <-- This is missing in sample.json
    },
    "favorites": {
        "colors": None,
        "numbers": None
    }
}

def extract_keys(d):
    """ Recursively extract only keys from a dictionary, replacing values with None. """
    if isinstance(d, dict):
        return {k: extract_keys(v) for k, v in d.items()}
    return None  # Ignore actual values

def check_json_file(json_file, expected_structure):
    """ Loads a JSON file and checks if it has all required keys. """
    with open(json_file, "r") as f:
        data = json.load(f)

    # Compare expected vs actual keys
    diff = DeepDiff(extract_keys(expected_structure), extract_keys(data), ignore_order=True)

    # Show missing keys
    if 'dictionary_item_removed' in diff:
        print("Missing keys detected:")
        for key in diff['dictionary_item_removed']:
            print(f" - {key}")
    else:
        print("All required keys are present!")

# Run the function on our sample file
check_json_file("sample.json", expected_keys)