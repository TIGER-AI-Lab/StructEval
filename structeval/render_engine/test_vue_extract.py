import os
import json
import logging
from render_vue import extract_vue_code_from_tag

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_vue_extraction():
    """Test the Vue code extraction from different formats"""
    
    # Read the Vue example from html.json
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Find Vue tasks (task_id starts with "0016")
    vue_tasks = [task for task in tasks if task.get("task_id", "").startswith("0016")]
    
    if not vue_tasks:
        logging.error("No Vue tasks found in html.json")
        return
    
    # Test extracting from each Vue task
    for task in vue_tasks:
        task_id = task.get("task_id", "unknown")
        generation = task.get("generation", "")
        
        logging.info(f"Extracting Vue code from task {task_id}")
        
        # Extract Vue code
        vue_code = extract_vue_code_from_tag(generation)
        if not vue_code:
            logging.error(f"Failed to extract Vue code from task {task_id}")
            continue
        
        logging.info(f"Extracted Vue code:")
        logging.info(vue_code)
        
        # Validate the extracted code is proper JavaScript object syntax
        try:
            # Basic syntax check - does it start with { and end with }?
            if not (vue_code.strip().startswith('{') and vue_code.strip().endswith('}')):
                logging.error(f"Extracted code is not a valid JavaScript object: {vue_code[:50]}...")
                continue
                
            logging.info(f"Extraction successful for task {task_id}")
            
            # Save the extracted code to a file for inspection
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"{task_id}_extracted.js")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("// Template for Vue application\nconst { createApp } = Vue;\n\n")
                f.write(f"// Vue component from task {task_id}\n")
                f.write(f"const App = {vue_code};\n\n")
                f.write("// Mount the app\nconst app = createApp(App);\napp.mount('#app');")
            
            logging.info(f"Saved extracted code to {output_file}")
        except Exception as e:
            logging.error(f"Error validating Vue code: {e}")

if __name__ == "__main__":
    test_vue_extraction() 