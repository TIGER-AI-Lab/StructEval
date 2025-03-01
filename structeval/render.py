import logging
import os
import json
import re
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# extract HTML code from <code> </code> tags
def extract_html_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

# Start headless browser
async def start_browser(headless=True):
    """
    Launch a headless browser instance and return the page object.
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    
    logging.info("Browser started.")
    return browser, context, page, playwright

# Render HTML and take a screenshot
async def render_html_and_screenshot(task_id, html_content, img_output_path):
    """
    Loads HTML content into a headless browser and captures a screenshot.

    :param task_id: Unique task ID for filename.
    :param html_content: The HTML string to render.
    """
    browser, context, page, playwright = await start_browser()
    os.makedirs(img_output_path, exist_ok=True)

    render_score = 0  # Default to 0 in case of errors
    
    if not html_content:
        logging.warning(f"Skipping task {task_id}: No valid HTML content found.")
        await browser.close()
        await playwright.stop()
        return render_score

    try:
        await page.set_content(html_content)
        await page.wait_for_load_state("load")  # Ensure full rendering
        
        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        logging.info(f"Screenshot saved: {screenshot_path}")
        render_score = 1  # Successful rendering
    except Exception as e:
        logging.error(f"Rendering failed for task {task_id}: {e}")
    
    await page.close()
    await context.close()
    await browser.close()
    await playwright.stop()
    
    return render_score

# Process the JSON file
async def process_json_file(json_file_path, img_output_path):
    """
    Reads a JSON file, extracts HTML tasks, and processes them.
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    logging.info(f"Loaded {len(tasks)} tasks from {json_file_path}")

    for task in tasks:
        task_id = task.get("task_id", "unknown")
        html_content = extract_html_from_code_tag(task.get("generation", ""))
        
        if task.get("useVisualRendering", False):
            task["render_score"] = await render_html_and_screenshot(task_id, html_content, img_output_path)
    
    # Save updated JSON with render scores
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
