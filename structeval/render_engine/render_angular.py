import os
import re
import logging
import subprocess
import tempfile
import asyncio
import json
import random
import shutil
import threading
from .render_utils import start_browser


ANGULAR_CACHE_DIR = os.path.join(
    os.path.expanduser("~"), ".cache", "structeval", "angular-render-v16"
)
_ANGULAR_CACHE_LOCK = threading.Lock()


def angular_package_json():
    return {
        "name": "angular-render",
        "version": "0.0.0",
        "scripts": {"start": "ng serve"},
        "dependencies": {
            "@angular/common": "^16.0.0",
            "@angular/compiler": "^16.0.0",
            "@angular/core": "^16.0.0",
            "@angular/forms": "^16.0.0",
            "@angular/platform-browser": "^16.0.0",
            "@angular/platform-browser-dynamic": "^16.0.0",
            "@angular/router": "^16.0.0",
            "rxjs": "~7.8.0",
            "tslib": "^2.3.0",
            "zone.js": "~0.13.0",
        },
        "devDependencies": {
            "@angular-devkit/build-angular": "^16.0.0",
            "@angular/cli": "^16.0.0",
            "@angular/compiler-cli": "^16.0.0",
            "@types/node": "18.19.39",
            "typescript": "~5.0.2",
        },
        "overrides": {
            "@types/node": "18.19.39",
        },
    }


def ensure_angular_dependency_cache():
    os.makedirs(ANGULAR_CACHE_DIR, exist_ok=True)
    package_json_path = os.path.join(ANGULAR_CACHE_DIR, "package.json")
    package_json = angular_package_json()
    package_json_text = json.dumps(package_json, indent=2, sort_keys=True)
    ng_binary = os.path.join(ANGULAR_CACHE_DIR, "node_modules", ".bin", "ng")

    with _ANGULAR_CACHE_LOCK:
        package_json_changed = not os.path.exists(package_json_path) or (
            open(package_json_path, encoding="utf-8").read() != package_json_text
        )
        if package_json_changed:
            with open(package_json_path, "w", encoding="utf-8") as f:
                f.write(package_json_text)

        if package_json_changed or not os.path.exists(ng_binary):
            logging.info("Installing cached Angular dependencies...")
            subprocess.run(
                ["npm", "install", "--legacy-peer-deps", "--prefer-offline"],
                check=True,
                cwd=ANGULAR_CACHE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    return ANGULAR_CACHE_DIR


def extract_angular_component_from_code_tag(generation, output_type="angular", task_id="unknown"):
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
    Renders Angular component code by creating a proper Angular project,
    compiling it with ng serve, and capturing the result with Playwright.
    """
    # Convert to absolute path first
    img_output_path_abs = os.path.abspath(img_output_path)
    os.makedirs(img_output_path_abs, exist_ok=True)
    render_score = 0

    if not angular_code:
        logging.warning(f"No Angular content for task {task_id}")
        return render_score

    # Use a random port to avoid conflicts with previous servers
    port = str(random.randint(4300, 9000))
    server_process = None
    browser = context = page = playwright = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            logging.info(f"Creating temporary Angular project for task {task_id}")

            def project_path(*parts):
                return os.path.join(tmpdir, *parts)

            # Determine if the code is a full Angular component
            is_component = "@Component" in angular_code
            component_name = "test-component"

            # Extract component selector if available
            selector_match = re.search(r'selector:\s*[\'"]([^\'"]+)[\'"]', angular_code)
            if selector_match:
                component_name = selector_match.group(1)

            # Create package.json
            with open(project_path("package.json"), "w") as f:
                json.dump(angular_package_json(), f, indent=2)

            # Create Angular project structure
            os.makedirs(project_path("src", "app"), exist_ok=True)

            # Create main.ts
            with open(project_path("src", "main.ts"), "w") as f:
                f.write(
                    """
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
"""
                )

            # Create app module
            with open(project_path("src", "app", "app.module.ts"), "w") as f:
                f.write(
                    f"""
import {{ NgModule }} from '@angular/core';
import {{ BrowserModule }} from '@angular/platform-browser';
import {{ AppComponent }} from './app.component';
import {{ TestComponent }} from './test.component';

@NgModule({{
  declarations: [
    AppComponent,
    TestComponent
  ],
  imports: [
    BrowserModule
  ],
  providers: [],
  bootstrap: [AppComponent]
}})
export class AppModule {{ }}
"""
                )

            # Create app component
            with open(project_path("src", "app", "app.component.ts"), "w") as f:
                f.write(
                    f"""
import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-root',
  template: `<{component_name}></{component_name}>`
}})
export class AppComponent {{ }}
"""
                )

            # Save the Angular component code
            with open(project_path("src", "app", "test.component.ts"), "w") as f:
                # For a full component, save as-is
                if is_component:
                    # Handle external template/style references
                    angular_code = re.sub(
                        r'templateUrl:\s*[\'"]./[^\'"]*.html[\'"]',
                        "template: `<div>Test Component</div>`",
                        angular_code,
                    )
                    angular_code = re.sub(
                        r"styleUrls:\s*\[[^\]]*\]",
                        "styles: [`div { padding: 20px; }`]",
                        angular_code,
                    )

                    # Change the component class name if needed
                    angular_code = re.sub(
                        r"export class \w+Component",
                        "export class TestComponent",
                        angular_code,
                    )

                    f.write(angular_code)
                else:
                    # For template-only code, create a simple component
                    template = angular_code.replace("`", "\\`").replace("${", "\\${")
                    f.write(
                        f"""
