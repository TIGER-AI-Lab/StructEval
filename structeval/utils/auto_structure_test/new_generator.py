import json
import openai
import os
import re
from tqdm import tqdm

openai.api_key = ""

with open("task_description.txt", "r", encoding="utf-8") as f:
    task_description = f.read()

created_questions = {}
new_cases = []

def extract_case_from_function_output(arguments_str):
    """Extract JSON case from the function call's arguments."""
    try:
        return json.loads(arguments_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing function output JSON: {e}")
        return None

non_renderable_types = {"Text", "Python", "JSON", "XML", "SQL", "CSV", "YAML", "Pygame"}

json_folder = "sampleFiles"
json_files = [f for f in os.listdir(json_folder) if f.endswith('.json')]

# the function schema for structured output using GPT-4o's function calling interface
create_case_function = {
    "name": "create_case",
    "description": (
        "Generate a new test case for the LLM. The case must include a long and detailed 'query', "
        "a list of keywords in 'raw_output_metric', a list of 'VQA_questions', and a list of corresponding "
        "'VQA_answers'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A long and detailed query. Must be much longer than the sample query. "
                               "IMPORTANT: The query must begin with 'please output {output_type}:' "
                               "where {output_type} is the output type specified in the JSON."
            },
            "raw_output_metric": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords that must appear in the raw output. Include not only tokens from the raw code but also any essential English keywords."
            },
            "VQA_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Questions to evaluate the rendered output. These should focus solely on aspects visible in the rendered output and not on the underlying raw code. Do not include interactive component tests."
            },
            "VQA_answers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Expected answers corresponding to each VQA question (short word or phrase)."
            }
        },
        "required": ["query", "raw_output_metric", "VQA_questions", "VQA_answers"]
    }
}

for json_file in tqdm(json_files, desc="Processing files"):
    file_path = os.path.join(json_folder, json_file)
    with open(file_path, "r", encoding="utf-8") as f:
        item = json.load(f)
    
    #  whether visual rendering is needed based on output_type.
    need_rendering = False if item['output_type'] in non_renderable_types else True
    created_questions_str = "\n".join(created_questions.get(item['task_name'], []))
    
    orig_task_id = item.get("task_id", "000000")
    prefix = orig_task_id[:-2] 
    start_number = int(orig_task_id[-2:])  

    user_prompt = f"""
Task description:
{task_description}

The output json format should be:
{json.dumps(item, indent=4, ensure_ascii=False)}

Do we need visual rendering for the generated case?: {need_rendering}

Current existing questions:
{created_questions_str}

IMPORTANT: When designing the query, you must start with the output type as specified in the JSON above.
For example, if the JSON shows "output_type": "HTML", then your query should begin with "please output HTML:" followed by the query details.

Please read the Task description carefully, the output json format, and the Current existing questions carefully, then output a new case for me.
The new case will be used to test the LLM's ability for {item['task_name']}.
For each generated case, please keep these values the same as the input: task_name, query_example, task_id, input_type, output_type.
You need to create the LLM test case for: query, raw_output_metric, VQA_questions, VQA_answers.
Please keep the query very long, desirably much longer than the sample query so that it generates long output.


IMPORTANT: If the task involves converting input code to a different code type, your query must include the input code (i.e. the code specified in the input_type field). The code must be very long code, similar to the long query requirement.
IMPORTANT: You must call the function "create_case" and output the final JSON strictly.
IMPORTANT: The VQA questions should focus solely on aspects visible in the rendered output and must not refer to or test the underlying raw code.
Do not include VQA questions that test interactive components (e.g., "Does the button change color on hover?").

If visual rendering is not needed, then VQA_questions and VQA_answers should be empty.
The VQA questions and answers can be boolean or diverse categorical types, with answers being a short word or phrase.
I will use json.loads() to load your case.
"""

    for example_index in range(50):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": user_prompt}],
                functions=[create_case_function],
                function_call={"name": "create_case"},
                max_tokens=4095,
                temperature=1
            )
            message = response.choices[0].message
            if hasattr(message, "function_call") and message.function_call:
                arguments_str = message.function_call.arguments
                new_case = extract_case_from_function_output(arguments_str)
            else:
                print(f"No function call returned for file: {json_file}, example {example_index}")
                new_case = None

            if new_case:
                # enforce that the query begins with "please output {output_type}:"
                output_type = item.get("output_type", "").strip()
                desired_prefix = f"please output {output_type}:"
                if output_type and not new_case["query"].lower().startswith(desired_prefix.lower()):
                    new_case["query"] = f"{desired_prefix} " + new_case["query"]

                # update the task_id: keep the first four digits the same, increment last two by the example index.
                new_task_id = f"{prefix}{(start_number + example_index):02d}"
                new_case['task_id'] = new_task_id
                
                new_case['task_name'] = item['task_name']
                new_case['query_example'] = item['query_example']
                new_case['input_type'] = item['input_type']
                new_case['output_type'] = item['output_type']
                new_case['rendering'] = need_rendering
                new_cases.append(new_case)
                
                if new_case['task_name'] not in created_questions:
                    created_questions[new_case['task_name']] = []
                created_questions[new_case['task_name']].append(new_case['query'])
                print(new_case)
                print(f"Successfully generated case for file: {json_file}, example {example_index}")
            else:
                print(f"Failed to extract valid case from response for file: {json_file}, example {example_index}")
        except Exception as e:
            print(f"Error processing file {json_file}, example {example_index}: {str(e)}")

with open("generated_cases.json", "w", encoding="utf-8") as f:
    json.dump(new_cases, f, indent=4, ensure_ascii=False)

print(f"Generated {len(new_cases)} cases successfully")
