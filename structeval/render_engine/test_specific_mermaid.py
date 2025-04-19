import os
import json
import logging
import asyncio
from render_mermaid import extract_mermaid_code_from_tag, render_mermaid_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_specific_mermaid_task():
    """Test mermaid rendering for the specific task that was failing"""
    # Load the html.json file
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find the mermaid task with ID 000900
    task = next((t for t in tasks if t.get("task_id") == "000900"), None)
    
    if not task:
        logging.error("Task 000900 not found in html.json")
        return
    
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    task_id = task.get("task_id", "unknown")
    generation = task.get("generation", "")
    logging.info(f"Testing mermaid rendering for task {task_id}")
    
    # Extract mermaid code
    mermaid_code = extract_mermaid_code_from_tag(generation)
    if not mermaid_code:
        logging.error(f"Failed to extract mermaid code from task")
        return
    
    logging.info(f"Extracted mermaid code (first 100 chars): {mermaid_code[:100]}...")
    
    # Render the mermaid code using our updated function
    output_path = os.path.join(output_dir, f"{task_id}.png")
    render_score = await render_mermaid_and_screenshot(task_id, mermaid_code, output_path)
    
    # Update the render score in the task
    task["render_score"] = render_score
    
    # Save the updated tasks back to html.json
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
    
    logging.info(f"Updated render score in {json_file_path}")

if __name__ == "__main__":
    asyncio.run(test_specific_mermaid_task()) 