# render_canvas.py
import os
import re
import logging
from .render_utils import start_browser
from .render_html import render_html_and_screenshot

def extract_canvas_html_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

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
            {canvas_html}
        </body>
        </html>
        """
        
        # Use HTML renderer to capture the rendered canvas
        render_score = await render_html_and_screenshot(task_id, html_wrapper, img_output_path)
        
    except Exception as e:
        logging.error(f"Canvas rendering error for {task_id}: {e}")
    
    return render_score