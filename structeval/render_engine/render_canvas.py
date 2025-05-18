# render_canvas.py
import os
import re
import logging
from .render_utils import start_browser
from .render_html import render_html_and_screenshot

def extract_canvas_html_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    if match:
        code = match.group(1)
    else:
        # 2. Try to extract from ```<output_type>``` fenced block
        code_fence_pattern = rf"```{output_type}\s*(.*?)```"
        match = re.search(code_fence_pattern, generation, re.DOTALL)
        if match:
            code = match.group(1).strip() if match else generation.strip()
        else:
            fence_pattern = r"```\s*(.*?)```"
            match = re.search(fence_pattern, generation, re.DOTALL)
            if match:
                code = match.group(1).strip() if match else generation.strip()
            else:
                raise ValueError("Parsing error: No correct tag found")
    return code

async def render_canvas_and_screenshot(task_id, canvas_html, img_output_path):
    """
    Renders HTML+Canvas code and captures a screenshot using Playwright.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not canvas_html:
        logging.warning(f"No Canvas HTML content for {task_id}")
        return render_score

    try:
        # Embedded canvas code should be wrapped in a full HTML document
        html_wrapper = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Canvas Render</title>
        </head>
        <body>
            <canvas id="canvas" width="600" height="400"></canvas>
            <script>
                {canvas_html}
            </script>
        </body>
        </html>
        """

        # print(html_wrapper)
        
        # Use HTML renderer to capture the rendered canvas
        render_score = await render_html_and_screenshot(task_id, html_wrapper, img_output_path)
        
    except Exception as e:
        logging.error(f"Canvas rendering error for {task_id}: {e}")
    
    return render_score