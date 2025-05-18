import os
import logging
import re
from .render_utils import start_browser

REACT_RENDER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "react_render")

def extract_react_from_code_tag(generation):
    """
    Return all text between the first <code> and the last </code>.
    Greedy match ensures we keep multi‑segment code blocks intact.
    """
    match = re.search(r"<code>(.*)</code>", generation, re.DOTALL)
    return match.group(1).strip() if match else generation.strip()

def create_simple_react_app(task_id, react_content):
    task_dir = os.path.join(REACT_RENDER_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    processed_react = react_content.strip()
    export_name = None  # remember the component that was exported as default

    # Remove outer <code> tags if present
    if processed_react.startswith("<code>") and processed_react.endswith("</code>"):
        processed_react = processed_react[len("<code>"):-len("</code>")].strip()

    # Split into lines and filter out all import and export lines
    lines = processed_react.splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import"):
            continue  # drop every import line
        if stripped.startswith("export default"):
            # remember which component was the default export, then drop the line
            export_parts = stripped.split()
            if len(export_parts) >= 3:
                export_name = export_parts[2].rstrip(";")
            continue
        new_lines.append(line)
    processed_react = "\n".join(new_lines)

    # If hooks like useState/useEffect are referenced without React import,
    # destructure them from the global React to avoid "useState is not defined" errors.
    hook_boilerplate = "const { useState, useEffect, useRef, useContext, useReducer, useMemo, useCallback } = React;"
    processed_react = hook_boilerplate + "\n\n" + processed_react

    # Extract component name
    match = re.search(r"function (\w+)", processed_react)
    component_name = match.group(1) if match else "App"

    # ------------------------------------------------------------------
    # Auto‑fix mounting so code written for React ≤17 still works with
    # the React 18 UMD bundle we inject, *and* add a mount if the user
    # supplied none at all.
    # ------------------------------------------------------------------
    has_old_render = re.search(r"ReactDOM\.render\s*\(", processed_react)
    has_create_root = re.search(r"ReactDOM\.createRoot\s*\(", processed_react)

    # (a) upgrade ReactDOM.render(...) → ReactDOM.createRoot(...).render(...)
    if has_old_render and not has_create_root:
        processed_react = re.sub(
            r"ReactDOM\.render\s*\(\s*(<[^,]+?>)\s*,\s*document\.getElementById\(['\"]root['\"]\)\s*\)",
            r"ReactDOM.createRoot(document.getElementById('root')).render(\1)",
            processed_react,
        )
        has_create_root = True  # now fixed

    # (b) no mount at all → guess the component and add a mount snippet
    if not has_create_root:
        # Try to grab the exported component name, otherwise fall back to the first function‑component match
        export_match = re.search(r"export\s+default\s+(\w+)", processed_react)
        first_fn_match = re.search(r"function\s+(\w+)\s*\(", processed_react)
        component_to_mount = export_name or (first_fn_match.group(1) if first_fn_match else component_name)
        processed_react += (
            f"\n\n// Auto‑generated mount\n"
            f"ReactDOM.createRoot(document.getElementById('root')).render(<{component_to_mount} />);\n"
        )


    html_template = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>React Render – {task_id}</title>
    <!-- React 18 UMD bundles -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <!-- Babel for on-the-fly JSX transform -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>body{{margin:0;font-family:sans-serif;}}</style>
  </head>
  <body>
    <div id="root"></div>

    <!-- User component -->
    <script type="text/babel">
    {processed_react}
    </script>
  </body>
</html>
"""

    html_path = os.path.join(task_dir, "index.html")
    try:
        with open(html_path, "w") as f:
            f.write(html_template)
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