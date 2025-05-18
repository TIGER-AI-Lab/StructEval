# render_vue.py
import os, re, asyncio, html, logging, textwrap
from pathlib import Path
from playwright.async_api import async_playwright
from .render_utils import start_browser, close_browser     

# ------------------------------------------------------------
def extract_vue_from_code_tag(generation: str) -> str | None:
    """
    Pull everything between <code> … </code> and return it as a raw string.
    The content is still HTML-escaped (&lt;template&gt; etc.).
    """
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

# ------------------------------------------------------------
def _build_preview_html(sfc_escaped: str) -> str:
    """
    Given the HTML-escaped SFC, return a complete preview page that:
       • loads Vue from a CDN
       • mounts the supplied component
    """
    sfc = html.unescape(sfc_escaped)           # &lt; → <
    # Escape back-ticks so the string can live inside a JS template literal
    safe_js_sfc = sfc.replace("`", "\\`")

    return textwrap.dedent(f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Vue Preview</title>
        <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
        <style>
          html,body{{margin:0;padding:32px;font-family:Arial,Helvetica,sans-serif}}
        </style>
      </head>
      <body>
        <div id="app"></div>

        <script type="module">
          // --- extract <template> and <script> blocks -------------------
          const sfc = `{safe_js_sfc}`;
          const tplMatch = /<template>([\\s\\S]*?)<\\/template>/i.exec(sfc);
          const jsMatch  = /<script>([\\s\\S]*?)<\\/script>/i.exec(sfc);

          const template = tplMatch ? tplMatch[1] : "<h2>⚠️ No &lt;template&gt;</h2>";
          const scriptSrc = jsMatch ? jsMatch[1] : "export default {{}}";

          // Evaluate the script part to get component options
          let options = {{}};
          try {{
            const exports = {{}};
            const module  = {{ exports }};
            (new Function(scriptSrc))(exports, module);
            options = module.exports || exports.default || exports || {{}};
          }} catch (e) {{
            options = {{ template: `<pre style='color:red'>${{e}}</pre>` }};
          }}

          options.template = template;
          Vue.createApp(options).mount("#app");
        </script>
      </body>
    </html>
    """)

# ------------------------------------------------------------
async def render_vue_and_screenshot(task_id: str,
                                    generation: str,
                                    img_output_path: str,
                                    headless: bool = True) -> float:
    """
    • Extracts the Vue SFC from <code>…</code> tags in `generation`
    • Builds a wrapper page, renders with Playwright, and captures a full-page PNG
    • Returns 1.0 on success, 0.0 on failure
    """
    vue_raw = extract_vue_from_code_tag(generation)
    if not vue_raw:
        logging.warning(f"[{task_id}] No Vue <code> block found.")
        return 0.0

    html_doc = _build_preview_html(vue_raw)

    browser, context, page, pw = await start_browser(headless=headless)
    Path(img_output_path).mkdir(parents=True, exist_ok=True)
    score = 0.0

    try:
        await page.set_content(html_doc)
        await page.wait_for_load_state("load")
        # Give Vue a moment to mount
        await asyncio.sleep(0.5)

        shot_path = os.path.join(img_output_path, f"{task_id}.png")
        await page.screenshot(path=shot_path, full_page=True)
        logging.info(f"[{task_id}] Vue screenshot saved → {shot_path}")
        score = 1.0
    except Exception as e:
        logging.error(f"[{task_id}] Vue render error: {e}")
    finally:
        await close_browser(browser, context, page, pw)

    return score