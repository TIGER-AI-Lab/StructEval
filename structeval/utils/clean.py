import json

def clean_json_objects(input_file, output_file, mode="manual"):
    """
    Cleans JSON data based on the specified mode.
    
    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output JSON file.
        mode (str): "manual" for manual data format, "llm" for LLM-generated data format.
    """
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            json_list = json.load(f)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format.")
            return

    cleaned_data = []
    
    for obj in json_list:
        if mode == "manual":
            # Extract fields for manual data
            query = obj.get("queryAnswer", "")
            raw_output_metric = obj.get("raw_output_answer", {}).get("text", [])
            use_visual_rendering = obj.get("shouldUseVisualRendering", "") == "Use Visual Rendering"
            task_id = obj.get("task_id", "")

            # Extract VQA questions/answers
            VQAmetric = []
            if use_visual_rendering:
                questions = obj.get("question", {}).get("text", [])
                answers = obj.get("desiredAnswer", {}).get("text", [])
                VQAmetric = [{"question": q, "answer": a} for q, a in zip(questions, answers)]

        elif mode == "llm":
            # Extract fields for LLM-generated data
            query = obj.get("query", "")
            raw_output_metric = obj.get("raw_output_metric", [])
            use_visual_rendering = obj.get("rendering", False)  # Boolean field
            task_id = obj.get("task_id", "")

            # Extract VQA questions/answers
            VQAmetric = []
            questions = obj.get("VQA_questions", [])
            answers = obj.get("VQA_answers", [])
            VQAmetric = [{"question": q, "answer": a} for q, a in zip(questions, answers)]

        else:
            print("Error: Invalid mode. Choose 'manual' or 'llm'.")
            return

        # Create cleaned object
        cleaned_obj = {
            "query": query,
            "raw_output_metric": raw_output_metric,
            "useVisualRendering": use_visual_rendering,
            "VQAmetric": VQAmetric,
            "task_id": task_id
        }

        cleaned_data.append(cleaned_obj)

    # Write cleaned data to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2)

# Usage Example
# Choose between 'manual' or 'llm' mode
input_filename = "HTMLquery.json"
output_filename = "HTML_cleaned_output.json"

# Run for manual data
# clean_json_objects(input_filename, output_filename, mode="manual")

# Run for LLM-generated data
clean_json_objects(input_filename, output_filename, mode="llm")
