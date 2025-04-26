import os
import re
import logging
from .render_utils import start_browser

def extract_svg_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_svg_and_screenshot(task_id, svg_code, img_output_path):
    """
    Renders inline SVG by injecting it into an HTML wrapper and using Playwright to take a screenshot.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not svg_code:
        logging.warning(f"No SVG content for task {task_id}")
        return render_score

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        svg {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
    {svg_code}
</body>
</html>
"""

    browser, context, page, playwright = await start_browser()
    try:
        await page.set_content(html_template)
        await page.wait_for_load_state("load")
        await page.wait_for_timeout(300)

        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=screenshot_path, full_page=True)

        logging.info(f"SVG screenshot saved: {screenshot_path}")
        render_score = 1
    except Exception as e:
        logging.error(f"SVG rendering failed for task {task_id}: {e}")
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()

    return render_score
