import os
import logging
import re
import subprocess
import tempfile
from pdf2image import convert_from_path

def render_latex_to_png(latex_code, output_path, dpi=300):
    """
    Renders LaTeX code to a PNG image using pdflatex + pdf2image.

    Args:
        latex_code (str): The LaTeX code (can be full doc or just snippet).
        output_path (str): Full path to save the PNG file.
        dpi (int): Resolution of the output image.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "doc.tex")
            pdf_path = os.path.join(tmpdir, "doc.pdf")

            # Wrap in a minimal document if not full LaTeX
            if "\\begin{document}" not in latex_code:
                latex_code = (
                    "\\documentclass{article}\n"
                    "\\usepackage{amsmath, tikz}\n"
                    "\\pagestyle{empty}\n"
                    "\\begin{document}\n"
                    f"{latex_code}\n"
                    "\\end{document}"
                )

            with open(tex_path, "w") as f:
                f.write(latex_code)

            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            images = convert_from_path(pdf_path, dpi=dpi)
            if not images:
                raise RuntimeError("No image generated from LaTeX.")

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            images[0].save(output_path, "PNG")
            return True

    except Exception as e:
        print(f"❌ LaTeX render failed: {e}")
        return False

def render_latex_and_screenshot(task_id, latex_code, img_output_path):
    """
    Wrapper that maps your task-based logic to the simpler LaTeX renderer.
    """
    if not latex_code:
        logging.warning(f"No LaTeX content for task {task_id}")
        return 0

    if os.path.splitext(img_output_path)[1] == "":
        os.makedirs(img_output_path, exist_ok=True)
        output_file = os.path.join(img_output_path, f"{task_id}.png")
    else:
        os.makedirs(os.path.dirname(img_output_path) or ".", exist_ok=True)
        output_file = img_output_path

    success = render_latex_to_png(latex_code, output_file)
    if success:
        logging.info(f"LaTeX rendered image saved: {output_file}")
        return 1
    else:
        logging.error(f"LaTeX rendering failed for task {task_id}")
        return 0

def extract_latex_from_code_tag(generation):
    """
    Extract LaTeX code from <code> tags and clean it up.
    Removes control characters and converts double backslashes to single ones.
    """
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    latex_code = match.group(1) if match else None

    if latex_code:
        # Remove control characters (ASCII 0-31, excluding \t, \n, \r)
        latex_code = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', latex_code)

        # Replace every double backslash with a single backslash
        #latex_code = latex_code.replace('\\\\', '\\')

        #logging.info(f"Cleaned LaTeX code: {latex_code}")

    return latex_code
