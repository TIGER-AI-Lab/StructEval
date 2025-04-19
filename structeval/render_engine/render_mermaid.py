import os
import re
import json  # Import json for escaping
import logging
from render_utils import start_browser

def extract_mermaid_code_from_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_mermaid_and_screenshot(task_id, mermaid_code, img_output_path):
    """
    Renders Mermaid diagram in a headless browser and takes a screenshot.
    """
    # Handle path as either directory or file
    if os.path.splitext(img_output_path)[1] == '':  # No file extension, treat as directory
        os.makedirs(img_output_path, exist_ok=True)
        screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
    else:  # Has file extension, treat as full file path
        os.makedirs(os.path.dirname(img_output_path) or '.', exist_ok=True)
        screenshot_path = img_output_path

    render_score = 0

    if not mermaid_code:
        logging.warning(f"No Mermaid content for task {task_id}")
        return render_score

    mermaid_code = mermaid_code.strip()
    # Escape the code for safe embedding in JavaScript
    escaped_mermaid_code = json.dumps(mermaid_code)

    # Improved HTML template with Mermaid support
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Mermaid Render</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      background-color: #ffffff;
      font-family: Arial, sans-serif;
    }}
    #mermaid-container {{
      min-height: 100px;
      min-width: 300px;
      padding: 20px;
      border: 1px solid #ccc;
      background: #f8f8f8;
      display: block;
    }}
    .render-status {{
      margin-top: 20px;
      padding: 10px;
      border-radius: 4px;
    }}
    .render-success {{
      background-color: #dff0d8;
      color: #3c763d;
    }}
    .render-error {{
      background-color: #f2dede;
      color: #a94442;
    }}
  </style>
</head>
<body>
  <div id="mermaid-container"></div>
  <div id="render-status" class="render-status"></div>

  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    
    const mermaidCode = {escaped_mermaid_code};
    const container = document.getElementById('mermaid-container');
    const status = document.getElementById('render-status');
    
    // Set a flag in window object to signal render completion
    window.mermaidRendered = false;
    window.mermaidError = null;

    try {{
      console.log('Mermaid code received by JS:', mermaidCode);
      
      // Initialize mermaid with explicit config
      mermaid.initialize({{ 
        startOnLoad: false,
        securityLevel: 'loose',
        theme: 'default'
      }});
      
      // Render the diagram
      const renderAsync = async () => {{
        try {{
          const {{ svg }} = await mermaid.render('mermaid-graph', mermaidCode);
          container.innerHTML = svg;
          console.log('Mermaid rendering successful');
          status.textContent = 'Rendering completed successfully!';
          status.className = 'render-status render-success';
          window.mermaidRendered = true;
        }} catch (e) {{
          console.error('Mermaid rendering failed:', e);
          container.innerHTML = `<pre>Syntax error in mermaid diagram:\\n${{e.str || e.message}}</pre>`;
          status.textContent = `Error: ${{e.str || e.message}}`;
          status.className = 'render-status render-error';
          window.mermaidError = e.message || 'Unknown error';
        }}
      }};
      
      // Execute rendering
      renderAsync();
    }} catch (e) {{
      console.error('Script execution error:', e);
      status.textContent = `Script Error: ${{e.message}}`;
      status.className = 'render-status render-error';
      window.mermaidError = e.message;
    }}
  </script>
</body>
</html>
"""

    browser, context, page, playwright = await start_browser()
    
    # Capture console logs from the page
    page.on("console", lambda msg: logging.info(f"Browser Console ({msg.type}): {msg.text}"))
    
    try:
        # Set content and wait for initial load
        await page.set_content(html_template)
        
        # Wait for network activity to settle
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # Wait for rendering to complete using the window flag
        try:
            # Poll for rendering completion
            await page.wait_for_function("""
                () => window.mermaidRendered === true || window.mermaidError !== null
            """, timeout=10000)
            
            # Check if there was an error
            error = await page.evaluate("window.mermaidError")
            if error:
                logging.error(f"[{task_id}] Mermaid rendering error: {error}")
                render_score = 0
            else:
                logging.info(f"[{task_id}] Mermaid rendering completed successfully")
                render_score = 1
        except Exception as wait_error:
            logging.warning(f"[{task_id}] Timeout waiting for mermaid rendering: {wait_error}")
            # We'll still try to take a screenshot
        
        # Additional wait to ensure SVG is fully rendered
        await page.wait_for_timeout(1000)
        
        # Take screenshot - try diagram element first
        try:
            logging.info(f"[{task_id}] Taking screenshot...")
            
            # Try to get the mermaid-container element
            container = await page.query_selector('#mermaid-container')
            
            if container:
                # Check if the container has content
                container_html = await container.inner_html()
                if container_html.strip() and '<svg' in container_html:
                    logging.info(f"[{task_id}] Container has SVG content, taking element screenshot")
                    
                    # Force a min-height to ensure element is visible
                    await page.evaluate("""
                        document.querySelector('#mermaid-container').style.minHeight = '200px';
                        document.querySelector('#mermaid-container svg').style.display = 'block';
                    """)
                    
                    # Take screenshot of the element
                    await container.screenshot(path=screenshot_path)
                    logging.info(f"[{task_id}] Element screenshot saved to {screenshot_path}")
                else:
                    logging.warning(f"[{task_id}] Container empty or no SVG, taking full page screenshot")
                    await page.screenshot(path=screenshot_path)
            else:
                logging.warning(f"[{task_id}] Container not found, taking full page screenshot")
                await page.screenshot(path=screenshot_path)
                
            # If render_score is still 0 but we got a screenshot, set to partial success
            if render_score == 0:
                render_score = 0.5
                
        except Exception as screenshot_error:
            logging.error(f"[{task_id}] Screenshot failed: {screenshot_error}")
            # Try one last time with full page screenshot
            try:
                await page.screenshot(path=screenshot_path)
                logging.info(f"[{task_id}] Full page screenshot saved as fallback")
                if render_score == 0:
                    render_score = 0.5  # Partial success
            except Exception as e:
                logging.error(f"[{task_id}] Full page screenshot also failed: {e}")
                render_score = 0
    
    except Exception as e:
        logging.error(f"[{task_id}] Mermaid rendering process failed: {e}")
        render_score = 0
    
    finally:
        # Clean up
        try:
            await page.close()
            await context.close()
            await browser.close()
            await playwright.stop()
            logging.info(f"[{task_id}] Browser resources cleaned up")
        except Exception as cleanup_error:
            logging.error(f"[{task_id}] Error during browser cleanup: {cleanup_error}")

    return render_score
