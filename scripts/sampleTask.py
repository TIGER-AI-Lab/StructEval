import openai
import json
import os


client = openai.OpenAI(api_key="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")  # set your key here


# Define type codes
TYPE_CODES = {
    "Text": "00",
    "Angular": "01",
    "CSV": "02",
    "Canvas": "03",
    "HTML": "04",
    "JSON": "05",
    "LaTeX": "06",
    "Markdown": "07",
    "Matplotlib": "08",
    "Mermaid": "09",
    "TOML": "10",
    "React": "11",
    "SVG": "12",
    "Tikz": "13",
    "Typst": "14",
    "Vega": "15",
    "Vue": "16",
    "XML": "17",
    "YAML": "18"
}

# Non-renderable types
non_renderable_types = {"JSON", "XML", "CSV", "YAML", "TOML"}

# Helper function to call OpenAI
def call_gpt_query_example(input_type, output_type):
    prompt = f"""
You are designing test queries for an LLM conversion task.

The input type is "{input_type}" and the output type is "{output_type}".

Generate a structured LLM query that starts with:
"Please output {output_type}:"

Use this format:

Please output {output_type}:

Task:
A one-sentence description of what the LLM should generate, based on the input/output types.

Feature Requirements:
- List 5 to 10 specific, **measurable** and **objective** requirements.
- Every requirement must describe something **visible** or **structural** in the output that can be tested or verified.
- Avoid vague terms like “responsive”, “user-friendly”, “visually appealing”, “well-styled”, etc.
- Instead, specify *what* should be shown, *where*, and *how many*.
- Do NOT include any external data required requirements (e.g., no <img>). The goal is that generation must be self-contained, runnable on its own.
- Do NOT include code or triple backticks in your output.

Examples of good requirements:
- “Include a centered title using an <h1> element with the text ‘Task List’”
- “Display exactly 3 list items, each containing a name and a date”
- “Use bold font for overdue items”

Output only the structured query text as described.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=1
    )
    return response.choices[0].message.content.strip()

# Main function to process tasks
def process_tasks(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tasks = [line.strip() for line in f if line.strip() and ("->" in line or "→" in line)]

    sample_cases = []

    for task in tasks:
        if "→" in task:
            input_type, output_type = task.split("→")
        else:
            input_type, output_type = task.split("->")
        input_type = input_type.strip()
        output_type = output_type.strip()

        input_code = TYPE_CODES.get(input_type, "XX")
        output_code = TYPE_CODES.get(output_type, "XX")
        task_id = f"{input_code}{output_code}00"
        task_name = f"{input_type} to {output_type}"

        print(f"🔍 Generating query for task: {task_name} (ID: {task_id})")

        try:
            query_example = call_gpt_query_example(input_type, output_type)
        except Exception as e:
            print(f"⚠️ Failed to generate query for {task_name}: {e}")
            continue

        sample_case = {
            "task_name": task_name,
            "task_id": task_id,
            "input_type": input_type,
            "output_type": output_type,
            "query_example": query_example,
            "query": "",
            "raw_output_metric": [],
            "VQA": {},
            "rendering": output_type not in non_renderable_types
        }

        sample_cases.append(sample_case)

    with open("sample_cases.json", "w", encoding="utf-8") as f:
        json.dump(sample_cases, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Generated {len(sample_cases)} sample cases in sample_cases.json")

# Run the function
process_tasks("tasks.txt")