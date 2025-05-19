import os
import re
import logging
import subprocess
import tempfile
import asyncio
import json
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
    Renders Angular component code by creating a proper Angular project,
    compiling it with ng serve, and capturing the result with Playwright.
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
            logging.info(f"Creating temporary Angular project for task {task_id}")

            # Determine if the code is a full Angular component
            is_component = "@Component" in angular_code
            component_name = "test-component"

            # Extract component selector if available
            selector_match = re.search(r'selector:\s*[\'"]([^\'"]+)[\'"]', angular_code)
            if selector_match:
                component_name = selector_match.group(1)

            # Setup a minimal Angular project
            os.chdir(tmpdir)

            # Create package.json
            package_json = {
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
                    "typescript": "~5.0.2",
                },
            }
            with open("package.json", "w") as f:
                json.dump(package_json, f, indent=2)

            # Create Angular project structure
            os.makedirs("src/app", exist_ok=True)

            # Create main.ts
            with open("src/main.ts", "w") as f:
                f.write(
                    """
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
"""
                )

            # Create app module
            with open("src/app/app.module.ts", "w") as f:
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
            with open("src/app/app.component.ts", "w") as f:
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
            with open("src/app/test.component.ts", "w") as f:
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
            with open("src/index.html", "w") as f:
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
            with open("angular.json", "w") as f:
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
            with open("tsconfig.json", "w") as f:
                f.write(
                    """
{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": "./",
    "outDir": "./dist/out-tsc",
    "forceConsistentCasingInFileNames": true,
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
            with open("src/polyfills.ts", "w") as f:
                f.write(
                    """
import 'zone.js';
"""
                )

            # Install Angular CLI globally if not already installed
            try:
                subprocess.run(
                    ["npm", "install", "-g", "@angular/cli"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                logging.warning(
                    "Failed to install Angular CLI globally, will try to proceed with local installation"
                )

            # Install dependencies
            logging.info("Installing Angular dependencies...")
            try:
                subprocess.run(
                    ["npm", "install", "--legacy-peer-deps"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to install dependencies: {e}")
                raise

            # Start Angular development server
            logging.info("Starting Angular development server...")
            port = "4200"
            server_process = subprocess.Popen(
                [
                    "npx",
                    "ng",
                    "serve",
                    "--port",
                    port,
                    "--host",
                    "localhost",
                    "--disable-host-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for server to start (this might take some time)
            logging.info("Waiting for Angular server to start...")
            await asyncio.sleep(45)  # Give more time for Angular to compile and start

            # Use Playwright to screenshot
            browser, context, page, playwright = await start_browser()
            try:
                await page.goto(f"http://localhost:{port}", timeout=60000)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(
                    5000
                )  # Extra time for Angular app to render
                screenshot_path = os.path.join(img_output_path_abs, f"{task_id}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                logging.info(f"Angular screenshot saved: {screenshot_path}")
                render_score = 1
            except Exception as e:
                logging.error(f"Angular rendering failed for task {task_id}: {e}")
                # Reset browser resources upon exception
                await page.close()
                await context.close()
                await browser.close()
                await playwright.stop()
                # Restart browser with fresh resources
                browser, context, page, playwright = await start_browser()
            finally:
                await page.close()
                await context.close()
                await browser.close()
                await playwright.stop()

                # Terminate the server
                if server_process:
                    server_process.terminate()
                    try:
                        server_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server_process.kill()
    except Exception as e:
        logging.error(f"Angular setup failed for task {task_id}: {e}")
    finally:
        # Restore the original working directory
        os.chdir(original_dir)

    return render_score
