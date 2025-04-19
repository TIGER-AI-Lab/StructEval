import os
import json
import asyncio
import logging
from render_vue import extract_vue_code_from_tag, render_vue_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_vue_rendering():
    # Set up the output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the html.json file to get Vue samples
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find Vue tasks (task_id starts with "0016")
    vue_tasks = [task for task in tasks if task.get("task_id", "").startswith("0016")]
    
    if not vue_tasks:
        logging.error("No Vue tasks found in html.json")
        return
    
    # Test with the first Vue task
    test_task = vue_tasks[0]
    task_id = test_task.get("task_id", "test")
    generation = test_task.get("generation", "")
    
    # Extract Vue code
    vue_code = extract_vue_code_from_tag(generation)
    if not vue_code:
        logging.error("Failed to extract Vue code from task")
        return
    
    logging.info(f"Extracted Vue code for task {task_id}")
    logging.info(f"Vue code snippet: {vue_code[:100]}...")
    
    # Render the Vue component
    render_score = await render_vue_and_screenshot(task_id, vue_code, output_dir)
    
    logging.info(f"Rendering completed with score: {render_score}")
    logging.info(f"Check the output directory: {output_dir}")

if __name__ == "__main__":
    asyncio.run(test_vue_rendering()) 