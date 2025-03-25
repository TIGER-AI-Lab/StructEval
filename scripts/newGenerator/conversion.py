import json
import openai
import os
from tqdm import tqdm


# === Type and conversion codes ===
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

# === CONFIG ===
INPUT_FILE = "conversion_tasks.txt"
OUTPUT_FILE = "conversion_generated_cases.json"
OPENAI_MODEL = "o3-mini"

non_renderable_types = {"JSON", "XML", "CSV", "YAML", "TOML"}

# === MODEL SETUP ===
client = openai.OpenAI(api_key="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")

def call_gpt(prompt, max_tokens=2048):
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_tokens,
        temperature=1
    )
    return response.choices[0].message.content.strip()

# === STEP 1: Parse conversion_tasks.txt ===
def load_conversion_tasks():
    tasks = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "→" in line:
                parts = line.strip().split("→")
            elif "->" in line:
                parts = line.strip().split("->")
            else:
                continue
            input_type = parts[0].strip()
            output_part = parts[1].strip().split(":")
            output_type = output_part[0].strip()
            num = int(output_part[1].strip())
            tasks.append((input_type, output_type, num))
    return tasks

# === STEP 2: Generate input code ===
def generate_input_code(input_type):
    is_non_renderable = input_type.upper() in non_renderable_types

    if is_non_renderable:
        prompt = f"""
Pick a random setting. You are asked to generate a code snippet written in {input_type}.

This code will be used in a conversion task where the input and output are both structured data formats.

Goals:
- Focus on **data organization**, **key-value structure**, or **nesting**
- Use realistic, well-named keys and values
- Include at least 3–5 top-level fields, with some lists or arrays

Constraints:
- The code must be valid, parseable {input_type} syntax
- Do NOT use external assets, image links, or placeholder references
- Avoid unnecessary repetition, but ensure variety in field types
- Do NOT include explanation — just the code

IMPORTANT:
Wrap the code inside <code> and </code> tags like this:
<code>
<your_code_here>
</code>
"""
    else:
        prompt = f"""
You are asked to generate a long and realistic code snippet written in {input_type}.

This code will be used for a visual conversion task that tests structural layout, visual hierarchy, and visible content.

Goals:
- Focus on **visible structure**, **layout**, and **formatted content**
- Include things like headings, sections, lists, labeled values, etc.
- Be long or deeply structured: aim for between 30 to 150 lines

Constraints:
- Do NOT use any images, external URLs, icons, scripts, links, or stylesheets
- Avoid animations, hover events, or click interactivity, only renderable to one page
- Must be valid {input_type} and standalone

IMPORTANT:
Wrap the code inside <code> and </code> tags like this:
<code>
<your_code_here>
</code>
"""
    return call_gpt(prompt, max_tokens=2048)

# === STEP 3: Construct query ===
def build_query(output_type, input_type, input_code):
    return f"""Please output {output_type}:

Task:
Convert the following {input_type} code to {output_type} code.

{input_code}"""

# === STEP 4: Generate Feature Requirements ===
def generate_feature_requirements(query, output_type):
    non_renderable = {"JSON", "XML", "CSV", "YAML", "TOML"}

    if output_type in non_renderable:
        focus_note = "The format is structured data (like dictionaries, tables, or trees), so your requirements should reflect the structure, key layout."
    else:
        focus_note = "The format will be visually rendered (e.g., HTML, LaTeX, Canvas), so your requirements should reflect what would be visible in a screenshot."

    prompt = f"""
You are given a code conversion query.

Your task is to extract 5–10 objective, measurable feature requirements that describe what the converted output must contain, based on the input code.

Query that contains the input code:
{query}

Output in the following structure, explained below:

Feature Requirements:
- {focus_note}
- Describe elements like headings, keys, labels, values, text groups, lists, or sections.
- Do NOT mention syntax (e.g., indentation, braces).
- Do NOT include interactivity, style, or external links.
- Ensure every requirement is verifiable from the output — either by parsing or rendering.

Return as a bullet-point list and nothing else. Do not output nothing.
"""
    return call_gpt(prompt)

