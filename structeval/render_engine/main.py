import os
import json
import logging
import asyncio
import codecs

from .render_html import render_html_and_screenshot
from .render_react import render_react_and_screenshot
from .render_utils import score_non_renderable, extract_renderable_code
from .render_latex import extract_latex_from_code_tag, render_latex_to_png
from .render_markdown import render_markdown_and_screenshot
from .render_matplotlib import render_matplotlib_and_screenshot
from .render_canvas import render_canvas_and_screenshot
from .render_angular import render_angular_and_screenshot
from .render_mermaid import render_mermaid_and_screenshot
from .render_svg import render_svg_and_screenshot
from .render_typst import render_typst_and_screenshot
from .render_vega import render_vega_and_screenshot
from .render_vue import render_vue_and_screenshot



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

NON_RENDERABLE_OUTPUT_TYPES = {"json", "yaml", "csv", "toml", "xml"}

DEFAULT_RENDER_TYPE_LIMITS = {
    "json": 16,
    "yaml": 16,
    "csv": 16,
    "toml": 16,
    "xml": 16,
    "html": 4,
    "svg": 4,
    "markdown": 4,
    "canvas": 4,
    "matplotlib": 4,
    "latex": 2,
    "tikz": 2,
    "mermaid": 2,
    "vega": 2,
    "react": 2,
    "vue": 1,
    "angular": 1,
    "typst": 1,
}

ASYNC_RENDERERS = {
    "html": render_html_and_screenshot,
    "react": render_react_and_screenshot,
    "markdown": render_markdown_and_screenshot,
    "canvas": render_canvas_and_screenshot,
    "angular": render_angular_and_screenshot,
    "mermaid": render_mermaid_and_screenshot,
    "svg": render_svg_and_screenshot,
    "vega": render_vega_and_screenshot,
    "vue": render_vue_and_screenshot,
}

THREAD_RENDERERS = {
    "matplotlib": render_matplotlib_and_screenshot,
    "typst": render_typst_and_screenshot,
}


def safe_unicode_decode(text):
    """
    Safely decode unicode escape sequences in text.
    If an error occurs, return the original text.
    """
    try:
        #replace &lt; with < , and &gt; with >
        text = text.replace("&lt;", "<").replace("&gt;", ">")
        
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


def _render_bucket(task):
    output_type = task.get("output_type", "unknown").lower()
    if not task.get("rendering", False):
        return output_type if output_type in NON_RENDERABLE_OUTPUT_TYPES else "skip"
    return output_type


def _extract_renderable_content(generation, output_type):
    if output_type in {"latex", "tikz"}:
        return extract_latex_from_code_tag(generation, output_type)
    return extract_renderable_code(safe_unicode_decode(generation), output_type)


async def _render_content(task_id, output_type, content, img_output_path):
    if output_type in {"latex", "tikz"}:
        return await asyncio.to_thread(render_latex_to_png, content, img_output_path, task_id)
    if output_type in THREAD_RENDERERS:
        return await asyncio.to_thread(THREAD_RENDERERS[output_type], task_id, content, img_output_path)
    if output_type in ASYNC_RENDERERS:
        return await ASYNC_RENDERERS[output_type](task_id, content, img_output_path)
    raise ValueError(f"Unsupported output type: {output_type}")


async def _process_task(task, counter, total, img_output_path, non_renderable_dir):
    print(f"Rendering task {task['task_id']} of {counter} out of {total}")
    try:
        task_id = task.get("task_id", "unknown")
        output_type = task.get("output_type", "unknown").lower()

        if not task.get("rendering", False):
            if output_type in NON_RENDERABLE_OUTPUT_TYPES:
                logging.info(f"Processing non-renderable task {task_id} with output type: {output_type}")
                updated_task = await asyncio.to_thread(score_non_renderable, task, non_renderable_dir)
                if updated_task is not task:
                    task.update(updated_task)
            return

        generation = task.get("generation", "")
        logging.info(f"Processing renderable task {task_id} with output type: {output_type}")

        content = None
        try:
            content = _extract_renderable_content(generation, output_type)
            task["parsed_code"] = content
            task["extract_error"] = None
        except Exception as e:
            task["extract_error"] = str(e)
            task["parsed_code"] = None
            logging.error(f"[{task_id}] Error extracting {output_type} from code tag: {str(e)}")

        if content is None:
            task["render_error"] = task.get("extract_error") or "No renderable content extracted"
            task["render_score"] = 0
            return

        try:
            task["render_score"] = await _render_content(task_id, output_type, content, img_output_path)
            task["render_error"] = None
        except Exception as e:
            task["render_error"] = str(e)
            task["render_score"] = 0
            logging.error(f"[{task_id}] Error processing {output_type}: {str(e)}")

    except Exception as e:
        logging.error(f"Error processing task {task.get('task_id', 'unknown')}: {str(e)}")
        task["render_score"] = 0


async def process_json_file(json_file_path, img_output_path, non_renderable_dir, render_concurrency=1):
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # Count renderable tasks
    renderable_count = sum(1 for task in tasks if task.get("rendering", False))
    logging.info(f"Processing {renderable_count} renderable tasks out of {len(tasks)} total tasks")

    render_concurrency = max(1, int(render_concurrency or 1))
    img_output_path = os.path.abspath(img_output_path)
    non_renderable_dir = os.path.abspath(non_renderable_dir)

    # Create output directories
    os.makedirs(img_output_path, exist_ok=True)
    os.makedirs(non_renderable_dir, exist_ok=True)

    logging.info(f"Rendering with global concurrency={render_concurrency}")
    if render_concurrency == 1:
        for counter, task in enumerate(tasks, start=1):
            await _process_task(task, counter, len(tasks), img_output_path, non_renderable_dir)
    else:
        global_semaphore = asyncio.Semaphore(render_concurrency)
        type_semaphores = {}

        def type_semaphore(bucket):
            if bucket not in type_semaphores:
                limit = min(render_concurrency, DEFAULT_RENDER_TYPE_LIMITS.get(bucket, 1))
                type_semaphores[bucket] = asyncio.Semaphore(max(1, limit))
            return type_semaphores[bucket]

        async def run_task(counter, task):
            bucket = _render_bucket(task)
            async with type_semaphore(bucket):
                async with global_semaphore:
                    await _process_task(task, counter, len(tasks), img_output_path, non_renderable_dir)

        await asyncio.gather(
            *(run_task(counter, task) for counter, task in enumerate(tasks, start=1))
        )

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
    render_concurrency = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    asyncio.run(process_json_file(json_file, img_dir, non_renderable_dir, render_concurrency))
