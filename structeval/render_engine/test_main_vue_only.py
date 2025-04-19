import os
import json
import asyncio
import logging
from render_vue import extract_vue_code_from_tag, render_vue_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_main_vue_only():
    """Test only Vue rendering from html.json"""
    # Set up the output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the path to html.json
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    
    # Load the tasks from html.json
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find Vue tasks (task_id starts with "0016")
    vue_tasks = [task for task in tasks if task.get("task_id", "").startswith("0016")]
    
    if not vue_tasks:
        logging.error("No Vue tasks found in html.json")
        return
    
    # Process Vue tasks only
    for task in vue_tasks:
        task_id = task.get("task_id", "unknown")
        generation = task.get("generation", "")
        
        logging.info(f"Processing Vue task {task_id}")
        
        # Extract Vue code
        vue_code = extract_vue_code_from_tag(generation)
        if not vue_code:
            logging.error(f"Failed to extract Vue code from task {task_id}")
            continue
        
        # Render the Vue component
        render_score = await render_vue_and_screenshot(task_id, vue_code, output_dir)
        
        # Update the render score in the task
        task["render_score"] = render_score
        
        logging.info(f"Task {task_id} render score: {render_score}")
        
        # Check if the screenshot was created
        screenshot_path = os.path.join(output_dir, f"{task_id}.png")
        if os.path.exists(screenshot_path):
            file_size = os.path.getsize(screenshot_path)
            logging.info(f"Screenshot created: {screenshot_path} ({file_size} bytes)")
        else:
            logging.error(f"Screenshot not found: {screenshot_path}")
    
    # Update the html.json file with the new render scores
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
    
    logging.info(f"Updated render scores in {json_file_path}")

if __name__ == "__main__":
    asyncio.run(test_main_vue_only()) 