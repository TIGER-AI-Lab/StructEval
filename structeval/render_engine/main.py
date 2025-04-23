import os
import json
import logging
import asyncio
import codecs

from render_html import extract_html_from_code_tag, render_html_and_screenshot
from render_react import extract_react_from_code_tag, render_react_and_screenshot
from render_utils import score_non_renderable
from render_latex import extract_latex_from_code_tag, render_latex_and_screenshot
from render_markdown import extract_markdown_from_code_tag, render_markdown_and_screenshot
from render_matplotlib import extract_matplotlib_from_code_tag, render_matplotlib_and_screenshot
from render_canvas import extract_canvas_html_from_code_tag, render_canvas_and_screenshot
from render_angular import extract_angular_component_from_code_tag, render_angular_and_screenshot
from render_mermaid import extract_mermaid_code_from_tag, render_mermaid_and_screenshot
from render_svg import extract_svg_from_code_tag, render_svg_and_screenshot
from render_typst import extract_typst_from_code_tag, render_typst_and_screenshot
from render_vega import extract_vega_json_from_code_tag, render_vega_and_screenshot
from render_vue import extract_vue_code_from_tag, render_vue_and_screenshot


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

async def process_json_file(json_file_path, img_output_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    for task in tasks:
        if not task.get("useVisualRendering", False):
            continue

        task_id = task.get("task_id", "unknown")
        type_code = task.get("task_id", "000000")[2:4]
        
        output_type = next((k.lower() for k, v in TYPE_CODES.items() if v == type_code), "").lower()

        print(output_type)

        generation = task.get("generation", "")
        #try:
            #generation = codecs.decode(generation, 'unicode_escape')
        #except Exception as e:
            #logging.warning(f"[{task_id}] Failed to decode generation string: {e}")
            # Continue with the original generation string if decoding fails
            #pass 
        #print(generation)

        if output_type == "html":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_html_from_code_tag(generation)
            task["render_score"] = await render_html_and_screenshot(task_id, content, img_output_path)

        elif output_type == "react":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_react_from_code_tag(generation)
            task["render_score"] = await render_react_and_screenshot(task_id, content, img_output_path)

        elif output_type == "latex" or output_type == "tikz":
            content = extract_latex_from_code_tag(generation)
        
            task["render_score"] = render_latex_and_screenshot(task_id, content, img_output_path)

        elif output_type == "markdown":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_markdown_from_code_tag(generation)
            task["render_score"] = await render_markdown_and_screenshot(task_id, content, img_output_path)

        elif output_type == "matplotlib":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_matplotlib_from_code_tag(generation)
            task["render_score"] = render_matplotlib_and_screenshot(task_id, content, img_output_path)

        elif output_type == "canvas":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_canvas_html_from_code_tag(generation)
            task["render_score"] = await render_canvas_and_screenshot(task_id, content, img_output_path)

        elif output_type == "angular":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_angular_component_from_code_tag(generation)
            task["render_score"] = await render_angular_and_screenshot(task_id, content, img_output_path)

        elif output_type == "mermaid":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_mermaid_code_from_tag(generation)
            task["render_score"] = await render_mermaid_and_screenshot(task_id, content, img_output_path)

        elif output_type == "svg":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_svg_from_code_tag(generation)
            task["render_score"] = await render_svg_and_screenshot(task_id, content, img_output_path)

        #elif output_type == "none":
            #generation = codecs.decode(generation, 'unicode_escape')
            #content = extract_tikz_from_code_tag(generation)
            #task["render_score"] = render_tikz_and_screenshot(task_id, content, img_output_path)

        elif output_type == "typst":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_typst_from_code_tag(generation)
            task["render_score"] = render_typst_and_screenshot(task_id, content, img_output_path)

        elif output_type == "vega":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_vega_json_from_code_tag(generation)
            task["render_score"] = await render_vega_and_screenshot(task_id, content, img_output_path)

        elif output_type == "vue":
            generation = codecs.decode(generation, 'unicode_escape')
            content = extract_vue_code_from_tag(generation)
            task["render_score"] = await render_vue_and_screenshot(task_id, content, img_output_path)

        else:
            score_non_renderable(task)

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)

if __name__ == "__main__":
    import sys
    json_file = sys.argv[1]
    img_dir = sys.argv[2]
    asyncio.run(process_json_file(json_file, img_dir))