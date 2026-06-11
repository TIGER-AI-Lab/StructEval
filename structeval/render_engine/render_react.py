import os
import logging
import re
import html
from .render_utils import start_browser

REACT_RENDER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "react_render"
)


def extract_react_from_code_tag(generation):
    """
    Return all text between the first <code> and the last </code>.
    Greedy match ensures we keep multi‑segment code blocks intact.
    """
    match = re.search(r"<code>(.*)</code>", generation, re.DOTALL)
    extracted_code = match.group(1).strip() if match else generation.strip()
    return html.unescape(extracted_code)  # Decode HTML entities


def _normalize_react_source(source):
    processed_react = source.strip()
    export_name = None

    if processed_react.startswith("<code>") and processed_react.endswith("</code>"):
        processed_react = processed_react[len("<code>") : -len("</code>")].strip()

    new_lines = []
    for line in processed_react.splitlines():
        stripped = line.strip()

        if re.match(r"^\s*import\b", line):
            continue

        default_function = re.match(
            r"^(\s*)export\s+default\s+(async\s+)?function(?:\s+([A-Za-z_$][\w$]*))?\s*\(",
            line,
        )
        if default_function:
            indent, async_prefix, name = default_function.groups()
            export_name = name or "App"
            replacement = f"{indent}{async_prefix or ''}function {export_name}("
            line = re.sub(
                r"^(\s*)export\s+default\s+(async\s+)?function(?:\s+[A-Za-z_$][\w$]*)?\s*\(",
                replacement,
                line,
                count=1,
            )
            new_lines.append(line)
            continue

        default_class = re.match(
            r"^(\s*)export\s+default\s+class(?:\s+([A-Za-z_$][\w$]*))?",
            line,
        )
        if default_class:
            indent, name = default_class.groups()
            export_name = name or "App"
            line = re.sub(
                r"^(\s*)export\s+default\s+class(?:\s+[A-Za-z_$][\w$]*)?",
                f"{indent}class {export_name}",
                line,
                count=1,
            )
            new_lines.append(line)
            continue

        default_identifier = re.match(
            r"^\s*export\s+default\s+([A-Za-z_$][\w$]*)\s*;?\s*$",
            line,
        )
        if default_identifier:
            export_name = default_identifier.group(1)
            continue

        default_expression = re.match(r"^(\s*)export\s+default\s+(.+)$", line)
        if default_expression:
            indent, expression = default_expression.groups()
            export_name = "App"
            new_lines.append(f"{indent}const App = {expression}")
            continue

        named_export = re.match(
            r"^(\s*)export\s+(?=(const|let|var|function|class)\b)",
            line,
        )
        if named_export:
            line = re.sub(r"^(\s*)export\s+", r"\1", line, count=1)

        if re.match(r"^\s*export\s+\{", line):
            continue

        new_lines.append(line)

    return "\n".join(new_lines), export_name


def _react_root_has_content(root_state):
    if not root_state.get("hasRoot"):
        return False
    html_content = (root_state.get("html") or "").strip()
    text_content = (root_state.get("text") or "").strip()
    return bool(html_content or text_content)


def create_simple_react_app(task_id, react_content):
    task_dir = os.path.join(REACT_RENDER_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    processed_react, export_name = _normalize_react_source(react_content)

    # If hooks like useState/useEffect are referenced without React import,
    # destructure them from the global React to avoid "useState is not defined" errors.
    hook_boilerplate = "const { useState, useEffect, useRef, useContext, useReducer, useMemo, useCallback } = React;"
    processed_react = hook_boilerplate + "\n\n" + processed_react

    # Extract component name - support both function declaration and arrow function syntax
    fn_match = re.search(r"function (\w+)", processed_react)
    const_match = re.search(r"const (\w+)\s*=", processed_react)
    component_name = None

    if fn_match:
        component_name = fn_match.group(1)
    elif const_match:
        component_name = const_match.group(1)
    else:
        component_name = "App"

    # ------------------------------------------------------------------
    # Auto‑fix mounting so code written for React ≤17 still works with
    # the React 18 UMD bundle we inject, *and* add a mount if the user
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
        component_to_mount = export_name or component_name
        processed_react += (
            f"\n\n// Auto‑generated mount\n"
            f"ReactDOM.createRoot(document.getElementById('root')).render(<{component_to_mount} />);\n"
        )

    # Add default CSS for better display of dashboard and other components
    default_css = """
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
      background-color: #f5f5f5;
      color: #333;
      line-height: 1.5;
    }
    #app, #root {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background-color: white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.12);
      min-height: 100vh;
    }
    header {
      margin-bottom: 20px;
      border-bottom: 1px solid #eee;
      padding-bottom: 15px;
    }
    h1 {
      color: #2c3e50;
      margin-top: 0;
    }
    h2 {
      color: #42b983;
      margin-top: 1.5em;
    }
    section, article {
      margin-bottom: 20px;
    }
    aside {
      background-color: #f9f9f9;
      padding: 15px;
      margin: 20px 0;
      border-left: 3px solid #42b983;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 15px 0;
    }
    th {
      background-color: #f2f2f2;
      text-align: left;
    }
    th, td {
      padding: 8px 10px;
      border: 1px solid #ddd;
    }
    footer {
      margin-top: 30px;
      padding-top: 15px;
      border-top: 1px solid #eee;
      color: #666;
      font-size: 0.9em;
    }
    ul, ol {
      padding-left: 20px;
    }
    li {
      margin-bottom: 8px;
    }
    """

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
    <style>
    {default_css}
    </style>
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
    img_output_path_abs = os.path.abspath(img_output_path)
    os.makedirs(img_output_path_abs, exist_ok=True)
    render_score = 0

    if not react_content:
        logging.warning(f"No React content for {task_id}")
        return render_score

    html_path = create_simple_react_app(task_id, react_content)
    if not html_path:
        return render_score

    browser, context, page, playwright = await start_browser()
    page_errors = []
    console_errors = []
    page.on("pageerror", lambda err: page_errors.append(str(err)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    screenshot_path = os.path.join(img_output_path_abs, f"{task_id}.png")
    error_screenshot_path = os.path.join(img_output_path_abs, f"{task_id}_error.png")
    try:
        await page.goto(f"file://{html_path}", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=60000)

        # Extra time to ensure React fully renders
        await page.wait_for_timeout(2000)

        root_state = await page.evaluate(
            """() => {
                const root = document.getElementById('root');
                return {
                    hasRoot: !!root,
                    html: root ? root.innerHTML : '',
                    text: root ? root.innerText : ''
                };
            }"""
        )

        failure_reason = None
        if page_errors:
            failure_reason = "; ".join(page_errors[:3])
        elif console_errors:
            failure_reason = "; ".join(console_errors[:3])
        elif not _react_root_has_content(root_state):
            failure_reason = "React root is empty"

        if failure_reason:
            logging.error(f"React rendering failed for {task_id}: {failure_reason}")
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
            await page.screenshot(path=error_screenshot_path, full_page=True)
            logging.info(f"React error screenshot saved: {error_screenshot_path}")
        else:
            if os.path.exists(error_screenshot_path):
                os.remove(error_screenshot_path)
            await page.screenshot(path=screenshot_path, full_page=True)
            logging.info(f"React screenshot saved: {screenshot_path}")
            render_score = 1
    except Exception as e:
        logging.error(f"React rendering error for {task_id}: {e}")
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        try:
            await page.screenshot(path=error_screenshot_path, full_page=True)
        except Exception:
            pass
    finally:
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()

    return render_score
