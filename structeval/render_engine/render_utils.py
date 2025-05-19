import json
import yaml
import csv
import io
import logging
import codecs
import re
import os
from playwright.async_api import async_playwright
import xmltodict
import toml


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
    "YAML": "18",
}


async def start_browser(headless=True):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    return browser, context, page, playwright


async def close_browser(browser, context, page, playwright):
    """
    Safely close browser instances to prevent resource leaks.
    """
    try:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
    except Exception as e:
        logging.error(f"Error closing browser: {e}")


def determine_output_type(task_id):
    """
    Determine output type from task_id.

    Args:
        task_id: Task identifier

    Returns:
        Output format type (json, yaml, csv, toml, xml)
    """
    if len(task_id) >= 4:
        type_code = task_id[2:4]
        # Return the lowercase type name based on TYPE_CODES
        for key, value in TYPE_CODES.items():
            if value == type_code:
                return key.lower()
    return ""


def extract_renderable_code(text: str, output_type: str = "") -> str:
    """
    Return whatever looks like the code payload.

    Priority:
      1. Anything between <code> … </code>
      2. Anything in a ```fenced``` block (any header, or matching output_type)
      3. Otherwise, the whole text (trimmed)

    Works even if closing tags / fences are missing.
    """
    tag_or_fence = rf"""
    (?:                             # 1) <code> … </code>
        <code>[ \t]*\n              # opener (+ newline it ends with)
        (?P<payload1>.*?)           # capture ALL lines that follow
        (?:</code>|$)               # until </code> or end-of-string
    )
    |
    (?:                             # 2) ``` fenced block
        ```(?:{re.escape(output_type)}|[^\n]*)[ \t]*\n
        (?P<payload2>.*?)           # capture payload
        (?:```|$)                   # until closing fence or EOS
    )
    """

    m = re.search(tag_or_fence, text, re.DOTALL | re.IGNORECASE | re.VERBOSE)
    if m:
        # whichever group matched, return it
        payload = m.group("payload1") or m.group("payload2")
        print(payload.strip())
        return payload.strip()

    # For HTML output, use the text verbatim
    if text.startswith("<html>"):
        return text.strip()

    if text.startswith(" <div class"):
        return text.strip()

    # 3) fallback: nothing matched—return everything (trimmed)
    raise ValueError("No renderable code found")


def extract_code_and_save(text, task_id, output_dir):
    """
    Extract code from <code>...</code> or ```<type>``` blocks, and save to file.

    Args:
        text: The input string possibly containing code blocks.
        task_id: Task identifier to infer output type and for filename.
        output_dir: Directory to save extracted file.

    Returns:
        Tuple of (extracted code, filename, success flag)
    """
    # Determine output type
    output_type = determine_output_type(task_id).lower()

    # Decode unicode escape sequences
    try:
        text = text.replace("&lt;", "<").replace("&gt;", ">")
        text = codecs.decode(text, "unicode_escape")
    except Exception:
        pass  # If decoding fails, use the original string

    tag_or_fence = rf"""
    (?:                             # 1) <code> … </code>
        <code>[ \t]*\n              # opener (+ newline it ends with)
        (?P<payload1>.*?)           # capture ALL lines that follow
        (?:</code>|$)               # until </code> or end-of-string
    )
    |
    (?:                             # 2) ``` fenced block
        ```(?:{re.escape(output_type)}|[^\n]*)[ \t]*\n
        (?P<payload2>.*?)           # capture payload
        (?:```|$)                   # until closing fence or EOS
    )
    """

    m = re.search(tag_or_fence, text, re.DOTALL | re.IGNORECASE | re.VERBOSE)
    if m:
        # whichever group matched, return it
        payload = m.group("payload1") or m.group("payload2")
        code = payload.strip()

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create filename with appropriate extension
    ext_map = {
        "json": ".json",
        "yaml": ".yaml",
        "csv": ".csv",
        "toml": ".toml",
        "xml": ".xml",
    }
    extension = ext_map.get(output_type, ".txt")
    filename = os.path.join(output_dir, f"{task_id}{extension}")

    print(code)
    print("hello world")

    # Save extracted code to file
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code)
        return code, filename, True
    except Exception as e:
        logging.error(f"Error saving code for task {task_id}: {str(e)}")
        return code, None, False


def score_non_renderable(task, non_renderable_dir):
    """
    Process and score a non-renderable task. Extracts code, saves to file, and validates format.

    Args:
        task: The task to process
        non_renderable_dir: Directory to save non-renderable files

    Returns:
        Updated task with render_score
    """
    task_id = task.get("task_id", "unknown")
    generation = task.get("generation", "")
    output_type = task.get("output_type", "unknown").lower()

    # Extract code and save to file
    code, file_path, success = extract_code_and_save(
        generation, task_id, non_renderable_dir
    )

    # Set file path in task for evaluation engine to use
    task["output_file"] = file_path if success else None

    score = 0.0

    if success:
        try:
            if output_type == "json":
                with open(file_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
            elif output_type == "yaml":
                with open(file_path, "r", encoding="utf-8") as f:
                    result = yaml.safe_load(f)
            elif output_type == "toml":
                with open(file_path, "r", encoding="utf-8") as f:
                    result = toml.load(f)
            elif output_type == "xml":
                with open(file_path, "r", encoding="utf-8") as f:
                    result = xmltodict.parse(f.read())
            elif output_type == "csv":
                with open(file_path, "r", encoding="utf-8") as f:
                    result = csv.DictReader(f)
            else:
                raise Valuerror("Unsupported file format.")

            # if file not empty, but valid format files, then score = 1
            if result:
                score = 1

        except Exception as e:
            logging.error(f"Error loading file {file_path}: {str(e)}")
            task["render_score"] = score
            return None, 0

    task["render_score"] = score
    return task
