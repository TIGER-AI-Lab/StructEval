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
VUE_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vue_template")

def extract_vue_code_from_tag(generation):
    """
    Extract Vue code from a code tag. Handles both object format and Single File Component format.
    For SFC format, converts it to object format that can be used with Vue.createApp.
    
    Improved to handle various edge cases and better clean HTML entities.
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
    if vue_code.strip().startswith('{'):
        return vue_code
    
    # Check if it's in SFC format with <template>, <script>, and <style> tags
    template_match = re.search(r"<template>(.*?)</template>", vue_code, re.DOTALL)
    script_match = re.search(r"<script>(.*?)</script>", vue_code, re.DOTALL)
    
    if template_match:
        template_content = template_match.group(1).strip()
        
        # If we have a script section, try to extract the component object
        if script_match:
            script_content = script_match.group(1).strip()
            
            # Extract the component object from the <script> section
            if "export default" in script_content:
                try:
                    comp = script_content.split("export default", 1)[1].strip()
                    # Drop a trailing semicolon, if present
                    if comp.endswith(";"):
                        comp = comp[:-1].rstrip()
                    
                    # Ensure it starts with "{" – otherwise we bail out
                    if comp.lstrip().startswith("{"):
                        component_object = comp

                        # Inject the template property if missing
                        if "template:" not in component_object:
                            component_object = component_object.rstrip("}")
                            if not component_object.endswith(","):
                                component_object += ","
                            component_object += f"\n  template: `{template_content}`\n}}"

                        return component_object
                except Exception as e:
                    logging.warning(f"Error extracting component object: {e}")
            
            # If we couldn't extract the component object properly, create a basic one
            logging.warning("Couldn't extract component object from script, creating minimal component")
        
        # Create a minimal component with just the template
        return '{\n  template: `' + template_content + '`\n}'
    
    # If all else fails, treat the whole code as template
    logging.warning("Couldn't identify Vue component format, using as template only")
    
    # Handle common issues with Vue templates
    # 1. Fix unclosed curly braces in template strings
    # 2. Replace problematic characters that might cause rendering issues
    # 3. Limit component size to avoid memory issues
    
    # Simplify very large components by keeping just the essential parts
    if len(vue_code) > 5000:
        logging.warning("Vue component is very large, simplifying for better rendering")
        vue_code = vue_code[:5000]  # Limit size to avoid memory issues
        
    # Ensure HTML structures are balanced
    vue_code = vue_code.replace("&copy;", "©")
        
    return '{\n  template: `' + vue_code + '`\n}'

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
        s.bind(('', 0))
        return s.getsockname()[1]

class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    """A quieter HTTP request handler that doesn't log every request"""
    def log_message(self, format, *args):
        pass  # Suppress log messages

def start_http_server(directory, port):
    """Start a simple HTTP server in a separate thread"""
    os.chdir(directory)                       # stay here until cleanup
    server = HTTPServer(('localhost', port), QuietHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

async def render_vue_and_screenshot(task_id, vue_code, img_output_path):
    """
    Renders Vue component code by copying a simplified Vue CDN template,
    injecting the component, and taking a screenshot.
    
    Improved to handle complex Vue components and provide better error recovery.
    """
    img_output_path = os.path.abspath(img_output_path)   # <— make path absolute
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not vue_code:
        logging.warning(f"No Vue content for task {task_id}")
        return render_score

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
            
            # Format the Vue code to fit the template - use a simplified approach for more reliable rendering
            formatted_vue_code = f"""
// Template for Vue application
const {{ createApp }} = Vue;

// Vue component from the task - simplified for rendering
const App = {vue_code};

// Mount the app
const app = createApp(App);
app.mount('#app');
"""
            
            with open(app_js_path, "w") as f:
                f.write(formatted_vue_code)
            logging.info(f"[{task_id}] Component code injected.")
            
            # Find a free port and start the HTTP server
            port = find_free_port()
            logging.info(f"[{task_id}] Starting Python HTTP server on port {port}...")
            server = start_http_server(project_dir, port)
            logging.info(f"[{task_id}] Server started on port {port}")

            # Set a longer timeout for rendering complex Vue components
            logging.info(f"[{task_id}] Starting Playwright browser...")
            browser, context, page, playwright = await start_browser()
            page.on("console", lambda msg: logging.info(f"[{task_id}] Browser Console ({msg.type}): {msg.text}"))
            logging.info(f"[{task_id}] Playwright browser started.")

            try:
                logging.info(f"[{task_id}] Navigating to page...")
                await page.goto(f"http://localhost:{port}", timeout=60000)  # Increase timeout to 60 seconds
                logging.info(f"[{task_id}] Navigation complete. Waiting for network idle...")
                
                # Longer wait time for complex Vue components with many elements
                await page.wait_for_load_state("networkidle", timeout=60000)
                logging.info(f"[{task_id}] Network idle detected. Taking screenshot...")
                
                # Add a small delay to ensure Vue has properly rendered everything
                await asyncio.sleep(1)
                
                screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                logging.info(f"[{task_id}] Vue screenshot saved: {screenshot_path}")
                render_score = 1
            except Exception as e:
                logging.error(f"[{task_id}] Vue rendering failed: {e}")
            finally:
                logging.info(f"[{task_id}] Starting Vue cleanup...")
                logging.info(f"[{task_id}] Closing Playwright page...")
                await page.close()
                logging.info(f"[{task_id}] Closing Playwright context...")
                await context.close()
                logging.info(f"[{task_id}] Closing Playwright browser...")
                await browser.close()
                logging.info(f"[{task_id}] Stopping Playwright...")
                await playwright.stop()
                if server:
                    logging.info(f"[{task_id}] Shutting down HTTP server...")
                    server.shutdown()
                logging.info(f"[{task_id}] Vue cleanup finished.")
    except Exception as e:
        logging.error(f"Vue setup failed for task {task_id}: {e}")
    finally:
        # Restore the original working directory
        os.chdir(original_dir)

    return render_score
