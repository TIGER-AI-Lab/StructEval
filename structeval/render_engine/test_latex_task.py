import os
import json
import logging
from render_latex import extract_latex_from_code_tag, render_latex_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_specific_latex_task():
    """Test LaTeX rendering for a specific task"""
    # Load the html.json file
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find the LaTeX task with ID 000600
    task = next((t for t in tasks if t.get("task_id") == "000600"), None)
    
    if not task:
        logging.error("Task 000600 not found in html.json")
        return
    
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    task_id = task.get("task_id", "unknown")
    generation = task.get("generation", "")
    logging.info(f"Testing LaTeX rendering for task {task_id}")
    
    # Extract LaTeX code
    latex_code = extract_latex_from_code_tag(generation)
    if not latex_code:
        logging.error(f"Failed to extract LaTeX from task")
        return
    
    logging.info(f"Extracted LaTeX: {latex_code}")
    
    # Render the LaTeX code using our updated function
    output_path = os.path.join(output_dir, f"{task_id}.png")
    render_score = render_latex_and_screenshot(task_id, latex_code, output_path)
    
    # Update the render score in the task
    task["render_score"] = render_score
    
    # Save the updated tasks back to html.json
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
    
    logging.info(f"Updated render score in {json_file_path}")

if __name__ == "__main__":
    test_specific_latex_task() 