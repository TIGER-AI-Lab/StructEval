import os
import json
import logging
from render_tikz import extract_tikz_from_code_tag, render_tikz_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_tikz_rendering():
    """Test TikZ rendering from html.json"""
    # Load the html.json file
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find TikZ tasks (task_id starts with "0013")
    tikz_tasks = [task for task in tasks if task.get("task_id", "").startswith("0013")]
    
    if not tikz_tasks:
        logging.error("No TikZ tasks found in html.json")
        return
    
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Process TikZ tasks
    for task in tikz_tasks:
        task_id = task.get("task_id", "unknown")
        generation = task.get("generation", "")
        logging.info(f"Testing TikZ rendering for task {task_id}")
        
        # Extract TikZ code
        tikz_code = extract_tikz_from_code_tag(generation)
        if not tikz_code:
            logging.error(f"Failed to extract TikZ from task")
            continue
        
        logging.info(f"Extracted TikZ code (first 100 chars): {tikz_code[:100]}...")
        
        # Render the TikZ code
        render_score = render_tikz_and_screenshot(task_id, tikz_code, output_dir)
        logging.info(f"TikZ rendering for task {task_id} completed with score: {render_score}")
        
        # Update the render score in the task
        task["render_score"] = render_score
    
    # Save the updated tasks back to html.json
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
    
    logging.info(f"Updated render scores in {json_file_path}")

if __name__ == "__main__":
    test_tikz_rendering() 