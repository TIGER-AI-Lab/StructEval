import os
import re
import logging
import tempfile
import subprocess

def extract_typst_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

def render_typst_and_screenshot(task_id, typst_code, img_output_path):
    """
    Renders Typst code to PNG using the typst compiler and ImageMagick.
    Returns 1 if successful, 0 otherwise.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not typst_code:
        logging.warning(f"No Typst content for task {task_id}")
        return render_score

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            typ_path = os.path.join(tmpdir, "temp.typ")
            pdf_path = os.path.join(tmpdir, "temp.pdf")
            png_path = os.path.join(img_output_path, f"{task_id}.png")

            # Save Typst code to file
            with open(typ_path, "w") as f:
                f.write(typst_code)

            # Compile to PDF
            # Capture stderr for typst compile
            compile_result = subprocess.run(["typst", "compile", typ_path, pdf_path],
                           check=True, capture_output=True, text=True)
            if compile_result.stderr:
                 logging.warning(f"[{task_id}] Typst compile stderr: {compile_result.stderr}")

            # Convert PDF to PNG
            # Capture stderr for convert
            convert_result = subprocess.run([
                               "magick", 
                               "-density", "300", 
                               pdf_path, 
                               "-background", "white", "-alpha", "remove", "-alpha", "off",
                               "-quality", "90", 
                               png_path
                           ],
                           check=True, capture_output=True, text=True)
            if convert_result.stderr:
                 # Filter out the specific deprecation warning, but log other warnings/errors
                 filtered_stderr = "\n".join(line for line in convert_result.stderr.splitlines() 
                                            if "deprecated in IMv7" not in line)
                 if filtered_stderr.strip():
                    logging.warning(f"[{task_id}] Magick stderr: {{filtered_stderr.strip()}}")

            logging.info(f"Typst rendered image saved: {png_path}")
            render_score = 1
    except Exception as e:
        logging.error(f"Typst rendering failed for {task_id}: {e}")

    return render_score
