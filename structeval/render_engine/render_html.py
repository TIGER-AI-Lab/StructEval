import os
import logging
import re
from playwright.async_api import async_playwright
from .render_utils import start_browser

def extract_html_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_html_and_screenshot(task_id, html_content, img_output_path):

    browser, context, page, playwright = await start_browser()
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not html_content:
        logging.warning(f"No HTML content for {task_id}")
        await browser.close(); await playwright.stop()
        return render_score

    try:
        await page.set_content(html_content)
        await page.wait_for_load_state("load")
        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        logging.info(f"HTML screenshot saved: {screenshot_path}")
        render_score = 1
    except Exception as e:
        logging.error(f"HTML rendering error for {task_id}: {e}")
    finally:
        await page.close(); await context.close(); await browser.close(); await playwright.stop()

    return render_score