import {{ Component }} from '@angular/core';

@Component({{
  selector: '{component_name}',
  template: `{template}`,
  styles: [`
    div {{ padding: 20px; }}
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
  `]
}})
export class TestComponent {{
  inputText = 'This is a sample text';
  features = [
    'Feature 1',
    'Feature 2',
    'Feature 3'
  ];
  books = [
    {{ title: 'Book 1', price: 19.99 }},
    {{ title: 'Book 2', price: 9.99 }},
    {{ title: 'Book 3', price: 29.99 }}
  ];
}}
"""
                    )

            # Create index.html
            with open(project_path("src", "index.html"), "w") as f:
                f.write(
                    """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Angular Render</title>
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <app-root></app-root>
</body>
</html>
"""
                )

            # Create angular.json
            with open(project_path("angular.json"), "w") as f:
                f.write(
                    """
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "newProjectRoot": "projects",
  "projects": {
    "angular-render": {
      "projectType": "application",
      "schematics": {},
      "root": "",
      "sourceRoot": "src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/angular-render",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.json",
            "assets": [],
            "styles": [],
            "scripts": []
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": {
            "browserTarget": "angular-render:build"
          }
        }
      }
    }
  }
}
"""
                )

            # Create tsconfig.json
            with open(project_path("tsconfig.json"), "w") as f:
                f.write(
                    """
{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": "./",
    "outDir": "./dist/out-tsc",
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "types": [],
    "strict": false,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "sourceMap": true,
    "declaration": false,
    "downlevelIteration": true,
    "experimentalDecorators": true,
    "moduleResolution": "node",
    "importHelpers": true,
    "target": "ES2022",
    "module": "ES2022",
    "useDefineForClassFields": false,
    "lib": [
      "ES2022",
      "dom"
    ]
  },
  "angularCompilerOptions": {
    "enableI18nLegacyMessageIdFormat": false,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "strictTemplates": true
  }
}
"""
                )

            # Create polyfills.ts
            with open(project_path("src", "polyfills.ts"), "w") as f:
                f.write(
                    """
