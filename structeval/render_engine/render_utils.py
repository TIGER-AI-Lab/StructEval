import json
import yaml
import csv
import io
import logging
from playwright.async_api import async_playwright

async def start_browser(headless=True):
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    return browser, context, page, playwright

def score_non_renderable(task):
    output_type = task.get("output_type", "").lower()
    generation = task.get("generation", "")
    score = 0.0

    try:
        if output_type == "json":
            json.loads(generation)
            score = 1.0

        elif output_type == "yaml":
            yaml.safe_load(generation)
            score = 1.0

        elif output_type == "csv":
            rows = list(csv.reader(io.StringIO(generation.strip())))
            score = 1.0 if rows and len(rows) >= 2 else 0.0

    except Exception as e:
        logging.warning(f"Failed to parse {output_type}: {e}")

    task["render_score"] = score
    return task