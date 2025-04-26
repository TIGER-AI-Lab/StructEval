import json
import yaml
import csv
import io
import logging
from playwright.async_api import async_playwright

# Copy of TYPE_CODES from main.py to avoid circular imports
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

async def start_browser(headless=True):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    return browser, context, page, playwright

def score_non_renderable(task):
    task_id = task.get("task_id", "unknown")
    type_code = task.get("task_id", "000000")[2:4]
    output_type = task.get("output_type", "").lower()
    
    # If output_type is not specified, try to determine it from the type_code
    if not output_type:
        for k, v in TYPE_CODES.items():
            if v == type_code:
                output_type = k.lower()
                break
    
    generation = task.get("generation", "")
    
    # Remove code tags if present
    if "<code>" in generation and "</code>" in generation:
        generation = generation.split("<code>")[1].split("</code>")[0]
    
    score = 0.0

    try:
        if output_type == "json":
            json.loads(generation)
            score = 1.0

        elif output_type == "yaml":
            yaml.safe_load(generation)
            score = 1.0

        elif output_type == "csv":
            rows = list(csv.reader(io.StringIO(generation.strip())))
            score = 1.0 if rows and len(rows) >= 2 else 0.0
            
        elif output_type == "toml":
            # Import toml only when needed
            import toml
            toml.loads(generation)
            score = 1.0
            
        elif output_type == "xml":
            # Import xml parser only when needed
            import xml.etree.ElementTree as ET
            ET.fromstring(generation)
            score = 1.0
            
        else:
            # For other non-renderable types, we can't validate the format
            # but we can still check if there's content
            score = 1.0 if generation.strip() else 0.0

    except Exception as e:
        logging.warning(f"[{task_id}] Failed to parse {output_type}: {e}")

    task["render_score"] = score
    return task