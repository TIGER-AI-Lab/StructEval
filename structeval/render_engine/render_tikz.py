import os
import re
import logging
import tempfile
import subprocess

def extract_tikz_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

def render_tikz_and_screenshot(task_id, tikz_code, img_output_path):
    """
    Renders TiKZ code to PNG using LaTeX (pdflatex) and ImageMagick (convert).
    Returns 1 if successful, 0 otherwise.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not tikz_code:
        logging.warning(f"No TiKZ content for task {task_id}")
        return render_score

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "temp.tex")
            pdf_path = os.path.join(tmpdir, "temp.pdf")
            png_path = os.path.join(img_output_path, f"{task_id}.png")

            # Check if the code already includes a document environment
            has_document_env = "\\begin{document}" in tikz_code and "\\end{document}" in tikz_code
            has_documentclass = "\\documentclass" in tikz_code
            
            # Prepare the LaTeX document
            if has_document_env and has_documentclass:
                latex_document = tikz_code
            else:
                # Wrap TiKZ code in a LaTeX document - using article class as it's more widely available
                latex_document = f"""
\\documentclass[tikz,border=10pt]{{article}}
\\usepackage{{tikz}}
\\pagestyle{{empty}}
\\begin{{document}}
{tikz_code}
\\end{{document}}
"""

            with open(tex_path, "w") as f:
                f.write(latex_document)

            # Compile LaTeX to PDF
            # Run without check=True, capture output, check returncode manually
            pdflatex_result = subprocess.run([
                                "pdflatex", 
                                "-interaction=nonstopmode", 
                                "-output-directory", tmpdir, # Ensure output goes to tmpdir
                                tex_path
                                ],
                                cwd=tmpdir, 
                                capture_output=True, 
                                text=True # Removed check=True
                                )
            # Log output if pdflatex failed
            if pdflatex_result.returncode != 0:
                logging.error(f"[{task_id}] pdflatex failed with exit code {pdflatex_result.returncode}")
                if pdflatex_result.stdout:
                    logging.error(f"[{task_id}] pdflatex stdout:\n{pdflatex_result.stdout.strip()}")
                if pdflatex_result.stderr:
                    logging.error(f"[{task_id}] pdflatex stderr:\n{pdflatex_result.stderr.strip()}")
                # Raise an exception to prevent continuing to magick step
                raise subprocess.CalledProcessError(pdflatex_result.returncode, pdflatex_result.args, 
                                                    output=pdflatex_result.stdout, stderr=pdflatex_result.stderr)
            elif pdflatex_result.stderr: # Log stderr even on success if present (warnings etc)
                 logging.warning(f"[{task_id}] pdflatex stderr (success): {pdflatex_result.stderr.strip()}")

            # Convert PDF to PNG using convert (ImageMagick)
            # Capture stderr for convert
            convert_result = subprocess.run([
                               "convert", 
                               "-density", "300", 
                               pdf_path, 
                               "-background", "white", "-alpha", "remove", "-alpha", "off", # Add background flags
                               "-quality", "90", 
                               png_path
                            ],
                            check=True, capture_output=True, text=True)
            if convert_result.stderr:
                 # Filter out the specific deprecation warning, but log other warnings/errors
                 filtered_stderr = "\n".join(line for line in convert_result.stderr.splitlines() 
                                            if "deprecated in IMv7" not in line)
                 if filtered_stderr.strip():
                    logging.warning(f"[{task_id}] Convert stderr: {filtered_stderr.strip()}")

            logging.info(f"TiKZ image rendered and saved: {png_path}")
            render_score = 1
    except Exception as e:
        logging.error(f"TiKZ rendering failed for {task_id}: {e}")

    return render_score
