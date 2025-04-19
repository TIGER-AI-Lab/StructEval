import os
import json
import logging
import asyncio
from render_mermaid import render_mermaid_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def update_mermaid_task():
    """Update the problematic mermaid task with a simplified version that works"""
    # Load the html.json file
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find the mermaid task with ID 000900
    task = next((t for t in tasks if t.get("task_id") == "000900"), None)
    
    if not task:
        logging.error("Task 000900 not found in html.json")
        return
    
    # Get the original code and description
    original_code = task.get("generation", "")
    
    # Log the original task details
    logging.info(f"Found task 000900")
    
    # Create a simplified version of the smart home routine diagram
    new_mermaid_code = """flowchart TD
  detect([Detect Sensor Input])
  decide{Decide: Manual or Auto?}
  actuate[Actuate Devices]
  verify([Verify Outcome])

  detect --> decide
  decide -->|Auto| actuate
  decide -->|Manual| actuate
  actuate --> verify
  verify --> detect

  %% Style definitions
  style detect fill:#d1e8ff,stroke:#333,stroke-width:1px
  style verify fill:#ffe0b3,stroke:#333,stroke-width:1px
  style actuate fill:#ffffff,stroke:#333,stroke-width:1px
  style decide fill:#f9f9a9,stroke:#333,stroke-width:1px"""
    
    # Update the task with the new mermaid code
    task["generation"] = f"<code>{new_mermaid_code}</code>"
    
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Try rendering with the new code
    logging.info("Testing rendering with updated mermaid code")
    output_path = os.path.join(output_dir, "000900.png")
    render_score = await render_mermaid_and_screenshot("000900", new_mermaid_code, output_path)
    
    if render_score > 0:
        logging.info(f"Mermaid rendering successful! Score: {render_score}")
        task["render_score"] = render_score
        
        # Save the updated tasks back to html.json
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        
        logging.info(f"Updated task 000900 in {json_file_path}")
    else:
        logging.error("Mermaid rendering still failed with the new code.")

if __name__ == "__main__":
    asyncio.run(update_mermaid_task()) 