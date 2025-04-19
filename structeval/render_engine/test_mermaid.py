import os
import logging
import asyncio
from render_mermaid import render_mermaid_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_mermaid_rendering():
    """Test mermaid rendering with a simple graph."""
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Simple mermaid graph example
    task_id = "test_mermaid"
    mermaid_code = """
    graph TD
        A[Start] --> B{Is it?}
        B -- Yes --> C[OK]
        C --> D[Rethink]
        D --> B
        B -- No --> E[End]
    """
    
    output_path = os.path.join(output_dir, f"{task_id}.png")
    
    logging.info(f"Testing mermaid rendering with simple graph")
    render_score = await render_mermaid_and_screenshot(task_id, mermaid_code, output_path)
    
    if render_score > 0:
        logging.info(f"Mermaid rendering successful! Score: {render_score}, Image saved to {output_path}")
    else:
        logging.error("Mermaid rendering failed.")

if __name__ == "__main__":
    asyncio.run(test_mermaid_rendering()) 