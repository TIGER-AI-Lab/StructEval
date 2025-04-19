import os
import logging
import asyncio
from render_mermaid import render_mermaid_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_simple_mermaid():
    """Test mermaid rendering with a simple diagram that definitely works"""
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a simplified version of the smart home routine diagram
    task_id = "smart_home_simple"
    mermaid_code = """
    flowchart TD
      detect([Detect Sensor Input])
      decide{Decide: Manual or Auto?}
      actuate[Actuate Devices]
      verify([Verify Outcome])

      detect --> decide
      decide -->|Auto| actuate
      decide -->|Manual| actuate
      actuate --> verify
      verify --> detect
    """
    
    output_path = os.path.join(output_dir, f"{task_id}.png")
    
    logging.info(f"Testing mermaid rendering with simplified code")
    render_score = await render_mermaid_and_screenshot(task_id, mermaid_code, output_path)
    
    if render_score > 0:
        logging.info(f"Mermaid rendering successful! Score: {render_score}, Image saved to {output_path}")
    else:
        logging.error("Mermaid rendering failed.")

if __name__ == "__main__":
    asyncio.run(test_simple_mermaid()) 