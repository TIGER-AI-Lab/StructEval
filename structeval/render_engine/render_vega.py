import os
import re
import json
import logging
from render_utils import start_browser

def extract_vega_json_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_vega_and_screenshot(task_id, vega_spec, img_output_path):
    """
    Renders a Vega visualization using the Vega CDN and captures a screenshot.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not vega_spec:
        logging.warning(f"No Vega spec for task {task_id}")
        return render_score

    try:
        # Try parsing as JSON to validate spec
        json.loads(vega_spec)
    except Exception as e:
        logging.error(f"Invalid Vega spec JSON for {task_id}: {e}")
        return render_score

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    body {{
      margin: 0;
      padding: 2rem;
      background: white;
    }}
    #vis {{
      width: 800px;
      height: 600px;
    }}
  </style>
</head>
<body>
  <div id="vis"></div>
  <script>
    const spec = {vega_spec};
    vegaEmbed('#vis', spec).catch(console.error);
  </script>
</body>
</html>
"""

    browser, context, page, playwright = await start_browser()
    try:
        await page.set_content(html_template)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=screenshot_path, full_page=True)

        logging.info(f"Vega screenshot saved: {screenshot_path}")
        render_score = 1
    except Exception as e:
        logging.error(f"Vega rendering failed for task {task_id}: {e}")
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()

    return render_score