# === STEP 5: Generate Raw Output Metric ===
def generate_raw_output_metric(feature_requirements, output_type):

    non_renderable = {"JSON", "XML", "CSV", "YAML", "TOML"}
    if output_type in non_renderable:
        if output_type == "JSON":
            structure_hint = "The output will be a JSON object with possible nested keys and arrays."
        elif output_type == "YAML":
            structure_hint = "The output will follow YAML format with nested maps and lists."
        elif output_type == "TOML":
            structure_hint = "The output will follow TOML format using key-value pairs and nested tables."
        elif output_type == "XML":
            structure_hint = "The output will be XML using nested tags. Paths should reflect the tag hierarchy."
        elif output_type == "CSV":
            structure_hint = "The output will be a CSV table. Use 'rows[n][column]' to refer to values, or 'rows[*][column]' to refer to a whole column."

        prompt = f"""
    Your task is to first read **feature requirements below** and then extract a list of key paths that must exist in some raw output generated by some other LLMs.
    You are NOT generating output — you are only listing keys to check for during evaluation.

    You are listing keys for: {output_type}, {structure_hint}

    Use the feature requirements below to infer what must exist in the output, do not invent new stuff that is not in the feature requirement.

    Feature Requirements:
    {feature_requirements}

    Instructions:
    - Use appropriate key path formatting based on {output_type}
    - For nested structures, use bracketed notation (e.g., user[profile][email])
    - For CSV, refer to rows and columns (e.g., rows[0][email])
    - Only include keys clearly implied by the feature requirements — do not invent

    Return only a JSON array of strings. Do not return explanations or empty output.

    """
    else:
        prompt = f"""
Your task is first see the **feature requirements below** and then extracting exact keywords or phrases that must appear in the raw output produced by other LLM — based only on the feature requirements. 
You are NOT generating output — you are only listing key words to check for during evaluation.

Output type: {output_type} (visually renderable), do not invent new stuff that is not in the feature requirement

Feature Requirements:
{feature_requirements}

Guidelines:
- Do NOT extract phrases from the feature requirements itself.
- Instead, deduce what the LLM should generate based on the query itself ONLY and list specific strings or tokens that must be present in that output.
- These could include heading text, labels, static strings, or keywords visible in the raw code.
- Do NOT include instructions, formatting terms (like “centered title”), or general phrases, these will not appear in the raw output.
- ONLY include tokens that are expected to appear verbatim in the raw output based on the feature requirements ONLY.

Return only a JSON array of strings. Do not return explanations or empty output.

"""
    try:
        response = call_gpt(prompt)
        #print(response)
        return json.loads(response)
    except:
        return []

# === STEP 6: Generate VQA ===
def generate_vqa(feature_requirements, output_type):
    non_renderable = {"JSON", "XML", "CSV", "YAML", "TOML"}

    if output_type in non_renderable:
        return {}  # No VQA for non-renderable outputs

    prompt = f"""
You are given a list of feature requirements:

Feature Requirements:
{feature_requirements}

Your task is to generate a set of 5–10 visual question-answer (VQA) pairs based on the **Feature Requirements**.

- Do NOT Ask about code syntax, tags, commands, or formatting instructions (e.g., no mention of \\begin{{equation}}, \\frac{{}}, <div>, etc.)
- Do NOT Ask about interactive behavior (hover, click, tabs, animations)
- Do NOT Ask about content from other pages or external components

DO:
- Ask about things that would be visible in a screenshot of the rendered output
- Include questions about text content, layout, list counts, bold/italic styling, visible structure, labels, etc.
- Ensure every question is objective and easily answerable by visual inspection
- Extract the visual question/answer pairs from the Feature Requirements only, do not invent something that is not there. 

Example:
{{
  "What is the page title at the top?": "Travel Getaway",
  "How many bullet points are shown in the left column?": "4",
  "Is the first word in each step bolded?": "Yes"
}}

You must return a JSON object with:
- Keys = visual questions
- Values = short expected answers

Do not produce empty output. 
"""
    try:
        response = call_gpt(prompt)
        vqa = json.loads(response)
        return {k.strip(): v.strip() for k, v in vqa.items() if k and v}
    except:
        return {}

# === MAIN SCRIPT ===
tasks = load_conversion_tasks()
all_cases = []

for input_type, output_type, count in tqdm(tasks, desc="Processing conversion tasks"):

    input_id = TYPE_CODES.get(input_type, "XX")
    output_id = TYPE_CODES.get(output_type, "XX")

    for i in range(count):
        try:
            input_code = generate_input_code(input_type)
            query = build_query(output_type, input_type, input_code)
            feature_reqs = generate_feature_requirements(query, output_type)

            #(feature_reqs)
            raw_metric = generate_raw_output_metric(feature_reqs, output_type)
            vqa = generate_vqa(feature_reqs, output_type)

            task_id = f"{input_id}{output_id}{i:02d}"

            case = {
                "task_id": task_id,
                "task_name": f"Convert {input_type} to {output_type}",
                "input_type": input_type,
                "output_type": output_type,
                "query": query,
                "raw_output_metric": raw_metric,
                "VQA": vqa,
                "rendering": output_type not in {"JSON", "XML", "CSV", "YAML", "TOML"},
                "feature requirements": feature_reqs
            }
            all_cases.append(case)
        except Exception as e:
            print(f"❌ Failed {input_type} → {output_type}, example {i}: {e}")

# === SAVE OUTPUT ===
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_cases, f, indent=4, ensure_ascii=False)

print(f"\nFinished! Saved {len(all_cases)} conversion cases to {OUTPUT_FILE}")