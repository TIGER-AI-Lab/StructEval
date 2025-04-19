import os
import logging
import re
from render_utils import start_browser

REACT_RENDER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "react_render")

def extract_react_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

def create_simple_react_app(task_id, react_content):
    task_dir = os.path.join(REACT_RENDER_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    html_path = os.path.join(task_dir, "index.html")
    try:
        with open(html_path, "w") as f:
            f.write(react_content)  # insert into a template if needed
        return html_path
    except Exception as e:
        logging.error(f"React app creation failed for {task_id}: {e}")
        return None

async def render_react_and_screenshot(task_id, react_content, img_output_path):
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not react_content:
        logging.warning(f"No React content for {task_id}")
        return render_score

    html_path = create_simple_react_app(task_id, react_content)
    if not html_path:
        return render_score

    browser, context, page, playwright = await start_browser()
    try:
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state("networkidle")
        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        logging.info(f"React screenshot saved: {screenshot_path}")
        render_score = 1
    except Exception as e:
        logging.error(f"React rendering error for {task_id}: {e}")
    finally:
        await page.close(); await context.close(); await browser.close(); await playwright.stop()

    return render_score