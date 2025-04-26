import logging
import os
import json
import re
from playwright.async_api import async_playwright
from typing import Dict, Any, List, Optional
import asyncio

# Import the render engine's main processing function
from render_engine.main import process_json_file as render_engine_process_json_file

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

async def process_json_file(json_file_path: str, img_output_path: str) -> str:
    """
    Coordinates rendering by delegating to the render_engine.
    This function serves as a facade for the render_engine functionality.
    
    Args:
        json_file_path: Path to the JSON file containing the tasks
        img_output_path: Directory where rendered images will be saved
        
    Returns:
        The img_output_path where rendered images are saved
    """
    logging.info(f"Starting rendering process for {json_file_path}")
    
    # Ensure the output directory exists
    os.makedirs(img_output_path, exist_ok=True)
    
    # Read tasks to identify non-renderable tasks
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Mark non-renderable tasks with render_score=None
    for task in tasks:
        if not task.get("useVisualRendering", False):
            task["render_score"] = None
    
    # Write back the updated tasks
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
    
    # Delegate to the main render engine for renderable tasks
    await render_engine_process_json_file(json_file_path, img_output_path)
    
    logging.info(f"Rendering completed. Images saved to {img_output_path}")
    return img_output_path

async def get_rendering_metadata(json_file_path: str) -> Dict[str, Any]:
    """
    Analyzes the dataset to provide rendering statistics
    
    Args:
        json_file_path: Path to the JSON file containing tasks
        
    Returns:
        A dictionary of statistics about renderable tasks
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    total_tasks = len(tasks)
    renderable_tasks = sum(1 for task in tasks if task.get("useVisualRendering", False))
    
    # Count by output type
    type_codes = {}
    for task in tasks:
        if task.get("useVisualRendering", False):
            task_id = task.get("task_id", "000000")
            if len(task_id) >= 4:
                type_code = task_id[2:4]
                type_codes[type_code] = type_codes.get(type_code, 0) + 1
    
    return {
        "total_tasks": total_tasks,
        "renderable_tasks": renderable_tasks,
        "type_distribution": type_codes,
        "percent_renderable": round(renderable_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python render.py <json_file_path> <img_output_path>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    img_dir = sys.argv[2]
    
    asyncio.run(process_json_file(json_file, img_dir))
