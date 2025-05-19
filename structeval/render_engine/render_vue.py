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

    Converts all formats to object format that can be used with Vue.createApp.
    """
    # Check if we have code tags
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    if not match:
        # Try without code tags
        vue_code = generation.strip()
    else:
        vue_code = match.group(1).strip()

    # Always decode HTML entities - this is crucial for properly rendering Vue components
    vue_code = html.unescape(vue_code)

    # Check if it's already in object format (starts with a curly brace)
    if vue_code.strip().startswith("{") and vue_code.strip().endswith("}"):
        return vue_code

    # Check if it's in SFC format with <template>, <script>, and <style> tags
    template_match = re.search(r"<template>(.*?)</template>", vue_code, re.DOTALL)
    if template_match:
        template_content = template_match.group(1).strip()
        return "{\n  template: `" + template_content + "`\n}"

    # Final fallback: treat whole code as template (this is a simplification)
    return "{\n  template: `<pre>${escapeTemplate(`" + vue_code + "`)}</pre>`\n}"


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
        processed_vue_code = extract_vue_code_from_tag(vue_code)
        logging.info(f"[{task_id}] Successfully processed Vue component")
    except Exception as e:
        logging.error(f"[{task_id}] Error processing Vue component: {e}")
        processed_vue_code = vue_code  # Use original code as fallback

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

            # For debugging, also write the processed component to a file
            debug_file = os.path.join(img_output_path, f"{task_id}_component.js")
            with open(debug_file, "w") as f:
                f.write(formatted_vue_code)

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
