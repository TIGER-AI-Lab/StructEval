import os
import re
import shutil
import logging
import subprocess
import tempfile
import asyncio
from render_utils import start_browser

def extract_angular_component_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

async def render_angular_and_screenshot(task_id, angular_code, img_output_path):
    """
    Renders Angular component code by creating a temporary Angular project,
    injecting the component, building the app, and taking a screenshot.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not angular_code:
        logging.warning(f"No Angular content for task {task_id}")
        return render_score

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = os.path.join(tmpdir, "temp-app")
            os.chdir(tmpdir)

            # Step 1: Create new Angular app
            subprocess.run(["npx", "-y", "@angular/cli", "new", "temp-app", "--defaults", "--skip-git", "--skip-install"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            os.chdir(project_dir)

            # Step 2: Install dependencies
            subprocess.run(["npm", "install"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Step 3: Overwrite app.component.html with the user's Angular template code
            app_html = os.path.join(project_dir, "src", "app", "app.component.html")
            with open(app_html, "w") as f:
                f.write(angular_code)

            # Step 4: Build the app
            subprocess.run(["npx", "ng", "build"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Step 5: Serve the built app using http-server
            dist_path = os.path.join(project_dir, "dist", "temp-app")
            port = "4201"
            server = subprocess.Popen(["npx", "http-server", dist_path, "-p", port], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Step 6: Use Playwright to screenshot the page
            await asyncio.sleep(2)  # give server time to start
            browser, context, page, playwright = await start_browser()
            try:
                await page.goto(f"http://localhost:{port}")
                await page.wait_for_load_state("networkidle")
                screenshot_path = os.path.join(img_output_path, f"{task_id}.png")
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

    return render_score
