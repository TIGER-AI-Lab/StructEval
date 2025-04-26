import os
import re
import tempfile
import logging
import markdown

from .render_utils import start_browser
from .render_html import render_html_and_screenshot

def extract_markdown_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_markdown_and_screenshot(task_id, markdown_content, img_output_path):
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not markdown_content:
        logging.warning(f"No Markdown content for {task_id}")
        return render_score

    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content)
        # Wrap in full HTML document
        html_document = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Markdown Render</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Use the HTML renderer to render and take screenshot
        render_score = await render_html_and_screenshot(task_id, html_document, img_output_path)
        
    except Exception as e:
        logging.error(f"Markdown rendering error for {task_id}: {e}")
        
    return render_score
