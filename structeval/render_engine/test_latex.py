import os
import json
import logging
import tempfile
import subprocess
from render_latex import extract_latex_from_code_tag, render_latex_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_latex_packages():
    """Test if LaTeX packages are properly installed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tex_path = os.path.join(tmpdir, "test.tex")
        
        # Create a minimal LaTeX document with standalone package
        minimal_latex = r"""
\documentclass{article}
\usepackage{amsmath}
\begin{document}
$E = mc^2$
\end{document}
"""
        with open(test_tex_path, "w") as f:
            f.write(minimal_latex)
        
        logging.info("Testing basic LaTeX packages...")
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, test_tex_path],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logging.info("Basic LaTeX setup is working")
        else:
            logging.error(f"Basic LaTeX test failed: {result.stderr}")
            
        # Test the standalone package
        standalone_latex = r"""
\documentclass{standalone}
\usepackage{amsmath}
\begin{document}
$E = mc^2$
\end{document}
"""
        with open(test_tex_path, "w") as f:
            f.write(standalone_latex)
        
        logging.info("Testing standalone LaTeX package...")
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, test_tex_path],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logging.info("Standalone LaTeX package is working")
        else:
            logging.error(f"Standalone LaTeX package test failed: {result.stderr}")

def test_latex_rendering():
    """Test LaTeX rendering from html.json"""
    # Load the html.json file
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find LaTeX tasks (task_id starts with "0006")
    latex_tasks = [task for task in tasks if task.get("task_id", "").startswith("0006")]
    
    if not latex_tasks:
        logging.error("No LaTeX tasks found in html.json")
        return
    
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Process LaTeX tasks
    for task in latex_tasks:
        task_id = task.get("task_id", "unknown")
        generation = task.get("generation", "")
        logging.info(f"Testing LaTeX rendering for task {task_id}")
        
        # Extract LaTeX code
        latex_code = extract_latex_from_code_tag(generation)
        if not latex_code:
            logging.error(f"Failed to extract LaTeX from task")
            continue
        
        logging.info(f"Extracted LaTeX: {latex_code}")
        
        # Render the LaTeX code using our updated function
        output_path = os.path.join(output_dir, f"{task_id}.png")
        render_score = render_latex_and_screenshot(task_id, latex_code, output_path)
        
        # Update the render score in the task
        task["render_score"] = render_score
    
    # Save the updated tasks back to html.json
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
    
    logging.info(f"Updated render scores in {json_file_path}")

def update_render_latex():
    """Print code for an updated render_latex.py file"""
    updated_code = """
import os
import logging
import re
import subprocess
import tempfile

def extract_latex_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

def render_latex_and_screenshot(task_id, latex_code, img_output_path):
    \"\"\"
    Renders LaTeX code to a PNG image using pdflatex and ImageMagick (convert).
    Returns 1 if successful, 0 otherwise.
    \"\"\"
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not latex_code:
        logging.warning(f"No LaTeX content for task {task_id}")
        return render_score

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "temp.tex")
            pdf_path = os.path.join(tmpdir, "temp.pdf")
            png_path = os.path.join(img_output_path, f"{task_id}.png")

            # Check if the code already includes a document environment
            has_document_env = "\\begin{document}" in latex_code and "\\end{document}" in latex_code
            has_documentclass = "\\documentclass" in latex_code
            
            # Write LaTeX content to file
            with open(tex_path, "w") as f:
                if has_document_env and has_documentclass:
                    # The code is a complete LaTeX document
                    f.write(latex_code)
                else:
                    # Wrap the code in a minimal document using article class (more compatible than standalone)
                    f.write(f"\\documentclass{{article}}\\n\\usepackage{{amsmath}}\\n\\pagestyle{{empty}}\\n\\begin{{document}}\\n{latex_code}\\n\\end{{document}}")

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
                    logging.error(f"[{task_id}] pdflatex stdout:\\n{pdflatex_result.stdout.strip()}")
                if pdflatex_result.stderr:
                    logging.error(f"[{task_id}] pdflatex stderr:\\n{pdflatex_result.stderr.strip()}")
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
                 filtered_stderr = "\\n".join(line for line in convert_result.stderr.splitlines() 
                                            if "deprecated in IMv7" not in line)
                 if filtered_stderr.strip():
                    logging.warning(f"[{task_id}] Convert stderr: {filtered_stderr.strip()}")

            logging.info(f"LaTeX rendered image saved: {png_path}")
            render_score = 1
    except Exception as e:
        logging.error(f"LaTeX rendering failed for {task_id}: {e}")

    return render_score
"""
    logging.info("Here's the updated render_latex.py code:")
    print(updated_code)

if __name__ == "__main__":
    test_latex_packages()
    test_latex_rendering()
    update_render_latex() 