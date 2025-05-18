import os
import json
import logging
import asyncio
import codecs

from .render_html import extract_html_from_code_tag, render_html_and_screenshot
from .render_react import extract_react_from_code_tag, render_react_and_screenshot
from .render_utils import score_non_renderable, determine_output_type, extract_renderable_code
from .render_latex import extract_latex_from_code_tag, render_latex_to_png
from .render_markdown import extract_markdown_from_code_tag, render_markdown_and_screenshot
from .render_matplotlib import extract_matplotlib_from_code_tag, render_matplotlib_and_screenshot
from .render_canvas import extract_canvas_html_from_code_tag, render_canvas_and_screenshot
from .render_angular import extract_angular_component_from_code_tag, render_angular_and_screenshot
from .render_mermaid import extract_mermaid_code_from_tag, render_mermaid_and_screenshot
from .render_svg import extract_svg_from_code_tag, render_svg_and_screenshot
from .render_typst import extract_typst_from_code_tag, render_typst_and_screenshot
from .render_vega import extract_vega_json_from_code_tag, render_vega_and_screenshot
from .render_vue import extract_vue_code_from_tag, render_vue_and_screenshot



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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def safe_unicode_decode(text):
    """
    Safely decode unicode escape sequences in text.
    If an error occurs, return the original text.
    """
    try:
        return codecs.decode(text, 'unicode_escape')
    except Exception as e:
        logging.warning(f"Unicode decode error: {str(e)}")
        # Try to escape any problematic sequences
        try:
            # Replace any single backslashes not followed by valid escape chars with double backslashes
            import re
            fixed_text = re.sub(r'\\(?![\\\'\"abfnrtv]|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})', r'\\\\', text)
            return codecs.decode(fixed_text, 'unicode_escape')
        except Exception:
            # If all else fails, return the original text
            return text

async def process_json_file(json_file_path, img_output_path, non_renderable_dir):
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # Count renderable tasks
    renderable_count = sum(1 for task in tasks if task.get("rendering", False))
    logging.info(f"Processing {renderable_count} renderable tasks out of {len(tasks)} total tasks")

    # Create output directories
    os.makedirs(img_output_path, exist_ok=True)
    os.makedirs(non_renderable_dir, exist_ok=True)

    # Process each task with error handling
    counter = 0 
    for task in tasks:
        #print the progress of rendering by task id and number of tasks rendered out of total tasks
        counter += 1
        print(f"Rendering task {task['task_id']} of {counter} out of {renderable_count}")
        try:
            task_id = task.get("task_id", "unknown")
            output_type = task.get("output_type", "unknown").lower()
            
            if not task.get("rendering", False):
                # For non-renderable types that can be validated (JSON, YAML, CSV, TOML, XML)
                if output_type in ["json", "yaml", "csv", "toml", "xml"]:
                    logging.info(f"Processing non-renderable task {task_id} with output type: {output_type}")
                    task = score_non_renderable(task, non_renderable_dir)
                continue

            generation = task.get("generation", "")
            
            logging.info(f"Processing renderable task {task_id} with output type: {output_type}")

            if output_type == "html":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_html_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing HTML: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "react":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_react_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing React: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "latex" or output_type == "tikz":
                try:
                    content = extract_latex_from_code_tag(generation, output_type)
                    task["render_score"] = render_latex_to_png(content, img_output_path, task_id)
                    #exit()
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing LaTeX/Tikz: {str(e)}")
                    task["render_score"] = 0
                    #exit()

            elif output_type == "markdown":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_markdown_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Markdown: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "matplotlib":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = render_matplotlib_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Matplotlib: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "canvas":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_canvas_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Canvas: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "angular":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_angular_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Angular: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "mermaid":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_mermaid_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Mermaid: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "svg":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_svg_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing SVG: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "typst":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = render_typst_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Typst: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "vega":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_vega_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Vega: {str(e)}")
                    task["render_score"] = 0

            elif output_type == "vue":
                try:
                    generation = safe_unicode_decode(generation)
                    content = extract_renderable_code(generation, output_type)
                    task["render_score"] = await render_vue_and_screenshot(task_id, content, img_output_path)
                except Exception as e:
                    logging.error(f"[{task_id}] Error processing Vue: {str(e)}")
                    task["render_score"] = 0
            else:
                raise ValueError(f"Unsupported output type: {output_type}")

        except Exception as e:
            logging.error(f"Error processing task {task.get('task_id', 'unknown')}: {str(e)}")
            task["render_score"] = 0
            continue

    # Save all tasks back to the file
    try:
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving tasks back to file: {str(e)}")
        # Create a backup file if original save fails
        backup_path = f"{json_file_path}.backup"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        logging.info(f"Tasks saved to backup file: {backup_path}")

if __name__ == "__main__":
    import sys
    json_file = sys.argv[1]
    img_dir = sys.argv[2]
    non_renderable_dir = sys.argv[3] if len(sys.argv) > 3 else "non_renderable_format_files"
    asyncio.run(process_json_file(json_file, img_dir, non_renderable_dir))