import 'zone.js';
"""
                )

            cache_dir = ensure_angular_dependency_cache()
            cached_node_modules = os.path.join(cache_dir, "node_modules")
            project_node_modules = project_path("node_modules")
            if not os.path.exists(project_node_modules):
                os.symlink(cached_node_modules, project_node_modules, target_is_directory=True)
            package_lock = os.path.join(cache_dir, "package-lock.json")
            if os.path.exists(package_lock):
                shutil.copy2(package_lock, project_path("package-lock.json"))

            # Start Angular development server with output capture for error detection
            logging.info(f"Starting Angular development server on port {port}...")
            server_output_file = os.path.join(tmpdir, "server_output.log")
            with open(server_output_file, "w") as output_file:
                ng_binary = project_path("node_modules", ".bin", "ng")
                server_process = subprocess.Popen(
                    [
                        ng_binary,
                        "serve",
                        "--port",
                        port,
                        "--host",
                        "localhost",
                        "--disable-host-check",
                    ],
                    cwd=tmpdir,
                    stdout=output_file,
                    stderr=output_file,
                )

            # Wait for server to start
            logging.info("Waiting for Angular server to start...")
            start_time = asyncio.get_event_loop().time()
            max_wait_time = 60  # Maximum wait time in seconds
            compiled_successfully = False
            
            # Check for compilation status periodically
            while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Check if server process is still running
                if server_process.poll() is not None:
                    logging.error(f"Angular server process exited with code {server_process.returncode}")
                    break
                
                # Check log file for compilation status
                with open(server_output_file, "r") as f:
                    log_content = f.read()
                    if "Compiled successfully" in log_content or "Compiled successfully." in log_content:
                        logging.info("Angular compilation successful")
                        compiled_successfully = True
                        break
                    elif "Error: " in log_content or "ERROR in" in log_content:
                        logging.error("Angular compilation failed with errors")
                        break

            # If compilation wasn't successful after max wait time, log a warning
            if not compiled_successfully:
                logging.warning(f"Angular compilation status uncertain after {max_wait_time} seconds")

            # Start browser and take screenshot
            browser, context, page, playwright = await start_browser()
            
            try:
                await page.goto(f"http://localhost:{port}", timeout=30000)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)  # Wait for Angular to render
                
                page_text = await page.locator("body").inner_text(timeout=5000)
                has_error_page = (
                    not compiled_successfully
                    or "Cannot GET /" in page_text
                    or "Error:" in page_text
                    or "Failed to compile" in page_text
                )
                if has_error_page:
                    logging.error(f"Angular rendering shows compilation error for task {task_id}")
                    # Still take screenshot to document the error
                    screenshot_path = os.path.join(img_output_path_abs, f"{task_id}_error.png")
                else:
                    screenshot_path = os.path.join(img_output_path_abs, f"{task_id}.png")
                    render_score = 1
                
                await page.screenshot(path=screenshot_path, full_page=True)
                logging.info(f"Angular screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logging.error(f"Angular rendering failed for task {task_id}: {e}")
            finally:
                # Ensure browser is fully cleaned up
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                if playwright:
                    await playwright.stop()

                # Terminate the server with force
                if server_process:
                    server_process.terminate()
                    try:
                        server_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server_process.kill()
                        server_process.wait(timeout=5)
                    
                    # Additional cleanup - kill any remaining process on the port
                    try:
                        subprocess.run(
                            ["fuser", "-k", f"{port}/tcp"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    except:
                        pass
    except Exception as e:
        logging.error(f"Angular setup failed for task {task_id}: {e}")
    finally:
        # Extra cleanup outside the tempdir context
        # Ensure browser is closed
        if browser or context or page or playwright:
            try:
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                if playwright:
                    await playwright.stop()
            except Exception as e:
                logging.error(f"Error cleaning up browser: {e}")
                
        # Ensure server is terminated
        if server_process and server_process.poll() is None:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
            except:
                try:
                    server_process.kill()
                except:
                    pass
    return render_score
