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
        # Try parsing only to pretty-print for debugging, but don't fail rendering if it doesn't parse
        try:
            vega_dict = json.loads(vega_spec)
            spec_script = json.dumps(vega_dict, indent=2)
        except Exception as inner_e:
            logging.warning(f"Using raw spec string for task {task_id} due to JSON decode error: {inner_e}")
            spec_script = vega_spec  # fallback to raw string

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
    const spec = {spec_script};
    vegaEmbed('#vis', spec).catch(console.error);
  </script>
</body>
</html>
"""
    except Exception as e:
        logging.error(f"Unexpected error preparing Vega spec for {task_id}: {e}")
        return render_score

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
