# render_canvas.py
import os
import re
import logging
from render_react import start_browser

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
        logging.warning(f"No canvas HTML content for task {task_id}")
        return render_score

    browser, context, page, playwright = await start_browser()

    try:
        await page.set_content(canvas_html)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(500)  # give time for JS drawing

        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=screenshot_path, full_page=True)

        logging.info(f"Canvas screenshot saved: {screenshot_path}")
        render_score = 1
    except Exception as e:
        logging.error(f"Canvas rendering failed for {task_id}: {e}")
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()

    return render_score