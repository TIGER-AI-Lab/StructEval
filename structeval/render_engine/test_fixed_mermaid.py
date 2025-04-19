import os
import json
import logging
import asyncio
from render_mermaid import render_mermaid_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_fixed_mermaid():
    """Test mermaid rendering with a fixed version of the problematic diagram"""
    # Set up output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Use a fixed version of the mermaid code from task 000900
    # Removed direction TB which was causing the error
    task_id = "000900_fixed"
    mermaid_code = """
    flowchart TD
      %% Title
      classDef titleStyle fill=white font-size=20px font-weight=bold;
      
      subgraph Smart_Home_Routine[Smart Home Routine]
        detect([Detect Sensor Input]):::start
        decide{{Decide: Manual or Auto?}}:::decision
        actuate[Actuate Devices]:::action
        verify([Verify Outcome]):::end

        detect -->|Sensor triggers| decide
        decide -->|Auto selected| actuate
        decide -->|Manual override| actuate
        actuate -->|Execute command| verify
        verify -->|Monitor for changes| detect
      end

      %% Legend
      subgraph Legend [Legend]
        rect1[Rectangular Node = Action Step]
        para1{{Parallelogram Node = Decision Point}}
        startColor([Start Node with unique color])
        endColor([End Node with contrasting color])
      end

      %% Styles
      classDef start fill=#d1e8ff,stroke=#333,stroke-width=1px;
      classDef end fill=#ffe0b3,stroke=#333,stroke-width=1px;
      classDef action fill=#ffffff,stroke=#333,stroke-width=1px;
      classDef decision fill=#f9f9a9,stroke=#333,stroke-width=1px;
      classDef legendRect fill=#ffffff,stroke-dasharray: 5 5;
      classDef legendPara fill=#f9f9a9,stroke-dasharray: 5 5;
    """
    
    output_path = os.path.join(output_dir, f"{task_id}.png")
    
    logging.info(f"Testing mermaid rendering with fixed code")
    render_score = await render_mermaid_and_screenshot(task_id, mermaid_code, output_path)
    
    if render_score > 0:
        logging.info(f"Mermaid rendering successful! Score: {render_score}, Image saved to {output_path}")
    else:
        logging.error("Mermaid rendering failed.")

if __name__ == "__main__":
    asyncio.run(test_fixed_mermaid()) 