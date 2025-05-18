import os
import re
import logging
import subprocess
import tempfile
import asyncio
from .render_utils import start_browser

def extract_angular_component_from_code_tag(generation):
    """Extract code content from <code> tags."""
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    if match:
        code = match.group(1)
    else:
        # 2. Try to extract from ```<output_type>``` fenced block
        code_fence_pattern = rf"```{output_type}\s*(.*?)```"
        match = re.search(code_fence_pattern, generation, re.DOTALL)
        if match:
            code = match.group(1).strip() if match else generation.strip()
        else:
            fence_pattern = r"```\s*(.*?)```"
            match = re.search(fence_pattern, generation, re.DOTALL)
            if match:
                code = match.group(1).strip() if match else generation.strip()
            else:
                code = ""
                logging.warning(f"No correct tag found for task {task_id}")
    return code

async def render_angular_and_screenshot(task_id, angular_code, img_output_path):
    """
    Renders Angular component code by creating a simple HTML page,
    correctly handling both template-only and full component structures.
    """
    # Convert to absolute path first
    img_output_path_abs = os.path.abspath(img_output_path)
    os.makedirs(img_output_path_abs, exist_ok=True)
    render_score = 0
    
    # Store the original working directory
    original_dir = os.getcwd()

    if not angular_code:
        logging.warning(f"No Angular content for task {task_id}")
        return render_score

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            logging.info(f"Creating temporary Angular rendering for task {task_id}")
            
            # Determine if the code is a full Angular component or just a template
            template_html = angular_code
            
            # If it's a Component class, try to extract the template
            template_match = re.search(r'template:\s*`(.*?)`', angular_code, re.DOTALL)
            if template_match:
                template_html = template_match.group(1)
            
            # Handle case where the template is HTML-like Angular syntax (e.g., <app-something>...</app-something>)
            # HTML decode any entities to ensure proper rendering
            template_html = template_html.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&')
            
            # Create a simple HTML file with styling and mock data
            html_path = os.path.join(tmpdir, "index.html")
            with open(html_path, "w") as f:
                f.write(f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Angular Component Render</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding: 20px; }}
    .card {{ 
      border: 1px solid #ddd; 
      border-radius: 4px; 
      padding: 15px; 
      margin-bottom: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .btn, button {{
      background-color: #4CAF50;
      border: none;
      color: white;
      padding: 10px 20px;
      text-align: center;
      text-decoration: none;
      display: inline-block;
      font-size: 16px;
      margin: 4px 2px;
      cursor: pointer;
      border-radius: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    table, th, td {{
      border: 1px solid #ddd;
      padding: 8px;
    }}
    th {{
      background-color: #f2f2f2;
      text-align: left;
    }}
    .itinerary-container {{
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      background-color: #f9f9f9;
    }}
    .action-buttons {{
      margin-top: 20px;
      display: flex;
      gap: 10px;
    }}
    .activity-id {{
      background-color: #333;
      color: white;
      border-radius: 50%;
      padding: 2px 6px;
      margin-left: 8px;
      font-size: 0.8em;
    }}
    ol {{
      padding-left: 20px;
    }}
    ol li {{
      margin-bottom: 10px;
    }}
  </style>
</head>
<body>
  <div id="angular-component">
    {template_html}
  </div>
  
  <script>
    // Simple script to replace Angular bindings with mock data
    document.addEventListener('DOMContentLoaded', function() {{
      const component = document.getElementById('angular-component');
      if (!component) return;
      
      // Replace Angular interpolations with mock values
      replaceInterpolations(component);
      
      // Remove Angular directives
      removeAngularDirectives(component);
    }});
    
    function replaceInterpolations(element) {{
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      let node;
      while (node = walker.nextNode()) {{
        node.textContent = node.textContent.replace(/{{\\s*([^}}]*)\\s*}}/g, 'Sample Value');
      }}
    }}
    
    function removeAngularDirectives(element) {{
      const elements = element.querySelectorAll('*');
      elements.forEach(el => {{
        // Get all attributes
        const attributes = Array.from(el.attributes);
        
        // Remove Angular-specific attributes
        attributes.forEach(attr => {{
          if (attr.name.startsWith('*ng') || 
              attr.name.startsWith('[') || 
              attr.name.startsWith('(') ||
              attr.name.startsWith('ng-')) {{
            el.removeAttribute(attr.name);
          }}
        }});
      }});
    }}
  </script>
</body>
</html>
                """)
            
            # Use a simple HTTP server to serve the files
            port = "4200"
            server = subprocess.Popen(["python", "-m", "http.server", port], 
                                     cwd=tmpdir,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Give the server time to start
            await asyncio.sleep(2)
            
            # Use Playwright to screenshot
            browser, context, page, playwright = await start_browser()
            try:
                await page.goto(f"http://localhost:{port}")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(1000)  # Extra time for any JS to execute
                screenshot_path = os.path.join(img_output_path_abs, f"{task_id}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                logging.info(f"Angular screenshot saved: {screenshot_path}")
                render_score = 1
            except Exception as e:
                logging.error(f"Angular rendering failed for task {task_id}: {e}")
            finally:
                await page.close()
                await context.close()
                await browser.close()
                await playwright.stop()
                server.terminate()
    except Exception as e:
        logging.error(f"Angular setup failed for task {task_id}: {e}")
    finally:
        # Restore the original working directory
        os.chdir(original_dir)

    return render_score
