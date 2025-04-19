import os
import logging
from render_latex import render_latex_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_pdf2image_rendering():
    """Test if pdf2image rendering works properly"""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a simple test case
    task_id = "test001"
    latex_code = r"$\frac{1}{2} + \int_{0}^{1} x^2 dx$"
    output_path = os.path.join(output_dir, f"{task_id}.png")
    
    logging.info(f"Testing LaTeX rendering with pdf2image for '{latex_code}'")
    render_score = render_latex_and_screenshot(task_id, latex_code, output_path)
    
    if render_score == 1:
        logging.info(f"LaTeX rendering successful! Image saved to {output_path}")
    else:
        logging.error("LaTeX rendering failed.")

if __name__ == "__main__":
    test_pdf2image_rendering() 