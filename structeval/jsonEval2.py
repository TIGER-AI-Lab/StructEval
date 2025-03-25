import json

def normalize_key(key: str) -> str:
    """ Normalize keys by converting to lowercase and removing spaces. """
    return key.lower().replace(" ", "")

def check_keys(data, keys_to_check):
    missing_keys = []

    for key_path in keys_to_check:
        normalized_path = key_path.replace("[", ".").replace("]", "").replace("'", "")
        key_parts = [normalize_key(part) for part in normalized_path.split(".")[1:]]  # Ignore "data"
        
        current = data
        for part in key_parts:
            if isinstance(current, dict) and any(normalize_key(k) == part for k in current.keys()):
                # Find the actual key in case it had different capitalization or spaces
                actual_key = next(k for k in current.keys() if normalize_key(k) == part)
                current = current[actual_key]
            else:
                missing_keys.append(key_path)
                break  # Stop checking deeper levels

    return missing_keys

if __name__ == "__main__":
    json_data = {
        "Person": {  
            " Name": "Alice"  
        },
        "Favorites": {
            " Colors": ["red", "green", "blue"], 
            "Numbers": [10, 20, 30]
        },
        "extra_field": "unexpected"
    }

    # List of keys to check (LLM can generate this)
    keys_to_check = [
        "data['person']['name']",
        "data['person']['age']",  
        "data['favorites']['colors']",
        "data['favorites']['numbers']"
    ]

    missing_keys = check_keys(json_data, keys_to_check)

    if missing_keys:
        print(" Missing keys detected:")
        for key in missing_keys:
            print(f" - {key}")
    else:
        print("All required keys are present!")