import os
import logging
from render_latex import render_latex_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_with_fixed_latex():
    """Test LaTeX rendering with a known working LaTeX equation"""
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Use a known working LaTeX equation
    task_id = "test002"
    latex_code = r"\begin{equation} \int_{0}^{1} \, \left( \frac{x^2}{1 + e^{x}} \right) \, dx \end{equation}"
    output_path = os.path.join(output_dir, f"{task_id}.png")
    
    logging.info(f"Testing LaTeX rendering with fixed equation: {latex_code}")
    render_score = render_latex_and_screenshot(task_id, latex_code, output_path)
    
    if render_score == 1:
        logging.info(f"LaTeX rendering successful! Image saved to {output_path}")
    else:
        logging.error("LaTeX rendering failed.")

if __name__ == "__main__":
    test_with_fixed_latex() 