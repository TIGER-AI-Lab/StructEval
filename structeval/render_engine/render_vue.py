import os
import re
import html  # for un‑escaping &lt;…&gt; that often wraps SFC code
import logging
import tempfile
import subprocess
import asyncio
import shutil
import time
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from .render_utils import start_browser

# Path to the simplified Vue template
VUE_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vue_template"
)


def extract_vue_code_from_tag(generation):
    """
    Extract Vue code from a code tag. Handles multiple Vue formats:
    1. Object format (starts with {})
    2. Single File Component (SFC) format with <template>, <script> tags
    3. Modern Vue format with imports and Composition API
    4. Component with export default
    5. <script setup> syntax (Vue 3)

    Converts all formats to object format that can be used with Vue.createApp.
    Returns a tuple of (component_code, style_content)
    """
    # Always decode HTML entities - this is crucial for properly rendering Vue components
    generation = html.unescape(generation)

    # Check if we have code tags
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    if not match:
        vue_code = generation.strip()
    else:
        vue_code = match.group(1).strip()

    # SFC: Extract <template>, <script>, and <style>
    template_match = re.search(r"<template>(.*?)</template>", vue_code, re.DOTALL)
    script_match = re.search(r"<script>(.*?)</script>", vue_code, re.DOTALL)
    script_setup_match = re.search(
        r"<script\s+setup.*?>(.*?)</script>", vue_code, re.DOTALL
    )
    style_match = re.search(r"<style.*?>(.*?)</style>", vue_code, re.DOTALL)

    template = template_match.group(1).strip() if template_match else None
    script = script_match.group(1).strip() if script_match else None
    script_setup = script_setup_match.group(1).strip() if script_setup_match else None
    style = style_match.group(1).strip() if style_match else None

    # Prepare the component code
    component_code = ""

    # Handle <script setup> syntax for Vue 3
    if template and script_setup:
        # For script setup, we need to convert it to options API format
        # This is a simplified conversion - in a real-world scenario, you'd need
        # a more sophisticated parser for complete support
        setup_code = f"setup() {{ {script_setup} return {{ }}; }}"
        component_code = "{\n  template: `" + template + "`,\n" + setup_code + "\n}"
    # If both template and script exist, merge them
    elif template and script:
        # Remove export default and surrounding braces if present
        script = script.strip()
        if script.startswith("export default"):
            script = script[len("export default") :].strip()
        if script.startswith("{") and script.endswith("}"):
            script = script[1:-1].strip()
        # Compose the component object
        component_code = "{\n  template: `" + template + "`,\n" + script + "\n}"
    elif template:
        component_code = "{\n  template: `" + template + "`\n}"
    # Check if it's already in object format (starts with a curly brace)
    elif vue_code.strip().startswith("{") and vue_code.strip().endswith("}"):
        component_code = vue_code
    else:
        # Final fallback: treat whole code as template (this is a simplification)
        component_code = (
            "{\n  template: `<pre>${escapeTemplate(`" + vue_code + "`)}</pre>`\n}"
        )

    return component_code, style


def escapeTemplate(text):
    """Escape special characters in template strings"""
    return text.replace("${", "\\${").replace("`", "\\`")


def ensure_vue_template_exists():
    """Check if the simplified Vue template exists"""
    if os.path.exists(VUE_TEMPLATE_DIR) and os.path.isdir(VUE_TEMPLATE_DIR):
        logging.info(f"Using existing Vue template at {VUE_TEMPLATE_DIR}")
        return True

    logging.error(f"Vue template not found at {VUE_TEMPLATE_DIR}")
    return False


def find_free_port():
    """Find a free port to use for the HTTP server"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    """A quieter HTTP request handler that doesn't log every request"""

    def log_message(self, format, *args):
        pass  # Suppress log messages


