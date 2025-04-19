import os
import re
import tempfile
import logging
import markdown
import subprocess
from render_html import render_html_and_screenshot

def extract_markdown_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_markdown_and_screenshot(task_id, markdown_text, img_output_path):
    """
    Converts Markdown to HTML and renders it to a screenshot using the HTML renderer.
    Returns 1 if successful, 0 otherwise.
    """
    if not markdown_text:
        logging.warning(f"No Markdown content for task {task_id}")
        return 0

    try:
        # Convert markdown to HTML
        # markdown_text = markdown_text.replace('\\n', '\n') # Commented out again, rely on global decode
        html_content = markdown.markdown(markdown_text, extensions=["fenced_code", "tables"])
        wrapped_html = f"<html><body>{html_content}</body></html>"

        # Use existing HTML renderer
        return await render_html_and_screenshot(task_id, wrapped_html, img_output_path)
    except Exception as e:
        logging.error(f"Markdown rendering failed for task {task_id}: {e}")
        return 0
