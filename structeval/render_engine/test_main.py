import os
import json
import asyncio
import logging
from main import process_json_file

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_main_with_vue():
    """Test main.py with a Vue example from html.json"""
    # Set up the output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the path to html.json
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    
    # Execute process_json_file with our html.json
    logging.info(f"Testing main.py with Vue example from {json_file_path}")
    await process_json_file(json_file_path, output_dir)
    
    # Check the results
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find Vue tasks (task_id starts with "0016")
    vue_tasks = [task for task in tasks if task.get("task_id", "").startswith("0016")]
    
    if not vue_tasks:
        logging.error("No Vue tasks found in html.json")
        return
    
    # Check the render score
    for task in vue_tasks:
        task_id = task.get("task_id")
        render_score = task.get("render_score", 0)
        logging.info(f"Task {task_id} render score: {render_score}")
        
        # Check if the screenshot was created
        screenshot_path = os.path.join(output_dir, f"{task_id}.png")
        if os.path.exists(screenshot_path):
            file_size = os.path.getsize(screenshot_path)
            logging.info(f"Screenshot created: {screenshot_path} ({file_size} bytes)")
        else:
            logging.error(f"Screenshot not found: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(test_main_with_vue()) 