def start_http_server(directory, port):
    """Start a simple HTTP server in a separate thread"""
    os.chdir(directory)  # stay here until cleanup
    server = HTTPServer(("localhost", port), QuietHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def render_vue_and_screenshot(task_id, vue_code, img_output_path):
    """
    Renders Vue component code by copying a simplified Vue CDN template,
    injecting the component, and taking a screenshot.
    """
    img_output_path = os.path.abspath(img_output_path)  # <— make path absolute
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not vue_code:
        logging.warning(f"No Vue content for task {task_id}")
        return render_score

    # Process the Vue code before rendering
    try:
        # Extract Vue component code from the raw text
        processed_vue_code, style_content = extract_vue_code_from_tag(vue_code)
        logging.info(f"[{task_id}] Successfully processed Vue component")
    except Exception as e:
        logging.error(f"[{task_id}] Error processing Vue component: {e}")
        # Create a fallback component wrapping the raw code in a pre element
        processed_vue_code = (
            "{\n  template: `<pre>${escapeTemplate(`" + vue_code + "`)}</pre>`\n}"
        )
        style_content = None

    # Ensure template exists
    if not ensure_vue_template_exists():
        logging.error(f"[{task_id}] Cannot render Vue - template not found")
        return render_score

    # Keep track of the original working directory
    original_dir = os.getcwd()
    server = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy the template to temp directory
            logging.info(f"[{task_id}] Copying Vue template...")
            project_dir = os.path.join(tmpdir, "vue-app")
            shutil.copytree(VUE_TEMPLATE_DIR, project_dir)
            logging.info(f"[{task_id}] Vue template copied to {project_dir}")

            # Replace app.js with user's Vue component code
            logging.info(f"[{task_id}] Injecting component code...")
            app_js_path = os.path.join(project_dir, "app.js")

            # Create a simpler Vue setup regardless of input component format
            formatted_vue_code = f"""
// Template for Vue application
const {{ createApp }} = Vue;

// Simple Vue component that directly uses the input code
const App = {processed_vue_code};

// Mount the app
const app = createApp(App);
app.mount('#app');
"""

            with open(app_js_path, "w") as f:
                f.write(formatted_vue_code)
            logging.info(f"[{task_id}] Component code injected.")

            # If style is present, inject it into index.html
            if style_content:
                logging.info(f"[{task_id}] Injecting style content...")
                index_html_path = os.path.join(project_dir, "index.html")
                with open(index_html_path, "r") as f:
                    html_content = f.read()

                # Insert style before </head>
                html_content = html_content.replace(
                    "</head>", f"<style>{style_content}</style></head>"
                )

                with open(index_html_path, "w") as f:
                    f.write(html_content)
                logging.info(f"[{task_id}] Style content injected.")

            # For debugging, also write the processed component to a file
            debug_file = os.path.join(img_output_path, f"{task_id}_component.js")
            with open(debug_file, "w") as f:
                f.write(formatted_vue_code)

            # Also save style content for debugging if present
            if style_content:
                debug_style_file = os.path.join(img_output_path, f"{task_id}_style.css")
                with open(debug_style_file, "w") as f:
                    f.write(style_content)

            # Find a free port and start the HTTP server
            port = find_free_port()
            logging.info(f"[{task_id}] Starting Python HTTP server on port {port}...")
            server = start_http_server(project_dir, port)
            logging.info(f"[{task_id}] Server started on port {port}")

            # Set a longer timeout for rendering complex Vue components
            logging.info(f"[{task_id}] Starting Playwright browser...")
            browser, context, page, playwright = await start_browser()

            # Log browser console messages for debugging
            page.on(
                "console",
                lambda msg: logging.info(
                    f"[{task_id}] Browser Console: {msg.type} - {msg.text}"
                ),
            )
            page.on(
                "pageerror", lambda err: logging.error(f"[{task_id}] Page Error: {err}")
            )

            logging.info(f"[{task_id}] Playwright browser started.")

            try:
                logging.info(f"[{task_id}] Navigating to page...")
                await page.goto(
                    f"http://localhost:{port}", timeout=60000
                )  # Increase timeout to 60 seconds
                logging.info(f"[{task_id}] Navigation complete. Waiting for load...")

                # Wait for the page to fully load
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=60000)
                logging.info(f"[{task_id}] Page loaded. Taking screenshot...")

                # Add a delay to ensure Vue has properly rendered
                await asyncio.sleep(3)

                # Evaluate the page content to check if Vue mounted correctly
                app_content = await page.evaluate(
                    """() => {
                    const app = document.getElementById('app');
                    return {
                        contentHTML: app ? app.innerHTML : 'No app element found',
                        appChildrenCount: app ? app.children.length : 0
                    };
                }"""
                )

                logging.info(f"[{task_id}] Vue app content: {app_content}")

                screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                logging.info(f"[{task_id}] Vue screenshot saved: {screenshot_path}")
                render_score = 1
            except Exception as e:
                logging.error(f"[{task_id}] Vue rendering failed: {e}")
            finally:
                logging.info(f"[{task_id}] Starting Vue cleanup...")
                await page.close()
                await context.close()
                await browser.close()
                await playwright.stop()
                if server:
                    server.shutdown()
                logging.info(f"[{task_id}] Vue cleanup finished.")
    except Exception as e:
        logging.error(f"Vue setup failed for task {task_id}: {e}")
    finally:
        # Restore the original working directory
        os.chdir(original_dir)

    return render_score
