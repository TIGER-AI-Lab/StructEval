import os
import re
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
    """
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    if not match:
        return None
    
    vue_code = match.group(1).strip()
    
    # Check if it's already in object format (starts with a curly brace)
    if vue_code.strip().startswith('{'):
        return vue_code
    
    # Check if it's in SFC format with <template>, <script>, and <style> tags
    template_match = re.search(r"<template>(.*?)</template>", vue_code, re.DOTALL)
    script_match = re.search(r"<script>(.*?)</script>", vue_code, re.DOTALL)
    
    if template_match and script_match:
        template_content = template_match.group(1).strip()
        script_content = script_match.group(1).strip()
        
        # Extract the component object from the script section
        # It could be in "export default {...}" format
        component_match = re.search(r"export\s+default\s+(\{.*?\}\s*;?)", script_content, re.DOTALL)
        if component_match:
            component_object = component_match.group(1).strip()
            if component_object.endswith(';'):
                component_object = component_object[:-1]  # Remove trailing semicolon
            
            # Add the template directly to the component object
            # First check if it already has a template property
            if "template:" not in component_object:
                # Insert before the closing brace, make sure it has proper commas
                component_object = component_object.rstrip('}')
                if not component_object.endswith(','):
                    component_object += ','
                component_object += '\n  template: `' + template_content + '`\n}'
            
            # Fix missing methods, computed etc.
            # Extract methods from component
            methods_match = re.search(r'methods:\s*{([^}]*)}', component_object, re.DOTALL)
            computed_match = re.search(r'computed:\s*{([^}]*)}', component_object, re.DOTALL)
            
            # Ensure the methods section has proper syntax
            if methods_match:
                methods_section = methods_match.group(1).strip()
                # Make sure each method ends with a comma if it doesn't already
                methods_lines = methods_section.split('\n')
                for i in range(len(methods_lines) - 1):  # Skip the last line
                    line = methods_lines[i].strip()
                    if line and not line.endswith(','):
                        methods_lines[i] = line + ','
                fixed_methods = '\n'.join(methods_lines)
                component_object = component_object.replace(methods_match.group(1), fixed_methods)
            
            # Do the same for computed properties
            if computed_match:
                computed_section = computed_match.group(1).strip()
                computed_lines = computed_section.split('\n')
                for i in range(len(computed_lines) - 1):  # Skip the last line
                    line = computed_lines[i].strip()
                    if line and not line.endswith(','):
                        computed_lines[i] = line + ','
                fixed_computed = '\n'.join(computed_lines)
                component_object = component_object.replace(computed_match.group(1), fixed_computed)
            
            return component_object
        
        # If we couldn't extract the component object, create a minimal one
        logging.warning("Couldn't extract component object from script, creating minimal component")
        return '{\n  template: `' + template_content + '`\n}'
    
    # If all else fails, treat the whole code as template
    logging.warning("Couldn't identify Vue component format, using as template only")
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
    # Change to the specified directory
    os.chdir(directory)
    
    # Create and start the server
    server = HTTPServer(('localhost', port), QuietHTTPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return server

async def render_vue_and_screenshot(task_id, vue_code, img_output_path):
    """
    Renders Vue component code by copying a simplified Vue CDN template,
    injecting the component, and taking a screenshot.
    """
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
            
            # Format the Vue code to fit the template
            formatted_vue_code = f"""
// Template for Vue application
const {{ createApp }} = Vue;

// Vue component from the task
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

            logging.info(f"[{task_id}] Starting Playwright browser...")
            browser, context, page, playwright = await start_browser()
            page.on("console", lambda msg: logging.info(f"[{task_id}] Browser Console ({msg.type}): {msg.text}"))
            logging.info(f"[{task_id}] Playwright browser started.")

            try:
                logging.info(f"[{task_id}] Navigating to page...")
                await page.goto(f"http://localhost:{port}")
                logging.info(f"[{task_id}] Navigation complete. Waiting for network idle...")
                await page.wait_for_load_state("networkidle")
                logging.info(f"[{task_id}] Network idle detected. Taking screenshot...")
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
